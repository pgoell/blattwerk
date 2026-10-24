// Sane props, the block's height, and a square that is made.
import { describe, expect, it } from "vitest";
import {
  DEFAULTS,
  heightFor,
  made,
  opLabel,
  sane,
} from "./malquadrat";
import {
  P,
  SEEDS,
} from "./malquadrat.fixtures";

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

