// The Pfeilbild generator: the numbers follow the operators, the given flags follow the mode, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { DEFAULTS, heightFor, inverse, layout, made, opLabel, sane, type PfeilbildProps, type Step } from "./pfeilbild";

const P = (over: Partial<PfeilbildProps> = {}): PfeilbildProps => ({ count: 4, columns: 2, boxes: 4, max: 20, ops: ["+", "-"], arrows: "one", given: "start", drawOps: true, seed: 1, ...over });

const OPS: Step["op"][] = ["+", "-", "*", ":"];

// The number that a step turns x into.
const then = (x: number, s: Step) => (s.op === "+" ? x + s.n : s.op === "-" ? x - s.n : s.op === "*" ? x * s.n : x / s.n);

describe("the pictures of a block", () => {
  it("sane of odd props gives the defaults", () => {
    const s = sane({ count: 13, columns: 0, boxes: 2, max: 50, ops: "+", arrows: "x", given: "bogus", drawOps: "yes", seed: NaN, typed: "no" } as unknown as PfeilbildProps);
    expect(s).toMatchObject({ count: 4, columns: 2, boxes: 4, max: 20, ops: ["+"], arrows: "one", given: "start", drawOps: true, seed: 0 });
    expect(s).not.toHaveProperty("typed");
  });

  it("sane keeps the operators in order, and drops * and : under max 20", () => {
    expect(sane(P({ ops: ["*", ":", "+", "+"], max: 20 })).ops).toEqual(["+", "*", ":"]);
    expect(sane(P({ ops: ["*", ":"], max: 10 })).ops).toEqual(["+"]);
    expect(sane(P({ ops: ["+", "*", ":"], max: 10 })).ops).toEqual(["+"]);
  });

  it("sane keeps the last of two typed numbers for one box, and drops the bad ones", () => {
    const s = sane(P({ typed: [[0, 0, 5], [0, 0, 6], [9, 0, 1], [0, 1, 1.5], [0, 2, 10000]] }));
    expect(s.typed).toEqual([[0, 0, 6]]);
  });

  it("the same props give the same pictures", () => {
    expect(made(P({ seed: 42 }))).toEqual(made(P({ seed: 42 })));
    expect(made(P({ seed: 1, max: 100 }))).not.toEqual(made(P({ seed: 2, max: 100 })));
  });

  it("every number of a picture that is drawn is whole and within 0 to max, and every step turns it into the next", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.constantFrom(10, 20, 100, 1000),
        fc.subarray(OPS, { minLength: 1 }),
        fc.constantFrom<PfeilbildProps["boxes"]>(4, 6, "random"),
        (seed, max, ops, boxes) => {
          const allowed = sane(P({ max, ops })).ops;
          for (const pic of made(P({ seed, max, ops, boxes, count: 3 })).pictures) {
            if (pic.over) continue;
            for (const n of pic.numbers) {
              expect(Number.isInteger(n)).toBe(true);
              expect(n >= 0 && n <= max).toBe(true);
            }
            pic.steps.forEach((s, j) => {
              expect(allowed).toContain(s.op);
              expect(then(pic.numbers[j], s)).toBe(pic.numbers[j + 1]);
            });
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("\"*\" and \":\" are never used under max 10", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.subarray(OPS, { minLength: 1 }), (seed, ops) => {
        for (const pic of made(P({ seed, max: 10, ops, count: 3 })).pictures) {
          for (const s of pic.steps) expect(["+", "-"]).toContain(s.op);
        }
      }),
      { numRuns: 100 },
    );
  });

  it("random boxes give 3 to 8 boxes per picture", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), (seed) => {
        for (const pic of made(P({ seed, boxes: "random", count: 6 })).pictures) {
          expect(pic.numbers.length).toBeGreaterThanOrEqual(3);
          expect(pic.numbers.length).toBeLessThanOrEqual(8);
          expect(pic.given).toHaveLength(pic.numbers.length);
          expect(pic.opGiven).toHaveLength(pic.numbers.length - 1);
        }
      }),
      { numRuns: 100 },
    );
  });

  it("given \"start\" shows box 0 and every operator", () => {
    for (const pic of made(P({ given: "start", boxes: 4, count: 3 })).pictures) {
      expect(pic.given).toEqual([true, false, false, false]);
      expect(pic.opGiven).toEqual([true, true, true]);
    }
  });

  it("given \"ends\" shows the first and the last box and no operator", () => {
    for (const pic of made(P({ given: "ends", boxes: 4, count: 3 })).pictures) {
      expect(pic.given).toEqual([true, false, false, true]);
      expect(pic.opGiven).toEqual([false, false, false]);
    }
  });

  it("given \"mixed\" shows box 0, and for each step exactly one of its operator and the box after it", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.constantFrom<PfeilbildProps["boxes"]>(3, 5, "random"), (seed, boxes) => {
        for (const pic of made(P({ seed, boxes, given: "mixed", count: 3 })).pictures) {
          expect(pic.given[0]).toBe(true);
          for (let j = 0; j < pic.opGiven.length; j++) expect(Number(pic.opGiven[j]) + Number(pic.given[j + 1])).toBe(1);
        }
      }),
      { numRuns: 100 },
    );
  });

  it("a typed box is the anchor for the other boxes of its picture", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.constantFrom(100, 1000), fc.nat(3), (seed, max, k) => {
        const base = made(P({ seed, max, count: 2 })).pictures[1];
        const typed = made(P({ seed, max, count: 2, typed: [[1, k, base.numbers[k]]] })).pictures[1];
        expect(typed.numbers).toEqual(base.numbers);
        expect(typed.wrong).toBe(false);
        expect(typed.over).toBe(false);
      }),
      { numRuns: 100 },
    );
  });

  it("a typed box that disagrees with the operators makes its picture wrong", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), (seed) => {
        const base = made(P({ seed, max: 100, count: 1 })).pictures[0];
        const typed = made(P({ seed, max: 100, count: 1, typed: [[0, 0, base.numbers[0]], [0, 1, base.numbers[1] + 1]] })).pictures[0];
        expect(typed.wrong).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it("inverse swaps + and -, and * and :, with the same operand", () => {
    expect(inverse({ op: "+", n: 4 })).toEqual({ op: "-", n: 4 });
    expect(inverse({ op: "-", n: 4 })).toEqual({ op: "+", n: 4 });
    expect(inverse({ op: "*", n: 2 })).toEqual({ op: ":", n: 2 });
    expect(inverse({ op: ":", n: 2 })).toEqual({ op: "*", n: 2 });
  });

  it("the labels of the operators", () => {
    expect(opLabel({ op: "+", n: 4 })).toBe("+4");
    expect(opLabel({ op: "-", n: 4 })).toBe("−4");
    expect(opLabel({ op: "*", n: 4 })).toBe("·4");
    expect(opLabel({ op: ":", n: 4 })).toBe(":4");
  });

  it("the height of the default block at 180 mm is its viewBox scaled to the width", () => {
    expect(heightFor({ ...DEFAULTS, seed: 1 }, 180)).toBe((layout(DEFAULTS).vbH * 180) / layout(DEFAULTS).vbW);
  });
});
