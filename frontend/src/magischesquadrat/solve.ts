// A magic square's line sums, solved by elimination, and one drawn square's given cells.
import { rng } from "../zahlenmauer";
import type { MagischesQuadratProps, Square } from "../magischesquadrat";

// What `solve` finds for a square of size n from its known cells (known[r][c], null where not known) and, when it is
// known, the Zielzahl: "none" no magic square in whole numbers has them; "one" exactly one, `cells`; "many" more than
// one, `cells` one of them (the free cells take `prefer`'s numbers where those give whole numbers from 0 to 9999, else
// the draws of `next` from 1 to max, up to 50 tries; with `distinct` only a key with distinct numbers counts; no such
// key is "none"). The unknowns are the n² cells and the Zielzahl; the equations are the 2n + 2 line sums, solved by
// Gaussian elimination with a tolerance of 1e-6 (rank = number of unknowns is "one").
export type Solved = { kind: "none" } | { kind: "one" | "many"; cells: number[][]; sum: number };

const EPS = 1e-6;
export const range = (n: number) => Array.from({ length: n }, (_, i) => i);
const m5 = (x: number) => ((x % 5) + 5) % 5;

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
export function squareOf(p: MagischesQuadratProps, i: number, next: () => number): Square {
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
