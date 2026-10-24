// The numbers of one Malquadrat: each typed cell is an equation over the row and column numbers, and a search finds them.
import type { MalquadratProps, Square } from "../malquadrat";

export const range = (n: number) => Array.from({ length: n }, (_, i) => i);

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
export function squareOf(p: MalquadratProps, i: number, next: () => number): Square {
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
