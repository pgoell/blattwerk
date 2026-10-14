// The writers of a table's lines: each border writes its own lines, and the splices keep the lines in step with the grid.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { edgesOf, type Edge, type Edges, type Lines } from "./edges";
import { bordered, cutLines, edgesSpliced, lined, type Border } from "./borders";
import { spliced, type TableBlock } from "./sheet";

type Table = TableBlock["props"];
const pen = { style: "dotted" as const, width: 1 };
// A 3 by 4 table, with no lines written yet.
const grid = { cells: Array.from({ length: 3 }, () => ["", "", "", ""]), cols: [1, 1, 1, 1] } as unknown as Table;
const drawn = (p: Lines & Partial<Table>): Edges => edgesOf(p as never)!;
const nulls = (n: number) => Array<Edge>(n).fill(null);

// The lines a border writes in the 3 by 4 table, for the rect [0, 1, 1, 2] (rows 0 to 1, columns 1 to 2).
const want: Record<Border, string[]> = {
  top: ["h0,1", "h0,2"],
  bottom: ["h2,1", "h2,2"],
  left: ["v0,1", "v1,1"],
  right: ["v0,3", "v1,3"],
  across: ["h1,1", "h1,2"],
  down: ["v0,2", "v1,2"],
  outer: ["h0,1", "h0,2", "h2,1", "h2,2", "v0,1", "v1,1", "v0,3", "v1,3"],
  inner: ["h1,1", "h1,2", "v0,2", "v1,2"],
  all: ["h0,1", "h0,2", "h2,1", "h2,2", "v0,1", "v1,1", "v0,3", "v1,3", "h1,1", "h1,2", "v0,2", "v1,2"],
};

// The names of the lines that hold an entry, as `h<r>,<c>` or `v<r>,<c>`.
const written = (e: Edges) => [
  ...e.h.flatMap((list, r) => list.flatMap((edge, c) => (edge ? [`h${r},${c}`] : []))),
  ...e.v.flatMap((list, r) => list.flatMap((edge, c) => (edge ? [`v${r},${c}`] : []))),
].sort();

describe("bordered", () => {
  it("writes each border's own lines and no others", () => {
    for (const which of Object.keys(want) as Border[]) {
      const e = drawn(bordered(grid, [0, 1, 1, 2], which, pen));
      expect(written(e), which).toStrictEqual([...want[which]].sort());
      expect(e.h.flat().filter(Boolean).every((edge) => edge!.style === "dotted" && edge!.width === 1)).toBe(true);
    }
  });

  it("never changes the props it gets", () => {
    fc.assert(
      fc.property(fc.constantFrom(...(Object.keys(want) as Border[])), fc.integer({ min: 0, max: 2 }), fc.integer({ min: 0, max: 3 }), (which, r, c) => {
        const before = structuredClone(grid);
        bordered(grid, [r, c, Math.min(2, r + 1), Math.min(3, c + 1)], which, pen);
        expect(grid).toStrictEqual(before);
      }),
    );
  });

  it("lets the later border win on a line the two share", () => {
    const first = bordered(grid, [0, 0, 0, 0], "right", { style: "dashed", width: 0.5 });
    const second = bordered(first, [0, 1, 0, 1], "left", pen);
    expect(drawn(second).v[0][1]).toStrictEqual(pen);
  });
});

describe("lined", () => {
  it("sets the whole table and takes the key out of each line", () => {
    const p = { ...grid, edges: drawn(bordered(grid, [0, 0, 0, 0], "all", { style: "dotted", width: 2 })) } as Table;
    const out = lined(p, { style: "dashed" });
    expect(out.lineStyle).toBe("dashed");
    expect(edgesOf(out)!.h[0][0]).toStrictEqual({ width: 2 });
  });

  it("keeps the width when the style is set, and the style when the width is", () => {
    const wide = lined(lined(grid, { style: "dashed" }), { width: 2 });
    expect(wide).toMatchObject({ lineStyle: "dashed", lineWidth: 2 });
    expect(lined(wide, { style: "dotted" })).toMatchObject({ lineStyle: "dotted", lineWidth: 2 });
  });

  it("writes nothing into a plain table asked for what it has", () => {
    expect(lined(grid, { style: "solid" })).toStrictEqual(grid);
    expect(lined(grid, { width: 0.25 })).toStrictEqual(grid);
  });

  it("removes edges when no line keeps a key", () => {
    const p = { ...grid, edges: drawn(bordered(grid, [0, 0, 0, 0], "top", pen)) } as Table;
    expect("edges" in lined(p, { style: "solid", width: 0.25 })).toBe(false);
  });
});

describe("cutLines", () => {
  it("sets dashed thin lines and drops edges on, and takes its keys off again", () => {
    const p = { ...grid, edges: drawn(bordered(grid, [0, 0, 0, 0], "top", pen)) } as Table;
    const on = cutLines(p, true);
    expect(on).toMatchObject({ cut: true, lineStyle: "dashed", lineWidth: 0.25 });
    expect("edges" in on).toBe(false);
    const off = cutLines(on, false);
    expect(off).toStrictEqual(grid);
  });
});

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
  it("gives a row added below every line that crosses the row above, and leaves the line between null", () => {
    const out = edgesSpliced(sized, "row", 1, true)!;
    expect(out.v[1]).toStrictEqual(Array(5).fill(pen));
    expect(out.h[1].every((edge) => edge === null)).toBe(true);
  });

  it("gives a row added at the top the first row's lines, and leaves the line under it null", () => {
    const out = edgesSpliced(sized, "row", 0, true)!;
    expect(out.v[0]).toStrictEqual(Array(5).fill(pen));
    expect(out.h[1].every((edge) => edge === null)).toBe(true);
  });

  it("gives a column added to the right the last column's lines, and leaves the line beside it null", () => {
    const out = edgesSpliced(sized, "col", 4, true)!;
    expect(out.h.map((list) => list[4])).toStrictEqual(Array(4).fill(pen));
    expect(out.v.every((list) => list[4] === null)).toBe(true);
  });

  it("gives a column added at the left the first column's lines, and leaves the line beside it null", () => {
    const out = edgesSpliced(sized, "col", 0, true)!;
    expect(out.h.map((list) => list[0])).toStrictEqual(Array(4).fill(pen));
    expect(out.v.every((list) => list[1] === null)).toBe(true);
  });

  // Issue #574: a row or column added after its anchor keeps the line at the join with the anchor, so a box round the
  // anchor stays closed.
  it("keeps the line between an anchor row and the next when a row goes after it, and leaves the new line null", () => {
    const out = edgesSpliced(sized, "row", 1, true, true)!;
    expect(out.h[1]).toStrictEqual(valid.h[1]);
    expect(out.h[2].every((edge) => edge === null)).toBe(true);
  });

  it("keeps the line between an anchor column and the next when a column goes after it, and leaves the new line null", () => {
    const out = edgesSpliced(sized, "col", 1, true, true)!;
    expect(out.v.map((list) => list[1])).toStrictEqual(valid.v.map((list) => list[1]));
    expect(out.v.every((list) => list[2] === null)).toBe(true);
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

describe("edgesSpliced, the rule", () => {
  const solid = { style: "solid" as const, width: 1.25 };
  const dotted = { style: "dotted" as const, width: 1.25 };
  const dashed = { style: "dashed" as const, width: 0.25 };
  const json = (edge: Edge) => JSON.stringify(edge);
  // The table of each case: (a) a solid frame and a dotted box, (b) the same pen for both, (c) every line dashed.
  const tables: Record<string, Table> = {
    a: bordered(bordered(grid, [0, 0, 2, 3], "outer", solid), [2, 1, 2, 1], "outer", dotted) as Table,
    b: bordered(bordered(grid, [0, 0, 2, 3], "outer", solid), [2, 1, 2, 1], "outer", solid) as Table,
    c: bordered(grid, [0, 0, 2, 3], "all", dashed) as Table,
  };
  // The cell of the box and the new row or column, for each side.
  const sides = {
    "row below": { axis: "row", i: 3, after: true, cell: [2, 1] },
    "row above": { axis: "row", i: 0, after: false, cell: [0, 1] },
    "column right": { axis: "col", i: 4, after: true, cell: [1, 3] },
    "column left": { axis: "col", i: 0, after: false, cell: [1, 0] },
  } as const;

  it.each(Object.keys(tables).flatMap((k) => Object.keys(sides).map((side) => [k, side])))("case %s, %s", (k, side) => {
    const { axis, i, after } = sides[side as keyof typeof sides];
    const out = edgesSpliced(tables[k], axis, i, true, after)!;
    if (k === "c") {
      expect([...out.h.flat(), ...out.v.flat()].filter((edge) => edge !== null).every((edge) => json(edge) === json(dashed))).toBe(true);
      return;
    }
    // The frame stays closed on the new rim.
    const rim = [...out.h[0], ...out.h[out.h.length - 1], ...out.v.map((list) => list[0]), ...out.v.map((list) => list[list.length - 1])];
    expect(rim.every((edge) => json(edge) === json(solid))).toBe(true);
    // The box stays round its old cell: four sides.
    expect([...out.h.flat(), ...out.v.flat()].filter((edge) => json(edge) === json(dotted)).length).toBe(4);
    // The new row or column is plain inside.
    if (axis === "row") {
      const newRow = out.v[i];
      expect(newRow.slice(1, -1).every((edge) => edge === null)).toBe(true);
    } else {
      const newCol = out.h.map((list) => list[i]);
      expect(newCol.slice(1, -1).every((edge) => edge === null)).toBe(true);
    }
  });

  it("issue #595: a frame closes on the new rim, and the box's bottom stays under its cell", () => {
    const framed = bordered(grid, [0, 0, 2, 3], "outer", solid) as Table;
    const boxed = { ...framed, edges: drawn(bordered(framed, [2, 1, 2, 1], "outer", dotted)) } as Table;
    const out = edgesSpliced(boxed, "row", 3, true, true)!;
    expect(out.h[4]).toStrictEqual([solid, solid, solid, solid]);
    expect(out.h[3]).toStrictEqual([null, dotted, null, null]);
  });

  it("keeps every line dashed when a row is added inside a dashed table", () => {
    const dashedTable = { ...grid, edges: drawn(bordered(grid, [0, 0, 2, 3], "all", dashed)) } as Table;
    const out = edgesSpliced(dashedTable, "row", 1, true)!;
    expect(out.h[1].every((edge) => json(edge) === json(dashed))).toBe(true);
    expect(out.h[2].every((edge) => json(edge) === json(dashed))).toBe(true);
    expect(out.v[1].every((edge) => json(edge) === json(dashed))).toBe(true);
  });

  it("keeps a frame round a one-row table when a column is added at its right", () => {
    const row = { cells: [["", "", "", ""]], cols: [1, 1, 1, 1] } as unknown as Table;
    const framed = { ...row, edges: drawn(bordered(row, [0, 0, 0, 3], "outer", solid)) } as Table;
    const out = edgesSpliced(framed, "col", 4, true, true)!;
    expect(out.h[0][4]).toStrictEqual(solid);
    expect(out.h[1][4]).toStrictEqual(solid);
  });
});

describe("splices keep the lines", () => {
  const cut = (n: number) => fc.integer({ min: 0, max: n });
  it("drops lines that do not fit the table, so a later splice cannot make them fit the wrong cells", () => {
    // As an older build leaves them: a row more, the edges of the table before.
    const stale = { ...grid, cells: [...grid.cells, ["", "", "", ""]], edges: drawn(bordered(grid, [0, 0, 0, 0], "all", pen)) } as Table;
    expect(edgesOf(stale)).toBeUndefined();
    expect("edges" in spliced(stale, "row", 1, false)).toBe(false);
  });

  it("writes nothing when the pen is the table's own, and takes a line's own look away", () => {
    expect(bordered(grid, [0, 0, 1, 1], "all", { style: "solid", width: 0.25 })).toBe(grid);
    const drawnOn = bordered(grid, [0, 0, 0, 0], "top", pen);
    expect("edges" in bordered(drawnOn, [0, 0, 0, 0], "top", { style: "solid", width: 0.25 })).toBe(false);
  });

  it("holds the sizes of the edges through any run of splices", () => {
    fc.assert(
      fc.property(
        fc.array(fc.record({ byRow: fc.boolean(), at: cut(6), add: fc.boolean() }), { maxLength: 8 }),
        (ops) => {
          let p = { ...grid, edges: drawn(bordered(grid, [0, 0, 2, 3], "all", pen)) } as Table;
          for (const { byRow, at, add } of ops) {
            const [rows, cols] = [p.cells.length, p.cols.length];
            const n = byRow ? rows : cols;
            if (!add && n < 2) continue;
            const i = add ? at % (n + 1) : at % n;
            p = spliced(p, byRow ? "row" : "col", i, add);
            const e = edgesOf(p);
            expect(e).toBeDefined();
            const [r, c] = [p.cells.length, p.cols.length];
            expect(e!.h.length).toBe(r + 1);
            expect(e!.h.every((list) => list.length === c)).toBe(true);
            expect(e!.v.length).toBe(r);
            expect(e!.v.every((list) => list.length === c + 1)).toBe(true);
          }
        },
      ),
    );
  });

  it("writes no edge object that is not null or a valid pen", () => {
    const entry = (edge: Edge) => edge === null || (edge.style !== undefined && edge.width !== undefined);
    const e = drawn(bordered(grid, [0, 0, 2, 3], "all", pen));
    expect([...e.h.flat(), ...e.v.flat()].every(entry)).toBe(true);
  });
});
