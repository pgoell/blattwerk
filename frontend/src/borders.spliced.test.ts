// Adding or removing a row or a column keeps the lines that still belong.
import { describe, expect, it } from "vitest";
import { type Edge, type Edges } from "./edges";
import { bordered, edgesSpliced } from "./borders";
import { pen, grid, drawn, nulls, type Table } from "./borders.fixtures";

describe("edgesSpliced", () => {
  const valid = drawn(bordered(grid, [0, 0, 2, 3], "all", pen));
  const sized = { ...grid, edges: valid } as Table;

  it("gives nothing for a table with no valid edges", () => {
    expect(edgesSpliced({ ...grid, edges: { h: [], v: [] } } as unknown as Table, "row", 0, true)).toBeUndefined();
  });

  it("keeps the rim when a row is added at the top", () => {
    const out = edgesSpliced(sized, "row", 0, true)!;
    expect(out.h.length).toBe(5);
    expect(out.h[0]).toStrictEqual(valid.h[0]);
  });

  it("drops the line under a removed last row, and keeps the rim", () => {
    const out = edgesSpliced(sized, "row", 2, false)!;
    expect(out.h[2]).toStrictEqual(valid.h[2]);
    expect(out.v.length).toBe(2);
  });

  // Issues #562 and #567 (PR #546): a new row or column takes the lines that cross its neighbour, so a closed frame
  // stays closed and a thick line inside runs on. The line between it and its neighbour is null, as I5 has it.
  // #594: a grid drawn all in one pen keeps that pen, so the new line takes it.
  it("gives a row added below every line that crosses the row above, and gives the line between the grid's pen (#594)", () => {
    const out = edgesSpliced(sized, "row", 1, true)!;
    expect(out.v[1]).toStrictEqual(Array(5).fill(pen));
    expect(out.h[1]).toStrictEqual(Array(4).fill(pen));
  });

  // #594: a grid drawn all in one pen keeps that pen, so the new line takes it.
  it("gives a row added at the top the first row's lines, and gives the line between the grid's pen (#594)", () => {
    const out = edgesSpliced(sized, "row", 0, true)!;
    expect(out.v[0]).toStrictEqual(Array(5).fill(pen));
    expect(out.h[1]).toStrictEqual(Array(4).fill(pen));
  });

  // #594: a grid drawn all in one pen keeps that pen, so the new line takes it.
  it("gives a column added to the right the last column's lines, and gives the line between the grid's pen (#594)", () => {
    const out = edgesSpliced(sized, "col", 4, true)!;
    expect(out.h.map((list) => list[4])).toStrictEqual(Array(4).fill(pen));
    expect(out.v.map((list) => list[4])).toStrictEqual(Array(3).fill(pen));
  });

  // #594: a grid drawn all in one pen keeps that pen, so the new line takes it.
  it("gives a column added at the left the first column's lines, and gives the line between the grid's pen (#594)", () => {
    const out = edgesSpliced(sized, "col", 0, true)!;
    expect(out.h.map((list) => list[0])).toStrictEqual(Array(4).fill(pen));
    expect(out.v.map((list) => list[1])).toStrictEqual(Array(3).fill(pen));
  });

  // Issue #574: a row or column added after its anchor keeps the line at the join with the anchor, so a box round the
  // anchor stays closed.
  // #594: a grid drawn all in one pen keeps that pen, so the new line takes it.
  it("keeps the line between an anchor row and the next when a row goes after it, and gives the line between the grid's pen (#594)", () => {
    const out = edgesSpliced(sized, "row", 1, true, true)!;
    expect(out.h[1]).toStrictEqual(valid.h[1]);
    expect(out.h[2]).toStrictEqual(Array(4).fill(pen));
  });

  // #594: a grid drawn all in one pen keeps that pen, so the new line takes it.
  it("keeps the line between an anchor column and the next when a column goes after it, and gives the line between the grid's pen (#594)", () => {
    const out = edgesSpliced(sized, "col", 1, true, true)!;
    expect(out.v.map((list) => list[1])).toStrictEqual(valid.v.map((list) => list[1]));
    expect(out.v.map((list) => list[2])).toStrictEqual(Array(3).fill(pen));
  });

  // Whether every line round the cells of the rect is drawn with `pen`.
  const closed = (e: Edges, [r0, c0, r1, c1]: [number, number, number, number]) => {
    const lines: Edge[] = [];
    for (let c = c0; c <= c1; c++) lines.push(e.h[r0][c], e.h[r1 + 1][c]);
    for (let r = r0; r <= r1; r++) lines.push(e.v[r][c0], e.v[r][c1 + 1]);
    return lines.every((line) => JSON.stringify(line) === JSON.stringify(pen));
  };
  // Review of #574: a box on either side of the new row or column stays closed, whichever cell is the anchor, and
  // the new row or column gets no line of the box.
  it.each([
    ["a box above, the row added after it", "row", [1, 1, 1, 1], 2, true, [1, 1, 1, 1]],
    ["a box below, the row added after the row above it", "row", [1, 1, 1, 1], 1, true, [2, 1, 2, 1]],
    ["a box above, the row added before the row under it", "row", [0, 1, 0, 1], 1, false, [0, 1, 0, 1]],
    ["a box round two cells below, the row added after the row above it", "row", [1, 1, 1, 2], 1, true, [2, 1, 2, 2]],
    ["a box round two cells above, the row added before the row under it", "row", [0, 0, 0, 2], 1, false, [0, 0, 0, 2]],
    ["a box left, the column added after it", "col", [1, 1, 1, 1], 2, true, [1, 1, 1, 1]],
    ["a box right, the column added after the column left of it", "col", [1, 2, 1, 2], 2, true, [1, 3, 1, 3]],
    ["a box right, the column added before it", "col", [1, 2, 2, 2], 2, false, [1, 3, 2, 3]],
  ] as const)("keeps %s closed", (_, axis, rect, i, after, moved) => {
    const out = edgesSpliced({ ...grid, edges: drawn(bordered(grid, [...rect], "outer", pen)) } as Table, axis, i, true, after)!;
    expect(closed(out, [...moved])).toBe(true);
    const lines = axis === "row" ? [...out.h[i], ...out.h[i + 1], ...out.v[i]] : [...out.v.map((l) => l[i]), ...out.v.map((l) => l[i + 1]), ...out.h.map((l) => l[i])];
    expect(lines.filter((line) => line !== null).length).toBe(axis === "row" ? (moved[0] === i + 1 ? moved[3] - moved[1] + 1 : rect[0] === i - 1 ? rect[3] - rect[1] + 1 : 0) : moved[1] === i + 1 ? moved[2] - moved[0] + 1 : rect[1] === i - 1 ? rect[2] - rect[0] + 1 : 0);
  });

  // The first column framed alone: its right line is thick inside the table.
  const column = { ...grid, edges: drawn(bordered(grid, [0, 0, 2, 0], "outer", pen)) } as Table;

  it("runs a thick line inside the table on through a new row, below and at the top", () => {
    for (const i of [3, 1, 0]) {
      const out = edgesSpliced(column, "row", i, true)!;
      expect(out.v[i]).toStrictEqual([pen, pen, null, null, null]);
      expect(out.h[i === 0 ? 1 : i].every((edge) => edge === null)).toBe(true);
    }
    // Below the last row the box round the whole column stays closed: its bottom moves to the new rim (#584 review).
    expect(edgesSpliced(column, "row", 3, true)!.h[4]).toStrictEqual([pen, null, null, null]);
  });

  // In a table of one row a box round one cell stays round it, though its sides run the table's full height.
  it("keeps a box round one cell of a one-row table at that cell when a row is added below", () => {
    const row = { cells: [["", "", "", ""]], cols: [1, 1, 1, 1] } as unknown as Table;
    const one = { ...row, edges: drawn(bordered(row, [0, 1, 0, 1], "outer", pen)) } as Table;
    const out = edgesSpliced(one, "row", 1, true)!;
    expect(out.h[1]).toStrictEqual([null, pen, null, null]);
    expect(out.h[2]).toStrictEqual(nulls(4));
    expect(out.v[1]).toStrictEqual(nulls(5));
  });

  // A box round the two middle cells of the last row keeps its bottom and takes no side into the new row.
  it("keeps a box round two cells of the last row at those cells when a row is added below", () => {
    const two = { ...grid, edges: drawn(bordered(grid, [2, 1, 2, 2], "outer", pen)) } as Table;
    const out = edgesSpliced(two, "row", 3, true)!;
    expect(out.h[3]).toStrictEqual([null, pen, pen, null]);
    expect(out.h[4]).toStrictEqual(nulls(4));
    expect(out.v[3]).toStrictEqual(nulls(5));
  });

  // Found by the review of #568: a line hidden inside a merged cell is not taken into the new row or column.
  it("does not take a line hidden inside a merged cell", () => {
    const all = { ...grid, edges: drawn(bordered(grid, [0, 0, 2, 3], "all", pen)) } as Table;
    const row = edgesSpliced({ ...all, spans: [[0, 0, 1, 2]] } as Table, "row", 1, true)!;
    expect(row.v[1]).toStrictEqual([pen, null, pen, pen, pen]);
    const col = edgesSpliced({ ...all, spans: [[0, 0, 2, 1]] } as Table, "col", 1, true)!;
    expect(col.h.map((list) => list[1])).toStrictEqual([pen, null, pen, pen]);
  });

  // Found by the review of #568: a box round one cell keeps its height when a row comes in below or above it.
  it("takes a line only where the neighbours on both sides draw it, so a box round one cell does not grow", () => {
    const one = { ...grid, edges: drawn(bordered(grid, [1, 1, 1, 1], "outer", pen)) } as Table;
    for (const i of [1, 2]) expect(edgesSpliced(one, "row", i, true)!.v[i]).toStrictEqual(nulls(5));
    for (const i of [1, 2]) expect(edgesSpliced(one, "col", i, true)!.h.map((list) => list[i])).toStrictEqual(nulls(4));
  });

  // Issue #584: a box round one cell of the last row stays round that cell. The new row below takes no side of it, and
  // its bottom is plain; the box's bottom stays under the cell.
  it("keeps a box round one cell of the last row at that cell when a row is added below", () => {
    const boxed = { ...grid, edges: drawn(bordered(grid, [2, 1, 2, 1], "outer", pen)) } as Table;
    const out = edgesSpliced(boxed, "row", 3, true)!;
    expect(out.h[3]).toStrictEqual([null, pen, null, null]);
    expect(out.h[4]).toStrictEqual(nulls(4));
    expect(out.v[3]).toStrictEqual(nulls(5));
  });

  // Issue #591: a box round a cell of the last row, in another pen, does not stop a box round whole columns from
  // closing: the columns' bottoms move to the new rim, the cell's box stays under its row, the new row takes the
  // columns' sides in their pen.
  describe("issue #591: a column box beside a box round a cell of the last row", () => {
    const solid = { style: "solid" as const, width: 1 };
    const with_ = (p: Table, rect: [number, number, number, number], which: "outer", style: typeof pen) => ({ ...p, edges: drawn(bordered(p, rect, which, style)) }) as Table;

    it("keeps the column boxes closed when the cell's box is solid", () => {
      const a = with_(grid, [0, 0, 2, 0], "outer", pen);
      const c = { ...a, edges: drawn(bordered(a, [0, 2, 2, 2], "outer", pen)) } as Table;
      const both = { ...c, edges: drawn(bordered(c, [2, 1, 2, 1], "outer", solid)) } as Table;
      const out = edgesSpliced(both, "row", 3, true)!;
      expect(out.h[3]).toStrictEqual([null, solid, null, null]);
      expect(out.h[4]).toStrictEqual([pen, null, pen, null]);
      expect(out.v[3]).toStrictEqual([pen, pen, pen, pen, null]);
    });

    it("keeps the column box closed when the cell's box is in the same pen", () => {
      const a = with_(grid, [0, 0, 2, 0], "outer", pen);
      const both = { ...a, edges: drawn(bordered(a, [2, 1, 2, 1], "outer", pen)) } as Table;
      const out = edgesSpliced(both, "row", 3, true)!;
      expect(out.h[3]).toStrictEqual([null, pen, null, null]);
      expect(out.h[4]).toStrictEqual([pen, null, null, null]);
      expect(out.v[3]).toStrictEqual([pen, pen, null, null, null]);
    });

    it("keeps the column boxes closed when all three boxes are in the same pen", () => {
      const a = with_(grid, [0, 0, 2, 0], "outer", pen);
      const c = { ...a, edges: drawn(bordered(a, [0, 2, 2, 2], "outer", pen)) } as Table;
      const all = { ...c, edges: drawn(bordered(c, [2, 1, 2, 1], "outer", pen)) } as Table;
      const out = edgesSpliced(all, "row", 3, true)!;
      expect(out.h[3]).toStrictEqual([null, pen, null, null]);
      expect(out.h[4]).toStrictEqual([pen, null, pen, null]);
      expect(out.v[3]).toStrictEqual([pen, pen, pen, pen, null]);
    });

    it("keeps a column box at the right edge closed beside a solid cell box", () => {
      const d = with_(grid, [0, 3, 2, 3], "outer", pen);
      const both = { ...d, edges: drawn(bordered(d, [2, 1, 2, 1], "outer", solid)) } as Table;
      const out = edgesSpliced(both, "row", 3, true)!;
      expect(out.h[3]).toStrictEqual([null, solid, null, null]);
      expect(out.h[4]).toStrictEqual([null, null, null, pen]);
      expect(out.v[3]).toStrictEqual([null, null, null, pen, pen]);
    });

    it("keeps a box round two whole columns closed beside a solid box round C3", () => {
      const ab = with_(grid, [0, 0, 2, 1], "outer", pen);
      const both = { ...ab, edges: drawn(bordered(ab, [2, 2, 2, 2], "outer", solid)) } as Table;
      const out = edgesSpliced(both, "row", 3, true)!;
      expect(out.h[3]).toStrictEqual([null, null, solid, null]);
      expect(out.h[4]).toStrictEqual([pen, pen, null, null]);
      expect(out.v[3]).toStrictEqual([pen, null, pen, null, null]);
    });

    // Review of #591: a dotted box round column A, and a solid box round its last cell A3. The column's bottom is
    // not a frame's (its top and bottom differ in pen), so the new row takes no side of it and its bottom stays.
    it("keeps a column box whose last cell has a solid box open under row 3, no side into the new row", () => {
      const a = with_(grid, [0, 0, 2, 0], "outer", pen);
      const both = { ...a, edges: drawn(bordered(a, [2, 0, 2, 0], "outer", solid)) } as Table;
      const out = edgesSpliced(both, "row", 3, true)!;
      expect(out.h[3]).toStrictEqual([solid, null, null, null]);
      expect(out.h[4]).toStrictEqual(nulls(4));
      expect(out.v[3]).toStrictEqual(nulls(5));
    });
  });

  it("runs a thick line across the table on through a new column", () => {
    const across = { ...grid, edges: drawn(bordered(grid, [0, 0, 0, 3], "outer", pen)) } as Table;
    const out = edgesSpliced(across, "col", 2, true)!;
    expect(out.h.map((list) => list[2])).toStrictEqual([pen, pen, null, null]);
    expect(out.v.every((list) => list[2] === null)).toBe(true);
  });
});
