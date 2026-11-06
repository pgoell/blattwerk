// The count tuples that keep a Stellenwert-Bild's rule, the drawn tasks, and a typed task's counts.
import { rng } from "../zahlenmauer";
import { placesOf, sane } from "./props";
import type { Made, StellenwertbildProps, Task } from "./props";

const valueOf = (counts: number[], vs: number[]): number => counts.reduce((s, c, k) => s + c * vs[k], 0);
const digitsOf = (n: number, vs: number[]): number[] => vs.map((v) => Math.floor(n / v) % 10);

// The count tuples that keep the rule and `zero` (null: the rule alone), by plain nested loops, the leading place
// outermost, each count rising from 0 (the leading one from 1) to 19; a tuple breaking the rule is dropped.
const tuplesMemo = new Map<string, number[][]>();

export function tuples(max: number, bundle: boolean, zero: boolean | null): number[][] {
  const key = JSON.stringify([max, bundle, zero]);
  const old = tuplesMemo.get(key);
  if (old) return old;
  const vs = max === 100 ? [10, 1] : [100, 10, 1];
  const out: number[][] = [];
  const consider = (counts: number[]) => {
    const n = valueOf(counts, vs);
    if (n >= max || counts[0] > 9) return;
    const tens = counts.slice(1).filter((c) => c >= 10).length;
    if (bundle ? tens !== 1 : tens !== 0) return;
    if (!bundle && counts.some((c) => c > 9)) return;
    const d = digitsOf(n, vs);
    if (zero === false && d.includes(0)) return;
    if (zero === true && !d.slice(1).includes(0)) return;
    out.push(counts);
  };
  if (max === 100) {
    for (let z = 1; z <= 19; z++) for (let e = 0; e <= 19; e++) consider([z, e]);
  } else {
    for (let h = 1; h <= 19; h++) for (let z = 0; z <= 19; z++) for (let e = 0; e <= 19; e++) consider([h, z, e]);
  }
  tuplesMemo.set(key, out);
  if (tuplesMemo.size > 50) tuplesMemo.delete(tuplesMemo.keys().next().value as string);
  return out;
}

// The teacher's own task: the drawn counts when their n is v, else the first tuple of the plain walk without the
// `zero` filter whose n is v; null when none fits.
export function solve(props: StellenwertbildProps, v: number, drawn: number[] | null): number[] | null {
  const p = sane(props);
  const vs = placesOf(p).map((pl) => pl.v);
  if (drawn && valueOf(drawn, vs) === v) return [...drawn];
  const hit = tuples(p.max, p.bundle, null).find((c) => valueOf(c, vs) === v);
  return hit ? [...hit] : null;
}

const madeMemo = new Map<string, Made>();

export function made(props: StellenwertbildProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = madeMemo.get(key);
  if (old) return old;
  const vs = placesOf(p).map((pl) => pl.v);
  const P = tuples(p.max, p.bundle, p.zero);
  const none = P.length === 0;
  const next = rng(p.seed);
  const seen = new Set<number>();
  const ok = (counts: number[]): Task => {
    const n = valueOf(counts, vs);
    return { counts: [...counts], n, digits: digitsOf(n, vs), wrong: false, none: false };
  };
  const empty = (isNone: boolean, wrong: boolean): Task => {
    const zeros = vs.map(() => 0);
    return { counts: zeros, n: 0, digits: zeros, wrong, none: isNone };
  };
  const tasks: Task[] = [];
  for (let i = 0; i < p.count; i++) {
    let counts: number[] = [];
    if (!none) {
      for (let t = 0; t < 20; t++) {
        counts = P[Math.floor(next() * P.length)];
        if (!seen.has(valueOf(counts, vs))) break;
      }
      seen.add(valueOf(counts, vs));
    }
    const mine = p.typed?.find(([j]) => j === i);
    if (!mine) {
      tasks.push(none ? empty(true, false) : ok(counts));
      continue;
    }
    const res = solve(p, mine[1], none ? null : counts);
    tasks.push(res ? ok(res) : empty(false, true));
  }
  const out: Made = { tasks, none };
  madeMemo.set(key, out);
  if (madeMemo.size > 50) madeMemo.delete(madeMemo.keys().next().value as string);
  return out;
}
