const unwrap = (s) =>
  s
    .replace(/<br\s*\/?>|#160;/g, " ")
    .replace(/#(quot|34);/g, '"')
    .replace(/\s+/g, " ")
    .trim();

// Mermaid ends a quoted state caption at the first ", so a caption writes " as #quot;.
export const quote = (s) => String(s).replaceAll('"', "#quot;");

export const LEGEND_ID = "legend";
export const FULL_LABELS = "%% labels in full";

export function parseMermaid(text) {
  const names = new Map();
  const nevers = [];
  let last = null;
  const newPart = () => ({ children: [], transitions: [] });
  const root = { name: "", parts: [newPart()] };
  const stack = [root];
  const part = () => stack[stack.length - 1].parts.at(-1);
  const display = (id) => names.get(id) ?? id;
  const implicit = new Map();
  const declare = (id) => {
    const prev = implicit.get(id);
    if (prev)
      prev.children.splice(
        prev.children.findIndex((c) => c.name === id),
        1,
      );
    implicit.set(id, null);
  };
  const mention = (id) => {
    if (id === "[*]" || implicit.has(id)) return;
    part().children.push({ name: id, leaf: true });
    implicit.set(id, part());
  };
  const body = text.replace(/^\s*---[ \t]*\r?\n[^]*?\r?\n---[ \t]*(\r?\n|$)/, "");
  for (const raw of body.split("\n")) {
    const line = raw.trim().replace(/(\[\*\]|[A-Za-z_]\w*):::[\w-]+/g, "$1");
    const when = /^%%\s*when\s+(not\s+)?(.+)$/.exec(line);
    if (when) {
      if (!last) throw new Error(`a %% when line must come right after a transition: ${line}`);
      if (!last.words)
        throw new Error(
          `the guarded step "${last.label}" must end its label with the guard's words in [ ]`,
        );
      last.when = { not: Boolean(when[1]), ids: when[2].split(",").map((s) => s.trim()) };
      last = null;
      continue;
    }
    last = null;
    const never = /^%%\s*never\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)(?:\s+--\s+(.*))?$/.exec(line);
    if (never) {
      nevers.push({
        name: never[1],
        states: never[2].split("&").map((s) => s.trim()),
        sentence: never[3] ?? "",
      });
      continue;
    }
    if (
      !line ||
      line.startsWith("%%") ||
      /^(stateDiagram|direction|classDef|class |note)/.test(line)
    )
      continue;
    let m = /^state\s+"([^"]*)"\s+as\s+([A-Za-z_]\w*)\s*(\{)?\s*$/.exec(line);
    if (!m) {
      const plain = /^state\s+([A-Za-z_]\w*)\s*(\{)?\s*$/.exec(line);
      if (plain) m = [line, null, plain[1], plain[2]];
    }
    if (m) {
      if (m[1] !== null && !names.has(m[2])) names.set(m[2], unwrap(m[1]));
      declare(m[2]);
      if (m[3]) {
        const node = { name: m[2], parts: [newPart()] };
        part().children.push(node);
        stack.push(node);
      } else part().children.push({ name: m[2], leaf: true });
      continue;
    }
    if (line === "}") {
      if (stack.length === 1) throw new Error("unmatched } in the chart");
      stack.pop();
      continue;
    }
    if (line === "--") {
      stack[stack.length - 1].parts.push(newPart());
      continue;
    }
    m = /^(\[\*\]|[A-Za-z_]\w*)\s*-->\s*(\[\*\]|[A-Za-z_]\w*)(?:\s*:\s*(.*))?$/.exec(line);
    if (m) {
      if (m[2] === "[*]" && m[1] !== "[*]")
        throw new Error(
          `cannot read final state in "${line}"; draw the step to the state the reader sees next`,
        );
      mention(m[1]);
      mention(m[2]);
      const said = m[3] ? unwrap(m[3]) : "";
      const label = said.replace(/\s*\[[^\]]*\]/g, "");
      last = { from: m[1], to: m[2], label, words: label !== said };
      part().transitions.push(last);
      continue;
    }
    m = /^([A-Za-z_]\w*)\s*:\s*(.*)$/.exec(line);
    if (m) {
      if (!names.has(m[1])) names.set(m[1], unwrap(m[2]));
      if (implicit.get(m[1]) === null) continue;
      declare(m[1]);
      part().children.push({ name: m[1], leaf: true });
      continue;
    }
    throw new Error(`cannot read chart line: ${line}`);
  }
  if (stack.length !== 1) throw new Error("the chart has an unclosed {");
  if (root.parts.length > 1)
    throw new Error(
      "the chart has -- outside a composite; to make parallel regions, split one top-level composite with --",
    );

  // Ids are global, as in Mermaid: a transition may name a state declared inside another composite.
  function region(p) {
    const out = { states: new Set(), initial: new Set(), transitions: [] };
    const info = new Map();
    const declared = new Set();
    (function collect(q) {
      for (const c of q.children) {
        if (c.name === LEGEND_ID) continue;
        declared.add(c.name);
        if (!c.leaf) for (const sub of c.parts) collect(sub);
      }
    })(p);
    const transitions = [];
    const lookup = (id) => {
      const found = info.get(id);
      if (!found) throw new Error(`transition names ${id}, which is not in this region`);
      return found;
    };
    function states(q, prefix, depth) {
      const local = q.children.filter((c) => c.name !== LEGEND_ID);
      for (const t of q.transitions) {
        for (const end of [t.from, t.to]) {
          if (end === "[*]" || declared.has(end)) continue;
          declared.add(end);
          local.push({ name: end, leaf: true });
        }
      }
      const all = [];
      for (const c of local) {
        if (info.has(c.name)) {
          if (local.indexOf(c) !== local.findIndex((x) => x.name === c.name)) continue;
          throw new Error(`state id ${c.name} is declared in two places`);
        }
        const full = `${prefix}${display(c.name)}`;
        if (c.leaf) {
          if (out.states.has(full))
            throw new Error(`two states have the caption "${full}"; give each its own caption`);
          out.states.add(full);
          info.set(c.name, { all: [full], initial: [full], depth });
          all.push(full);
          continue;
        }
        if (c.parts.length > 1)
          throw new Error(
            `${display(c.name)} splits into regions below the top level; make each region a top-level region`,
          );
        const inner = states(c.parts[0], `${full}.`, depth + 1);
        const initial = c.parts[0].transitions
          .filter((t) => t.from === "[*]")
          .flatMap((t) => lookup(t.to).initial);
        if (initial.length === 0)
          throw new Error(
            `${display(c.name)} has no [*] --> start, so a transition into it has nowhere to land`,
          );
        info.set(c.name, { all: inner, initial, depth });
        all.push(...inner);
      }
      for (const t of q.transitions) if (t.from !== "[*]" && t.to !== "[*]") transitions.push(t);
      return all;
    }
    states(p, "", 0);
    for (const t of p.transitions)
      if (t.from === "[*]") for (const s of lookup(t.to).initial) out.initial.add(s);
    transitions.sort((a, b) => lookup(b.from).depth - lookup(a.from).depth);
    const handled = new Set();
    let pending = [];
    let depth = null;
    for (const t of transitions) {
      const from = lookup(t.from);
      if (from.depth !== depth) {
        for (const h of pending) handled.add(h);
        pending = [];
        depth = from.depth;
      }
      for (const f of from.all) {
        const key = `${f}\u0000${t.label}`;
        if (t.label && handled.has(key)) continue;
        for (const to of lookup(t.to).initial)
          out.transitions.push({
            from: f,
            to,
            label: t.label,
            ...(t.when ? { when: t.when } : {}),
          });
        if (t.label) pending.push(key);
      }
    }
    return [out, info];
  }

  const owners = new Map();
  const regions = {};
  const top = root.parts[0];
  const machine = top.children.filter((c) => c.name !== LEGEND_ID);
  const parallel =
    machine.length === 1 &&
    !machine[0].leaf &&
    machine[0].parts.length > 1 &&
    top.transitions.every((t) => t.from === "[*]");
  if (parallel) {
    for (const p of machine[0].parts) {
      const [only] = p.children;
      const holder =
        p.children.length === 1 &&
        !only.leaf &&
        p.transitions.every((t) => t.from === "[*]" && t.to === only.name)
          ? only
          : null;
      if (holder && holder.parts.length > 1)
        throw new Error(`${display(holder.name)} splits into regions below the top level`);
      const name = holder ? display(holder.name) : `Region${Object.keys(regions).length + 1}`;
      const [r, ids] = region(holder ? holder.parts[0] : p);
      regions[name] = r;
      for (const [id, { all }] of ids) owners.set(id, { name, all });
    }
  } else {
    const [r, ids] = region(top);
    regions.Main = r;
    for (const [id, { all }] of ids) owners.set(id, { name: "Main", all });
  }
  for (const [name, r] of Object.entries(regions))
    for (const t of r.transitions) {
      if (!t.when) continue;
      if (!parallel)
        throw new Error("a %% when line guards a step on other regions, and the chart has none");
      const states = {};
      for (const id of t.when.ids) {
        const at = owners.get(id);
        if (!at)
          throw new Error(`a %% when line names ${id}, which is not a state id in the chart`);
        if (at.name === name)
          throw new Error(
            `a %% when line names ${display(id)}, which is in the step's own region; a guard reads other regions`,
          );
        states[at.name] = [...new Set([...(states[at.name] ?? []), ...at.all])].sort();
      }
      t.guard = { not: t.when.not, states };
      delete t.when;
    }
  return { regions, nevers };
}

function guardHolds(guard, at) {
  if (!guard) return true;
  const hits = Object.entries(guard.states).map(([r, states]) => states.includes(at[r]));
  return guard.not ? !hits.some(Boolean) : hits.every(Boolean);
}

export function productOf(regions) {
  const names = Object.keys(regions);
  const rs = Object.values(regions);
  const join = (parts) => parts.join(" | ");
  const byLabel = new Map();
  const unlabeled = [];
  rs.forEach((r, ri) => {
    for (const t of r.transitions) {
      if (!t.label) {
        unlabeled.push({ ri, from: t.from, to: t.to, guard: t.guard });
        continue;
      }
      if (!byLabel.has(t.label))
        byLabel.set(
          t.label,
          rs.map(() => new Map()),
        );
      const moves = byLabel.get(t.label)[ri];
      if (!moves.has(t.from)) moves.set(t.from, []);
      moves.get(t.from).push({ to: t.to, guard: t.guard });
    }
  });
  let starts = [[]];
  for (const r of rs) starts = starts.flatMap((p) => [...r.initial].map((s) => [...p, s]));
  const out = { states: new Set(), initial: new Set(starts.map(join)), transitions: [] };
  const seen = new Set(starts.map(join));
  const queue = [...starts];
  const step = (from, to, label) => {
    const [a, b] = [join(from), join(to)];
    if (a === b) return;
    out.transitions.push({ from: a, to: b, label });
    if (!seen.has(b)) {
      seen.add(b);
      queue.push(to);
    }
  };
  while (queue.length) {
    const cur = queue.shift();
    out.states.add(join(cur));
    const at = Object.fromEntries(names.map((n, ri) => [n, cur[ri]]));
    for (const u of unlabeled) {
      if (cur[u.ri] !== u.from || !guardHolds(u.guard, at)) continue;
      const next = [...cur];
      next[u.ri] = u.to;
      step(cur, next, "");
    }
    for (const [label, perRegion] of byLabel) {
      const open = perRegion.map((moves, ri) =>
        (moves.get(cur[ri]) ?? []).filter((m) => guardHolds(m.guard, at)).map((m) => m.to),
      );
      if (open.every((tos) => tos.length === 0)) continue;
      let nexts = [[]];
      open.forEach((tos, ri) => {
        const options = tos.length ? [...new Set(tos)] : [cur[ri]];
        nexts = nexts.flatMap((p) => options.map((s) => [...p, s]));
      });
      for (const next of nexts) step(cur, next, label);
    }
  }
  return out;
}

export function compareCharts(expectedRegions, actualRegions) {
  const expected = productOf(expectedRegions);
  const actual = productOf(actualRegions);
  const edgeSet = (m) => {
    const labeled = new Set();
    const out = new Set();
    for (const t of m.transitions) {
      if (!t.label) continue;
      labeled.add(`${t.from} --> ${t.to}`);
      for (const l of t.label.split(" or ")) out.add(`${t.from} --> ${t.to} : ${l}`);
    }
    for (const t of m.transitions)
      if (!t.label && !labeled.has(`${t.from} --> ${t.to}`)) out.add(`${t.from} --> ${t.to}`);
    return out;
  };
  const minus = (a, b) => [...a].filter((x) => !b.has(x)).sort();
  const unreached = [];
  const regionEntries = Object.entries(expectedRegions);
  if (regionEntries.length === 1) {
    for (const s of regionEntries[0][1].states) if (!expected.states.has(s)) unreached.push(s);
  } else {
    regionEntries.forEach(([name, r], ri) => {
      const seen = new Set([...expected.states].map((s) => s.split(" | ")[ri]));
      for (const s of r.states) if (!seen.has(s)) unreached.push(`${name}: ${s}`);
    });
  }
  return [
    ["states the agreed chart's own steps never reach", unreached.sort()],
    [
      "states only in EXPECTED (no path from the start reaches them in the spec, or the spec renamed them)",
      minus(expected.states, actual.states),
    ],
    ["states only in ACTUAL", minus(actual.states, expected.states)],
    ["start states only in EXPECTED", minus(expected.initial, actual.initial)],
    ["start states only in ACTUAL", minus(actual.initial, expected.initial)],
    [
      "transitions only in EXPECTED (a guard in the spec blocks them, or the spec renamed the step)",
      minus(edgeSet(expected), edgeSet(actual)),
    ],
    ["transitions only in ACTUAL", minus(edgeSet(actual), edgeSet(expected))],
  ].filter(([, xs]) => xs.length > 0);
}

export const STATUS_CLASSES = [
  "classDef works fill:#f4f6f7,stroke:#566573,color:#1b2631",
  "classDef wrong fill:#fdedec,stroke:#c0392b,color:#7b241c",
  "classDef fixed fill:#e9f7ef,stroke:#1e8449,color:#145a32",
  "classDef worksPath fill:#f4f6f7,stroke:#1f3a93,stroke-width:4px,color:#1b2631",
  "classDef wrongPath fill:#fdedec,stroke:#1f3a93,stroke-width:4px,color:#7b241c",
  "classDef fixedPath fill:#e9f7ef,stroke:#1f3a93,stroke-width:4px,color:#145a32",
];

export const GROUP_PALETTE = [
  "#d6eaf8",
  "#fdebd0",
  "#e8daef",
  "#fcf3cf",
  "#d1f2eb",
  "#ede0d4",
  "#f6e0ef",
];
export const PLAIN_FILL = "#f4f6f7";

const rgb = (hex) => {
  const h = hex.length === 4 ? [...hex.slice(1)].map((c) => c + c).join("") : hex.slice(1);
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
};
// WCAG relative luminance: 0 for black, 1 for white.
function luminance(hex) {
  const [r, g, b] = rgb(hex).map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
export function groupColorProblem(color) {
  if (typeof color !== "string" || !/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(color))
    return 'is not "#rgb" or "#rrggbb"';
  if (luminance(color) < 0.5) return "is too dark for the status borders to show on it";
  return null;
}

const BORDERS = {
  Wrong: ["stroke:#c0392b,stroke-width:4px", "#7b241c"],
  Fixed: ["stroke:#1e8449,stroke-width:4px", "#145a32"],
  Path: ["stroke:#1f3a93,stroke-width:4px", "#1b2631"],
};
export function groupClassDef(base, fill, border) {
  const darker = `#${rgb(fill)
    .map((c) =>
      Math.round(c / 2)
        .toString(16)
        .padStart(2, "0"),
    )
    .join("")}`;
  const [stroke, color] = BORDERS[border] ?? [
    `stroke:${fill === PLAIN_FILL ? "#566573" : darker}`,
    "#1b2631",
  ];
  return `classDef ${base}${border} fill:${fill},${stroke},color:${color}`;
}
