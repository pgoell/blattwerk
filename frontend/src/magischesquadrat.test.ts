// The Magisches Quadrat generator: every drawn square is magic, the given cells follow the Schwierigkeit, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import {
  DEFAULT_GIVEN,
  DEFAULTS,
  GIVEN,
  made,
  sane,
  solve,
  type MagischesQuadratProps,
} from "./magischesquadrat";

const P = (over: Partial<MagischesQuadratProps> = {}): MagischesQuadratProps => ({
  ...DEFAULTS,
  seed: 1,
  ...over,
});

const seeds = fc.integer({ min: 0, max: 1_000_000 });
const RUNS = { numRuns: 60 };

// The sums of every row, column and both diagonals.
function lines(cells: number[][]): number[] {
  const n = cells.length;
  const rows = cells.map((row) => row.reduce((s, v) => s + v, 0));
  const cols = range(n).map((c) => cells.reduce((s, row) => s + row[c], 0));
  const diag = range(n).reduce((s, i) => s + cells[i][i], 0);
  const anti = range(n).reduce((s, i) => s + cells[i][n - 1 - i], 0);
  return [...rows, ...cols, diag, anti];
}

const range = (n: number) => Array.from({ length: n }, (_, i) => i);

describe("the Magisches Quadrate of a block", () => {
  it("every drawn square is magic, its numbers distinct and from 1 to max", () => {
    fc.assert(
      fc.property(
        seeds,
        fc.constantFrom<3 | 5>(3, 5),
        fc.constantFrom(20, 100, 1000, 50),
        fc.boolean(),
        (seed, size, max, showSum) => {
          const props = P({ seed, size, max, showSum });
          const limit = sane(props).max;
          for (const sq of made(props).squares) {
            expect(sq.wrong).toBe(false);
            expect(lines(sq.cells).every((s) => s === sq.sum)).toBe(true);
            const flat = sq.cells.flat();
            expect(new Set(flat).size).toBe(flat.length);
            expect(flat.every((v) => v >= 1 && v <= limit)).toBe(true);
          }
        },
      ),
      RUNS,
    );
  });

  it("exactly the given cells are given, for every given in GIVEN[size]", () => {
    fc.assert(
      fc.property(seeds, fc.constantFrom<3 | 5>(3, 5), fc.nat(), (seed, size, k) => {
        const [lo, hi] = GIVEN[size];
        const given = lo + (k % (hi - lo + 1));
        for (const sq of made(P({ seed, size, given })).squares) {
          expect(sq.given.flat().filter(Boolean).length).toBe(given);
        }
      }),
      RUNS,
    );
  });

  it("with enough given cells the square has one solution, which solve finds", () => {
    fc.assert(
      fc.property(
        seeds,
        fc.constantFrom<3 | 5>(3, 5),
        fc.boolean(),
        fc.nat(),
        (seed, size, showSum, k) => {
          const [, hi] = GIVEN[size];
          const need = (size === 3 ? 3 : 15) - (showSum ? 1 : 0);
          const given = need + (k % (hi - need + 1));
          for (const sq of made(P({ seed, size, given, showSum })).squares) {
            expect(sq.many).toBe(false);
            const known = sq.cells.map((row, r) => row.map((v, c) => (sq.given[r][c] ? v : null)));
            const r = solve(known, showSum ? sq.sum : null, {});
            expect(r.kind).toBe("one");
            if (r.kind === "one") expect(r.cells).toEqual(sq.cells);
          }
        },
      ),
      RUNS,
    );
  });

  it("the Lo Shu square is unique, and with one row changed it has no solution", () => {
    const lo = [
      [2, 7, 6],
      [9, 5, 1],
      [4, 3, 8],
    ];
    expect(solve(lo, null, {}).kind).toBe("one");
    const changed = [
      [2, 7, 5],
      [9, 5, 1],
      [4, 3, 8],
    ];
    expect(solve(changed, null, {}).kind).toBe("none");
  });

  it("typed numbers that fit a magic square are not wrong, and the key is magic", () => {
    const sq = made(P({ typed: [[0, 1, 1, 8], [0, 1, 2, 1], [0, 1, 3, 6], [0, 2, 2, 5]] })).squares[0];
    expect(sq.wrong).toBe(false);
    expect(lines(sq.cells).every((s) => s === sq.sum)).toBe(true);
    expect(sq.cells[0]).toEqual([8, 1, 6]);
    expect(sq.cells[1][1]).toBe(5);
  });

  it("typed numbers that fit no magic square are wrong", () => {
    // Row 1 is 1, 1, 9 so the Zielzahl is 11, but the centre would be 11 / 3.
    const sq = made(
      P({ typed: [[0, 1, 1, 1], [0, 1, 2, 1], [0, 1, 3, 9], [0, 2, 1, 9], [0, 3, 1, 1]] }),
    ).squares[0];
    expect(sq.wrong).toBe(true);
    expect(sq.sum).toBe(0);
    expect(sq.cells.flat().filter((v) => v !== 0)).toEqual([1, 1, 9, 9, 1]);
  });

  it("two typed numbers leave more than one solution, and the key keeps them", () => {
    const sq = made(P({ typed: [[0, 1, 1, 4], [0, 2, 3, 7]] })).squares[0];
    expect(sq.wrong).toBe(false);
    expect(sq.many).toBe(true);
    expect(sq.cells[0][0]).toBe(4);
    expect(sq.cells[1][2]).toBe(7);
    expect(lines(sq.cells).every((s) => s === sq.sum)).toBe(true);
  });

  it("sane of odd props gives the defaults and clamps", () => {
    const s = sane({
      count: 9,
      columns: 0,
      size: 4,
      max: "x",
      given: 99,
      showSum: "yes",
      seed: NaN,
      typed: "no",
    } as unknown as MagischesQuadratProps);
    expect(s).toMatchObject({
      count: 2,
      columns: 2,
      size: 3,
      max: 20,
      given: 8,
      showSum: false,
      seed: 0,
    });
    expect(s.typed).toBeUndefined();
    expect(sane(P({ size: 5, max: 20 })).max).toBe(100);
    expect(sane(P({ size: 3, given: 2.5 })).given).toBe(DEFAULT_GIVEN[3]);
    expect(
      sane(
        P({
          typed: [
            [0, 1, 1, 5],
            [0, 1, 1, 6],
            [0, 9, 1, 1],
            [1, 2, 2, 3],
          ],
        }),
      ).typed,
    ).toEqual([
      [0, 1, 1, 6],
      [1, 2, 2, 3],
    ]);
  });

  it("made is the same for the same props", () => {
    fc.assert(
      fc.property(seeds, (seed) => {
        expect(made(P({ seed }))).toEqual(made(P({ seed })));
      }),
      RUNS,
    );
  });

  it("a typed entry in square 0 leaves square 1 as it was", () => {
    fc.assert(
      fc.property(seeds, (seed) => {
        const before = made(P({ seed })).squares[1];
        const after = made(P({ seed, typed: [[0, 1, 1, 5]] })).squares[1];
        expect(after).toEqual(before);
      }),
      RUNS,
    );
  });
});
