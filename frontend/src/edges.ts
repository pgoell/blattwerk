// The lines of a table: what its props say of them, read with care. A table with none of the four keys below is an
// old table, and is drawn as it always was. `borders.ts` holds the writers.
import { spansOf } from "./cells";

export type LineStyle = "solid" | "dashed" | "dotted" | "none";
// One line between two cells, or along the table's rim. null, or a key left out: the table's own style or width.
export type Edge = {
  /** The style of this one line: "solid", "dashed", "dotted" or "none". Left out, the table's line style. */
  style?: LineStyle;
  /** The width of this one line, in mm, from 0.25 to 3. Left out, the table's line width.
   * @minimum 0.25
   * @maximum 3
   */
  width?: number;
} | null;
// h[r][c] is the line above cell (r, c), and h[rows][c] the line under the last row: rows + 1 lists of cols entries.
// v[r][c] is the line left of cell (r, c), and v[r][cols] the line right of the last column: rows lists of cols + 1.
export type Edges = {
  /** The lines across the table: h[row][column] is the line above that cell, and h[rows] the line under the last row. Null means the table's own line. */
  h: Edge[][];
  /** The lines down the table: v[row][column] is the line left of that cell, and v[row][columns] the line right of the last column. Null means the table's own line. */
  v: Edge[][];
};
// The four keys on a table's props, all optional. `lineStyle` and `lineWidth` (mm) are for every line; `cut` shows
// the scissors of Schneidelinien at the left end of the top line.
export type Lines = {
  /** The style of every line of the table: "solid", "dashed", "dotted" or "none". Left out, solid. */
  lineStyle?: LineStyle;
  /** The width of every line of the table, in mm, from 0.25 to 3. Left out, 0.25.
   * @minimum 0.25
   * @maximum 3
   */
  lineWidth?: number;
  /** Whether scissors mark a cutting line (Schneidelinie) at the left end of the top line. Left out, no. */
  cut?: boolean;
  /** The style and width of single lines, per edge of a cell. Left out, every line takes lineStyle and lineWidth. */
  edges?: Edges;
};
// What a line is drawn with.
export type Pen = { style: LineStyle; width: number };
type Grid = { cells: string[][]; cols: number[]; spans?: unknown; lineStyle?: unknown; lineWidth?: unknown; cut?: unknown; edges?: unknown };

export const STYLES: readonly LineStyle[] = ["solid", "dashed", "dotted", "none"];
// A width in mm: the steps of a shape's Randstärke. THIN is what a line has when no width is set.
export const [THIN, WIDEST, STEP] = [0.25, 3, 0.25];

const styleOf = (s: unknown) => (STYLES.includes(s as LineStyle) ? (s as LineStyle) : undefined);
const widthOf = (w: unknown) => (typeof w === "number" && w >= THIN && w <= WIDEST ? w : undefined);

// Whether the table has lines of the new kind: any of the four keys is there. Only then is anything drawn anew.
export const edged = (p: Grid) => [p.lineStyle, p.lineWidth, p.cut, p.edges].some((v) => v !== undefined && v !== null);

// The table's `edges` if they hold: a sheet may come from anywhere, and an older build adds a row without them.
// They count only when `h` is rows + 1 lists of cols entries and `v` rows lists of cols + 1, each entry null or an
// object whose `style`, if there, is a known one and whose `width`, if there, lies in the steps' range. Anything
// else and the whole of `edges` is left out: every line then takes the table's style. Never throws.
export function edgesOf(p: Grid): Edges | undefined {
  const e = p.edges as Partial<Edges> | null | undefined;
  if (!e || typeof e !== "object") return undefined;
  const [rows, cols] = [p.cells.length, p.cols.length];
  const entry = (x: unknown) =>
    x === null || (typeof x === "object" && !Array.isArray(x) && ((x as Pen).style === undefined || !!styleOf((x as Pen).style)) && ((x as Pen).width === undefined || !!widthOf((x as Pen).width)));
  const lists = (all: unknown, n: number, each: number) => Array.isArray(all) && all.length === n && all.every((list) => Array.isArray(list) && list.length === each && list.every(entry));
  return lists(e.h, rows + 1, cols) && lists(e.v, rows, cols + 1) ? (e as Edges) : undefined;
}

// The pen of each line of the table: `at("h", r, c)` for the line above cell (r, c), `at("v", r, c)` for the line
// left of it, counted as `Edges` counts them. A line inside a merged cell has the style "none".
export function linesOf(p: Grid): (axis: "h" | "v", r: number, c: number) => Pen {
  const edges = edgesOf(p);
  const [style, width] = [styleOf(p.lineStyle) ?? "solid", widthOf(p.lineWidth) ?? THIN];
  const spans = spansOf(p);
  const inside = (axis: "h" | "v", r: number, c: number) => spans.some(([y, x, h, w]) => (axis === "h" ? r > y && r < y + h && c >= x && c < x + w : c > x && c < x + w && r >= y && r < y + h));
  return (axis, r, c) => {
    const edge = edges?.[axis][r]?.[c];
    return { style: inside(axis, r, c) ? "none" : (edge?.style ?? style), width: edge?.width ?? width };
  };
}
