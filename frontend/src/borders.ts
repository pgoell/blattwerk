// The writers of a table's lines: a border button, the line style and width, Schneidelinien, and a row or column
// that comes or goes. Each returns new props and never changes the ones it gets. `edges.ts` holds the reader.
import { edgesOf, THIN, type Edge, type Edges, type LineStyle, type Lines, type Pen } from "./edges";
import type { Rect } from "./cells";

// The borders a button puts its pen on: all, the inner ones, the outer ones, or one side, or the inner lines across or down.
export type Border = "all" | "inner" | "outer" | "top" | "bottom" | "left" | "right" | "across" | "down";
type Table = Lines & { cells: string[][]; cols: number[] };
// A line of `Edges`: its axis, its row and its column in that axis's grid.
type At = ["h" | "v", number, number];

const nulls = (n: number) => Array<Edge>(n).fill(null);
// Inserts `one` before the entry at `at`, and takes out the entry at `at`.
const insert = <T,>(all: T[], at: number, one: T) => [...all.slice(0, at), one, ...all.slice(at)];
const remove = <T,>(all: T[], at: number) => [...all.slice(0, at), ...all.slice(at + 1)];

// The lines a border button writes, both ends of the rect inside. The top, the bottom, the left and the right are
// the rim; across and down are the lines inside it.
function linesOf([r0, c0, r1, c1]: Rect, which: Border): At[] {
  const range = (from: number, to: number) => Array.from({ length: to - from + 1 }, (_, i) => from + i);
  const top: At[] = range(c0, c1).map((c) => ["h", r0, c]);
  const bottom: At[] = range(c0, c1).map((c) => ["h", r1 + 1, c]);
  const left: At[] = range(r0, r1).map((r) => ["v", r, c0]);
  const right: At[] = range(r0, r1).map((r) => ["v", r, c1 + 1]);
  const across: At[] = range(r0 + 1, r1).flatMap((r) => range(c0, c1).map((c): At => ["h", r, c]));
  const down: At[] = range(c0 + 1, c1).flatMap((c) => range(r0, r1).map((r): At => ["v", r, c]));
  const outer = [...top, ...bottom, ...left, ...right];
  const inner = [...across, ...down];
  return { all: [...outer, ...inner], inner, outer, top, bottom, left, right, across, down }[which];
}

// The table's `edges` as a copy that `set` may write into. A table without valid `edges` gets a blank one.
// Lines are kept as they are where `set` does not write.
function edged<T extends Table>(p: T, set: (e: Edges) => void): T {
  const e = edgesOf(p) ?? { h: Array.from({ length: p.cells.length + 1 }, () => nulls(p.cols.length)), v: Array.from({ length: p.cells.length }, () => nulls(p.cols.length + 1)) };
  const copy: Edges = { h: e.h.map((list) => [...list]), v: e.v.map((list) => [...list]) };
  set(copy);
  return { ...p, edges: copy };
}

// The table with the lines of the rect that `which` names drawn with `pen`. A line between two cells is one line,
// so the later click wins. The cells of the rect stay as they are.
export function bordered<T extends Table>(p: T, rect: Rect, which: Border, pen: Pen): T {
  return edged(p, (e) => {
    for (const [axis, r, c] of linesOf(rect, which)) e[axis][r][c] = { style: pen.style, width: pen.width };
  });
}

// The table with its lines all of one style or width: `lineStyle` and `lineWidth` set, and the same key taken out of
// every line, so that each takes the table's. A line with no key left is null; no line left, no `edges` key.
export function lined<T extends Table>(p: T, patch: { style?: LineStyle; width?: number }): T {
  const keys = (["style", "width"] as const).filter((k) => patch[k] !== undefined);
  const drop = (edge: Edge): Edge => {
    if (!edge) return null;
    const kept: Record<string, unknown> = { ...edge };
    for (const k of keys) delete kept[k];
    return Object.keys(kept).length ? (kept as Edge) : null;
  };
  const { edges, lineStyle, lineWidth, ...rest } = p;
  const set = { ...(patch.style !== undefined && { lineStyle: patch.style }), ...(patch.width !== undefined && { lineWidth: patch.width }) };
  const e = edgesOf(p);
  if (!e) return { ...rest, ...set } as T;
  const h = e.h.map((list) => list.map(drop));
  const v = e.v.map((list) => list.map(drop));
  const any = [...h.flat(), ...v.flat()].some((edge) => edge !== null);
  return { ...rest, ...set, ...(any && { edges: { h, v } }) } as T;
}

// The table with Schneidelinien on or off. On: every line dashed and thin, `edges` gone, the scissors shown. Off: the
// three keys that Schneidelinien sets are taken away, and `edges` stays.
export function cutLines<T extends Table>(p: T, on: boolean): T {
  if (!on) {
    const { cut: _, lineStyle: __, lineWidth: ___, ...rest } = p;
    return rest as T;
  }
  const { edges: _, ...rest } = p;
  return { ...rest, cut: true, lineStyle: "dashed", lineWidth: THIN } as T;
}

// The `edges` of the table after a row or a column is added before the one at `i`, or the one at `i` is taken away.
// `p` is the table before the change. Undefined when it has no valid `edges`. A new row's top rim stays the rim.
export function edgesSpliced(p: Table, axis: "row" | "col", i: number, add: boolean): Edges | undefined {
  const e = edgesOf(p);
  if (!e) return undefined;
  const [rows, cols] = [p.cells.length, p.cols.length];
  if (axis === "row") {
    if (add) return { h: insert(e.h, i === 0 ? 1 : i, nulls(cols)), v: insert(e.v, i, nulls(cols + 1)) };
    return { h: remove(e.h, i === rows - 1 ? i : i + 1), v: remove(e.v, i) };
  }
  if (add) return { h: e.h.map((list) => insert(list, i, null)), v: e.v.map((list) => insert(list, i === 0 ? 1 : i, null)) };
  return { h: e.h.map((list) => remove(list, i)), v: e.v.map((list) => remove(list, i === cols - 1 ? i : i + 1)) };
}
