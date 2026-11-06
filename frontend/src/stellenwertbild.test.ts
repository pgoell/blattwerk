// The Stellenwert-Bild generator: every drawn task keeps the rule, `zero` and its digits (checked by an independent
// oracle of plain loops), a typed number fits or gives a wrong task as the oracle says, `sane` keeps the contract,
// and the layout numbers.
import { describe, expect, it } from "vitest";
import { rng } from "./zahlenmauer";
import {
  DEFAULTS,
  heightFor,
  layout,
  made,
  sane,
  widthFor,
  type StellenwertbildProps,
} from "./stellenwertbild";

// The oracle: its own place table and plain nested loops, no helper of the generator. Each tuple is the counts
// [H, Z, E] (or [Z, E] for 100), highest place first.
const PLACE_VALUES: Record<number, number[]> = { 100: [10, 1], 1000: [100, 10, 1] };

function oracleTuples(max: number, bundle: boolean, zero: boolean | null): number[][] {
  const vals = PLACE_VALUES[max];
  const out: number[][] = [];
  const keep = (c: number[]) => {
    let n = 0;
    for (let k = 0; k < c.length; k++) n += c[k] * vals[k];
    if (n >= max) return;
    let tens = 0;
    for (let k = 1; k < c.length; k++) if (c[k] >= 10) tens++;
    if (bundle && tens !== 1) return;
    if (!bundle && tens !== 0) return;
    for (let k = 0; k < c.length; k++) {
      const allowed = bundle && k > 0 ? 19 : 9;
      if (c[k] > allowed) return;
    }
    const digits = vals.map((v) => Math.floor(n / v) % 10);
    if (zero === false && digits.some((d) => d === 0)) return;
    if (zero === true && !digits.slice(1).some((d) => d === 0)) return;
    out.push(c);
  };
  if (max === 100) {
    for (let z = 1; z <= 9; z++) for (let e = 0; e <= 19; e++) keep([z, e]);
  } else {
    for (let h = 1; h <= 9; h++) for (let z = 0; z <= 19; z++) for (let e = 0; e <= 19; e++) keep([h, z, e]);
  }
  return out;
}

// The oracle's own digit split of n, highest place first.
function oracleDigits(n: number, max: number): number[] {
  return PLACE_VALUES[max].map((v) => Math.floor(n / v) % 10);
}

function oracleSum(c: number[], max: number): number {
  const vals = PLACE_VALUES[max];
  let n = 0;
  for (let k = 0; k < c.length; k++) n += c[k] * vals[k];
  return n;
}

// The sixteen settings: Zahlenraum × Stellen mit 0 × Bündeln × Aufgabentyp.
const SETTINGS: { max: number; zero: boolean; bundle: boolean; task: "read" | "draw" }[] = [];
for (const max of [100, 1000])
  for (const zero of [false, true])
    for (const bundle of [false, true])
      for (const task of ["read", "draw"] as const) SETTINGS.push({ max, zero, bundle, task });
const SEEDS = [1, 2, 3];

describe("drawn tasks", () => {
  it("every setting and seed: the drawn tasks are oracle tuples, with n, digits and the rule as the oracle says", () => {
    const wrongPictures: string[] = [];
    const falseKeys: string[] = [];
    for (const s of SETTINGS) {
      const list = oracleTuples(s.max, s.bundle, s.zero);
      const keys = new Set(list.map((c) => c.join(",")));
      for (const seed of SEEDS) {
        const p: StellenwertbildProps = { ...DEFAULTS, ...s, count: 12, columns: 4, seed };
        const m = made(p);
        const label = `${JSON.stringify(s)} seed ${seed}`;
        if (m.none !== (list.length === 0)) falseKeys.push(`${label}: none`);
        m.tasks.forEach((t, i) => {
          if (list.length === 0) {
            if (!t.none || t.n !== 0 || t.counts.some((x) => x !== 0)) wrongPictures.push(`${label} task ${i}: not empty`);
            return;
          }
          if (t.wrong || t.none) wrongPictures.push(`${label} task ${i}: wrong or empty`);
          if (!keys.has(t.counts.join(","))) wrongPictures.push(`${label} task ${i}: counts ${t.counts} not in the oracle`);
          if (oracleSum(t.counts, s.max) !== t.n) falseKeys.push(`${label} task ${i}: sum is not n`);
          const d = oracleDigits(t.n, s.max);
          if (d.join(",") !== t.digits.join(",")) falseKeys.push(`${label} task ${i}: digits ${t.digits} not ${d}`);
          if (s.zero === false && t.digits.includes(0)) falseKeys.push(`${label} task ${i}: a digit 0`);
          if (s.zero === true && !t.digits.slice(1).includes(0)) falseKeys.push(`${label} task ${i}: no 0 in digits`);
          const big = t.counts.slice(1).filter((c) => c >= 10).length;
          if (s.bundle ? big !== 1 : big !== 0) wrongPictures.push(`${label} task ${i}: bundle count`);
          if (t.counts[0] < 1 || t.counts[0] > 9) wrongPictures.push(`${label} task ${i}: leading count`);
        });
      }
    }
    expect(wrongPictures.slice(0, 5)).toEqual([]);
    expect(falseKeys.slice(0, 5)).toEqual([]);
    expect({ wrongPictures: wrongPictures.length, falseKeys: falseKeys.length }).toEqual({ wrongPictures: 0, falseKeys: 0 });
  });
});

describe("typed numbers", () => {
  it("every setting: a typed task is wrong exactly when the rule has no tuple with that sum, and the other tasks keep their n", () => {
    const bad: string[] = [];
    let fits = 0;
    let misses = 0;
    for (const s of SETTINGS) {
      const rule = oracleTuples(s.max, s.bundle, null);
      const keys = new Set(rule.map((c) => c.join(",")));
      const sums = new Set(rule.map((c) => oracleSum(c, s.max)));
      const pick = rng(4242);
      for (let k = 0; k < 300; k++) {
        const i = Math.floor(pick() * 12);
        const v = Math.floor(pick() * 10000);
        const seed = 1 + (k % 3);
        const base: StellenwertbildProps = { ...DEFAULTS, ...s, count: 12, columns: 4, seed };
        const withTyped = made({ ...base, typed: [[i, v]] });
        const without = made(base);
        const label = `${JSON.stringify(s)} seed ${seed} typed ${v} on ${i}`;
        withTyped.tasks.forEach((t, j) => {
          if (j !== i) {
            if (t.n !== without.tasks[j].n) bad.push(`${label}: untyped task ${j} changed`);
            return;
          }
          if (!sums.has(v)) {
            misses++;
            if (!t.wrong || t.n !== 0 || t.counts.some((x) => x !== 0)) bad.push(`${label}: should be wrong`);
            return;
          }
          fits++;
          if (t.wrong || t.n !== v) bad.push(`${label}: n ${t.n}`);
          if (!keys.has(t.counts.join(","))) bad.push(`${label}: counts ${t.counts} not in the rule`);
          if (oracleSum(t.counts, s.max) !== v) bad.push(`${label}: counts do not sum to v`);
        });
      }
    }
    expect(fits).toBeGreaterThan(0);
    expect(misses).toBeGreaterThan(0);
    expect(bad.slice(0, 5)).toEqual([]);
    expect(bad.length).toBe(0);
  });
});

describe("sane", () => {
  it("odd values give the defaults", () => {
    const odd = {
      count: 0,
      columns: 5,
      max: 500,
      task: "x",
      table: "yes",
      zero: undefined,
      bundle: 1,
      seed: Number.NaN,
    } as unknown as StellenwertbildProps;
    expect(sane(odd)).toEqual({ ...DEFAULTS, seed: 0 });
    expect(sane({ ...DEFAULTS, seed: 5, count: 13 }).count).toBe(4);
    expect(sane({ ...DEFAULTS, seed: 5, count: 1.5 }).count).toBe(4);
    expect(sane({ ...DEFAULTS, seed: 5, max: 100, task: "draw" })).toMatchObject({ max: 100, task: "draw" });
  });

  it("typed entries out of range or malformed are dropped; of two for one task the last stays", () => {
    const with_ = (typed: unknown) => sane({ ...DEFAULTS, seed: 1, typed } as unknown as StellenwertbildProps).typed;
    expect(with_([[0, 5], [0, 7]])).toEqual([[0, 7]]);
    expect(with_([[0, 5], [1, 6], [0, 7]])?.slice().sort()).toEqual([[0, 7], [1, 6]]);
    expect(with_([[2, 3], [99, 1]])).toEqual([[2, 3]]);
    expect(with_([[11, 9999]])).toEqual([[11, 9999]]);
    expect(with_([[12, 5]])).toBeUndefined();
    expect(with_([[1, 10000]])).toBeUndefined();
    expect(with_([[1, -1]])).toBeUndefined();
    expect(with_([[1.5, 2]])).toBeUndefined();
    expect(with_([[1]])).toBeUndefined();
    expect(with_([[1, 2, 3]])).toBeUndefined();
    expect(with_("x")).toBeUndefined();
  });
});

describe("layout", () => {
  it("the picture, the line and the sheet's size as the contract says", () => {
    const p1000: StellenwertbildProps = { ...DEFAULTS, seed: 1 };
    const p100: StellenwertbildProps = { ...DEFAULTS, max: 100, seed: 1 };
    expect(layout(p1000).PW).toBeCloseTo(82.8);
    expect(layout(p100).PW).toBeCloseTo(38.8);
    expect(layout(p1000).PH).toBe(40);
    expect(layout(p100).PH).toBe(12);
    expect(layout({ ...p100, task: "draw" }).PH).toBe(20);
    expect(layout({ ...p1000, bundle: true }).zones[1].h).toBe(26);
    expect(layout({ ...p1000, table: true }).LW).toBe(45);
    expect(layout({ ...p1000, table: true }).LH).toBe(13);
    expect(layout({ ...p1000, task: "draw", bundle: true }).LW).toBe(34 + 5 + 16);
    expect(layout({ ...p1000, bundle: true }).KL).toBe(6);
    const l = layout(p1000);
    expect(l.vbW).toBeCloseTo(2 * 82.8 + 8 + 1);
    expect(widthFor(p1000)).toBeCloseTo(l.vbW);
    expect(heightFor(p1000, widthFor(p1000))).toBeCloseTo(l.vbH);
    expect(heightFor(p1000, widthFor(p1000) / 2)).toBeCloseTo(l.vbH / 2);
    expect(heightFor(p1000, 10000)).toBeCloseTo(l.vbH);
  });
});
