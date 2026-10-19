// The Zahlenkette generator: the chains keep their step, the given rings follow the settings, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { DEFAULTS, heightFor, layout, made, sane, startFlags, stepLabel, type ZahlenketteProps } from "./zahlenkette";

const P = (over: Partial<ZahlenketteProps> = {}): ZahlenketteProps => ({ count: 4, columns: 2, rings: 6, max: 20, op: "+", showStep: false, given: "start", seed: 1, ...over });

const steps = (numbers: number[]) => numbers.slice(1).map((n, i) => n - numbers[i]);

describe("the chains of a block", () => {
  it("rings 4 to 12 give that many numbers", () => {
    fc.assert(
      fc.property(fc.integer({ min: 4, max: 12 }), fc.integer({ min: 0, max: 1_000_000 }), (rings, seed) => {
        for (const c of made(P({ rings, seed, count: 3 })).chains) expect(c.numbers).toHaveLength(rings);
      }),
      { numRuns: 100 },
    );
  });

  it("every chain keeps its step for +, - and *", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.integer({ min: 4, max: 12 }),
        fc.constantFrom(10, 20, 100, 1000),
        fc.constantFrom("+", "-", "*") as fc.Arbitrary<"+" | "-" | "*">,
        (seed, rings, max, op) => {
          const real = sane(P({ op, max })).op;
          for (const c of made(P({ seed, rings, max, op, count: 3 })).chains) {
            if (real === "*") {
              expect(c.numbers.slice(1)).toEqual(c.numbers.slice(1).map((_, i) => c.numbers[i] * c.step));
            } else {
              expect(steps(c.numbers)).toEqual(c.numbers.slice(1).map(() => (real === "+" ? c.step : -c.step)));
            }
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("\"+\" and \"-\" with a random step stay within 0 to max when the rings fit", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.integer({ min: 4, max: 12 }), fc.constantFrom(100, 1000), fc.constantFrom("+", "-") as fc.Arbitrary<"+" | "-">, (seed, rings, max, op) => {
        for (const c of made(P({ seed, rings, max, op, count: 3 })).chains) {
          expect(c.over).toBe(false);
          for (const n of c.numbers) {
            expect(n).toBeGreaterThanOrEqual(0);
            expect(n).toBeLessThanOrEqual(max);
          }
        }
      }),
      { numRuns: 100 },
    );
  });

  it("\"+\" and \"-\" stay within 0 to max, or are flagged over, at any max", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.integer({ min: 4, max: 12 }), fc.constantFrom(10, 20), (seed, rings, max) => {
        for (const op of ["+", "-"] as const) {
          for (const c of made(P({ seed, rings, max, op, count: 3 })).chains) {
            if (!c.over) for (const n of c.numbers) expect(n >= 0 && n <= max).toBe(true);
          }
        }
      }),
      { numRuns: 100 },
    );
  });

  it("\"-\" goes down", () => {
    for (const c of made(P({ op: "-", max: 100, count: 3 })).chains) {
      expect(steps(c.numbers).every((d) => d === -c.step)).toBe(true);
      expect(c.step).toBeGreaterThanOrEqual(1);
    }
  });

  it("\"*\" only under sane with max 100 or more, else it becomes \"+\"", () => {
    expect(sane(P({ op: "*", max: 20 })).op).toBe("+");
    expect(sane(P({ op: "*", max: 10 })).op).toBe("+");
    expect(sane(P({ op: "*", max: 100 })).op).toBe("*");
    expect(sane(P({ op: "*", max: 1000 })).op).toBe("*");
  });

  it("a fixed step is used", () => {
    expect(made(P({ step: 3, max: 100, count: 3 })).chains.every((c) => c.step === 3)).toBe(true);
    expect(made(P({ op: "*", max: 100, step: 5, count: 3, rings: 4 })).chains.every((c) => c.step === 5)).toBe(true);
  });

  it("a fixed step out of range is dropped", () => {
    for (const step of [0, 1001, 2.5, -3]) expect(sane(P({ step })).step).toBeUndefined();
    expect(sane(P({ op: "*", max: 100, step: 11 })).step).toBeUndefined();
    expect(sane(P({ op: "*", max: 100, step: 1 })).step).toBeUndefined();
    expect(sane(P({ op: "*", max: 100, step: 2 })).step).toBe(2);
    expect(sane(P({ step: 1000 })).step).toBe(1000);
  });

  it("given \"start\" flags the first two rings", () => {
    for (const c of made(P({ given: "start", rings: 6 })).chains) expect(c.given).toEqual([true, true, false, false, false, false]);
  });

  it("given \"ends\" flags the first and the last ring", () => {
    for (const c of made(P({ given: "ends", rings: 5 })).chains) expect(c.given).toEqual([true, false, false, false, true]);
  });

  it("given \"random\" flags at least two rings, the same for the same seed", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.integer({ min: 4, max: 12 }), (seed, rings) => {
        const chains = made(P({ seed, rings, given: "random", count: 3 })).chains;
        for (const c of chains) {
          expect(c.given.filter(Boolean)).toHaveLength(Math.max(2, Math.round(rings / 3)));
        }
        expect(made(P({ seed, rings, given: "random", count: 3 }))).toEqual(made(P({ seed, rings, given: "random", count: 3 })));
      }),
      { numRuns: 100 },
    );
  });

  it("given \"free\" flags the rings of `free`, the same for every chain", () => {
    const free = [true, false, true, false, false, true];
    for (const c of made(P({ given: "free", free, count: 3 })).chains) expect(c.given).toEqual(free);
  });

  it("a free of another length gives the start rings", () => {
    expect(sane(P({ given: "free", free: [true, false] })).free).toEqual(startFlags(6));
    expect(sane(P({ given: "free", free: [true, "x" as unknown as boolean, true, true, true, true] })).free).toEqual(startFlags(6));
  });

  it("a typed ring is the anchor for the rest of its chain", () => {
    const { chains } = made(P({ count: 1, rings: 6, op: "+", step: 3, max: 100, typed: [[0, 2, 10]] }));
    expect(chains[0].numbers).toEqual([4, 7, 10, 13, 16, 19]);
    expect(chains[0].wrong).toBe(false);
    expect(chains[0].over).toBe(false);
  });

  it("the lowest typed ring is the anchor, whatever the order", () => {
    const a = made(P({ count: 1, op: "+", step: 3, max: 100, typed: [[0, 4, 16], [0, 2, 10]] })).chains[0];
    const b = made(P({ count: 1, op: "+", step: 3, max: 100, typed: [[0, 2, 10], [0, 4, 16]] })).chains[0];
    expect(a).toEqual(b);
    expect(a.numbers).toEqual([4, 7, 10, 13, 16, 19]);
    expect(a.wrong).toBe(false);
  });

  it("a typed ring that disagrees with the step makes its chain wrong", () => {
    expect(made(P({ count: 1, op: "+", step: 3, max: 100, typed: [[0, 2, 10], [0, 4, 17]] })).chains[0].wrong).toBe(true);
    expect(made(P({ count: 1, op: "+", step: 3, max: 100, typed: [[0, 2, 10], [0, 4, 16]] })).chains[0].wrong).toBe(false);
  });

  it("a number below 0 makes its chain wrong", () => {
    expect(made(P({ count: 1, op: "+", step: 3, max: 100, typed: [[0, 3, 1]] })).chains[0].wrong).toBe(true);
    expect(made(P({ count: 1, op: "-", step: 2, max: 100, typed: [[0, 0, 4]] })).chains[0].wrong).toBe(true);
    expect(made(P({ count: 1, op: "-", step: 2, max: 100, typed: [[0, 0, 10]] })).chains[0].wrong).toBe(false);
  });

  it("a backward Mal division that is not whole makes its chain wrong", () => {
    expect(made(P({ count: 1, op: "*", step: 3, max: 1000, rings: 4, typed: [[0, 2, 10]] })).chains[0].wrong).toBe(true);
    const whole = made(P({ count: 1, op: "*", step: 3, max: 1000, rings: 4, typed: [[0, 2, 18]] })).chains[0];
    expect(whole.wrong).toBe(false);
    expect(whole.numbers).toEqual([2, 6, 18, 54]);
  });

  it("a typed chain is wrong only itself", () => {
    const chains = made(P({ count: 2, op: "+", step: 3, max: 100, typed: [[1, 2, 10], [1, 4, 17]] })).chains;
    expect(chains[0].wrong).toBe(false);
    expect(chains[1].wrong).toBe(true);
  });

  it("a fixed step too big for max is flagged over", () => {
    expect(made(P({ count: 1, op: "+", step: 50, max: 100 })).chains[0].over).toBe(true);
    expect(made(P({ count: 1, op: "+", step: 3, max: 100 })).chains[0].over).toBe(false);
    expect(made(P({ count: 1, op: "*", step: 10, max: 100, rings: 6 })).chains[0].over).toBe(true);
  });

  it("the same props give the same chains", () => {
    expect(made(P({ seed: 42 }))).toEqual(made(P({ seed: 42 })));
    expect(made(P({ seed: 42, op: "*", max: 1000, rings: 8 }))).toEqual(made(P({ seed: 42, op: "*", max: 1000, rings: 8 })));
    expect(made(P({ seed: 1, max: 1000 }))).not.toEqual(made(P({ seed: 2, max: 1000 })));
  });
});

describe("the settings and the drawing", () => {
  it("sane of odd props gives the defaults", () => {
    const s = sane({ count: 13, columns: 0, rings: 3, max: 50, op: "/", showStep: "yes", given: "bogus", seed: NaN } as unknown as ZahlenketteProps);
    expect(s).toMatchObject({ count: 4, columns: 2, rings: 6, max: 20, op: "+", showStep: false, given: "start", seed: 0 });
  });

  it("the default layout is 179 by 39", () => {
    expect(layout(DEFAULTS)).toMatchObject({ D: 10, G: 5, A: 6, chainW: 85, chainH: 16, CG: 8, RG: 6, rows: 2, vbW: 179, vbH: 39 });
  });

  it("the default block is 39 mm high at 180 mm wide", () => {
    expect(heightFor({ ...DEFAULTS, seed: 1 }, 180)).toBeCloseTo(39);
  });

  it("the labels of the arcs", () => {
    expect(stepLabel("+", 3)).toBe("+3");
    expect(stepLabel("-", 3)).toBe("−3");
    expect(stepLabel("*", 2)).toBe("·2");
  });
});
