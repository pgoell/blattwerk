// The Operatorfeld generator: the numbers follow the operators, the given flags follow the mode, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { DEFAULTS, made, sane, type Link, type Op, type OperatorfeldProps } from "./operatorfeld";

const P = (over: Partial<OperatorfeldProps> = {}): OperatorfeldProps => ({ ...DEFAULTS, seed: 1, ...over });

const ALL: Op[] = ["+", "-", "*", ":"];

// The number that x becomes with op and n.
const then = (x: number, op: Op, n: number) => (op === "+" ? x + n : op === "-" ? x - n : op === "*" ? x * n : x / n);

// Whether every link of a field holds: numbers[from] op n = numbers[to].
const holds = (numbers: number[], links: Link[]) => links.every((l) => then(numbers[l.from], l.op, l.n) === numbers[l.to]);

describe("the Operatorfelder of a block", () => {
  it("sane of odd props gives the defaults", () => {
    const s = sane({ centre: "yes", count: 13, columns: 0, boxes: 2, max: 50, ops: "+", only: "some", given: "bogus", drawOps: "yes", seed: NaN, typed: "no" } as unknown as OperatorfeldProps);
    expect(s).toMatchObject({ centre: false, count: 2, columns: 2, boxes: 4, max: 20, ops: ["+"], only: "none", given: "start", drawOps: true, seed: 0 });
    expect(s).not.toHaveProperty("typed");
  });

  it("sane drops * and : mit Zentrum and under max 20, and keeps the operators in order", () => {
    expect(sane(P({ centre: true, ops: ALL })).ops).toEqual(["+", "-"]);
    expect(sane(P({ max: 10, ops: ALL })).ops).toEqual(["+", "-"]);
    expect(sane(P({ ops: ["*", ":", "+", "+"] })).ops).toEqual(["+", "*", ":"]);
  });

  it("sane gives none for only tens under max 20", () => {
    expect(sane(P({ only: "tens", max: 20 })).only).toBe("none");
    expect(sane(P({ only: "hundreds", max: 100 })).only).toBe("none");
  });

  it("sane keeps the last of two typed numbers for one box, and drops the bad ones", () => {
    const s = sane(P({ typed: [[0, 0, 5], [0, 0, 6], [9, 0, 1], [0, 1, 1.5], [0, 2, 10000]] }));
    expect(s.typed).toEqual([[0, 0, 6]]);
  });

  it("the same props give the same fields, another seed other fields", () => {
    expect(made(P({ seed: 42 }))).toEqual(made(P({ seed: 42 })));
    expect(made(P({ seed: 1, max: 100 })).fields).not.toEqual(made(P({ seed: 2, max: 100 })).fields);
  });

  it("every link holds, the numbers are whole and within 0 to max, and the operands are in range", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.constantFrom(10, 20, 100, 1000),
        fc.integer({ min: 3, max: 8 }),
        fc.boolean(),
        fc.subarray(ALL, { minLength: 1 }),
        (seed, max, boxes, centre, ops) => {
          const allowed = sane(P({ max, boxes, centre, ops })).ops;
          for (const f of made(P({ seed, max, boxes, centre, ops, count: 3 })).fields) {
            if (f.over) continue;
            for (const n of f.numbers) {
              expect(Number.isInteger(n)).toBe(true);
              expect(n >= 0 && n <= max).toBe(true);
            }
            for (const l of f.links) {
              expect(allowed).toContain(l.op);
              if (l.op === "+" || l.op === "-") expect(l.n).toBeGreaterThanOrEqual(1);
              else expect(l.n >= 2 && l.n <= 10).toBe(true);
            }
            expect(holds(f.numbers, f.links)).toBe(true);
            expect(f.wrong).toBe(false);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("every field of one Rechenart draws with 8 Kästchen in each Zahlenraum where it is allowed", () => {
    const cases: [Op, number[]][] = [
      ["+", [10, 20, 100, 1000]],
      ["-", [10, 20, 100, 1000]],
      ["*", [20, 100, 1000]],
      [":", [20, 100, 1000]],
    ];
    for (const [op, maxes] of cases) {
      for (const max of maxes) {
        for (let seed = 0; seed < 50; seed++) {
          const fields = made(P({ seed, max, boxes: 8, count: 12, ops: [op] })).fields;
          expect(fields.every((f) => !f.over), `${op} bis ${max}, seed ${seed}`).toBe(true);
        }
      }
    }
  });

  it("no setting gives a field that is over", () => {
    for (const centre of [false, true])
      for (const max of [10, 20, 100, 1000])
        for (const only of ["none", "tens", "hundreds"] as const)
          for (const ops of [["+"], ["-"], ["*"], [":"], ["*", ":"], ["+", "-", "*", ":"]] as Op[][])
            for (const boxes of [3, 8])
              for (let seed = 0; seed < 20; seed++) {
                const m = made({ ...DEFAULTS, centre, max, only, ops, boxes, count: 6, seed });
                expect(m.fields.filter((f) => f.over)).toHaveLength(0);
              }
  });

  it("mit Zentrum: the centre first, every link from 0, + and − only, outer numbers distinct", () => {
    for (let seed = 0; seed < 100; seed++) {
      for (const f of made(P({ seed, centre: true, boxes: 4, max: 100, ops: ALL, count: 3 })).fields) {
        if (f.over) continue;
        expect(f.numbers).toHaveLength(5);
        expect(f.links.map((l) => l.from)).toEqual([0, 0, 0, 0]);
        expect(f.links.map((l) => l.to)).toEqual([1, 2, 3, 4]);
        expect(f.links.every((l) => l.op === "+" || l.op === "-")).toBe(true);
        expect(new Set(f.numbers.slice(1)).size).toBe(4);
        expect(holds(f.numbers, f.links)).toBe(true);
      }
    }
  });

  it("only tens: every number and every + or − operand a multiple of 10", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.constantFrom(100, 1000),
        fc.boolean(),
        fc.subarray(ALL, { minLength: 1 }),
        (seed, max, centre, ops) => {
          for (const f of made(P({ seed, max, centre, ops, only: "tens", count: 3 })).fields) {
            if (f.over) continue;
            for (const n of f.numbers) expect(n % 10).toBe(0);
            for (const l of f.links) if (l.op === "+" || l.op === "-") expect(l.n % 10).toBe(0);
            expect(holds(f.numbers, f.links)).toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("only hundreds: every number and every + or − operand a multiple of 100", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.boolean(), fc.subarray(ALL, { minLength: 1 }), (seed, centre, ops) => {
        for (const f of made(P({ seed, max: 1000, centre, ops, only: "hundreds", count: 3 })).fields) {
          if (f.over) continue;
          for (const n of f.numbers) expect(n % 100).toBe(0);
          for (const l of f.links) if (l.op === "+" || l.op === "-") expect(l.n % 100).toBe(0);
          expect(holds(f.numbers, f.links)).toBe(true);
        }
      }),
      { numRuns: 100 },
    );
  });

  it("given \"start\" shows the first box (mit Zentrum the centre) and every operator", () => {
    for (const centre of [false, true]) {
      for (const f of made(P({ given: "start", centre, boxes: 4, count: 3 })).fields) {
        expect(f.given).toEqual(f.numbers.map((_, j) => j === 0));
        expect(f.opGiven.every(Boolean)).toBe(true);
      }
    }
  });

  it("given \"ops\" shows every box and no operator", () => {
    for (const centre of [false, true]) {
      for (const f of made(P({ given: "ops", centre, boxes: 4, count: 3 })).fields) {
        expect(f.given.every(Boolean)).toBe(true);
        expect(f.opGiven.some(Boolean)).toBe(false);
      }
    }
  });

  it("given \"mixed\" shows the first box, and each link its operator or its other box; ohne Zentrum the last link always its operator", () => {
    for (const centre of [false, true]) {
      for (let seed = 0; seed < 50; seed++) {
        for (const f of made(P({ seed, centre, boxes: 5, given: "mixed", count: 3 })).fields) {
          expect(f.given[0]).toBe(true);
          const last = f.links.length - 1;
          for (let j = 0; j < f.links.length; j++) {
            if (!centre && j === last) expect(f.opGiven[j]).toBe(true);
            else expect(Number(f.opGiven[j]) + Number(f.given[j + 1])).toBe(1);
          }
        }
      }
    }
  });

  it("a typed number replaces the generated one, and the field is never over", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.constantFrom(20, 100), (seed, max) => {
        const f = made(P({ seed, max, count: 2, typed: [[1, 0, 7]] })).fields[1];
        expect(f.numbers[0]).toBe(7);
        expect(f.over).toBe(false);
        expect(f.wrong).toBe(!holds(f.numbers, f.links));
      }),
      { numRuns: 100 },
    );
  });

  it("a typed pair that no allowed op links gives wrong", () => {
    for (let seed = 0; seed < 20; seed++) {
      const f = made(P({ seed, max: 20, boxes: 4, ops: ["*"], count: 1, typed: [[0, 0, 3], [0, 1, 7]] })).fields[0];
      expect(f.wrong).toBe(true);
    }
  });

  it("typed fields are never over", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), (seed) => {
        expect(made(P({ seed, max: 20, boxes: 8, ops: ["*"], count: 2, typed: [[0, 0, 5]] })).fields[0].over).toBe(false);
      }),
      { numRuns: 100 },
    );
  });

  it("typed entries of field 0 do not change field 1", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), (seed) => {
        const base = made(P({ seed, count: 2 })).fields[1];
        const typed = made(P({ seed, count: 2, typed: [[0, 0, 5], [0, 2, 9]] })).fields[1];
        expect(typed).toEqual(base);
      }),
      { numRuns: 100 },
    );
  });
});
