// The splice rule, and the lines a later splice must still fit.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { edgesOf, type Edge } from "./edges";
import { bordered, edgesSpliced } from "./borders";
import { spliced } from "./sheet";
import { pen, grid, drawn, type Table } from "./borders.fixtures";

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
    // A box on the rim shows its own pen there.
    expect(rim.every((edge) => json(edge) === json(solid) || json(edge) === json(dotted))).toBe(true);
    // The box stays round its old cell: four sides.
    // In b the box has the frame's pen, so its sides cannot be counted apart.
    if (k === "a") expect([...out.h.flat(), ...out.v.flat()].filter((edge) => json(edge) === json(dotted)).length).toBe(4);
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

// Found by the review of #596: each case as the reviewer gave it. `t(r, c)` is an empty table; the lines are read as
// their style after the splice, "s" where a line takes the table's solid default.
describe("review of #596", () => {
  const t = (rows: number, cols: number) => ({ cells: Array.from({ length: rows }, () => Array(cols).fill("")), cols: Array(cols).fill(1), size: 12 }) as unknown as Table;
  const none = { style: "none" as const, width: 0.25 };
  const dashed = { style: "dashed" as const, width: 0.25 };
  const styles = (p: Table, axis: "row" | "col", i: number, after = false) => {
    const e = edgesOf(spliced(p, axis, i, true, after) as never)!;
    const s = (edge: Edge) => edge?.style ?? "s";
    return { h: e.h.map((list) => list.map(s)), v: e.v.map((list) => list.map(s)) };
  };

  it("keeps a table without a rim without one, below, above and to the right", () => {
    const p = bordered(t(2, 3), [0, 0, 1, 2], "outer", none);
    const below = styles(p, "row", 2, true);
    expect(below.h[2]).toStrictEqual(["s", "s", "s"]);
    expect(below.h[3]).toStrictEqual(["none", "none", "none"]);
    expect(below.v[2]).toStrictEqual(["none", "s", "s", "none"]);
    expect(styles(p, "row", 0).h[0]).toStrictEqual(["none", "none", "none"]);
    const right = styles(p, "col", 3, true);
    expect(right.v.map((list) => list[4])).toStrictEqual(["none", "none"]);
    expect(right.h[0][3]).toBe("none");
    // A row inside: the new row's sides stay none (master drew them solid).
    expect(styles(p, "row", 1).v[1]).toStrictEqual(["none", "s", "s", "none"]);
  });

  it("keeps a none line at the join on one side when a row goes in between", () => {
    const p = bordered(t(2, 2), [0, 0, 1, 1], "across", none);
    const out = styles(p, "row", 1);
    expect([out.h[1], out.h[2]].filter((list) => list.every((x) => x === "none"))).toHaveLength(1);
  });

  it("keeps a dashed table of one column or one row dashed", () => {
    const column = bordered(t(3, 1), [0, 0, 2, 0], "all", dashed);
    for (const i of [0, 1]) expect(styles(column, "col", i, i === 1).h.flat().every((x) => x === "dashed")).toBe(true);
    const row = bordered(t(1, 3), [0, 0, 0, 2], "all", dashed);
    for (const i of [0, 1]) expect(styles(row, "row", i, i === 1).v.flat().every((x) => x === "dashed")).toBe(true);
  });

  it("keeps the dashed frame round a box round the whole last row", () => {
    const p = bordered(bordered(t(3, 4), [0, 0, 2, 3], "all", dashed), [2, 0, 2, 3], "outer", { style: "solid", width: 1 });
    const out = styles(p, "row", 3, true);
    expect(out.v[3]).toStrictEqual(["dashed", "dashed", "dashed", "dashed", "dashed"]);
    expect(out.h[4]).toStrictEqual(["dashed", "dashed", "dashed", "dashed"]);
    expect(out.h[3]).toStrictEqual(["solid", "solid", "solid", "solid"]);
  });
});
