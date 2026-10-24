// A table's cells, and a row or column that comes or goes.

import { edgesSpliced } from "../borders";
import { type Span, heightsOf, spansOf } from "../cells";
import type { Lines } from "../edges";
import { PT } from "../height";
import type { Breaks } from "../syllables";
import type { Box, Align } from "./box";
import type { Font, Tints, Fade } from "./look";

// `cells` holds the texts, a row of columns at a time. `cols` holds each column's share of the block's width, in
// parts of their sum. A row is as high as its highest cell needs, and the rows share equally what room the block
// has beyond that. `line` is the colour of the lines, and `head` sets the first row in bold. A cell holds no runs, so
// a whole cell is a gap: `gaps` holds a flag for each cell, a row of columns at a time as `cells` does.
// `rows` holds a lowest height in mm for each row; a row still grows when its text needs more.
export type TableBlock = Box & {
  type: "table";
  /** The table's text, layout and lines. */
  props: {
    /** The text of each cell, as cells[row][column], counted from 0. A cell holds one plain text. */
    cells: string[][];
    /** The width share of each column, as parts of the sum of all of them. Only the ratios between columns count. */
    cols: number[];
    /** Font size of the cell text, in pt. */
    size: number;
    /** Horizontal alignment of the cell text: "left", "center" or "right". */
    align: Align;
    /** Font of the cell text. Left out, the default font. */
    font?: Font;
    /** Colour of the cell text. Left out, the default colour. */
    color?: string;
    /** Colour of the table's lines. */
    line: string;
    /** Whether the first row is printed in bold. Default false. */
    head?: boolean;
    /** Whether the words in the cells are split into syllables, with hyphens at the breaks. Default false. */
    syllables?: boolean;
    /** The teacher's own syllable breaks: each word in lower case as the key, with the places it breaks at as the value. */
    breaks?: Breaks;
    /** The two colours the syllables take in turn, first then second. */
    tints?: Tints;
    /** Whether the colours of the syllables turn on from word to word through the text. Left out, each word starts with the first colour. */
    tintsAcross?: boolean;
    /** Per cell, true makes the whole cell a gap to fill in, a row of columns at a time as cells does. */
    gaps?: boolean[][];
    /** Width of the gaps in mm, all the same. The editor takes 5 mm or more.
     * @minimum 5
     */
    gapWidth?: number;
    /** A word bank printed under the table for the gaps. Left out, there is none. */
    bank?: number;
    /** How the cell text shows as a trace to write over: true for grey, "outline" for letters with a line round them and no fill, "dotted" for dotted letters. Left out, no trace. */
    trace?: boolean | "outline" | "dotted";
    /** Makes the trace fade step by step until it is gone: "row" along each row, "rows" from row to row. Left out, no fade. */
    fade?: Fade;
    /** Merged cells, each as [row, column, rows, columns]: the cell where it starts and how many rows and columns it covers, counted from 0. */
    spans?: Span[];
    /** The lowest height of each row, in mm. A row still grows when its text needs more. */
    rows?: number[];
  } & Lines;
};
export const sum = (ns: number[]) => ns.reduce((all, n) => all + n, 0);
// A table's props with an empty row or column more, before the one at `i`, or without the one at `i`. A new column
// is as wide as the others are on average. The block's width changes by that in `rank`: the widths are shares of it.
// A row or column that comes or goes takes its gap flags along: a new one has no gap. A merged cell that grows or
// shrinks keeps its span; one that loses its first row or column hands its text and flag to the cell that starts it.
// A row that comes takes the height a new row gets in the editor; set heights of the other rows stay.
export function spliced(props: TableBlock["props"], axis: "row" | "col", i: number, add: boolean, after = false): TableBlock["props"] {
  // Row heights that do not hold go: with a row more they could fit by chance and set rows that never had them.
  // Lines that do not hold go too: with a row more or less they could fit by chance, on the wrong cells.
  const { cells, cols, gaps, spans: _, rows: __, edges: ___, ...rest } = props;
  const put =<T,>(all: T[], one: T) => [...all.slice(0, i), ...(add ? [one] : []), ...all.slice(add ? i : i + 1)];
  const heights = heightsOf(props);
  // A sheet may come from anywhere: the flags take the shape of the cells first.
  const held = gaps && cells.map((row, r) => row.map((_, c) => gaps[r]?.[c] === true));
  const grid = cells.map((row) => [...row]);
  const flagged = held?.map((row) => [...row]);
  const spans = spansOf(props).flatMap(([r, c, h, w]): Span[] => {
    const start = axis === "row" ? r : c;
    const len = axis === "row" ? h : w;
    let to = start;
    let n = len;
    if (add ? start >= i : start > i) to = start + (add ? 1 : -1);
    else if (!add && start === i && len > 1) {
      const [ar, ac] = axis === "row" ? [r + 1, c] : [r, c + 1];
      grid[ar][ac] = grid[r][c];
      grid[r][c] = "";
      if (flagged) [flagged[ar][ac], flagged[r][c]] = [flagged[r][c], false];
      n = len - 1;
    } else if (add ? start < i && i < start + len : start <= i && i < start + len) n = len + (add ? 1 : -1);
    const span: Span = axis === "row" ? [to, c, n, w] : [r, to, h, n];
    return span[2] * span[3] >= 2 ? [span] : [];
  });
  const flags = flagged && { gaps: axis === "row" ? put(flagged, cols.map(() => false)) : flagged.map((row) => put(row, false)) };
  const kept = spans.length ? { spans } : {};
  const edges = edgesSpliced(props, axis, i, add, after);
  if (axis === "row") return { ...rest, cols, cells: put(grid, cols.map(() => "")), ...flags, ...kept, ...(heights && { rows: put(heights, props.size * PT * 1.6 + 0.25) }), ...(edges && { edges }) };
  return { ...rest, cells: grid.map((row) => put(row, "")), cols: put(cols, sum(cols) / cols.length), ...flags, ...kept, ...(heights && { rows: heights }), ...(edges && { edges }) };
}
