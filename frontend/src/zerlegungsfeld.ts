// The Zerlegungsfeld generator: Zehnerübergang in zwei Schritten. For 8 + 5 the 5 splits into 2 and 3, so that the
// first step reaches the full ten: 8 + 2 = 10, then 10 + 3 = 13. A pure function of the block's settings and its seed,
// so that the editor, the thumbnail and the PDF draw the same tasks.
//
// The contract of #827, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "zerlegungsfeld", props: ZerlegungsfeldProps }`.
// - `count` tasks (1 to 12, default 6) in `columns` side by side (1 to 3, default 3).
// - `op`, the Rechenart: "+" (Plus, default) or "-" (Minus). The sheet shows "+" or "−" (U+2212).
// - `max`, the Zahlenraum: 20, 100 or 1000 (default 20; any other value gives 20).
// - `step`, the Übergang: "zehner" (default) or "hunderter". "hunderter" counts only with max 1000; with 20 or 100 it
//   acts as "zehner" (and stays stored). The unit u is 10 for "zehner", 100 for "hunderter"; the grain g is 1 for
//   "zehner", 10 for "hunderter" (a drawn Hunderter task has multiples of 10 only, as 370 + 50).
// - `big`, "Zweite Zahl mehrstellig": false (default) draws the second number below u (8 + 5, 370 + 50); true draws it
//   at least u (3 + 34: 3 + 7 = 10, 10 + 27 = 37).
// - `task`, the Aufgabentyp, which boxes a drawn task gives:
//   - "task" (default): the first and the second number.
//   - "split": the first and the second number and the split (both parts).
//   - "result": the first number and the result.
// - `typed`: numbers the teacher typed, each entry [task from 0, position 0 to 5, value 0 to 9999]. The positions: 0 the
//   first number a, 1 the second number b, 2 the result r, 3 the left part of the split b1, 4 the right part b2, 5 the
//   Zwischenergebnis t (the full ten or hundred). An entry that is not three whole numbers, or whose task is not 0 to
//   11, position not 0 to 5 or value not 0 to 9999, is dropped; of two for the same task and position the last one
//   stays. An entry of a task the block does not have (after fewer tasks) stays stored and plays no part.
// - `seed` alone gives the tasks.
//
// The rule every task keeps, drawn or typed (with u from `step` and `max` as above):
// - Plus: a is no multiple of u; t is the next multiple of u above a; b1 = t − a; b2 = b − b1 ≥ 1; r = a + b = t + b2.
// - Minus: a is no multiple of u; t is the multiple of u below a, at least u; b1 = a − t; b2 = b − b1 ≥ 1;
//   r = a − b = t − b2 ≥ 0.
// So the crossing is always required: b2 is at least 1. Every value is a whole number 0 to 9999. `max` and `big` only
// steer the draw; a typed task is checked against the rule alone (u counts, the Zahlenraum and `big` do not).
// A Hunderterübergang inside 20 or 100 cannot exist without passing the Zahlenraum (Plus needs r > 100, Minus a > 100),
// so "hunderter" needs max 1000.
//
// The drawn tasks (`made`, memo of 50, `rng` from zahlenmauer.ts). Per task i, every draw in this order whatever is
// typed, so that the tasks after a typed one stay as they were: up to 20 tries, each one draw for a and then one for b;
// a try whose (a, b) equals an earlier task's drawn (a, b) is dropped, and after 20 tries the last one stays.
// - a: the list A of every multiple of g that has at least one b (below), in rising order; a = A[floor(next() · |A|)].
//   Plus: a from g to max − g; Minus: a from u to max.
// - b: every multiple of g from lo to hi, in rising order, one drawn the same way. Plus: lo = b1 + g, hi = max − a.
//   Minus: lo = b1 + g, hi = a. Not big: hi is at most u − g. Big: lo is at least u.
// - Drawn tasks never pass the Zahlenraum (Plus: r ≤ max; Minus: a ≤ max).
//
// Typed numbers win over the seed. A task with at least one typed entry is the teacher's own: exactly its typed
// positions are given, the drawn ones are not. The panel, at the first number typed into a task, stores that task's
// drawn given positions as typed entries with it, so that nothing the sheet showed goes away. A teacher's own task is
// worked out by `solve` from its typed positions alone, exactly, with no search budget: a fixes t and b1; b, b2 or r
// fix b; so `solve` walks every a from 1 to the cap and, for each, takes b from a typed b, b2 or r (all that are typed
// must agree), or, with none of them typed, counts the free b. No solution: `wrong`. One: the task's values. Two or
// more: `many`, the values shown are the drawn task's when it fits, else the solution of the smallest a and then the
// smallest b; the key says "Auch andere Lösungen sind richtig." and the panel "Es gibt mehr als eine Lösung.".
// Typed numbers outside the Zahlenraum count. A wrong task shows its typed numbers on the pupils' sheet; the other
// boxes stay empty, also in the key: never a false number.
//
// The drawing (sheet.tsx `Zerlegungsfeld`, on screen, print and in the key alike): `div.zerlegungsfeld` holds one svg.
// Each task `g.task[data-task=i]` (class `wrong`, class `many`) has four lines of boxes. A box is
// `g.box[data-pos=p][data-line=l]`: a white rect with stroke #222 of 0.4 and, when its position shows, a text: class
// `given` in #222, in the key an empty position class `answer` in #c0392b. Lines (l) and their boxes, left to right:
// 0 the task a, b, r; 1 the split b1, b2; 2 the first step a, b1, t; 3 the second step t, b2, r. Lines 0, 2 and 3 have
// `text.op` ("+" or "−") between the first two boxes and `text.eq` ("=") between the last two. Two `line.branch`
// (stroke #222, 0.4) go from the bottom middle of line 0's b box to the top middle of b1 and of b2. In the key a task
// with `many` and not wrong has `text.note` "Auch andere Lösungen sind richtig." below it.
//
// Units: a box is BW = 12 wide and BH = 8 high; an op or "=" column is OW = 5 wide, so a line is TW = 3 · BW + 2 · OW
// = 46 wide; boxes of lines 0, 2 and 3 sit at x 0, 17 and 34. Line 0 at y 0, line 1 at y 14 (b1 at x 9, b2 at x 25),
// line 2 at y 26, line 3 at y 38; below it NOTE_H = 6 always (room for the key's note, so that the key and the sheet
// have the same height): a task is TH = 52 high. Tasks side by side CG = 8 apart, rows of tasks RG = 6 apart. A
// number of more than 2 digits draws smaller to fit the box's width (`numberSize` in sheet.tsx, of BW · 0.85).
//
// The panel (pages/Zerlegungsfeld.tsx), whose words the tests take as selectors: steppers "Eine Aufgabe weniger" /
// "Eine Aufgabe mehr" ("6 Aufgaben", "1 Aufgabe"), "Weniger Aufgaben nebeneinander" / "Mehr Aufgaben nebeneinander"
// ("3 nebeneinander"); select "Rechenart" ("Plus", "Minus"; a change drops `typed` in the same undo step); select
// "Zahlenraum" ("bis 20", "bis 100", "bis 1000"; a change that changes u, so from or to bis 1000 with "hunderter"
// stored, drops `typed` in the same undo step); with bis 1000 select "Übergang" ("Zehner", "Hunderter"; a change
// drops `typed` in the same undo step); checkbox "Zweite Zahl mehrstellig"; select "Aufgabentyp" ("Nur die Aufgabe",
// "Aufgabe und Zerlegung", "Erste Zahl und Ergebnis"); select "Aufgabe für eigene Zahlen" (with 2 or more tasks,
// "Aufgabe 1" ...); number fields "Erste Zahl", "Zweite Zahl", "Ergebnis", "Zerlegung links", "Zerlegung rechts",
// "Zwischenergebnis" showing the given numbers (typed or drawn), the other fields empty; each field is one undo step
// (key `typed:i:p`). Hints (p.hint, role=status): per wrong task "Aufgabe i: Die Zahlen passen nicht zusammen."; per
// task with many and not wrong "Aufgabe i: Es gibt mehr als eine Lösung." Buttons "Eigene Zahlen entfernen" (with
// typed), "Neu würfeln" (changes only the seed).

import { rng } from "./zahlenmauer";

/** A number the teacher typed: the task's index (from 0), the position (0 to 5), the value (0 to 9999). */
export type ZerlegungsfeldTyped = [number, number, number];
export type ZerlegungsfeldProps = {
  /** Number of tasks on the sheet, side by side in rows of `columns`. Default 6.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of tasks per row. Default 3.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** The Rechenart: "+" (Plus: 8 + 5 = 8 + 2 + 3) or "-" (Minus: 13 − 5 = 13 − 3 − 2). Default "+". */
  op: "+" | "-";
  /** The Zahlenraum, 20, 100 or 1000: the result of a Plus task and the first number of a Minus task are at most max. Default 20. */
  max: number;
  /** The Übergang: "zehner" (the first step reaches the full ten) or "hunderter" (the full hundred, with multiples of 10 such as 370 + 50; only with max 1000, else it acts as "zehner"). Default "zehner". */
  step: "zehner" | "hunderter";
  /** Expert option: false draws a second number below the ten (or hundred) as in 8 + 5; true draws one of at least the ten (or hundred) as in 3 + 34 = 3 + 7 + 27. Default false. */
  big: boolean;
  /** The Aufgabentyp, which boxes are given: "task" the first and the second number; "split" also the two parts of the split; "result" the first number and the result. The pupil fills the other boxes. Every drawn task has one solution. Default "task". */
  task: "task" | "split" | "result";
  /** Seed for the random tasks. The same seed always gives the same tasks. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [task index from 0, position 0 to 5, value 0 to 9999]. Positions: 0 the first number, 1 the second number, 2 the result, 3 the left part of the split (to the full ten, with "hunderter" the full hundred), 4 the right part, 5 the Zwischenergebnis (that full ten or hundred). A task with typed numbers shows exactly its typed boxes; the others are worked out from them. A task whose typed numbers do not fit is marked wrong and its key shows no answers. */
  typed?: ZerlegungsfeldTyped[];
};

// A task: its six values at the positions of the contract (0 where unknown), which positions show on the pupils' sheet,
// and whether its typed numbers do not fit or allow more than one solution.
export type Task = {
  op: "+" | "-";
  values: number[];
  given: boolean[];
  wrong: boolean;
  many: boolean;
};
export type Made = { tasks: Task[] };

export const DEFAULTS: Omit<ZerlegungsfeldProps, "seed"> = {
  count: 6,
  columns: 3,
  op: "+",
  max: 20,
  step: "zehner",
  big: false,
  task: "task",
};
export const MAXES = [20, 100, 1000];
// The panel's words for the six positions, in position order.
export const NAMES = ["Erste Zahl", "Zweite Zahl", "Ergebnis", "Zerlegung links", "Zerlegung rechts", "Zwischenergebnis"];

// The exports the drawing, the panel and the insert use; the generator fills them in:
// - `sane(p: ZerlegungsfeldProps): ZerlegungsfeldProps`: the sane settings (a wrong value gives its default, as the
//   contract says; `typed` only when it has entries; `step` stays as stored).
// - `unit(p: ZerlegungsfeldProps): 10 | 100`: u of the contract (100 only for "hunderter" with max 1000).
// - `layout(p: Pick<ZerlegungsfeldProps, "count" | "columns">)`: { BW, BH, OW, NOTE_H, CG, RG, TW, TH, lines, vbW, vbH },
//   TW and TH one task's slot with its note line, vbW and vbH the viewBox (+1 each, as malquadrat.ts).
// - `heightFor(p: ZerlegungsfeldProps, w: number): number`: the height in mm at width w, at the default scale at most
//   (S0 = 180 / layout(DEFAULTS).vbW, as malquadrat.ts).
// - `opLabel(op: "+" | "-"): string`: "+" or "−".
// - `solve(op, u, known: (number | null)[], drawn: number[] | null, cap = 9999): { kind: "none" } | { kind: "one" |
//   "many"; values: number[] }`: a teacher's own task from its typed positions (known[p], null where not typed), as
//   the contract says; every value of a solution is 0 to cap.
// - `made(p: ZerlegungsfeldProps): Made`.

export function sane(p: ZerlegungsfeldProps): ZerlegungsfeldProps {
  const count = Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : DEFAULTS.count;
  const columns = Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 3 ? p.columns : DEFAULTS.columns;
  const op = p.op === "+" || p.op === "-" ? p.op : DEFAULTS.op;
  const max = MAXES.includes(p.max) ? p.max : DEFAULTS.max;
  const step = p.step === "zehner" || p.step === "hunderter" ? p.step : DEFAULTS.step;
  const big = p.big === true;
  const task = p.task === "split" || p.task === "result" ? p.task : DEFAULTS.task;
  const seed = Number.isFinite(p.seed) ? p.seed : 0;
  const typed = new Map<string, ZerlegungsfeldTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [i, pos, v] = t;
      if (i < 0 || i > 11 || pos < 0 || pos > 5 || v < 0 || v > 9999) continue;
      typed.delete(`${i}:${pos}`);
      typed.set(`${i}:${pos}`, [i, pos, v]);
    }
  }
  const kept = [...typed.values()];
  return { count, columns, op, max, step, big, task, seed, ...(kept.length ? { typed: kept } : {}) };
}

export function unit(p: ZerlegungsfeldProps): 10 | 100 {
  const q = sane(p);
  return q.step === "hunderter" && q.max === 1000 ? 100 : 10;
}

export function opLabel(op: "+" | "-"): string {
  return op === "-" ? "−" : "+";
}

export function layout(p: Pick<ZerlegungsfeldProps, "count" | "columns">) {
  const [BW, BH, OW, NOTE_H, CG, RG] = [12, 8, 5, 6, 8, 6];
  const TW = 3 * BW + 2 * OW;
  // Four lines, the last one 8 high at y 38, then the note.
  const TH = 38 + BH + NOTE_H;
  const across = Math.min(p.columns, p.count);
  const lines = Math.ceil(p.count / p.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = lines * TH + (lines - 1) * RG + 1;
  return { BW, BH, OW, NOTE_H, CG, RG, TW, TH, lines, vbW, vbH };
}

// The default block is drawn at 180 mm wide at this scale; a narrower block scales down, a wider one stays at it.
const S0 = 180 / layout(DEFAULTS).vbW;

export function heightFor(p: ZerlegungsfeldProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// The six values of a task [a, b, r, b1, b2, t] from a and b.
function full(op: "+" | "-", u: number, a: number, b: number): number[] {
  const t = op === "+" ? (Math.floor(a / u) + 1) * u : Math.floor(a / u) * u;
  const b1 = op === "+" ? t - a : a - t;
  return [a, b, op === "+" ? a + b : a - b, b1, b - b1, t];
}

// The contract's rule on six values, every value 0 to cap.
function holds(v: number[], op: "+" | "-", u: number, cap: number): boolean {
  const [a, b, r, b1, b2, t] = v;
  if (a % u === 0 || b2 !== b - b1 || b2 < 1) return false;
  const want = full(op, u, a, b);
  if (op === "-" && t < u) return false;
  return want.every((x, i) => x === v[i]) && v.every((x) => x >= 0 && x <= cap) && r >= 0;
}

export function solve(
  op: "+" | "-",
  u: number,
  known: (number | null)[],
  drawn: number[] | null,
  cap = 9999,
): { kind: "none" } | { kind: "one" | "many"; values: number[] } {
  const same = (k: number | null, v: number) => k === null || k === v;
  let count = 0;
  let first: number[] | null = null;
  for (let a = 1; a <= cap && count < 2; a++) {
    if (a % u === 0) continue;
    const t = op === "+" ? (Math.floor(a / u) + 1) * u : Math.floor(a / u) * u;
    if (t > cap || (op === "-" && t < u)) continue;
    const b1 = op === "+" ? t - a : a - t;
    if (!same(known[0], a) || !same(known[3], b1) || !same(known[5], t)) continue;
    const fixed = new Set<number>();
    if (known[1] !== null) fixed.add(known[1]);
    if (known[4] !== null) fixed.add(b1 + known[4]);
    if (known[2] !== null) fixed.add(op === "+" ? known[2] - a : a - known[2]);
    if (fixed.size > 1) continue;
    if (fixed.size === 1) {
      const v = full(op, u, a, [...fixed][0]);
      if (holds(v, op, u, cap)) {
        count++;
        if (!first) first = v;
      }
      continue;
    }
    // b is free: every b from b1 + 1 up to the Zahlenraum is a solution.
    const hi = op === "+" ? cap - a : a;
    if (hi > b1) {
      count += hi - b1;
      if (!first) first = full(op, u, a, b1 + 1);
    }
  }
  if (count === 0) return { kind: "none" };
  const kind = count === 1 ? "one" : "many";
  const fits = !!drawn && holds(drawn, op, u, cap) && drawn.every((x, i) => same(known[i] ?? null, x));
  return { kind, values: fits && drawn ? [...drawn] : first! };
}

// The drawn tasks: `A` and `b` ranges per a, 20 tries against duplicates (see the contract).
const memo = new Map<string, Made>();

export function made(props: ZerlegungsfeldProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const u = unit(p);
  const g = u === 100 ? 10 : 1;
  const bRange = (a: number): [number, number] | null => {
    const v = full(p.op, u, a, 0);
    let lo = v[3] + g;
    let hi = p.op === "+" ? p.max - a : a;
    if (!p.big) hi = Math.min(hi, u - g);
    else lo = Math.max(lo, u);
    return lo <= hi ? [lo, hi] : null;
  };
  const A: number[] = [];
  for (let a = g; a <= p.max; a += g) {
    if (a % u === 0 || (p.op === "-" && a < u)) continue;
    if (bRange(a)) A.push(a);
  }
  const next = rng(p.seed);
  const drawn: [number, number][] = [];
  const tasks: Task[] = [];
  const given = (task: ZerlegungsfeldProps["task"]) => [0, 1, 2, 3, 4, 5].map((pos) => {
    if (task === "split") return pos !== 2 && pos !== 5;
    if (task === "result") return pos === 0 || pos === 2;
    return pos === 0 || pos === 1;
  });
  for (let i = 0; i < p.count; i++) {
    let a = 0;
    let b = 0;
    for (let k = 0; k < 20; k++) {
      a = A[Math.floor(next() * A.length)];
      const [lo, hi] = bRange(a)!;
      b = lo + g * Math.floor(next() * ((hi - lo) / g + 1));
      if (!drawn.some(([x, y]) => x === a && y === b)) break;
    }
    drawn.push([a, b]);
    const values = full(p.op, u, a, b);
    const mine = (p.typed ?? []).filter((e) => e[0] === i);
    if (mine.length === 0) {
      tasks.push({ op: p.op, values, given: given(p.task), wrong: false, many: false });
      continue;
    }
    const known = [0, 1, 2, 3, 4, 5].map((pos) => mine.find((e) => e[1] === pos)?.[2] ?? null);
    const res = solve(p.op, u, known, values);
    const shown = known.map((k) => k !== null);
    if (res.kind === "none") {
      tasks.push({ op: p.op, values: known.map((k) => k ?? 0), given: shown, wrong: true, many: false });
    } else {
      tasks.push({ op: p.op, values: res.values, given: shown, wrong: false, many: res.kind === "many" });
    }
  }
  const out: Made = { tasks };
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}
