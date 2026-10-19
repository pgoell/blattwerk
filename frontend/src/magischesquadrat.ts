// The Magisches Quadrat generator: 3×3 and 5×5 squares where every row, every column and both diagonals have the same
// sum, the Zielzahl. A pure function of the block's settings and its seed, so that the editor, the thumbnail and the
// PDF draw the same squares.
//
// The contract of #825, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "magischesquadrat", props: MagischesQuadratProps }`.
// - `count` squares (1 to 4, default 2) in `columns` side by side (1 to 3, default 2).
// - `size` 3 (default) or 5: the square has size × size cells. Any other value gives 3.
// - `max`, the Zahlenraum: the largest number in a drawn square, a whole number from MIN_MAX[size] (9 for 3, 25 for 5)
//   to 9999 (default 20). The panel offers 20, 100, 1000 and "Eigener" (any other); 5×5 has no 20 (25 numbers do not fit
//   in 1 to 20): a 5×5 with a max below 25 gives 100.
// - `given`, the Schwierigkeit: how many cells are given on the pupils' sheet, GIVEN[size] = [lo, hi] (3: 2 to 8,
//   5: 6 to 24). Default DEFAULT_GIVEN[size] (3: 4, 5: 15). A value outside the range gives the nearest end, a value
//   that is not a whole number the default.
// - `showSum`: the Zielzahl prints above each square, "Zielzahl: S" (default false).
// - `typed`: numbers the teacher typed, each entry [square from 0, row from 1, column from 1, value 0 to 9999]. An entry
//   outside 1 to 5 or 0 to 9999, or not four whole numbers, is dropped; of two for the same cell the last one stays.
// - `seed` alone gives the squares.
//
// A drawn square (no typed entry for it): every number from 1 to max, all distinct.
// - 3×3: the centre c and two offsets a, b, drawn until all nine numbers are distinct and from 1 to max:
//     c−b    c+a+b  c−a
//     c−a+b  c      c+a−b
//     c+a    c−a−b  c+b
//   then one of the 8 turns and mirrors, drawn. S = 3c.
// - 5×5: two Latin squares L1(i, j) = (a1·i + b1·j + s1) mod 5 and L2 likewise, with a, b, a+b, a−b not 0 mod 5 (each
//   row, column and diagonal holds 0 to 4 once) and a1·b2 − a2·b1 not 0 mod 5 (every pair once); each symbol renamed by a
//   drawn order of 0 to 4; the cell is base + P·L1 + Q·L2 with Q ≥ 1 and P ≥ 5·Q (so all 25 differ), base ≥ 1 and
//   base + 4P + 4Q ≤ max. S = 5·base + 10P + 10Q.
// - The given cells: a drawn order of all cells; going down it, a cell joins while it makes the solution more certain
//   (raises the rank of the line equations with the givens, see `solve`), until the square has one solution or `given`
//   cells; then the next cells of the order fill up to `given`. One solution needs 3 well placed cells in a 3×3 and 15
//   in a 5×5, one fewer with showSum (the Zielzahl is then known). Below that the square has more than one solution:
//   `many`, and the key says "Auch andere Lösungen sind richtig."
//
// Typed numbers win over the seed. A square with at least one typed entry is the teacher's own: exactly its typed cells
// are given, the drawn ones are not. The panel, at the first number typed into a square, stores that square's drawn
// given cells as typed entries with it, so that nothing the sheet showed goes away. Its numbers are worked out by
// `solve` from the typed cells alone (the Zielzahl is never typed, it follows from them):
// - One solution in whole numbers from 0 to 9999: the key shows it.
// - More than one: the key shows one of them, `many`; the free cells take the drawn square's numbers where those fit,
//   else up to 50 seeded draws from 1 to max; a key needs whole numbers from 0 to 9999, and distinct ones when the
//   typed numbers are distinct.
// - None (a line with all cells typed and a sum that differs, a key that is not whole or below 0, or no key found):
//   `wrong`. The pupils' sheet shows the typed cells, the other cells stay empty, also in the key: never a false
//   number. The Zielzahl does not print on a wrong square.
// Typed numbers outside the Zahlenraum count. Typed entries of squares the block does not have (after fewer squares)
// stay stored and play no part; an entry in row or column 4 or 5 of a 3×3 likewise.
//
// The generator `made` (memo of 50, `rng` from zahlenmauer.ts): per square, every draw in this order whatever is
// typed, so that the squares after a typed one stay as they were: the numbers (3×3: up to 500 tries of c, a, b, then
// the turn; 5×5: a1, b1, a2, b2 up to 200 tries each pair, s1, s2, the two symbol orders, Q, P, base), the cell order,
// the 50 draws for free cells.
//
// The drawing (sheet.tsx `MagischesQuadrat`, on screen, print and in the key alike): `div.magischesquadrat` holds one
// svg. Each square `g.square[data-square=i]` (class `wrong`, class `many`) has, with showSum and not wrong,
// `text.sum` "Zielzahl: S" above it, and a cell `g.cell[data-row][data-col]` (from 1) per cell: a rect and, when it
// shows, a text: class `given` in #222, in the key an empty one class `answer` in #c0392b. In the key a square with
// `many` and not wrong has `text.note` "Auch andere Lösungen sind richtig." below it.
//
// Units: a cell is CELL = 10 square, a square size · CELL wide, SUM_H = 8 above it when showSum, NOTE_H = 6 below
// it always (room for the key's note, so that the key and the sheet have the same height), squares side by side
// CG = 8 apart, rows of squares RG = 4 apart.
//
// The panel (pages/MagischesQuadrat.tsx), whose words the tests take as selectors: steppers "Ein Quadrat weniger/mehr"
// ("2 Quadrate"), "Weniger Quadrate nebeneinander" / "Mehr Quadrate nebeneinander" ("2 nebeneinander"), "Eine
// vorgegebene Zahl weniger/mehr" ("4 Zahlen vorgegeben"); select "Größe" ("3 × 3", "5 × 5"; a change sets `given` to
// the size's default, drops `typed` and with 5 and max below 25 sets max 100, in one undo step); select "Zahlenraum"
// ("bis 20" (disabled with 5 × 5), "bis 100", "bis 1000", "Eigener"; Eigener sets max 50) and, with Eigener, a number
// field "Eigener Zahlenraum"; checkbox "Zielzahl anzeigen"; select "Magisches Quadrat für eigene Zahlen"; number fields
// "Zeile i, Spalte j" (from 1) showing the given numbers (typed or drawn), the other boxes empty. Hints (p.hint,
// role=status): per wrong square "Magisches Quadrat i: Die Zahlen passen nicht zusammen."; per square with many and
// not wrong "Magisches Quadrat i: Es gibt mehr als eine Lösung." Buttons "Eigene Zahlen entfernen" (with typed),
// "Neu würfeln".

/** A number the teacher typed: the square's index (from 0), the row (from 1), the column (from 1), the value (0 to 9999). */
export type MagischesQuadratTyped = [number, number, number, number];
export type MagischesQuadratProps = {
  /** Number of magic squares on the sheet, side by side in rows of `columns`. Default 2.
   * @minimum 1
   * @maximum 4
   */
  count: number;
  /** Number of squares per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** Cells per side: 3 (a 3×3 square) or 5 (a 5×5 square). Default 3. */
  size: 3 | 5;
  /** The Zahlenraum, the largest number in a drawn square: 20, 100, 1000 or any whole number from 9 (3×3) or 25 (5×5) to 9999. A 5×5 with a smaller value gives 100. Default 20.
   * @minimum 9
   * @maximum 9999
   */
  max: number;
  /** The Schwierigkeit: how many cells are given on the pupils' sheet; the others are to fill in. 2 to 8 for a 3×3, 6 to 24 for a 5×5. With 3 or more (3×3) or 15 or more (5×5), or one fewer with showSum, the given cells allow exactly one solution; with fewer the key says that other solutions are right too. Default 4 (3×3) or 15 (5×5).
   * @minimum 2
   * @maximum 24
   */
  given: number;
  /** Whether the Zielzahl, the sum of every row, column and diagonal, prints above each square ("Zielzahl: 15"). Default false. */
  showSum: boolean;
  /** Seed for the random squares. The same seed always gives the same squares. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [square index from 0, row from 1, column from 1, value 0 to 9999]. A square with typed numbers shows exactly its typed cells; the others are worked out from them. A square whose typed numbers fit no magic square is marked wrong and its key shows no answers. */
  typed?: MagischesQuadratTyped[];
};

// A square: its numbers (cells[r][c], 0 where unknown), which show on the pupils' sheet, the Zielzahl, and whether its
// typed numbers fit no magic square or allow more than one.
export type Square = {
  size: 3 | 5;
  cells: number[][];
  given: boolean[][];
  sum: number;
  wrong: boolean;
  many: boolean;
};
export type Made = { squares: Square[] };

export const DEFAULTS: Omit<MagischesQuadratProps, "seed"> = {
  count: 2,
  columns: 2,
  size: 3,
  max: 20,
  given: 4,
  showSum: false,
};
export const MIN_MAX: Record<3 | 5, number> = { 3: 9, 5: 25 };
export const GIVEN: Record<3 | 5, [number, number]> = { 3: [2, 8], 5: [6, 24] };
export const DEFAULT_GIVEN: Record<3 | 5, number> = { 3: 4, 5: 15 };

// The drawing in svg units. `vbW` and `vbH` are the viewBox; `TW` and `TH` one square's slot, with the Zielzahl's
// line above (SUM_H when showSum) and the note's line below (NOTE_H). The square's cells start at `top` in the slot.
export function layout(p: Pick<MagischesQuadratProps, "count" | "columns" | "size" | "showSum">) {
  const [CELL, CG, RG, SUM_H, NOTE_H] = [10, 8, 4, 8, 6];
  const top = p.showSum ? SUM_H : 0;
  const TW = p.size * CELL;
  const TH = top + p.size * CELL + NOTE_H;
  const across = Math.min(p.columns, p.count);
  const lines = Math.ceil(p.count / p.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = lines * TH + (lines - 1) * RG + 1;
  return { CELL, CG, RG, SUM_H, NOTE_H, top, TW, TH, lines, vbW, vbH };
}

// The default block is drawn at the scale S0 at 180 mm wide. A block of width w draws its squares at that scale at
// most, and its height grows with them, so that they keep that size.
const S0 = 180 / layout(DEFAULTS).vbW;

// The height in mm of a block of width w with the props p, at which its squares draw at the default scale at most.
export function heightFor(p: MagischesQuadratProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// What `solve` finds for a square of size n from its known cells (known[r][c], null where not known) and, when it is
// known, the Zielzahl: "none" no magic square in whole numbers has them; "one" exactly one, `cells`; "many" more than
// one, `cells` one of them (the free cells take `prefer`'s numbers where those give whole numbers from 0 to 9999, else
// the draws of `next` from 1 to max, up to 50 tries; with `distinct` only a key with distinct numbers counts; no such
// key is "none"). The unknowns are the n² cells and the Zielzahl; the equations are the 2n + 2 line sums, solved by
// Gaussian elimination with a tolerance of 1e-6 (rank = number of unknowns is "one").
export type Solved = { kind: "none" } | { kind: "one" | "many"; cells: number[][]; sum: number };

// TO DO (generator): sane, made, solve as the contract says.
export function sane(p: MagischesQuadratProps): MagischesQuadratProps {
  return { ...DEFAULTS, ...p };
}

export function solve(
  _known: (number | null)[][],
  _sum: number | null,
  _opts: { prefer?: number[][]; next?: () => number; max?: number; distinct?: boolean },
): Solved {
  return { kind: "none" };
}

export function made(_props: MagischesQuadratProps): Made {
  return { squares: [] };
}
