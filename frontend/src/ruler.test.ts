// A line as a ruler: centimetre ticks with numbers, millimetres on request, and a typed angle.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { inked } from "./pages/Format";
import { REACH, aimed, shownAngle, ticksOf, type Tick } from "./ruler";
import type { ShapeBlock } from "./sheet";

function line(over: Partial<Omit<ShapeBlock, "props">> & { props?: Partial<ShapeBlock["props"]> } = {}): ShapeBlock {
  const { props, ...box } = over;
  return {
    id: "a",
    type: "shape",
    x: 40,
    y: 80,
    w: 50,
    h: 0,
    z: 1,
    locked: false,
    ...box,
    props: { kind: "line", fill: "none", stroke: "#222222", strokeWidth: 0.5, ...props },
  };
}

const at = (ticks: Tick[], kind: Tick["kind"]) => ticks.filter((t) => t.kind === kind).map((t) => t.at);

describe("ticksOf", () => {
  it("puts a numbered centimetre tick every 10 mm, and none between", () => {
    const ticks = ticksOf(50, false);
    expect(ticks.map((t) => t.at)).toEqual([0, 10, 20, 30, 40, 50]);
    expect(ticks.map((t) => t.n)).toEqual([0, 1, 2, 3, 4, 5]);
    expect(ticks.every((t) => t.kind === "cm" && t.reach === REACH.cm)).toBe(true);
  });

  it("stops at the last whole millimetre and keeps the tick that lands on the length", () => {
    expect(ticksOf(53.2, false).map((t) => t.at)).toEqual([0, 10, 20, 30, 40, 50]);
    expect(ticksOf(9.2, false).map((t) => t.n)).toEqual([0]);
    expect(ticksOf(0, false)).toEqual([]);
    expect(ticksOf(Number.NaN, true)).toEqual([]);
  });

  it("with millimetres draws every millimetre, longer at the half and longest at the centimetre", () => {
    const ticks = ticksOf(30, true);
    expect(ticks.map((t) => t.at)).toEqual(Array.from({ length: 31 }, (_, i) => i));
    expect(at(ticks, "cm")).toEqual([0, 10, 20, 30]);
    expect(at(ticks, "half")).toEqual([5, 15, 25]);
    expect(at(ticks, "mm")).toHaveLength(31 - 4 - 3);
    const reach = Object.fromEntries(ticks.map((t) => [t.kind, t.reach]));
    expect(reach.cm).toBeGreaterThan(reach.half);
    expect(reach.half).toBeGreaterThan(reach.mm);
    expect(reach.mm).toBeGreaterThan(0);
  });
});

describe("aimed", () => {
  it("turns a level line about its centre and keeps its length", () => {
    const flat = line();
    const down = aimed(flat, 90);
    expect(down.w).toBeCloseTo(0, 2);
    expect(down.h).toBeCloseTo(50, 2);
    expect(down.props.from).toBe("nw");
    expect(down.x + down.w / 2).toBeCloseTo(flat.x + flat.w / 2, 2);
    expect(down.y + down.h / 2).toBeCloseTo(flat.y + flat.h / 2, 2);
    expect(shownAngle({ ...flat, ...down })).toBe(90);

    const left = aimed(flat, 180);
    expect(left.h).toBeCloseTo(0, 2);
    expect(left.w).toBeCloseTo(50, 2);
    expect(left.props.from).toBe("ne");
    expect(shownAngle({ ...flat, ...left })).toBe(180);

    const up = aimed(flat, -90);
    expect(up.props.from).toBe("sw");
    expect(shownAngle({ ...flat, ...up })).toBe(270);
    expect(shownAngle({ ...flat, ...aimed(flat, 370) })).toBe(10);
  });

  it("shows the angle that was typed, for a line long enough to hold it", () => {
    fc.assert(
      fc.property(fc.integer({ min: 10, max: 300 }), fc.integer({ min: 0, max: 359 }), (length, deg) => {
        const next = aimed(line({ w: length }), deg);
        const got = shownAngle({ ...line({ w: length }), ...next });
        const gap = Math.min(Math.abs(got - deg), 360 - Math.abs(got - deg));
        expect(gap).toBeLessThanOrEqual(0.15);
        expect(Math.hypot(next.w, next.h)).toBeCloseTo(length, 1);
      }),
    );
  });
});

describe("inked", () => {
  it("keeps a ruler's ticks and numbers on one side of a level line", () => {
    const b = line({ props: { ruler: true } });
    const ink = inked(b);
    expect(ink.y).toBeLessThan(b.y - REACH.cm);
    expect(ink.y + ink.h).toBeLessThanOrEqual(b.y + b.props.strokeWidth / 2 + 0.05);
    expect(ink.x).toBeLessThan(b.x);
    expect(ink.x + ink.w).toBeGreaterThan(b.x + b.w);
  });

  it("puts the same side up when the line points left", () => {
    const b = line({ props: { ruler: true, from: "ne" } });
    const ink = inked(b);
    expect(ink.y).toBeLessThan(b.y - REACH.cm);
    expect(ink.y + ink.h).toBeLessThanOrEqual(b.y + 0.3);
  });

  it("leaves a line with no ruler as wide as its stroke", () => {
    const b = line();
    const ink = inked(b);
    expect(ink.h).toBeLessThan(1);
    expect(ink.y).toBeGreaterThan(b.y - 1);
  });
});
