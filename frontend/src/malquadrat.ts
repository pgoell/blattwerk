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
//   `wrong`; with a = 0 the equation waits until all is known. An equation with no unknown must hold, else `wrong`.
// - When numbers stay unknown, the square has more than one solution: `many`, and the key says "Auch andere Lösungen
//   sind richtig." Then the first unknown (column numbers 1 to n, then row numbers 1 to n) tries the drawn number, then
//   1 to 100 in order; the first that propagates without `wrong` stays; then the next unknown likewise. No number fits:
//   `wrong`. The try is greedy, with no going back: a typed set that fits some square can still come out `wrong` when
//   its free numbers are not those first tries; a subset of a drawn square's numbers always gives that square back.
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
