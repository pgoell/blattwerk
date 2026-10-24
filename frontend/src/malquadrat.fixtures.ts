import {
  DEFAULTS,
  type MalquadratProps,
} from "./malquadrat";

export const P = (over: Partial<MalquadratProps> = {}): MalquadratProps => ({
  ...DEFAULTS,
  seed: 1,
  ...over,
});

export const range = (n: number) => Array.from({ length: n }, (_, i) => i);
export const SEEDS = range(50);
export const TASKS = ["factors", "mixed", "knobel"] as const;
export const OPS = ["*", "+"] as const;
export const SIZES = [2, 3, 4];

// Every number of the square satisfies its equation (the sums, the total and every inner cell).
export function holds(cells: number[][], n: number, op: "*" | "+"): boolean {
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

// The whole square of row numbers g and column numbers f, computed from the operation.
export function fullSquare(n: number, op: "*" | "+", f: number[], g: number[]): number[][] {
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

// The positions of a square of size n, without the corners.
export function positions(n: number): [number, number][] {
  const out: [number, number][] = [];
  for (let r = 0; r <= n + 1; r++)
    for (let c = 0; c <= n + 1; c++) {
      const corner = (r === 0 && c === 0) || (r === 0 && c === n + 1) || (r === n + 1 && c === 0);
      if (!corner) out.push([r, c]);
    }
  return out;
}
