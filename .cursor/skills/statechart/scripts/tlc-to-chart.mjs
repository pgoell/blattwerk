#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import {
  pathToFileURL,
} from "node:url";
import {
  FULL_LABELS,
  GROUP_PALETTE,
  LEGEND_ID,
  PLAIN_FILL,
  compareCharts,
  groupClassDef,
  groupColorProblem,
  parseMermaid,
  productOf,
  quote,
  STATUS_CLASSES,
} from "./mermaid.mjs";
import {
  checkTlcOutput,
  isRecord,
  joinLabels,
  parseDot,
  parseTraces,
  ruleSentences,
  stateKey,
  wrap,
} from "./lib.mjs";

import { HELP, USAGE } from "./tlc-help.mjs";
import { buildModel } from "./tlc-model.mjs";
import { makeRegions } from "./tlc-regions.mjs";
import { writeChart } from "./tlc-write.mjs";
const more = "Run node tlc-to-chart.mjs --help for the flags.";

const args = {
  traces: [],
  fixedTraces: [],
  againstTraces: [],
  specs: [],
  view: "customer",
  highlight: 1,
};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  const next = () => process.argv[++i];
  if (a === "-h" || a === "--help") {
    console.log(HELP);
    process.exit(0);
  } else if (a === "--dot") args.dot = next();
  else if (a === "--map") args.map = next();
  else if (a === "--traces") args.traces.push(next());
  else if (a === "--fixed-dot") args.fixedDot = next();
  else if (a === "--fixed-traces") args.fixedTraces.push(next());
  else if (a === "--against-dot") args.againstDot = next();
  else if (a === "--against-traces") args.againstTraces.push(next());
  else if (a === "--label") args.label = next();
  else if (a === "--spec") args.specs.push(next());
  else if (a === "--view") args.view = next();
  else if (a === "--highlight") args.highlight = Number(next());
  else if (a === "--path-only") args.pathOnly = true;
  else if (a === "--full-labels") args.fullLabels = true;
  else if (a === "--flat") args.flat = true;
  else if (a === "--regions") args.regions = true;
  else if (a === "--proof") args.proof = next();
  else if (a === "--regions-all") args.regionsAll = next();
  else if (a === "--cover") args.cover = true;
  else if (a === "--title") args.title = next();
  else if (a === "--out") args.out = next();
  else if (a === "--story") args.story = next();
  else if (a === "--summary") args.summary = next();
  else {
    console.error(`unknown argument ${a}. ${more}`);
    process.exit(2);
  }
}
const fail = (message) => {
  console.error(`${message} ${more}`);
  process.exit(2);
};
if (!args.dot || !args.map) fail(USAGE);
if (!["customer", "developer", "layered"].includes(args.view))
  fail(`--view must be customer, developer, or layered, not ${args.view}.`);
if (args.fixedDot && args.againstDot) fail("use --fixed-dot or --against-dot, not both.");
if (args.fixedTraces.length && !args.fixedDot) fail("--fixed-traces needs --fixed-dot.");
if (args.againstTraces.length && !args.againstDot) fail("--against-traces needs --against-dot.");
if (args.label !== undefined && !args.fixedDot && !args.againstDot)
  fail("--label names the second model; it needs --fixed-dot or --against-dot.");
if (args.proof && !args.regions) fail("--proof writes the regions proof; it needs --regions.");
if (args.regionsAll && !args.regions)
  fail("--regions-all writes every regions arrow; it needs --regions.");
if (
  args.regions &&
  (args.view !== "customer" || args.flat || args.pathOnly || args.highlight !== 0)
)
  fail(
    "--regions draws the whole customer chart: use --highlight 0, without --flat or --path-only.",
  );

const role = args.fixedDot ? "fix" : args.againstDot ? "against" : null;
const L = args.label ?? (role === "fix" ? "the fix" : "the spec");
const within = role === "fix" ? "with" : "in";
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

const mapping = await import(pathToFileURL(path.resolve(args.map)).href);
if (typeof mapping.state !== "function")
  throw new Error("the mapping module must export state(vars)");
if (args.view !== "customer" && typeof mapping.detail !== "function")
  throw new Error(`--view ${args.view} needs detail(vars) in the mapping module`);
const SEP = "\u0000";
const edgeId = (from, to) => `${from}${SEP}${SEP}${to}`;

const rules = new Map();
for (const f of args.specs)
  for (const [name, sentence] of ruleSentences(fs.readFileSync(f, "utf8")))
    if (!rules.has(name)) rules.set(name, sentence);

const readerActions = new Set(mapping.readerActions ?? []);
const factsFrom = (enabled) => ({
  enabled,
  settled: [...enabled].every((a) => readerActions.has(a)),
});
function keyOf(vars, facts) {
  if (args.view === "developer") return String(mapping.detail(vars, facts));
  const outer = mapping.state(vars, facts);
  if (typeof outer !== "string")
    throw new Error(`state() must return a string; got ${JSON.stringify(outer)}`);
  return args.view === "layered" ? `${outer}${SEP}${mapping.detail(vars, facts)}` : outer;
}
function stepLabel(action, before, after, view = args.view) {
  const said = typeof mapping.step === "function" ? mapping.step(action, before, after) : action;
  const named = view === "customer" || said === action ? said : `${said} [${action}]`;
  const seconds = typeof mapping.timer === "function" ? mapping.timer(action, before, after) : null;
  if (seconds === undefined || seconds === null || seconds === "" || !named) return named;
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds <= 0)
    throw new Error(
      `timer() must return a number of seconds above 0, or nothing; got ${JSON.stringify(seconds)} for ${action}`,
    );
  return `after ${seconds} s, ${named}`;
}
function stepGuard(action, before, after) {
  if (typeof mapping.guard !== "function") return "";
  return String(mapping.guard(action, before, after) ?? "")
    .replace(/[[\]]/g, "")
    .trim();
}
function guarded(guards, label) {
  const words = guards?.get(label);
  return words && !words.has("") ? `${label} [${[...words].sort().join(" or ")}]` : label;
}
const addGuard = (guards, label, words) => {
  if (!guards.has(label)) guards.set(label, new Set());
  guards.get(label).add(words);
};

function lacking(a, b, prefix = []) {
  return Object.keys(a).flatMap((k) =>
    !(k in b)
      ? [[...prefix, k]]
      : isRecord(a[k]) && isRecord(b[k])
        ? lacking(a[k], b[k], [...prefix, k])
        : [],
  );
}
const holder = (o, p) => p.slice(0, -1).reduce((x, k) => (isRecord(x?.[k]) ? x[k] : null), o);
function omit(vars, paths) {
  if (!paths.length) return vars;
  const out = structuredClone(vars);
  for (const p of paths) {
    const o = holder(out, p);
    if (o) delete o[p.at(-1)];
  }
  return out;
}
function fill(vars, paths, from) {
  if (!paths.length) return vars;
  const out = structuredClone(vars);
  for (const p of paths) {
    const [o, f] = [holder(out, p), holder(from, p)];
    if (o && f && p.at(-1) in f) o[p.at(-1)] = structuredClone(f[p.at(-1)]);
  }
  return out;
}

const {
  modelEdges,
    classes,
    initial,
    lacks,
    main,
    diverges,
    status,
    edgesAlong,
    second,
    mainClasses,
    group,
    allNodes,
    graph,
    onPath,
    introduced,
    secondQ,
    chosen,
    now,
} = buildModel({
  args,
    role,
    L,
    within,
    mapping,
    SEP,
    edgeId,
    readerActions,
    factsFrom,
    keyOf,
    stepLabel,
    stepGuard,
    addGuard,
    lacking,
    omit,
    fill,
});
function chartEdges() {
  const edges = new Map(modelEdges);
  for (const { second: s } of classes.filter(diverges)) {
    if (modelEdges.has(s.edge)) continue;
    if (!edges.has(s.edge))
      edges.set(s.edge, { from: s.from, to: s.key, labels: new Set(), secondOnly: true });
    edges.get(s.edge).labels.add(s.text);
  }
  const pathNumbers = new Map();
  (chosen ? edgesAlong(chosen) : []).forEach((step, i) => {
    if (!pathNumbers.has(step.id)) pathNumbers.set(step.id, []);
    const shown = step.guard ? `${step.label} [${step.guard}]` : step.label;
    pathNumbers.get(step.id).push({ n: i + 1, label: step.label, shown });
    if (!edges.has(step.id))
      edges.set(step.id, { from: step.from, to: step.to, labels: new Set([step.label]) });
  });
  if (!args.cover) return { edges, pathNumbers, coverEdges: null };

  const coverEdges = new Set();
  const bfs = (q, targets) => {
    const parent = new Map([...q.initial].map((k) => [k, null]));
    const queue = [...q.initial];
    const outEdges = new Map();
    for (const [id, e] of q.edges) {
      if (!outEdges.has(e.from)) outEdges.set(e.from, []);
      outEdges.get(e.from).push([id, e]);
    }
    while (queue.length) {
      const k = queue.shift();
      for (const [id, e] of outEdges.get(k) ?? []) {
        if (parent.has(e.to)) continue;
        parent.set(e.to, id);
        queue.push(e.to);
      }
    }
    for (const t of targets) {
      for (let id = parent.get(t); id; id = parent.get(q.edges.get(id).from)) coverEdges.add(id);
    }
  };
  bfs(now, now.settled);
  if (secondQ)
    bfs(
      secondQ,
      [...secondQ.settled].filter((k) => !now.nodes.has(k)),
    );
  const pathLabels = new Map();
  for (const c of classes) {
    for (const step of edgesAlong(c)) {
      coverEdges.add(step.id);
      pathLabels.set(step.id, (pathLabels.get(step.id) ?? new Set()).add(step.label));
    }
    if (diverges(c)) coverEdges.add(c.second.edge);
  }
  for (const id of coverEdges) {
    if (edges.has(id)) continue;
    const [from, to] = id.split(`${SEP}${SEP}`);
    edges.set(id, { from, to, labels: pathLabels.get(id) });
  }
  return { edges, pathNumbers, coverEdges };
}
const { edges, pathNumbers, coverEdges } = chartEdges();

const LEGEND = {
  works: ["legendWorks", mapping.legend?.works ?? (role === "fix" ? "Works today" : "Works")],
  wrong: [
    "legendWrong",
    mapping.legend?.wrong ?? (role === "fix" ? `Still wrong with ${L}` : "Breaks a rule"),
  ],
  fixed: [
    "legendFixed",
    mapping.legend?.fixed ?? (role === "fix" ? `Fixed or new with ${L}` : `Only in ${L}`),
  ],
};

const grouping = typeof mapping.group === "function";
const groupsOf = new Map();
const groupOf = (k) => (groupsOf.get(k)?.size === 1 ? [...groupsOf.get(k)][0] : "");
const groupNames = [];
const fills = new Map();
if (grouping) {
  const add = (k, vars, m) => {
    const g = mapping.group(vars, m.facts(vars));
    if (g !== undefined && g !== null && typeof g !== "string")
      throw new Error(`group() must return a group name or nothing; got ${JSON.stringify(g)}`);
    if (!groupsOf.has(k)) groupsOf.set(k, new Set());
    groupsOf.get(k).add((g ?? "").replace(/\s+/g, " ").trim());
  };
  for (const n of graph.nodes.values()) add(now.keys.get(n.id), n.vars, main);
  if (second)
    for (const n of second.graph.nodes.values()) add(secondQ.keys.get(n.id), n.vars, second);

  const given = mapping.groupColors ?? {};
  if (!isRecord(given))
    throw new Error("groupColors must be an object from a group name to a color such as #d6eaf8");
  const statusNames = new Set(
    [
      "Works",
      "Works today",
      "Breaks a rule",
      "Still wrong",
      "Fixed",
      ...Object.values(LEGEND).map(([, t]) => t),
    ].map((t) => t.toLowerCase()),
  );
  const found = new Set([...groupsOf.values()].flatMap((gs) => [...gs]).filter(Boolean));
  for (const g of found)
    if (statusNames.has(g.toLowerCase()))
      throw new Error(
        `group "${g}" has the name of a status; TLC decides the status, so name the group for what the reader sees`,
      );
  groupNames.push(
    ...Object.keys(given).filter((g) => found.has(g)),
    ...[...found].filter((g) => !Object.hasOwn(given, g)).sort(),
  );
  for (const [g, color] of Object.entries(given)) {
    if (color === undefined || color === null || color === "") continue;
    const why = groupColorProblem(color);
    if (why) throw new Error(`groupColors["${g}"] ${JSON.stringify(color)} ${why}`);
    if (found.has(g)) fills.set(g, color.toLowerCase());
  }
  const free = GROUP_PALETTE.filter((c) => ![...fills.values()].includes(c));
  for (const g of groupNames) {
    if (fills.has(g)) continue;
    if (!free.length)
      throw new Error(
        `the mapping has ${groupNames.length} groups, more than the ${GROUP_PALETTE.length} colors of the palette; give the others a color in groupColors`,
      );
    fills.set(g, free.shift());
  }
}
const mixedGroups = [...groupsOf].filter(([, gs]) => gs.size > 1).map(([k]) => k);

const BORDER = { works: "", wrong: "Wrong", fixed: "Fixed" };
const classFor = (g, s, path) =>
  grouping
    ? `${g ? `group${groupNames.indexOf(g)}` : "plain"}${BORDER[s] || (path ? "Path" : "")}`
    : `${s}${path ? "Path" : ""}`;
const drawnState = (g, s, path = false) => ({ group: g, status: s, cls: classFor(g, s, path) });
const groupCounts = (drawn) =>
  groupNames
    .map((g) => ({
      name: g,
      color: fills.get(g),
      states: drawn.filter((d) => d.group === g).length,
    }))
    .filter((g) => g.states > 0);

// Mermaid shrinks a chart to the page width unless useMaxWidth is false, and rewraps labels that
// wrap() already wrapped unless markdownAutoWrap is false.
const frontMatter = (title) => [
  "---",
  ...(title ? [`title: ${JSON.stringify(title)}`] : []),
  "config:",
  "  markdownAutoWrap: false",
  "  state:",
  "    useMaxWidth: false",
  "---",
];
function head(drawn) {
  const out = [...frontMatter(args.title), "stateDiagram-v2"];
  if (role) out.push(`  %% second model (${role}): ${L}`);
  if (args.fullLabels) out.push(`  ${FULL_LABELS}`);
  const used = Object.keys(LEGEND).filter((s) => drawn.some((d) => d.status === s));
  const legend = grouping
    ? [
        ...groupCounts(drawn).map(({ name }) => {
          const i = groupNames.indexOf(name);
          return [`legendGroup${i}`, name, `group${i}`];
        }),
        ...used.filter((s) => BORDER[s]).map((s) => [...LEGEND[s], `plain${BORDER[s]}`]),
      ]
    : used.map((s) => [...LEGEND[s], s]);
  if (grouping) {
    const styleClasses = new Set([...drawn.map((d) => d.cls), ...legend.map(([, , c]) => c)]);
    const bases = [["plain", PLAIN_FILL], ...groupNames.map((g, i) => [`group${i}`, fills.get(g)])];
    for (const [base, fill] of bases)
      for (const border of ["", "Wrong", "Fixed", "Path"])
        if (styleClasses.has(base + border)) out.push(`  ${groupClassDef(base, fill, border)}`);
  } else for (const c of STATUS_CLASSES) out.push(`  ${c}`);
  if (legend.length) {
    out.push(`  state "Legend" as ${LEGEND_ID} {`);
    for (const [id, text] of legend) out.push(`    state "${quote(text)}" as ${id}`);
    out.push("  }");
    for (const [id, , c] of legend) out.push(`  class ${id} ${c}`);
  }
  return out;
}

const {
  regionsChart,
} = makeRegions({
  mapping,
    SEP,
    guarded,
    addGuard,
    second,
    classes,
    diverges,
    initial,
    status,
    edgesAlong,
    edges,
    LEGEND,
    groupOf,
    drawnState,
    groupCounts,
    frontMatter,
    head,
});
const regions = args.regions
  ? regionsChart({
      states: allNodes,
      starts: [...initial],
      edges,
      classes,
      proofPath: args.proof,
      allPath: args.regionsAll,
    })
  : null;
if (regions?.why) console.error(`regions: not drawn, because ${regions.why}`);

writeChart({
  args,
    role,
    L,
    within,
    cap,
    SEP,
    edgeId,
    rules,
    guarded,
    graph,
    lacks,
    second,
    mainClasses,
    introduced,
    classes,
    allNodes,
    initial,
    status,
    chosen,
    onPath,
    edges,
    pathNumbers,
    coverEdges,
    grouping,
    groupOf,
    mixedGroups,
    drawnState,
    groupCounts,
    head,
    regions,
});
