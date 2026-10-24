// The pairs that keep a Zehnerfeld's rule, the dots of a pair, and a typed task's numbers.
import { rng } from "../zahlenmauer";
import { acts, sane } from "./props";
import type { Cross, Made, Task, ZehnerfeldProps } from "./props";

export function crosses(op: "+" | "-", a: number, b: number): boolean {
  const x = op === "+" ? a : a - b;
  return (x % 10) + (b % 10) > 10;
}

export function picture(op: "+" | "-", a: number, b: number, C: number): number[] {
  const out = new Array<number>(C).fill(0);
  for (let k = 0; k < a && k < C; k++) out[k] = 1;
  if (op === "+") {
    for (let k = a; k < a + b && k < C; k++) out[k] = 2;
  } else {
    for (let k = a - b; k < a && k < C; k++) out[k] = 3;
  }
  return out;
}

// The teacher's own task: the drawn task when it fits the typed positions and the rule, else the solution of the
// smallest a and then the smallest b, by a plain walk; null when none fits.
export function solve(op: "+" | "-", known: (number | null)[], drawn: number[] | null, C: number): number[] | null {
  const result = (a: number, b: number): number | null => {
    if (a < 1 || a > C || b < 1 || b > C) return null;
    if (op === "+") return a + b <= C ? a + b : null;
    return b <= a ? a - b : null;
  };
  const matches = (v: number[]): boolean => known.every((x, i) => x === null || x === v[i]);
  if (drawn && result(drawn[0], drawn[1]) === drawn[2] && matches(drawn)) return [...drawn];
  for (let a = 1; a <= C; a++) {
    for (let b = 1; b <= C; b++) {
      const r = result(a, b);
      if (r !== null && matches([a, b, r])) return [a, b, r];
    }
  }
  return null;
}

// The pairs (a, b) that keep the rule, the Zahlenraum and the Zehnerübergang as they act, a first, then b, rising.
const pairsMemo = new Map<string, [number, number][]>();

function pairs(op: "+" | "-", C: number, M: number, cross: Cross): [number, number][] {
  // Only what decides which pairs fit: a stepper or a look change reuses the list.
  const key = JSON.stringify([op, C, M, cross]);
  const old = pairsMemo.get(key);
  if (old) return old;
  const out: [number, number][] = [];
  for (let a = 1; a <= M; a++) {
    for (let b = 1; b <= M; b++) {
      const valid = op === "+" ? a + b <= M : b <= a;
      if (!valid) continue;
      const cr = crosses(op, a, b);
      if ((cross === "yes" && !cr) || (cross === "no" && cr)) continue;
      out.push([a, b]);
    }
  }
  pairsMemo.set(key, out);
  if (pairsMemo.size > 50) pairsMemo.delete(pairsMemo.keys().next().value as string);
  return out;
}

const madeMemo = new Map<string, Made>();

export function made(props: ZehnerfeldProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = madeMemo.get(key);
  if (old) return old;
  const { C, M, cross } = acts(p);
  const P = pairs(p.op, C, M, cross);
  const none = P.length === 0;
  const next = rng(p.seed);
  const drawn: [number, number][] = [];
  const tasks: Task[] = [];
  const task = (kind: "dots" | "write", values: number[], wrong: boolean, empty: boolean): Task => {
    const ok = !wrong && !empty;
    return {
      values: ok ? values : [0, 0, 0],
      kind,
      dots: ok ? picture(p.op, values[0], values[1], C) : new Array<number>(C).fill(0),
      wrong,
      none: empty,
    };
  };
  for (let i = 0; i < p.count; i++) {
    let a = 0;
    let b = 0;
    if (!none) {
      for (let t = 0; t < 20; t++) {
        [a, b] = P[Math.floor(next() * P.length)];
        if (!drawn.some(([x, y]) => x === a && y === b)) break;
      }
      drawn.push([a, b]);
    }
    const kind = p.task === "mixed" ? (i % 2 === 0 ? "dots" : "write") : p.task;
    const mine = (p.typed ?? []).filter((e) => e[0] === i);
    if (mine.length === 0) {
      const r = p.op === "+" ? a + b : a - b;
      tasks.push(none ? task(kind, [0, 0, 0], false, true) : task(kind, [a, b, r], false, false));
      continue;
    }
    const known = [0, 1, 2].map((pos) => mine.find((e) => e[1] === pos)?.[2] ?? null);
    const r = p.op === "+" ? a + b : a - b;
    const res = solve(p.op, known, none ? null : [a, b, r], C);
    tasks.push(res ? task(kind, res, false, false) : task(kind, [0, 0, 0], true, false));
  }
  const out: Made = { tasks, none };
  madeMemo.set(key, out);
  if (madeMemo.size > 50) madeMemo.delete(madeMemo.keys().next().value as string);
  return out;
}
