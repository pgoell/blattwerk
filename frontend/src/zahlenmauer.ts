// The Zahlenmauer: the numbers of each wall and which stones show theirs. A pure function of the block's settings
// and its seed, so the editor, the thumbnail and the PDF draw the same walls.
import type { Typed, ZahlenmauerProps } from "./sheet";

// A wall: every stone's number by stone index, and whether the stone shows it. `wrong` says the numbers the teacher
// typed allow no wall.
export type Wall = { numbers: number[]; given: boolean[]; wrong: boolean };
// What gives more walls when fewer fit than asked for: a larger Zahlenraum, fewer base stones.
export type Loosen = "max" | "base";
export type Made = { walls: Wall[]; loosen: Loosen[] };

// How many stones a wall with `base` stones in its lowest row has.
export const stones = (base: number) => (base * (base + 1)) / 2;
// The index of a stone: rows count from the bottom, row 0 is the base row, and a row runs from the left.
export const at = (base: number, row: number, col: number) => row * base - (row * (row - 1)) / 2 + col;

// The settings as a wall can take them, whatever a stored sheet holds.
export function sane(p: ZahlenmauerProps): ZahlenmauerProps {
  const base = p.base === 4 || p.base === 5 ? p.base : 3;
  const n = stones(base);
  const free = Array.isArray(p.free) && p.free.length === n && p.free.every((f) => typeof f === "boolean") ? p.free : Array.from({ length: n }, (_, i) => i < base);
  const count = Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : 4;
  const typed = new Map<string, Typed>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [w, s, v] = t;
      if (w < 0 || w >= count || s < 0 || s >= n || v < 0 || v > 9999) continue;
      typed.delete(`${w}:${s}`);
      typed.set(`${w}:${s}`, [w, s, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    base,
    count,
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 4 ? p.columns : 2,
    max: [10, 20, 100, 1000].includes(p.max) ? p.max : 20,
    op: p.op === "*" ? "*" : "+",
    given: p.given === "mix" || p.given === "free" ? p.given : "base",
    free,
    empty: p.empty === true,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// A fraction, as [numerator, denominator] with the denominator above 0 and no common factor.
type Fr = [number, number];
const gcd = (a: number, b: number): number => (b ? gcd(b, a % b) : Math.abs(a));
const frac = (n: number, d = 1): Fr => {
  const s = d < 0 ? -1 : 1;
  const g = gcd(n, d) || 1;
  return [(s * n) / g || 0, (s * d) / g];
};
const add = (x: Fr, y: Fr): Fr => frac(x[0] * y[1] + y[0] * x[1], x[1] * y[1]);
const mul = (x: Fr, y: Fr): Fr => frac(x[0] * y[0], x[1] * y[1]);
const div = (x: Fr, y: Fr): Fr => frac(x[0] * y[1], x[1] * y[0]);
const neg = (x: Fr): Fr => [-x[0], x[1]];

// The binomial coefficient, for the rows of a stone over the base stones.
const binom = (n: number, k: number): number => (k === 0 ? 1 : (binom(n - 1, k - 1) * n) / k);

// The base row each stone sits over, as [row, col] by stone index.
const cells = (base: number): [number, number][] => {
  const out: [number, number][] = [];
  for (let r = 0; r < base; r++) for (let c = 0; c < base - r; c++) out.push([r, c]);
  return out;
};

// The row of a stone over the base stones: stone (r, c) is the sum over j of C(r, j) times base stone (c + j).
const vector = (base: number, i: number): number[] => {
  const v: number[] = Array.from({ length: base }, () => 0);
  const [r, c] = cells(base)[i];
  for (let j = 0; j <= r; j++) v[c + j] += binom(r, j);
  return v;
};

// Gauss-Jordan elimination over exact fractions: the rank of the rows, and when the rank is `n` and the right sides
// agree with it, the one solution.
function solve(n: number, rows: number[][], rhs: number[]): { rank: number; ok: boolean; x?: Fr[] } {
  const m: Fr[][] = rows.map((r, i) => [...r.map((v): Fr => [v, 1]), [rhs[i], 1]]);
  let rank = 0;
  for (let col = 0; col < n && rank < m.length; col++) {
    const p = m.findIndex((row, i) => i >= rank && row[col][0] !== 0);
    if (p < 0) continue;
    [m[rank], m[p]] = [m[p], m[rank]];
    const piv = m[rank][col];
    m[rank] = m[rank].map((v) => div(v, piv));
    for (let i = 0; i < m.length; i++) {
      if (i === rank || m[i][col][0] === 0) continue;
      const f = m[i][col];
      m[i] = m[i].map((v, k) => add(v, neg(mul(f, m[rank][k]))));
    }
    rank++;
  }
  const ok = m.slice(rank).every((row) => row[n][0] === 0);
  if (!ok || rank < n) return { rank, ok };
  return { rank, ok, x: m.slice(0, n).map((row) => row[n]) };
}

// The rank of some rows over `n` base stones.
const rankOf = (n: number, rows: number[][]): number => solve(n, rows, rows.map(() => 0)).rank;

// True when the given stones allow exactly one wall: their rows over the base stones have rank `base`. The same holds
// for times, since the numbers there are 1 or more.
export function fixes(base: number, given: boolean[]): boolean {
  const rows: number[][] = [];
  for (let i = 0; i < stones(base); i++) if (given[i]) rows.push(vector(base, i));
  return rankOf(base, rows) === base;
}

// The numbers of a wall from its base row, by the wall rule.
const build = (base: number, row: number[], times: boolean): number[] => {
  const numbers = [...row];
  for (let r = 1; r < base; r++) for (let c = 0; c < base - r; c++) {
    const a = numbers[at(base, r - 1, c)];
    const b = numbers[at(base, r - 1, c + 1)];
    numbers.push(times ? a * b : a + b);
  }
  return numbers;
};

// A seeded generator of numbers from 0 up to 1: mulberry32, as `rng` in suchsel.ts.
export function rng(seed: number) {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = ((t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t) | 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// The smallest a base stone may be: 0 only where no wall without a 0 fits (plus), else 1.
const floorOf = (p: ZahlenmauerProps): number => (p.op === "+" && p.max < 2 ** (p.base - 1) ? 0 : 1);

// Whether a base row gives a wall that fits the Zahlenraum: its top is at least 1 and at most max.
const fits = (p: ZahlenmauerProps, row: number[]): boolean => {
  const top = build(p.base, row, p.op === "*").at(-1) as number;
  return top >= 1 && top <= p.max && row.every((v) => v <= p.max);
};

// The base rows that fit, in a fixed order, up to 2000. A row whose lowest stones are already too big cuts its loop.
function listRows(p: ZahlenmauerProps, lo: number): number[][] {
  const out: number[][] = [];
  const row: number[] = [];
  const walk = (j: number) => {
    if (j === p.base) {
      if (fits(p, row)) out.push([...row]);
      return;
    }
    for (let v = lo; v <= p.max && out.length < 2000; v++) {
      row.push(v);
      const low = [...row, ...Array.from({ length: p.base - j - 1 }, () => lo)];
      if ((build(p.base, low, p.op === "*").at(-1) as number) > p.max) {
        row.pop();
        break;
      }
      walk(j + 1);
      row.pop();
    }
  };
  walk(0);
  return out;
}

// A base row drawn at random, each stone within the range that could still fit.
function drawRow(p: ZahlenmauerProps, lo: number, next: () => number): number[] {
  const times = p.op === "*";
  return Array.from({ length: p.base }, (_, j) => {
    const C = binom(p.base - 1, j);
    let hi: number;
    if (times) {
      hi = lo;
      while ((hi + 1) ** C <= p.max) hi++;
    } else {
      hi = Math.floor((p.max - lo * (2 ** (p.base - 1) - C)) / C);
    }
    // Times draw on a log scale, so the products mostly fit.
    if (times) return Math.min(hi, Math.floor(Math.exp(next() * Math.log(hi + 1))));
    return lo + Math.floor(next() * (hi - lo + 1));
  });
}

// Whether the given stones fill in the whole wall step by step: a stone with two of the three of its triangle known
// gives the third, until all are known.
function solvable(base: number, known: boolean[]): boolean {
  const k = [...known];
  let changed = true;
  while (changed) {
    changed = false;
    for (let r = 1; r < base; r++) for (let c = 0; c < base - r; c++) {
      const three = [at(base, r, c), at(base, r - 1, c), at(base, r - 1, c + 1)];
      if (three.filter((i) => k[i]).length !== 2) continue;
      k[three.find((i) => !k[i]) as number] = true;
      changed = true;
    }
  }
  return k.every(Boolean);
}

// The given stones of a wall with "mix": `base` stones, not all in the base row, solvable step by step.
function pattern(p: ZahlenmauerProps, next: () => number): boolean[] {
  const n = stones(p.base);
  for (let tries = 0; tries < 200; tries++) {
    const pick = new Set<number>();
    while (pick.size < p.base) pick.add(Math.floor(next() * n));
    const given = Array.from({ length: n }, (_, i) => pick.has(i));
    if ([...pick].some((i) => i >= p.base) && solvable(p.base, given)) return given;
  }
  // The base row but the last stone, and the stone above the last two: solvable, and not all in the base row.
  return Array.from({ length: n }, (_, i) => i < p.base - 1 || i === at(p.base, 1, p.base - 2));
}

// The prime factors of a number, each once.
const primesOf = (n: number): number[] => {
  const out: number[] = [];
  for (let d = 2; d * d <= n; d++) if (n % d === 0) {
    out.push(d);
    while (n % d === 0) n /= d;
  }
  if (n > 1) out.push(n);
  return out;
};

// How often the prime p divides n.
const exponent = (n: number, p: number): number => {
  let e = 0;
  for (; n % p === 0; n /= p) e++;
  return e;
};

// The numbers of a wall with typed stones: the typed ones, then the generated base stones from the left that raise the
// rank, solved exactly. Times are solved per prime, a plus wall over the exponents. `wrong` when the typed numbers
// contradict each other or some stone comes out not whole, below 0 (plus) or below 1 (times).
function over(p: ZahlenmauerProps, generated: number[], typed: Map<number, number>): { numbers: number[]; wrong: boolean } {
  const base = p.base;
  const times = p.op === "*";
  const shown = { numbers: generated.map((v, i) => (typed.has(i) ? (typed.get(i) as number) : v)), wrong: true };
  if (times && [...typed.values()].includes(0)) return shown;
  const used: number[] = [...typed.keys()];
  const rows = used.map((i) => vector(base, i));
  for (let j = 0; j < base; j++) {
    if (typed.has(j)) continue;
    const e = vector(base, j);
    if (rankOf(base, [...rows, e]) > rankOf(base, rows)) {
      used.push(j);
      rows.push(e);
    }
  }
  const valueOf = (i: number) => typed.get(i) ?? generated[i];
  const greedy = derive(p, typed, used, rows, valueOf);
  if (greedy) return { numbers: greedy, wrong: false };
  // The greedy fill gave no wall: search the base stones for one that fits the typed numbers.
  // A base stone in no typed stone keeps its number, unless only a smaller one keeps every stone within 9999: the
  // smallest it may be makes every stone over it as small as it gets.
  const found = search(p, typed, generated) ?? search(p, typed, generated.map((v, j) => (j < base ? (times ? 1 : 0) : v)));
  return found ? { numbers: found, wrong: false } : shown;
}

// A depth-first search over the base stones for a wall that holds every typed number, in integers only. A base stone in
// no typed stone keeps its generated value. Undefined when no wall fits, or after 100000 nodes.
function search(p: ZahlenmauerProps, typed: Map<number, number>, generated: number[]): number[] | undefined {
  const base = p.base;
  const times = p.op === "*";
  // The teacher's own wall may hold a 0 where plus allows it.
  const floor = times ? 1 : 0;
  const cons = [...typed].map(([i, v]) => ({ v, a: vector(base, i) }));
  const searched = Array.from({ length: base }, (_, j) => j).filter((j) => cons.some((c) => c.a[j] > 0));
  const x = generated.slice(0, base);
  const assigned = Array.from({ length: base }, () => false);
  let visited = 0;
  let result: number[] | undefined;

  // The assigned part of a constraint (sum, or product), and the stones of it not yet assigned.
  const part = (c: { v: number; a: number[] }) => {
    let s = times ? 1 : 0;
    const open: number[] = [];
    for (let j = 0; j < base; j++) {
      if (c.a[j] === 0) continue;
      if (!assigned[j]) {
        open.push(j);
        continue;
      }
      for (let k = 0; k < c.a[j]; k++) {
        s = times ? s * x[j] : s + x[j];
        if (times && s > c.v) return { s, open };
      }
    }
    return { s, open };
  };

  // The stone m that is the only open one of a constraint must be this: plus (v - sum) / a, times the a-th root of v / product.
  const forced = (c: { v: number; a: number[] }, m: number, s: number): number | undefined => {
    if (!times) {
      const rem = c.v - s;
      if (rem < 0 || rem % c.a[m] !== 0) return undefined;
      return rem / c.a[m];
    }
    if (c.v % s !== 0) return undefined;
    const rem = c.v / s;
    const r = Math.round(rem ** (1 / c.a[m]));
    for (let y = Math.max(1, r - 1); y <= r + 1; y++) {
      let pw = 1;
      for (let k = 0; k < c.a[m]; k++) pw *= y;
      if (pw === rem) return y;
    }
    return undefined;
  };

  // The values to try for stone j, the generated one first, then by distance from it.
  function* candidates(j: number): Generator<number> {
    const mine = cons.filter((c) => c.a[j] > 0);
    const g = generated[j];
    if (times) {
      let G = 0;
      for (const c of mine) G = gcd(G, c.v);
      const divs: number[] = [];
      for (let d = 1; d * d <= G; d++) if (G % d === 0) divs.push(d, G / d);
      divs.sort((p1, p2) => Math.abs(p1 - g) - Math.abs(p2 - g) || p1 - p2);
      yield* divs;
      return;
    }
    const u = Math.min(...mine.map((c) => c.v));
    for (let d = 0; d <= Math.max(u, g) + 1; d++) {
      for (const y of d === 0 ? [g] : [g - d, g + d]) if (y >= floor && y <= u) yield y;
    }
  }

  const fullCheck = (): boolean => {
    const wall = build(base, x, times);
    if (wall.some((v) => v > 9999)) return false;
    if ([...typed].some(([i, v]) => wall[i] !== v)) return false;
    result = wall;
    return true;
  };

  const dfs = (depth: number): boolean => {
    if (++visited > 100000) return false;
    if (depth === searched.length) return fullCheck();
    const j = searched[depth];
    const mine = cons.filter((c) => c.a[j] > 0);
    let domain: Iterable<number> = candidates(j);
    for (const c of mine) {
      const { s, open } = part(c);
      if (open.length === 1 && open[0] === j) {
        const f = forced(c, j, s);
        if (f === undefined || f < floor) return false;
        domain = [f];
        break;
      }
    }
    for (const y of domain) {
      x[j] = y;
      assigned[j] = true;
      const ok = mine.every((c) => {
        const { s, open } = part(c);
        if (times ? c.v % s !== 0 : s > c.v) return false;
        return open.length > 0 || s === c.v;
      });
      if (ok && dfs(depth + 1)) return true;
      assigned[j] = false;
    }
    return false;
  };

  return dfs(0) ? result : undefined;
}

// The numbers of a wall from the rows of its constrained stones and the value of each: solved exactly, then checked.
// Undefined when the stones are not whole, below 0 (plus) or below 1 (times), above 9999, or contradict the typed ones.
function derive(p: ZahlenmauerProps, typed: Map<number, number>, used: number[], rows: number[][], valueOf: (i: number) => number): number[] | undefined {
  const base = p.base;
  const n = stones(base);
  // The value of a stone from the solved base stones x: its row times x, which must be whole and 0 or more.
  const of = (x: Fr[], i: number): number | undefined => {
    const [r, c] = cells(base)[i];
    let s: Fr = [0, 1];
    for (let j = 0; j <= r; j++) s = add(s, mul(x[c + j], [binom(r, j), 1]));
    return s[1] === 1 && s[0] >= 0 ? s[0] : undefined;
  };
  const out = Array.from({ length: n }, () => 1);
  if (p.op !== "*") {
    const res = solve(base, rows, used.map(valueOf));
    if (!res.ok || !res.x) return undefined;
    for (let i = 0; i < n; i++) {
      const v = of(res.x, i);
      if (v === undefined) return undefined;
      out[i] = v;
    }
  } else {
    const primes = new Set<number>();
    for (const i of used) for (const q of primesOf(valueOf(i))) primes.add(q);
    for (const q of primes) {
      const res = solve(base, rows, used.map((i) => exponent(valueOf(i), q)));
      if (!res.ok || !res.x) return undefined;
      for (let i = 0; i < n; i++) {
        const e = of(res.x, i);
        if (e === undefined) return undefined;
        out[i] *= q ** e;
        if (!Number.isSafeInteger(out[i])) return undefined;
      }
    }
  }
  if (out.some((v) => v > 9999)) return undefined;
  if ([...typed].some(([i, v]) => out[i] !== v)) return undefined;
  return out;
}

// The walls of sane settings and what to loosen. The same settings give the same walls on every call.
function lay(p: ZahlenmauerProps): Made {
  const next = rng(p.seed);
  const lo = floorOf(p);
  const list = listRows(p, lo);
  let rows: number[][];
  if (list.length < 2000) {
    for (let i = list.length - 1; i > 0; i--) {
      const j = Math.floor(next() * (i + 1));
      [list[i], list[j]] = [list[j], list[i]];
    }
    rows = list.slice(0, p.count);
  } else {
    rows = [];
    const seen = new Set<string>();
    while (rows.length < p.count) {
      const row = drawRow(p, lo, next);
      const key = row.join(",");
      if (!fits(p, row) || seen.has(key)) continue;
      seen.add(key);
      rows.push(row);
    }
  }
  const walls = rows.map((row, w): Wall => {
    const generated = build(p.base, row, p.op === "*");
    const typed = new Map<number, number>();
    for (const [tw, s, v] of p.typed ?? []) if (tw === w) typed.set(s, v);
    const given = p.given === "mix" ? pattern(p, next) : p.given === "free" ? [...(p.free as boolean[])] : Array.from({ length: stones(p.base) }, (_, i) => i < p.base);
    const shown = typed.size ? over(p, generated, typed) : { numbers: generated, wrong: false };
    return { numbers: shown.numbers, given, wrong: shown.wrong };
  });
  const loosen: Loosen[] = [];
  if (walls.length < p.count) {
    if (p.max !== 1000) loosen.push("max");
    if (p.base !== 3) loosen.push("base");
  }
  return { walls, loosen };
}

// The Zahlenmauer's walls and what to loosen. The same settings give the same walls on every call.
const memo = new Map<string, Made>();

export function made(props: ZahlenmauerProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const out = lay(p);
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}
