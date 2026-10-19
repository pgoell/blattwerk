// The Malquadrat generator: the squares are right for every task, the given numbers follow the task, and the typed numbers
// come out right or wrong, never a false number.
import fc from "fast-check";
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

// The whole square of row numbers g and column numbers f, computed from the operation.
function fullSquare(n: number, op: "*" | "+", f: number[], g: number[]): number[][] {
  const cells = range(n + 2).map(() => Array(n + 2).fill(0) as number[]);
  const op2 = (a: number, b: number) => (op === "*" ? a * b : a + b);
  range(n).forEach((j) => (cells[0][j + 1] = f[j]));
  range(n).forEach((i) => (cells[i + 1][0] = g[i]));
  range(n).forEach((i) => range(n).forEach((j) => (cells[i + 1][j + 1] = op2(g[i], f[j]))));
  range(n).forEach((i) => (cells[i + 1][n + 1] = range(n).reduce((s, j) => s + cells[i + 1][j + 1], 0)));
  range(n).forEach((j) => (cells[n + 1][j + 1] = range(n).reduce((s, i) => s + cells[i + 1][j + 1], 0)));
  cells[n + 1][n + 1] = range(n).reduce((s, i) => s + cells[i + 1][n + 1], 0);
  return cells;
}

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
});
