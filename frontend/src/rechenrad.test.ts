// The Rechenrad generator: the numbers follow the chains, the given flags follow the task, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { DEFAULTS, made, sane, type Op, type RechenradProps } from "./rechenrad";

const P = (over: Partial<RechenradProps> = {}): RechenradProps => ({ ...DEFAULTS, seed: 1, ...over });

const ALL: Op[] = ["+", "-", "*", ":"];

// The number that x becomes with op and c.
const then = (x: number, op: Op, c: number) => (op === "+" ? x + c : op === "-" ? x - c : op === "*" ? x * c : x / c);

describe("the Rechenräder of a block", () => {
  it("sane of odd props gives the defaults", () => {
    const s = sane({ count: 13, columns: 0, rings: 4, segments: 3, max: 50, op: "*", task: "middle", seed: NaN, typed: "no" } as unknown as RechenradProps);
    expect(s).toMatchObject({ count: 2, columns: 2, rings: 2, segments: 8, max: 20, op: "*", task: "outer", seed: 0 });
    expect(s).not.toHaveProperty("typed");
  });

  it("sane drops * and : under max 20, and a middle task with 2 rings", () => {
    expect(sane(P({ op: "*", max: 10 })).op).toBe("+");
    expect(sane(P({ op: ":", max: 20 })).op).toBe(":");
    expect(sane(P({ task: "middle", rings: 2 })).task).toBe("outer");
    expect(sane(P({ task: "middle", rings: 3 })).task).toBe("middle");
  });

  it("sane keeps the last of two typed numbers for one box, and drops the bad ones", () => {
    const s = sane(P({ count: 2, typed: [[0, 1, 1, 5], [0, 1, 1, 6], [9, 0, 0, 1], [0, 4, 0, 1], [0, 1, 1, 1.5], [0, 1, 20, 3], [0, 0, 3, 2]] }));
    expect(s.typed).toEqual([[0, 1, 1, 6]]);
  });

  it("the same props give the same wheels, another seed other wheels", () => {
    expect(made(P({ seed: 42 }))).toEqual(made(P({ seed: 42 })));
    expect(made(P({ seed: 1, max: 100 })).wheels).not.toEqual(made(P({ seed: 2, max: 100 })).wheels);
  });

  it("untyped wheels: every number is in 0 to max, every chain holds, nothing is wrong", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.constantFrom(...ALL),
        fc.constantFrom(2, 3),
        fc.integer({ min: 4, max: 12 }),
        fc.constantFrom(10, 20, 100, 1000),
        (seed, op, rings, segments, max) => {
          const eff = sane(P({ op, max })).op;
          for (const w of made(P({ seed, op, rings, segments, max, count: 3 })).wheels) {
            expect(w.wrong).toBe(false);
            expect(Number.isInteger(w.centre) && w.centre >= 0).toBe(true);
            for (const row of w.rings) for (const n of row) expect(Number.isInteger(n) && n >= 0 && n <= max).toBe(true);
            for (let r = 1; r < rings; r++)
              for (let s = 0; s < segments; s++) expect(then(w.rings[r - 1][s], eff, w.centre)).toBe(w.rings[r][s]);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("given: outer hides the outer ring, inner the inner, middle the middle, mixed one box per segment", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.constantFrom(2, 3), fc.integer({ min: 4, max: 12 }), (seed, rings, segments) => {
        for (const w of made(P({ seed, rings, segments, task: "outer", count: 2 })).wheels)
          expect(w.given.every((row, r) => row.every((g) => g === (r !== rings - 1)))).toBe(true);
        for (const w of made(P({ seed, rings, segments, task: "inner", count: 2 })).wheels)
          expect(w.given.every((row, r) => row.every((g) => g === (r !== 0)))).toBe(true);
        if (rings === 3) for (const w of made(P({ seed, rings, segments, task: "middle", count: 2 })).wheels)
          expect(w.given.every((row, r) => row.every((g) => g === (r !== 1)))).toBe(true);
        for (const w of made(P({ seed, rings, segments, task: "mixed", count: 2 })).wheels)
          for (let s = 0; s < segments; s++) expect(w.given.filter((row) => !row[s])).toHaveLength(1);
      }),
      { numRuns: 100 },
    );
  });

  it("the same numbers for every task but the given flags, a mixed task drawing its rings after the inner numbers", () => {
    const base = made(P({ seed: 9, count: 1 })).wheels[0];
    for (const task of ["outer", "inner"] as const) expect(made(P({ seed: 9, count: 1, task })).wheels[0]).toEqual({ ...base, given: expect.anything() });
    expect(made(P({ seed: 9, count: 1, task: "mixed" })).wheels[0].rings).toEqual(base.rings);
  });

  it("a typed centre wins over the drawn one", () => {
    const w = made(P({ seed: 3, count: 1, typed: [[0, 0, 0, 7]] })).wheels[0];
    expect(w.centre).toBe(7);
  });

  it("a typed ring number wins over the chain's", () => {
    const w = made(P({ seed: 5, count: 1, typed: [[0, 1, 2, 3]] })).wheels[0];
    expect(w.rings[0][2]).toBe(3);
  });

  it("a typed wheel that does not fit is wrong, and has no NaN or Infinity", () => {
    for (let seed = 0; seed < 20; seed++) {
      // Ring 1 is 1 and ring 2 is 5: a "-" chain from 1 cannot reach 5.
      const w = made(P({ seed, count: 1, op: "-", typed: [[0, 1, 0, 1], [0, 2, 0, 5]] })).wheels[0];
      expect(w.wrong).toBe(true);
      for (const row of w.rings) for (const n of row) expect(Number.isFinite(n) && n >= 0).toBe(true);
    }
  });

  it("typed centre 0 with \":\" is wrong", () => {
    for (let seed = 0; seed < 20; seed++) expect(made(P({ seed, count: 1, op: ":", typed: [[0, 0, 0, 0]] })).wheels[0].wrong).toBe(true);
  });

  it("a typed centre with fitting typed ring numbers is not wrong", () => {
    const w = made(P({ seed: 4, count: 1, typed: [[0, 0, 0, 4], [0, 1, 0, 6], [0, 2, 0, 10]] })).wheels[0];
    expect(w.centre).toBe(4);
    expect(w.rings[1][0]).toBe(10);
    expect(w.wrong).toBe(false);
  });

  it("a typed wheel does not change the other wheels", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.constantFrom(...ALL),
        fc.constantFrom(10, 20, 100),
        fc.constantFrom(2, 3),
        (seed, op, max, rings) => {
          const base = made(P({ seed, op, max, rings, count: 3 })).wheels;
          const typed = made(P({ seed, op, max, rings, count: 3, typed: [[0, 0, 0, 5], [0, 1, 2, 9], [0, 2, 1, 0]] })).wheels;
          expect(typed.slice(1)).toEqual(base.slice(1));
        },
      ),
      { numRuns: 100 },
    );
  });

  it("a change of the task keeps every wheel's numbers", () => {
    const rings = (task: RechenradProps["task"]) => made(P({ rings: 3, count: 4, task })).wheels.map((w) => [w.centre, w.rings]);
    for (const task of ["inner", "middle", "mixed"] as const) expect(rings(task)).toEqual(rings("outer"));
  });

  it("a typed ring the wheel does not have plays no part", () => {
    expect(made(P({ count: 1, seed: 5, typed: [[0, 3, 0, 15]] })).wheels).toEqual(made(P({ count: 1, seed: 5 })).wheels);
  });

  it("a typed number that does not fit shows as typed and the wheel is wrong", () => {
    const [w] = made(P({ count: 1, typed: [[0, 0, 0, 7], [0, 1, 0, 5], [0, 2, 0, 99]] })).wheels;
    expect(w.wrong).toBe(true);
    expect([w.rings[0][0], w.rings[1][0]]).toEqual([5, 99]);
  });

  it("a wrong wheel shows no made-up number", () => {
    for (const props of [P({ op: ":", typed: [[0, 0, 0, 0]] }), P({ op: "-", max: 10, typed: [[0, 0, 0, 15]] })]) {
      const [w] = made(props).wheels;
      expect(w.wrong).toBe(true);
      expect(w.given.flat().some(Boolean)).toBe(false);
    }
  });

  it("a typed centre 0 with Mal or Geteilt gives a wrong wheel of whole numbers", () => {
    for (const op of ["*", ":"] as const) {
      const [w] = made(P({ op, rings: 3, typed: [[0, 0, 0, 0]] })).wheels;
      expect(w.wrong).toBe(true);
      expect(w.rings.flat().every((n) => Number.isInteger(n) && n >= 0)).toBe(true);
    }
  });
});
