// The Zahlenstrahl model: the ticks, the labels, the random and the free tasks, the arcs, and the sanitising of stored props.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { DEFAULTS, LEFT, LIMIT, RIGHT, count, crowded, made, sane, xOf, type ZahlenstrahlProps } from "./zahlenstrahl";

const P = (over: Partial<ZahlenstrahlProps> = {}): ZahlenstrahlProps => ({ ...DEFAULTS, seed: 1, ...over });
const values = (p: ZahlenstrahlProps) => made(p).ticks.map((t) => t.value);
const labelled = (p: ZahlenstrahlProps) => made(p).ticks.filter((t) => t.label).map((t) => t.value);
// Stored props as a sheet may hold them: anything at all.
const garbage = (x: unknown) => x as ZahlenstrahlProps;

const LABELS = ["all", "major", "ends", "none"] as const;
const SETTINGS = fc.record({
  start: fc.integer({ min: 0, max: 50 }),
  span: fc.integer({ min: 1, max: 60 }),
  labels: fc.constantFrom(...LABELS),
  boxes: fc.integer({ min: 0, max: 12 }),
  arrows: fc.integer({ min: 0, max: 6 }),
  seed: fc.integer(),
});
const settingsProps = (s: { start: number; span: number; labels: (typeof LABELS)[number]; boxes: number; arrows: number; seed: number }) =>
  P({ start: s.start, end: s.start + s.span, labels: s.labels, boxes: s.boxes, arrows: s.arrows, seed: s.seed });

describe("xOf spreads the ticks", () => {
  it("tick 0 at LEFT, the last at w - RIGHT, equal gaps", () => {
    for (const n of [2, 3, 7, 21, 200])
      for (const w of [40, 180, 297]) {
        expect(xOf(0, n, w)).toBe(LEFT);
        expect(xOf(n - 1, n, w)).toBeCloseTo(w - RIGHT, 9);
        const gap = xOf(1, n, w) - xOf(0, n, w);
        for (let i = 1; i < n; i++) expect(xOf(i, n, w) - xOf(i - 1, n, w)).toBeCloseTo(gap, 9);
      }
  });

  it("spreads any count over any width", () => {
    fc.assert(
      fc.property(fc.integer({ min: 2, max: 500 }), fc.integer({ min: 30, max: 400 }), (n, w) => {
        expect(xOf(0, n, w)).toBe(LEFT);
        expect(xOf(n - 1, n, w)).toBeCloseTo(w - RIGHT, 9);
        const gap = (w - LEFT - RIGHT) / (n - 1);
        for (let i = 0; i < n; i++) expect(xOf(i, n, w)).toBeCloseTo(LEFT + i * gap, 9);
      }),
    );
  });
});

describe("ticks and labels", () => {
  it("labels all: every tick shows its number", () => {
    const { ticks } = made(P({ start: 0, end: 10, labels: "all" }));
    expect(ticks.map((t) => t.label)).toEqual(Array(11).fill(true));
  });

  it("labels major: the long ticks, which are 0, 5 and 10 here", () => {
    const { ticks } = made(P({ start: 0, end: 10, labels: "major" }));
    expect(ticks.map((t) => t.long)).toEqual([true, false, false, false, false, true, false, false, false, false, true]);
    expect(labelled(P({ start: 0, end: 10, labels: "major" }))).toEqual([0, 5, 10]);
  });

  it("labels ends: the first and the last tick only", () => {
    expect(labelled(P({ start: 0, end: 10, labels: "ends" }))).toEqual([0, 10]);
  });

  it("labels none: no tick shows its number", () => {
    expect(labelled(P({ start: 0, end: 10, labels: "none" }))).toEqual([]);
  });

  it("a cut-out line 340 to 420 step 2, major 10", () => {
    const p = P({ start: 340, end: 420, minor: 2, major: 10, labels: "major" });
    expect(values(p)).toHaveLength(41);
    expect(values(p)[0]).toBe(340);
    expect(values(p)[40]).toBe(420);
    const long = made(p).ticks.filter((t) => t.long).map((t) => t.value);
    expect(long).toEqual([340, 350, 360, 370, 380, 390, 400, 410, 420]);
    expect(labelled(p)).toEqual(long);
  });

  it("an end that is no multiple of minor: the last tick is the last one not above end", () => {
    expect(values(P({ start: 0, end: 10, minor: 3 }))).toEqual([0, 3, 6, 9]);
    expect(values(P({ start: 1, end: 10, minor: 4 }))).toEqual([1, 5, 9]);
    expect(count(P({ start: 1, end: 10, minor: 4 }))).toBe(3);
  });

  it("LIMIT: LIMIT ticks are drawn, one more gives no ticks, arrows or arcs", () => {
    const ok = made(P({ start: 0, end: LIMIT - 1, arrows: 2, jumps: true }));
    expect(ok.ticks).toHaveLength(LIMIT);
    const over = made(P({ start: 0, end: LIMIT, arrows: 2, jumps: true, tasks: "free", marks: [[3, "arrow"]] }));
    expect(over).toEqual({ ticks: [], arrows: [], arcs: [] });
  });
});

describe("random tasks", () => {
  it("gives the counts asked for when the line has room", () => {
    const { ticks, arrows } = made(P({ end: 40, boxes: 3, arrows: 2 }));
    expect(ticks.filter((t) => t.task === "box")).toHaveLength(3);
    expect(ticks.filter((t) => t.task === "arrow")).toHaveLength(2);
    expect(arrows).toHaveLength(2);
  });

  it("never on the first tick, never two tasks on one tick, arrows are the arrow ticks", () => {
    fc.assert(
      fc.property(SETTINGS, (s) => {
        const { ticks, arrows } = made(settingsProps(s));
        expect(ticks[0].task).toBeUndefined();
        const tasked = ticks.filter((t) => t.task);
        expect(new Set(tasked.map((t) => t.value)).size).toBe(tasked.length);
        expect([...arrows].sort((a, b) => a - b)).toEqual(ticks.filter((t) => t.task === "arrow").map((t) => t.value).sort((a, b) => a - b));
      }),
    );
  });

  it("boxes go on ticks that show no number when there are enough of them", () => {
    fc.assert(
      fc.property(SETTINGS, (s) => {
        const p = settingsProps({ ...s, labels: s.labels === "all" ? "major" : s.labels });
        const { ticks } = made(p);
        const unlabelled = ticks.filter((t, i) => i > 0 && !t.label).length;
        const boxes = ticks.filter((t) => t.task === "box");
        if (unlabelled >= p.boxes!) expect(boxes.every((t) => !t.label)).toBe(true);
        expect(boxes).toHaveLength(Math.min(p.boxes!, ticks.length - 1));
      }),
    );
  });

  it("the same seed gives the same tasks, another seed other ones", () => {
    const p = P({ end: 100, boxes: 3, arrows: 2 });
    expect(made({ ...p, seed: 42 })).toEqual(made({ ...p, seed: 42 }));
    fc.assert(
      fc.property(fc.integer(), fc.integer(), (a, b) => {
        fc.pre(a !== b);
        expect(made({ ...p, seed: a })).not.toEqual(made({ ...p, seed: b }));
      }),
      { numRuns: 50 },
    );
  });
});

describe("free tasks", () => {
  it("marks on ticks show, marks off the grid or past the end are not drawn", () => {
    const p = P({ tasks: "free", start: 0, end: 20, minor: 2, marks: [[4, "box"], [7, "arrow"], [8, "arrow"], [40, "box"]] });
    const { ticks, arrows } = made(p);
    expect(ticks.filter((t) => t.task).map((t) => [t.value, t.task])).toEqual([
      [4, "box"],
      [8, "arrow"],
    ]);
    expect(arrows).toEqual([8]);
  });

  it("a mark off the grid is not drawn at all", () => {
    const { ticks, arrows } = made(P({ tasks: "free", start: 0, end: 10, minor: 2, marks: [[3, "box"]] }));
    expect(ticks.some((t) => t.task)).toBe(false);
    expect(arrows).toEqual([]);
  });
});

describe("arcs", () => {
  it("one arc per jump that ends on a tick, labelled +jump unless a label is given", () => {
    const { arcs } = made(P({ end: 20, major: 5, jumps: true, arcs: ["a", null] }));
    expect(arcs).toEqual([
      { from: 0, to: 5, label: "a" },
      { from: 5, to: 10, label: "+5" },
      { from: 10, to: 15, label: "+5" },
      { from: 15, to: 20, label: "+5" },
    ]);
  });

  it("a jump of 10 on a line to 25 gives two arcs; none without jumps", () => {
    expect(made(P({ end: 25, jump: 10, jumps: true })).arcs.map((a) => a.to)).toEqual([10, 20]);
    expect(made(P({ end: 25, jump: 10, jumps: false })).arcs).toEqual([]);
  });
});

describe("crowded", () => {
  it("warns when the ticks stand less than 1 mm apart", () => {
    expect(crowded(P({ start: 0, end: 100 }), 50)).toBe(true);
    expect(crowded(P({ start: 0, end: 20 }), 180)).toBe(false);
    expect(crowded(P({ start: 0, end: 1, minor: 5 }), 50)).toBe(false);
  });
});

describe("sane", () => {
  it("gives the defaults for wrong kinds and out-of-range values", () => {
    const s = sane(
      garbage({
        start: "x", end: -5, minor: 2, major: 7, labels: "weird", size: NaN, cut: "yes", tasks: 3, boxes: 99, arrows: -1,
        marks: "nope", jumps: 1, jump: 3, arcs: "x", seed: 1.5,
      }),
    );
    expect(s).toMatchObject({ ...DEFAULTS, minor: 2, major: 10, seed: 0 });
    expect(s.jump).toBeUndefined();
  });

  it("an end not above start gives start + 20, capped at MAX", () => {
    expect(sane(garbage({ start: 50, end: 10, seed: 1 }))).toMatchObject({ start: 50, end: 70 });
    expect(sane(garbage({ start: 999990, end: 5, seed: 1 }))).toMatchObject({ start: 999990, end: 1000000 });
  });

  it("keeps a valid major and jump, a jump not a multiple of minor is undefined", () => {
    expect(sane(garbage({ minor: 5, major: 10, jump: 10, seed: 1 }))).toMatchObject({ major: 10, jump: 10 });
    expect(sane(garbage({ minor: 5, major: 10, jump: 7, seed: 1 })).jump).toBeUndefined();
  });

  it("drops bad marks and keeps the last of two for one number", () => {
    const s = sane(garbage({ marks: [[3, "box"], [3, "arrow"], [4.5, "box"], [5, "x"], "bad", [6, "arrow"]], seed: 1 }));
    expect(s.marks).toEqual([[3, "arrow"], [6, "arrow"]]);
  });

  it("an arc label that is not a string becomes null", () => {
    expect(sane(garbage({ arcs: ["a", 3, null], seed: 1 })).arcs).toEqual(["a", null, null]);
  });

  it("does not mutate its input", () => {
    const input = garbage({ start: "x", marks: [[3, "box"]], arcs: ["a", 3], seed: 2.5 });
    const copy = structuredClone(input);
    sane(input);
    expect(input).toEqual(copy);
  });

  it("is idempotent on anything", () => {
    fc.assert(
      fc.property(fc.anything(), (x) => {
        const once = sane(garbage(x));
        expect(sane(once)).toEqual(once);
      }),
    );
  });
});
