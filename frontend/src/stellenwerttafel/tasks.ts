// The moves of a number, the rule a number keeps, and the drawn tasks of a Stellenwerttafel.
import { rng } from "../zahlenmauer";
import { DEFAULTS, placesOf, sane } from "./props";
import type { Made, StellenwerttafelProps, Task } from "./props";

const valuesOf = (max: number): number[] => placesOf({ ...DEFAULTS, seed: 0, max }).map((pl) => pl.v);
const digitsOf = (n: number, vs: number[]): number[] => vs.map((v) => Math.floor(n / v) % 10);

// The numbers one dot away: a dot from column i to column j, where column i holds a dot and column j at most 8.
export function moves(n: number, max: number): number[] {
  const vs = valuesOf(max);
  const d = digitsOf(n, vs);
  const out: number[] = [];
  vs.forEach((vi, i) => {
    if (d[i] < 1) return;
    vs.forEach((vj, j) => {
      if (j !== i && d[j] <= 8) out.push(n - vi + vj);
    });
  });
  return out.sort((a, b) => a - b);
}

// v keeps the rule: 1 ≤ v < max, its digit sum at most `dots`, and with "move" at least one move. Not `zero`.
export function fits(p: StellenwerttafelProps, v: number): boolean {
  const s = sane(p);
  if (v < 1 || v >= s.max) return false;
  const sum = digitsOf(v, valuesOf(s.max)).reduce((a, b) => a + b, 0);
  if (sum > s.dots) return false;
  return s.task !== "move" || moves(v, s.max).length > 0;
}

// P, the numbers a drawn task may take: one plain loop in rising order, kept per setting.
const poolMemo = new Map<string, number[]>();

function pool(p: StellenwerttafelProps): number[] {
  const key = JSON.stringify([p.max, p.task, p.dots, p.zero]);
  const old = poolMemo.get(key);
  if (old) return old;
  const vs = valuesOf(p.max);
  const P: number[] = [];
  for (let n = 1; n <= p.max - 1; n++) {
    const d = digitsOf(n, vs);
    if (d.reduce((a, b) => a + b, 0) > p.dots) continue;
    if (!p.zero && d.includes(0)) continue;
    if (p.task === "move" && moves(n, p.max).length === 0) continue;
    P.push(n);
  }
  poolMemo.set(key, P);
  if (poolMemo.size > 50) poolMemo.delete(poolMemo.keys().next().value as string);
  return P;
}

const madeMemo = new Map<string, Made>();

export function made(props: StellenwerttafelProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = madeMemo.get(key);
  if (old) return old;
  const vs = valuesOf(p.max);
  const P = pool(p);
  const none = P.length === 0;
  const next = rng(p.seed);
  const seen = new Set<number>();
  const taskOf = (n: number): Task => ({
    n,
    digits: digitsOf(n, vs),
    moves: p.task === "move" ? moves(n, p.max) : [],
    wrong: false,
    none: false,
  });
  const blank = (wrong: boolean, isNone: boolean): Task => ({
    n: 0,
    digits: vs.map(() => 0),
    moves: [],
    wrong,
    none: isNone,
  });
  const tasks: Task[] = [];
  for (let i = 0; i < p.count; i++) {
    let n = 0;
    if (!none) {
      for (let t = 0; t < 20; t++) {
        n = P[Math.floor(next() * P.length)];
        if (!seen.has(n)) break;
      }
      seen.add(n);
    }
    const mine = p.typed?.find(([j]) => j === i);
    if (mine) tasks.push(fits(p, mine[1]) ? taskOf(mine[1]) : blank(true, false));
    else tasks.push(none ? blank(false, true) : taskOf(n));
  }
  const out: Made = { tasks, none };
  madeMemo.set(key, out);
  if (madeMemo.size > 50) madeMemo.delete(madeMemo.keys().next().value as string);
  return out;
}
