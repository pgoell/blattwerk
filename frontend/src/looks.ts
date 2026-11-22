// The look of single cells of a table: their font, size, bold, italic and underline, each over the table's own.
// The grid lies beside `cells`, a row of columns at a time, as `gaps` does. Each cell's entry is an object, so that
// more keys (a fill, a padding) can join it later.
import type { Rect } from "./cells";
import { FONTS, type Font } from "./sheet/look";

// One cell's look. null, or a key left out: the table's own.
export type CellLook = {
  /** Font of this cell's text. Left out, the table's font. */
  font?: Font;
  /** Font size of this cell's text, in pt. Left out, the table's size.
   * @minimum 1
   */
  size?: number;
  /** True makes this cell's text bold, false makes it plain, also in a Kopfzeile. Left out, the table's setting. */
  bold?: boolean;
  /** True makes this cell's text italic. Left out, upright. */
  italic?: boolean;
  /** True underlines this cell's text. Left out, no underline. */
  underline?: boolean;
} | null;
export type Looks = CellLook[][];
type Look = NonNullable<CellLook>;
type Grid = { cells: string[][]; cols: number[]; looks?: unknown };

const FLAGS = ["bold", "italic", "underline"] as const;

// The keys of `x` that hold, or an empty look.
const sane = (x: unknown): Look => {
  if (!x || typeof x !== "object" || Array.isArray(x)) return {};
  const o = x as Record<string, unknown>;
  const out: Look = {};
  if (typeof o.font === "string" && Object.hasOwn(FONTS, o.font)) out.font = o.font as Font;
  if (typeof o.size === "number" && Number.isFinite(o.size) && o.size >= 1) out.size = o.size;
  for (const k of FLAGS) if (typeof o[k] === "boolean") out[k] = o[k];
  return out;
};

// The table's looks if they hold: as many rows as `cells`, each as many entries as columns. Anything else and the
// whole of `looks` counts as absent. Never throws.
export function looksOf(p: Grid): Looks | undefined {
  const l = p.looks;
  const [rows, cols] = [p.cells.length, p.cols.length];
  if (!Array.isArray(l) || l.length !== rows || !l.every((row) => Array.isArray(row) && row.length === cols)) return undefined;
  return l as Looks;
}

// The look of the cell at (r, c), with only the keys that hold.
export const lookAt = (p: Grid, r: number, c: number): Look => sane(looksOf(p)?.[r]?.[c]);

// The grid as it is saved: an empty look is null, and no grid at all when no cell has one.
function keep<T extends Grid>(p: T, grid: Look[][]): T {
  const { looks: _, ...rest } = p;
  const out = grid.map((row) => row.map((l) => (Object.keys(l).length ? l : null)));
  return (out.some((row) => row.some(Boolean)) ? { ...rest, looks: out } : rest) as T;
}

// Every cell's look, read with care.
const all = (p: Grid): Look[][] => p.cells.map((row, r) => p.cols.map((_, c) => lookAt(p, r, c)));

// The table with `patch` on each cell of `rect`. A key set to undefined goes back to the table's own.
export function looked<T extends Grid>(p: T, [r0, c0, r1, c1]: Rect, patch: Partial<Record<keyof Look, unknown>>): T {
  return keep(
    p,
    all(p).map((row, r) =>
      row.map((l, c) => {
        if (r < r0 || r > r1 || c < c0 || c > c1) return l;
        const next: Record<string, unknown> = { ...l, ...patch };
        for (const k of Object.keys(next)) if (next[k] === undefined) delete next[k];
        return next as Look;
      }),
    ),
  );
}

// The table with `key` out of every cell: what the table then sets holds for all of them.
export const unlooked = <T extends Grid>(p: T, key: keyof Look): T => looked(p, [0, 0, p.cells.length - 1, p.cols.length - 1], { [key]: undefined });
