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
// `p` is the table before the change. Undefined when it has no valid `edges`. One rule for the four sides: lines are
// compared by their keys, the pen a line is drawn with (null when it is not drawn). Inside, the line at the join keeps
// the side it belongs to, and the other side and the new sides take the grid pen `G`. Under the last row (above the
// first, by flipping) a box round cells stays round them, and a frame or a one-pen rim moves its bottom to the new rim.
// The new row's sides are the sides of the rows above it. A column is a row of the transposed table. `after`: the new
// row or column goes after the anchor (the cell open while it is added), not before it.
type Grid<T> = { h: T[][]; v: T[][] };
const flip = <T,>(g: Grid<T>): Grid<T> => ({ h: [...g.h].reverse(), v: [...g.v].reverse() });
// Rows and columns swap: the line above (r, c) of one grid is the line left of (c, r) of the other.
const turn = <T,>(g: Grid<T>): Grid<T> => ({
  h: g.v[0].map((_, c) => g.v.map((list) => list[c])),
  v: g.h[0].map((_, c) => g.h.map((list) => list[c])),
});
// The whole numbers from a up to b, b not counted.
const span = (a: number, b: number) => Array.from({ length: b - a }, (_, x) => a + x);

// The grid after a row is added before the one at `i`. `e` holds the lines, `k` their keys.
function rowAdded(e: Grid<Edge>, k: Grid<string | null>, i: number, after: boolean): Grid<Edge> {
  const rows = k.v.length;
  const cols = k.h[0].length;
  if (i === 0) return flip(rowAdded(flip(e), flip(k), rows, after));
  // The grid pen: a key that more than half of all inner lines have, and at least half of those across and of those
  // down: a box round a whole row, half the lines across, does not hide a dashed grid, three boxes in one pen down
  // the table do not make a grid of it (#591).
  const innerH: [string | null, Edge][] = span(1, rows).flatMap((r) => span(0, cols).map((c): [string | null, Edge] => [k.h[r][c], e.h[r][c]]));
  const innerV: [string | null, Edge][] = span(0, rows).flatMap((r) => span(1, cols).map((c): [string | null, Edge] => [k.v[r][c], e.v[r][c]]));
  const count = (lines: [string | null, Edge][], key: string | null) => lines.filter(([x]) => x === key).length;
  const grid = [...innerH, ...innerV].find(
    ([key]) => key !== null && count([...innerH, ...innerV], key) * 2 > innerH.length + innerV.length && count(innerH, key) * 2 >= innerH.length && count(innerV, key) * 2 >= innerV.length,
  );
  const G: Edge = innerH.length && innerV.length && grid ? grid[1] : null;

  if (i < rows) {
    // The join splits in two. A run goes with the side whose lines across meet its ends in its key, or with the
    // anchor where both sides or neither do. The other side takes G.
    const [up, down, keys, join] = [k.v[i - 1], k.v[i], k.h[i], e.h[i]];
    const [a, b] = [nulls(cols), nulls(cols)];
    for (let s = 0, t = 0; s < cols; s = t) {
      for (t = s + 1; t < cols && keys[t] === keys[s]; t++);
      if (keys[s] === null) continue;
      const one = keys[s] === up[s] || keys[s] === up[t];
      const two = keys[s] === down[s] || keys[s] === down[t];
      const [toFirst, toSecond] = one === two ? [after, !after] : [one, two];
      for (let x = s; x < t; x++) [a[x], b[x]] = [toFirst ? join[x] : G, toSecond ? join[x] : G];
    }
    // A new side is the one on both sides when both are drawn in one key; not drawn on either, null; else G.
    const v = Array.from({ length: cols + 1 }, (_, j): Edge => (up[j] === null || down[j] === null ? null : up[j] === down[j] ? e.v[i - 1][j] : G));
    return { h: [...e.h.slice(0, i), a, b, ...e.h.slice(i + 1)], v: insert(e.v, i, v) };
  }

  // Under the last row. A box round cells of the rim: its sides run up from the rim to a closed top line.
  const last = rows - 1;
  const bottom = k.h[rows];
  const boxes: { l: number; r: number; top: number }[] = [];
  for (let c = 0; c < cols; c++) {
    const p = bottom[c];
    if (p === null) continue;
    const l = span(0, c + 1).reverse().find((j) => k.v[last][j] === p);
    const r = span(c + 1, cols + 1).find((j) => k.v[last][j] === p);
    if (l === undefined || r === undefined || !span(l, r).every((j) => bottom[j] === p)) continue;
    for (let row = last; row >= 0 && k.v[row][l] === p && k.v[row][r] === p; row--) {
      if (!span(l, r).every((j) => k.h[row][j] === p)) continue;
      // Closed. A frame round the whole table is no box.
      if (!(row === 0 && (rows > 1 || (l === 0 && r === cols)))) boxes.push({ l, r, top: row });
      break;
    }
  }
  // Every cell of the rim row a box, all in one pen, is a grid, not boxes: a dashed table of one row or column.
  if (boxes.some((b) => b.l !== boxes[0].l) && span(0, cols).every((c) => boxes.some((b) => b.l <= c && c < b.r)) && boxes.every((b) => bottom[b.l] === bottom[0])) boxes.length = 0;
  const boxed = (c: number) => boxes.some((b) => b.l <= c && c < b.r);
  // A frame of whole columns: full-height sides in the top line's key, on either side of the column.
  const full = (j: number) => k.v.every((list) => list[j] !== null);
  // The frame of column c, as the span [L, R) of columns between its two sides, if the bottom rim shows its key there.
  const frameOf = (c: number): [number, number] | undefined => {
    const f = k.h[0][c];
    if (f === null) return undefined;
    const side = (j: number) => full(j) && k.v[0][j] === f;
    // The table's own frame counts though a box covers its whole bottom; a frame of some columns shows its key there.
    const shows = (L: number, R: number) => side(L) && side(R) && ((L === 0 && R === cols) || span(L, R).some((x) => bottom[x] === f));
    if (rows === 1) return shows(0, cols) ? [0, cols] : undefined;
    // The nearest pair of sides whose bottom shows the key: in a dashed grid with a box round B3 the sides of B alone
    // do not, the table's do (#594).
    for (const L of span(0, c + 1).reverse().filter(side)) for (const R of span(c + 1, cols + 1).filter(side)) if (shows(L, R)) return [L, R];
    return undefined;
  };
  const framed = (c: number) => frameOf(c) !== undefined;
  const uniform = bottom[0] !== null && bottom.every((x) => x === bottom[0]) && boxes.length === 0;
  const moves = (c: number) => !boxed(c) && ((framed(c) && bottom[c] === k.h[0][c]) || uniform);
  const between = Array.from({ length: cols }, (_, c): Edge => (moves(c) ? G : e.h[rows][c]));
  const rim = Array.from({ length: cols }, (_, c): Edge => (moves(c) ? e.h[rows][c] : framed(c) ? e.h[0][c] : null));
  // The new row's side at j: the last row's, as Word runs a line on (#567), unless it is the side of a box that stays.
  // Then, beside a frame's side, the key most rows above have, a box's sides left out; else G, or null where no row is
  // left to ask (a box round a cell of a one-row table does not grow).
  const frameAt = (c: number) => (c >= 0 && c < cols ? frameOf(c) : undefined);
  const sides = Array.from({ length: cols + 1 }, (_, j): Edge => {
    const rowsOf = span(0, rows).filter((row) => !boxes.some((b) => (j === b.l || j === b.r) && b.top <= row));
    if (rowsOf.includes(last)) return k.v[last][j] === null ? null : e.v[last][j];
    const keys = rowsOf.map((row) => k.v[row][j]);
    if (keys.length === 0) return null;
    if ([frameAt(j - 1), frameAt(j)].some((f) => f && (f[0] === j || f[1] === j))) {
      const most = keys.reduce((best, key) => (keys.filter((x) => x === key).length > keys.filter((x) => x === best).length ? key : best));
      return e.v[rowsOf[keys.indexOf(most)]][j];
    }
    return G;
  });
  return { h: [...e.h.slice(0, rows), between, rim], v: [...e.v, sides] };
}

export function edgesSpliced(p: Table & { spans?: unknown }, axis: "row" | "col", i: number, add: boolean, after = false): Edges | undefined {
  const e = edgesOf(p);
  if (!e) return undefined;
  const [rows, cols] = [p.cells.length, p.cols.length];
  if (add) {
    const pen = pens(p);
    const key = (line: "h" | "v", r: number, c: number) => {
      const drawn = pen(line, r, c);
      // Null only for a line hidden inside a merged cell. A line drawn "none" is a pen like any other: a table
      // without a rim keeps none on its new rim (review of #596).
      const own = e[line][r][c]?.style ?? p.lineStyle ?? "solid";
      return drawn.style === "none" && own !== "none" ? null : JSON.stringify({ style: drawn.style, width: drawn.width });
    };
    const keys: Grid<string | null> = {
      h: Array.from({ length: rows + 1 }, (_, r) => Array.from({ length: cols }, (_, c) => key("h", r, c))),
      v: Array.from({ length: rows }, (_, r) => Array.from({ length: cols + 1 }, (_, c) => key("v", r, c))),
    };
    const g = axis === "row" ? rowAdded(e, keys, i, after) : turn(rowAdded(turn(e), turn(keys), i, after));
    return { h: g.h, v: g.v };
  }
  if (axis === "row") return { h: remove(e.h, i === rows - 1 ? i : i + 1), v: remove(e.v, i) };
  return { h: e.h.map((list) => remove(list, i)), v: e.v.map((list) => remove(list, i === cols - 1 ? i : i + 1)) };
}
