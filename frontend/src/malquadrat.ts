// The Malquadrat generator: Einmaleins-Rätsel with the factors at the edges, the products in the middle, the sum of each
// row and each column outside, and one total that checks everything. A pure function of the block's settings and its
// seed, so that the editor, the thumbnail and the PDF draw the same squares.
//
// The contract of #826, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "malquadrat", props: MalquadratProps }`.
// - `count` Malquadrate (1 to 4, default 2) in `columns` side by side (1 to 3, default 2).
// - `size`: the square has size × size inner cells, 2 to 4 (default 3). A value outside gives the nearest end, a value
//   that is not a whole number the default.
// - `op`, the Rechenart: "*" (Mal, default) or "+" (Plus, the addition version). The corner shows "·" or "+". Inner
//   cell (i, j) is row number i op column number j.
// - Mal: `reihen`, the Einmaleins-Reihen, distinct whole numbers 1 to 10 (default [2, 3, 4, 5, 6, 7, 8, 9]; entries
//   outside or twice are dropped, an empty list gives the default). The column numbers are drawn from the Reihen: a
//   drawn order of the list, and a list shorter than size starts again in a new drawn order, so numbers repeat only
//   then. The row numbers are drawn from 2 to 10, distinct.
// - Plus: `max`, the Zahlenraum, 20, 100 or 1000 (default 20; any other value gives 20): every row and column number
//   from 1 to max / 2, distinct per side, so that every inner cell is at most max. The sums may go beyond max.
// - `task`, the Aufgabentyp:
//   - "factors" (default): every row and column number is given; the inner cells, the sums and the total are to fill.
//   - "mixed": h = floor(size / 2) row numbers and h column numbers are hidden (the first h of a drawn order of the rows
//     and of the columns). Per hidden row number one inner cell of that row in a shown column is given, per hidden
//     column number one inner cell of that column in a shown row (each drawn). One solution.
//   - "knobel": as "mixed", but the first hidden row (in the drawn order) has no given inner cell; its row sum is given
//     instead. That row number can be found only through the sum (Mal: row sum : the sum of the column numbers; Plus:
//     (row sum − the sum of the column numbers) : size). One solution.
//   The sums and the total are to fill in all three, save that one row sum.
// - `typed`: numbers the teacher typed, each entry [square from 0, row 0 to 5, column 0 to 5, value 0 to 9999]. With
//   n = size, the positions are: row 0 column j (1 to n) column number j; row i (1 to n) column 0 row number i; row i
//   column j the inner cell (i, j); row i column n + 1 the row sum i; row n + 1 column j the column sum j; row n + 1
//   column n + 1 the total. [s, 0, 0], [s, 0, n + 1] and [s, n + 1, 0] are no position. An entry that is not four whole
//   numbers, or whose square is not 0 to 3, row or column not 0 to 5, or value not 0 to 9999, is dropped; of two for
//   the same cell the last one stays. An entry of a square the block does not have (after fewer squares), or at no
//   position of the square's size, stays stored and plays no part.
// - `seed` alone gives the squares.
//
// Typed numbers win over the seed. A square with at least one typed entry at a position is the teacher's own: exactly
// its typed cells are given, the drawn ones are not. The panel, at the first number typed into a square, stores that
// square's drawn given cells as typed entries with it, so that nothing the sheet showed goes away. The numbers of a
// teacher's own square are worked out by `solve` from its typed cells alone:
// - The unknowns are the 2n row and column numbers. Each typed cell is an equation: a typed row or column number fixes
//   it; an inner cell, a row sum, a column sum or the total is a function of the numbers (Mal: g·f, g·F, f·G, G·F; Plus:
//   g + f, n·g + F, n·f + G, n·G + n·F; with F the sum of the column numbers, G of the row numbers) that is linear in
//   each single number.
// - Propagation: while some equation has exactly one unknown x, it is a·x + b with b its value at x = 0 and a its value
//   at x = 1 minus b; with a ≠ 0, x = (typed − b) / a must be a whole number from 0 to 9999, else the square is
//   `wrong`; with a = 0 the equation does not depend on x: it must hold already (b = typed), else `wrong`. An equation
//   with no unknown must hold, else `wrong`.
// - When numbers stay unknown, the square has more than one solution: `many`, and the key says "Auch andere Lösungen
//   sind richtig." Then a depth-first search over the unknowns. At each node the unknown picked is the one in the
//   equation with the fewest unknowns (two or more); ties: an inner cell before a sum, then the lower index. Each try
//   propagates, and a try that fails goes back to the next candidate of the level above. A try whose lower bound (every
//   equation with its open numbers at 0) is above its typed value fails at once. The candidates of an unknown: no value
//   above the largest one at which each equation with it stays at or below its typed value (the others at 0); in Mal
//   also a divisor of every typed inner cell or row or column sum above 0 it is a factor of (the divisors, ascending).
//   Without a divisor rule: 0 up to that bound, ascending. Mal line sums and the total are products of two parts, each
//   a single number or the sum F (of the column numbers) or G (of the row numbers): a part fully known and above 0 makes
//   the other part's sum a linear target, value / part, which must be whole (else `wrong`), and propagates when one
//   number is left; a known part 0 needs a typed value 0. A typed value above 0 caps every number of its parts at the
//   value, and a known part caps the other part's numbers at target minus the sum known. The pick prefers the numbers
//   of a part with such a target. The first complete assignment stays, and every number of it
//   must be whole and 0 to 99999. Two passes, each with its own budget of tries (a candidate that is tried counts, also
//   one that fails at once); pass 2 runs only when pass 1 found nothing. Pass 1, budget 1500: the drawn number first if
//   it is in the domain, then ascending. Pass 2, budget 3500: ascending, the drawn number not used. In an ascending run
//   a lower-bound failure stops the run, as every larger candidate fails too. A square whose pass 2 runs out of budget is
//   `wrong`: that is the only way a typed set that fits some square can still come out `wrong`. A subset of a drawn
//   square's numbers always gives that square back.
// - A square is also `wrong` when any of its numbers (sums and total too) is above 99999.
// - A wrong square shows its typed cells on the pupils' sheet; the other cells stay empty, also in the key: never a
//   false number. Typed numbers outside the Zahlenraum or the Reihen count.
//
// The generator `made` (memo of 50, `rng` from zahlenmauer.ts): per square, every draw in this order whatever is
// typed, so that the squares after a typed one stay as they were: the column numbers, the row numbers, the drawn order
// of the rows, that of the columns, one draw per hidden row (its given cell's column), one per hidden column (its given
// cell's row). Each square's numbers are `cells`, (n + 2) × (n + 2), cells[r][c] at the positions above, 0 at the
// three corners that are no position.
//
// The drawing (sheet.tsx `Malquadrat`, on screen, print and in the key alike): `div.malquadrat` holds one svg. Each
// square `g.square[data-square=i]` (class `wrong`, class `many`) has `g.corner` (a rect and `text.op`, "·" or "+"),
// and a cell `g.cell[data-row][data-col]` per position (rows and columns from 0 as above): a rect and, when it shows, a
// text: class `given` in #222, in the key an empty one class `answer` in #c0392b. The row and column number cells and
// the corner are filled #eeeeee, the inner cells white, the sums and the total white with a stroke of 0.8, the others
// 0.4. In the key a square with `many` and not wrong has `text.note` "Auch andere Lösungen sind richtig." below it.
//
// Units: a cell is CELL = 10 square; the sums column and the sums row sit SG = 2 apart from the inner cells; a square
// is (n + 2) · CELL + SG wide, and as high plus NOTE_H = 6 below it always (room for the key's note, so that the key
// and the sheet have the same height); squares side by side CG = 8 apart, rows of squares RG = 4 apart. A number of
// more than 3 digits draws smaller to fit its cell (`numberSize` in sheet.tsx).
//
// The panel (pages/Malquadrat.tsx), whose words the tests take as selectors: steppers "Ein Malquadrat weniger/mehr"
// ("2 Malquadrate"), "Weniger Malquadrate nebeneinander" / "Mehr Malquadrate nebeneinander" ("2 nebeneinander"),
// "Kleiner" / "Größer" ("3 × 3 Felder"; a change drops `typed` in the same undo step); select "Rechenart" ("Mal",
// "Plus"; a change drops `typed` in the same undo step too); with Mal checkboxes "1er-Reihe" to "10er-Reihe" (the last checked one is disabled); with Plus select
// "Zahlenraum" ("bis 20", "bis 100", "bis 1000"); select "Aufgabentyp" ("Nur die Zahlen am Rand", "Rand und Innen
// gemischt", "Knobelaufgabe über die Summen"); select "Malquadrat für eigene Zahlen" (with 2 or more squares); number
// fields "Zeile i, Spalte j" (i and j from 0 to n + 1, every position) showing the given numbers (typed or drawn), the
// other boxes empty. Hints (p.hint, role=status): per wrong square "Malquadrat i: Die Zahlen passen nicht zusammen.";
// per square with many and not wrong "Malquadrat i: Es gibt mehr als eine Lösung." Buttons "Eigene Zahlen entfernen"
// (with typed), "Neu würfeln".

import { rng } from "./zahlenmauer";

/** A number the teacher typed: the square's index (from 0), the row (0 to 5), the column (0 to 5), the value (0 to 9999). */
export type MalquadratTyped = [number, number, number, number];
export type MalquadratProps = {
  /** Number of Malquadrate on the sheet, side by side in rows of `columns`. Default 2.
   * @minimum 1
   * @maximum 4
   */
  count: number;
  /** Number of Malquadrate per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** Inner cells per side: the square has size × size products, size row numbers down the left and size column numbers along the top, a sum after each row and below each column, and the total in the corner. Default 3.
   * @minimum 2
   * @maximum 4
   */
  size: number;
  /** The Rechenart: "*" (Mal: each inner cell is row number times column number) or "+" (Plus: row number plus column number). Default "*". */
  op: "*" | "+";
  /** Mal only: the Einmaleins-Reihen the column numbers are drawn from, distinct numbers 1 to 10. The row numbers are 2 to 10. Default [2, 3, 4, 5, 6, 7, 8, 9]. */
  reihen: number[];
  /** Plus only: the Zahlenraum, 20, 100 or 1000: every row and column number is at most half of it, so every inner cell is at most max. Default 20. */
  max: number;
  /** The Aufgabentyp: "factors" every row and column number is given and the rest is to fill; "mixed" some row and column numbers are hidden and one inner cell each is given instead; "knobel" as mixed, but one hidden row number can only be found through its given row sum. Every task has one solution. Default "factors". */
  task: "factors" | "mixed" | "knobel";
  /** Seed for the random squares. The same seed always gives the same squares. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [square index from 0, row 0 to 5, column 0 to 5, value 0 to 9999]. Row 0 holds the column numbers, column 0 the row numbers, row and column size + 1 the sums, and [s, size + 1, size + 1] the total. A square with typed numbers shows exactly its typed cells; the others are worked out from them. A square whose typed numbers do not fit together is marked wrong and its key shows no answers. */
  typed?: MalquadratTyped[];
};

// A square: its numbers (cells[r][c] at the positions of the contract, 0 where unknown or no position), which show on
// the pupils' sheet, and whether its typed numbers do not fit together or allow more than one solution.
export type Square = {
  size: number;
  op: "*" | "+";
  cells: number[][];
  given: boolean[][];
  wrong: boolean;
  many: boolean;
};
export type Made = { squares: Square[] };

export const DEFAULTS: Omit<MalquadratProps, "seed"> = {
  count: 2,
  columns: 2,
  size: 3,
  op: "*",
  reihen: [2, 3, 4, 5, 6, 7, 8, 9],
  max: 20,
  task: "factors",
};
export const MAXES = [20, 100, 1000];

// The exports the drawing, the panel and the insert use; the generator fills them in:
// - `sane(p: MalquadratProps): MalquadratProps`: the sane settings (a wrong value gives its default, as the contract
//   says; `typed` only when it has entries).
// - `layout(p: Pick<MalquadratProps, "count" | "columns" | "size">)`: { CELL, SG, NOTE_H, CG, RG, TW, TH, lines, vbW,
//   vbH }, TW and TH one square's slot with its note line, vbW and vbH the viewBox (+1 each, as magischesquadrat.ts).
// - `heightFor(p: MalquadratProps, w: number): number`: the height in mm at width w, at the default scale at most (S0
//   = 180 / layout(DEFAULTS).vbW, as magischesquadrat.ts).
// - `opLabel(op: "*" | "+"): string`: "·" or "+".
// - `solve(n, op, known: (number | null)[][], drawn: number[][]): { kind: "none" } | { kind: "one" | "many"; cells:
//   number[][] }`: the teacher's own square from its typed cells, as above.
// - `made(p: MalquadratProps): Made` (p already sane).

const range = (n: number) => Array.from({ length: n }, (_, i) => i);

export function opLabel(op: "*" | "+"): string {
  return op === "*" ? "·" : "+";
}

export function sane(p: MalquadratProps): MalquadratProps {
  const count = Number.isInteger(p.count) && p.count >= 1 && p.count <= 4 ? p.count : DEFAULTS.count;
  const columns = Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 3 ? p.columns : DEFAULTS.columns;
  const size = Number.isInteger(p.size) ? Math.min(4, Math.max(2, p.size)) : DEFAULTS.size;
  const op = p.op === "*" || p.op === "+" ? p.op : DEFAULTS.op;
  const cleaned = Array.isArray(p.reihen)
    ? [...new Set(p.reihen.filter((k) => Number.isInteger(k) && k >= 1 && k <= 10))]
    : [];
  const reihen = cleaned.length ? cleaned : DEFAULTS.reihen;
  const max = MAXES.includes(p.max) ? p.max : DEFAULTS.max;
  const task = p.task === "mixed" || p.task === "knobel" ? p.task : DEFAULTS.task;
  const seed = Number.isFinite(p.seed) ? p.seed : 0;
  const typed = new Map<string, MalquadratTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 4 || !t.every((x) => Number.isInteger(x))) continue;
      const [s, r, c, v] = t;
      if (s < 0 || s > 3 || r < 0 || r > 5 || c < 0 || c > 5 || v < 0 || v > 9999) continue;
      typed.delete(`${s}:${r}:${c}`);
      typed.set(`${s}:${r}:${c}`, [s, r, c, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count,
    columns,
    size,
    op,
    reihen,
    max,
    task,
    seed,
    ...(kept.length ? { typed: kept } : {}),
  };
}

export function layout(p: Pick<MalquadratProps, "count" | "columns" | "size">) {
  const [CELL, SG, NOTE_H, CG, RG] = [10, 2, 6, 8, 4];
  const TW = (p.size + 2) * CELL + SG;
  const TH = TW + NOTE_H;
  const across = Math.min(p.columns, p.count);
  const lines = Math.ceil(p.count / p.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = lines * TH + (lines - 1) * RG + 1;
  return { CELL, SG, NOTE_H, CG, RG, TW, TH, lines, vbW, vbH };
}

// The default block is drawn at 180 mm wide at this scale; a narrower block scales down, a wider one stays at it.
const S0 = 180 / layout(DEFAULTS).vbW;

export function heightFor(p: MalquadratProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// Positions of a square of size n: every grid position except the three corners.
function positions(n: number): [number, number][] {
  const out: [number, number][] = [];
  for (let r = 0; r <= n + 1; r++)
    for (let c = 0; c <= n + 1; c++) {
      const corner = (r === 0 && c === 0) || (r === 0 && c === n + 1) || (r === n + 1 && c === 0);
      if (!corner) out.push([r, c]);
    }
  return out;
}

// The unknowns: x[j] the column number j, x[n + i] the row number i (0-based). The numbers at grid position (r, c).
function valueAt(op: "*" | "+", n: number, r: number, c: number, x: number[]): number {
  const mal = op === "*";
  const F = range(n).reduce((s, j) => s + x[j], 0);
  const G = range(n).reduce((s, i) => s + x[n + i], 0);
  if (r === 0) return x[c - 1];
  if (c === 0) return x[n + r - 1];
  const g = x[n + r - 1];
  const f = x[c - 1];
  if (r <= n && c <= n) return mal ? g * f : g + f;
  if (c === n + 1 && r <= n) return mal ? g * F : n * g + F;
  if (r === n + 1 && c <= n) return mal ? f * G : n * f + G;
  return mal ? G * F : n * G + n * F;
}

// The unknowns an equation at grid position (r, c) depends on.
function varsAt(n: number, r: number, c: number): number[] {
  if (r === 0) return [c - 1];
  if (c === 0) return [n + r - 1];
  if (r <= n && c <= n) return [n + r - 1, c - 1];
  if (c === n + 1 && r <= n) return [n + r - 1, ...range(n)];
  if (r === n + 1 && c <= n) return [c - 1, ...range(n).map((i) => n + i)];
  return range(2 * n);
}

// A Mal line sum or the total is the product of two parts, each the sum of some numbers (a single number is a part too).
type Eq = { r: number; c: number; value: number; vars: number[]; prod?: { LA: number[]; LB: number[] } };

// The parts of a product equation: the sum of each part's numbers, and the numbers still open in it.
const partOf = (x: (number | null)[], L: number[]) => {
  let s = 0;
  const open: number[] = [];
  for (const k of L) {
    const y = x[k];
    if (y === null) open.push(k);
    else s += y;
  }
  return { s, open };
};

// Propagates the equations over x (null where unknown). False when an equation breaks or a number has no whole value.
// The lowest value an equation can take: every number is at least 0 and every equation grows with each of its numbers,
// so with its open numbers at 0 it is a lower bound. Above the typed value, no open number fits.
function lowerFails(op: "*" | "+", n: number, eqs: Eq[], x: (number | null)[]): boolean {
  return eqs.some((e) => {
    if (e.vars.every((v) => x[v] !== null)) return false;
    return valueAt(op, n, e.r, e.c, x.map((v) => v ?? 0)) > e.value;
  });
}

function propagate(op: "*" | "+", n: number, eqs: Eq[], x: (number | null)[]): boolean {
  let changed = true;
  while (changed) {
    changed = false;
    for (const e of eqs) {
      if (e.prod) {
        // One part fully known and > 0: the other part's sum is value / that part (whole); 0 needs value 0.
        const A = partOf(x, e.prod.LA);
        const B = partOf(x, e.prod.LB);
        if (A.open.length === 0 && B.open.length === 0) {
          if (A.s * B.s !== e.value) return false;
        } else if (A.open.length === 0 || B.open.length === 0) {
          const K = A.open.length === 0 ? A : B;
          const O = A.open.length === 0 ? B : A;
          if (K.s === 0) {
            if (e.value !== 0) return false;
          } else {
            if (e.value % K.s !== 0) return false;
            const target = e.value / K.s;
            if (O.s > target) return false;
            if (O.open.length === 0) {
              if (O.s !== target) return false;
            } else if (O.open.length === 1) {
              const d = target - O.s;
              if (!Number.isInteger(d) || d < 0 || d > 9999) return false;
              x[O.open[0]] = d;
              changed = true;
            }
          }
        }
      }
      const open = e.vars.filter((v) => x[v] === null);
      if (open.length > 1) {
        if (lowerFails(op, n, [e], x)) return false;
        continue;
      }
      const known = x.map((v) => v ?? 0);
      if (open.length === 0) {
        if (valueAt(op, n, e.r, e.c, known) !== e.value) return false;
        continue;
      }
      const v = open[0];
      known[v] = 0;
      const b = valueAt(op, n, e.r, e.c, known);
      known[v] = 1;
      const a = valueAt(op, n, e.r, e.c, known) - b;
      if (a === 0) {
        if (b !== e.value) return false;
        continue;
      }
      const d = (e.value - b) / a;
      if (!Number.isInteger(d) || d < 0 || d > 9999) return false;
      x[v] = d;
      changed = true;
    }
  }
  return true;
}

export type Solved = { kind: "none" } | { kind: "one" | "many"; cells: number[][] };

// The numbers of a square of size n from its known grid (null where not known). Propagation first; the numbers still
// free are searched depth first in two passes (see the contract above): the unknown with the fewest open equation
// partners first, each try propagates, a failed try goes back to the next candidate. Budgets of 1500 and 3500 tries;
// none when the second runs out. Kind "many" when propagation from the typed cells alone left numbers free.
export function solve(
  n: number,
  op: "*" | "+",
  known: (number | null)[][],
  drawn: number[][],
): Solved {
  const eqs: Eq[] = [];
  for (const [r, c] of positions(n)) {
    const value = known[r][c];
    if (value === null) continue;
    const gList = range(n).map((i) => n + i);
    const fList = range(n);
    let prod: Eq["prod"];
    if (op === "*" && r <= n && c === n + 1) prod = { LA: [n + r - 1], LB: fList };
    else if (op === "*" && r === n + 1 && c <= n) prod = { LA: [c - 1], LB: gList };
    else if (op === "*" && r === n + 1 && c === n + 1) prod = { LA: gList, LB: fList };
    eqs.push({ r, c, value, vars: varsAt(n, r, c), prod });
  }
  const start: (number | null)[] = Array(2 * n).fill(null);
  if (!propagate(op, n, eqs, start)) return { kind: "none" };
  const free = start.some((v) => v === null);
  const divCache = new Map<number, number[]>();
  const divisorsOf = (p: number): number[] => {
    let d = divCache.get(p);
    if (!d) {
      d = range(p).map((k) => k + 1).filter((k) => p % k === 0);
      divCache.set(p, d);
    }
    return d;
  };
  const isInner = (e: Eq) => e.r >= 1 && e.r <= n && e.c >= 1 && e.c <= n;
  // The candidates of the unknown v at x, as [value, ascending] pairs. Both ops: no value above the largest one at which
  // each equation with v stays at or below its typed value (the others at 0). Mal: v divides every typed inner cell and
  // row or column sum (above 0) it is a factor of. Mode 1 starts with the drawn number when it is in the domain.
  function* candidates(v: number, x: (number | null)[], mode: 1 | 2): Generator<[number, boolean]> {
    let divs: number[] | null = null;
    let bound = 9999;
    for (const e of eqs) {
      if (!e.vars.includes(v)) continue;
      if (e.prod) {
        // Both parts are at least 1 when the value is above 0, so each number of a part is at most the value. A known
        // part with a sum target caps the numbers of the other part at target minus its known sum.
        if (e.value > 0) bound = Math.min(bound, e.value);
        const A = partOf(x, e.prod.LA);
        const B = partOf(x, e.prod.LB);
        const K = A.open.length === 0 ? A : B.open.length === 0 ? B : null;
        const O = K === A ? B : A;
        if (K && K.s > 0 && e.value % K.s === 0 && O.open.includes(v)) {
          const cap = e.value / K.s - O.s;
          if (cap < 0) return;
          bound = Math.min(bound, cap);
        }
      }
      const xs = x.map((y) => y ?? 0);
      xs[v] = 0;
      if (valueAt(op, n, e.r, e.c, xs) > e.value) return;
      let lo = 0;
      let hi = bound;
      while (lo < hi) {
        const mid = Math.ceil((lo + hi) / 2);
        xs[v] = mid;
        if (valueAt(op, n, e.r, e.c, xs) <= e.value) lo = mid;
        else hi = mid - 1;
      }
      bound = Math.min(bound, lo);
      if (op === "*" && e.value > 0) {
        const restricts =
          isInner(e) || (e.c === n + 1 && e.r <= n && v === n + e.r - 1) || (e.r === n + 1 && e.c <= n && v === e.c - 1);
        if (restricts) {
          const d = divisorsOf(e.value);
          divs = divs ? divs.filter((t) => d.includes(t)) : d;
        }
      }
    }
    const first = v < n ? drawn[0][v + 1] : drawn[v - n + 1][0];
    const inDomain = (t: number) => t <= bound && (divs === null || divs.includes(t));
    if (mode === 1 && inDomain(first)) yield [first, false];
    const skip = mode === 1 ? first : -1;
    if (divs) {
      for (const t of divs) if (t <= bound && t !== skip) yield [t, true];
    } else {
      for (let t = 0; t <= bound; t++) if (t !== skip) yield [t, true];
    }
  }
  // The unknown in the fewest equations with two or more unknowns; ties: an inner cell before a sum, then the lower index.
  const pick = (x: (number | null)[]): number => {
    let best = -1;
    let bestCount = Infinity;
    let bestInner = 2;
    const consider = (k: number, count: number, inner: number) => {
      if (count < bestCount || (count === bestCount && (inner < bestInner || (inner === bestInner && k < best)))) {
        best = k;
        bestCount = count;
        bestInner = inner;
      }
    };
    for (const e of eqs) {
      if (e.prod) {
        const A = partOf(x, e.prod.LA);
        const B = partOf(x, e.prod.LB);
        if ((A.open.length === 0) !== (B.open.length === 0)) {
          // One part is known: the other part has a sum target, so its numbers come first.
          for (const k of (A.open.length === 0 ? B : A).open) consider(k, 0, 1);
          continue;
        }
      }
      const open = e.vars.filter((k) => x[k] === null);
      if (open.length < 2) continue;
      const inner = isInner(e) ? 0 : 1;
      for (const k of open) consider(k, open.length, inner);
    }
    return best;
  };
  // One depth-first pass with `limit` tries.
  const pass = (mode: 1 | 2, limit: number): (number | null)[] | null => {
    let budget = limit;
    const search = (x0: (number | null)[]): (number | null)[] | null => {
      const x = [...x0];
      if (!propagate(op, n, eqs, x)) return null;
      const v = pick(x);
      if (v < 0) {
        // No equation with two unknowns left: each remaining number takes its first candidate, without branching.
        const out = [...x];
        for (let k = 0; k < 2 * n; k++) {
          if (out[k] !== null) continue;
          const c = candidates(k, x, mode).next();
          if (c.done) return null;
          out[k] = c.value[0];
        }
        return out;
      }
      for (const [t, ascending] of candidates(v, x, mode)) {
        if (--budget < 0) return null;
        const trial = x.map((y, k) => (k === v ? t : y));
        if (lowerFails(op, n, eqs, trial)) {
          if (ascending) break;
          continue;
        }
        const r = search(trial);
        if (r) return r;
      }
      return null;
    };
    return search(start);
  };
  const x = pass(1, 1500) ?? pass(2, 3500);
  if (!x) return { kind: "none" };
  const nums = x as number[];
  const cells = range(n + 2).map(() => Array(n + 2).fill(0));
  for (const [r, c] of positions(n)) cells[r][c] = valueAt(op, n, r, c, nums);
  if (cells.flat().some((v) => !Number.isInteger(v) || v < 0 || v > 99999)) return { kind: "none" };
  return { kind: free ? "many" : "one", cells };
}

const shuffle = <T>(xs: T[], next: () => number): T[] => {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};

// One square: its numbers, the draws of its numbers and of its hidden positions (always, typed or not), then either its
// typed cells solved or its drawn given cells picked for the task.
function squareOf(p: MalquadratProps, i: number, next: () => number): Square {
  const n = p.size;
  // Column numbers, then row numbers.
  let f: number[];
  let g: number[];
  if (p.op === "*") {
    const pool: number[] = [];
    while (pool.length < n) pool.push(...shuffle(p.reihen, next));
    f = pool.slice(0, n);
    g = shuffle(range(9).map((k) => k + 2), next).slice(0, n);
  } else {
    const half = Math.floor(p.max / 2);
    f = shuffle(range(half).map((k) => k + 1), next).slice(0, n);
    g = shuffle(range(half).map((k) => k + 1), next).slice(0, n);
  }
  const rowOrder = shuffle(range(n), next);
  const colOrder = shuffle(range(n), next);
  const h = Math.floor(n / 2);
  const hiddenRows = rowOrder.slice(0, h);
  const shownRows = rowOrder.slice(h);
  const hiddenCols = colOrder.slice(0, h);
  const shownCols = colOrder.slice(h);
  const rowCells = hiddenRows.map((r) => [r, shownCols[Math.floor(next() * shownCols.length)]]);
  const colCells = hiddenCols.map((c) => [shownRows[Math.floor(next() * shownRows.length)], c]);

  const x = [...f, ...g];
  const drawn = range(n + 2).map((r) => range(n + 2).map((c) => 0));
  for (const [r, c] of positions(n)) drawn[r][c] = valueAt(p.op, n, r, c, x);
  const empty = () => range(n + 2).map(() => Array(n + 2).fill(false) as boolean[]);

  const typed = (p.typed ?? []).filter(([s, r, c]) => s === i && positions(n).some(([pr, pc]) => pr === r && pc === c));
  if (typed.length) {
    const known: (number | null)[][] = range(n + 2).map(() => Array(n + 2).fill(null));
    const given = empty();
    for (const [, r, c, v] of typed) {
      known[r][c] = v;
      given[r][c] = true;
    }
    const res = solve(n, p.op, known, drawn);
    const cells = res.kind === "none" ? range(n + 2).map(() => Array(n + 2).fill(0)) : res.cells;
    if (res.kind === "none") for (const [, r, c, v] of typed) cells[r][c] = v;
    return {
      size: n,
      op: p.op,
      cells,
      given,
      wrong: res.kind === "none",
      many: res.kind === "many",
    };
  }

  const given = empty();
  if (p.task !== "factors") {
    f.forEach((_, j) => (given[0][j + 1] = !hiddenCols.includes(j)));
    g.forEach((_, i2) => (given[i2 + 1][0] = !hiddenRows.includes(i2)));
  } else {
    f.forEach((_, j) => (given[0][j + 1] = true));
    g.forEach((_, i2) => (given[i2 + 1][0] = true));
  }
  if (p.task !== "factors") {
    const inner = p.task === "knobel" ? rowCells.slice(1) : rowCells;
    for (const [r, c] of [...inner, ...colCells]) given[r + 1][c + 1] = true;
    if (p.task === "knobel") given[hiddenRows[0] + 1][n + 1] = true;
  }
  return { size: n, op: p.op, cells: drawn, given, wrong: false, many: false };
}

// The squares of the settings. Same settings, same squares; a memo of 50 keeps the last ones.
const memo = new Map<string, Made>();

export function made(props: MalquadratProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const next = rng(p.seed);
  const out: Made = { squares: range(p.count).map((i) => squareOf(p, i, next)) };
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}
