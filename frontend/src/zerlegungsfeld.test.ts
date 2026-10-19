// The Zerlegungsfeld generator: every drawn task keeps the rule, and `solve` agrees with a brute force oracle.
import { describe, expect, it } from "vitest";
import { rng } from "./zahlenmauer";
import {
  DEFAULTS,
  made,
  sane,
  solve,
  unit,
  type Task,
  type ZerlegungsfeldProps,
} from "./zerlegungsfeld";

const CAP = 1200;
const OPS = ["+", "-"] as const;
const MAX_LIST = [20, 100, 1000];
const STEPS = ["zehner", "hunderter"] as const;
const TASKS = ["task", "split", "result"] as const;

// The unit, written out again for the test (not the generator's `unit`).
function uOf(step: string, max: number): number {
  return step === "hunderter" && max === 1000 ? 100 : 10;
}

// The rule, checked with plain comparisons on [a, b, r, b1, b2, t].
function ruleHolds(v: number[], op: "+" | "-", u: number, cap: number): boolean {
  const [a, b, r, b1, b2, t] = v;
  if (a % u === 0) return false;
  const nextTen = op === "+" ? (Math.floor(a / u) + 1) * u : Math.floor(a / u) * u;
  if (t !== nextTen) return false;
  if (op === "-" && t < u) return false;
  if (b1 !== (op === "+" ? t - a : a - t)) return false;
  if (b2 !== b - b1 || b2 < 1) return false;
  if (r !== (op === "+" ? a + b : a - b)) return false;
  return v.every((x) => x >= 0 && x <= cap);
}

// Every task of the oracle for CAP: plain loops over a and b, and b1 from 1 to u - 1. Built once per op and unit.
type Row = [number, number, number, number, number, number];
const tables = new Map<string, Row[]>();
function oracleOf(op: "+" | "-", u: number): Row[] {
  const key = `${op}${u}`;
  const cached = tables.get(key);
  if (cached) return cached;
  const rows: Row[] = [];
  for (let a = 0; a <= CAP; a++) {
    for (let b = 0; b <= CAP; b++) {
      const r = op === "+" ? a + b : a - b;
      if (r < 0 || r > CAP) continue;
      for (let b1 = 1; b1 <= u - 1; b1++) {
        const t = op === "+" ? a + b1 : a - b1;
        if (op === "+" && t > CAP) continue;
        if (op === "-" && t < u) continue;
        if (t % u !== 0) continue;
        const b2 = b - b1;
        if (b2 < 1) continue;
        rows.push([a, b, r, b1, b2, t]);
        break;
      }
    }
  }
  tables.set(key, rows);
  return rows;
}

describe("drawn tasks", () => {
  it("keep the rule, the Zahlenraum, big and the grain, over many seeds", () => {
    let tasksSeen = 0;
    for (const op of OPS) {
      for (const max of MAX_LIST) {
        for (const step of STEPS) {
          for (const big of [false, true]) {
            for (const task of TASKS) {
              for (let seed = 0; seed < 40; seed++) {
                const props: ZerlegungsfeldProps = { ...DEFAULTS, op, max, step, big, task, seed };
                const u = uOf(step, max);
                for (const t of made(props).tasks) {
                  tasksSeen++;
                  const [a, b, r, b1, b2, tt] = t.values;
                  expect(ruleHolds(t.values, op, u, max)).toBe(true);
                  expect(a % u).not.toBe(0);
                  expect(tt % u).toBe(0);
                  expect(b1 + b2).toBe(b);
                  expect(b2).toBeGreaterThanOrEqual(1);
                  expect(op === "+" ? a + b : a - b).toBe(r);
                  expect(op === "+" ? a + b1 : a - b1).toBe(tt);
                  expect(op === "+" ? tt + b2 : tt - b2).toBe(r);
                  expect(t.values.every((x) => x <= max)).toBe(true);
                  if (big) expect(b).toBeGreaterThanOrEqual(u);
                  else expect(b).toBeLessThan(u);
                  if (step === "hunderter" && max === 1000) {
                    expect(a % 10).toBe(0);
                    expect(b % 10).toBe(0);
                  }
                }
              }
            }
          }
        }
      }
    }
    expect(tasksSeen).toBeGreaterThan(10000);
  });

  it("acts as zehner with hunderter at max 20 or 100", () => {
    for (const max of [20, 100]) {
      const hund = sane({ ...DEFAULTS, step: "hunderter", max, seed: 7 });
      expect(unit(hund)).toBe(10);
      for (const op of OPS) {
        const z = made({ ...DEFAULTS, op, max, step: "zehner", seed: 7 });
        const h = made({ ...DEFAULTS, op, max, step: "hunderter", seed: 7 });
        expect(h.tasks.map((t) => t.values)).toEqual(z.tasks.map((t) => t.values));
      }
    }
  });

  it("solve from the given positions alone gives the drawn task back", () => {
    for (const op of OPS) {
      for (const max of MAX_LIST) {
        for (const step of STEPS) {
          for (const task of TASKS) {
            for (let seed = 0; seed < 8; seed++) {
              const props: ZerlegungsfeldProps = { ...DEFAULTS, op, max, step, big: seed % 2 === 0, task, seed };
              const u = uOf(step, max);
              for (const t of made(props).tasks as Task[]) {
                const known = t.values.map((x, pos) => (t.given[pos] ? x : null));
                const res = solve(op, u, known, null);
                expect(res.kind).toBe("one");
                expect(res).toEqual({ kind: "one", values: t.values });
              }
            }
          }
        }
      }
    }
  });
});

describe("solve against a brute force oracle", () => {
  it("agrees on 1500 cases, with no false hints and no false keys", () => {
    const pick = (n: number) => Math.floor(r() * n);
    const r = rng(20261020);
    let falseHints = 0;
    let falseKeys = 0;
    let kindMismatch = 0;
    let counts = { none: 0, one: 0, many: 0 };
    for (let c = 0; c < 1500; c++) {
      const op = r() < 0.5 ? "+" : "-";
      const max = MAX_LIST[pick(3)];
      const step = STEPS[pick(2)];
      const u = uOf(step, max);
      const positions = [0, 1, 2, 3, 4, 5].sort(() => r() - 0.5);
      const known: (number | null)[] = [null, null, null, null, null, null];
      if (c % 2 === 0) {
        // a true task of made(), some of its positions typed
        const big = r() < 0.5;
        const tasks = made({ ...DEFAULTS, op, max, step, big, seed: pick(100000), count: 3 }).tasks;
        const v = tasks[pick(3)].values;
        const k = 1 + pick(6);
        for (const pos of positions.slice(0, k)) known[pos] = v[pos];
      } else {
        // random values 0 to 120 at 1 to 3 positions
        const k = 1 + pick(3);
        for (const pos of positions.slice(0, k)) known[pos] = pick(121);
      }

      const rows = oracleOf(op, u);
      let n = 0;
      for (const row of rows) {
        if (known.every((k, pos) => k === null || k === row[pos])) n++;
      }
      const res = solve(op, u, known, null, CAP);
      const want = n === 0 ? "none" : n === 1 ? "one" : "many";
      counts[want]++;
      if (res.kind !== want) {
        kindMismatch++;
        if (res.kind === "none") falseHints++;
        continue;
      }
      if (res.kind !== "none") {
        const okKey = ruleHolds(res.values, op, u, CAP) && known.every((k, pos) => k === null || k === res.values[pos]);
        if (!okKey) falseKeys++;
      }
    }
    expect(falseHints).toBe(0);
    expect(falseKeys).toBe(0);
    expect(kindMismatch).toBe(0);
    // every kind must actually occur, or the test checks less than it says
    expect(counts.none).toBeGreaterThan(0);
    expect(counts.one).toBeGreaterThan(0);
    expect(counts.many).toBeGreaterThan(0);
  }, 120_000);
});

describe("made with typed numbers", () => {
  it("marks numbers that do not fit as wrong and shows only the typed ones", () => {
    // 8 + 5 with the given a = 8 and b = 5 and the result 20: no solution (a + b is 13)
    const p: ZerlegungsfeldProps = {
      ...DEFAULTS,
      count: 1,
      seed: 3,
      typed: [
        [0, 0, 8],
        [0, 1, 5],
        [0, 2, 20],
      ],
    };
    const t = made(p).tasks[0];
    expect(t.wrong).toBe(true);
    expect(t.many).toBe(false);
    expect(t.values).toEqual([8, 5, 20, 0, 0, 0]);
    expect(t.given).toEqual([true, true, true, false, false, false]);
  });

  it("gives a drawn task back from a typed subset and keeps the other tasks as they were", () => {
    const base = { ...DEFAULTS, count: 3, seed: 11 };
    const plain = made(base).tasks;
    const drawn = plain[1].values;
    const typed = made({
      ...base,
      typed: [
        [1, 0, drawn[0]],
        [1, 1, drawn[1]],
      ],
    }).tasks;
    expect(typed[1].wrong).toBe(false);
    expect(typed[1].many).toBe(false);
    expect(typed[1].values).toEqual(drawn);
    expect(typed[0]).toEqual(plain[0]);
    expect(typed[2]).toEqual(plain[2]);
  });
});
