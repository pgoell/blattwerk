// The Rechendreieck generator: the triangles hold the rules, the given fields alone fix each one, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { FIELDS, SIDES, fixes, heightFor, made, type RechendreieckProps, type FieldTyped as Typed } from "./rechendreieck";

const P = (over: Partial<RechendreieckProps> = {}): RechendreieckProps => ({ count: 4, columns: 4, max: 20, given: "inner", empty: false, seed: 1, ...over });

const SUMS = SIDES.map(([x, y]) => [x, y] as const);

// Independent solver, written apart from the generator. It counts the triangles of whole numbers from 0 up that show
// the given fields (field to value). It enumerates one inner number from 0 up to the largest given number, derives the
// other two from the given sums, checks every given field, and stops at the second solution.
function solve(shown: Map<number, number>): number[][] {
  const sols: number[][] = [];
  const bound = Math.max(0, ...shown.values());
  const innerGiven = [0, 1, 2].filter((i) => shown.has(i));
  const e = innerGiven.length ? innerGiven[0] : 0;
  for (let x = 0; x <= bound && sols.length < 2; x++) {
    const k: (number | undefined)[] = [0, 1, 2].map((i) => shown.get(i));
    k[e] = x;
    for (let pass = 0; pass < 3; pass++) {
      SUMS.forEach(([a, b], s) => {
        const v = shown.get(3 + s);
        if (v === undefined) return;
        if (k[a] !== undefined && k[b] === undefined) k[b] = v - k[a];
        else if (k[b] !== undefined && k[a] === undefined) k[a] = v - k[b];
      });
    }
    if (k.some((v) => v === undefined)) throw new Error("the given fields leave an inner number open");
    const inner = k as number[];
    if (inner.some((v) => v < 0)) continue;
    const all = [...inner, ...SUMS.map(([a, b]) => inner[a] + inner[b])];
    if ([...shown].every(([f, v]) => all[f] === v)) sols.push(all);
  }
  return sols;
}

const shownOf = (numbers: number[], given: boolean[]) => new Map(numbers.map((v, f) => [f, v] as const).filter(([f]) => given[f]));

describe("the rules of a block", () => {
  it("the triangles hold the rules for every setting", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.constantFrom(10, 20, 100, 1000),
        fc.constantFrom<RechendreieckProps["given"]>("inner", "mix", "outer", "free"),
        fc.integer({ min: 1, max: 12 }),
        (seed, max, given, count) => {
          const { triangles } = made(P({ seed, max, given, count, free: [true, true, true, false, false, true] }));
          expect(triangles).toHaveLength(count);
          const triples = new Set<string>();
          for (const t of triangles) {
            expect(t.numbers).toHaveLength(FIELDS);
            expect(t.wrong).toBe(false);
            const inner = t.numbers.slice(0, 3);
            expect(inner.every((v) => v >= 1)).toBe(true);
            SUMS.forEach(([a, b], s) => {
              expect(t.numbers[3 + s]).toBe(inner[a] + inner[b]);
              expect(t.numbers[3 + s]).toBeLessThanOrEqual(max);
            });
            triples.add(inner.join(","));
          }
          expect(triples.size).toBe(count);
        },
      ),
      { numRuns: 200 },
    );
  });

  it("a block of 12 at max 10 gets all 12 triangles, all different", () => {
    const { triangles } = made(P({ count: 12, max: 10, seed: 7 }));
    expect(triangles).toHaveLength(12);
    expect(new Set(triangles.map((t) => t.numbers.slice(0, 3).join(","))).size).toBe(12);
  });

  it("the same props give the same triangles, another seed other ones", () => {
    expect(made(P({ seed: 42 }))).toEqual(made(P({ seed: 42 })));
    expect(made(P({ seed: 42 }))).not.toEqual(made(P({ seed: 43 })));
  });

  it("a mix shows two inner fields and the outer that holds the inner left out", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), (seed) => {
        for (const t of made(P({ seed, given: "mix", count: 6 })).triangles) {
          expect(t.given.filter(Boolean)).toHaveLength(3);
          const inner = [0, 1, 2].filter((i) => t.given[i]);
          const outer = [3, 4, 5].filter((f) => t.given[f]);
          expect(inner).toHaveLength(2);
          expect(outer).toHaveLength(1);
          const left = [0, 1, 2].find((i) => !t.given[i]) as number;
          expect(SIDES[outer[0] - 3].includes(left)).toBe(true);
        }
      }),
      { numRuns: 200 },
    );
  });
});

// Rank by exact Gauss elimination over fractions, written apart from the generator: the check of `fixes`.
function rankOf(rows: number[][]): number {
  const m = rows.map((r) => r.map((v) => v / 1));
  let rank = 0;
  for (let col = 0; col < 3 && rank < m.length; col++) {
    const p = m.findIndex((r, i) => i >= rank && Math.abs(r[col]) > 1e-9);
    if (p < 0) continue;
    [m[rank], m[p]] = [m[p], m[rank]];
    for (let i = 0; i < m.length; i++) {
      if (i === rank || Math.abs(m[i][col]) < 1e-9) continue;
      const f = m[i][col] / m[rank][col];
      m[i] = m[i].map((v, k) => v - f * m[rank][k]);
    }
    rank++;
  }
  return rank;
}

describe("fixes", () => {
  it("agrees with the rank of the given rows on all 64 subsets", () => {
    for (let mask = 0; mask < 64; mask++) {
      const given = Array.from({ length: FIELDS }, (_, f) => ((mask >> f) & 1) === 1);
      const rows = given.flatMap((g, f) => (g ? [f < 3 ? [0, 1, 2].map((i) => (i === f ? 1 : 0)) : [0, 1, 2].map((i) => (SIDES[f - 3].includes(i) ? 1 : 0))] : []));
      expect(fixes(given), `mask ${mask}`).toBe(rankOf(rows) === 3);
    }
  });

  it("the hand-worked cases", () => {
    const g = (...f: number[]) => Array.from({ length: FIELDS }, (_, i) => f.includes(i));
    expect(fixes(g(3, 4, 5))).toBe(true); // the three outer: an odd cycle
    expect(fixes(g(0, 1, 2))).toBe(true); // the three inner
    expect(fixes(g(0, 1, 3))).toBe(false); // e0, e1, e0+e1: dependent
    expect(fixes(g(0, 1, 4))).toBe(true); // e0, e1, e1+e2
    expect(fixes(g(0, 3, 4))).toBe(true); // e0, e0+e1, e1+e2
    expect(fixes(g(0, 1))).toBe(false); // only two rows
    expect(fixes(g(3, 4))).toBe(false);
    expect(fixes(g())).toBe(false);
  });
});

describe("the solver proof", () => {
  it("the given fields of every generated triangle show exactly that triangle", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.constantFrom(10, 20, 100, 1000),
        fc.constantFrom<RechendreieckProps["given"]>("inner", "mix", "outer", "free"),
        fc.integer({ min: 0, max: 63 }),
        (seed, max, given, mask) => {
          const free = Array.from({ length: FIELDS }, (_, f) => ((mask >> f) & 1) === 1);
          fc.pre(given !== "free" || fixes(free));
          for (const t of made(P({ seed, max, given, count: 12, free })).triangles) {
            const found = solve(shownOf(t.numbers, t.given));
            expect(found).toHaveLength(1);
            expect(found[0]).toEqual(t.numbers);
          }
        },
      ),
      { numRuns: 400 },
    );
  });
});

describe("typed numbers", () => {
  it("a typed inner changes the two outer fields beside it and no other", () => {
    const gen = made(P({ seed: 3 })).triangles[0].numbers;
    const typed = made(P({ seed: 3, typed: [[0, 0, 7]] })).triangles[0];
    expect(typed.wrong).toBe(false);
    expect(typed.numbers[0]).toBe(7);
    expect(typed.numbers[1]).toBe(gen[1]);
    expect(typed.numbers[2]).toBe(gen[2]);
    expect(typed.numbers[3]).toBe(7 + gen[1]);
    expect(typed.numbers[4]).toBe(gen[4]);
    expect(typed.numbers[5]).toBe(7 + gen[2]);
  });

  it("three typed outer numbers fix the inner ones, the nearest rule has nothing to choose", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.integer({ min: 0, max: 20 }), fc.integer({ min: 0, max: 20 }), (seed, a, b) => {
        // Three outer numbers from two inner numbers a, b and c = a: their sum is even, so the triple has one solution.
        const x = a;
        const y = b;
        const z = (a + b) % 2 === 0 ? 0 : 1;
        const outer = [x + y, y + z, z + x];
        const typed: Typed[] = [0, 1, 2].map((f) => [0, 3 + f, outer[f]] as Typed);
        const t = made(P({ seed, max: 1000, count: 1, typed })).triangles[0];
        // Brute force over whole numbers 0 to 20 for the inner triple that holds the typed sums.
        const holds: number[][] = [];
        for (let i = 0; i <= 25; i++) for (let j = 0; j <= 25; j++) for (let k = 0; k <= 25; k++) {
          if (i + j === outer[0] && j + k === outer[1] && k + i === outer[2]) holds.push([i, j, k]);
        }
        expect(t.wrong).toBe(holds.length === 0);
        if (holds.length) expect(t.numbers.slice(0, 3)).toEqual(holds[0]);
      }),
      { numRuns: 200 },
    );
  });

  it("one or two typed numbers take the nearest triangle, as the brute force says", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.array(fc.tuple(fc.integer({ min: 0, max: 5 }), fc.integer({ min: 0, max: 20 })), { minLength: 1, maxLength: 2 }),
        (seed, raw) => {
          fc.pre(new Set(raw.map(([f]) => f)).size === raw.length);
          const typed: Typed[] = raw.map(([f, v]) => [0, f, v]);
          const gen = made(P({ seed, max: 20, count: 1 })).triangles[0].numbers.slice(0, 3);
          // Brute force over whole numbers 0 to 25 for the inner triple holding the typed numbers, nearest to gen, ties to the smallest.
          const sum = (t: number[], f: number) => (f < 3 ? t[f] : t[SIDES[f - 3][0]] + t[SIDES[f - 3][1]]);
          let best: number[] | undefined;
          for (let i = 0; i <= 25; i++) for (let j = 0; j <= 25; j++) for (let k = 0; k <= 25; k++) {
            const t = [i, j, k];
            if (!raw.every(([f, v]) => sum(t, f) === v)) continue;
            const d = (q: number[]) => q.reduce((acc, w, n) => acc + Math.abs(w - gen[n]), 0);
            const before = (a: number[], b: number[]) => {
              const n = a.findIndex((w, q) => w !== b[q]);
              return n >= 0 && a[n] < b[n];
            };
            if (!best || d(t) < d(best) || (d(t) === d(best) && before(t, best))) best = t;
          }
          const out = made(P({ seed, max: 20, count: 1, typed })).triangles[0];
          expect(out.wrong).toBe(best === undefined);
          if (best) expect(out.numbers.slice(0, 3)).toEqual(best);
        },
      ),
      { numRuns: 300 },
    );
    // A brute force per run: about 3 s on a laptop, over 5 s on a loaded runner (#569).
  }, 30_000);

  it("contradicting typed numbers give a wrong triangle that shows the typed values", () => {
    const typed: Typed[] = [
      [0, 0, 5],
      [0, 1, 5],
      [0, 3, 3],
    ];
    const t = made(P({ seed: 9, count: 2, typed })).triangles[0];
    expect(t.wrong).toBe(true);
    expect(t.numbers[0]).toBe(5);
    expect(t.numbers[1]).toBe(5);
    expect(t.numbers[3]).toBe(3);
    expect(made(P({ seed: 9, count: 2, typed })).triangles[1].wrong).toBe(false);
  });

  it("three typed outer numbers with an odd sum give a wrong triangle", () => {
    const typed: Typed[] = [
      [0, 3, 3],
      [0, 4, 4],
      [0, 5, 4],
    ];
    expect(made(P({ seed: 5, count: 1, typed })).triangles[0].wrong).toBe(true);
  });

  it("no field goes above 9999: two typed inner numbers of 9999 give a wrong triangle, 5000 and 4999 do not", () => {
    const big = (b: number) => made(P({ seed: 5, count: 1, typed: [[0, 0, 9999], [0, 1, b]] })).triangles[0];
    expect(big(9999).wrong).toBe(true);
    expect(big(0).wrong).toBe(false);
    expect(big(0).numbers.every((v) => v <= 9999)).toBe(true);
    const fits = made(P({ seed: 5, count: 1, typed: [[0, 0, 5000], [0, 1, 4999]] })).triangles[0];
    expect(fits.wrong).toBe(false);
    expect(fits.numbers[3]).toBe(9999);
  });

  it("a typed 0 is allowed", () => {
    const t = made(P({ seed: 5, count: 1, typed: [[0, 0, 0]] })).triangles[0];
    expect(t.wrong).toBe(false);
    expect(t.numbers[0]).toBe(0);
  });
});

describe("the height of a block", () => {
  it("the default block of 4 in a row fits its 50 mm", () => {
    expect(heightFor(P({ count: 4, columns: 4 }), 180)).toBeLessThanOrEqual(50);
  });

  it("12 triangles in the same 4 columns ask about three times the height of 4, the row gaps adding a little", () => {
    const ratio = heightFor(P({ count: 12, columns: 4 }), 180) / heightFor(P({ count: 4, columns: 4 }), 180);
    expect(ratio).toBeGreaterThan(2.8);
    expect(ratio).toBeLessThan(3.4);
  });

  it("more triangles in the same columns never ask less", () => {
    const heights = [1, 2, 3, 4, 5, 8, 12].map((count) => heightFor(P({ count, columns: 2 }), 180));
    expect(heights).toEqual([...heights].sort((a, b) => a - b));
  });

  it("fewer columns for the same triangles ask more height", () => {
    expect(heightFor(P({ count: 4, columns: 2 }), 180)).toBeGreaterThan(heightFor(P({ count: 4, columns: 4 }), 180));
  });
});
