// The Zahlenmauer generator: the walls hold the rule, solve from their given stones alone, and the settings and typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import type { ZahlenmauerProps } from "./sheet";
import { at, fixes, made, sane, stones } from "./zahlenmauer";

const P = (over: Partial<ZahlenmauerProps> = {}): ZahlenmauerProps => ({ base: 3, count: 1, columns: 1, max: 20, op: "+", given: "base", empty: false, seed: 1, ...over });

// Independent checks, not the code under test. Stone (r, c) is the sum (or product) of the two below it.
const cellsOf = (base: number): [number, number][] => {
  const out: [number, number][] = [];
  for (let r = 0; r < base; r++) for (let c = 0; c < base - r; c++) out.push([r, c]);
  return out;
};
const choose = (n: number, k: number): number => (k === 0 ? 1 : (choose(n - 1, k - 1) * n) / k);
const rowOf = (base: number, i: number): number[] => {
  const v = Array.from({ length: base }, () => 0);
  const [r, c] = cellsOf(base)[i];
  for (let j = 0; j <= r; j++) v[c + j] += choose(r, j);
  return v;
};

// Exact solve by Gauss-Jordan on fractions [num, den], written apart from the code under test. Returns the unique
// solution, or undefined when the rows do not fix all `n` unknowns or contradict.
function exact(n: number, rows: number[][], rhs: number[]): number[] | undefined {
  const gcd = (a: number, b: number): number => (b ? gcd(b, a % b) : Math.abs(a));
  const norm = ([a, b]: [number, number]): [number, number] => {
    const g = gcd(a, b) || 1;
    return b < 0 ? [-a / g, -b / g] : [a / g, b / g];
  };
  const sub = (x: [number, number], y: [number, number]): [number, number] => norm([x[0] * y[1] - y[0] * x[1], x[1] * y[1]]);
  const m = rows.map((r, i) => [...r.map((v): [number, number] => [v, 1]), [rhs[i], 1] as [number, number]]);
  let rank = 0;
  for (let col = 0; col < n; col++) {
    const p = m.findIndex((row, i) => i >= rank && row[col][0] !== 0);
    if (p < 0) continue;
    [m[rank], m[p]] = [m[p], m[rank]];
    const piv = m[rank][col];
    m[rank] = m[rank].map((v) => norm([v[0] * piv[1], v[1] * piv[0]]));
    for (let i = 0; i < m.length; i++) {
      if (i === rank || m[i][col][0] === 0) continue;
      const f = m[i][col];
      m[i] = m[i].map((v, k) => sub(v, norm([f[0] * m[rank][k][0], f[1] * m[rank][k][1]])));
    }
    rank++;
  }
  if (rank < n) return undefined;
  if (m.slice(n).some((row) => row[n][0] !== 0)) return undefined;
  return m.slice(0, n).map((row) => {
    if (row[n][1] !== 1) throw new Error("solution not whole");
    return row[n][0] || 0;
  });
}

// The primes dividing n, and how often each divides it.
const primeExp = (n: number, q: number): number => {
  let e = 0;
  for (; n % q === 0; n /= q) e++;
  return e;
};
const primesIn = (ns: number[]): number[] => {
  const out = new Set<number>();
  for (const n of ns) {
    let m = n;
    for (let q = 2; q * q <= m; q++) if (m % q === 0) {
      out.add(q);
      while (m % q === 0) m /= q;
    }
    if (m > 1) out.add(m);
  }
  return [...out];
};

// The base row a wall's given stones solve to, from the given stones alone: a unique solution or undefined.
function solveFromGiven(base: number, numbers: number[], given: boolean[], op: "+" | "*"): number[] | undefined {
  const idx = [...given.keys()].filter((i) => given[i]);
  const rows = idx.map((i) => rowOf(base, i));
  if (op === "+") return exact(base, rows, idx.map((i) => numbers[i]));
  // Times: a plus wall over the exponents of each prime that divides a number of the wall.
  const primes = primesIn(numbers);
  const exps: number[][] = primes.map((q) => exact(base, rows, idx.map((i) => primeExp(numbers[i], q))) as number[]);
  if (exps.some((e) => e === undefined)) return undefined;
  return Array.from({ length: base }, (_, j) => primes.reduce((acc, q, k) => acc * q ** exps[k][j], 1));
}

// The wall rule over every stone, unless the wall is wrong.
function holdsRule(base: number, numbers: number[], op: "+" | "*"): boolean {
  for (let r = 1; r < base; r++) for (let c = 0; c < base - r; c++) {
    const a = numbers[at(base, r - 1, c)];
    const b = numbers[at(base, r - 1, c + 1)];
    if (numbers[at(base, r, c)] !== (op === "+" ? a + b : a * b)) return false;
  }
  return true;
}

// Propagation as the pupils do it: a stone with two of its triangle known gives the third, until all are known.
function stepByStep(base: number, given: boolean[]): boolean {
  const k = [...given];
  for (let changed = true; changed; ) {
    changed = false;
    for (let r = 1; r < base; r++) for (let c = 0; c < base - r; c++) {
      const t = [at(base, r, c), at(base, r - 1, c), at(base, r - 1, c + 1)];
      const known = t.filter((i) => k[i]);
      if (known.length === 2) {
        k[t.find((i) => !k[i]) as number] = true;
        changed = true;
      }
    }
  }
  return k.every(Boolean);
}

const seeds = fc.integer({ min: -(2 ** 31), max: 2 ** 31 - 1 });
const base = fc.constantFrom(3, 4, 5);
const op = fc.constantFrom<"+" | "*">("+", "*");
const max = fc.constantFrom(10, 20, 100, 1000);
const given = fc.constantFrom<"base" | "mix">("base", "mix");

describe("made: the main proof", () => {
  it("every wall holds the rule and the given stones solve it to exactly one wall", () => {
    fc.assert(
      fc.property(seeds, base, op, max, given, (seed, b, o, m, g) => {
        const { walls } = made(P({ seed, base: b, op: o, max: m, given: g, count: 12 }));
        for (const w of walls) {
          expect(w.wrong).toBe(false);
          expect(holdsRule(b, w.numbers, o)).toBe(true);
          const solved = solveFromGiven(b, w.numbers, w.given, o);
          expect(solved).toEqual(w.numbers.slice(0, b));
        }
      }),
      { numRuns: 300 },
    );
  });
});

describe("made: mix", () => {
  it("gives exactly base stones, not all in the base row, solvable step by step", () => {
    fc.assert(
      fc.property(seeds, base, op, max, (seed, b, o, m) => {
        const { walls } = made(P({ seed, base: b, op: o, max: m, given: "mix", count: 12 }));
        for (const w of walls) {
          expect(w.given.filter(Boolean).length).toBe(b);
          expect(w.given.slice(b).some(Boolean)).toBe(true);
          expect(stepByStep(b, w.given)).toBe(true);
        }
      }),
      { numRuns: 300 },
    );
  });
});

describe("made: determinism and variety", () => {
  it("gives the same walls on two calls and different walls for different seeds", () => {
    fc.assert(
      fc.property(seeds, base, op, max, (seed, b, o, m) => {
        const p = P({ seed, base: b, op: o, max: m, given: "mix", count: 6 });
        expect(made(p)).toEqual(made({ ...p }));
      }),
      { numRuns: 100 },
    );
    const shapes = new Set<string>();
    for (let seed = 1; seed <= 20; seed++) shapes.add(JSON.stringify(made(P({ seed, base: 4, max: 100, count: 4 })).walls));
    expect(shapes.size).toBeGreaterThan(1);
  });
});

describe("made: fixed cases", () => {
  it("base 4, max 10, plus, count 8 gives 6 walls and loosens max and base, for every seed", () => {
    fc.assert(
      fc.property(seeds, (seed) => {
        const m = made(P({ base: 4, max: 10, count: 8, seed }));
        expect(m.walls.length).toBe(6);
        expect(m.loosen).toEqual(["max", "base"]);
      }),
      { numRuns: 100 },
    );
  });

  it("base 3, max 20, count 12 gives 12 walls and loosens nothing, for every seed", () => {
    fc.assert(
      fc.property(seeds, (seed) => {
        const m = made(P({ base: 3, max: 20, count: 12, seed }));
        expect(m.walls.length).toBe(12);
        expect(m.loosen).toEqual([]);
      }),
      { numRuns: 100 },
    );
  });
});

describe("made: limits", () => {
  it("keeps the top stone between 1 and max, the base stones 1 or more where they can, and no 0 with times", () => {
    fc.assert(
      fc.property(seeds, base, op, max, (seed, b, o, m) => {
        const { walls } = made(P({ seed, base: b, op: o, max: m, count: 12 }));
        for (const w of walls) {
          const top = w.numbers[w.numbers.length - 1];
          expect(top).toBeGreaterThanOrEqual(1);
          expect(top).toBeLessThanOrEqual(m);
          const zeroOk = o === "+" && m < 2 ** (b - 1);
          if (!zeroOk) expect(w.numbers.slice(0, b).every((v) => v >= 1)).toBe(true);
          expect(w.numbers.every((v) => Number.isInteger(v) && v >= 0)).toBe(true);
          if (o === "*") expect(w.numbers.includes(0)).toBe(false);
        }
        const bases = walls.map((w) => w.numbers.slice(0, b).join(","));
        expect(new Set(bases).size).toBe(bases.length);
      }),
      { numRuns: 200 },
    );
  });
});

describe("fixes", () => {
  it("is true for the base row, for two base corners and the top, and for all stones", () => {
    expect(fixes(3, [true, true, true, false, false, false])).toBe(true);
    expect(fixes(3, [true, false, true, false, false, true])).toBe(true);
    expect(fixes(3, [true, true, true, true, true, true])).toBe(true);
    expect(fixes(5, [true, true, true, true, true, false, false, false, false, false, false, false, false, false, false])).toBe(true);
  });

  it("is false for the middle row sum, for no stones, and for too few stones", () => {
    expect(fixes(3, [false, false, false, true, true, true])).toBe(false);
    expect(fixes(3, [false, false, false, false, false, false])).toBe(false);
    expect(fixes(3, [true, true, false, false, false, false])).toBe(false);
  });
});

describe("typed numbers", () => {
  it("(a) a typed base stone sits in the wall and the stones above follow", () => {
    const w = made(P({ typed: [[0, 0, 5]] })).walls[0];
    expect(w.numbers[0]).toBe(5);
    expect(w.wrong).toBe(false);
    expect(holdsRule(3, w.numbers, "+")).toBe(true);
  });

  it("(b) plus, base stones 1 and 2 and the top 9 give the middle base stone 3", () => {
    const w = made(P({ typed: [[0, 0, 1], [0, 2, 2], [0, 5, 9]] })).walls[0];
    expect(w.numbers[1]).toBe(3);
    expect(w.wrong).toBe(false);
    expect(holdsRule(3, w.numbers, "+")).toBe(true);
  });

  it("(c) plus, typed base stones 1, 1, 1 and top 5 are wrong, and the typed numbers lie over the generated ones", () => {
    const w = made(P({ typed: [[0, 0, 1], [0, 1, 1], [0, 2, 1], [0, 5, 5]] })).walls[0];
    expect(w.wrong).toBe(true);
    expect(w.numbers.slice(0, 3)).toEqual([1, 1, 1]);
    expect(w.numbers[5]).toBe(5);
  });

  it("(d) times, a typed top 7 is wrong and a typed top 9 gives the middle stone 3; a typed 0 is wrong", () => {
    const seven = made(P({ op: "*", typed: [[0, 0, 1], [0, 2, 1], [0, 5, 7]] })).walls[0];
    expect(seven.wrong).toBe(true);
    const nine = made(P({ op: "*", typed: [[0, 0, 1], [0, 2, 1], [0, 5, 9]] })).walls[0];
    expect(nine.numbers[1]).toBe(3);
    expect(nine.wrong).toBe(false);
    expect(holdsRule(3, nine.numbers, "*")).toBe(true);
    expect(made(P({ op: "*", typed: [[0, 0, 0]] })).walls[0].wrong).toBe(true);
  });
});

describe("sane", () => {
  it("gives the defaults for odd stored values", () => {
    const odd = {
      base: "4",
      count: 99,
      columns: 0,
      max: 15,
      op: "x",
      given: "other",
      free: [1, 2],
      empty: "yes",
      seed: NaN,
      typed: [[0, 0, 1.5], [5, 0, 1], [0, 99, 1], [0, 0, 10000], [0, 0, "2"], "nope"],
    } as unknown as ZahlenmauerProps;
    expect(sane(odd)).toEqual({ base: 3, count: 4, columns: 2, max: 20, op: "+", given: "base", free: [true, true, true, false, false, false], empty: false, seed: 0 });
  });

  it("keeps the last typed entry for a stone and drops out-of-range ones", () => {
    const p = sane(P({ typed: [[0, 0, 1], [0, 0, 2], [0, 6, 3]] }));
    expect(p.typed).toEqual([[0, 0, 2]]);
    expect(stones(3)).toBe(6);
  });
});

describe("own cases", () => {
  it("with free, every wall takes the free flags", () => {
    const free = [true, false, false, false, true, false];
    const { walls } = made(P({ given: "free", free, count: 3 }));
    for (const w of walls) expect(w.given).toEqual(free);
  });

  it("[0, 1, 4] in base 3 fixes the wall and stays step by step, while [0, 1] does not fix it", () => {
    expect(fixes(3, [true, true, false, false, true, false])).toBe(true);
    expect(stepByStep(3, [true, true, false, false, true, false])).toBe(true);
    expect(fixes(3, [true, true, false, false, false, false])).toBe(false);
  });
});
