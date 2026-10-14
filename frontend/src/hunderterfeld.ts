// The Hunderterfeld: a Hundertertafel of the numbers 1 to 100 (or 0 to 99) in a 10 by 10 grid, or a field of 10 by
// 10 dots. A pure function of the block's settings and its seed, so the editor, the thumbnail and the PDF draw the
// same field.
//
// The contract of #85, which the model, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "hunderterfeld", props: HunderterfeldProps }`. All numbers are whole. A cell is named
// by its index i, 0 to 99, row by row from the top left: row `i div 10`, column `i mod 10`, number `from + i`.
// - `look`: "tafel" the Hundertertafel, "punkte" the field of dots (default "tafel").
// - `from`: the first number, 1 (1 to 100) or 0 (0 to 99) (default 1).
// - `show`, the Tafel's numbers: "all" every number, "none" none, "random" all but `hide` cells picked from the seed,
//   "free" all but the cells in `hidden` (default "all"). `hide` 0 to 100 (default 20). `hidden`: cell indices.
// - `tint`, which cells of the Tafel are tinted: "none", "even" the even numbers, "times" the numbers 1·n to 10·n of
//   the Einmaleins row n = `times`, "row" the row `line`, "column" the column `line`, "free" the cells in `tints`
//   (default "none"). A rule tints in colour `color`, 1 or 2 (default 1). `times` 1 to 10 (default 2), `line` 1 to 10,
//   counted from the top or the left (default 1). `tints`: `[cell, 1 | 2]` each.
// - `cut`, the Ausschnitt (default false): only the cells in `shape` are drawn, the cell `given` shows its number and
//   the others are empty for the pupil to fill in (`shown` false, so the answer key prints them in red); `show` does
//   not count then, tints do. `shape`: cell indices
//   (default a cross: 34, 43, 44, 45, 54). `given`: a cell index; one not in `shape` gives the lowest cell of `shape`.
//   An empty shape draws nothing but the hint in the panel.
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
// - Ausschnitt: the viewBox is the square around the bounding box of `shape`, side 10·max(cols, rows), centred on
//   it, so the cut-out fills the block; the lines and the numbers keep their size relative to a square.
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

export type Tint = 1 | 2;
export type HunderterfeldProps = {
  look: "tafel" | "punkte";
  from: 0 | 1;
  show: "all" | "none" | "random" | "free";
  hide: number;
  hidden?: number[];
  tint: "none" | "even" | "times" | "row" | "column" | "free";
  times: number;
  line: number;
  color: Tint;
  tints?: [number, Tint][];
  cut: boolean;
  shape?: number[];
  given?: number;
  fill: "count" | "free";
  dots: number;
  filled?: number[];
  seed: number;
};

// A cell of the Tafel: its index, its number, whether it is drawn (inside the Ausschnitt or no Ausschnitt), whether
// its number shows, and its tint (0 none).
export type Cell = { i: number; value: number; drawn: boolean; shown: boolean; tint: 0 | Tint };
// `frame`: the viewBox, `[x, y, side, side]` in the field's units. `filled`: per dot whether it is filled.
export type Made = { cells: Cell[]; frame: [number, number, number, number]; filled: boolean[] };

export const DEFAULTS: Omit<HunderterfeldProps, "seed"> = {
  look: "tafel",
  from: 1,
  show: "all",
  hide: 20,
  tint: "none",
  times: 2,
  line: 1,
  color: 1,
  cut: false,
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

// The props as they draw: any stored value gives whole props in range. Stub: the model task fills it in.
export function sane(p: HunderterfeldProps): HunderterfeldProps {
  return { ...DEFAULTS, ...(p ?? {}), seed: typeof p?.seed === "number" ? p.seed : 0 };
}

// The cells, the viewBox and the dots of the field. Stub: the model task fills it in.
export function made(p: HunderterfeldProps): Made {
  const q = sane(p);
  void rng;
  const cells: Cell[] = Array.from({ length: 100 }, (_, i) => ({ i, value: q.from + i, drawn: true, shown: q.show !== "none", tint: 0 }));
  return { cells, frame: [0, 0, SIDE, SIDE], filled: cells.map((c) => c.i < q.dots) };
}
