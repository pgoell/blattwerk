// What the insert buttons make, checked against literal values taken from the editor on master (not computed by insert.ts).
import { describe, expect, it } from "vitest";
import { INSERTS, MATHS, grown, topZ } from "./insert";
import type { Block, Doc } from "./sheet";

const NO_DOC = {} as Doc;

describe("INSERTS", () => {
  it("text, heading, symbol, table, ruling, name, points", () => {
    expect(INSERTS.text()).toEqual({ w: 80, h: 12, type: "text", props: { text: "", size: 14, align: "left" } });
    expect(INSERTS.heading()).toEqual({ w: 180, h: 14, type: "text", props: { text: "", size: 24, align: "center", bold: true } });
    expect(INSERTS.symbol()).toEqual({ w: 20, h: 20, type: "symbol", props: { code: "270F" } });
    expect(INSERTS.table()).toEqual({ w: 180, h: 30, type: "table", props: { cells: [["", "", ""], ["", "", ""], ["", "", ""]], cols: [1, 1, 1], size: 14, align: "center", line: "#222222" } });
    expect(INSERTS.ruling()).toEqual({ w: 180, h: 60, type: "ruling", props: { kind: "l1", color: "#555555" } });
    expect(INSERTS.name()).toEqual({ w: 180, h: 10, type: "name", props: {} });
    expect(INSERTS.points()).toEqual({ w: 40, h: 12, type: "points", props: { max: 10 } });
  });

  it("the seeded blocks take their seed", () => {
    expect(INSERTS.suchsel(7)).toEqual({ w: 120, h: 140, type: "suchsel", props: { words: [], cols: 10, rows: 10, ways: "down", caps: true, umlauts: true, show: "words", seed: 7 } });
    expect(INSERTS.zahlenmauer(7)).toMatchObject({ w: 180, h: 60, type: "zahlenmauer", props: { base: 3, count: 4, columns: 2, max: 20, op: "+", given: "base", empty: false, seed: 7 } });
    expect(INSERTS.rechendreieck(7)).toMatchObject({ w: 180, h: 50, type: "rechendreieck", props: { seed: 7 } });
    expect(INSERTS.zahlenstrahl(7)).toMatchObject({ w: 180, h: 30, type: "zahlenstrahl", props: { seed: 7 } });
    expect(INSERTS.hunderterfeld(7)).toMatchObject({ w: 100, h: 100, type: "hunderterfeld", props: { seed: 7 } });
    expect(INSERTS.uhr(7)).toMatchObject({ w: 180, h: 58.5, type: "uhr", props: { count: 4, cols: 4, seed: 7 } });
    expect(INSERTS.selbstkontrolle(7)).toMatchObject({ w: 180, h: 30, type: "selbstkontrolle", props: { seed: 7 } });
  });

  it("Strecke is a line with ticks, 50 mm wide and no height", () => {
    expect(INSERTS.strecke()).toEqual({ w: 50, h: 0, type: "shape", props: { kind: "line", fill: "none", stroke: "#222222", strokeWidth: 0.5, ticks: true } });
  });

  it("a framed shape is 40 mm high and holds its text; a line is 0 high", () => {
    expect(INSERTS.shape("rect")).toEqual({ w: 60, h: 40, type: "shape", props: { kind: "rect", fill: "none", stroke: "#222222", strokeWidth: 0.5, inside: true, floor: true } });
    expect(INSERTS.shape("line")).toEqual({ w: 60, h: 0, type: "shape", props: { kind: "line", fill: "none", stroke: "#222222", strokeWidth: 0.5 } });
  });

  // Edge: a triangle is 40 mm wide, not 60.
  it("a triangle is 40 mm wide", () => {
    expect(INSERTS.shape("triangle")).toMatchObject({ w: 40, h: 40, props: { kind: "triangle", inside: true } });
  });

  it("the Lernwörter-Liste: a row per word, at least one row", () => {
    // Edge: no words still gives one row (row 11.5 mm, page 210 x 297, margin 15).
    expect(INSERTS.wordList(0, [210, 297], 11.5)).toMatchObject({ w: 180, h: 11.5, type: "ruling", props: { kind: "l3", list: "fold", folds: 2 } });
    expect(INSERTS.wordList(3, [210, 297], 11.5)).toMatchObject({ w: 180, h: 34.5 });
  });
});

describe("MATHS", () => {
  it("the limits of a new maths block, and its look", () => {
    expect(MATHS.w).toBe(180);
    expect(MATHS.limits(9)).toEqual({ ops: ["+"], max: 20, a: [[0, 9], [0, 9]], b: [[0, 9], [0, 9]], carry: "either", rest: false, format: "row", count: 12, seed: 9 });
    expect(MATHS.look).toEqual({ columns: 3, size: 14 });
  });
});

describe("topZ", () => {
  it("is 1 on an empty page, and one above the highest block", () => {
    expect(topZ([])).toBe(1);
    expect(topZ([{ z: 3 }, { z: 7 }, { z: 5 }] as Block[])).toBe(8);
  });
});

describe("grown", () => {
  const uhr = (count: number) => ({ id: "u", x: 15, y: 20, z: 1, locked: false, ...INSERTS.uhr(1), props: { ...INSERTS.uhr(1).props, count } }) as Block;

  it("a Uhr grows when its count goes from 4 to 8", () => {
    const b = uhr(4);
    const next = { ...b, props: { ...b.props, count: 8 } } as Block;
    const r = grown(b, next, NO_DOC, 297);
    expect(r.h).toBeGreaterThan(58.5);
  });

  it("a Uhr does not shrink when its count goes from 8 to 4", () => {
    const b = uhr(8);
    const next = { ...b, props: { ...b.props, count: 4 } } as Block;
    expect(grown(b, next, NO_DOC, 297)).toEqual({});
  });
});
