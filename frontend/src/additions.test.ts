// Issue #845: coloured clock hands and both times, a Zahlenstrahl that can end in an arrow with ticks
// under the line, a Rechendreieck that multiplies, and a Zahlenmauer with 2 or 6 base stones.
import { describe, expect, it } from "vitest";
import { SIDES, made as madeDreieck, sane as saneDreieck, signOf, type RechendreieckProps } from "./rechendreieck";
import { DEFAULTS as UHR, handStroke, sane as saneUhr, written, type UhrProps } from "./uhr";
import type { ZahlenmauerProps } from "./sheet";
import { made as madeMauer, sane as saneMauer, stones } from "./zahlenmauer";
import { DEFAULTS as STRAHL, arrowTip, sane as saneStrahl, tickLine, type ZahlenstrahlProps } from "./zahlenstrahl";

const Uhr = (over: Partial<UhrProps> = {}): UhrProps => ({ ...UHR, seed: 1, ...over });
const Strahl = (over: Partial<ZahlenstrahlProps> = {}): ZahlenstrahlProps => ({ ...STRAHL, seed: 1, ...over });
const Dreieck = (over: Partial<RechendreieckProps> = {}): RechendreieckProps => ({
  count: 4,
  columns: 4,
  max: 20,
  given: "inner",
  empty: false,
  op: "+",
  seed: 1,
  ...over,
});
const Mauer = (over: Partial<ZahlenmauerProps> = {}): ZahlenmauerProps => ({
  base: 3,
  count: 1,
  columns: 1,
  max: 20,
  op: "+",
  given: "base",
  empty: false,
  seed: 1,
  ...over,
});

describe("Uhr: both times and coloured hands", () => {
  it("format both writes the 12-hour time and the other time of the same hands", () => {
    const p = saneUhr({ ...Uhr(), format: "both" } as UhrProps);
    expect(p.format).toBe("both");
    expect(written(3 * 60 + 30, p)).toBe("3:30 Uhr\n15:30 Uhr");
    expect(written(15 * 60 + 30, p)).toBe("3:30 Uhr\n15:30 Uhr");
    expect(written(12 * 60, p)).toBe("12:00 Uhr\n0:00 Uhr");
    expect(written(0, p)).toBe("12:00 Uhr\n0:00 Uhr");
    expect(written(12 * 60 + 30, p)).toBe("12:30 Uhr\n0:30 Uhr");
    expect(written(60 + 5, p)).toBe("1:05 Uhr\n13:05 Uhr");
  });

  it("colours stays off unless the sheet asks, and a bad value is off", () => {
    expect(saneUhr(Uhr()).colours).toBe(false);
    expect(saneUhr({ ...Uhr(), colours: true }).colours).toBe(true);
    expect(saneUhr({ ...Uhr(), colours: "yes" } as unknown as UhrProps).colours).toBe(false);
  });

  it("a coloured hour hand is blue and the minute hand red; without colour the old ink stays", () => {
    expect(handStroke("hour", { colours: true, task: "read" }, false)).toBe("#1a56db");
    expect(handStroke("minute", { colours: true, task: "read" }, false)).toBe("#e02424");
    expect(handStroke("hour", { colours: true, task: "draw" }, true)).toBe("#1a56db");
    expect(handStroke("minute", { colours: true, task: "draw" }, true)).toBe("#e02424");
    expect(handStroke("hour", { colours: false, task: "read" }, false)).toBe("#222");
    expect(handStroke("minute", { colours: false, task: "draw" }, true)).toBe("#c0392b");
  });
});

describe("Zahlenstrahl: arrow at the end, ticks below the line", () => {
  it("point and under are off unless the sheet asks", () => {
    expect(saneStrahl(Strahl()).point).toBe(false);
    expect(saneStrahl(Strahl()).under).toBe(false);
    const on = saneStrahl({ ...Strahl(), point: true, under: true });
    expect(on.point).toBe(true);
    expect(on.under).toBe(true);
    expect(saneStrahl({ ...Strahl(), point: "yes", under: 1 } as unknown as ZahlenstrahlProps).point).toBe(false);
  });

  it("the last tick is omitted when the arrow replaces it, and under hangs each stroke below the line", () => {
    expect(tickLine(false, true, 20, false, false)).toEqual({ y1: 17, y2: 23 });
    expect(tickLine(false, false, 20, false, false)).toEqual({ y1: 18.5, y2: 21.5 });
    expect(tickLine(true, true, 20, false, false)).toEqual({ y1: 20, y2: 23 });
    expect(tickLine(true, false, 20, false, true)).toEqual({ y1: 20, y2: 21.5 });
    expect(tickLine(false, true, 20, true, true)).toBeUndefined();
    expect(arrowTip(false, 170, 180)).toBe(179);
    expect(arrowTip(true, 170, 180)).toBe(170);
  });
});

describe("Rechendreieck: Mal", () => {
  it("op times is kept, and the sign in the middle is × only then", () => {
    expect(saneDreieck(Dreieck()).op).toBe("+");
    expect(saneDreieck(Dreieck({ op: "*" })).op).toBe("*");
    expect(saneDreieck({ ...Dreieck(), op: "x" } as unknown as RechendreieckProps).op).toBe("+");
    expect(signOf("*")).toBe("\u00d7");
    expect(signOf("+")).toBe("");
  });

  it("each outer field is the product of its side, and no product is above max", () => {
    const { triangles } = madeDreieck(Dreieck({ op: "*", max: 20, count: 12, seed: 4 }));
    expect(triangles).toHaveLength(12);
    const seen = new Set<string>();
    for (const t of triangles) {
      const [a, b, c] = t.numbers;
      expect(a).toBeGreaterThanOrEqual(1);
      expect(b).toBeGreaterThanOrEqual(1);
      expect(c).toBeGreaterThanOrEqual(1);
      SIDES.forEach(([x, y], s) => {
        expect(t.numbers[3 + s]).toBe(t.numbers[x] * t.numbers[y]);
        expect(t.numbers[3 + s]).toBeLessThanOrEqual(20);
      });
      seen.add([a, b, c].join(","));
    }
    expect(seen.size).toBe(12);
  });

  it("a typed inner keeps the other inners and rebuilds the products", () => {
    const gen = madeDreieck(Dreieck({ op: "*", seed: 3, count: 1, max: 100 })).triangles[0].numbers;
    const typed = madeDreieck(Dreieck({ op: "*", seed: 3, count: 1, max: 100, typed: [[0, 0, 4]] })).triangles[0];
    expect(typed.wrong).toBe(false);
    expect(typed.numbers[0]).toBe(4);
    expect(typed.numbers[1]).toBe(gen[1]);
    expect(typed.numbers[2]).toBe(gen[2]);
    expect(typed.numbers[3]).toBe(4 * gen[1]);
    expect(typed.numbers[4]).toBe(gen[1] * gen[2]);
    expect(typed.numbers[5]).toBe(4 * gen[2]);
  });

  it("one or two typed numbers take the nearest product triangle", () => {
    const gen = madeDreieck(Dreieck({ op: "*", seed: 8, count: 1, max: 20 })).triangles[0].numbers.slice(0, 3);
    const raw: [number, number][] = [[3, 12], [1, 3]];
    const shown = new Map(raw);
    let best: number[] | undefined;
    const distance = (t: number[]) => t.reduce((s, v, i) => s + Math.abs(v - gen[i]), 0);
    for (let a = 0; a <= 40; a++) for (let b = 0; b <= 40; b++) for (let c = 0; c <= 40; c++) {
      const t = [a, b, c];
      const fields = [...t, t[0] * t[1], t[1] * t[2], t[2] * t[0]];
      if ([...shown].some(([f, v]) => fields[f] !== v)) continue;
      if (fields.some((v) => v > 9999)) continue;
      const nearer = !best || distance(t) < distance(best) || (distance(t) === distance(best) && t.some((v, i) => v !== best![i] && v < best![i] && t.slice(0, i).every((w, q) => w === best![q])));
      if (nearer) best = t;
    }
    const out = madeDreieck(Dreieck({ op: "*", seed: 8, count: 1, max: 20, typed: raw.map(([f, v]) => [0, f, v]) })).triangles[0];
    expect(out.wrong).toBe(best === undefined);
    if (best) expect(out.numbers.slice(0, 3)).toEqual(best);
  });

  it("4 and 3 with the side 12 is a product, so the triangle holds, and 4 × 3 = 7 does not", () => {
    const held = madeDreieck(Dreieck({ op: "*", seed: 2, count: 1, typed: [[0, 0, 4], [0, 1, 3], [0, 3, 12]] })).triangles[0];
    expect(held.wrong).toBe(false);
    expect(held.numbers[0]).toBe(4);
    expect(held.numbers[1]).toBe(3);
    expect(held.numbers[3]).toBe(12);
    const broken = madeDreieck(Dreieck({ op: "*", seed: 2, count: 1, typed: [[0, 0, 4], [0, 1, 3], [0, 3, 7]] })).triangles[0];
    expect(broken.wrong).toBe(true);
    expect(broken.numbers[3]).toBe(7);
  });
});

describe("Zahlenmauer: 2 and 6 base stones", () => {
  it("keeps 2 and 6 and still refuses a base outside that range", () => {
    expect(saneMauer(Mauer({ base: 2 })).base).toBe(2);
    expect(saneMauer(Mauer({ base: 6 })).base).toBe(6);
    expect(saneMauer({ ...Mauer(), base: 1 } as unknown as ZahlenmauerProps).base).toBe(3);
    expect(saneMauer({ ...Mauer(), base: 7 } as unknown as ZahlenmauerProps).base).toBe(3);
  });

  it("a wall of 2 base stones is two stones and their sum", () => {
    const { walls } = madeMauer(Mauer({ base: 2, count: 4, max: 20, seed: 4 }));
    expect(walls).toHaveLength(4);
    for (const w of walls) {
      expect(w.numbers).toHaveLength(stones(2));
      expect(w.numbers[2]).toBe(w.numbers[0] + w.numbers[1]);
      expect(w.numbers[2]).toBeLessThanOrEqual(20);
      expect(w.wrong).toBe(false);
    }
  });

  it("a wall of 6 base stones holds the sum rule and fits the Zahlenraum", () => {
    const { walls } = madeMauer(Mauer({ base: 6, count: 2, max: 100, seed: 5 }));
    expect(walls.length).toBeGreaterThan(0);
    for (const w of walls) {
      expect(w.numbers).toHaveLength(stones(6));
      expect(w.numbers.every((v) => v >= 0 && v <= 100)).toBe(true);
      for (let r = 1; r < 6; r++) for (let c = 0; c < 6 - r; c++) {
        const at = (row: number, col: number) => row * 6 - (row * (row - 1)) / 2 + col;
        expect(w.numbers[at(r, c)]).toBe(w.numbers[at(r - 1, c)] + w.numbers[at(r - 1, c + 1)]);
      }
    }
  });
});
