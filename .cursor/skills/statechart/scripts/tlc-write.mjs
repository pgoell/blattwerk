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


export function writeChart(env) {
  const {
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
    regions
  } = env;
const flatStates =
  args.pathOnly && chosen
    ? onPath
    : coverEdges
      ? new Set([
          ...initial,
          ...[...coverEdges].flatMap((id) => [edges.get(id).from, edges.get(id).to]),
        ])
      : allNodes;
const sorted = [...flatStates].sort();
const drawn = sorted.map((k) => drawnState(groupOf(k), status(k), onPath.has(k)));

const boxes = new Map();
const boxOf = new Map();
const inBox = (k, box) => {
  if (!boxes.has(box)) boxes.set(box, []);
  boxes.get(box).push(k);
};
if (args.view === "layered") for (const k of sorted) inBox(k, k.split(SEP)[0]);
else if (args.view === "customer" && !args.flat) {
  for (const k of sorted) {
    const at = k.indexOf(": ");
    if (at > 0 && at + 2 < k.length) inBox(k, k.slice(0, at));
  }
  for (const [box, members] of boxes) if (members.length < 2) boxes.delete(box);
}
const boxIds = new Map([...boxes.keys()].map((box, i) => [box, `g${i}`]));
for (const [box, members] of boxes) for (const k of members) boxOf.set(k, box);
const declared = [...[...boxes.values()].flat(), ...sorted.filter((k) => !boxOf.has(k))];
const stateIds = new Map(declared.map((k, i) => [k, `s${i}`]));
const idOf = (k) => stateIds.get(k);
const caption = (k) =>
  args.view === "layered" ? k.split(SEP)[1] : boxOf.has(k) ? k.slice(boxOf.get(k).length + 2) : k;

function numbered(steps) {
  const runs = [];
  for (const { n, shown } of steps) {
    const last = runs.at(-1);
    if (last?.shown === shown && last.n.at(-1) === n - 1) last.n.push(n);
    else runs.push({ shown, n: [n] });
  }
  return runs.map(({ shown, n }) => `${n.join(", ")}. ${shown}`);
}
const drawnLabels = new Set();
const arrows = new Map();
for (const [id, e] of edges) {
  if (!flatStates.has(e.from) || !flatStates.has(e.to)) continue;
  if (args.pathOnly && chosen && !pathNumbers.has(id) && id !== chosen.second?.edge) continue;
  if (coverEdges && !coverEdges.has(id)) continue;
  const pair = edgeId(e.from, e.to);
  if (!arrows.has(pair))
    arrows.set(pair, { from: e.from, to: e.to, groups: [[], [], []], plain: true, labels: [] });
  const a = arrows.get(pair);
  const [numbers, current, other] = a.groups;
  const all = [...e.labels];
  const shown = all.map((l) => guarded(e.guards, l));
  const said = args.fullLabels ? shown.join(" or ") : joinLabels(shown);
  const p = pathNumbers.get(id);
  const chosenStep = chosen?.second && id === chosen.second.edge;
  if (p) numbers.push(...numbered(p));
  else if (!e.secondOnly) current.push(said);
  else other.push(args.pathOnly && chosenStep ? chosen.second.text : said);
  if (chosenStep && !e.secondOnly) other.push(chosen.second.text);
  if (p || chosenStep || id.endsWith(`${SEP}second`)) a.plain = false;
  a.labels.push(...all);
  for (const l of p ? p.map((s) => s.label) : all) drawnLabels.add(l);
}
const transitions = [...arrows.values()].map(({ from, to, groups, plain, labels }) => ({
  from,
  to,
  // ";" ends a Mermaid statement, even inside a transition label.
  text: groups
    .map((g) =>
      g
        .filter(Boolean)
        .map((l) => wrap(l.replaceAll(";", ","), 30))
        .join("<br/>"),
    )
    .filter(Boolean)
    .join("<br/>#160;<br/>"),
  plain,
  labels: labels.sort(),
}));
const fromBox = [];
const folded = new Set();
for (const [box, members] of boxes) {
  const mine = new Set(members);
  const byStep = new Map();
  for (const l of transitions) {
    if (!l.plain || !mine.has(l.from) || mine.has(l.to)) continue;
    const step = `${l.to}${SEP}${l.text}${SEP}${l.labels.join(SEP)}`;
    if (!byStep.has(step)) byStep.set(step, []);
    byStep.get(step).push(l);
  }
  for (const same of byStep.values()) {
    if (new Set(same.map((l) => l.from)).size !== members.length) continue;
    for (const l of same) folded.add(l);
    fromBox.push({ ...same[0], box });
  }
}

const out = head(drawn);
for (const [box, members] of boxes) {
  out.push(`  state "${quote(wrap(box))}" as ${boxIds.get(box)} {`);
  for (const k of members) out.push(`    state "${quote(wrap(caption(k)))}" as ${idOf(k)}`);
  out.push("  }");
}
for (const k of sorted)
  if (!boxOf.has(k)) out.push(`  state "${quote(wrap(caption(k)))}" as ${idOf(k)}`);
for (const k of sorted)
  if (initial.has(k) && (!args.pathOnly || k === chosen?.path[0].key))
    out.push(`  [*] --> ${idOf(k)}`);
const arrow = (from, l) => `  ${from} --> ${idOf(l.to)}${l.text ? ` : ${l.text}` : ""}`;
for (const l of fromBox) out.push(arrow(boxIds.get(l.box), l));
for (const l of transitions) if (!folded.has(l)) out.push(arrow(idOf(l.from), l));
sorted.forEach((k, i) => out.push(`  class ${idOf(k)} ${drawn[i].cls}`));
const mermaid = regions?.mermaid ?? out.join("\n") + "\n";
if (args.out) fs.writeFileSync(args.out, mermaid);
else process.stdout.write(mermaid);

const show = (k) => (args.view === "layered" ? k.replace(SEP, ": ") : k);
const ruleOf = (c) => rules.get(c.invariant) ?? `\`${c.invariant}\``;
function secondLine(c) {
  const W = cap(within);
  if (c.introduced) return `Only ${L} has this bug. The steps above happen ${within} ${L}.`;
  const s = c.second;
  if (!s) return null;
  if (s.sameEnd)
    return s.ruleHolds
      ? `${W} ${L} you see the same screens and steps, yet the rule holds, so the state labels do not show what ${L} changes.`
      : `${W} ${L} you see the same screens and steps, so ${L} does not change this path.`;
  if (s.reason) return `${cap(L)} cannot take these steps: it ${s.reason}.`;
  const outcome = s.disabled
    ? "cannot happen, so you stay at"
    : s.key === s.from
      ? "keeps you at"
      : "takes you to";
  if (s.hidden) {
    const when = s.step ? `after step ${s.step}` : "before your first step";
    return `${W} ${L}, ${when}, "${s.said}" happens and ${outcome}: ${show(s.key)}.`;
  }
  return `${W} ${L}, step ${s.step} (${s.said}) ${outcome}: ${show(s.key)}.`;
}
if (args.story) {
  const lines = [];
  const header = role === "fix" ? `New with ${L}: ` : `Only in ${L}: `;
  classes.forEach((c, i) => {
    lines.push(`## ${i + 1}. ${c.introduced ? header : ""}${show(c.end)}`, "");
    lines.push(`Rule broken: ${ruleOf(c)}`);
    if (c.cause) lines.push(`Why: ${c.cause.replace(/\.$/, "")}.`);
    lines.push(
      c.count === 1
        ? "This is the only way to get here in the model."
        : `There are ${c.count} ways to get here in the model. This is the shortest.`,
      "",
    );
    c.path.forEach((p, j) =>
      lines.push(
        j === 0 ? `0. Start: ${show(p.key)}` : `${j}. ${cap(p.label)}. Now: ${show(p.key)}`,
      ),
    );
    lines.push("");
    const said = secondLine(c);
    if (said) lines.push(said, "");
  });
  fs.writeFileSync(args.story, lines.join("\n"));
}
const CODE_LIKE = /\b[a-z]{2,}[A-Z][a-z]|\b\w+_\w+\b|\b[A-Za-z_]\w*\(|\b[A-Z][a-z]+[A-Z][a-z]/;
const codeLike = [
  ...new Set([
    ...(args.view === "customer" ? [...sorted, ...drawnLabels] : []),
    ...classes.map((c) => c.cause).filter(Boolean),
  ]),
].filter((t) => CODE_LIKE.test(t));
const secondOf = (c) =>
  c.introduced
    ? role === "fix"
      ? `new with ${L}`
      : `only in ${L}`
    : c.second
      ? c.second.sameEnd
        ? c.second.ruleHolds
          ? "same screens, but the rule holds"
          : "unchanged"
        : (c.second.reason ?? show(c.second.key))
      : null;
const summary = {
  view: args.view,
  ...(role ? { second: { role, label: L, lacks: lacks.map((p) => p.join(".")) } } : {}),
  modelStates: graph.nodes.size,
  modelTransitions: graph.edges.length,
  chartStates: regions?.mermaid ? regions.states[0] + regions.states[1] : flatStates.size,
  chartTransitions: regions?.mermaid ? regions.transitions : transitions.length,
  chartStatus: regions?.mermaid
    ? regions.status
    : Object.fromEntries(
        ["works", "wrong", "fixed"].map((s) => [
          s,
          [...flatStates].filter((k) => status(k) === s).length,
        ]),
      ),
  ...(grouping
    ? {
        chartGroups: regions?.mermaid ? regions.groups : groupCounts(drawn),
        mixedGroups: mixedGroups.map(show).sort(),
      }
    : {}),
  ...(regions
    ? {
        regions: regions.mermaid
          ? {
              drawn: true,
              states: regions.states,
              transitions: regions.transitions,
              all: regions.all,
              flat: regions.flat,
            }
          : { drawn: false, why: regions.why },
      }
    : {}),
  classes: classes.map((c, i) => ({
    n: i + 1,
    end: show(c.end),
    invariant: c.invariant,
    rule: rules.get(c.invariant) ?? null,
    cause: c.cause,
    readerSteps: c.path.length - 1,
    modelSteps: c.trace.steps.length,
    counterexamples: c.count,
    [role ?? "fix"]: secondOf(c),
  })),
  codeLike,
};
if (args.summary) fs.writeFileSync(args.summary, JSON.stringify(summary, null, 2) + "\n");
const extraBugs = introduced.length
  ? `, ${introduced.length} ${role === "fix" ? `new with ${L}` : `only in ${L}`}`
  : "";
const drawnAs = regions?.mermaid
  ? ` of ${regions.all} in 2 regions (proved against ${regions.flat.states} states, ${regions.flat.transitions} transitions)`
  : "";
console.error(
  `chart: ${summary.chartStates} states, ${summary.chartTransitions} transitions${drawnAs} from ${summary.modelStates} model states; ` +
    `${mainClasses.length} bug(s)${extraBugs}`,
);
}
