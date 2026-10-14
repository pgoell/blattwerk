// The writers of a table's lines: a border button, the line style and width, Schneidelinien, and a row or column
// that comes or goes. Each returns new props and never changes the ones it gets. `edges.ts` holds the reader.
import { edgesOf, linesOf as pens, THIN, type Edge, type Edges, type LineStyle, type Lines, type Pen } from "./edges";
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
  // A line drawn as the table draws its lines anyway holds nothing of its own: a table asked for what it has stays as it is.
  const own = pen.style === (p.lineStyle ?? "solid") && pen.width === (p.lineWidth ?? THIN);
  const out = edged(p, (e) => {
    for (const [axis, r, c] of linesOf(rect, which)) e[axis][r][c] = own ? null : { style: pen.style, width: pen.width };
  });
  if ([...out.edges!.h.flat(), ...out.edges!.v.flat()].some((edge) => edge !== null)) return out;
  if (!("edges" in p)) return p;
  const { edges: _, ...rest } = out;
  return rest as T;
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
  // What a table without the key has anyway is not written: a plain table asked for solid lines stays plain.
  const set = {
    ...(patch.style !== undefined && !(patch.style === "solid" && p.lineStyle === undefined) && { lineStyle: patch.style }),
    ...(patch.width !== undefined && !(patch.width === THIN && p.lineWidth === undefined) && { lineWidth: patch.width }),
  };
  const out = { ...p, ...set };
  const e = edgesOf(p);
  if (!e) return out;
  const h = e.h.map((list) => list.map(drop));
  const v = e.v.map((list) => list.map(drop));
  if ([...h.flat(), ...v.flat()].some((edge) => edge !== null)) return { ...out, edges: { h, v } };
  delete out.edges;
  return out;
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
// A new row or column takes a line that crosses it where its neighbours on both sides draw that same line (the one
// neighbour at the rim): a closed frame stays closed and a thick line inside runs on (#562, #567), and a box round
// one cell does not grow. A line hidden inside a merged cell is not taken. Its other new lines are null: the
// table's style. `after`: the new row or column goes after the anchor (the cell open while it is added), not before it.
export function edgesSpliced(p: Table & { spans?: unknown }, axis: "row" | "col", i: number, add: boolean, after = false): Edges | undefined {
  const e = edgesOf(p);
  if (!e) return undefined;
  const [rows, cols] = [p.cells.length, p.cols.length];
  const pen = pens(p);
  // The line at `c` that crosses row (or column) `at`, or undefined where there is none to take.
  const crossing = (cross: "h" | "v", at: number, c: number) => {
    if (at < 0 || at >= (axis === "row" ? rows : cols)) return undefined;
    const [r, k] = cross === "v" ? [at, c] : [c, at];
    return pen(cross, r, k).style === "none" ? null : e[cross][r][k];
  };
  const taken = (cross: "h" | "v", c: number): Edge => {
    const [before, below] = [crossing(cross, i - 1, c), crossing(cross, i, c)];
    if (before === null || below === null) return null;
    if (before === undefined || below === undefined) return before ?? below ?? null;
    return JSON.stringify(before) === JSON.stringify(below) ? before : null;
  };
  const same = (a: Edge, b: Edge | undefined) => a !== null && JSON.stringify(a) === JSON.stringify(b);
  // The line at the join, split in two: each run of one pen along it stays with the side whose lines across meet the
  // run's ends in that pen too (a box round cells on that side), and with the anchor where both sides or neither do
  // (#574). `first(k)` and `second(k)` are the lines across on each side at point k of the join.
  const split = (join: Edge[], first: (k: number) => Edge | undefined, second: (k: number) => Edge | undefined): [Edge[], Edge[]] => {
    const [a, b] = [nulls(join.length), nulls(join.length)];
    for (let s = 0, t = 0; s < join.length; s = t) {
      for (t = s + 1; t < join.length && JSON.stringify(join[t]) === JSON.stringify(join[s]); t++);
      const line = join[s];
      const one = same(line, first(s)) || same(line, first(t));
      const two = same(line, second(s)) || same(line, second(t));
      const [toFirst, toSecond] = one === two ? [after, !after] : [one, two];
      for (let k = s; k < t; k++) [a[k], b[k]] = [toFirst ? line : null, toSecond ? line : null];
    }
    return [a, b];
  };
  if (axis === "row") {
    if (add && i > 0 && i < rows) {
      const [a, b] = split(e.h[i], (k) => e.v[i - 1][k], (k) => e.v[i][k]);
      return { h: [...e.h.slice(0, i), a, b, ...e.h.slice(i + 1)], v: insert(e.v, i, Array.from({ length: cols + 1 }, (_, c) => taken("v", c))) };
    }
    // Under the last row, a box round some of its cells stays round them: the bottom stays under its row, and a side
    // comes only where the line runs the table's full height (#584). A box round whole columns, its sides the table's
    // full height, is a frame of those columns: its bottom moves to the new rim with the sides, as a frame round the
    // table does.
    if (add && i === rows && rows > 0 && !e.h[rows].every((edge) => same(edge, e.h[rows][0]))) {
      // A side runs the full height when a line stands at it in every row, in whatever pen (#591).
      const full = (c: number) => e.v.every((list) => list[c] !== null);
      // In a table of one row every side runs its full height: a box there is round its cell. A frame of whole
      // columns has its top on the table's first line in the same pen as its bottom (#591).
      const framed = (c: number) => {
        if (rows === 1 || !same(e.h[0][c], e.h[rows][c])) return false;
        let [l, r] = [c, c + 1];
        while (l > 0 && !e.v[rows - 1][l]) l--;
        while (r < cols && !e.v[rows - 1][r]) r++;
        return full(l) && full(r);
      };
      const bottom = e.h[rows];
      return {
        h: [...e.h.slice(0, rows), bottom.map((edge, c) => (framed(c) ? null : edge)), bottom.map((edge, c) => (framed(c) ? edge : null))],
        // The new row's side at c comes where a frame moves to the rim beside it, or where the side is one pen down the
        // whole column (as before #591). Its pen is the first row's, not the last's, which a box round a cell may change.
        v: insert(
          e.v,
          rows,
          Array.from({ length: cols + 1 }, (_, c) => {
            const frame = (c > 0 && framed(c - 1)) || (c < cols && framed(c));
            const one = e.v.every((list) => same(list[c], e.v[0][c]));
            return rows > 1 && ((full(c) && frame) || one) ? e.v[0][c] : null;
          }),
        ),
      };
    }
    if (add) return { h: insert(e.h, i === 0 ? 1 : i, nulls(cols)), v: insert(e.v, i, Array.from({ length: cols + 1 }, (_, c) => taken("v", c))) };
    return { h: remove(e.h, i === rows - 1 ? i : i + 1), v: remove(e.v, i) };
  }
  if (add && i > 0 && i < cols) {
    const [a, b] = split(
      e.v.map((list) => list[i]),
      (k) => e.h[k][i - 1],
      (k) => e.h[k][i],
    );
    return { h: e.h.map((list, r) => insert(list, i, taken("h", r))), v: e.v.map((list, r) => [...list.slice(0, i), a[r], b[r], ...list.slice(i + 1)]) };
  }
  if (add) return { h: e.h.map((list, r) => insert(list, i, taken("h", r))), v: e.v.map((list) => insert(list, i === 0 ? 1 : i, null)) };
  return { h: e.h.map((list) => remove(list, i)), v: e.v.map((list) => remove(list, i === cols - 1 ? i : i + 1)) };
}
