// Properties of the merged cells of a table: what merging, splitting and adding or removing a row or column make of its grid.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { anchorOf, beside, merged, next, rectOf, spanAt, spansOf, unmerged, type Span } from "./cells";
import { spliced, type TableBlock } from "./sheet";

type Table = TableBlock["props"];
type Op = { kind: "merge" | "unmerge" | "addRow" | "addCol" | "removeRow" | "removeCol"; a: number; b: number };

// A grid of up to 4 by 4 cells, some with text, some with a gap flag.
const table = fc
  .record({
    rows: fc.integer({ min: 1, max: 4 }),
    width: fc.integer({ min: 1, max: 4 }),
    texts: fc.array(fc.constantFrom("", "", "a", "b", "c d"), { minLength: 16, maxLength: 16 }),
    flags: fc.option(fc.array(fc.boolean(), { minLength: 16, maxLength: 16 }), { nil: undefined }),
  })
  .map(({ rows, width, texts, flags }) => {
    const grid = <T,>(f: (i: number) => T) => Array.from({ length: rows }, (_, r) => Array.from({ length: width }, (_, c) => f(r * width + c)));
    return { cells: grid((i) => texts[i]), cols: Array<number>(width).fill(1), ...(flags && { gaps: grid((i) => flags[i]) }) } as Table;
  });
const op = fc.record({ kind: fc.constantFrom<Op["kind"]>("merge", "merge", "merge", "unmerge", "addRow", "addCol", "removeRow", "removeCol"), a: fc.integer({ min: 0, max: 15 }), b: fc.integer({ min: 0, max: 15 }) });

// Each step applied to the table, with the slots and rows reduced to the grid.
const apply = (p: Table, { kind, a, b }: Op): Table => {
  const total = p.cells.flat().length;
  const rows = p.cells.length;
  const width = p.cols.length;
  switch (kind) {
    case "merge":
      return merged(p, rectOf(p, a % total, b % total));
    case "unmerge":
      return unmerged(p, a % total);
    case "addRow":
      return spliced(p, "row", a % (rows + 1), true);
    case "addCol":
      return spliced(p, "col", a % (width + 1), true);
    case "removeRow":
      return rows > 1 ? spliced(p, "row", a % rows, false) : p;
    case "removeCol":
      return width > 1 ? spliced(p, "col", a % width, false) : p;
  }
};

// The grid is whole, its spans lie inside it and do not overlap, and each covered cell holds "".
const sound = (p: Table) => {
  expect(p.cells.every((row) => row.length === p.cols.length)).toBe(true);
  const spans = spansOf(p);
  expect(spans.length).toBe(p.spans?.length ?? 0);
  if (!spans.length) expect("spans" in p).toBe(false);
  const seen = new Set<string>();
  for (const [r, c, h, w] of spans) {
    expect(r + h <= p.cells.length && c + w <= p.cols.length).toBe(true);
    for (let y = r; y < r + h; y++)
      for (let x = c; x < c + w; x++) {
        expect(seen.has(`${y},${x}`)).toBe(false);
        seen.add(`${y},${x}`);
        if (y !== r || x !== c) expect(p.cells[y][x]).toBe("");
      }
  }
};

// The lines of the texts, as a sorted list: merging and splitting must keep them all.
const lines = (p: Table) => p.cells.flat().flatMap((t) => t.split("\n")).filter(Boolean).sort();

describe("merged cells", () => {
  it("keeps the grid whole and the spans valid through any change", () => {
    fc.assert(
      fc.property(table, fc.array(op, { maxLength: 10 }), (start, ops) => {
        let p = start;
        sound(p);
        for (const o of ops) {
          p = apply(p, o);
          sound(p);
        }
      }),
    );
  });

  it("never loses a line of text when merging or splitting", () => {
    fc.assert(
      fc.property(table, fc.array(op.filter((o) => o.kind === "merge" || o.kind === "unmerge"), { maxLength: 10 }), (start, ops) => {
        let p = start;
        for (const o of ops) {
          p = apply(p, o);
          expect(lines(p)).toStrictEqual(lines(start));
        }
      }),
    );
  });

  it("keeps the anchor's text when a row or column goes through the first one of a span", () => {
    fc.assert(
      fc.property(table, fc.integer({ min: 0, max: 15 }), fc.integer({ min: 0, max: 15 }), fc.boolean(), (start, a, b, byRow) => {
        const total = start.cells.flat().length;
        const p = merged(start, rectOf(start, a % total, b % total));
        const s = spansOf(p).find(([, , h, w]) => (byRow ? h : w) > 1);
        if (!s) return;
        const [r, c] = s;
        const out = spliced(p, byRow ? "row" : "col", byRow ? r : c, false);
        expect(out.cells[r][c]).toBe(p.cells[r][c]);
      }),
    );
  });

  it("gives a table with no spans the same result as before, with no spans key", () => {
    fc.assert(
      fc.property(table, fc.boolean(), fc.integer({ min: 0, max: 4 }), fc.boolean(), (p, byRow, at, add) => {
        const rows = p.cells.length;
        const width = p.cols.length;
        const i = add ? at % ((byRow ? rows : width) + 1) : at % (byRow ? rows : width);
        if (!add && (byRow ? rows : width) < 2) return;
        const out = spliced(p, byRow ? "row" : "col", i, add);
        const put = <T,>(all: T[], one: T) => [...all.slice(0, i), ...(add ? [one] : []), ...all.slice(add ? i : i + 1)];
        const want = byRow
          ? { cells: put(p.cells, p.cols.map(() => "")), ...(p.gaps && { gaps: put(p.gaps, p.cols.map(() => false)) }) }
          : { cells: p.cells.map((row) => put(row, "")), cols: put(p.cols, p.cols.reduce((all, n) => all + n, 0) / width), ...(p.gaps && { gaps: p.gaps.map((row) => put(row, false)) }) };
        expect(out).toStrictEqual({ ...p, ...want });
        expect("spans" in out).toBe(false);
      }),
    );
  });

  it("gives rectangles that hold both cells and every merged cell they cut whole", () => {
    fc.assert(
      fc.property(table, fc.array(op.filter((o) => o.kind === "merge"), { maxLength: 4 }), fc.integer({ min: 0, max: 15 }), fc.integer({ min: 0, max: 15 }), (start, ops, a, b) => {
        const p = ops.reduce(apply, start);
        const total = p.cells.flat().length;
        const [x, y] = [a % total, b % total];
        const [r0, c0, r1, c1] = rectOf(p, x, y);
        const inside = (slot: number) => {
          const [r, c] = [Math.floor(slot / p.cols.length), slot % p.cols.length];
          return r >= r0 && r <= r1 && c >= c0 && c <= c1;
        };
        expect(inside(x) && inside(y)).toBe(true);
        for (const [r, c, h, w] of spansOf(p)) {
          const cuts = r <= r1 && r + h - 1 >= r0 && c <= c1 && c + w - 1 >= c0;
          if (cuts) expect(r >= r0 && r + h - 1 <= r1 && c >= c0 && c + w - 1 <= c1).toBe(true);
        }
      }),
    );
  });

  it("steps next and beside over covered cells only", () => {
    fc.assert(
      fc.property(table, fc.array(op.filter((o) => o.kind === "merge"), { maxLength: 4 }), (start, ops) => {
        const p = ops.reduce(apply, start);
        for (let slot = 0; slot < p.cells.flat().length; slot++) {
          for (const step of [1, -1] as const) {
            const n = next(p, slot, step);
            if (n === undefined) continue;
            expect(anchorOf(p, n)).toBe(n);
            expect(Math.sign(n - slot)).toBe(step);
          }
          for (const to of ["up", "down"] as const) {
            const n = beside(p, slot, to);
            if (n !== undefined) expect(anchorOf(p, n)).toBe(n);
          }
        }
      }),
    );
  });
});

describe("spansOf", () => {
  const cells = [
    ["a", "", ""],
    ["", "", "b"],
  ];
  const cols = [1, 1, 1];
  it("keeps the spans that hold", () => {
    expect(spansOf({ cells, cols, spans: [[0, 0, 1, 2]] })).toStrictEqual([[0, 0, 1, 2]]);
    expect(spansOf({ cells, cols })).toStrictEqual([]);
  });

  it("drops what does not hold", () => {
    const bad: unknown[] = ["x", [0, 0, 2], [0, 0, 0, 2], [0.5, 0, 2, 2], null, [0, 0, 1, 1], [1, 2, 2, 1], [0, 0, 1, 2, 3]];
    for (const entry of bad) expect(spansOf({ cells, cols, spans: [entry] })).toStrictEqual([]);
    expect(spansOf({ cells, cols, spans: "x" })).toStrictEqual([]);
    expect(spansOf({ cells, cols, spans: {} })).toStrictEqual([]);
    expect(spansOf({ cells, cols, spans: [[0, 0, 1, 2]] as Span[] })).toStrictEqual([[0, 0, 1, 2]]);
  });

  it("drops an entry over a cell that holds text, and one that overlaps an entry before it", () => {
    expect(spansOf({ cells, cols, spans: [[1, 1, 1, 2]] })).toStrictEqual([]);
    expect(spansOf({ cells, cols, spans: [[0, 0, 1, 2], [0, 1, 1, 2]] })).toStrictEqual([[0, 0, 1, 2]]);
  });

  it("reads the span and the anchor of a cell", () => {
    const p = { cells, cols, spans: [[0, 0, 1, 2] as Span] };
    expect(spanAt(p, 1)).toStrictEqual([0, 0, 1, 2]);
    expect(anchorOf(p, 1)).toBe(0);
    expect(anchorOf(p, 5)).toBe(5);
  });
});
