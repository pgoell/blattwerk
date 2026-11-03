// The Hunderterfeld: a Hundertertafel of the numbers 1 to 100 (or 0 to 99) in a 10 by 10 grid, or a field of 10 by
// 10 dots. A pure function of the block's settings and its seed, so the editor, the thumbnail and the PDF draw the
// same field.
//
// The contract of #85, which the model, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "hunderterfeld", props: HunderterfeldProps }`. All numbers are whole. A cell is named
// by its index i, 0 to 99, row by row from the top left: row `i div 10`, column `i mod 10`, number `from + i`.
// - `look`: "tafel" the Hundertertafel, "punkte" the field of dots (default "tafel").
// - `from`: the first number. 0 is 0 to 99. 1, 101, 201, … 901 are the Tausenderbuch pages (301 is 301 to 400).
//   Anything else is kept as 1 (default 1).
// - `show`, the Tafel's numbers: "all" every number, "none" none, "random" all but `hide` cells picked from the seed,
//   "free" all but the cells in `hidden`, "row" the row `cover`, "column" the column `cover`, "diagonal" one diagonal
//   (`cover` 1 from the top left, 2 from the top right), "muster" the picture `muster` (default "all"). `hide` 0 to 100
//   (default 20). `hidden`: cell indices. `cover` 1 to 10 (default 1). `muster`: "herz", "pfeil" or "a" to "z"
//   (default "herz"). `blank`, a hidden cell: "empty" the square stays, "grey" it is grey, "gone" it is not drawn
//   (default "empty"). The answer key still prints the number. A cut-out ignores `show` and `blank`.
// - `tint`, which cells of the Tafel are tinted: "none", "even" the even numbers, "times" the numbers 1·n to 10·n of
//   the Einmaleins row n = `times`, "row" the row `line`, "column" the column `line`, "free" the cells in `tints`
//   (default "none"). A rule tints in colour `color`, 1 or 2 (default 1). `times` 1 to 10 (default 2), `line` 1 to 10,
//   counted from the top or the left (default 1). `tints`: `[cell, 1 | 2]` each.
// - `cut`, the Ausschnitt (default false): only the cut's cells are drawn, the cell `given` shows its number and
//   the others are empty for the pupil to fill in (`shown` false, so the answer key prints them in red); `show` does
//   not count then, tints do. `form` picks the cells: "cells" the list `shape` (default a cross: 34, 43, 44, 45, 54),
//   "rect" the rectangle `wide` by `tall` from the top-left cell `anchor` (a 5 by 5 is wide 5, tall 5; clipped at the
//   edge), "row" the row `place`, "column" the column `place`. `given`: a cell index; one not in the cut gives the
//   lowest cell of it. An empty "cells" list draws nothing but the hint in the panel.
// - `fill`, the dots: "count" the first `dots` dots row by row (0 to 100, default 0), "free" the dots in `filled`
//   (default "count"). `filled`: cell indices.
// - `seed`: with the other props alone it gives the random hidden cells, so every draw gives the same ones.
// Indices out of 0 to 99, doubles and wrong kinds are dropped by `sane`, which never throws on any stored value.
// Settings of the other look and mode stay stored as they are, so switching back brings them back.
//
// The geometry: the field is a square in its own units, 100 by 100, laid in the block centred at the largest size
// that fits (`preserveAspectRatio` meet), so the field stays square whatever the block's shape and its numbers scale
// with the squares. The editor and the panel keep the block square on resize (as a picture or a symbol).
// - Tafel: cell i is the square of side 10 at (10·col, 10·row); its number centred in it at 4 units (40 % of a
//   square). The lines: 0.3 units, the outer frame 0.6.
// - Ausschnitt: the frame is the square around the bounding box of `shape`, side 10·max(cols, rows), centred on
//   it, so the cut-out fills the block; the numbers keep their size relative to a square, the lines their width on
//   the page (0.3 of a 100 field). The Punkte look ignores `cut` and always shows the whole field.
// - The svg's viewBox is the frame grown by one line width (0.3 of a 100 field) on each side, so no line lies on
//   the svg's edge.
// - Punkte: dot (row, col) has its centre at `dotAt(col)`, `dotAt(row)`: 8 + 9·k, plus 3 from the sixth on (the gap
//   after five each way), radius 3.6. A filled dot is #222, an empty one a circle of 0.4 in #222.
// - Tint colours (`TINT`): 1 a yellow and 2 a blue whose greys differ by at least 40 of 255 from each other and from
//   white (the grey of a black and white copy: 0.299 r + 0.587 g + 0.114 b), so they tell apart on a copy; the key's
//   red #c0392b differs from both by at least 40 too.
//
// The drawing, on screen and in print alike (`Draw` in sheet.tsx): `div.hunderterfeld` (with `.solved` in the answer
// key) holds one `svg` with the viewBox above. Tafel: per drawn cell `g.cell[data-i=i][data-value=v]` (with
// `data-tint` "1" or "2" when tinted) holding its `rect` and its number as `text.given` (#222) when it shows, or in
// the answer key as `text.answer` (#c0392b) when it is hidden. Punkte: per dot `circle.dot[data-i=i]`, class
// `filled` when filled. Numbers in Andika. The dock adds a block of 100 by 100 mm under "Mathe-Blöcke".
//
// The panel (pages/Hunderterfeld.tsx), by aria-label: "Darstellung" (select: "tafel" Hundertertafel, "punkte"
// Punktefeld), "Erste Zahl" (select: "1" 1 bis 100, "0" 0 bis 99). Tafel: "Zahlen" (select: "all" Alle, "none" Keine,
// "random" Zufällig verdeckt, "free" Selbst verdecken), for "random" "Verdeckt" (number input) and "Neu würfeln";
// "Färben" (select: "none" Nicht, "even" Gerade Zahlen, "times" Einmaleins-Reihe, "row" Eine Zeile, "column" Eine
// Spalte, "free" Selbst färben), for "times" "Reihe" and for "row" and "column" "Nummer" (number inputs), for a rule
// "Farbe" (select: "1" Gelb, "2" Blau); "Ausschnitt" (checkbox). Punkte: "Füllen" (select: "count" Anzahl, "free"
// Selbst füllen), for "count" "Gefüllt" (number input). While a mode set by clicking is on, a grid of 100 buttons
// `.hundert button`, each "Feld <v>", with `data-hidden`, `data-tint` "1" | "2", `data-cut` "in" | "given",
// `data-filled` as stored; with more than one such mode a select "Klick setzt" ("hide" Verdecken, "tint" Färben,
// "cut" Ausschnitt, "fill" Füllen) says which a click sets. A click toggles hidden, cycles the tint none, 1, 2,
// cycles the Ausschnitt out, in, given (a new given makes the old one plain in), toggles filled. Each change is one
// undo step; typing into one field is one step.
//
// The props type lives here; sheet.tsx imports it (and draws the block), never the other way round but for types.

import { rng } from "./zahlenmauer";
import { STARTS, cutOf, hideOf, type Start } from "./hunderterfeld-shape";
import { MUSTER_NAMES, type MusterName } from "./hunderterfeld-muster";

export type Tint = 1 | 2;
export type { Start, MusterName };
export { STARTS, MUSTER_NAMES };
// Grey of a hidden cell with `blank` "grey". It sits 47 of 255 under white, so a copy shows it.
export const GREY = "#d0d0d0";
export type HunderterfeldProps = {
  /** What is drawn: "tafel" the Hundertertafel with its numbers in a 10 by 10 grid, "punkte" a field of 10 by 10 dots. Default "tafel". */
  look: "tafel" | "punkte";
  /** The first number of the Tafel. 0 gives 0 to 99. 1, 101, 201, … 901 give that page of a hundred (301 gives 301 to 400). Anything else is read as 1. Default 1. */
  from: Start;
  /** Which numbers of the Tafel show. "all": every number. "none": no number. "random": all but `hide` cells, picked from the seed, are hidden. "free": all but the cells in `hidden` show. "row" and "column": the row or column `cover`. "diagonal": one diagonal, `cover` 1 from the top left or 2 from the top right. "muster": the picture `muster`. Default "all". */
  show: "all" | "none" | "random" | "free" | "row" | "column" | "diagonal" | "muster";
  /** Number of cells hidden with `show` "random". Default 20.
   * @minimum 0
   * @maximum 100
   */
  hide: number;
  /** Cell indices (0 to 99, row by row from the top left) whose number is hidden with `show` "free". */
  hidden?: number[];
  /** The row or column hidden with `show` "row" or "column", 1 to 10 from the top or the left. For "diagonal", 1 is top left to bottom right and 2 is the other; any other value is read as 1. Default 1.
   * @minimum 1
   * @maximum 10
   */
  cover?: number;
  /** The picture hidden with `show` "muster": "herz", "pfeil", or a letter "a" to "z". An unknown name is read as "herz". Default "herz". */
  muster?: MusterName;
  /** How a hidden cell of the Tafel is drawn. "empty": the square stays and the number is gone. "grey": the square is grey. "gone": the square is not drawn. The answer key still prints the number. Ignored while `cut` is on. Default "empty". */
  blank?: "empty" | "grey" | "gone";
  /** Which cells of the Tafel are tinted. "none": no cell. "even": the even numbers. "times": the multiples of `times` up to 10 times `times`. "row": the row `line`. "column": the column `line`. "free": the cells in `tints`. Default "none". */
  tint: "none" | "even" | "times" | "row" | "column" | "free";
  /** The row of the Einmaleins that "times" tints, 1 to 10. Default 2.
   * @minimum 1
   * @maximum 10
   */
  times: number;
  /** The row or column tinted with "row" or "column", counted from the top or the left, 1 to 10. Default 1.
   * @minimum 1
   * @maximum 10
   */
  line: number;
  /** The colour of a tint from "even", "times", "row" or "column": 1 yellow, 2 blue. Default 1. */
  color: Tint;
  /** Each tinted cell with its colour, for tint "free": [cell index 0 to 99, colour 1 yellow or 2 blue]. */
  tints?: [number, Tint][];
  /** Cut-out (Ausschnitt): when true, only the cut's cells are drawn, and the cell `given` shows its number while the other cells stay empty for the pupil to fill in. Default false. */
  cut: boolean;
  /** Which cells a cut draws. "cells": the cells in `shape`. "rect": the rectangle `wide` by `tall` from `anchor`. "row": the row `place`. "column": the column `place`. Default "cells". */
  form?: "cells" | "rect" | "row" | "column";
  /** Width of a "rect" cut, in cells, 1 to 10. Default 5.
   * @minimum 1
   * @maximum 10
   */
  wide?: number;
  /** Height of a "rect" cut, in cells, 1 to 10. Default 5.
   * @minimum 1
   * @maximum 10
   */
  tall?: number;
  /** Top-left cell of a "rect" cut, 0 to 99, row by row. A rectangle past the right or bottom edge is clipped. Default 0.
   * @minimum 0
   * @maximum 99
   */
  anchor?: number;
  /** The row or column of a "row" or "column" cut, 1 to 10 from the top or the left. Default 1.
   * @minimum 1
   * @maximum 10
   */
  place?: number;
  /** Cell indices (0 to 99) drawn when `cut` is on and `form` is "cells". Default a cross: 34, 43, 44, 45, 54. An empty list draws nothing. */
  shape?: number[];
  /** The cell index (0 to 99) that shows its number with `cut`. If it is not in `shape`, the lowest cell of `shape` is used. Default 44.
   * @minimum 0
   * @maximum 99
   */
  given?: number;
  /** With "count", the first `dots` dots are filled, row by row. With "free", the dots in `filled` are. Default "count". */
  fill: "count" | "free";
  /** Number of filled dots with `fill` "count", counted row by row from the top left. Default 0.
   * @minimum 0
   * @maximum 100
   */
  dots: number;
  /** Cell indices (0 to 99) of the filled dots with `fill` "free". */
  filled?: number[];
  /** Seed for the random hidden cells with `show` "random". The same seed always hides the same cells. */
  seed: number;
};

// A cell of the Tafel: its index, its number, whether it is drawn (inside the Ausschnitt or no Ausschnitt), whether
// its number shows, and its tint (0 none).
export type Cell = { i: number; value: number; drawn: boolean; shown: boolean; tint: 0 | Tint; blank: "empty" | "grey" | "gone" };
// `frame`: the viewBox, `[x, y, side, side]` in the field's units. `filled`: per dot whether it is filled.
export type Made = { cells: Cell[]; frame: [number, number, number, number]; filled: boolean[] };

export const DEFAULTS: Omit<HunderterfeldProps, "seed"> = {
  look: "tafel",
  from: 1,
  show: "all",
  hide: 20,
  cover: 1,
  muster: "herz",
  blank: "empty",
  tint: "none",
  times: 2,
  line: 1,
  color: 1,
  cut: false,
  form: "cells",
  wide: 5,
  tall: 5,
  anchor: 0,
  place: 1,
  shape: [34, 43, 44, 45, 54],
  given: 44,
  fill: "count",
  dots: 0,
};
// The tint colours by tint, index 0 unused.
export const TINT = ["", "#f4c542", "#6f9fd8"] as const;
export const SIDE = 100;
export const CELL = 10;

// The centre of the dot in column (or row) k, in the field's units.
export function dotAt(k: number): number {
  return 8 + 9 * k + (k >= 5 ? 3 : 0);
}

// The props as they draw: any stored value gives whole props in range.
export function sane(p: HunderterfeldProps): HunderterfeldProps {
  const r = (p ?? {}) as unknown as Record<string, unknown>;
  return {
    look: pick(r.look, ["tafel", "punkte"] as const, DEFAULTS.look),
    from: (STARTS as readonly number[]).includes(r.from as number) ? (r.from as Start) : 1,
    show: pick(r.show, ["all", "none", "random", "free", "row", "column", "diagonal", "muster"] as const, DEFAULTS.show),
    hide: whole(r.hide, 0, 100, DEFAULTS.hide),
    hidden: cellList(r.hidden),
    cover: whole(r.cover, 1, 10, DEFAULTS.cover as number),
    muster: (MUSTER_NAMES as readonly string[]).includes(r.muster as string) ? (r.muster as MusterName) : "herz",
    blank: pick(r.blank, ["empty", "grey", "gone"] as const, "empty"),
    tint: pick(r.tint, ["none", "even", "times", "row", "column", "free"] as const, DEFAULTS.tint),
    times: whole(r.times, 1, 10, DEFAULTS.times),
    line: whole(r.line, 1, 10, DEFAULTS.line),
    color: whole(r.color, 1, 2, DEFAULTS.color) as Tint,
    tints: tintList(r.tints),
    cut: typeof r.cut === "boolean" ? r.cut : DEFAULTS.cut,
    form: pick(r.form, ["cells", "rect", "row", "column"] as const, "cells"),
    wide: whole(r.wide, 1, 10, DEFAULTS.wide as number),
    tall: whole(r.tall, 1, 10, DEFAULTS.tall as number),
    anchor: whole(r.anchor, 0, 99, DEFAULTS.anchor as number),
    place: whole(r.place, 1, 10, DEFAULTS.place as number),
    shape: cellList(r.shape) ?? DEFAULTS.shape,
    given: whole(r.given, 0, 99, DEFAULTS.given as number),
    fill: pick(r.fill, ["count", "free"] as const, DEFAULTS.fill),
    dots: whole(r.dots, 0, 100, DEFAULTS.dots),
    filled: cellList(r.filled),
    seed: isWhole(r.seed) ? r.seed : 0,
  };
}

// The cells, the viewBox and the dots of the field. `p` is any stored value.
export function made(p: HunderterfeldProps): Made {
  const q = sane(p);
  const shape = q.cut ? cutOf(q.form ?? "cells", q.shape ?? [], q.anchor ?? 0, q.wide ?? 5, q.tall ?? 5, q.place ?? 1) : (q.shape ?? []);
  const inShape = new Set(shape);
  const rule = hideOf(q.show, q.cover ?? 1, q.muster ?? "herz");
  const given = shape.length === 0 ? -1 : inShape.has(q.given as number) ? (q.given as number) : Math.min(...shape);
  const rnd = rng(q.seed);
  const order = Array.from({ length: 100 }, (_, i) => i);
  for (let i = 99; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  const randomHidden = new Set(order.slice(0, q.hide));
  const hidden = new Set(q.hidden ?? []);
  const tints = new Map(q.tints ?? []);
  const cells: Cell[] = Array.from({ length: 100 }, (_, i) => {
    const value = q.from + i;
    const drawn = !q.cut || inShape.has(i);
    const shows = q.cut ? drawn && i === given : !numberHidden(q, i, randomHidden, hidden, rule);
    const blank = !shows && !q.cut && (q.blank === "grey" || q.blank === "gone") ? q.blank : "empty";
    return { i, value, drawn, shown: shows, tint: drawn ? tintOf(q, i, value, tints) : 0, blank };
  });
  const filledFree = new Set(q.filled ?? []);
  const filled = Array.from({ length: 100 }, (_, i) => (q.fill === "free" ? filledFree.has(i) : i < q.dots));
  return { cells, frame: frameOf(q, shape), filled };
}

// Whether cell i hides its number. A cut-out does not ask: its empty cells are for writing, not a hide rule.
function numberHidden(q: HunderterfeldProps, i: number, randomHidden: Set<number>, free: Set<number>, rule: Set<number> | null): boolean {
  if (q.show === "random") return randomHidden.has(i);
  if (q.show === "free") return free.has(i);
  if (rule) return rule.has(i);
  return q.show === "none";
}

// The tint of a drawn cell i with number `value`.
function tintOf(q: HunderterfeldProps, i: number, value: number, tints: Map<number, Tint>): 0 | Tint {
  const row = Math.floor(i / 10) + 1;
  const col = (i % 10) + 1;
  switch (q.tint) {
    case "even":
      return value % 2 === 0 ? q.color : 0;
    case "times":
      return value > 0 && value % q.times === 0 && value <= 10 * q.times ? q.color : 0;
    case "row":
      return row === q.line ? q.color : 0;
    case "column":
      return col === q.line ? q.color : 0;
    case "free":
      return tints.get(i) ?? 0;
    default:
      return 0;
  }
}

// The viewBox: the whole field, or with a cut-out the square around the bounding box of the shape, centred on it.
function frameOf(q: HunderterfeldProps, shape: number[]): Made["frame"] {
  if (q.look !== "tafel" || !q.cut || shape.length === 0) return [0, 0, SIDE, SIDE];
  const rows = shape.map((i) => Math.floor(i / 10));
  const cols = shape.map((i) => i % 10);
  const r0 = Math.min(...rows);
  const c0 = Math.min(...cols);
  const nr = Math.max(...rows) - r0 + 1;
  const nc = Math.max(...cols) - c0 + 1;
  const side = CELL * Math.max(nr, nc);
  return [CELL * c0 - (side - CELL * nc) / 2, CELL * r0 - (side - CELL * nr) / 2, side, side];
}

const isWhole = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v);
const whole = (v: unknown, lo: number, hi: number, dflt: number): number => (isWhole(v) && v >= lo && v <= hi ? v : dflt);
const pick = <T extends string>(v: unknown, list: readonly T[], dflt: T): T => list.find((x) => x === v) ?? dflt;
const isCell = (v: unknown): v is number => isWhole(v) && v >= 0 && v <= 99;
// The cells of a list, in order, each once; undefined when the stored value is no list.
const cellList = (v: unknown): number[] | undefined => (Array.isArray(v) ? [...new Set(v.filter(isCell))] : undefined);
// The free tints, the first entry for a cell wins; undefined when the stored value is no list.
function tintList(v: unknown): [number, Tint][] | undefined {
  if (!Array.isArray(v)) return undefined;
  const seen = new Map<number, Tint>();
  for (const e of v) if (Array.isArray(e) && isCell(e[0]) && (e[1] === 1 || e[1] === 2) && !seen.has(e[0])) seen.set(e[0], e[1]);
  return [...seen];
}
