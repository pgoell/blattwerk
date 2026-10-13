// The merged cells of a table: pure helpers over its grid. A merged cell is a rectangle of cells. Its top-left cell
// (its anchor) holds the text, and the other cells it covers hold nothing.

// A merged cell: where it starts, and how many rows and columns it covers.
export type Span = [row: number, col: number, rows: number, cols: number];
// A rectangle of cells, both ends inside: [first row, first col, last row, last col].
export type Rect = [number, number, number, number];
type Grid = { cells: string[][]; cols: number[]; gaps?: boolean[][]; spans?: unknown };

// The merged cells of a table that hold: a sheet may come from anywhere. An entry counts only when it is an array
// of four whole numbers, rows >= 1, cols >= 1, rows * cols >= 2, it lies inside the grid, it does not overlap an
// entry kept before it, and every cell it covers but its anchor holds "" (an older build may have let a teacher
// write there: then the cells show as single cells and no text is hidden). Anything else is dropped. Never throws.
export function spansOf(p: Grid): Span[] {
  if (!Array.isArray(p.spans)) return [];
  const width = p.cols.length;
  const taken = new Set<number>();
  const out: Span[] = [];
  for (const s of p.spans as unknown[]) {
    if (!Array.isArray(s) || s.length !== 4 || !s.every(Number.isInteger)) continue;
    const [r, c, h, w] = s as Span;
    if (r < 0 || c < 0 || h < 1 || w < 1 || h * w < 2 || r + h > p.cells.length || c + w > width) continue;
    const slots: number[] = [];
    for (let y = r; y < r + h; y++) for (let x = c; x < c + w; x++) slots.push(y * width + x);
    if (slots.some((slot) => taken.has(slot))) continue;
    if (cover(p, s as Span).slice(1).some(([y, x]) => (p.cells[y]?.[x] ?? "") !== "")) continue;
    slots.forEach((slot) => taken.add(slot));
    out.push(s as Span);
  }
  return out;
}

// The cells a span covers, its anchor first.
const cover = (p: Grid, [r, c, h, w]: Span) => {
  const out: [number, number][] = [];
  for (let y = r; y < r + h; y++) for (let x = c; x < c + w; x++) out.push([y, x]);
  return out;
};

// The span of the cell that holds `slot`: the merged cell that covers it, or [row, col, 1, 1].
export function spanAt(p: Grid, slot: number): Span {
  const width = p.cols.length;
  const row = Math.floor(slot / width);
  const col = slot % width;
  return spansOf(p).find(([r, c, h, w]) => row >= r && row < r + h && col >= c && col < c + w) ?? [row, col, 1, 1];
}

// The slot of the cell that holds `slot`: the anchor of the merged cell that covers it, or `slot` itself.
export function anchorOf(p: Grid, slot: number): number {
  const [r, c] = spanAt(p, slot);
  return r * p.cols.length + c;
}

// The smallest rectangle that holds the cells at slots `a` and `b` and every merged cell it cuts, whole.
export function rectOf(p: Grid, a: number, b: number): Rect {
  const width = p.cols.length;
  let [r0, c0, r1, c1] = [Math.min(Math.floor(a / width), Math.floor(b / width)), Math.min(a % width, b % width), Math.max(Math.floor(a / width), Math.floor(b / width)), Math.max(a % width, b % width)];
  // A merged cell that the rect cuts joins it, so the rect grows until no merged cell is cut.
  let grew = true;
  while (grew) {
    grew = false;
    for (const [r, c, h, w] of spansOf(p)) {
      if (r > r1 || r + h <= r0 || c > c1 || c + w <= c0) continue;
      const next: Rect = [Math.min(r0, r), Math.min(c0, c), Math.max(r1, r + h - 1), Math.max(c1, c + w - 1)];
      if (next.some((v, i) => v !== [r0, c0, r1, c1][i])) {
        [r0, c0, r1, c1] = next;
        grew = true;
      }
    }
  }
  return [r0, c0, r1, c1];
}

// The slots of the cells (anchors and plain cells, no covered ones) inside `rect`, in reading order.
export function slotsIn(p: Grid, [r0, c0, r1, c1]: Rect): number[] {
  const width = p.cols.length;
  const out: number[] = [];
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) if (anchorOf(p, r * width + c) === r * width + c) out.push(r * width + c);
  return out;
}

// Sets the merged cells of a grid to `spans`, or takes the key away when there are none.
const withSpans = <T extends Grid>(p: T, spans: Span[]): T => {
  const { spans: _, ...rest } = p;
  return (spans.length ? { ...rest, spans } : rest) as T;
};

// The table with the cells of `rect` as one cell. The texts that are not empty join in reading order with "\n"
// into the top-left cell, the others become "". The merged cells inside `rect` go into the new one. The top-left
// cell keeps its gap flag, the others lose theirs (when `gaps` is there). A rect of one cell changes nothing.
export function merged<T extends Grid>(p: T, rect: Rect): T {
  const [r0, c0, r1, c1] = rect;
  if (r0 === r1 && c0 === c1) return p;
  const inside = (r: number, c: number) => r >= r0 && r <= r1 && c >= c0 && c <= c1;
  const texts: string[] = [];
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) if (p.cells[r][c]) texts.push(p.cells[r][c]);
  const cells = p.cells.map((row, r) => row.map((text, c) => (inside(r, c) ? "" : text)));
  cells[r0][c0] = texts.join("\n");
  const gaps = p.gaps?.map((row, r) => row.map((flag, c) => (inside(r, c) && (r !== r0 || c !== c0) ? false : flag)));
  const kept = spansOf(p).filter(([r, c, h, w]) => r + h - 1 < r0 || r > r1 || c + w - 1 < c0 || c > c1);
  return withSpans({ ...p, cells, ...(gaps && { gaps }) }, [...kept, [r0, c0, r1 - r0 + 1, c1 - c0 + 1]]);
}

// The table without the merged cell at `slot`: its cells are single again, the text stays in the first.
// Drops the `spans` key when no merged cell is left.
export function unmerged<T extends Grid>(p: T, slot: number): T {
  const [r, c] = spanAt(p, slot);
  return withSpans(p, spansOf(p).filter(([sr, sc]) => sr !== r || sc !== c));
}

// The cell after (`step` 1) or before (-1) the one at `slot` in reading order, covered cells stepped over;
// undefined past the last or before the first.
export function next(p: Grid, slot: number, step: 1 | -1): number | undefined {
  const total = p.cells.flat().length;
  for (let s = slot + step; s >= 0 && s < total; s += step) if (anchorOf(p, s) === s) return s;
  return undefined;
}

// The cell above or below the one at `slot`, in the column where that one starts; undefined at the table's edge.
// From a merged cell "down" goes below its last row.
export function beside(p: Grid, slot: number, to: "up" | "down"): number | undefined {
  const [r, c, h] = spanAt(p, slot);
  const row = to === "up" ? r - 1 : r + h;
  if (row < 0 || row >= p.cells.length) return undefined;
  return anchorOf(p, row * p.cols.length + c);
}

// The table's line at its left and at its top, in mm: one pixel of the print. The columns share the block's width
// without it, and the rows its height, so a column measures its width from line to line.
export const EDGE = 25.4 / 96;

// Each column's width in mm in a block `w` mm wide.
export const widthsOf = (cols: number[], w: number): number[] => {
  const total = cols.reduce((all, n) => all + n, 0);
  return cols.map((n) => (n / total) * (w - EDGE));
};

// The lowest heights of a table's rows, one per row, when they hold: finite numbers above 0, as many as the rows.
// Anything else counts as absent. Never throws.
export function heightsOf(p: { cells: string[][]; rows?: unknown }): number[] | undefined {
  const rows = p.rows;
  if (!Array.isArray(rows) || rows.length !== p.cells.length) return undefined;
  return rows.every((h) => typeof h === "number" && Number.isFinite(h) && h > 0) ? (rows as number[]) : undefined;
}

// `sizes` with the entries from `from` to `to` set: each one `value`, or, without `each`, the same proportions
// with their sum `value`.
export function sized(sizes: number[], from: number, to: number, value: number, each: boolean): number[] {
  const inside = sizes.slice(from, to + 1);
  const total = inside.reduce((all, n) => all + n, 0);
  const share = inside.map((n) => (each ? value : total ? (n / total) * value : value / inside.length));
  return [...sizes.slice(0, from), ...share, ...sizes.slice(to + 1)];
}

// `sizes` with the entries from `from` to `to` made equal, each their share of the sum they hold.
export function evened(sizes: number[], from: number, to: number): number[] {
  const inside = sizes.slice(from, to + 1);
  const each = inside.reduce((all, n) => all + n, 0) / inside.length;
  return [...sizes.slice(0, from), ...inside.map(() => each), ...sizes.slice(to + 1)];
}
