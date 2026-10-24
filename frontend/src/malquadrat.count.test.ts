// Solve says whether one solution or many are right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import {
  solve,
} from "./malquadrat";
import { rng } from "./zahlenmauer";
import {
  fullSquare,
  range,
  OPS,
  holds,
  positions,
} from "./malquadrat.fixtures";

describe("solve says one or many exactly (#954)", () => {
  // Typed entries [square, row, col, value] to the known grid of a square of size n.
  const knownOf = (n: number, typed: [number, number, number, number][]) => {
    const known: (number | null)[][] = range(n + 2).map(() => Array(n + 2).fill(null) as null[]);
    for (const [, r, c, v] of typed) known[r][c] = v;
    return known;
  };
  // Number k of a square: column numbers 0..n-1, then row numbers n..2n-1.
  const numOf = (cells: number[][], n: number, k: number) => (k < n ? cells[0][k + 1] : cells[k - n + 1][0]);

  for (const op of OPS)
    for (const n of [2, 3, 4]) {
      it(`${op} n=${n}: one or many is exact, and each proof and other square check out`, { timeout: 120000 }, () => {
        let runs = 0;
        let ones = 0;
        let manys = 0;
        let unsures = 0;
        let worst = 0;
        fc.assert(
          fc.property(
            fc.integer({ min: 0, max: 1e9 }),
            fc.integer({ min: 0, max: 3 }),
            (seed, sel) => {
              runs++;
              // sel 3: the wide case, numbers 0 to 60; otherwise Mal 1 to 10 and 2 to 10, Plus 1 to max / 2.
              const max = [20, 100, 1000][sel % 3];
              const [fLo, fHi, gLo, gHi] = sel === 3 ? [0, 60, 0, 60] : op === "*" ? [1, 10, 2, 10] : [1, max / 2, 1, max / 2];
              const pick = (s: number, lo: number, hi: number) => {
                const r = rng(s);
                return range(n).map(() => lo + Math.floor(r() * (hi - lo + 1)));
              };
              const truth = fullSquare(n, op, pick(seed, fLo, fHi), pick(seed + 1, gLo, gHi));
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
              if (res.kind === "one") {
                ones++;
                // Independent proof: with number k fenced off on either side of its solution value, nothing fits.
                for (let k = 0; k < 2 * n; k++) {
                  const s = numOf(res.cells, n, k);
                  const sides: [number, number][] = [];
                  if (s > 0) sides.push([0, s - 1]);
                  sides.push([s + 1, 9999]);
                  for (const side of sides) {
                    const bounds: [number, number][] = range(2 * n).map((j) => (j === k ? side : [0, 9999]));
                    expect(solve(n, op, known, drawn, 2000, bounds)).toEqual({ kind: "none" });
                  }
                }
                return;
              }
              if (res.unsure) {
                unsures++;
                return;
              }
              manys++;
              const other = res.other;
              expect(other).toBeDefined();
              if (!other) return;
              expect(range(2 * n).some((k) => numOf(other, n, k) !== numOf(res.cells, n, k))).toBe(true);
              expect(holds(other, n, op)).toBe(true);
              for (const [r, c] of chosen) expect(other[r][c]).toBe(truth[r][c]);
            },
          ),
          { numRuns: 400 },
        );
        console.log(`solve one or many ${op} n=${n}: ${runs} runs, ${ones} one, ${manys} many, ${unsures} many and unsure, worst ${worst.toFixed(2)} ms`);
        expect(unsures).toBe(0);
      });
    }

  it("Plus n=2, typed 5 1 with the row numbers 5 4: one", () => {
    const res = solve(2, "+", knownOf(2, [[0, 1, 0, 5], [0, 1, 3, 16], [0, 3, 1, 19], [0, 3, 2, 11]]), range(4).map(() => Array(4).fill(0) as number[]));
    expect(res.kind).toBe("one");
    if (res.kind !== "none") {
      expect([res.cells[0][1], res.cells[0][2]]).toEqual([5, 1]);
      expect([res.cells[1][0], res.cells[2][0]]).toEqual([5, 4]);
    }
  });

  it("Mal n=2, [2,2]=5 [2,3]=10 [3,1]=6: one", () => {
    const res = solve(2, "*", knownOf(2, [[0, 2, 2, 5], [0, 2, 3, 10], [0, 3, 1, 6]]), range(4).map(() => Array(4).fill(0) as number[]));
    expect(res.kind).toBe("one");
  });

  it("Mal n=2, [1,0]=3 [2,1]=3 [3,2]=24 [3,3]=36: one", () => {
    const res = solve(2, "*", knownOf(2, [[0, 1, 0, 3], [0, 2, 1, 3], [0, 3, 2, 24], [0, 3, 3, 36]]), range(4).map(() => Array(4).fill(0) as number[]));
    expect(res.kind).toBe("one");
  });

  it("a second search cut short by the cap is many and unsure, the default cap finds the other square", () => {
    const drawn = fullSquare(2, "+", [1, 2], [3, 4]);
    const known = knownOf(2, [[0, 1, 1, drawn[1][1]]]);
    const capped = solve(2, "+", known, drawn, 1);
    expect(capped.kind).toBe("many");
    expect(capped.unsure).toBe(true);
    const full = solve(2, "+", known, drawn);
    expect(full.kind).toBe("many");
    expect(full.unsure).toBeFalsy();
    expect(full.kind !== "none" && full.other).toBeDefined();
  });

  // An independent oracle, no search of solve: the squares with every number 0..K that keep every typed cell.
  // It checks a typed cell as soon as its numbers are set (a column or row number, or a product or sum of two),
  // sums and totals only at the end. It stops after `stop` matches.
  function bruteCount(n: number, op: "*" | "+", known: (number | null)[][], K: number, stop = 2) {
    const nums: number[] = Array(2 * n).fill(0);
    const needOf = (r: number, c: number) => {
      if (r === 0) return c >= 1 && c <= n ? c - 1 : -1;
      if (c === 0) return r >= 1 && r <= n ? n + r - 1 : -1;
      return r <= n && c <= n ? Math.max(c - 1, n + r - 1) : -1;
    };
    const checks: [number, number, number][][] = range(2 * n).map(() => []);
    const sumChecks: [number, number, number][] = [];
    for (const [r, c] of positions(n)) {
      const v = known[r][c];
      const need = needOf(r, c);
      if (v === null) continue;
      if (need >= 0) checks[need].push([r, c, v]);
      else sumChecks.push([r, c, v]);
    }
    const cellValue = (r: number, c: number) =>
      r === 0 ? nums[c - 1] : c === 0 ? nums[n + r - 1] : op === "*" ? nums[n + r - 1] * nums[c - 1] : nums[n + r - 1] + nums[c - 1];
    // A sum or the total of the inner cells, from the numbers set so far (all of them at the end).
    const inner = (i: number, j: number) => (op === "*" ? nums[n + i - 1] * nums[j - 1] : nums[n + i - 1] + nums[j - 1]);
    const sumValue = (r: number, c: number) => {
      if (r === n + 1 && c === n + 1) return range(n).reduce((s, i) => s + range(n).reduce((t, j) => t + inner(i + 1, j + 1), 0), 0);
      if (c === n + 1) return range(n).reduce((s, j) => s + inner(r, j + 1), 0);
      return range(n).reduce((s, i) => s + inner(i + 1, c), 0);
    };
    const squares: number[][][] = [];
    const rec = (idx: number): boolean => {
      if (idx === 2 * n) {
        if (sumChecks.every(([r, c, v]) => sumValue(r, c) === v)) squares.push(fullSquare(n, op, nums.slice(0, n), nums.slice(n)));
        return squares.length >= stop;
      }
      for (let v = 0; v <= K; v++) {
        nums[idx] = v;
        if (checks[idx].every(([r, c, want]) => cellValue(r, c) === want) && rec(idx + 1)) return true;
      }
      return false;
    };
    rec(0);
    return { count: squares.length, squares };
  }

  for (const op of OPS)
    for (const [n, K] of [
      [2, 30],
      [3, 15],
    ] as const) {
      it(`brute force oracle up to ${K} (${op} n=${n})`, { timeout: 120000 }, () => {
        let runs = 0;
        let ones = 0;
        let manys = 0;
        let worstBrute = 0;
        let worstSolve = 0;
        fc.assert(
          fc.property(fc.integer({ min: 0, max: 1e9 }), (seed) => {
            runs++;
            const pick = (s: number) => {
              const r = rng(s);
              return range(n).map(() => Math.floor(r() * (K + 1)));
            };
            const truth = fullSquare(n, op, pick(seed), pick(seed + 1));
            const pr = rng(seed + 2);
            let chosen = positions(n).filter(() => pr() < 0.3);
            if (!chosen.length) chosen = [positions(n)[Math.floor(pr() * positions(n).length)]];
            const known: (number | null)[][] = range(n + 2).map(() => Array(n + 2).fill(null) as null[]);
            for (const [r, c] of chosen) known[r][c] = truth[r][c];
            const dr = rng(seed + 3);
            const drawn = range(n + 2).map(() => range(n + 2).map(() => Math.floor(dr() * 31)));
            const bounds = range(2 * n).map((): [number, number] => [0, K]);

            const t0 = performance.now();
            const brute = bruteCount(n, op, known, K);
            worstBrute = Math.max(worstBrute, performance.now() - t0);
            const t1 = performance.now();
            const res = solve(n, op, known, drawn, 2000, bounds);
            worstSolve = Math.max(worstSolve, performance.now() - t1);

            expect(brute.count).toBeGreaterThan(0);
            if (brute.count === 1) {
              ones++;
              expect(res.kind).toBe("one");
              if (res.kind !== "none") expect(res.cells).toEqual(brute.squares[0]);
              return;
            }
            manys++;
            expect(res.kind).toBe("many");
            if (res.kind === "none") return;
            expect(res.unsure).toBeFalsy();
            expect(res.other).toBeDefined();
            if (!res.other) return;
            expect(holds(res.cells, n, op)).toBe(true);
            expect(holds(res.other, n, op)).toBe(true);
            expect(range(2 * n).some((k) => numOf(res.other!, n, k) !== numOf(res.cells, n, k))).toBe(true);
            for (const [r, c] of chosen) {
              expect(res.cells[r][c]).toBe(truth[r][c]);
              expect(res.other[r][c]).toBe(truth[r][c]);
            }
          }),
          { numRuns: 300 },
        );
        console.log(
          `brute force oracle ${op} n=${n}: ${runs} runs, ${ones} one, ${manys} many, worst brute ${worstBrute.toFixed(1)} ms, worst solve ${worstSolve.toFixed(1)} ms`,
        );
      });
    }
});
