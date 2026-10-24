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
import { range, solve, squareOf } from "./malquadrat/solve";
export { solve };
export type { Solved } from "./malquadrat/solve";

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
