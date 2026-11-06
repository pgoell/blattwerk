// The Stellenwerttafel generator, checked by an oracle of plain loops that takes nothing from the model but `made` and
// `sane`: every drawn task fits the rule, a typed number fits or gives a wrong task as the oracle says, and the other
// tasks keep their numbers when one is typed.
import { describe, expect, it } from "vitest";
import { made, sane, type StellenwerttafelProps, type StellenwerttafelTyped, type Task } from "./stellenwerttafel";

const MAXES = [1000, 10000];
const TASK_NAMES = ["read", "lay", "move"];
const DOTS = Array.from({ length: 36 }, (_, i) => i + 1);
const ZEROS = [false, true];
const SEEDS = [1, 2, 3];
const COUNT = 12;
// The oracle's own table: place values, highest place first.
const PV: Record<number, number[]> = { 1000: [100, 10, 1], 10000: [1000, 100, 10, 1] };

// A fixed Park-Miller generator, for the typed numbers.
function lcg(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 48271) % 2147483647;
    return s / 2147483647;
  };
}

// The four digits of every n from 0 to 9999 (highest first) and their sums: built once.
const DIG: number[][] = [];
const DSUM: number[] = [];
for (let n = 0; n < 10000; n++) {
  const d = [Math.floor(n / 1000) % 10, Math.floor(n / 100) % 10, Math.floor(n / 10) % 10, n % 10];
  DIG.push(d);
  DSUM.push(d[0] + d[1] + d[2] + d[3]);
}

// The digits of n in the Zahlenraum's columns: three for bis 1000 (the thousands digit is 0 there).
function digitsOf(n: number, max: number): number[] {
  return max === 1000 ? DIG[n].slice(1) : DIG[n];
}

// The moves of n, by plain loops: a dot leaves column i and goes to column j (d[j] at most 8); the numbers rising, once each.
function movesOracle(n: number, max: number): number[] {
  const vs = PV[max];
  const k = vs.length;
  const d = digitsOf(n, max);
  const found = new Set<number>();
  for (let i = 0; i < k; i++) {
    if (d[i] < 1) continue;
    for (let j = 0; j < k; j++) {
      if (j === i || d[j] > 8) continue;
      let m = 0;
      for (let c = 0; c < k; c++) {
        const dc = c === i ? d[c] - 1 : c === j ? d[c] + 1 : d[c];
        m += dc * vs[c];
      }
      found.add(m);
    }
  }
  return [...found].sort((a, b) => a - b);
}

// MOVES[max][n] for every n below max, built once.
const MOVES: Record<number, number[][]> = { 1000: [], 10000: [] };
for (const max of MAXES) for (let n = 0; n < max; n++) MOVES[max][n] = movesOracle(n, max);

// The numbers a drawn task may show for a Zahlenraum, a type and a dots limit: 1 to max - 1, every column a dot when
// zero is off, digit sum at most dots, and a move when the type is "move". Memoised per setting.
const SETS = new Map<string, number[]>();
function drawable(max: number, task: string, dots: number, zero: boolean): number[] {
  const key = [max, task, dots, zero].join("|");
  const hit = SETS.get(key);
  if (hit) return hit;
  const out: number[] = [];
  for (let n = 1; n < max; n++) {
    const d = digitsOf(n, max);
    if (!zero && d.includes(0)) continue;
    if (DSUM[n] > dots) continue;
    if (task === "move" && MOVES[max][n].length === 0) continue;
    out.push(n);
  }
  SETS.set(key, out);
  return out;
}

// The digits and moves of a task with its n set: the oracle's digits of n, digit sum within dots, the oracle's moves.
function shapeErrors(max: number, task: string, dots: number, t: Task): string[] {
  const errs: string[] = [];
  const want = digitsOf(t.n, max);
  if (t.digits.length !== PV[max].length) errs.push(`digits length ${t.digits.length}`);
  if (JSON.stringify(t.digits) !== JSON.stringify(want)) errs.push(`digits ${t.digits.join()} not ${want.join()}`);
  if (t.digits.reduce((a, x) => a + x, 0) > dots) errs.push(`digit sum over ${dots}`);
  const wantMoves = task === "move" ? MOVES[max][t.n] : [];
  if (JSON.stringify(t.moves) !== JSON.stringify(wantMoves)) errs.push(`moves ${t.moves.join()} not ${wantMoves.join()}`);
  return errs;
}

// A task that shows nothing: n 0, no dot, no move, not wrong.
function emptyErrors(t: Task): string[] {
  const errs: string[] = [];
  if (!t.none) errs.push("not none");
  if (t.wrong) errs.push("wrong");
  if (t.n !== 0 || t.digits.some((x) => x !== 0) || t.moves.length !== 0) errs.push("not empty");
  return errs;
}

// A misfit typed task: wrong, n 0, no dot, no move.
function misfitErrors(t: Task): string[] {
  const errs: string[] = [];
  if (!t.wrong) errs.push("should be wrong");
  if (t.none) errs.push("none");
  if (t.n !== 0 || t.digits.some((x) => x !== 0) || t.moves.length !== 0) errs.push("not empty");
  return errs;
}

// One test per Zahlenraum, type and six dots, so that each stays under 2 s (made costs more with more dots).
const DOT_GROUPS = [0, 6, 12, 18, 24, 30].map((a) => DOTS.slice(a, a + 6));
describe("drawn tasks", () => {
  for (const max of MAXES)
    for (const task of TASK_NAMES)
      for (const group of DOT_GROUPS)
        it(`max ${max} ${task} dots ${group[0]} to ${group[5]}: the drawn tasks are oracle numbers with the oracle's digits and moves`, () => {
    const bad: string[] = [];
    let drawn = 0;
    let wrong = 0;
        for (const dots of group)
          for (const zero of ZEROS) {
            const set = drawable(max, task, dots, zero);
            const ok = new Set(set);
            for (const seed of SEEDS) {
              const p: StellenwerttafelProps = { count: COUNT, columns: 3, max, task, dots, zero, seed } as StellenwerttafelProps;
              const label = `max ${max} ${task} dots ${dots} zero ${zero} seed ${seed}`;
              const m = made(p);
              if (set.length === 0) {
                if (!m.none) bad.push(`${label}: none false`);
                m.tasks.forEach((t, i) => bad.push(...emptyErrors(t).map((e) => `${label} task ${i}: ${e}`)));
                continue;
              }
              if (m.none) bad.push(`${label}: none true with ${set.length} numbers`);
              m.tasks.forEach((t, i) => {
                if (t.wrong) {
                  wrong++;
                  bad.push(`${label} task ${i}: wrong`);
                  return;
                }
                drawn++;
                if (t.none) {
                  bad.push(`${label} task ${i}: none`);
                  return;
                }
                if (!ok.has(t.n)) {
                  bad.push(`${label} task ${i}: n ${t.n} not in the oracle set`);
                  return;
                }
                bad.push(...shapeErrors(max, task, dots, t).map((e) => `${label} task ${i}: ${e}`));
              });
            }
          }
    expect(drawn).toBeGreaterThan(0);
    expect({ wrong, falseKeys: bad.length }).toEqual({ wrong: 0, falseKeys: 0 });
    expect(bad.slice(0, 5)).toEqual([]);
  });
});

// One test per Zahlenraum and type. Per setting: every task typed at once, then one typed task (task 0 and one random
// index) with every other task checked to stay as it was without typed numbers.
describe("typed numbers", () => {
  for (const max of MAXES)
    for (const task of TASK_NAMES)
      for (const group of DOT_GROUPS)
        it(`max ${max} ${task} dots ${group[0]} to ${group[5]}: a typed task fits or is wrong as the oracle says, the other tasks keep their numbers`, () => {
        const rnd = lcg(4242);
        const SPECIAL = [306, 3065, 999, 9999, 45, 0, 1];
        const bad: string[] = [];
        let fits = 0;
        let misses = 0;
        // A fit gives n v and the oracle's digits and moves; a misfit gives a wrong empty task.
        const check = (label: string, dots: number, v: number, t: Task) => {
          const fitsV = v >= 1 && v < max && DSUM[v] <= dots && (task !== "move" || MOVES[max][v].length > 0);
          if (fitsV) {
            fits++;
            const errs = t.wrong || t.none || t.n !== v ? [`n ${t.n} for ${v}`] : shapeErrors(max, task, dots, t);
            bad.push(...errs.map((e) => `${label}: ${e}`));
          } else {
            misses++;
            bad.push(...misfitErrors(t).map((e) => `${label}: ${e}`));
          }
        };
        for (const dots of group)
          for (const zero of ZEROS) {
            const base: StellenwerttafelProps = { count: COUNT, columns: 3, max, task, dots, zero, seed: 1 } as StellenwerttafelProps;
            const plain = made(base).tasks;
            const vals = [...SPECIAL];
            while (vals.length < COUNT) vals.push(rnd() < 0.5 ? Math.floor(rnd() * 10000) : Math.floor(rnd() * max));
            const label = `dots ${dots} zero ${zero}`;
            const all: StellenwerttafelTyped[] = vals.slice(0, COUNT).map((v, i) => [i, v]);
            made({ ...base, typed: all }).tasks.forEach((t, i) => check(`${label} all typed task ${i} value ${vals[i]}`, dots, vals[i], t));
            for (const i of [0, Math.floor(rnd() * COUNT)]) {
              const tasks = made({ ...base, typed: [[i, vals[i]]] }).tasks;
              tasks.forEach((t, j) => {
                if (j === i) check(`${label} typed ${vals[i]} on ${i}`, dots, vals[i], t);
                else if (JSON.stringify(t) !== JSON.stringify(plain[j])) bad.push(`${label} typed ${vals[i]} on ${i}: task ${j} changed`);
              });
            }
          }
        expect(fits).toBeGreaterThan(0);
        expect(misses).toBeGreaterThan(0);
        expect(bad.slice(0, 5)).toEqual([]);
        expect(bad.length).toBe(0);
      });
});

describe("determinism and sane", () => {
  it("the same props give the same tasks, typed or not", () => {
    const p: StellenwerttafelProps = { count: 12, columns: 3, max: 10000, task: "move", dots: 9, zero: false, seed: 7, typed: [[2, 3065]] } as StellenwerttafelProps;
    const copy: StellenwerttafelProps = JSON.parse(JSON.stringify(p));
    expect(made(copy)).toEqual(made(p));
    expect(made(p)).toEqual(made(p));
  });

  it("sane gives defaults for odd values and drops bad typed entries", () => {
    const odd = { count: 0, columns: 2, max: 500, task: "x", dots: 0, zero: false, seed: 1 } as unknown as StellenwerttafelProps;
    const s = sane(odd);
    expect([s.count, s.max, s.task, s.dots]).toEqual([4, 1000, "read", 9]);
    expect(sane({ ...odd, count: 3, max: 1000, task: "read", dots: 37 }).dots).toBe(9);

    const raw = {
      count: 4, columns: 2, max: 1000, task: "read", dots: 9, zero: false, seed: 1,
      typed: [[0, 306], [0, 7], [11, 5], [12, 5], [3, -1], [4, 10000], [5, 1.5], [6, 2]],
    } as unknown as StellenwerttafelProps;
    expect([...(sane(raw).typed ?? [])].sort((a, b) => a[0] - b[0])).toEqual([[0, 7], [6, 2], [11, 5]]);
    expect(((sane({ ...raw, typed: [[12, 5]] } as unknown as StellenwerttafelProps).typed) ?? [])).toEqual([]);
  });
});

describe("306", () => {
  it("306 fits with zero off and writes 3, 0, 6; 3065 bis 1000 does not fit", () => {
    const p: StellenwerttafelProps = { count: 2, columns: 2, max: 1000, task: "read", dots: 9, zero: false, seed: 3, typed: [[0, 306]] } as StellenwerttafelProps;
    const [t] = made(p).tasks;
    expect(t.wrong).toBe(false);
    expect(t.n).toBe(306);
    expect(t.digits).toEqual([3, 0, 6]);
    const [w] = made({ ...p, typed: [[0, 3065]] }).tasks;
    expect(w.wrong).toBe(true);
  });
});
