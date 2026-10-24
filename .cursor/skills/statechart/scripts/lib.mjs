import fs from "node:fs";
import process from "node:process";

export function findTlc() {
  const { TLA2TOOLS, JAVA } = process.env;
  if (!TLA2TOOLS)
    throw new Error(
      "Cannot find TLC. Download tla2tools.jar from a TLA+ release:\n  https://github.com/tlaplus/tlaplus/releases\nThen set TLA2TOOLS to the path of tla2tools.jar, and JAVA to a java binary (Java 11 or later).",
    );
  if (!fs.existsSync(TLA2TOOLS)) throw new Error(`TLA2TOOLS is ${TLA2TOOLS}, which does not exist.`);
  return { jar: TLA2TOOLS, java: JAVA || "java" };
}

export function parseValue(text) {
  const src = text.trim();
  let i = 0;
  const ws = () => {
    while (i < src.length && /\s/.test(src[i])) i++;
  };
  const peek = (s) => src.startsWith(s, i);
  const eat = (s) => {
    ws();
    if (!peek(s)) throw new Error(`expected ${s} at ${i} in ${src}`);
    i += s.length;
  };
  const list = (close, item) => {
    const out = [];
    ws();
    if (peek(close)) {
      i += close.length;
      return out;
    }
    for (;;) {
      out.push(item());
      ws();
      if (peek(",")) {
        i++;
        continue;
      }
      eat(close);
      return out;
    }
  };
  const value = () => {
    ws();
    if (peek("<<")) {
      i += 2;
      return list(">>", value);
    }
    if (peek("{")) {
      i++;
      return list("}", value);
    }
    if (peek("[")) {
      i++;
      const pairs = list("]", () => {
        ws();
        const m = /^[A-Za-z_][A-Za-z0-9_]*/.exec(src.slice(i));
        if (!m) throw new Error(`bad record field at ${i}`);
        i += m[0].length;
        eat("|->");
        return [m[0], value()];
      });
      return Object.fromEntries(pairs);
    }
    if (peek("(")) {
      i++;
      const fn = {};
      for (;;) {
        const k = value();
        eat(":>");
        fn[typeof k === "string" ? k : JSON.stringify(k)] = value();
        ws();
        if (peek("@@")) {
          i += 2;
          continue;
        }
        eat(")");
        return fn;
      }
    }
    if (peek('"')) {
      i++;
      let s = "";
      while (i < src.length && src[i] !== '"') {
        if (src[i] === "\\") i++;
        s += src[i++];
      }
      i++;
      return s;
    }
    const m = /^-?\d+|^[A-Za-z_][A-Za-z0-9_]*/.exec(src.slice(i));
    if (!m) throw new Error(`bad value at ${i} in ${src}`);
    i += m[0].length;
    if (m[0] === "TRUE") return true;
    if (m[0] === "FALSE") return false;
    return /^-?\d+$/.test(m[0]) ? Number(m[0]) : m[0];
  };
  try {
    const v = value();
    ws();
    return i === src.length ? v : src;
  } catch {
    return src;
  }
}

// One state as TLC prints it: "/\ x = 1" lines, or "x = 1" for one variable.
function parseState(text) {
  const lines = text.split("\n").filter((l) => l.trim() !== "");
  const conjuncts = [];
  for (const line of lines) {
    if (/^\s*\/\\ /.test(line) || conjuncts.length === 0)
      conjuncts.push(line.replace(/^\s*\/\\ /, ""));
    else conjuncts[conjuncts.length - 1] += ` ${line.trim()}`;
  }
  const vars = {};
  for (const c of conjuncts) {
    const eq = c.indexOf(" = ");
    if (eq < 0) continue;
    vars[c.slice(0, eq).trim()] = parseValue(c.slice(eq + 3));
  }
  return vars;
}

export const isRecord = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const canon = (v) =>
  Array.isArray(v)
    ? v.map(canon)
    : isRecord(v)
      ? Object.fromEntries(
          Object.keys(v)
            .sort()
            .map((k) => [k, canon(v[k])]),
        )
      : v;
export const stateKey = (vars) => JSON.stringify(canon(vars));

export function ruleSentences(tla) {
  const out = new Map();
  const lines = tla.split("\n");
  lines.forEach((line, i) => {
    const name = /^([A-Za-z_]\w*)\s*==/.exec(line)?.[1];
    if (!name) return;
    const said = [];
    for (let j = i - 1; j >= 0 && /^\s*\\\*/.test(lines[j]); j--)
      said.unshift(lines[j].replace(/^\s*\\\*\s?/, "").trim());
    const sentence = said.filter(Boolean).join(" ");
    if (sentence) out.set(name, sentence);
  });
  return out;
}

function unescapeDot(s) {
  let out = "";
  for (let i = 0; i < s.length; i++) {
    if (s[i] === "\\" && i + 1 < s.length) {
      const n = s[++i];
      out += n === "n" ? "\n" : n;
    } else out += s[i];
  }
  return out;
}

export function parseDot(text) {
  const nodes = new Map();
  const edges = [];
  const loops = [];
  const seen = new Set();
  const LABEL = '"((?:[^"\\\\]|\\\\.)*)"';
  const nodeRe = new RegExp(`^(-?\\d+) \\[label=${LABEL}(.*)\\];?\\s*$`);
  const edgeRe = new RegExp(`^(-?\\d+) -> (-?\\d+)(?: \\[label=${LABEL})?`);
  for (const line of text.split("\n")) {
    let m = edgeRe.exec(line);
    if (m) {
      const e = { from: m[1], to: m[2], action: m[3] ? unescapeDot(m[3]) : "" };
      const id = `${e.from} ${e.to} ${e.action}`;
      if (seen.has(id)) continue;
      seen.add(id);
      (e.from === e.to ? loops : edges).push(e);
      continue;
    }
    m = nodeRe.exec(line);
    if (m)
      nodes.set(m[1], {
        id: m[1],
        vars: parseState(unescapeDot(m[2])),
        init: /style\s*=\s*filled/.test(m[3]),
      });
  }
  if (nodes.size === 0)
    throw new Error("no states found; dump the graph with TLC -dump dot,actionlabels <file>");
  const missing = [...edges, ...loops].find((e) => !nodes.has(e.from) || !nodes.has(e.to));
  if (missing)
    throw new Error(
      `transition ${missing.from} -> ${missing.to} names a state the file does not define`,
    );
  if (edges.length > 0 && [...edges, ...loops].every((e) => !e.action))
    throw new Error(
      "the graph has no action names; dump it with TLC -dump dot,actionlabels <file>",
    );
  return { nodes, edges, loops };
}

export function parseTraces(text) {
  const traces = [];
  let invariant = null;
  let current = null;
  const lines = text.split("\n");
  const stateAt = (i) => {
    const body = [];
    while (i + 1 < lines.length && lines[i + 1].trim() !== "") body.push(lines[++i]);
    return [parseState(body.join("\n")), i];
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const inv = /^Error: Invariant (\S+) is violated( by the initial state:)?/.exec(line);
    if (inv) {
      invariant = inv[1];
      if (inv[2]) {
        const [vars, end] = stateAt(i);
        traces.push({ invariant, steps: [{ action: null, vars }] });
        i = end;
      }
      continue;
    }
    if (line.startsWith("Error: ") && !line.startsWith("Error: The behavior up to this point is"))
      invariant = null;
    const head = /^State (\d+): <([^\s>(]+)/.exec(line);
    if (!head) continue;
    const [vars, end] = stateAt(i);
    i = end;
    if (head[1] === "1") {
      current = { invariant, steps: [] };
      traces.push(current);
    }
    current?.steps.push({ action: head[2] === "Initial" ? null : head[2], vars });
  }
  return traces;
}

// With -continue, TLC prints "Model checking completed" even after broken invariants, and not
// when it stopped early.
export function checkTlcOutput(text, file) {
  const other = text
    .split("\n")
    .find(
      (l) =>
        l.startsWith("Error: ") &&
        !/^Error: (Invariant \S+ is violated|The behavior up to this point is)/.test(l),
    );
  if (other)
    throw new Error(
      `${file}: TLC stopped on an error that is not a broken rule: ${other.slice(7)}`,
    );
  if (!/^Model checking completed\./m.test(text))
    throw new Error(
      `${file}: TLC did not finish, so its counterexamples are not all there; read the file`,
    );
}

export function wrap(text, width = 26) {
  const words = String(text).split(/\s+/);
  const rows = [];
  let row = "";
  for (const w of words) {
    if (row && (row + " " + w).length > width) {
      rows.push(row);
      row = w;
    } else row = row ? `${row} ${w}` : w;
  }
  if (row) rows.push(row);
  return rows.join("<br/>");
}

const OPENS_A_PHRASE = new Set(
  "a an the your my our their its this that to of in on at for with from by and or".split(" "),
);
export function joinLabels(labels) {
  if (labels.length < 2) return labels.join(" or ");
  const words = labels.map((l) => String(l).split(" "));
  let n = 0;
  while (words.every((w) => n < w.length - 1 && w[n] === words[0][n])) n++;
  while (n > 0 && OPENS_A_PHRASE.has(words[0][n - 1])) n--;
  if (n < 2) return labels.join(" or ");
  const rest = words.map((w) => w.slice(n).join(" "));
  const list =
    rest.length === 2 ? rest.join(" or ") : `${rest.slice(0, -1).join(", ")}, or ${rest.at(-1)}`;
  return `${words[0].slice(0, n).join(" ")} ${list}`;
}

