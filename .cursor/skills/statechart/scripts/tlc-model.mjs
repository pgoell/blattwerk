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


export function buildModel(env) {
  const {
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
    fill
  } = env;
function modelOf(graph, lookup = (vars) => vars) {
  const byId = new Map([...graph.nodes.keys()].map((id) => [id, new Set()]));
  for (const e of [...graph.edges, ...graph.loops]) byId.get(e.from).add(e.action);
  const index = new Map(
    [...graph.nodes.values()].map((n) => [stateKey(n.raw ?? n.vars), byId.get(n.id)]),
  );
  const facts = (vars) => factsFrom(index.get(stateKey(lookup(vars))) ?? new Set());
  return {
    graph,
    facts,
    key: (vars) => keyOf(vars, facts(vars)),
    customer: (vars) => String(mapping.state(vars, facts(vars))),
  };
}

function quotient(m) {
  const { graph } = m;
  const keys = new Map();
  for (const n of graph.nodes.values()) keys.set(n.id, m.key(n.vars));
  const nodes = new Set(keys.values());
  const initial = new Set(
    [...graph.nodes.values()].filter((n) => n.init).map((n) => keys.get(n.id)),
  );
  const edges = new Map();
  for (const e of graph.edges) {
    const from = keys.get(e.from);
    const to = keys.get(e.to);
    if (from === to) continue;
    const id = edgeId(from, to);
    if (!edges.has(id)) edges.set(id, { from, to, counts: new Map(), guards: new Map() });
    const [before, after] = [graph.nodes.get(e.from).vars, graph.nodes.get(e.to).vars];
    const label = stepLabel(e.action, before, after);
    if (!label) continue;
    edges.get(id).counts.set(label, (edges.get(id).counts.get(label) ?? 0) + 1);
    addGuard(edges.get(id).guards, label, stepGuard(e.action, before, after));
  }
  for (const e of edges.values())
    e.labels = new Set([...e.counts].sort((a, b) => b[1] - a[1]).map(([l]) => l));
  const settled = new Set(
    [...graph.nodes.values()].filter((n) => m.facts(n.vars).settled).map((n) => keys.get(n.id)),
  );
  return { nodes, initial, edges, keys, settled };
}

const graph = parseDot(fs.readFileSync(args.dot, "utf8"));
const main = modelOf(graph);
const now = quotient(main);
const mainInit = [...graph.nodes.values()].find((n) => n.init).vars;

const secondDot = args.fixedDot ?? args.againstDot;
const secondGraph = secondDot ? parseDot(fs.readFileSync(secondDot, "utf8")) : null;
const secondInit = secondGraph && [...secondGraph.nodes.values()].find((n) => n.init).vars;
const lacks = secondGraph ? lacking(mainInit, secondInit) : [];
const extra = secondGraph ? lacking(secondInit, mainInit) : [];
const secondFilled = secondGraph && {
  ...secondGraph,
  nodes: new Map(
    [...secondGraph.nodes].map(([id, n]) => [
      id,
      { ...n, raw: n.vars, vars: fill(n.vars, lacks, mainInit) },
    ]),
  ),
};
const second = secondFilled && modelOf(secondFilled, (vars) => omit(vars, lacks));
const secondQ = second && quotient(second);

function readerPath(trace, key, labelOf = stepLabel) {
  const out = [{ key: key(trace.steps[0].vars), label: null, modelStep: 0 }];
  for (let i = 1; i < trace.steps.length; i++) {
    const { action } = trace.steps[i];
    const k = key(trace.steps[i].vars);
    if (k === out[out.length - 1].key && !readerActions.has(action)) continue;
    const [before, after] = [trace.steps[i - 1].vars, trace.steps[i].vars];
    const label = labelOf(action, before, after) || action;
    const guard = stepGuard(action, before, after);
    out.push({ key: k, label, guard, action, modelStep: i });
  }
  return out;
}

const readerLabel = (action, before, after) => stepLabel(action, before, after, "customer");
function replaySecond(trace) {
  if (!second) return null;
  const shared = (vars) => stateKey(omit(vars, lacks));
  const sharedOf = (n) => stateKey(omit(n.raw, extra));
  const out = new Map();
  for (const e of [...second.graph.edges, ...second.graph.loops]) {
    if (!out.has(e.from)) out.set(e.from, []);
    out.get(e.from).push(e);
  }
  const actions = new Set([...second.graph.edges, ...second.graph.loops].map((e) => e.action));
  const nodeOf = (id) => second.graph.nodes.get(id);
  const screen = new Map(
    [...second.graph.nodes.values()].map((n) => [n.id, second.customer(n.vars)]),
  );
  const words = (e) => readerLabel(e.action, nodeOf(e.from).vars, nodeOf(e.to).vars) || e.action;
  const settle = (ids) => {
    const all = new Set(ids);
    for (const id of all)
      for (const e of out.get(id) ?? [])
        if (!readerActions.has(e.action) && screen.get(e.to) === screen.get(id)) all.add(e.to);
    return all;
  };
  const seen = readerPath(trace, main.customer, readerLabel);
  const shownAt = new Map(seen.map((p, j) => [p.modelStep, j]));
  let here = settle(
    [...second.graph.nodes.values()]
      .filter((n) => n.init && screen.get(n.id) === seen[0].key)
      .map((n) => n.id),
  );
  if (here.size === 0) return { reason: "starts on another screen" };
  const passed = new Set(here);
  let j = 0;
  for (let i = 1; i < trace.steps.length; i++) {
    const { action } = trace.steps[i];
    const hidden = !shownAt.has(i);
    if (!hidden) j = shownAt.get(i);
    const want = seen[j];
    const [before, after] = [trace.steps[i - 1].vars, trace.steps[i].vars];
    const known = actions.has(action);
    if (!known && (hidden || shared(before) === shared(after))) continue;
    const tries = [...here].flatMap((id) =>
      (out.get(id) ?? []).filter((e) =>
        known ? e.action === action : sharedOf(nodeOf(e.to)) === shared(after),
      ),
    );
    if (hidden && tries.length === 0) continue;
    const same = known
      ? tries.filter((e) => screen.get(e.to) === want.key && (hidden || words(e) === want.label))
      : tries;
    if (same.length) {
      here = settle(same.map((e) => e.to));
      for (const id of here) passed.add(id);
      continue;
    }
    const outcomes = new Map();
    for (const e of tries) {
      const id = `${screen.get(e.to)}${SEP}${words(e)}`;
      outcomes.set(id, [...(outcomes.get(id) ?? []), e]);
    }
    const taken = [...outcomes.values()].sort((a, b) => b.length - a.length)[0]?.[0];
    const from = main.key(before);
    const said = hidden ? readerLabel(action, before, after) || action : want.label;
    const at = { step: j, said, from, hidden };
    if (!taken)
      return {
        ...at,
        key: from,
        label: stepLabel(action, before, after) || action,
        disabled: true,
      };
    const [b, a] = [nodeOf(taken.from).vars, nodeOf(taken.to).vars];
    return { ...at, key: second.key(a), label: stepLabel(taken.action, b, a) || taken.action };
  }
  const bad = new Set(
    rawSecondTraces
      .filter((t) => t.invariant === trace.invariant)
      .map((t) => stateKey(t.steps[t.steps.length - 1].vars)),
  );
  const ruleHolds =
    secondTraceFiles.length > 0 && ![...passed].some((id) => bad.has(stateKey(nodeOf(id).vars)));
  return { sameEnd: true, ruleHolds };
}

function readTraces(files, paths = []) {
  return files.flatMap((f) => {
    const text = fs.readFileSync(f, "utf8");
    checkTlcOutput(text, f);
    return parseTraces(text).map((t) => ({
      ...t,
      steps: t.steps.map((s) => ({ ...s, vars: fill(s.vars, paths, mainInit) })),
    }));
  });
}
// With -continue, TLC reports every bad state, including states after the first bad one.
function firstBad(raw) {
  const badStates = new Map();
  for (const t of raw) {
    if (!badStates.has(t.invariant)) badStates.set(t.invariant, new Set());
    badStates.get(t.invariant).add(stateKey(t.steps[t.steps.length - 1].vars));
  }
  const cuts = [];
  const seen = new Set();
  for (const t of raw) {
    const first = t.steps.findIndex((s) => badStates.get(t.invariant).has(stateKey(s.vars)));
    const cut = { invariant: t.invariant, steps: t.steps.slice(0, first + 1) };
    const id = `${t.invariant}${SEP}${stateKey(cut.steps[cut.steps.length - 1].vars)}`;
    if (seen.has(id)) continue;
    seen.add(id);
    cuts.push(cut);
  }
  return cuts;
}
const rawTraces = readTraces(args.traces);
const secondTraceFiles = role === "fix" ? args.fixedTraces : args.againstTraces;
const rawSecondTraces = readTraces(secondTraceFiles, lacks);
const traces = firstBad(rawTraces);
const secondTraces = firstBad(rawSecondTraces);
function group(cuts, m) {
  const byId = new Map();
  for (const trace of cuts) {
    const rp = readerPath(trace, m.customer);
    const last = trace.steps[trace.steps.length - 1].vars;
    const said =
      typeof mapping.cause === "function"
        ? mapping.cause(last, m.facts(last), trace.invariant)
        : null;
    const cause = said === undefined || said === null ? null : String(said);
    const id = `${trace.invariant}${SEP}${cause ?? rp[rp.length - 1].key}`;
    const prev = byId.get(id);
    if (
      !prev ||
      rp.length < prev.steps ||
      (rp.length === prev.steps && trace.steps.length < prev.trace.steps.length)
    ) {
      byId.set(id, {
        id,
        cause,
        steps: rp.length,
        trace,
        invariant: trace.invariant,
        count: (prev?.count ?? 0) + 1,
      });
    } else prev.count++;
  }
  return byId;
}
const byOrder = (a, b) =>
  a.steps - b.steps ||
  a.trace.steps.length - b.trace.steps.length ||
  (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
const inSecond = (l) => `${within} ${L}, ${l}`;
const modelEdges = new Map(now.edges);
if (secondQ)
  for (const [id, e] of secondQ.edges)
    if (!modelEdges.has(id))
      modelEdges.set(id, {
        ...e,
        labels: new Set([...e.labels].map(inSecond)),
        guards: new Map([...e.guards].map(([l, words]) => [inSecond(l), words])),
        secondOnly: true,
      });
function divergence(s) {
  if (s?.key === undefined) return s;
  const plain = edgeId(s.from, s.key);
  const text = inSecond(`${s.label}${s.disabled ? " cannot happen" : ""}`);
  const drawn = !s.disabled && [s.label, text].some((l) => modelEdges.get(plain)?.labels.has(l));
  return { ...s, text, edge: drawn ? plain : `${plain}${SEP}second` };
}
const withPath = (c, m) => {
  const path = readerPath(c.trace, m.key);
  return { ...c, path, end: path[path.length - 1].key };
};
const classesById = group(traces, main);
const mainClasses = [...classesById.values()]
  .sort(byOrder)
  .map((c) => ({ ...withPath(c, main), second: divergence(replaySecond(c.trace)) }));
const introduced = second
  ? [...group(secondTraces, second).values()]
      .filter((c) => !classesById.has(c.id))
      .sort(byOrder)
      .map((c) => ({ ...withPath(c, second), second: null, introduced: true }))
  : [];
const classes = [...mainClasses, ...introduced];

const diverges = (c) => c.second?.key !== undefined;
function badKeys(m, keys, raw) {
  const g = m.graph;
  const bad = new Set(raw.map((t) => stateKey(t.steps[t.steps.length - 1].vars)));
  const out = new Set(raw.map((t) => m.key(t.steps[t.steps.length - 1].vars)));
  const ok = (id) => !bad.has(stateKey(g.nodes.get(id).vars));
  const next = new Map();
  for (const e of g.edges) {
    if (!next.has(e.from)) next.set(e.from, []);
    next.get(e.from).push(e.to);
  }
  const clean = new Set([...g.nodes.values()].filter((n) => n.init && ok(n.id)).map((n) => n.id));
  const queue = [...clean];
  while (queue.length) {
    for (const to of next.get(queue.shift()) ?? []) {
      if (clean.has(to) || !ok(to)) continue;
      clean.add(to);
      queue.push(to);
    }
  }
  const reached = new Set([...clean].map((id) => keys.get(id)));
  for (const k of keys.values()) if (!reached.has(k)) out.add(k);
  return out;
}
const badNow = badKeys(main, now.keys, rawTraces);
const badSecond =
  second && secondTraceFiles.length > 0
    ? badKeys(second, secondQ.keys, rawSecondTraces)
    : role === "fix"
      ? badNow
      : new Set();
const allNodes = new Set([...now.nodes, ...(secondQ?.nodes ?? [])]);
const initial = new Set([...now.initial, ...(secondQ?.initial ?? [])]);
const onlySecond = (k) => second && !now.nodes.has(k);
const status = (k) => {
  if (role === "against")
    return badNow.has(k) || badSecond.has(k) ? "wrong" : onlySecond(k) ? "fixed" : "works";
  if (role === "fix")
    return badSecond.has(k) ? "wrong" : badNow.has(k) || onlySecond(k) ? "fixed" : "works";
  return badNow.has(k) ? "wrong" : "works";
};

const chosen = args.highlight > 0 ? classes[args.highlight - 1] : null;
if (args.highlight > 0 && classes.length > 0 && !chosen)
  throw new Error(`--highlight ${args.highlight}: only ${classes.length} classes`);
const onPath = new Set(chosen ? chosen.path.map((p) => p.key) : []);
if (chosen && diverges(chosen)) onPath.add(chosen.second.key);

const edgesAlong = (c) =>
  c.path.slice(1).map((p, i) => ({
    id: edgeId(c.path[i].key, p.key),
    from: c.path[i].key,
    to: p.key,
    label: p.label,
    guard: p.guard,
  }));
  return {
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
  };
}
