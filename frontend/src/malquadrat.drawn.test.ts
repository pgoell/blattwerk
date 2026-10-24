// Drawn squares, and the typed numbers that are a subset of one.
import { describe, expect, it } from "vitest";
import {
  DEFAULTS,
  made,
  solve,
  type Square,
} from "./malquadrat";
import { rng } from "./zahlenmauer";
import {
  P,
  range,
  SEEDS,
  TASKS,
  OPS,
  SIZES,
  holds,
  positions,
} from "./malquadrat.fixtures";

describe("drawn squares", () => {
  for (const op of OPS)
    for (const size of SIZES)
      for (const task of TASKS)
        it(`${op} ${size}x${size} ${task}: right, and given as the task says`, () => {
          for (const seed of SEEDS) {
            const props = P({ seed, op, size, task });
            const n = size;
            const sqs = made(props).squares;
            expect(sqs.length).toBe(DEFAULTS.count);
            for (const sq of sqs) {
              expect(sq.wrong).toBe(false);
              expect(sq.many).toBe(false);
              expect(holds(sq.cells, n, op)).toBe(true);
              const cols = range(n).map((j) => sq.cells[0][j + 1]);
              const rows = range(n).map((i) => sq.cells[i + 1][0]);
              if (op === "*") {
                expect(cols.every((v) => DEFAULTS.reihen.includes(v))).toBe(true);
                expect(new Set(rows).size).toBe(n);
                expect(rows.every((v) => v >= 2 && v <= 10)).toBe(true);
              } else {
                const half = Math.floor(props.max! / 2);
                for (const side of [cols, rows]) {
                  expect(new Set(side).size).toBe(n);
                  expect(side.every((v) => v >= 1 && v <= half)).toBe(true);
                }
              }
              if (task === "factors") {
                const given = positions(n).filter(([r, c]) => sq.given[r][c]);
                expect(given.length).toBe(2 * n);
                expect(given.every(([r, c]) => (r === 0 && c >= 1 && c <= n) || (c === 0 && r >= 1 && r <= n))).toBe(true);
              }
              if (task !== "factors") {
                const h = Math.floor(n / 2);
                const hiddenCols = range(n).filter((j) => !sq.given[0][j + 1]);
                const hiddenRows = range(n).filter((i) => !sq.given[i + 1][0]);
                expect(hiddenCols.length).toBe(h);
                expect(hiddenRows.length).toBe(h);
                const kind = solve(n, op, sq.cells.map((row, r) => row.map((v, c) => (sq.given[r][c] ? v : null))), sq.cells);
                if (task === "mixed") {
                  expect(kind.kind).toBe("one");
                  if (kind.kind !== "none") expect(kind.cells).toEqual(sq.cells);
                }
                if (task === "knobel") {
                  const sums = range(n).filter((i) => sq.given[i + 1][n + 1]);
                  expect(sums.length).toBe(1);
                  const r0 = sums[0];
                  expect(hiddenRows).toContain(r0);
                  expect(range(n).some((j) => sq.given[r0 + 1][j + 1])).toBe(false);
                  expect(kind.kind).toBe("one");
                  if (kind.kind !== "none") expect(kind.cells).toEqual(sq.cells);
                }
              }
            }
          }
        });
});

// Random subsets of a drawn square's numbers, typed in: the square comes back the same, never wrong.
describe("typed subsets of a drawn square", () => {
  for (const op of OPS)
    for (const size of SIZES)
      for (const task of TASKS)
        it(`${op} ${size}x${size} ${task}: the drawn square comes back`, () => {
          for (const seed of SEEDS) {
            const drawn = made(P({ seed, op, size, task })).squares[0];
            const pick = rng(seed + 7);
            const typed = positions(size)
              .filter(() => pick() < 0.3)
              .map(([r, c]): [number, number, number, number] => [0, r, c, drawn.cells[r][c]]);
            const sq = made(P({ seed, op, size, task, typed })).squares[0];
            expect(sq.wrong).toBe(false);
            expect(holds(sq.cells, size, op)).toBe(true);
            expect(sq.cells).toEqual(drawn.cells);
          }
        });

  it("a typed number that contradicts the others gives wrong, and the key shows only the typed cells", () => {
    const sq = made(P({ size: 2, typed: [[0, 0, 1, 3], [0, 1, 0, 2], [0, 1, 1, 7]] })).squares[0];
    expect(sq.wrong).toBe(true);
    expect(sq.cells[1][1]).toBe(7);
    expect(sq.cells[2][2]).toBe(0);
    expect(sq.cells[0][1]).toBe(3);
  });

  it("a typed number outside the Zahlenraum counts (column number 37)", () => {
    const sq = made(P({ size: 2, typed: [[0, 0, 1, 37], [0, 1, 0, 2], [0, 1, 1, 74]] })).squares[0];
    expect(sq.wrong).toBe(false);
    expect(sq.cells[0][1]).toBe(37);
    expect(sq.given[0][1]).toBe(true);
    expect(holds(sq.cells, 2, "*")).toBe(true);
  });

  it("random custom sets: no false print, and the share of wrong squares", { timeout: 60000 }, () => {
    let total = 0;
    let wrong = 0;
    for (const seed of SEEDS) {
      const rand = rng(seed + 99);
      for (const op of OPS)
        for (const size of SIZES) {
          const drawn = made(P({ seed, op, size, task: "factors" })).squares[0];
          const count = 1 + Math.floor(rand() * 4);
          const typed = range(count).map((): [number, number, number, number] => {
            const [r, c] = positions(size)[Math.floor(rand() * positions(size).length)];
            const v = rand() < 0.5 ? drawn.cells[r][c] : Math.floor(rand() * 30);
            return [0, r, c, v];
          });
          const sq: Square = made(P({ seed, op, size, typed })).squares[0];
          total++;
          if (sq.wrong) {
            wrong++;
            continue;
          }
          expect(holds(sq.cells, size, op)).toBe(true);
          const last = new Map(typed.map(([, r, c, v]) => [`${r}:${c}`, [r, c, v]] as const));
          for (const [r, c, v] of last.values()) expect(sq.cells[r][c]).toBe(v);
        }
    }
    console.log(`random custom sets: ${wrong} of ${total} wrong (${((100 * wrong) / total).toFixed(1)} %)`);
    expect(total).toBeGreaterThan(0);
  });
});
