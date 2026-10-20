// The Halbschriftlich generator: every drawn task keeps the rule (checked by an independent oracle), `none` agrees with a
// brute force, `solve` agrees with a brute force oracle, and the typed numbers, `sane` and `steps` keep the contract.
import { describe, expect, it } from "vitest";
import { rng } from "./zahlenmauer";
import {
  DEFAULTS,
  acts,
  layout,
  made,
  sane,
  solve,
  steps,
  type HalbschriftlichProps,
  type Rule,
} from "./halbschriftlich";

const OPS = ["+", "-"] as const;
const MAXES = [100, 1000];
const DIGITS = [1, 2, 3];
const RULES: Rule[] = ["any", "yes", "no"];
const SEEDS = [1, 2, 3, 4, 5];

type Op = "+" | "-";
type Known = (number | null)[];

// The panel settings, all of them.
function settings(): HalbschriftlichProps[] {
  const out: HalbschriftlichProps[] = [];
  for (const op of OPS)
    for (const max of MAXES)
      for (const digits of DIGITS)
        for (const einer of RULES)
          for (const zehner of RULES) out.push({ ...DEFAULTS, op, max, digits, einer, zehner, seed: 0 });
  return out;
}

// The oracle: the digit of x at place p, the number of digits and the rules as they act, all in plain arithmetic.
const digitAt = (x: number, p: number): number => Math.floor(x / 10 ** p) % 10;

function actingK(max: number, digits: number): number {
  return max === 100 && digits === 3 ? 2 : digits;
}

function oracleSteps(op: Op, a: number, b: number, k: number): [number, number, number][] {
  const out: [number, number, number][] = [];
  let s = a;
  for (let p = k - 1; p >= 0; p--) {
    const d = digitAt(b, p);
    if (d === 0) continue;
    const part = d * 10 ** p;
    const to = op === "+" ? s + part : s - part;
    out.push([s, part, to]);
    s = to;
  }
  return out;
}

// Does (a, b) keep the rule of the panel setting? Each rule is checked on the digits of a and b.
function oracleFits(op: Op, max: number, digits: number, einer: Rule, zehner: Rule, a: number, b: number): boolean {
  const k = actingK(max, digits);
  const zAct = max === 1000 && k >= 2 ? zehner : "any";
  if (a < 1 || a > max) return false;
  if (b < 10 ** (k - 1) || b > 10 ** k - 1) return false;
  const r = op === "+" ? a + b : a - b;
  if (op === "+" && r > max) return false;
  if (op === "-" && (b > a || r < 0)) return false;
  const crosses = (p: number): boolean =>
    op === "+" ? digitAt(a, p) + digitAt(b, p) >= 10 : digitAt(a, p) < digitAt(b, p);
  if (einer === "yes" && !crosses(0)) return false;
  if (einer === "no" && crosses(0)) return false;
  if (zAct === "yes" && !crosses(1)) return false;
  if (zAct === "no" && crosses(1)) return false;
  return true;
}

// The brute force for `none`: any pair at all, the loops stop at the first fit.
function anyPair(p: HalbschriftlichProps): boolean {
  const k = actingK(p.max, p.digits);
  for (let a = 1; a <= p.max; a++)
    for (let b = 10 ** (k - 1); b <= 10 ** k - 1; b++)
      if (oracleFits(p.op, p.max, p.digits, p.einer, p.zehner, a, b)) return true;
  return false;
}

// The oracle for solve: the solutions within cap, the typed ones fixed, counted up to 2 (none, one, many).
function oracleSolve(op: Op, known: Known, cap: number): { count: number; first: number[] | null } {
  let count = 0;
  let first: number[] | null = null;
  for (let a = 1; a <= cap; a++)
    for (let b = 1; b <= cap; b++) {
      const r = op === "+" ? a + b : a - b;
      if (r < 0 || r > cap) continue;
      const v = [a, b, r];
      if (!known.every((x, i) => x === null || x === v[i])) continue;
      count++;
      if (!first) first = v;
      if (count >= 2) return { count, first };
    }
  return { count, first };
}

// The same count for cap 9999, looping over one free number only (a typed: over b; else over a).
function countBig(op: Op, known: Known, limit = 2): number {
  const cap = 9999;
  const plus = op === "+";
  let count = 0;
  const check = (a: number, b: number): boolean => {
    if (a < 1 || a > cap || b < 1 || b > cap) return false;
    const r = plus ? a + b : a - b;
    if (r < 0 || r > cap) return false;
    return known.every((x, i) => x === null || x === [a, b, r][i]);
  };
  if (known[0] !== null) {
    for (let b = 1; b <= cap && count < limit; b++) if (check(known[0], b)) count++;
  } else if (known[1] !== null) {
    for (let a = 1; a <= cap && count < limit; a++) if (check(a, known[1])) count++;
  } else {
    for (let a = 1; a <= cap && count < limit; a++) {
      const r = known[2]!;
      const b = plus ? r - a : a - r;
      if (check(a, b)) count++;
    }
  }
  return count;
}

const fitsTyped = (v: number[], known: Known, op: Op, cap: number): boolean => {
  const [a, b, r] = v;
  const rule = a >= 1 && b >= 1 && a <= cap && b <= cap && r >= 0 && r <= cap && r === (op === "+" ? a + b : a - b);
  return rule && known.every((x, i) => x === null || x === v[i]);
};

// A random subset of 1 to 3 of the positions 0, 1, 2.
function randomSubset(next: () => number): number[] {
  const all = [0, 1, 2];
  const n = 1 + Math.floor(next() * 3);
  const out: number[] = [];
  while (out.length < n) {
    const pos = all[Math.floor(next() * all.length)];
    if (!out.includes(pos)) out.push(pos);
  }
  return out;
}

describe("the drawn tasks", () => {
  it("keep the rule for every panel setting and seed, and none agrees with the brute force", () => {
    const bad: string[] = [];
    const noneSettings: string[] = [];
    for (const base of settings()) {
      const pair = anyPair(base);
      if (!pair) noneSettings.push(`${base.op} ${base.max} ${base.digits} ${base.einer} ${base.zehner}`);
      const k = actingK(base.max, base.digits);
      for (const seed of SEEDS) {
        const p = { ...base, seed, count: 12 };
        const m = made(p);
        const tag = `${p.op} ${p.max} ${p.digits} ${p.einer} ${p.zehner} seed ${seed}`;
        if (m.none === pair) bad.push(`${tag}: none ${m.none}, pair ${pair}`);
        if (m.tasks.length !== 12) bad.push(`${tag}: ${m.tasks.length} tasks`);
        for (const t of m.tasks) {
          if (m.none) {
            if (!t.none || t.wrong || t.many || t.steps.length || t.values.some((x) => x !== 0) || t.given.some((g) => g))
              bad.push(`${tag}: empty task not blank`);
            continue;
          }
          if (t.none || t.wrong || t.many) bad.push(`${tag}: drawn task flagged ${JSON.stringify(t)}`);
          const [a, b, r] = t.values;
          if (!oracleFits(p.op, p.max, p.digits, p.einer, p.zehner, a, b)) bad.push(`${tag}: ${a} ${p.op} ${b} breaks the rule`);
          if (r !== (p.op === "+" ? a + b : a - b)) bad.push(`${tag}: ${a} ${b} r ${r}`);
          if (b < 10 ** (k - 1) || b > 10 ** k - 1) bad.push(`${tag}: b ${b} not ${k} digits`);
          if (JSON.stringify(t.steps) !== JSON.stringify(oracleSteps(p.op, a, b, k))) bad.push(`${tag}: steps of ${a} ${b}`);
          if (JSON.stringify(t.given) !== JSON.stringify([true, true, false])) bad.push(`${tag}: given`);
        }
      }
    }
    expect(bad).toEqual([]);
    // The panel reaches none in no setting: every panel setting has a pair (see the report).
    expect(noneSettings).toEqual([]);
  });
});

describe("solve", () => {
  it("agrees with the brute force on about 1500 cases, and keeps the drawn task when it fits", () => {
    const cap = 150;
    const next = rng(42);
    let checked = 0;
    const bad: string[] = [];
    for (let c = 0; c < 1500; c++) {
      const op: Op = next() < 0.5 ? "+" : "-";
      const a = 1 + Math.floor(next() * cap);
      const b = 1 + Math.floor(next() * cap);
      const r = op === "+" ? a + b : a - b;
      const real = op === "+" ? r <= cap : r >= 0;
      let known: Known;
      let drawn: number[] | null;
      if (c % 2 === 0 && real) {
        const pos = randomSubset(next);
        const v = [a, b, r];
        known = [null, null, null];
        for (const q of pos) known[q] = v[q];
        drawn = v;
      } else {
        known = [null, null, null];
        for (const q of randomSubset(next)) known[q] = Math.floor(next() * (cap + 1));
        drawn = next() < 0.5 ? [a, b, r] : null;
      }
      const want = oracleSolve(op, known, cap);
      const got = solve(op, known, drawn, cap);
      checked++;
      const tag = `${op} ${JSON.stringify(known)} cap ${cap}`;
      if (want.count === 0) {
        if (got.kind !== "none") bad.push(`${tag}: want none, got ${JSON.stringify(got)}`);
      } else if (want.count === 1) {
        if (got.kind !== "one" || JSON.stringify(got.values) !== JSON.stringify(want.first))
          bad.push(`${tag}: want one ${want.first}, got ${JSON.stringify(got)}`);
      } else {
        if (got.kind !== "many") bad.push(`${tag}: want many, got ${JSON.stringify(got)}`);
        else {
          if (!fitsTyped(got.values, known, op, cap)) bad.push(`${tag}: many values ${got.values} do not fit`);
          if (drawn && fitsTyped(drawn, known, op, cap) && JSON.stringify(got.values) !== JSON.stringify(drawn))
            bad.push(`${tag}: many ignores the drawn task ${drawn}`);
        }
      }
    }
    expect(checked).toBe(1500);
    expect(bad).toEqual([]);
  });

  it("gives the edge cases", () => {
    expect(solve("-", [1, null, null], null)).toEqual({ kind: "one", values: [1, 1, 0] });
    expect(solve("+", [null, null, 2], null)).toEqual({ kind: "one", values: [1, 1, 2] });
    expect(solve("+", [5, 6, 12], null)).toEqual({ kind: "none" });
    expect(solve("-", [5, 6, 12], null)).toEqual({ kind: "none" });
    expect(solve("+", [0, null, null], null)).toEqual({ kind: "none" });
    expect(solve("-", [0, null, null], null)).toEqual({ kind: "none" });
  });
});

describe("made with typed numbers", () => {
  it("never marks a task wrong when its typed numbers are the drawn ones, and marks many only with two solutions", () => {
    const next = rng(7);
    const bad: string[] = [];
    for (let c = 0; c < 20; c++) {
      const all = settings();
      const base = all[Math.floor(next() * all.length)];
      const p = { ...base, seed: 1 + Math.floor(next() * 1000), count: 12 };
      const drawn = made(p).tasks;
      if (made(p).none) continue;
      const i = Math.floor(next() * 12);
      const v = drawn[i].values;
      const pos = randomSubset(next);
      const typedFromDrawn = pos.map((q) => [i, q, v[q]] as [number, number, number]);
      const known: Known = [0, 1, 2].map((q) => (pos.includes(q) ? v[q] : null));
      const m = made({ ...p, typed: typedFromDrawn });
      const t = m.tasks[i];
      if (t.wrong) bad.push(`drawn ${v} wrong with ${JSON.stringify(known)}`);
      if (!fitsTyped(t.values, known, base.op, 9999)) bad.push(`values ${t.values} do not fit ${JSON.stringify(known)}`);
      const count = countBig(base.op, known);
      if (t.many !== (count >= 2)) bad.push(`many ${t.many}, count ${count}, ${JSON.stringify(known)}`);
    }
    expect(bad).toEqual([]);
  });

  it("gives a wrong typed task no steps and no values but the typed ones", () => {
    const next = rng(9);
    const bad: string[] = [];
    let wrongs = 0;
    for (let c = 0; c < 200; c++) {
      const all = settings();
      const base = all[Math.floor(next() * all.length)];
      const i = Math.floor(next() * 12);
      const pos = randomSubset(next);
      const typed: [number, number, number][] = pos.map((q) => [i, q, Math.floor(next() * 10000)]);
      const known: Known = [0, 1, 2].map((q) => typed.find((e) => e[1] === q)?.[2] ?? null);
      const m = made({ ...base, seed: c, count: 12, typed });
      const t = m.tasks[i];
      if (!t.wrong) {
        if (!fitsTyped(t.values, known, base.op, 9999)) bad.push(`not wrong but values ${t.values} off ${JSON.stringify(known)}`);
        continue;
      }
      wrongs++;
      if (t.steps.length) bad.push("wrong task has steps");
      for (let q = 0; q < 3; q++) {
        const want = known[q] ?? 0;
        if (t.values[q] !== want) bad.push(`wrong task value ${q} is ${t.values[q]}, want ${want}`);
      }
      if (JSON.stringify(t.given) !== JSON.stringify(known.map((x) => x !== null))) bad.push("wrong task given");
    }
    expect(wrongs).toBeGreaterThan(0);
    expect(bad).toEqual([]);
  });
});

describe("sane", () => {
  it("gives defaults for wrong values and filters the typed entries", () => {
    const s = sane({
      ...DEFAULTS,
      seed: 3,
      count: 13,
      columns: 4,
      op: "*" as Op,
      max: 500,
      digits: 4,
      einer: "maybe" as Rule,
      zehner: "no",
      grid: "yes" as unknown as boolean,
      head: 1 as unknown as boolean,
      typed: [
        [0, 0, 5],
        [0, 0, 7],
        [12, 0, 1],
        [11, 0, 1],
        [0, 3, 1],
        [0, 0, 10000],
        [0, 0, 1.5],
        [0, 0, -1],
        [0, 0] as unknown as [number, number, number],
      ],
    });
    expect(s.count).toBe(6);
    expect(s.columns).toBe(2);
    expect(s.op).toBe("+");
    expect(s.max).toBe(1000);
    expect(s.digits).toBe(3);
    expect(s.einer).toBe("any");
    expect(s.zehner).toBe("no");
    expect(s.grid).toBe(true);
    expect(s.head).toBe(false);
    expect(s.typed).toEqual([
      [0, 0, 7],
      [11, 0, 1],
    ]);
  });

  it("keeps digits and zehner as stored, and acts on them", () => {
    const p = { ...DEFAULTS, seed: 0, max: 100, digits: 3, zehner: "yes" as Rule };
    expect(sane(p).digits).toBe(3);
    expect(acts(p)).toEqual({ k: 2, einer: "any", zehner: "any" });
    expect(acts({ ...p, max: 1000, digits: 1 }).zehner).toBe("any");
    expect(acts({ ...p, max: 1000, digits: 2 }).zehner).toBe("yes");
    expect(sane({ ...p, seed: NaN }).seed).toBe(0);
    expect(sane(p).typed).toBeUndefined();
  });
});

describe("steps and layout", () => {
  it("gives the steps of the contract", () => {
    expect(steps("+", 345, 123)).toEqual([
      [345, 100, 445],
      [445, 20, 465],
      [465, 3, 468],
    ]);
    expect(steps("+", 345, 103)).toEqual([
      [345, 100, 445],
      [445, 3, 448],
    ]);
    expect(steps("-", 468, 123)).toEqual([
      [468, 100, 368],
      [368, 20, 348],
      [348, 3, 345],
    ]);
  });

  it("lays out the default block as the contract says", () => {
    const l = layout({ ...DEFAULTS, seed: 0 });
    expect(l.TW).toBe(70);
    expect(l.S).toBe(3);
    expect(l.TH).toBe((0 + 1 + l.S + 1) * 5);
    expect(l.across).toBe(2);
    expect(l.rows).toBe(3);
    expect(l.vbW).toBe(2 * 70 + 5 + 1);
    expect(l.vbH).toBe(3 * l.TH + 2 * 5 + 1);
  });
});
