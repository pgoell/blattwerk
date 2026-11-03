// The Formen from #835: geometry only, no browser. The numbers for the five-point star are the ones
// shape.tsx drew before a spike count existed.
import { describe, expect, it } from "vitest";
import {
  arcGeometry,
  arcHandle,
  barStrips,
  bulgeFrom,
  circlePath,
  cornersOf,
  diamondPoints,
  filledOf,
  hubAt,
  partsOf,
  pieWedges,
  polygonPoints,
  roomOf,
  spikesOf,
  starInnerAt,
  starPoints,
  thoughtPath,
} from "./formen";

const FIVE = [
  [20, 1],
  [24.462470579970194, 23.205232417897268],
  [39.00112913733745, 23.154236775153706],
  [27.220429072188235, 36.826829494761654],
  [31.743343631500515, 59.00054487216526],
  [20, 45.24543946932006],
  [8.256656368499488, 59.00054487216526],
  [12.779570927811768, 36.826829494761654],
  [0.9988708626625435, 23.154236775153713],
  [15.537529420029802, 23.205232417897268],
];

describe("Raute", () => {
  it("is a rhombus on the middle of each side", () => {
    expect(diamondPoints(40, 40, 0)).toEqual([
      [20, 0],
      [40, 20],
      [20, 40],
      [0, 20],
    ]);
    expect(diamondPoints(60, 40, 1)[0]).toEqual([30, 1]);
  });
});

describe("Vieleck", () => {
  it("has from 5 to 15 corners, and a point at the top", () => {
    expect(cornersOf({})).toBe(6);
    expect(cornersOf({ corners: 2 })).toBe(5);
    expect(cornersOf({ corners: 99 })).toBe(15);
    expect(polygonPoints(40, 40, 0, { corners: 5 })).toHaveLength(5);
    expect(polygonPoints(40, 40, 0, { corners: 15 })).toHaveLength(15);
    const hex = polygonPoints(40, 40, 0, {});
    expect(hex).toHaveLength(6);
    expect(hex[0][0]).toBeCloseTo(20);
    expect(hex[0][1]).toBeCloseTo(0);
  });
});

describe("Stern", () => {
  it("keeps the five-point star when no spike count is set", () => {
    const pts = starPoints(40, 60, 1, {});
    expect(pts).toHaveLength(10);
    pts.forEach((p, i) => {
      expect(p[0]).toBeCloseTo(FIVE[i][0]);
      expect(p[1]).toBeCloseTo(FIVE[i][1]);
    });
    expect(starPoints(40, 60, 1, { spikes: 5, inner: 0.2 })[1][0]).not.toBeCloseTo(FIVE[1][0]);
  });

  it("takes 3 to 35 points, and the handle sets the depth", () => {
    expect(spikesOf({})).toBe(5);
    expect(spikesOf({ spikes: 1 })).toBe(3);
    expect(spikesOf({ spikes: 80 })).toBe(35);
    expect(starPoints(40, 40, 0, { spikes: 3 })).toHaveLength(6);
    expect(starPoints(40, 40, 0, { spikes: 35 })).toHaveLength(70);
    const n = 7;
    const handle = starPoints(80, 50, 0, { spikes: n, inner: 0.4 })[2 * n - 1];
    expect(starInnerAt(80, 50, handle[0], handle[1], n)).toBeCloseTo(0.4, 2);
  });
});

describe("Bogen", () => {
  it("bends off the straight line, and the handle is that bend", () => {
    const flat = arcGeometry(60, 30, 1, 0, 0).curve;
    const bent = arcGeometry(60, 30, 1, 1, 0).curve;
    expect(flat).not.toBe(bent);
    expect(flat).toContain("Q");
    const at = arcHandle(60, 30, 1, 0.4);
    expect(bulgeFrom(60, 30, 1, at[1])).toBeCloseTo(0.4);
    const { curve, head } = arcGeometry(60, 30, 1, 0.5, 4);
    expect(curve.startsWith("M")).toBe(true);
    expect(head).toHaveLength(3);
  });
});

describe("Gedankenwolke", () => {
  it("is a body with a tail of three small bubbles", () => {
    const d = thoughtPath(60, 40, 1, [0.2, 1]);
    expect(d.match(/A/g)).toHaveLength(8);
  });
});

describe("Brüche", () => {
  it("splits a circle into 2 to 50 parts and fills the ones asked for", () => {
    expect(partsOf({})).toBe(4);
    expect(partsOf({ parts: 1 })).toBe(2);
    expect(partsOf({ parts: 80 })).toBe(50);
    expect(filledOf({})).toBe(1);
    expect(filledOf({ parts: 4, filled: 9 })).toBe(4);
    const wedges = pieWedges(40, 40, 1, { parts: 8, filled: 3 });
    expect(wedges).toHaveLength(8);
    expect(wedges.filter((w) => w.on)).toHaveLength(3);
    expect(wedges[0].d.startsWith("M")).toBe(true);
  });

  it("splits a bar the same way, from the left", () => {
    const strips = barStrips(60, 20, 1, { parts: 5, filled: 2 });
    expect(strips).toHaveLength(5);
    expect(strips.filter((s) => s.on).map((s) => s.x)).toEqual([strips[0].x, strips[1].x]);
    const span = strips[4].x + strips[4].w - strips[0].x;
    expect(span).toBeCloseTo(58);
  });
});

describe("Kreis", () => {
  it("marks the centre", () => {
    expect(hubAt(40, 30)).toEqual([20, 15]);
  });
});

describe("Quadratisch and Kreisförmig", () => {
  it("draw in the centred square, and Kreisförmig is a circle", () => {
    expect(roomOf(80, 40, "square")).toEqual({ x: 20, y: 0, s: 40 });
    expect(roomOf(80, 40, "round")).toEqual({ x: 20, y: 0, s: 40 });
    expect(roomOf(80, 40, undefined)).toBeUndefined();
    expect(circlePath(20, 0, 40, 0)).toMatch(/^M20,20 A20,20/);
  });
});
