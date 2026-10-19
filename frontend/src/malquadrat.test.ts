// The Malquadrat generator: the squares are right for every task, the given numbers follow the task, and the typed numbers
// come out right or wrong, never a false number.
import { describe, expect, it } from "vitest";
import {
  DEFAULTS,
  heightFor,
  made,
  opLabel,
  sane,
  solve,
  type MalquadratProps,
  type Square,
} from "./malquadrat";
import { rng } from "./zahlenmauer";

const P = (over: Partial<MalquadratProps> = {}): MalquadratProps => ({
  ...DEFAULTS,
  seed: 1,
  ...over,
});

const range = (n: number) => Array.from({ length: n }, (_, i) => i);
const SEEDS = range(50);
const TASKS = ["factors", "mixed", "knobel"] as const;
const OPS = ["*", "+"] as const;
const SIZES = [2, 3, 4];

// Every number of the square satisfies its equation (the sums, the total and every inner cell).
function holds(cells: number[][], n: number, op: "*" | "+"): boolean {
  const f = (a: number, b: number) => (op === "*" ? a * b : a + b);
  for (let i = 1; i <= n; i++) for (let j = 1; j <= n; j++) if (cells[i][j] !== f(cells[i][0], cells[0][j])) return false;
  for (let i = 1; i <= n; i++) {
    if (range(n).reduce((s, j) => s + cells[i][j + 1], 0) !== cells[i][n + 1]) return false;
  }
  for (let j = 1; j <= n; j++) {
    if (range(n).reduce((s, i) => s + cells[i + 1][j], 0) !== cells[n + 1][j]) return false;
  }
  const inner = range(n).reduce((s, i) => s + range(n).reduce((t, j) => t + cells[i + 1][j + 1], 0), 0);
  return cells[n + 1][n + 1] === inner;
}

// The positions of a square of size n, without the corners.
function positions(n: number): [number, number][] {
  const out: [number, number][] = [];
  for (let r = 0; r <= n + 1; r++)
    for (let c = 0; c <= n + 1; c++) {
      const corner = (r === 0 && c === 0) || (r === 0 && c === n + 1) || (r === n + 1 && c === 0);
      if (!corner) out.push([r, c]);
    }
  return out;
}

describe("sane", () => {
  it("a wrong value gives its default, the size clamps to 2..4", () => {
    const s = sane({ ...DEFAULTS, seed: 1, count: 9, columns: 0, size: 7, op: "/" as never, task: "x" as never, max: 50 });
    expect(s.count).toBe(DEFAULTS.count);
    expect(s.columns).toBe(DEFAULTS.columns);
    expect(s.size).toBe(4);
    expect(s.op).toBe("*");
    expect(s.task).toBe("factors");
    expect(s.max).toBe(20);
    expect(sane({ ...DEFAULTS, seed: 1, size: 1 }).size).toBe(2);
    expect(sane({ ...DEFAULTS, seed: 1, size: 2.5 }).size).toBe(DEFAULTS.size);
  });

  it("max 20, 100 or 1000 stays, any other gives 20", () => {
    expect(sane(P({ max: 100 })).max).toBe(100);
    expect(sane(P({ max: 1000 })).max).toBe(1000);
    expect(sane(P({ max: 50 })).max).toBe(20);
  });

  it("the Reihen keep 1 to 10 once each, an empty list gives the default", () => {
    expect(sane(P({ reihen: [3, 3, 0, 11, 7, 2] })).reihen).toEqual([3, 7, 2]);
    expect(sane(P({ reihen: [] })).reihen).toEqual(DEFAULTS.reihen);
  });

  it("typed entries are filtered, and of two for the same cell the last one stays", () => {
    const s = sane(
      P({
        typed: [
          [0, 0, 1, 5],
          [0, 0, 1, 9],
          [4, 0, 1, 3],
          [0, 6, 1, 3],
          [0, 1, 1, 10000],
          [0, 1.5, 1, 3],
        ],
      }),
    );
    expect(s.typed).toEqual([[0, 0, 1, 9]]);
    expect(sane(P({ typed: [] })).typed).toBeUndefined();
  });

  it("opLabel", () => {
    expect(opLabel("*")).toBe("·");
    expect(opLabel("+")).toBe("+");
  });
});

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

  it("random custom sets: no false print, and the share of wrong squares", () => {
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

describe("made", () => {
  it("the same props give the same squares, memo or not", () => {
    const a = made(P({ seed: 5, size: 4, op: "+", task: "knobel" }));
    const b = made({ ...P({ seed: 5, size: 4, op: "+", task: "knobel" }) });
    expect(b).toEqual(a);
  });

  it("a typed entry in square 0 leaves square 1 unchanged", () => {
    for (const seed of SEEDS.slice(0, 20)) {
      const plain = made(P({ seed, count: 2 })).squares[1];
      const typed = made(P({ seed, count: 2, typed: [[0, 1, 1, 5], [0, 2, 0, 3]] })).squares[1];
      expect(typed).toEqual(plain);
    }
  });
});

describe("heightFor", () => {
  it("is a sensible positive number and grows with count and size", () => {
    const h = heightFor({ ...DEFAULTS, seed: 1 }, 180);
    expect(h).toBeGreaterThan(0);
    expect(Number.isFinite(h)).toBe(true);
    expect(heightFor(P({ count: 4, columns: 2 }), 180)).toBeGreaterThan(h);
    expect(heightFor(P({ size: 4 }), 1000)).toBeGreaterThan(heightFor(P({ size: 3 }), 1000));
    expect(heightFor(P({ size: 3 }), 1000)).toBeGreaterThan(heightFor(P({ size: 2 }), 1000));
  });
});
