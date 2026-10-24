import { edgesOf, type Edge, type Edges, type Lines } from "./edges";
import { bordered, type Border } from "./borders";
import type { TableBlock } from "./sheet";

export type Table = TableBlock["props"];
export const pen = { style: "dotted" as const, width: 1 };
// A 3 by 4 table, with no lines written yet.
export const grid = { cells: Array.from({ length: 3 }, () => ["", "", "", ""]), cols: [1, 1, 1, 1] } as unknown as Table;
export const drawn = (p: Lines & Partial<Table>): Edges => edgesOf(p as never)!;
export const nulls = (n: number) => Array<Edge>(n).fill(null);

// The lines a border writes in the 3 by 4 table, for the rect [0, 1, 1, 2] (rows 0 to 1, columns 1 to 2).
export const want: Record<Border, string[]> = {
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
export const written = (e: Edges) => [
  ...e.h.flatMap((list, r) => list.flatMap((edge, c) => (edge ? [`h${r},${c}`] : []))),
  ...e.v.flatMap((list, r) => list.flatMap((edge, c) => (edge ? [`v${r},${c}`] : []))),
].sort();
