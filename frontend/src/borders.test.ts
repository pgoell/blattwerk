// What a border, a line and the cut lines write on a table.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { edgesOf } from "./edges";
import { bordered, cutLines, lined, type Border } from "./borders";
import { pen, grid, drawn, want, written, type Table } from "./borders.fixtures";

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
