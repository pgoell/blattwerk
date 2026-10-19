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
// - The unknowns are the 2n row and column numbers, and F and G, the sums of the column numbers and of the row numbers.
//   Each has an interval of whole numbers: 0 to 9999 for a row or column number, 0 to n · 9999 for F and G. Each typed
//   cell is an equation: a typed row or column number fixes it; an inner cell, a row sum, a column sum or the total is
//   linear in the numbers (Plus: g + f, n·g + F, n·f + G, n·G + n·F) or the product of two of them (Mal: g·f, g·F,
//   f·G, G·F). F and G are tied to the numbers by equations too. Every cell of the result is at most 99999: in Mal each
//   cell's product is capped so, in Plus the total (G + F at most 99999 / n; no other cell can pass it).
// - Propagation: a linear equation narrows each number's interval from the others' intervals; a product narrows each
//   factor from the other (above 0 both factors are at least 1; 0 needs a factor 0), and a cap narrows each factor to
//   99999 over the other's lowest value. Repeat until nothing changes. An empty interval means `wrong`.
// - When propagation fixes every row and column number, the square has one solution. Otherwise, after the first
//   solution, a second search under its own cap of 2000 nodes looks for one with other row or column numbers: found,
//   the square has more than one solution, `many`, and the key says "Auch andere Lösungen sind richtig."; not found,
//   one. A second search that reaches its cap gives `many`: the note keeps the key true (a pupil's other answer may be
//   right), where "one" without proof could mark a right answer wrong (#954).
// - Plus also, at each node: the equations must have a whole solution (column operations to one pivot per row; two row
//   sums whose difference n does not divide fail here), and the equations solved for F, G and then other numbers turn
//   every bound and the cap into an inequality over the free numbers alone, which narrows them (g + f = v ties two
//   numbers that intervals alone keep apart).
// - The search: depth first, each value of a free number in turn, the drawn value first. A Mal product that is still
//   open branches over the divisors of its value for one factor (a value 0 branches "a = 0", then "b = 0"). The first
//   assignment in which every typed cell is exact and every number of the result is at most 99999 stays. The search
//   tries every value, so a typed set is `wrong` only when no square fits it. A cap of 2000 nodes keeps typing from
//   freezing: a square whose first search reaches it is `unsure`, shows only its typed cells (in the key too) and gets
//   no hint. Of 2400 random subsets of true squares and 20000 random typed sets none reached it, in the first search
//   or the second; the slowest took 31 ms for both searches together.
// - A subset of a drawn square's numbers always gives that square back: when the drawn numbers already fit, they are
//   the answer.
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
// other boxes empty. Hints (p.hint, role=status): per wrong square that is not unsure (an unsure one is drawn as wrong:
// class `wrong`, no answers) "Malquadrat i: Die Zahlen passen nicht zusammen.";
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
  unsure: boolean;
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
// - `solve(n, op, known: (number | null)[][], drawn: number[][], cap = 2000, bounds?: [number, number][]): { kind:
//   "none"; unsure?: true } | { kind: "one" | "many"; cells: number[][]; other?: number[][]; unsure?: true }`: the
//   teacher's own square from its typed cells (see the contract above); `unsure` when a search reached its node cap,
//   `other` a second solution, `bounds` narrows the row and column numbers.
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

// The equation of a typed cell over the unknowns: a sum of coefficient · unknown = v, or a product of two unknowns = v.
// A cap: a · b (Mal) or a + b (Plus) is at most v.
type Eq =
  | { k: "lin"; t: [number, number][]; v: number }
  | { k: "prod"; a: number; b: number; v: number }
  | { k: "cap"; mal: boolean; a: number; b: number; v: number };
type Iv = [number, number][];

function eqAt(n: number, op: "*" | "+", r: number, c: number, v: number): Eq {
  const mal = op === "*";
  const F = 2 * n;
  const G = 2 * n + 1;
  const lin = (t: [number, number][]): Eq => ({ k: "lin", t, v });
  const prod = (a: number, b: number): Eq => ({ k: "prod", a, b, v });
  if (r === 0) return lin([[1, c - 1]]);
  if (c === 0) return lin([[1, n + r - 1]]);
  if (r <= n && c <= n) return mal ? prod(n + r - 1, c - 1) : lin([[1, n + r - 1], [1, c - 1]]);
  if (c === n + 1 && r <= n) return mal ? prod(n + r - 1, F) : lin([[n, n + r - 1], [1, F]]);
  if (r === n + 1 && c <= n) return mal ? prod(c - 1, G) : lin([[n, c - 1], [1, G]]);
  return mal ? prod(G, F) : lin([[n, G], [n, F]]);
}

// Narrows the intervals x by the equations until none changes. False when an interval empties.
function propagate(eqs: Eq[], x: Iv): boolean {
  let changed = true;
  const cut = (k: number, lo: number, hi: number): boolean => {
    const nlo = Math.max(x[k][0], lo);
    const nhi = Math.min(x[k][1], hi);
    if (nlo > nhi) return false;
    if (nlo !== x[k][0] || nhi !== x[k][1]) {
      x[k] = [nlo, nhi];
      changed = true;
    }
    return true;
  };
  while (changed) {
    changed = false;
    for (const e of eqs) {
      if (e.k === "cap") {
        const [a, b] = [x[e.a][0], x[e.b][0]];
        const ok = e.mal
          ? (b === 0 || cut(e.a, 0, Math.floor(e.v / b))) && (a === 0 || cut(e.b, 0, Math.floor(e.v / a)))
          : cut(e.a, 0, e.v - b) && cut(e.b, 0, e.v - a);
        if (!ok) return false;
        continue;
      }
      if (e.k === "prod") {
        if (e.v === 0) {
          if (x[e.a][0] > 0 && !cut(e.b, 0, 0)) return false;
          if (x[e.b][0] > 0 && !cut(e.a, 0, 0)) return false;
        } else {
          // Both factors in 1..v; each within v over the other's interval.
          const ok =
            cut(e.a, 1, e.v) &&
            cut(e.b, 1, e.v) &&
            cut(e.a, Math.ceil(e.v / x[e.b][1]), Math.floor(e.v / x[e.b][0])) &&
            cut(e.b, Math.ceil(e.v / x[e.a][1]), Math.floor(e.v / x[e.a][0]));
          if (!ok) return false;
        }
        continue;
      }
      const mins = e.t.map(([a, k]) => Math.min(a * x[k][0], a * x[k][1]));
      const maxs = e.t.map(([a, k]) => Math.max(a * x[k][0], a * x[k][1]));
      const lo = mins.reduce((s, m) => s + m, 0);
      const hi = maxs.reduce((s, m) => s + m, 0);
      for (let i = 0; i < e.t.length; i++) {
        const [a, k] = e.t[i];
        // a · x[k] lies in [A, B], given the others' sum.
        const A = e.v - (hi - maxs[i]);
        const B = e.v - (lo - mins[i]);
        const ok = a > 0 ? cut(k, Math.ceil(A / a), Math.floor(B / a)) : cut(k, Math.ceil(B / a), Math.floor(A / a));
        if (!ok) return false;
      }
    }
  }
  return true;
}

// Whether the linear equations and the fixed numbers have a whole solution at all, bounds aside (Plus: two row sums whose
// difference n does not divide). Column operations that keep whole solutions whole bring each row to one pivot.
function wholeSolvable(eqs: Eq[], x: Iv): boolean {
  const k = x.length;
  const rows: number[][] = [];
  for (const e of eqs)
    if (e.k === "lin") {
      const row = Array(k + 1).fill(0) as number[];
      for (const [a, i] of e.t) row[i] += a;
      row[k] = e.v;
      rows.push(row);
    }
  x.forEach(([lo, hi], i) => {
    if (lo !== hi) return;
    const row = Array(k + 1).fill(0) as number[];
    row[i] = 1;
    row[k] = lo;
    rows.push(row);
  });
  const y: number[] = [];
  let col = 0;
  for (const row of rows) {
    for (;;) {
      let p = -1;
      for (let c = col; c < k; c++) if (row[c] !== 0 && (p < 0 || Math.abs(row[c]) < Math.abs(row[p]))) p = c;
      if (p < 0) break;
      let done = true;
      for (let c = col; c < k; c++) {
        if (c === p || row[c] === 0) continue;
        const q = Math.floor(row[c] / row[p]);
        for (const r of rows) r[c] -= q * r[p];
        if (row[c] !== 0) done = false;
      }
      if (done) {
        for (const r of rows) [r[col], r[p]] = [r[p], r[col]];
        break;
      }
    }
    const rest = row[k] - y.reduce((s, v, c) => s + row[c] * v, 0);
    if (col < k && row[col] !== 0) {
      if (rest % row[col] !== 0) return false;
      y.push(rest / row[col]);
      col++;
    } else if (rest !== 0) return false;
  }
  return true;
}

// Plus: the equations solved for some numbers in terms of the others (free), so that each bound and the cap become one
// inequality over free numbers alone; these narrow the free numbers' intervals, and those the others'. Intervals per
// number lose that g + f = v ties two numbers; this keeps it. Bounds are rounded outward, so it never drops a solution.
function project(eqs: Eq[], x: Iv): boolean {
  const k = x.length;
  const rows: number[][] = [];
  for (const e of eqs)
    if (e.k === "lin") {
      const row = Array(k + 1).fill(0) as number[];
      for (const [a, i] of e.t) row[i] += a;
      row[k] = e.v;
      rows.push(row);
    }
  const pivots: number[] = [];
  let r0 = 0;
  // F and G first, so that the cap on G + F reads over the row and column numbers.
  for (const c of [k - 2, k - 1, ...range(k - 2)]) {
    if (r0 >= rows.length) break;
    const p = rows.findIndex((row, i) => i >= r0 && Math.abs(row[c]) > 1e-9);
    if (p < 0) continue;
    [rows[r0], rows[p]] = [rows[p], rows[r0]];
    const piv = rows[r0][c];
    rows[r0] = rows[r0].map((v) => v / piv);
    for (let i = 0; i < rows.length; i++)
      if (i !== r0 && Math.abs(rows[i][c]) > 1e-9) {
        const m = rows[i][c];
        rows[i] = rows[i].map((v, j) => v - m * rows[r0][j]);
      }
    pivots.push(c);
    r0++;
  }
  const free = range(k).filter((c) => !pivots.includes(c));
  // Each inequality: lo ≤ const + Σ coef · free ≤ hi. A pivot number p = rhs − Σ row[q] · x[q].
  const ineqs: { p?: number; c: number; t: [number, number][]; lo: number; hi: number }[] = pivots.map((p, i) => ({
    p,
    c: rows[i][k],
    t: free.filter((q) => Math.abs(rows[i][q]) > 1e-9).map((q): [number, number] => [-rows[i][q], q]),
    lo: x[p][0],
    hi: x[p][1],
  }));
  for (const e of eqs)
    if (e.k === "cap" && !e.mal) {
      // a + b over the free numbers.
      const coef = Array(k).fill(0) as number[];
      let c = 0;
      for (const v of [e.a, e.b]) {
        const i = pivots.indexOf(v);
        if (i < 0) coef[v] += 1;
        else {
          c += rows[i][k];
          for (const q of free) coef[q] -= rows[i][q];
        }
      }
      ineqs.push({ c, t: free.filter((q) => Math.abs(coef[q]) > 1e-9).map((q): [number, number] => [coef[q], q]), lo: -Infinity, hi: e.v });
    }
  const eps = 1e-6;
  for (let round = 0; round < 20; round++) {
    let changed = false;
    for (const q of ineqs) {
      const mins = q.t.map(([a, i]) => Math.min(a * x[i][0], a * x[i][1]));
      const maxs = q.t.map(([a, i]) => Math.max(a * x[i][0], a * x[i][1]));
      const lo = q.c + mins.reduce((s, m) => s + m, 0);
      const hi = q.c + maxs.reduce((s, m) => s + m, 0);
      if (lo > q.hi + eps || hi < q.lo - eps) return false;
      q.t.forEach(([a, i], j) => {
        // a · x[i] lies in [q.lo − (hi − maxs[j]), q.hi − (lo − mins[j])].
        const A = q.lo - (hi - maxs[j]);
        const B = q.hi - (lo - mins[j]);
        let [nlo, nhi] = a > 0 ? [A / a, B / a] : [B / a, A / a];
        nlo = Math.max(x[i][0], Math.ceil(nlo - eps));
        nhi = Math.min(x[i][1], Math.floor(nhi + eps));
        if (nlo !== x[i][0] || nhi !== x[i][1]) {
          x[i] = [nlo, nhi];
          changed = true;
        }
      });
      if (q.t.some(([, i]) => x[i][0] > x[i][1])) return false;
    }
    if (!changed) break;
  }
  // The solved-for numbers from the free numbers' intervals.
  for (const q of ineqs) {
    if (q.p === undefined) continue;
    const lo = q.c + q.t.reduce((s, [a, i]) => s + Math.min(a * x[i][0], a * x[i][1]), 0);
    const hi = q.c + q.t.reduce((s, [a, i]) => s + Math.max(a * x[i][0], a * x[i][1]), 0);
    const nlo = Math.max(x[q.p][0], Math.ceil(lo - eps));
    const nhi = Math.min(x[q.p][1], Math.floor(hi + eps));
    if (nlo > nhi) return false;
    x[q.p] = [nlo, nhi];
  }
  return true;
}

// `unsure`: a search reached its cap, so a "none" set may still fit and a "many" set may have one solution only.
// `other`: a second solution, with other row or column numbers than `cells`.
export type Solved =
  | { kind: "none"; unsure?: true }
  | { kind: "one" | "many"; cells: number[][]; other?: number[][]; unsure?: true };

// The search's cap, in nodes, so that typing never freezes the editor (see the contract).
const STEPS = 2000;

const divCache = new Map<number, number[]>();
const divisorsOf = (v: number): number[] => {
  let d = divCache.get(v);
  if (!d) {
    d = [];
    for (let k = 1; k * k <= v; k++) if (v % k === 0) d.push(k, v / k);
    d = [...new Set(d)].sort((a, b) => a - b);
    divCache.set(v, d);
  }
  return d;
};

// The numbers of a square of size n from its typed cells, exactly: propagation, then a depth-first search that tries every value, up to `cap` nodes.
// Kind "one" when propagation fixes every row and column number or a second search proves no other; "many" when it
// finds one (`other`) or reaches its cap (`unsure`). `bounds` narrows the row and column numbers (the tests' check).
export function solve(
  n: number,
  op: "*" | "+",
  known: (number | null)[][],
  drawn: number[][],
  cap = STEPS,
  bounds?: [number, number][],
): Solved {
  const F = 2 * n;
  const G = 2 * n + 1;
  const sumOf = (S: number, base: number): Eq => ({
    k: "lin",
    t: [[1, S], ...range(n).map((i): [number, number] => [-1, base + i])],
    v: 0,
  });
  const eqs: Eq[] = [sumOf(F, 0), sumOf(G, n)];
  if (op === "+") eqs.push({ k: "cap", mal: false, a: G, b: F, v: Math.floor(99999 / n) });
  const typed: [number, number, number][] = [];
  for (const [r, c] of positions(n)) {
    const e = eqAt(n, op, r, c, 0);
    if (e.k === "prod") eqs.push({ k: "cap", mal: true, a: e.a, b: e.b, v: 99999 });
    const v = known[r][c];
    if (v === null) continue;
    typed.push([r, c, v]);
    eqs.push(eqAt(n, op, r, c, v));
  }
  const root: Iv = range(2 * n + 2).map((k): [number, number] => (k < 2 * n ? [0, 9999] : [0, n * 9999]));
  bounds?.forEach(([lo, hi], k) => (root[k] = [Math.max(root[k][0], lo), Math.min(root[k][1], hi)]));
  if (root.some(([lo, hi]) => lo > hi) || !propagate(eqs, root)) return { kind: "none" };
  // Propagation alone fixed every row and column number: one solution, no second search needed.
  const fixed = root.slice(0, 2 * n).every(([lo, hi]) => lo === hi);

  const grid = (nums: number[]) => {
    const cells = range(n + 2).map(() => Array(n + 2).fill(0) as number[]);
    for (const [r, c] of positions(n)) cells[r][c] = valueAt(op, n, r, c, nums);
    return cells;
  };
  const fits = (cells: number[][]) =>
    typed.every(([r, c, v]) => cells[r][c] === v) && cells.flat().every((v) => v <= 99999);
  // The drawn numbers: the column numbers, the row numbers, then F and G.
  const dn = [...range(n).map((j) => drawn[0][j + 1]), ...range(n).map((i) => drawn[i + 1][0])];
  dn.push(
    dn.slice(0, n).reduce((s, v) => s + v, 0),
    dn.slice(n, 2 * n).reduce((s, v) => s + v, 0),
  );
  const drawnFits = dn.every((v, k) => v >= root[k][0] && v <= root[k][1]) && fits(grid(dn));
  // The value to try first: the drawn number, when it is among the values.
  const withDrawn = (k: number, list: number[]) =>
    list.includes(dn[k]) ? [dn[k], ...list.filter((t) => t !== dn[k])] : list;

  // Each node: propagate, then either an open product's factor to branch on (a divisor of its value), or the open
  // unknown with the smallest interval. Alternatives are tried in order; the first complete assignment that fits wins.
  let steps = 0;
  // Once set, the first solution: a leaf with the same row and column numbers does not count.
  let first: number[] | null = null;
  const search = (iv: Iv): number[] | null => {
    if (steps++ >= cap) return null;
    const x = iv.slice();
    if (!propagate(eqs, x)) return null;
    if (op === "+" && (!wholeSolvable(eqs, x) || !project(eqs, x) || !propagate(eqs, x))) return null;
    let alts: [number, number[]][] = [];
    let most = Infinity;
    for (const e of eqs) {
      if (e.k !== "prod") continue;
      const a = x[e.a];
      const b = x[e.b];
      if (e.v === 0) {
        if (a[1] === 0 || b[1] === 0) continue;
        if (most > 2) {
          most = 2;
          alts = [
            [e.a, [0]],
            [e.b, [0]],
          ];
        }
        continue;
      }
      if (a[0] === a[1] && b[0] === b[1]) continue;
      const dv = divisorsOf(e.v);
      const inA = dv.filter((d) => d >= a[0] && d <= a[1]);
      const inB = dv.filter((d) => d >= b[0] && d <= b[1]);
      const pick: [number, number[]] = inB.length < inA.length ? [e.b, inB] : [e.a, inA];
      if (pick[1].length < most) {
        most = pick[1].length;
        alts = [[pick[0], withDrawn(pick[0], pick[1])]];
      }
    }
    if (!alts.length) {
      let k = -1;
      for (let i = 0; i < 2 * n + 2; i++) if (x[i][0] < x[i][1] && (k < 0 || x[i][1] - x[i][0] < x[k][1] - x[k][0])) k = i;
      if (k < 0) {
        const nums = x.map((r) => r[0]);
        const f = first;
        return fits(grid(nums)) && !(f && range(2 * n).every((i) => nums[i] === f[i])) ? nums : null;
      }
      alts = [[k, withDrawn(k, range(x[k][1] - x[k][0] + 1).map((t) => x[k][0] + t))]];
    }
    for (const [k, vals] of alts)
      for (const t of vals) {
        const child = x.slice();
        child[k] = [t, t];
        const r = search(child);
        if (r) return r;
      }
    return null;
  };
  const nums = drawnFits ? dn : search(root);
  if (!nums) return steps > cap ? { kind: "none", unsure: true } : { kind: "none" };
  if (fixed) return { kind: "one", cells: grid(nums) };
  // A second search, under its own cap, for a solution with other row or column numbers.
  first = nums;
  steps = 0;
  const other = search(root);
  if (other) return { kind: "many", cells: grid(nums), other: grid(other) };
  return steps > cap ? { kind: "many", cells: grid(nums), unsure: true } : { kind: "one", cells: grid(nums) };
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
      unsure: res.kind === "none" && !!res.unsure,
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
  return { size: n, op: p.op, cells: drawn, given, wrong: false, many: false, unsure: false };
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
