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
//   else the drawn square's numbers turned by v → k·v + d (k 1 or −1, d whole, so that the mean at the typed cells
//   matches: a magic square stays magic), else up to 50 seeded draws from 1 to max (or to twice the largest typed
//   number, if more); a key needs whole numbers from 0 to 9999, and distinct ones when the typed numbers are distinct.
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

import { rng } from "./zahlenmauer";

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

const EPS = 1e-6;
const range = (n: number) => Array.from({ length: n }, (_, i) => i);
const m5 = (x: number) => ((x % 5) + 5) % 5;
const whole = (x: number, lo: number, hi: number) => Number.isInteger(x) && x >= lo && x <= hi;

// The sane settings of the props: a wrong value gives its default, a typed entry that is not four whole numbers in
// range is dropped, and of two for the same cell the last one stays.
export function sane(p: MagischesQuadratProps): MagischesQuadratProps {
  const count = whole(p.count, 1, 4) ? p.count : DEFAULTS.count;
  const columns = whole(p.columns, 1, 3) ? p.columns : DEFAULTS.columns;
  const size: 3 | 5 = p.size === 5 ? 5 : 3;
  const max =
    Number.isInteger(p.max) && p.max <= 9999 && p.max >= MIN_MAX[size] ? p.max : size === 5 ? 100 : 20;
  const given = Number.isInteger(p.given)
    ? Math.min(GIVEN[size][1], Math.max(GIVEN[size][0], p.given))
    : DEFAULT_GIVEN[size];
  const typed = new Map<string, MagischesQuadratTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 4 || !t.every((x) => Number.isInteger(x))) continue;
      const [s, r, c, v] = t;
      if (s < 0 || s >= count || !whole(r, 1, 5) || !whole(c, 1, 5) || !whole(v, 0, 9999)) continue;
      typed.delete(`${s}:${r}:${c}`);
      typed.set(`${s}:${r}:${c}`, [s, r, c, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count,
    columns,
    size,
    max,
    given,
    showSum: p.showSum === true,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// The line equations of an n×n square over the unknowns: the cells (index r·n + c) and the Zielzahl (index n·n).
// Each equation is [coefficients, right side]: the 2n + 2 line sums minus S, one per known cell, and S = sum if known.
type Eq = [number[], number];
function system(known: (number | null)[][], sum: number | null): Eq[] {
  const n = known.length;
  const m = n * n + 1;
  const eqs: Eq[] = [];
  const line = (cells: number[]) => {
    const a = Array(m).fill(0);
    for (const k of cells) a[k] = 1;
    a[n * n] = -1;
    eqs.push([a, 0]);
  };
  for (let r = 0; r < n; r++) line(range(n).map((c) => r * n + c));
  for (let c = 0; c < n; c++) line(range(n).map((r) => r * n + c));
  line(range(n).map((i) => i * n + i));
  line(range(n).map((i) => i * n + (n - 1 - i)));
  for (let r = 0; r < n; r++)
    for (let c = 0; c < n; c++) {
      const v = known[r][c];
      if (v !== null) {
        const a = Array(m).fill(0);
        a[r * n + c] = 1;
        eqs.push([a, v]);
      }
    }
  if (sum !== null) {
    const a = Array(m).fill(0);
    a[n * n] = 1;
    eqs.push([a, sum]);
  }
  return eqs;
}

// Gauss-Jordan elimination with partial pivoting. `piv` lists the pivot column of each reduced row; a row past the rank
// with a right side that is not 0 says the equations contradict each other.
function reduce(eqs: Eq[], m: number) {
  const A = eqs.map(([a]) => [...a]);
  const b = eqs.map(([, v]) => v);
  const piv: number[] = [];
  for (let col = 0; col < m && piv.length < A.length; col++) {
    const k = piv.length;
    let best = k;
    for (let i = k + 1; i < A.length; i++)
      if (Math.abs(A[i][col]) > Math.abs(A[best][col])) best = i;
    if (Math.abs(A[best][col]) < EPS) continue;
    [A[k], A[best]] = [A[best], A[k]];
    [b[k], b[best]] = [b[best], b[k]];
    const d = A[k][col];
    for (let j = 0; j < m; j++) A[k][j] /= d;
    b[k] /= d;
    for (let i = 0; i < A.length; i++) {
      if (i === k || Math.abs(A[i][col]) < EPS) continue;
      const f = A[i][col];
      for (let j = 0; j < m; j++) A[i][j] -= f * A[k][j];
      b[i] -= f * b[k];
    }
    piv.push(col);
  }
  const inconsistent = b.some((v, i) => i >= piv.length && Math.abs(v) > EPS);
  return { A, b, piv, inconsistent };
}

function rankOf(known: (number | null)[][], sum: number | null): number {
  const n = known.length;
  return reduce(system(known, sum), n * n + 1).piv.length;
}

// A Fisher-Yates shuffle with the draws of next.
function shuffle<T>(xs: T[], next: () => number): T[] {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function solve(
  known: (number | null)[][],
  sum: number | null,
  opts: { prefer?: number[][]; next?: () => number; max?: number; distinct?: boolean },
): Solved {
  const n = known.length;
  const N = n * n;
  const m = N + 1;
  const sys = reduce(system(known, sum), m);
  if (sys.inconsistent) return { kind: "none" };
  const isWhole = (v: number) => Math.abs(v - Math.round(v)) < EPS;
  const good = (x: number[], distinct: boolean) => {
    if (!x.every(isWhole)) return false;
    const cells = x.slice(0, N).map(Math.round);
    if (!cells.every((v) => v >= 0 && v <= 9999)) return false;
    return !distinct || new Set(cells).size === N;
  };
  // The unknowns of the free columns set, the pivots follow from the reduced rows.
  const free = range(m).filter((j) => !sys.piv.includes(j));
  const at = (f: number[]) => {
    const x: number[] = Array(m).fill(0);
    free.forEach((j, k) => (x[j] = f[k]));
    sys.piv.forEach((j, k) => {
      let v = sys.b[k];
      for (const jf of free) v -= sys.A[k][jf] * x[jf];
      x[j] = v;
    });
    return x;
  };
  const toSquare = (x: number[]) =>
    range(n).map((r) => range(n).map((c) => Math.round(x[r * n + c])));
  if (free.length === 0) {
    const x = at([]);
    return good(x, false) ? { kind: "one", cells: toSquare(x), sum: Math.round(x[N]) } : { kind: "none" };
  }
  const next = opts.next ?? rng(0);
  const max = opts.max ?? 9999;
  const prefer = opts.prefer;
  const rowSum0 = prefer ? prefer[0].reduce((s, v) => s + v, 0) : 0;
  // A magic square stays magic under v -> k·v + d: the source square, mapped so that its mean at the known cells is the
  // mean of the known values. Its free cells, and S when free, are the values to try.
  const mapFrom = (src: number[][], srcSum: number, k: 1 | -1): number[] => {
    const pairs = known.flatMap((row, r) => row.flatMap((v, c) => (v === null ? [] : [[v, src[r][c]]])));
    const d = pairs.length ? Math.round(pairs.reduce((s, [v, p]) => s + v - k * p, 0) / pairs.length) : 0;
    return free.map((j) => (j < N ? k * src[Math.floor(j / n)][j % n] + d : k * srcSum + n * d));
  };
  const attempt = (f: number[]): Solved | null => {
    const x = at(f);
    return good(x, !!opts.distinct) ? { kind: "many", cells: toSquare(x), sum: Math.round(x[N]) } : null;
  };
  if (prefer) {
    const preferred = free.map((j) => (j < N ? prefer[Math.floor(j / n)][j % n] : rowSum0));
    for (const f of [preferred, mapFrom(prefer, rowSum0, 1), mapFrom(prefer, rowSum0, -1)]) {
      const r = attempt(f);
      if (r) return r;
    }
  }
  // A fresh small drawn square (1 to 9, or 1 to 25) is narrow, so mapped it fits a typed number far from 1 to max.
  for (let t = 0; t < 20; t++) {
    const smalls = n === 3 ? [magic3(9, next)] : [magic5(25, next), magic5(5, next, true)];
    for (const small of smalls)
      for (const k of [1, -1] as const) {
        const r = attempt(mapFrom(small.cells, small.sum, k));
        if (r) return r;
      }
  }
  const knownVals = known.flat().filter((v): v is number => v !== null);
  const hi = Math.max(max, 2 * Math.max(0, ...knownVals));
  for (let t = 0; t < 50; t++) {
    const f = free.map((j) => (j === N ? 3 + Math.floor(next() * (n * hi - 2)) : 1 + Math.floor(next() * hi)));
    const r = attempt(f);
    if (r) return r;
  }
  return { kind: "none" };
}

// The rotations and mirrors of a square: the transpose (for the mirror) and then the quarter turns.
const rot = (g: number[][]) => g.map((_, r) => g.map((_, c) => g[g.length - 1 - c][r]));
const tr = (g: number[][]) => g.map((_, r) => g.map((_, c) => g[c][r]));

// A 3×3 magic square with the centre c and the offsets a, b, drawn until its nine numbers are distinct and from 1 to max.
function magic3(max: number, next: () => number): { cells: number[][]; sum: number } {
  let [c, a, b] = [5, 1, 3]; // the fallback: 1 to 9 fits every max from 9
  for (let t = 0; t < 500; t++) {
    const c0 = 1 + Math.floor(next() * max);
    const a0 = Math.floor(next() * max) - Math.floor(max / 2);
    const b0 = Math.floor(next() * max) - Math.floor(max / 2);
    const vals = [c0, c0 + a0, c0 - a0, c0 + b0, c0 - b0, c0 + a0 + b0, c0 - a0 - b0, c0 + a0 - b0, c0 - a0 + b0];
    if (new Set(vals).size === 9 && vals.every((v) => v >= 1 && v <= max)) {
      [c, a, b] = [c0, a0, b0];
      break;
    }
  }
  let cells = [
    [c - b, c + a + b, c - a],
    [c - a + b, c, c + a - b],
    [c + a, c - a - b, c + b],
  ];
  const t = Math.floor(next() * 8);
  if (t & 4) cells = tr(cells);
  for (let k = 0; k < (t & 3); k++) cells = rot(cells);
  return { cells, sum: 3 * c };
}

// A 5×5 magic square from two orthogonal Latin squares (see the header), with base, P and Q as drawn there.
// With `thin` one Latin square alone (cell = base + L1, 1 to 5): a magic square with a spread of 4, for solve.
function magic5(max: number, next: () => number, thin = false): { cells: number[][]; sum: number } {
  const pairOk = (a: number, b: number) => [a, b, a + b, a - b].every((x) => m5(x) !== 0);
  const pair = (ok: (a: number, b: number) => boolean, fallback: [number, number]): [number, number] => {
    for (let t = 0; t < 200; t++) {
      const a = 1 + Math.floor(next() * 4);
      const b = 1 + Math.floor(next() * 4);
      if (ok(a, b)) return [a, b];
    }
    return fallback;
  };
  const [a1, b1] = pair(pairOk, [1, 2]);
  const [a2, b2] = pair((a, b) => pairOk(a, b) && m5(a1 * b - a * b1) !== 0, [2, 1]);
  const s1 = Math.floor(next() * 5);
  const s2 = Math.floor(next() * 5);
  const o1 = shuffle(range(5), next);
  const o2 = shuffle(range(5), next);
  const qMax = Math.max(1, Math.floor((max - 1) / 24));
  const Q = thin ? 0 : 1 + Math.floor(next() * qMax);
  const pHi = Math.floor((max - 1 - 4 * Q) / 4);
  const P = thin ? 1 : 5 * Q + Math.floor(next() * (pHi - 5 * Q + 1));
  const base = 1 + Math.floor(next() * (max - 4 * P - 4 * Q));
  const cells = range(5).map((i) =>
    range(5).map((j) => {
      const L1 = m5(a1 * i + b1 * j + s1);
      const L2 = m5(a2 * i + b2 * j + s2);
      return base + P * o1[L1] + Q * o2[L2];
    }),
  );
  return { cells, sum: 5 * base + 10 * P + 10 * Q };
}

// One square i of the props: its drawn numbers, cell order and 50 reserved draws (always, typed or not, so that the
// squares after it stay as they were), then either its typed cells solved or its drawn given cells picked.
function squareOf(p: MagischesQuadratProps, i: number, next: () => number): Square {
  const n = p.size;
  const N = n * n;
  const drawn = n === 3 ? magic3(p.max, next) : magic5(p.max, next);
  const order = shuffle(range(N), next);
  const reserve = Array.from({ length: 50 }, () => next());
  // The free-cell draws of solve: a generator seeded by the reserve, so that its tries never replay the same numbers.
  const draw = rng(Math.floor(reserve[0] * 2 ** 31));
  const typed = (p.typed ?? []).filter(([s, r, c]) => s === i && r <= n && c <= n);
  if (typed.length) {
    const known: (number | null)[][] = range(n).map(() => Array(n).fill(null));
    const given = range(n).map(() => Array(n).fill(false));
    for (const [, r, c, v] of typed) {
      known[r - 1][c - 1] = v;
      given[r - 1][c - 1] = true;
    }
    const values = typed.map((t) => t[3]);
    const r = solve(known, null, {
      prefer: drawn.cells,
      next: draw,
      max: p.max,
      distinct: new Set(values).size === values.length,
    });
    const cells = r.kind === "none" ? range(n).map(() => Array(n).fill(0)) : r.cells;
    for (const [, rr, cc, v] of typed) cells[rr - 1][cc - 1] = v;
    return {
      size: n,
      cells,
      given,
      sum: r.kind === "none" ? 0 : r.sum,
      wrong: r.kind === "none",
      many: r.kind === "many",
    };
  }
  // The drawn given cells: a cell joins while it raises the rank, until the square is unique or given cells are picked.
  const sum = p.showSum ? drawn.sum : null;
  const known: (number | null)[][] = range(n).map(() => Array(n).fill(null));
  const at = (idx: number): [number, number] => [Math.floor(idx / n), idx % n];
  const picked: number[] = [];
  let rank = rankOf(known, sum);
  for (const idx of order) {
    if (picked.length >= p.given || rank === N + 1) break;
    const [r, c] = at(idx);
    known[r][c] = drawn.cells[r][c];
    const r2 = rankOf(known, sum);
    if (r2 > rank) {
      rank = r2;
      picked.push(idx);
    } else known[r][c] = null;
  }
  for (const idx of order) {
    if (picked.length >= p.given) break;
    if (picked.includes(idx)) continue;
    const [r, c] = at(idx);
    known[r][c] = drawn.cells[r][c];
    picked.push(idx);
  }
  return {
    size: n,
    cells: drawn.cells,
    given: known.map((row) => row.map((v) => v !== null)),
    sum: drawn.sum,
    wrong: false,
    many: rankOf(known, sum) < N + 1,
  };
}

// The squares of the settings. Same settings, same squares; a memo of 50 keeps the last ones.
const memo = new Map<string, Made>();

export function made(props: MagischesQuadratProps): Made {
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
