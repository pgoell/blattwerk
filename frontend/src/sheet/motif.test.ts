// A shape's Muster and its Lineatur: the repeat, the ink, and which one is drawn.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { MOTIFS, PAPERS, fillMode, inkOf, motifOf, motifTile, paperOf, paperTile, scaleOf, tileOf, type Pen } from "./motif";

const inside = (pen: Pen, size: number) => {
  const half = pen.width / 2;
  const flat = pen.y1 === pen.y2;
  if (flat) {
    expect(pen.y1).toBeGreaterThanOrEqual(half);
    expect(pen.y1).toBeLessThanOrEqual(size - half);
    expect(pen.x1).toBe(0);
    expect(pen.x2).toBe(size);
  } else {
    expect(pen.x1).toBe(pen.x2);
    expect(pen.x1).toBeGreaterThanOrEqual(half);
    expect(pen.x1).toBeLessThanOrEqual(size - half);
    expect(pen.y1).toBe(0);
    expect(pen.y2).toBe(size);
  }
};

describe("scaleOf", () => {
  it("is 5 when nothing usable is stored, and stays inside 2 to 20", () => {
    expect(scaleOf(undefined)).toBe(5);
    expect(scaleOf("8")).toBe(5);
    expect(scaleOf(Number.NaN)).toBe(5);
    expect(scaleOf(0)).toBe(2);
    expect(scaleOf(40)).toBe(20);
    expect(scaleOf(8)).toBe(8);
  });
});

describe("inkOf", () => {
  it("is black when the Muster is schwarz-weiß, else the fill, else black", () => {
    expect(inkOf("#ffd43b", true)).toBe("#000000");
    expect(inkOf("#ffd43b", false)).toBe("#ffd43b");
    expect(inkOf("none", false)).toBe("#222222");
    expect(inkOf("#fff", false)).toBe("#222222");
  });
});

describe("fillMode", () => {
  it("is none, a colour, a Muster, or a Lineatur, and the Lineatur wins", () => {
    expect(fillMode({ fill: "none" })).toBe("none");
    expect(fillMode({ fill: "#ff0000" })).toBe("color");
    expect(fillMode({ fill: "#ff0000", motif: "stripes" })).toBe("pattern");
    expect(fillMode({ fill: "#ff0000", paper: "mm" })).toBe("ruling");
    expect(fillMode({ motif: "dots", paper: "k5" })).toBe("ruling");
    expect(motifOf({ motif: "dots", paper: "k5" })).toBeUndefined();
    expect(paperOf({ paper: "nope" })).toBeUndefined();
    expect(motifOf({ motif: "plaid" })).toBeUndefined();
  });
});

describe("motifTile", () => {
  it("draws bands, spots, a chequer and one wave, each the size of the repeat", () => {
    const stripes = motifTile("stripes", 8);
    expect(stripes).toEqual({ size: 8, ground: false, pens: [], blobs: [{ x: 0, y: 0, w: 8, h: 4 }] });
    const dots = motifTile("dots", 6);
    expect(dots.blobs).toEqual([{ cx: 3, cy: 3, r: 1 }]);
    const checks = motifTile("checks", 10);
    expect(checks.blobs).toEqual([{ x: 0, y: 0, w: 5, h: 5 }, { x: 5, y: 5, w: 5, h: 5 }]);
    const waves = motifTile("waves", 5);
    expect(waves.pens).toEqual([]);
    expect(waves.blobs).toEqual([{ d: "M0 2.5 Q1.25 1.5 2.5 2.5 T5 2.5", width: 5 / 12 }]);
  });

  it("keeps every mark inside the repeat", () => {
    fc.assert(
      fc.property(fc.constantFrom(...MOTIFS), fc.double({ min: 2, max: 20, noNaN: true }), (motif, scale) => {
        const tile = motifTile(motif, scale);
        expect(tile.size).toBe(scale);
        expect(tile.ground).toBe(false);
        for (const blob of tile.blobs) {
          if ("d" in blob) expect(blob.d.startsWith("M0 ") && blob.d.endsWith(`T${scale} ${scale / 2}`)).toBe(true);
          else if ("r" in blob) {
            expect(blob.cx - blob.r).toBeGreaterThanOrEqual(0);
            expect(blob.cx + blob.r).toBeLessThanOrEqual(scale);
          } else {
            expect(blob.x).toBeGreaterThanOrEqual(0);
            expect(blob.y).toBeGreaterThanOrEqual(0);
            expect(blob.x + blob.w).toBeLessThanOrEqual(scale);
            expect(blob.y + blob.h).toBeLessThanOrEqual(scale);
          }
        }
      }),
    );
  });
});

describe("paperTile", () => {
  it("is Millimeterpapier at 1 mm, with a heavier line at 5 mm and at 10 mm", () => {
    const tile = paperTile("mm");
    expect(tile.size).toBe(10);
    expect(tile.ground).toBe(true);
    const width = (at: number) => tile.pens.find((pen) => pen.y1 === at || (at === 0 && pen.y1 < 1 && pen.y1 === pen.y2))!.width;
    expect(width(0)).toBe(0.3);
    expect(width(5)).toBe(0.18);
    expect(width(1)).toBe(0.1);
    expect(tile.pens).toHaveLength(20);
    for (const pen of tile.pens) inside(pen, 10);
  });

  it("is Karo at 5, 7 and 10 mm, one line each way", () => {
    expect(paperTile("k5").size).toBe(5);
    expect(paperTile("k7").size).toBe(7);
    expect(paperTile("k10").size).toBe(10);
    for (const paper of ["k5", "k7", "k10"] as const) {
      const tile = paperTile(paper);
      expect(tile.ground).toBe(true);
      expect(tile.pens.map((pen) => pen.width)).toEqual([0.2, 0.2]);
      for (const pen of tile.pens) inside(pen, tile.size);
    }
  });

  it("draws the Lineatur when a Muster is stored too", () => {
    expect(tileOf({ motif: "waves", paper: "k7", scale: 4 })?.size).toBe(7);
    expect(tileOf({ motif: "nope" })).toBeUndefined();
    expect(PAPERS).toEqual(["mm", "k5", "k7", "k10"]);
  });
});
