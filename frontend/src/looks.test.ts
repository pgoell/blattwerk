// What a table's cell looks hold, and what the writers put in them.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { lookAt, looked, looksOf, unlooked } from "./looks";
import { merged } from "./cells";
import { spliced, type TableBlock } from "./sheet";

type Table = TableBlock["props"];
// A 3 by 4 table with no looks yet.
const grid = { cells: Array.from({ length: 3 }, () => ["", "", "", ""]), cols: [1, 1, 1, 1], size: 12, align: "left", line: "#222222" } as Table;

describe("looksOf", () => {
  it("drops a grid of the wrong shape and never throws", () => {
    fc.assert(
      fc.property(fc.anything(), (looks) => {
        const out = looksOf({ ...grid, looks } as never);
        if (out) expect(out.length === 3 && out.every((row) => row.length === 4)).toBe(true);
      }),
    );
  });

  it("keeps only the keys that hold", () => {
    const looks = [[{ bold: true, font: "nope", size: -2, italic: "yes" }, null, { size: 14, font: "nord", underline: false }, null], [null, null, null, null], [null, null, null, null]];
    expect(lookAt({ ...grid, looks } as never, 0, 0)).toStrictEqual({ bold: true });
    expect(lookAt({ ...grid, looks } as never, 0, 2)).toStrictEqual({ size: 14, font: "nord", underline: false });
    expect(lookAt({ ...grid, looks } as never, 1, 1)).toStrictEqual({});
  });
});

describe("looked", () => {
  it("writes the patch on the rect's cells and on no others", () => {
    const out = looked(grid, [0, 1, 1, 2], { bold: true, size: 16 });
    for (let r = 0; r < 3; r++)
      for (let c = 0; c < 4; c++) expect(lookAt(out, r, c), `${r},${c}`).toStrictEqual(r <= 1 && c >= 1 && c <= 2 ? { bold: true, size: 16 } : {});
  });

  it("takes a key away with undefined, and the whole grid when no cell has a look", () => {
    const on = looked(grid, [0, 0, 0, 0], { italic: true });
    expect(looked(on, [0, 0, 0, 0], { italic: undefined }).looks).toBeUndefined();
  });

  it("never changes the props it gets", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 2 }), fc.integer({ min: 0, max: 3 }), fc.boolean(), (r, c, on) => {
        const p = looked(grid, [0, 0, 2, 3], { underline: true });
        const before = structuredClone(p);
        looked(p, [r, c, 2, 3], { underline: on, size: 9 });
        expect(p).toStrictEqual(before);
      }),
    );
  });
});

describe("unlooked", () => {
  it("takes one key out of every cell", () => {
    const p = looked(grid, [0, 0, 1, 1], { font: "nord", bold: true });
    const out = unlooked(p, "font");
    expect(lookAt(out, 0, 0)).toStrictEqual({ bold: true });
    expect(unlooked(out, "bold").looks).toBeUndefined();
  });
});

describe("the looks keep their cells", () => {
  it("through a row or column that comes or goes", () => {
    const p = looked(grid, [1, 2, 1, 2], { bold: true });
    expect(lookAt(spliced(p, "row", 0, true), 2, 2)).toStrictEqual({ bold: true });
    expect(lookAt(spliced(p, "row", 0, true), 0, 2)).toStrictEqual({});
    expect(lookAt(spliced(p, "col", 1, false), 1, 1)).toStrictEqual({ bold: true });
    expect(spliced(p, "row", 1, false).looks).toBeUndefined();
    const out = spliced(p, "col", 3, true);
    expect(looksOf(out)!.every((row) => row.length === 5)).toBe(true);
  });

  it("through a merge, where the top-left cell keeps its look", () => {
    const p = looked(looked(grid, [0, 0, 0, 0], { italic: true }), [0, 1, 0, 1], { bold: true });
    const out = merged(p, [0, 0, 0, 1]);
    expect(lookAt(out, 0, 0)).toStrictEqual({ italic: true });
    expect(lookAt(out, 0, 1)).toStrictEqual({});
  });

  it("when the first row of a merged cell goes: the look moves to its new top-left cell", () => {
    const p = merged(looked(grid, [0, 1, 0, 1], { size: 20 }), [0, 1, 1, 1]);
    const out = spliced(p, "row", 0, false);
    expect(lookAt(out, 0, 1)).toStrictEqual({ size: 20 });
  });
});
