import { describe, expect, it } from "vitest";
import { cover, paint, trim, turnedCut, type Ground } from "./ground";

const page = { w: 210, h: 297 };

function ground(over: Partial<Ground> = {}): Ground {
  return { upload: 1, ratio: 1.5, cut: [0, 0, 0, 0], ...over };
}

describe("cover", () => {
  it("fills the page and keeps the picture's proportions", () => {
    const box = cover(page.w, page.h, 1.5);
    expect(box.w / box.h).toBeCloseTo(1.5, 5);
    expect(box.w).toBeGreaterThanOrEqual(page.w - 0.001);
    expect(box.h).toBeGreaterThanOrEqual(page.h - 0.001);
    // One side meets the page: the picture is not larger than the cover needs.
    expect(Math.min(box.w - page.w, box.h - page.h)).toBeCloseTo(0, 5);
  });

  it("a square picture on its side still covers", () => {
    const box = cover(297, 210, 1);
    expect(box.w).toBeCloseTo(297, 5);
    expect(box.h).toBeCloseTo(297, 5);
  });
});

describe("paint", () => {
  it("centres the cover", () => {
    const drawn = paint(page.w, page.h, ground());
    expect(drawn.x + drawn.width / 2).toBeCloseTo(page.w / 2, 5);
    expect(drawn.y + drawn.height / 2).toBeCloseTo(page.h / 2, 5);
    expect(drawn.opacity).toBe(1);
    expect(drawn.turns).toBe(0);
  });

  it("shifts by at and grows by scale", () => {
    const drawn = paint(page.w, page.h, ground({ at: [10, -4], scale: 2 }));
    const plain = paint(page.w, page.h, ground());
    expect(drawn.width).toBeCloseTo(plain.width * 2, 5);
    expect(drawn.x - (page.w - drawn.width) / 2).toBeCloseTo(10, 5);
    expect(drawn.y - (page.h - drawn.height) / 2).toBeCloseTo(-4, 5);
    expect(drawn.opacity).toBe(1);
  });

  it("a quarter turn swaps the proportions", () => {
    const drawn = paint(page.w, page.h, ground({ ratio: 2, turns: 1 }));
    expect(drawn.width / drawn.height).toBeCloseTo(0.5, 5);
    expect(drawn.turns).toBe(1);
  });

  it("reads a missing fade as solid", () => {
    expect(paint(page.w, page.h, ground({ opacity: 0.25 })).opacity).toBe(0.25);
  });
});

describe("turnedCut", () => {
  it("sends the left edge to the top on a clockwise quarter turn", () => {
    expect(turnedCut([0.1, 0.2, 0.3, 0.4])).toEqual([0.4, 0.1, 0.2, 0.3]);
  });
});

describe("trim", () => {
  it("cuts more off an edge and keeps a share of the picture", () => {
    expect(trim([0, 0, 0, 0], 0, 0.2)).toEqual([0.2, 0, 0, 0]);
    expect(trim([0.9, 0, 0, 0], 0, 0.2)[0]).toBeCloseTo(0.95, 5);
    expect(trim([0, 0, 0, 0], 2, -0.1)).toEqual([0, 0, 0, 0]);
  });
});
