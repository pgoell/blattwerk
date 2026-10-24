// Solve searches back until the given numbers determine the square.
import { describe, expect, it } from "vitest";
import {
  made,
  solve,
} from "./malquadrat";
import { rng } from "./zahlenmauer";
import {
  P,
  fullSquare,
  range,
  holds,
  positions,
} from "./malquadrat.fixtures";

describe("solve searches back", () => {
  it("300 random squares with random typed subsets (true values): never wrong, every equation holds", () => {
    const rand = rng(4242);
    let wrong = 0;
    for (let k = 0; k < 300; k++) {
      const op = rand() < 0.5 ? "*" : "+";
      const n = 2 + Math.floor(rand() * 3);
      const f = range(n).map(() => Math.floor(rand() * 31));
      const g = range(n).map(() => Math.floor(rand() * 31));
      const truth = fullSquare(n, op, f, g);
      const p = rand();
      let chosen = positions(n).filter(() => rand() < p);
      if (!chosen.length) chosen = [positions(n)[0]];
      const known: (number | null)[][] = range(n + 2).map(() => Array(n + 2).fill(null) as null[]);
      for (const [r, c] of chosen) known[r][c] = truth[r][c];
      const drawn = range(n + 2).map(() => range(n + 2).map(() => Math.floor(rand() * 31)));
      const res = solve(n, op, known, drawn);
      if (res.kind === "none") {
        wrong++;
        continue;
      }
      expect(holds(res.cells, n, op)).toBe(true);
      for (const [r, c] of chosen) expect(res.cells[r][c]).toBe(truth[r][c]);
    }
    console.log(`solve random subsets: ${wrong} of 300 wrong`);
    expect(wrong).toBe(0);
  });

  it("Plus size 2, the total only: 2 is fitted by row numbers 1, 0 and column numbers 0, 0", () => {
    const known: (number | null)[][] = range(4).map(() => Array(4).fill(null) as null[]);
    known[3][3] = 2;
    const drawn = range(4).map(() => Array(4).fill(5) as number[]);
    expect(solve(2, "+", known, drawn).kind).not.toBe("none");
  });

  it("Mal size 2, typed total and row sum 7: not wrong, many", () => {
    const known: (number | null)[][] = range(4).map(() => Array(4).fill(null) as null[]);
    known[3][3] = 7;
    known[1][3] = 7;
    const drawn = range(4).map(() => Array(4).fill(0) as number[]);
    const res = solve(2, "*", known, drawn);
    expect(res.kind).toBe("many");
    if (res.kind !== "none") expect(holds(res.cells, 2, "*")).toBe(true);
  });

  it("the two misses of the random sets fit: Plus size 2, and Mal size 3", () => {
    const plus: (number | null)[][] = range(4).map(() => Array(4).fill(null) as null[]);
    plus[3][1] = 84;
    plus[3][3] = 142;
    expect(solve(2, "+", plus, range(4).map(() => Array(4).fill(0) as number[])).kind).not.toBe("none");
    const mal: (number | null)[][] = range(5).map(() => Array(5).fill(null) as null[]);
    mal[1][3] = 570;
    mal[2][2] = 6;
    mal[4][1] = 851;
    mal[4][2] = 222;
    const res = solve(3, "*", mal, range(5).map(() => Array(5).fill(0) as number[]));
    expect(res.kind).not.toBe("none");
    if (res.kind !== "none") expect(holds(res.cells, 3, "*")).toBe(true);
  });

  it("random-set misses that fit now (Mal, sums and totals)", () => {
    const cases: [number, [number, number, number, number][]][] = [
      [4, [[0, 4, 2, 0], [0, 5, 5, 3150]]],
      [3, [[0, 0, 3, 26], [0, 1, 0, 0], [0, 3, 4, 858], [0, 4, 1, 527], [0, 4, 4, 2046]]],
      [3, [[0, 4, 4, 2494]]],
      [3, [[0, 4, 4, 1125]]],
    ];
    for (const [n, typed] of cases) {
      const known: (number | null)[][] = range(n + 2).map(() => Array(n + 2).fill(null) as null[]);
      for (const [, r, c, v] of typed) known[r][c] = v;
      const res = solve(n, "*", known, range(n + 2).map(() => Array(n + 2).fill(0) as number[]));
      expect(res.kind).not.toBe("none");
      if (res.kind !== "none") expect(holds(res.cells, n, "*")).toBe(true);
    }
  });

  it("Mal size 3, typed 120, 150 and a column sum 200: not wrong, many", () => {
    const known: (number | null)[][] = range(5).map(() => Array(5).fill(null) as null[]);
    known[1][1] = 120;
    known[1][2] = 150;
    known[4][1] = 200;
    const drawn = range(5).map(() => Array(5).fill(0) as number[]);
    const res = solve(3, "*", known, drawn);
    expect(res.kind).toBe("many");
    if (res.kind !== "none") expect(holds(res.cells, 3, "*")).toBe(true);
  });

  it("Neu würfeln on a typed 4 by 4 that fits nothing does not freeze: 40 seeds take well under 3 s", () => {
    const typed: [number, number, number, number][] = [[0, 1, 5, 182], [0, 2, 5, 78], [0, 3, 5, 208], [0, 4, 5, 260], [0, 5, 2, 280], [0, 5, 3, 113], [0, 5, 5, 728]];
    expect(made(P({ count: 1, size: 4, typed, seed: 1 })).squares[0].wrong).toBe(true);
    const t = performance.now();
    for (let seed = 2; seed < 42; seed++) made(P({ count: 1, size: 4, typed, seed }));
    expect(performance.now() - t).toBeLessThan(3000);
  });
});
