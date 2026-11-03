// Digits take the Montessori place colours, from the right. A decimal stays one uncoloured run.
import { describe, expect, it } from "vitest";
import { GAP } from "./decimal";
import { MONTESSORI, type PlaceColors, gridTint, placeColors, placeName, runs, storedPlaces } from "./places";

const GREEN = MONTESSORI.einer;
const BLUE = MONTESSORI.zehner;
const RED = MONTESSORI.hunderter;
const THOUSAND = MONTESSORI.tausender;

const coloured = (text: string) => runs(text, MONTESSORI).filter((part) => part.place);

describe("place colours", () => {
  it("colours 1234 as Tausender, Hunderter, Zehner, Einer", () => {
    expect(coloured("1234")).toEqual([
      { text: "1", color: THOUSAND, place: "tausender" },
      { text: "2", color: RED, place: "hunderter" },
      { text: "3", color: BLUE, place: "zehner" },
      { text: "4", color: GREEN, place: "einer" },
    ]);
  });

  it("keeps a thousands digit on its own colour when Einer changes", () => {
    const colors = { ...MONTESSORI, einer: "#445566", tausender: "#112233" };
    expect(colouredDigits("1000", colors)).toEqual(["#112233", RED, BLUE, "#445566"]);
  });

  it("repeats Zehner and Hunderter above the thousands, and Einer at the millions", () => {
    expect(placeName(4)).toBe("zehner");
    expect(placeName(5)).toBe("hunderter");
    expect(placeName(6)).toBe("einer");
    expect(coloured("10000").map((part) => part.place)).toEqual(["zehner", "tausender", "hunderter", "zehner", "einer"]);
    expect(coloured("1000000")[0].place).toBe("einer");
  });

  it("leaves a decimal number black, and the whole numbers beside it coloured", () => {
    expect(runs("3,50", MONTESSORI)).toEqual([{ text: "3,50" }]);
    expect(runs("12 + 3,5 = 15", MONTESSORI).map((part) => part.place ?? part.text)).toEqual([
      "zehner",
      "einer",
      " + 3,5 = ",
      "zehner",
      "einer",
    ]);
  });

  it("colours the digits of a grouped whole number and not the gap", () => {
    const text = `1${GAP}234`;
    expect(coloured(text).map((part) => part.text).join("")).toBe("1234");
    expect(runs(text, MONTESSORI).some((part) => part.text === GAP && !part.place)).toBe(true);
  });

  it("stays off until the sheet turns the colours on", () => {
    expect(runs("1234", null)).toEqual([{ text: "1234" }]);
    expect(placeColors({})).toBeNull();
    expect(placeColors({ places: { einer: "#ff00ff" } })).toBeNull();
    expect(placeColors({ places: { on: true } })).toEqual(MONTESSORI);
    expect(placeColors({ places: { on: true, einer: "#FF00FF", zehner: "red" } })).toEqual({ ...MONTESSORI, einer: "#ff00ff" });
  });

  it("keeps a picked colour while the switch is off, and drops a colour it did not write", () => {
    expect(storedPlaces({ on: true, einer: "#FF00FF", zehner: "blue" })).toEqual({ on: true, einer: "#ff00ff" });
    expect(storedPlaces({ einer: "#00ff00" })).toEqual({ einer: "#00ff00" });
    expect(storedPlaces({ on: false })).toBeUndefined();
    expect(storedPlaces("an")).toBeUndefined();
  });

  it("colours a written sum by each number, a carry by its column, and a decimal not at all", () => {
    const sum = gridTint(
      [
        { x: 0, y: 0, ch: "1", kind: 0 },
        { x: 1, y: 0, ch: "2", kind: 0 },
        { x: 2, y: 0, ch: "·", kind: 0 },
        { x: 3, y: 0, ch: "3", kind: 0 },
        { x: 2, y: 1, ch: "1", kind: 2 },
      ],
      MONTESSORI,
    );
    expect(sum.get("0,0")?.place).toBe("zehner");
    expect(sum.get("1,0")?.place).toBe("einer");
    expect(sum.get("3,0")?.place).toBe("einer");
    expect(sum.get("2,1")?.place).toBe("zehner");
    expect(sum.has("2,0")).toBe(false);

    const decimal = gridTint(
      [
        { x: 1, y: 0, ch: "0", kind: 0 },
        { x: 2, y: 0, ch: ",", kind: 0 },
        { x: 3, y: 0, ch: "5", kind: 0 },
        { x: 1, y: 2, ch: "1", kind: 2 },
      ],
      MONTESSORI,
    );
    expect(decimal.has("1,0")).toBe(false);
    expect(decimal.has("3,0")).toBe(false);
    expect(decimal.get("1,2")?.place).toBe("einer");
    expect(gridTint([{ x: 0, y: 0, ch: "7", kind: 0 }], null).size).toBe(0);
  });
});

function colouredDigits(text: string, colors: PlaceColors) {
  return runs(text, colors).filter((part) => part.place).map((part) => part.color);
}
