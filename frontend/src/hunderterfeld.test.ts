// The Hunderterfeld model: the shown numbers, the tints, the Ausschnitt, the dots, the sanitising of stored props, the seed.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { DEFAULTS, TINT, made, sane, type HunderterfeldProps } from "./hunderterfeld";

const P = (over: Partial<HunderterfeldProps> = {}): HunderterfeldProps => ({ ...DEFAULTS, seed: 1, ...over });
const shown = (p: HunderterfeldProps) => made(p).cells.filter((c) => c.shown).map((c) => c.i);
const hiddenDrawn = (p: HunderterfeldProps) => made(p).cells.filter((c) => c.drawn && !c.shown).map((c) => c.i);
const tinted = (p: HunderterfeldProps) => made(p).cells.filter((c) => c.tint);
const tintedValues = (p: HunderterfeldProps) => tinted(p).map((c) => c.value);
const range = (lo: number, hi: number) => Array.from({ length: hi - lo + 1 }, (_, k) => lo + k);
// Stored props as a sheet may hold them: anything at all.
const garbage = (x: unknown) => x as HunderterfeldProps;

const grey = (hex: string) => {
  const [r, g, b] = [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16));
  return 0.299 * r + 0.587 * g + 0.114 * b;
};

describe("show", () => {
  it("all: every number shows, from 1 gives 1 to 100", () => {
    const { cells } = made(P({ show: "all" }));
    expect(shown(P({ show: "all" }))).toEqual(range(0, 99));
    expect(cells[0].value).toBe(1);
    expect(cells[99].value).toBe(100);
  });

  it("none: no number shows", () => {
    expect(shown(P({ show: "none" }))).toEqual([]);
  });

  it("free: all but the cells in hidden", () => {
    const hidden = [0, 5, 99];
    expect(shown(P({ show: "free", hidden }))).toEqual(range(0, 99).filter((i) => !hidden.includes(i)));
  });

  it("random: exactly hide cells hidden, the same seed the same cells, another seed other cells", () => {
    fc.assert(
      fc.property(fc.integer(), fc.integer({ min: 0, max: 100 }), (seed, hide) => {
        expect(hiddenDrawn(P({ show: "random", hide, seed }))).toHaveLength(hide);
      }),
      { numRuns: 100 },
    );
    expect(hiddenDrawn(P({ show: "random", seed: 7 }))).toEqual(hiddenDrawn(P({ show: "random", seed: 7 })));
    expect(hiddenDrawn(P({ show: "random", seed: 7 }))).not.toEqual(hiddenDrawn(P({ show: "random", seed: 8 })));
  });

  it("random: a higher hide keeps the cells hidden before (no number flickers in as the teacher raises hide)", () => {
    const low = hiddenDrawn(P({ show: "random", hide: 20, seed: 3 }));
    const high = hiddenDrawn(P({ show: "random", hide: 25, seed: 3 }));
    expect(high.filter((i) => low.includes(i))).toEqual(low);
  });
});

describe("tint rules", () => {
  it("even: the even numbers, from 1 and from 0", () => {
    expect(tintedValues(P({ tint: "even" }))).toEqual(range(1, 50).map((k) => 2 * k));
    expect(tintedValues(P({ tint: "even", from: 0 }))).toEqual(range(0, 49).map((k) => 2 * k));
  });

  it("even in colour 2 gives tint 2", () => {
    const t = tinted(P({ tint: "even", color: 2 }));
    expect(t.length).toBe(50);
    expect(t.every((c) => c.tint === 2)).toBe(true);
  });

  it("times 3 from 0 tints 3 to 30, not 0", () => {
    expect(tintedValues(P({ tint: "times", times: 3, from: 0 }))).toEqual([3, 6, 9, 12, 15, 18, 21, 24, 27, 30]);
  });

  it("times 3 from 1 tints 3 to 30", () => {
    expect(tintedValues(P({ tint: "times", times: 3, from: 1 }))).toEqual([3, 6, 9, 12, 15, 18, 21, 24, 27, 30]);
  });

  it("times 10 from 1 reaches 100, from 0 it stops at 90", () => {
    expect(tintedValues(P({ tint: "times", times: 10, from: 1 }))).toEqual(range(1, 10).map((k) => 10 * k));
    expect(tintedValues(P({ tint: "times", times: 10, from: 0 }))).toEqual(range(1, 9).map((k) => 10 * k));
  });

  it("row 2 is the numbers 11 to 20 from 1, 10 to 19 from 0", () => {
    expect(tintedValues(P({ tint: "row", line: 2 }))).toEqual(range(11, 20));
    expect(tintedValues(P({ tint: "row", line: 2, from: 0 }))).toEqual(range(10, 19));
  });

  it("column 3 is every tenth from the third from 1, from 0 the same count from 2", () => {
    expect(tintedValues(P({ tint: "column", line: 3 }))).toEqual(range(0, 9).map((k) => 3 + 10 * k));
    expect(tintedValues(P({ tint: "column", line: 3, from: 0 }))).toEqual(range(0, 9).map((k) => 2 + 10 * k));
  });

  it("row in colour 2 gives tint 2", () => {
    expect(tinted(P({ tint: "row", line: 1, color: 2 })).every((c) => c.tint === 2)).toBe(true);
  });

  it("free: the cells of tints, each in its own colour, colour ignored", () => {
    const t = made(P({ tint: "free", tints: [[3, 2], [7, 1]], color: 2 })).cells.map((c) => c.tint);
    expect(t.slice(0, 8)).toEqual([0, 0, 0, 2, 0, 0, 0, 1]);
    expect(t.filter(Boolean)).toHaveLength(2);
  });

  it("tints only on drawn cells: a tinted row in a cut-out tints only the cut-out's cell in it", () => {
    const t = tinted(P({ tint: "row", line: 4, cut: true }));
    expect(t.map((c) => c.i)).toEqual([34]);
  });
});

describe("cut-out", () => {
  it("default cross: frame [30, 30, 30, 30], drawn cells are the cross", () => {
    const m = made(P({ cut: true }));
    expect(m.frame).toEqual([30, 30, 30, 30]);
    expect(m.cells.filter((c) => c.drawn).map((c) => c.i)).toEqual([34, 43, 44, 45, 54]);
  });

  it("a 2 by 4 piece: frame [10, 10, 40, 40] centred on it", () => {
    const shape = [21, 22, 23, 24, 31, 32, 33, 34];
    expect(made(P({ cut: true, shape, given: 21 })).frame).toEqual([10, 10, 40, 40]);
  });

  it("only the given cell shows, its number kept, show ignored", () => {
    expect(shown(P({ cut: true, given: 45, show: "all" }))).toEqual([45]);
    expect(shown(P({ cut: true, given: 44, show: "none" }))).toEqual([44]);
  });

  it("a given not in shape gives the lowest cell of shape", () => {
    expect(shown(P({ cut: true, given: 0 }))).toEqual([34]);
  });

  it("an empty shape: frame [0, 0, 100, 100], no cell drawn", () => {
    const m = made(P({ cut: true, shape: [] }));
    expect(m.frame).toEqual([0, 0, 100, 100]);
    expect(m.cells.some((c) => c.drawn || c.shown)).toBe(false);
  });

  it("without cut the frame is the whole field and every cell is drawn", () => {
    const m = made(P({ shape: [34] }));
    expect(m.frame).toEqual([0, 0, 100, 100]);
    expect(m.cells.every((c) => c.drawn)).toBe(true);
  });
});

describe("dots", () => {
  it("count: the first dots, row by row", () => {
    const f = made(P({ fill: "count", dots: 13 })).filled;
    expect(f).toHaveLength(100);
    expect(f.map((x, i) => (x ? i : -1)).filter((i) => i >= 0)).toEqual(range(0, 12));
  });

  it("free: the dots in filled", () => {
    const f = made(P({ fill: "free", filled: [5, 50], dots: 90 })).filled;
    expect(f.map((x, i) => (x ? i : -1)).filter((i) => i >= 0)).toEqual([5, 50]);
  });
});

describe("sane", () => {
  it("wrong values give the defaults", () => {
    const q = sane(garbage({ look: "x", from: 2, show: "x", hide: 1.5, tint: "x", times: 11, line: 0, color: 3, cut: "yes", fill: "x", dots: -1, seed: 1.5 }));
    expect(q).toEqual({ ...DEFAULTS, seed: 0 });
  });

  it("lists keep order and drop bad and repeated entries", () => {
    const q = sane(garbage({ ...DEFAULTS, shape: [44, 44, 1.5, -3, 100, "a", 12, 34], tints: [[3, 2], [3, 1], [4, 3], [5, "x"], [6, 1]] }));
    expect(q.shape).toEqual([44, 12, 34]);
    expect(q.tints).toEqual([[3, 2], [6, 1]]);
  });

  it("given is kept as stored when whole and in 0 to 99, and out of range gives the default", () => {
    expect(sane(garbage({ given: 0 })).given).toBe(0);
    expect(sane(garbage({ given: 100 })).given).toBe(44);
  });

  it("never throws on anything, and is idempotent", () => {
    fc.assert(
      fc.property(fc.anything(), (x) => {
        const once = sane(garbage(x));
        expect(sane(once)).toEqual(once);
        expect(once.hide).toBeGreaterThanOrEqual(0);
        expect(once.hide).toBeLessThanOrEqual(100);
        made(once);
      }),
      { numRuns: 200 },
    );
  });
});

describe("tint colours", () => {
  it("the greys of the two tints, white and the key's red differ pairwise by at least 40", () => {
    const greys = [TINT[1], TINT[2], "#ffffff", "#c0392b"].map(grey);
    const gaps = greys.flatMap((a, i) => greys.slice(i + 1).map((b) => Math.abs(a - b)));
    expect(Math.min(...gaps)).toBeGreaterThanOrEqual(40);
  });
});
