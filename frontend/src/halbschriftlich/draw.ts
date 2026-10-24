// The steps of a half-written sum, which pairs fit the rules, and the tasks a block draws.
import { rng } from "../zahlenmauer";
import { acts, sane } from "./props";
import type { HalbschriftlichProps, Made, Rule, Task } from "./props";

const Q = 5;
const D = 4;

export type Solved = { kind: "none" } | { kind: "one" | "many"; values: number[] };

export function steps(op: "+" | "-", a: number, b: number): [number, number, number][] {
  const out: [number, number, number][] = [];
  let s = a;
  for (let p = 3; p >= 0; p--) {
    const d = Math.floor(b / 10 ** p) % 10;
    if (d === 0) continue;
    const part = d * 10 ** p;
    const to = op === "+" ? s + part : s - part;
    out.push([s, part, to]);
    s = to;
  }
  return out;
}

// Does b (already of k digits) fit a under the rules as they act? Plain digit arithmetic.
function fits(op: "+" | "-", max: number, einer: Rule, zehner: Rule, a: number, b: number): boolean {
  if (a < 1 || a > max) return false;
  if (op === "+" ? a + b > max : b > a) return false;
  const cross = (p: number): boolean => {
    const m = 10 ** (p + 1);
    return op === "+" ? (a % m) + (b % m) >= m : a % m < b % m;
  };
  if (einer !== "any" && cross(0) !== (einer === "yes")) return false;
  if (zehner !== "any" && cross(1) !== (zehner === "yes")) return false;
  return true;
}

// For each a, the count of b that fit it, and the list A of the a with at least one. Memo keyed on the settings.
const tableMemo = new Map<string, { A: number[]; n: number[] }>();

function table(p: HalbschriftlichProps): { A: number[]; n: number[] } {
  // Only what decides which (a, b) fit: a stepper or a look change reuses the table.
  const key = JSON.stringify({ op: p.op, max: p.max, ...acts(p) });
  const old = tableMemo.get(key);
  if (old) return old;
  const { k, einer, zehner } = acts(p);
  const A: number[] = [];
  const n: number[] = [];
  for (let a = 1; a <= p.max; a++) {
    let c = 0;
    for (let b = 10 ** (k - 1); b < 10 ** k; b++) if (fits(p.op, p.max, einer, zehner, a, b)) c++;
    n[a] = c;
    if (c > 0) A.push(a);
  }
  const out = { A, n };
  tableMemo.set(key, out);
  if (tableMemo.size > 50) tableMemo.delete(tableMemo.keys().next().value as string);
  return out;
}

// The idx-th b (from 0, rising) that fits a.
function nthFit(p: HalbschriftlichProps, k: number, a: number, idx: number): number {
  const { einer, zehner } = acts(p);
  let left = idx;
  for (let b = 10 ** (k - 1); ; b++) {
    if (fits(p.op, p.max, einer, zehner, a, b) && left-- === 0) return b;
  }
}

export function layout(p: HalbschriftlichProps) {
  const s = sane(p);
  const S = made(s).S;
  const headRows = s.head ? 1 : 0;
  const CG = Q;
  const RG = Q;
  const TW = (3 * D + 2) * Q;
  const TH = (headRows + 1 + S + 1) * Q;
  const across = Math.min(s.columns, s.count);
  const rows = Math.ceil(s.count / s.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = rows * TH + (rows - 1) * RG + 1;
  return { Q, D, S, CG, RG, TW, TH, rows, across, vbW, vbH, headRows };
}

export function heightFor(p: HalbschriftlichProps, w: number): number {
  const l = layout(p);
  return l.vbH * Math.min(w / l.vbW, 1);
}

export function widthFor(p: HalbschriftlichProps): number {
  return layout(p).vbW;
}

// The teacher's own task from its typed positions, by the rule alone (a ≥ 1, b ≥ 1, Plus r = a + b ≤ cap, Minus
// r = a − b ≥ 0, all values 0 to cap), by algebra and counting.
export function solve(op: "+" | "-", known: (number | null)[], drawn: number[] | null, cap = 9999): Solved {
  const plus = op === "+";
  const ok = (v: number[]): boolean => {
    const [a, b, r] = v;
    return a >= 1 && a <= cap && b >= 1 && b <= cap && r >= 0 && r <= cap && r === (plus ? a + b : a - b);
  };
  const typedBy = (v: number[]): boolean => known.every((x, i) => x === null || x === v[i]);
  const typed = [0, 1, 2].filter((i) => known[i] !== null);
  if (typed.length === 0) return { kind: "many", values: drawn && ok(drawn) ? [...drawn] : [1, 1, plus ? 2 : 0] };
  if (typed.length >= 2) {
    const [ka, kb, kr] = known;
    let cand: number[];
    if (ka !== null && kb !== null) cand = [ka, kb, plus ? ka + kb : ka - kb];
    else if (ka !== null && kr !== null) cand = [ka, plus ? kr - ka : ka - kr, kr];
    else cand = [plus ? kr! - kb! : kr! + kb!, kb!, kr!];
    return ok(cand) && typedBy(cand) ? { kind: "one", values: cand } : { kind: "none" };
  }
  // One typed position: the count of the solutions, and the first (smallest a, then smallest b).
  const pos = typed[0];
  const x = known[pos]!;
  let count = 0;
  let first: number[] = [];
  if (pos === 0 && x >= 1 && x <= cap) {
    count = plus ? cap - x : x;
    first = plus ? [x, 1, x + 1] : [x, 1, x - 1];
  } else if (pos === 1 && x >= 1 && x <= cap) {
    count = plus ? cap - x : cap - x + 1;
    first = plus ? [1, x, 1 + x] : [x, x, 0];
  } else if (pos === 2 && x >= 0 && x <= cap) {
    count = plus ? Math.max(0, x - 1) : cap - x;
    first = plus ? [1, x - 1, x] : [x + 1, 1, x];
  }
  if (count === 0) return { kind: "none" };
  if (count === 1) return { kind: "one", values: first };
  return { kind: "many", values: drawn && ok(drawn) && typedBy(drawn) ? [...drawn] : first };
}

const madeMemo = new Map<string, Made>();

export function made(props: HalbschriftlichProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = madeMemo.get(key);
  if (old) return old;
  const { k, einer, zehner } = acts(p);
  const { A, n } = table(p);
  const none = A.length === 0;
  const plus = p.op === "+";
  const next = rng(p.seed);
  const drawn: [number, number][] = [];
  const tasks: Task[] = [];
  for (let i = 0; i < p.count; i++) {
    let a = 0;
    let b = 0;
    if (!none) {
      for (let t = 0; t < 20; t++) {
        a = A[Math.floor(next() * A.length)];
        b = nthFit(p, k, a, Math.floor(next() * n[a]));
        if (!drawn.some(([x, y]) => x === a && y === b)) break;
      }
      drawn.push([a, b]);
    }
    const r = plus ? a + b : a - b;
    const mine = (p.typed ?? []).filter((e) => e[0] === i);
    if (mine.length === 0) {
      tasks.push(
        none
          ? { op: p.op, values: [0, 0, 0], steps: [], given: [false, false, false], wrong: false, many: false, none: true }
          : { op: p.op, values: [a, b, r], steps: steps(p.op, a, b), given: [true, true, false], wrong: false, many: false, none: false },
      );
      continue;
    }
    const known = [0, 1, 2].map((pos) => mine.find((e) => e[1] === pos)?.[2] ?? null);
    const shown = known.map((x) => x !== null);
    const res = solve(p.op, known, none ? null : [a, b, r]);
    if (res.kind === "none") {
      tasks.push({ op: p.op, values: known.map((x) => x ?? 0), steps: [], given: shown, wrong: true, many: false, none: false });
    } else {
      tasks.push({
        op: p.op,
        values: res.values,
        steps: steps(p.op, res.values[0], res.values[1]),
        given: shown,
        wrong: false,
        many: res.kind === "many",
        none: false,
      });
    }
  }
  const S = Math.max(k, ...tasks.map((t) => t.steps.length));
  const out: Made = { tasks, none, D, S };
  madeMemo.set(key, out);
  if (madeMemo.size > 50) madeMemo.delete(madeMemo.keys().next().value as string);
  return out;
}
