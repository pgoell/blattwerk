// Solve is exact: a number is right or it is wrong.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import {
  solve,
} from "./malquadrat";
import { rng } from "./zahlenmauer";
import {
  fullSquare,
  range,
  holds,
  positions,
} from "./malquadrat.fixtures";

describe("solve is exact (#951)", () => {
  // Typed entries [square, row, col, value] to the known grid of a square of size n.
  const knownOf = (n: number, typed: [number, number, number, number][]) => {
    const known: (number | null)[][] = range(n + 2).map(() => Array(n + 2).fill(null) as null[]);
    for (const [, r, c, v] of typed) known[r][c] = v;
    return known;
  };
  const fitsPlain = (n: number, op: "*" | "+", typed: [number, number, number, number][]) => {
    const res = solve(n, op, knownOf(n, typed), range(n + 2).map(() => Array(n + 2).fill(0) as number[]));
    expect(res.kind).not.toBe("none");
    if (res.kind !== "none") expect(holds(res.cells, n, op)).toBe(true);
    for (const [, r, c, v] of typed) if (res.kind !== "none") expect(res.cells[r][c]).toBe(v);
  };

  it("property: every set of true numbers fits, every typed cell is kept", { timeout: 60000 }, () => {
    let worst = 0;
    for (const op of ["*", "+"] as const) {
      fc.assert(
        fc.property(
          fc.integer({ min: 2, max: 4 }),
          fc.integer({ min: 0, max: 1e9 }),
          fc.integer({ min: 0, max: 3 }),
          (n, seed, sel) => {
            // sel 3: the wide case, numbers 0 to 60; otherwise Mal 1 to 10 and 2 to 10, Plus 1 to max / 2.
            const max = [20, 100, 1000][sel % 3];
            const [fLo, fHi, gLo, gHi] =
              sel === 3
                ? [0, 60, 0, 60]
                : op === "*"
                  ? [1, 10, 2, 10]
                  : [1, max / 2, 1, max / 2];
            const pick = (s: number, lo: number, hi: number) => {
              const r = rng(s);
              return range(n).map(() => lo + Math.floor(r() * (hi - lo + 1)));
            };
            const f = pick(seed, fLo, fHi);
            const g = pick(seed + 1, gLo, gHi);
            const truth = fullSquare(n, op, f, g);
            const pr = rng(seed + 2);
            let chosen = positions(n).filter(() => pr() < 0.5);
            if (!chosen.length) chosen = [positions(n)[0]];
            const known: (number | null)[][] = range(n + 2).map(() => Array(n + 2).fill(null) as null[]);
            for (const [r, c] of chosen) known[r][c] = truth[r][c];
            const dr = rng(seed + 3);
            const drawn = range(n + 2).map(() => range(n + 2).map(() => Math.floor(dr() * 31)));
            const t0 = performance.now();
            const res = solve(n, op, known, drawn);
            worst = Math.max(worst, performance.now() - t0);
            expect(res.kind).not.toBe("none");
            if (res.kind === "none") return;
            expect(holds(res.cells, n, op)).toBe(true);
            for (const [r, c] of chosen) expect(res.cells[r][c]).toBe(truth[r][c]);
          },
        ),
        { numRuns: 3000 },
      );
    }
    console.log(`solve exact property: worst single solve ${worst.toFixed(2)} ms`);
  });

  it('"*" n=4 typed fits', () => {
    fitsPlain(4, "*", [[0, 4, 1, 198], [0, 4, 2, 99], [0, 5, 2, 495], [0, 5, 3, 1100]]);
  });
  it('"+" n=4 typed fits', () => {
    fitsPlain(4, "+", [[0, 1, 3, 32], [0, 1, 5, 120], [0, 5, 2, 152], [0, 5, 3, 120]]);
  });
  it('"*" n=3 typed fits', () => {
    fitsPlain(3, "*", [[0, 1, 1, 0], [0, 1, 4, 0], [0, 4, 2, 1092], [0, 4, 4, 2478]]);
  });
  it('"*" n=4 typed fits (sums)', () => {
    fitsPlain(4, "*", [[0, 2, 5, 600], [0, 3, 4, 63], [0, 5, 1, 756]]);
  });
  it('"*" n=4 typed fits (total)', () => {
    fitsPlain(4, "*", [[0, 3, 5, 1995], [0, 5, 1, 972]]);
  });
  it('"+" n=3 typed fits', () => {
    fitsPlain(3, "+", [[0, 1, 0, 148], [0, 1, 4, 997], [0, 3, 3, 390], [0, 3, 4, 613], [0, 4, 1, 718]]);
  });
  it('"*" n=4 typed fits (mixed)', () => {
    fitsPlain(4, "*", [[0, 0, 1, 10], [0, 3, 0, 9], [0, 3, 5, 216], [0, 5, 1, 300], [0, 5, 2, 210]]);
  });

  const noFit = (n: number, op: "*" | "+", typed: [number, number, number, number][]) => {
    const t0 = performance.now();
    const res = solve(n, op, knownOf(n, typed), range(n + 2).map(() => Array(n + 2).fill(0) as number[]));
    expect(performance.now() - t0).toBeLessThan(200);
    expect(res.kind).toBe("none");
  };
  it('"+" n=2 column sums of different parity: none', () => {
    noFit(2, "+", [[0, 3, 1, 4], [0, 3, 2, 5]]);
  });
  it('"*" n=2 three typed cells: none', () => {
    noFit(2, "*", [[0, 0, 1, 3], [0, 1, 0, 2], [0, 1, 1, 7]]);
  });
  it('"*" n=4 column 5 typed: none', () => {
    noFit(4, "*", [[0, 1, 5, 182], [0, 2, 5, 78], [0, 3, 5, 208], [0, 4, 5, 260], [0, 5, 2, 280], [0, 5, 3, 113], [0, 5, 5, 728]]);
  });
  it('"+" n=2 a row sum and two cells of different parity: none (took 19 s by intervals alone)', () => {
    noFit(2, "+", [[0, 1, 3, 4722], [0, 2, 1, 8933], [0, 2, 2, 9090]]);
  });
  it('"+" n=4 four cells far apart fit under the cap of the total (ran out of the node cap by intervals alone)', () => {
    fitsPlain(4, "+", [[0, 1, 2, 8420], [0, 2, 1, 3963], [0, 3, 3, 9042], [0, 4, 1, 5573]]);
  });
  it("a search that reaches its node cap is unsure, not none", () => {
    const typed: [number, number, number, number][] = [[0, 1, 2, 8420], [0, 2, 1, 3963], [0, 3, 3, 9042], [0, 4, 1, 5573]];
    expect(solve(4, "+", knownOf(4, typed), range(6).map(() => Array(6).fill(3) as number[]), 1)).toEqual({ kind: "none", unsure: true });
    expect(solve(4, "+", knownOf(4, typed), range(6).map(() => Array(6).fill(3) as number[])).kind).toBe("many");
  });
});
