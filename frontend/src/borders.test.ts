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

  // Issue #562 (PR #546): a new row or column takes the borders of its neighbour, so a closed frame stays closed.
  it("gives a row added below the frame's pen at both ends, and leaves the line between the rows null", () => {
    const out = edgesSpliced(sized, "row", 1, true)!;
    expect(out.v[1]).toStrictEqual(valid.v[0]);
    expect(out.v[1][0]).toStrictEqual(pen);
    expect(out.v[1][4]).toStrictEqual(pen);
    expect(out.h[1].every((edge) => edge === null)).toBe(true);
  });

  it("gives a row added at the top the first row's ends, and leaves the line under it null", () => {
    const out = edgesSpliced(sized, "row", 0, true)!;
    expect(out.v[0]).toStrictEqual(valid.v[0]);
    expect(out.h[1].every((edge) => edge === null)).toBe(true);
  });

  it("gives a column added to the right the last column's ends, and leaves the line beside it null", () => {
    const out = edgesSpliced(sized, "col", 4, true)!;
    for (let r = 0; r < out.h.length; r++) expect(out.h[r][4]).toStrictEqual(valid.h[r][3]);
    expect(out.h[0][4]).toStrictEqual(pen);
    expect(out.v.every((list) => list[4] === null)).toBe(true);
  });

  it("gives a column added at the left the first column's ends, and leaves the line beside it null", () => {
    const out = edgesSpliced(sized, "col", 0, true)!;
    for (let r = 0; r < out.h.length; r++) expect(out.h[r][0]).toStrictEqual(valid.h[r][0]);
    expect(out.v.every((list) => list[1] === null)).toBe(true);
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
