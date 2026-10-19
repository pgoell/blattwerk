// The Pfeilbild generator: the numbers follow the operators, the given flags follow the mode, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { DEFAULTS, heightFor, inverse, layout, made, noted, opLabel, sane, type PfeilbildProps, type Step } from "./pfeilbild";

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
    // Given "ends", and "mixed" with Mal or Geteilt, keep a line of 6 units for the key's note.
    expect(layout({ ...DEFAULTS, given: "ends" }).vbH).toBe(layout(DEFAULTS).vbH + 6);
    expect(layout({ ...DEFAULTS, given: "mixed", ops: ["+", "*"] }).vbH).toBe(layout(DEFAULTS).vbH + 6);
    expect(layout({ ...DEFAULTS, given: "mixed", ops: ["+", "-"] }).vbH).toBe(layout(DEFAULTS).vbH);
  });

  it("draws every picture of one Rechenart with many boxes in a small Zahlenraum", () => {
    // Plus only or Minus only bis 10 with 8 boxes fits (0, 1, ..., 7): every picture is drawn.
    for (const op of ["+", "-"] as const) {
      for (let seed = 0; seed < 50; seed++) {
        const m = made({ ...DEFAULTS, count: 12, boxes: 8, max: 10, ops: [op], seed });
        expect(m.pictures.every((pic) => !pic.over)).toBe(true);
      }
    }
  });
});

describe("typed operators", () => {
  it("a picture past the Zahlenraum stays hidden with some arrows typed, and is drawn with all of them", () => {
    const over = P({ count: 1, boxes: 8, max: 20, ops: [":"] });
    expect(made(over).pictures[0].over).toBe(true);
    expect(made({ ...over, typedOps: [[0, 0, ":", 2]] }).pictures[0].over).toBe(true);
    const all = made({ ...over, typedOps: Array.from({ length: 7 }, (_, j): [number, number, "+", number] => [0, j, "+", 1]) }).pictures[0];
    expect(all.over).toBe(false);
    expect(all.wrong).toBe(false);
    expect(all.steps.every((s) => s.op === "+" && s.n === 1)).toBe(true);
  });

  it("sane keeps the last of two typed operators for one arrow, and drops the bad ones", () => {
    const s = sane(
      P({
        typedOps: [
          [0, 0, "+", 3],
          [0, 0, "-", 4],
          [1, 2, "*", 5],
          [0, 1, "x", 2],
          [0, 1, "+", 0],
          [0, 1, "+", 1.5],
          [9, 0, "+", 1],
          [0, 7, "+", 1],
          ["0", 0, "+", 1],
        ] as unknown as PfeilbildProps["typedOps"],
      }),
    );
    expect(s.typedOps).toEqual([
      [0, 0, "-", 4],
      [1, 2, "*", 5],
    ]);
    expect(sane(P({ typedOps: [] }))).not.toHaveProperty("typedOps");
  });

  it("a typed operator replaces the arrow's step, and the numbers follow it", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.constantFrom<Step["op"]>("+", "-", "*", ":"), fc.integer({ min: 1, max: 3 }), (seed, op, n) => {
        const pic = made(P({ seed, max: 100, count: 2, typedOps: [[0, 1, op, n]] })).pictures[0];
        expect(pic.steps[1]).toEqual({ op, n });
        if (pic.wrong) return;
        expect(pic.over).toBe(false);
        pic.steps.forEach((s, j) => {
          expect(then(pic.numbers[j], s)).toBe(pic.numbers[j + 1]);
        });
        for (const x of pic.numbers) expect(Number.isInteger(x) && x >= 0 && x <= 100).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it("other pictures are unchanged by a typed operator on picture 0", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.constantFrom<PfeilbildProps["boxes"]>(4, "random"), (seed, boxes) => {
        const base = made(P({ seed, boxes, count: 4 })).pictures;
        const typed = made(P({ seed, boxes, count: 4, typedOps: [[0, 0, "*", 2]] })).pictures;
        expect(typed.slice(1)).toEqual(base.slice(1));
      }),
      { numRuns: 100 },
    );
  });

  it("typed operators only: the start is chosen so that the chain fits", () => {
    const typedOps: PfeilbildProps["typedOps"] = [
      [0, 0, "*", 2],
      [0, 1, "*", 2],
      [0, 2, "*", 2],
    ];
    for (let seed = 0; seed < 30; seed++) {
      const pic = made(P({ seed, max: 20, boxes: 4, count: 1, typedOps })).pictures[0];
      expect(pic.wrong).toBe(false);
      expect(pic.over).toBe(false);
      const [s] = pic.numbers;
      expect(pic.numbers).toEqual([s, 2 * s, 4 * s, 8 * s]);
      expect(8 * s).toBeLessThanOrEqual(20);
    }
  });

  it("a typed operator that cannot fit makes the picture wrong, and its out of range given boxes are empty", () => {
    const typedOps: PfeilbildProps["typedOps"] = [0, 1, 2].map((j) => [0, j, "+", 9] as [number, number, Step["op"], number]);
    for (let seed = 0; seed < 30; seed++) {
      const pic = made(P({ seed, max: 10, boxes: 4, count: 1, given: "ends", typedOps })).pictures[0];
      expect(pic.wrong).toBe(true);
      expect(pic.numbers.every((x) => x >= 0)).toBe(true);
      expect(pic.given[3]).toBe(false);
    }
  });

  it("a typed box that disagrees with a typed operator makes the picture wrong", () => {
    const pic = made(P({ count: 1, boxes: 4, typed: [[0, 0, 5], [0, 1, 7]], typedOps: [[0, 0, "+", 3]] })).pictures[0];
    expect(pic.wrong).toBe(true);
  });

  it("noted: mixed with a typed Mal is noted, with a typed Plus only it is not", () => {
    expect(noted({ given: "mixed", ops: ["+"], typedOps: [[0, 0, "*", 2]] })).toBe(true);
    expect(noted({ given: "mixed", ops: ["+"], typedOps: [[0, 0, ":", 2]] })).toBe(true);
    expect(noted({ given: "mixed", ops: ["+"], typedOps: [[0, 0, "+", 2]] })).toBe(false);
    expect(noted({ given: "start", ops: ["+"], typedOps: [[0, 0, "*", 2]] })).toBe(false);
    const plain = P({ given: "mixed" });
    expect(heightFor(P({ given: "mixed", typedOps: [[0, 0, "*", 2]] }), 180)).toBeGreaterThan(heightFor(plain, 180));
    expect(heightFor(P({ given: "mixed", typedOps: [[0, 0, "+", 2]] }), 180)).toBe(heightFor(plain, 180));
  });

  it("without typed operators the pictures are what they were", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), (seed) => {
        expect(made(P({ seed }))).toEqual(made(P({ seed, typedOps: [] })));
      }),
      { numRuns: 100 },
    );
  });
});
