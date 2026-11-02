// The Geobrett: nails, rubber bands, and the answers a task derives from them.
import { describe, expect, it } from "vitest";
import {
  ASK,
  COLORS,
  DEFAULTS,
  areaOf,
  areaText,
  figures,
  lengthText,
  mirrored,
  moved,
  rightAngles,
  sane,
  scaled,
  solution,
  turned,
  type Band,
  type GeobrettProps,
} from "./geobrett";

const band = (nails: Band["nails"], over: Partial<Band> = {}): Band => ({
  nails,
  color: COLORS[0],
  fill: true,
  ...over,
});

const props = (over: Partial<GeobrettProps> = {}): GeobrettProps => ({ ...DEFAULTS, ...over });

describe("sane", () => {
  it("gives an empty 5 by 5 board", () => {
    expect(sane(undefined)).toEqual(DEFAULTS);
    expect(DEFAULTS).toMatchObject({ cols: 5, rows: 5, bands: [], task: "leer" });
  });

  it("drops a board that is not 2 to 12 nails, a task it does not know, and a seed that is not whole", () => {
    expect(sane({ cols: 1, rows: 99, task: "nope", bands: "x", seed: 1.5 })).toMatchObject({
      cols: 5,
      rows: 5,
      task: "leer",
      bands: [],
      seed: 0,
    });
  });

  it("keeps a band on the nails and drops a nail that is off the board", () => {
    const kept = sane({
      cols: 5,
      rows: 5,
      bands: [band([[0, 0], [2, 0], [9, 9]], { color: "#1F6FEB", fill: true }), band([[0, 0]])],
    });
    expect(kept.bands).toEqual([band([[0, 0], [2, 0]], { color: "#1f6feb", fill: true })]);
  });
});

describe("bands", () => {
  const square = band([[0, 0], [2, 0], [2, 2], [0, 2]]);

  it("moves by whole nails and stays when a move would leave the board", () => {
    expect(moved(square, 1, 0, 5, 5).nails).toEqual([[1, 0], [3, 0], [3, 2], [1, 2]]);
    expect(moved(square, -1, 0, 5, 5)).toBe(square);
  });

  it("turns 90° clockwise about the band's centre", () => {
    expect(turned(square, 5, 5).nails).toEqual([[2, 0], [2, 2], [0, 2], [0, 0]]);
  });

  it("turns about the top-left nail when the centre would miss the nails, and stays when the turn leaves the board", () => {
    const wide = band([[1, 0], [3, 0], [3, 1], [1, 1]]);
    expect(turned(wide, 5, 5).nails).toEqual([[1, 0], [1, 2], [0, 2], [0, 0]]);
    expect(turned(wide, 2, 2)).toBe(wide);
  });

  it("mirrors left to right and top to bottom", () => {
    const flag = band([[0, 0], [2, 1]]);
    expect(mirrored(flag, "x").nails).toEqual([[2, 0], [0, 1]]);
    expect(mirrored(flag, "y").nails).toEqual([[0, 1], [2, 0]]);
  });

  it("doubles from the top-left nail and halves a band on even steps", () => {
    const small = band([[1, 1], [2, 1], [2, 2]]);
    const big = scaled(small, 2, 5, 5);
    expect(big.nails).toEqual([[1, 1], [3, 1], [3, 3]]);
    expect(scaled(big, 0.5, 5, 5).nails).toEqual(small.nails);
    expect(scaled(big, 2, 5, 5)).toBe(big);
    expect(scaled(small, 0.5, 5, 5)).toBe(small);
  });
});

describe("measure", () => {
  it("counts the squares a band encloses", () => {
    expect(areaOf(band([[0, 0], [1, 0], [1, 1], [0, 1]]))).toBe(1);
    expect(areaOf(band([[0, 0], [2, 0], [0, 2]]))).toBe(2);
    expect(areaText(4)).toBe("4");
    expect(areaText(0.5)).toBe("0,5");
  });

  it("writes a length as a sum of square roots", () => {
    expect(lengthText(band([[0, 0], [1, 0], [1, 1], [0, 1]]))).toBe("4");
    expect(lengthText(band([[0, 0], [3, 0], [0, 3]]))).toBe("6 + 3√2");
    expect(lengthText(band([[0, 0], [1, 1]], { fill: false }))).toBe("√2");
  });

  it("names the right angles of a closed band", () => {
    expect(rightAngles(band([[0, 0], [2, 0], [0, 2]]))).toEqual([[0, 0]]);
    expect(rightAngles(band([[0, 0], [2, 0], [2, 2], [0, 2]]))).toEqual([[0, 0], [2, 0], [2, 2], [0, 2]]);
  });
});

describe("solution", () => {
  it("mirrors each band across the axis", () => {
    const given = props({
      task: "spiegel",
      axis: { dir: "v", at: 2 },
      bands: [band([[0, 1], [2, 2], [0, 3]])],
    });
    expect(solution(given)).toEqual({
      kind: "spiegel",
      bands: [band([[4, 1], [2, 2], [4, 3]])],
    });
  });

  it("finds the axes of a square and the one axis of an isosceles triangle", () => {
    const square = props({ task: "achsen", bands: [band([[1, 1], [3, 1], [3, 3], [1, 3]])] });
    expect(solution(square)).toEqual({
      kind: "achsen",
      axes: [
        { dir: "v", at: 2 },
        { dir: "h", at: 2 },
        { dir: "d", at: 0 },
        { dir: "a", at: 4 },
      ],
    });
    const triangle = props({ task: "achsen", bands: [band([[1, 1], [3, 1], [2, 3]])] });
    expect(solution(triangle)).toEqual({ kind: "achsen", axes: [{ dir: "v", at: 2 }] });
  });

  it("turns each band 90° clockwise about the centre nail", () => {
    const given = props({ task: "drehung", centre: [2, 2], bands: [band([[1, 1], [1, 3], [2, 3]])] });
    expect(solution(given)).toEqual({
      kind: "drehung",
      bands: [band([[3, 1], [1, 1], [1, 2]])],
    });
  });

  it("groups the parallel sides of a square", () => {
    const given = props({ task: "parallelen", bands: [band([[0, 0], [2, 0], [2, 2], [0, 2]])] });
    expect(solution(given)).toEqual({ kind: "parallelen", groups: [[0, 2], [1, 3]] });
  });

  it("answers with the area, the perimeter and the coordinates from the bottom left", () => {
    const shape = [band([[0, 0], [2, 0], [2, 2], [0, 2]])];
    expect(solution(props({ task: "flaeche", bands: shape }))).toEqual({ kind: "flaeche", area: 4, text: "4" });
    expect(solution(props({ task: "umfang", bands: [band([[0, 0], [3, 0], [0, 3]])] }))).toEqual({ kind: "umfang", text: "6 + 3√2" });
    expect(solution(props({ task: "koordinaten", bands: [band([[0, 4], [2, 4], [2, 2]], { fill: false })] }))).toEqual({
      kind: "koordinaten",
      nails: [[0, 0], [2, 0], [2, 2]],
    });
  });

  it("gives an empty board no answer", () => {
    expect(solution(props())).toEqual({ kind: "leer" });
  });
});

describe("figures", () => {
  it("has two starting figures for every task but the empty board", () => {
    expect(figures("leer")).toEqual([]);
    for (const task of ["spiegel", "achsen", "drehung", "winkel", "parallelen", "flaeche", "umfang", "koordinaten"] as const) {
      const found = figures(task);
      expect(found.length).toBeGreaterThanOrEqual(2);
      expect(ASK[task].length).toBeGreaterThan(0);
      for (const figure of found) {
        const made = sane({ ...DEFAULTS, task, ...figure });
        expect(made.bands.length).toBeGreaterThan(0);
        const answer = solution(made);
        expect(answer.kind).toBe(task);
      }
    }
  });
});
