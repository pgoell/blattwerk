// The Zehnerfeld generator: every drawn task keeps the rule, the Zahlenraum and the Zehnerübergang (checked by an
// independent oracle of plain loops), `none` agrees with a brute force, `solve` and `made` agree with a brute force
// on random typed numbers, and `sane`, the colours, `crosses` and the layout keep the contract.
import { describe, expect, it } from "vitest";
import { rng } from "./zahlenmauer";
import {
  COLOR,
  DEFAULTS,
  GREY,
  MAXES,
  crosses,
  heightFor,
  layout,
  made,
  sane,
  solve,
  widthFor,
  type Cross,
  type Field,
  type ZehnerfeldProps,
  type ZehnerfeldTyped,
} from "./zehnerfeld";

type Op = "+" | "-";
type Task = "dots" | "write" | "mixed";

const OPS: Op[] = ["+", "-"];
const FIELDS: Field[] = ["zehn", "zehn2", "zwanzig", "hundert"];
const CROSSES: Cross[] = ["any", "yes", "no"];
const TASKS: Task[] = ["dots", "write", "mixed"];
const SEEDS = [1, 2, 3];

// The oracle: its own table of the field sizes and plain loops, no helper of zehnerfeld.ts.
const CSIZE: Record<Field, number> = { zehn: 10, zehn2: 10, zwanzig: 20, hundert: 100 };

// Every pair (a, b) that keeps the rule, the Zahlenraum (max, at most C) and the Zehnerübergang as it acts.
function oraclePairs(op: Op, C: number, max: number, cross: Cross): [number, number][] {
  const M = Math.min(max, C);
  const useCross = C >= 20 ? cross : "any";
  const out: [number, number][] = [];
  for (let a = 1; a <= M; a++) {
    for (let b = 1; b <= M; b++) {
      let r: number;
      if (op === "+") {
        if (a + b > M) continue;
        r = a + b;
      } else {
        if (b > a) continue;
        r = a - b;
      }
      if (useCross !== "any") {
        const crossing = op === "+" ? (a % 10) + (b % 10) > 10 : (r % 10) + (b % 10) > 10;
        if (useCross === "yes" && !crossing) continue;
        if (useCross === "no" && crossing) continue;
      }
      out.push([a, b]);
    }
  }
  return out;
}

// The picture: dots 0 to a − 1 in colour 1 (Minus: struck through from a − b on), then the second number in colour 2.
function oraclePicture(op: Op, a: number, b: number, C: number): number[] {
  const out: number[] = [];
  for (let k = 0; k < C; k++) out.push(0);
  for (let k = 0; k < a; k++) out[k] = 1;
  if (op === "+") {
    for (let k = a; k < a + b; k++) out[k] = 2;
  } else {
    for (let k = a - b; k < a; k++) out[k] = 3;
  }
  return out;
}

// Every pair (a, b) with the rule for the field size C, and the typed positions (known[p] null where not typed).
function oracleFits(op: Op, C: number, known: (number | null)[]): [number, number][] {
  const out: [number, number][] = [];
  for (let a = 1; a <= C; a++) {
    for (let b = 1; b <= C; b++) {
      const r = op === "+" ? a + b : a - b;
      if (op === "+" && r > C) continue;
      if (op === "-" && b > a) continue;
      const v = [a, b, r];
      if (known.some((x, pos) => x !== null && x !== v[pos])) continue;
      out.push([a, b]);
    }
  }
  return out;
}

// The panel settings: every field, Rechenart, Zahlenraum up to C, Zehnerübergang and Aufgabentyp.
describe("drawn tasks", () => {
  it("every setting: the drawn tasks keep the rule, the Zahlenraum, the Zehnerübergang and their picture", () => {
    for (const field of FIELDS)
      for (const op of OPS)
        for (const max of MAXES) {
          const C = CSIZE[field];
          if (max > C) continue;
          for (const cross of CROSSES)
            for (const task of TASKS)
              for (const seed of SEEDS) {
                const p: ZehnerfeldProps = { ...DEFAULTS, count: 12, columns: 4, field, op, max, cross, task, seed };
                const oracle = oraclePairs(op, C, max, cross);
                const found = new Set(oracle.map(([x, y]) => x * 1000 + y));
                const m = made(p);
                expect(m.none).toBe(oracle.length === 0);
                for (let i = 0; i < 12; i++) {
                  const t = m.tasks[i];
                  const kind = task === "mixed" ? (i % 2 === 0 ? "dots" : "write") : task;
                  expect(t.kind).toBe(kind);
                  expect(t.wrong).toBe(false);
                  expect(t.none).toBe(oracle.length === 0);
                  if (oracle.length === 0) {
                    expect(t.dots).toEqual(new Array<number>(C).fill(0));
                    continue;
                  }
                  const [a, b, r] = t.values;
                  expect(found.has(a * 1000 + b)).toBe(true);
                  expect(r).toBe(op === "+" ? a + b : a - b);
                  expect(t.dots).toEqual(oraclePicture(op, a, b, C));
                }
              }
        }
  }, 2000);
});

// Random typed numbers on random settings: a task is wrong exactly when no (a, b) fits, and otherwise keeps the rule
// and every typed value. `solve` agrees with the oracle on its own.
describe("typed tasks", () => {
  it("random typed entries: wrong exactly when no pair fits, else the rule and every typed value hold", () => {
    const R = rng(829);
    const pick = <T,>(xs: readonly T[]): T => xs[Math.floor(R() * xs.length)];
    const int = (lo: number, hi: number): number => lo + Math.floor(R() * (hi - lo + 1));
    for (let round = 0; round < 2000; round++) {
      const field = pick(FIELDS);
      const C = CSIZE[field];
      const op = pick(OPS);
      const max = pick(MAXES.filter((x) => x <= C));
      const count = int(1, 12);
      const typed: ZehnerfeldTyped[] = [];
      for (let e = int(0, 8); e > 0; e--) {
        const value = R() < 0.5 ? int(0, 999) : int(1, C);
        typed.push([int(0, 11), int(0, 2), value]);
      }
      const p: ZehnerfeldProps = {
        ...DEFAULTS,
        count,
        columns: int(1, 4),
        field,
        op,
        max,
        cross: pick(CROSSES),
        task: pick(TASKS),
        seed: int(0, 1000000),
        typed,
      };
      const m = made(p);
      for (let i = 0; i < count; i++) {
        // The last typed entry of each position for this task.
        const known: (number | null)[] = [null, null, null];
        for (const [ti, pos, v] of typed) if (ti === i) known[pos] = v;
        if (known.every((x) => x === null)) continue;
        const fits = oracleFits(op, C, known);
        const t = m.tasks[i];
        expect(t.none).toBe(false);
        expect(t.wrong).toBe(fits.length === 0);
        if (fits.length === 0) {
          expect(t.values).toEqual([0, 0, 0]);
          expect(t.dots).toEqual(new Array<number>(C).fill(0));
          expect(solve(op, known, null, C)).toBeNull();
          continue;
        }
        const [a, b, r] = t.values;
        expect(fits).toContainEqual([a, b]);
        expect(r).toBe(op === "+" ? a + b : a - b);
        known.forEach((x, pos) => {
          if (x !== null) expect([a, b, r][pos]).toBe(x);
        });
        expect(t.dots).toEqual(oraclePicture(op, a, b, C));
        const [fa, fb] = fits[0];
        expect(solve(op, known, null, C)).toEqual([fa, fb, op === "+" ? fa + fb : fa - fb]);
      }
    }
  }, 2000);
});

describe("small contract checks", () => {
  it("sane on odd input never throws and gives the defaults", () => {
    const odd = { count: "x", columns: 9, field: "foo", op: "*", task: 3, max: 7, cross: "maybe", lines: "yes", colors: "blue", manual: 1, seed: NaN, marks: "no", typed: 4 } as unknown as ZehnerfeldProps;
    expect(() => sane(odd)).not.toThrow();
    expect(() => sane({} as ZehnerfeldProps)).not.toThrow();
    const s = sane(odd);
    expect(s).toEqual({
      count: 4,
      columns: 2,
      field: "zwanzig",
      op: "+",
      task: "dots",
      max: 20,
      cross: "any",
      lines: true,
      colors: "color",
      color1: COLOR[0],
      color2: COLOR[1],
      manual: false,
      seed: 0,
    });
  });

  it("the colours differ by at least 40 in grey, and the greys differ from each other and from white", () => {
    const luma = (hex: string): number => {
      const n = parseInt(hex.slice(1), 16);
      const r = (n >> 16) & 255;
      const g = (n >> 8) & 255;
      const b = n & 255;
      return 0.299 * r + 0.587 * g + 0.114 * b;
    };
    expect(Math.abs(luma(COLOR[0]) - luma(COLOR[1]))).toBeGreaterThanOrEqual(40);
    expect(Math.abs(luma(GREY[0]) - luma(GREY[1]))).toBeGreaterThanOrEqual(40);
    expect(255 - luma(GREY[0])).toBeGreaterThanOrEqual(40);
    expect(255 - luma(GREY[1])).toBeGreaterThanOrEqual(40);
  });

  it("crosses: the examples of the contract", () => {
    expect(crosses("+", 8, 5)).toBe(true);
    expect(crosses("+", 6, 4)).toBe(false);
    expect(crosses("+", 16, 4)).toBe(false);
    expect(crosses("-", 13, 5)).toBe(true);
    expect(crosses("-", 10, 4)).toBe(false);
    expect(crosses("-", 20, 4)).toBe(false);
    expect(crosses("+", 45, 30)).toBe(false);
  });

  it("layout of the default block", () => {
    const l = layout({ ...DEFAULTS, seed: 0 });
    expect(l.TW).toBe(60);
    expect(l.TH).toBe(23);
    expect(l.vbW).toBe(127);
    expect(l.vbH).toBe(53);
    expect(widthFor({ ...DEFAULTS, seed: 0 })).toBe(127);
  });

  it("heightFor scales down when narrower and stays at full height when wider", () => {
    const p = { ...DEFAULTS, seed: 0 };
    expect(heightFor(p, widthFor(p) / 2)).toBeCloseTo(53 / 2);
    expect(heightFor(p, 1000)).toBe(53);
  });
});
