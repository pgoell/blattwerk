// The Halbschriftlich generator: semi-written addition and subtraction. The second number is added (or taken away)
// place by place, the highest place first: 345 + 123 is 345 + 100 = 445, 445 + 20 = 465, 465 + 3 = 468. A pure
// function of the block's settings and its seed, so that the editor, the thumbnail and the PDF draw the same tasks.
//
// The contract of #828, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "halbschriftlich", props: HalbschriftlichProps }`.
// - `count` tasks (1 to 12, default 6) in `columns` side by side (1 to 3, default 2).
// - `op`, the Rechenart: "+" (Plus, default) or "-" (Minus). The sheet shows "+" or "−" (U+2212).
// - `max`, the Zahlenraum of the first number and the result: 100 or 1000 (default 1000; any other value gives 1000).
// - `digits`, the places of the second number: 1, 2 or 3 (default 3; any other value gives the default). A drawn second
//   number has exactly that many digits (2: 10 to 99). 3 counts only with max 1000; with max 100 it acts as 2 (and
//   stays stored).
// - `einer`, the Übergang in the Einer step: "any" (default), "yes" or "no". `zehner`, the Übergang in the Zehner
//   step: the same values. `zehner` counts only with max 1000 and digits (as it acts) 2 or 3; else it acts as "any"
//   (and stays stored). Any other value gives "any".
// - `grid`, Karo: true (default) draws the 5 mm squares behind the tasks; false draws plain white with a box per number.
// - `head`, Stellenwerte: false (default); true draws a row of place letters (T H Z E) above each task's numbers.
// - `tint`: false (default); true tints the second number and its parts in the steps.
// - `ops`: true (default) prints the step lines' signs ("+" or "−" and "=") on the pupils' sheet; false leaves them out
//   there, so the pupils write them (the slots stay). The key always shows the full steps.
// - `typed`: numbers the teacher typed, each entry [task from 0, position 0 to 2, value 0 to 9999]. The positions: 0 the
//   first number a, 1 the second number b, 2 the result r. An entry that is not three whole numbers, or whose task is
//   not 0 to 11, position not 0 to 2 or value not 0 to 9999, is dropped; of two for the same task and position the last
//   one stays. An entry of a task the block does not have (after fewer tasks) stays stored and plays no part.
// - `seed` alone gives the drawn tasks.
//
// The steps of a task (a, b): one step per digit of b that is not 0, the highest place first. The part of a step is
// that digit times its place value (b = 305 gives the parts 300 and 5). Step j goes from s(j) to s(j + 1), with s(0) = a,
// s(j + 1) = s(j) + part j for Plus and s(j) − part j for Minus; the last s is r. So 345 + 103 has two steps.
//
// The rule every task keeps, drawn or typed: a ≥ 1, b ≥ 1; Plus r = a + b ≤ 9999; Minus r = a − b ≥ 0.
// The Übergang of the step at place p (p = 0 the Einer, 1 the Zehner), where a_p and b_p are the digits of a and b at p:
// Plus: the step crosses a multiple of 10^(p+1) exactly when a_p + b_p ≥ 10; Minus: exactly when a_p < b_p (the higher
// places of b are already added or taken away, and they do not change digit p). "yes" needs that, "no" forbids it. A
// place where b's digit is 0 has no step, so it has no Übergang: "yes" there cannot hold, "no" always holds.
//
// The drawn tasks (`made`, memo of 50, `rng` from zahlenmauer.ts). The drawn task keeps, besides the rule: a ≤ max,
// b has exactly k digits (k = `digits` as it acts), Plus r ≤ max, and the `einer` and `zehner` rules as they act.
// For each a from 1 to max let n(a) be the count of b that fit with a. A is the list of a with n(a) ≥ 1, in rising order.
// The lists are computed exactly (a plain walk of every a and every b of k digits), never by trying random tasks, so a
// drawn task never breaks a rule. If A is empty, no task fits the settings: `none` is true, no draws are made, every
// task not the teacher's own is empty (no given number, no answer, also in the key).
// Per task i, every draw in this order whatever is typed, so that the tasks after a typed one stay as they were: up to
// 20 tries, each one draw a = A[floor(next() · |A|)] and then one draw for b, the floor(next() · n(a))-th b (from 0)
// that fits with a in rising order; a try whose (a, b) equals an earlier task's drawn (a, b) is dropped, and after 20
// tries the last one stays (a repeated task keeps every rule).
// A drawn task gives a and b; the pupil writes r and the steps.
//
// Typed numbers win over the seed. A task with at least one typed entry is the teacher's own: exactly its typed
// positions are given, the drawn ones are not. The panel, at the first number typed into a task, stores that task's
// drawn given positions (a and b) as typed entries with it, so that nothing the sheet showed goes away (not when `none`).
// A teacher's own task is worked out by `solve` from its typed positions alone against the rule alone (`max`, `digits`,
// `einer` and `zehner` only steer the draw), exactly, by counting with no search budget: any two of a, b, r fix the
// task (one solution or none); one alone gives a count (a typed: Plus b from 1 to cap − a, Minus b from 1 to a; b
// typed: Plus a from 1 to cap − b, Minus a from b to cap; r typed: Plus a from 1 to r − 1, Minus a from r + 1 to cap),
// which can be 0, 1 (Minus a = 1, Plus r = 2) or more. No solution: `wrong`. One: the task's values and steps. Two or more: `many`, the values shown are the drawn task's
// when it fits the typed numbers, else the solution of the smallest a and then the smallest b; the key says "Auch andere
// Lösungen sind richtig." and the panel "Es gibt mehr als eine Lösung.". A wrong task shows its typed numbers on the
// pupils' sheet; the other boxes stay empty, also in the key: never a false number.
//
// Layout, in squares of Q = 5 units (1 unit = 1 mm at the default scale, so Karo is 5 mm): a number column is D = 4
// squares wide always (every value is 0 to 9999, so the width never changes with the numbers). A task line is the columns [number D][sign 1][number D][= 1][number D]: TW = (3 · D + 2) · Q wide. A digit sits in its
// own square, the number right-aligned in its column. S = the most steps of any task, at least k. A task's rows top
// down: with `head` one row of place letters, then the task line (row of line 0), then S step lines (line j + 1 is step
// j), then one note row (room for the key's note, so the key and the sheet have the same height): TH = (head ? 1 : 0)
// + 1 + S + 1 squares. Tasks side by side CG = Q apart, rows of tasks RG = Q apart; vbW = across · TW + (across − 1) ·
// CG + 1, vbH = rows · TH + (rows − 1) · RG + 1 (+1 for the stroke; the drawing sits at 0.5, 0.5).
// The default block is drawn at scale 1 (Karo 5 mm), inserted at its vbW wide; a narrower block scales down, a wider
// one stays at scale 1.
//
// The drawing (sheet.tsx `Halbschriftlich`, on screen, print and in the key alike): `div.halbschriftlich` holds one svg.
// With `grid`, `g.karo` draws the square lines over the whole viewBox (stroke #9fb4c8, 0.15). Each task
// `g.task[data-task=i]` (class `wrong`, class `many`, class `none` for an empty drawn task when `none`). A number slot is
// `g.slot[data-line=l][data-pos=p]` (line 0 the task: p 0 a, 1 b, 2 r; line j + 1 step j: p 0 s(j), 1 part j, 2 s(j+1)):
// without `grid` a white rect with stroke #222 of 0.3 around its D squares; with `tint` the slots of p 1 have a
// `rect.tint` fill #dbeafe under the digits; the digits as one `text` per slot (class `given` in #222, in the key an
// empty position class `answer` in #c0392b), letter-spaced so that each digit sits in its square, size Q · 0.75.
// Every drawn line has `text.op` ("+" or "−") in its sign square and `text.eq` ("=") in its = square.
// Line 0 always draws with its signs. Step lines on the pupils' sheet: the task's own steps (S lines for a wrong task or
// an empty one), each with its empty slots, and with `ops` also its `text.op` and `text.eq`; `ops` changes only the
// signs. In the key: the task's own steps with their signs and every number as `answer`; a wrong or empty task's key
// is its pupils' sheet. With `none` the sheet shows no words for it: the empty tasks stay blank, the panel says why. With `head`
// `text.head` letters ("E", "Z", "H", "T" from the right) in #555, size Q · 0.6, over each of the three number columns.
// In the key a task with `many` and not wrong has `text.note` "Auch andere Lösungen sind richtig." in its note row.
//
// The panel (pages/Halbschriftlich.tsx), whose words the tests take as selectors: steppers "Eine Aufgabe weniger" /
// "Eine Aufgabe mehr" ("6 Aufgaben", "1 Aufgabe"), "Weniger Aufgaben nebeneinander" / "Mehr Aufgaben nebeneinander"
// ("2 nebeneinander"); select "Rechenart" ("Plus", "Minus"; a change drops `typed` in the same undo step); select
// "Zahlenraum" ("bis 100", "bis 1000"); select "Stellen der zweiten Zahl" ("einstellig", "zweistellig", with bis 1000
// also "dreistellig"; it shows k as it acts, so a stored 3 with bis 100 reads "zweistellig"; a choice stores its number); select "Übergang bei den Einern" ("egal", "mit Übergang", "ohne Übergang"); with bis 1000 and
// zweistellig or dreistellig select "Übergang bei den Zehnern" (the same words); checkboxes "Karo", "Stellenwerte
// zeigen", "Zweite Zahl färben", "Rechenzeichen der Schritte drucken"; select "Aufgabe für eigene Zahlen" (with 2 or
// more tasks, "Aufgabe 1" ...); number fields "Erste Zahl", "Zweite Zahl", "Ergebnis" showing the given numbers (typed or
// drawn), the other fields empty; each field is one undo step (key `typed:i:p`). Hints (p.hint, role=status): with
// `none` "Mit diesen Einstellungen gibt es keine Aufgabe."; per wrong task "Aufgabe i: Die Zahlen passen nicht
// zusammen."; per task with many and not wrong "Aufgabe i: Es gibt mehr als eine Lösung." Buttons "Eigene Zahlen
// entfernen" (with typed), "Neu würfeln" (changes only the seed). Every setting is one undo step.

import { rng } from "./zahlenmauer";

/** A number the teacher typed: the task's index (from 0), the position (0 to 2), the value (0 to 9999). */
export type HalbschriftlichTyped = [number, number, number];
export type Rule = "any" | "yes" | "no";
export type HalbschriftlichProps = {
  /** Number of tasks on the sheet, side by side in rows of `columns`. Default 6.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of tasks per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** The Rechenart: "+" (Plus: 345 + 123 = 345 + 100 + 20 + 3) or "-" (Minus: 468 − 123 = 468 − 100 − 20 − 3). Default "+". */
  op: "+" | "-";
  /** The Zahlenraum of the first number and the result, 100 or 1000: the first number, and the result of a Plus task, are at most max. Default 1000. */
  max: number;
  /** The places of the second number: 1, 2 or 3 digits (3 only with max 1000, else it acts as 2). One step per digit that is not 0. Default 3. */
  digits: number;
  /** The Übergang in the Einer step: "yes" every task crosses a ten there (Plus: the Einer of both numbers add up to 10 or more; Minus: the first number's Einer is smaller than the second's), "no" none does, "any" either. Default "any". */
  einer: Rule;
  /** The Übergang in the Zehner step, crossing a hundred there (Plus: the Zehner of both numbers add up to 10 or more; Minus: the first number's Zehner is smaller than the second's): "yes", "no" or "any". Counts only with max 1000 and a second number of 2 or 3 digits. Default "any". */
  zehner: Rule;
  /** Karo: true draws 5 mm squares behind the tasks, one digit to a square; false draws plain white with a box per number. Default true. */
  grid: boolean;
  /** Stellenwerte: true draws the place letters T H Z E above each task's numbers. Default false. */
  head: boolean;
  /** true tints the second number and its parts in the steps. Default false. */
  tint: boolean;
  /** true prints the signs (+ or − and =) of the step lines on the pupils' sheet; false leaves the signs out for the pupils to write (the number boxes stay). The key always shows the full steps. Default true. */
  ops: boolean;
  /** Seed for the random tasks. The same seed always gives the same tasks. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [task index from 0, position 0 to 2, value 0 to 9999]. Positions: 0 the first number, 1 the second number, 2 the result. Any two fix the task and its steps. A task with typed numbers shows exactly its typed boxes; the others are worked out from them. A task whose typed numbers do not fit is marked wrong and its key shows no answers. */
  typed?: HalbschriftlichTyped[];
};

// A task: [a, b, r] (0 where unknown), its steps as [from, part, to], which of a, b, r show on the pupils' sheet,
// whether its typed numbers do not fit or allow more than one solution, and whether it is an empty drawn task (`none`).
export type Task = {
  op: "+" | "-";
  values: number[];
  steps: [number, number, number][];
  given: boolean[];
  wrong: boolean;
  many: boolean;
  none: boolean;
};
export type Made = { tasks: Task[]; none: boolean; D: number; S: number };

export const DEFAULTS: Omit<HalbschriftlichProps, "seed"> = {
  count: 6,
  columns: 2,
  op: "+",
  max: 1000,
  digits: 3,
  einer: "any",
  zehner: "any",
  grid: true,
  head: false,
  tint: false,
  ops: true,
};
export const MAXES = [100, 1000];
// The panel's words for the three positions, in position order.
export const NAMES = ["Erste Zahl", "Zweite Zahl", "Ergebnis"];

// The exports the drawing, the panel and the insert use; the generator fills them in:
// - `sane(p: HalbschriftlichProps): HalbschriftlichProps`: the sane settings (a wrong value gives its default, as the
//   contract says; `typed` only when it has entries; `digits` and `zehner` stay as stored).
// - `acts(p: HalbschriftlichProps): { k: number; einer: Rule; zehner: Rule }`: digits and rules as they act.
// - `steps(op, a, b): [number, number, number][]`: the steps of the contract.
// - `layout(p: HalbschriftlichProps)`: { Q, D, S, CG, RG, TW, TH, rows, across, vbW, vbH, headRows } as the contract says
//   (D is 4; it calls `made` for S).
// - `heightFor(p: HalbschriftlichProps, w: number): number`: the height in mm at width w, vbH · min(w / vbW, 1).
// - `widthFor(p: HalbschriftlichProps): number`: vbW, the width the insert gives a new block.
// - `opLabel(op: "+" | "-"): string`: "+" or "−".
// - `solve(op, known: (number | null)[], drawn: number[] | null, cap = 9999): { kind: "none" } | { kind: "one" |
//   "many"; values: number[] }`: a teacher's own task from its typed positions (known[p], null where not typed), as the
//   contract says; a, b and r of a solution are 0 to cap (a ≥ 1, b ≥ 1). Exact, by algebra and counting, no search
//   budget.
// - `made(p: HalbschriftlichProps): Made`.

const Q = 5;
const D = 4;

export type Solved = { kind: "none" } | { kind: "one" | "many"; values: number[] };

const pick = <T>(v: unknown, ok: readonly T[], dflt: T): T => (ok.includes(v as T) ? (v as T) : dflt);

export function sane(p: HalbschriftlichProps): HalbschriftlichProps {
  const typed = new Map<string, HalbschriftlichTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [i, pos, v] = t;
      if (i < 0 || i > 11 || pos < 0 || pos > 2 || v < 0 || v > 9999) continue;
      typed.delete(`${i}:${pos}`);
      typed.set(`${i}:${pos}`, [i, pos, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count: Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : DEFAULTS.count,
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 3 ? p.columns : DEFAULTS.columns,
    op: p.op === "+" || p.op === "-" ? p.op : DEFAULTS.op,
    max: MAXES.includes(p.max) ? p.max : DEFAULTS.max,
    digits: p.digits === 1 || p.digits === 2 || p.digits === 3 ? p.digits : DEFAULTS.digits,
    einer: pick<Rule>(p.einer, ["any", "yes", "no"], DEFAULTS.einer),
    zehner: pick<Rule>(p.zehner, ["any", "yes", "no"], DEFAULTS.zehner),
    grid: typeof p.grid === "boolean" ? p.grid : DEFAULTS.grid,
    head: typeof p.head === "boolean" ? p.head : DEFAULTS.head,
    tint: typeof p.tint === "boolean" ? p.tint : DEFAULTS.tint,
    ops: typeof p.ops === "boolean" ? p.ops : DEFAULTS.ops,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

export function acts(p: HalbschriftlichProps): { k: number; einer: Rule; zehner: Rule } {
  const s = sane(p);
  const k = s.max === 100 && s.digits === 3 ? 2 : s.digits;
  return { k, einer: s.einer, zehner: s.max === 1000 && k >= 2 ? s.zehner : "any" };
}

export function opLabel(op: "+" | "-"): string {
  return op === "-" ? "−" : "+";
}

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
    const ap = Math.floor(a / 10 ** p) % 10;
    const bp = Math.floor(b / 10 ** p) % 10;
    return op === "+" ? ap + bp >= 10 : ap < bp;
  };
  if (einer !== "any" && cross(0) !== (einer === "yes")) return false;
  if (zehner !== "any" && cross(1) !== (zehner === "yes")) return false;
  return true;
}

// For each a, the count of b that fit it, and the list A of the a with at least one. Memo keyed on the settings.
const tableMemo = new Map<string, { A: number[]; n: number[] }>();

function table(p: HalbschriftlichProps): { A: number[]; n: number[] } {
  const key = JSON.stringify({ ...p, seed: 0, typed: undefined });
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
