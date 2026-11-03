// The Karofeld (#831): a free grid with one digit or sign in each square, for Kopfrechnen, Rechenwege
// and geometry. A pure function of the block's settings, so the editor, the thumbnail and the PDF draw
// the same field.
//
// Stored shape: a block `{ type: "karofeld", props: KarofeldProps }`.
// - `cols`, `rows`: the grid, 1 to 30 across and 1 to 40 down.
// - `size`: the side of one square in mm, 4 to 16. `fontOf` is 55 % of that, and `boxOf` is cols by rows times it.
// - `look`: "karos" the squares, "kreise" a circle in each square, "punkte" a dot in each square, "iso" an isometric grid.
// - `cells`: the squares, row by row. A square holds one digit or one of + − · : = < >, optional `mark` "," or "." on a
//   digit, `line` for a Lösungsstrich, `thick` for a thick edge on top, right, bottom, left, and `fill` a hex colour.
// - `caret`: [column, row] of the square the next sign goes in.
// - `seed`: stored as the other blocks store one. The grid does not use it.
//
// `typeKaro` writes one sign and steps to the next square, or the next row at the end of a row. A comma or a point
// attaches to the digit just written and takes no square. `entered` moves to the start of the next row.
// `insertedSign` and `deletedSign` shift the rest of that row. `insertedRow` and `deletedRow` shift the rows below.
// `gridPoints` are the corners the field offers, and `snapped` picks the one within reach. `sane` never throws.

import { SIGNS } from "./sheet/maths";

export type KaroMark = "," | ".";
export type Look = "karos" | "kreise" | "punkte" | "iso";
export type Square = {
  /** The one digit or sign in the square. Left out, the square is empty. */
  sign?: string;
  /** A comma or a point attached to the digit. Left out, none. */
  mark?: KaroMark;
  /** A Lösungsstrich under the square, for the pupil to write on. Left out, none. */
  line?: boolean;
  /** Thick edges, in order top, right, bottom, left. Left out, every edge is thin. */
  thick?: boolean[];
  /** Background colour of the square, a six-digit hex colour such as #ffe066. Left out, none. */
  fill?: string;
};
export type KarofeldProps = {
  /** Squares across the grid.
   * @minimum 1
   * @maximum 30
   */
  cols: number;
  /** Squares down the grid.
   * @minimum 1
   * @maximum 40
   */
  rows: number;
  /** Side of one square in mm. The letter is a fixed share of it.
   * @minimum 4
   * @maximum 16
   */
  size: number;
  /** What is drawn: "karos" the squares, "kreise" a circle in each square, "punkte" a dot in each square, "iso" an isometric grid. */
  look: Look;
  /** The squares, row by row from the top left. A missing row or square is empty. */
  cells?: Square[][];
  /** The square the next sign goes in, as [column, row] counted from 0. Left out, the first square. */
  caret?: [number, number];
  /** Stored with the block, as the other maths blocks store a seed. The grid does not use it. */
  seed: number;
};

export const DEFAULTS: Omit<KarofeldProps, "seed"> = { cols: 10, rows: 8, size: 8, look: "karos" };

const DIGITS = "0123456789";
const SIN = Math.sin(Math.PI / 3);
const round = (n: number) => Math.round(n * 100) / 100;
const clamp = (n: unknown, lo: number, hi: number, fallback: number) =>
  typeof n === "number" && Number.isFinite(n) ? Math.min(hi, Math.max(lo, Math.round(n))) : fallback;

// One digit, or one sign as the sheet writes it. Anything else is not a square's content.
export function signOf(ch: string): string | undefined {
  if (ch.length !== 1) return undefined;
  if (DIGITS.includes(ch)) return ch;
  if (ch === "+") return SIGNS["+"];
  if (ch === "-" || ch === "\u2212") return SIGNS["-"];
  if (ch === "*" || ch === "\u00b7" || ch === "\u00d7") return SIGNS["*"];
  if (ch === "/" || ch === ":") return SIGNS["/"];
  if (ch === "=" || ch === "<" || ch === ">") return ch;
  return undefined;
}

function clean(sq: Square | undefined): Square {
  const sign = typeof sq?.sign === "string" ? signOf(sq.sign) : undefined;
  const out: Square = {};
  if (sign) out.sign = sign;
  if (sign && DIGITS.includes(sign) && (sq?.mark === "," || sq?.mark === ".")) out.mark = sq.mark;
  if (sq?.line === true) out.line = true;
  const thick = sq?.thick;
  if (Array.isArray(thick) && thick.length === 4 && thick.every((v) => typeof v === "boolean") && thick.some(Boolean)) out.thick = [thick[0], thick[1], thick[2], thick[3]];
  if (typeof sq?.fill === "string" && /^#[0-9a-fA-F]{6}$/.test(sq.fill)) out.fill = sq.fill.toLowerCase();
  return out;
}

function caretOf(p: KarofeldProps): [number, number] {
  const [c, r] = p.caret ?? [0, 0];
  if (typeof c !== "number" || typeof r !== "number") return [0, 0];
  return [Math.min(p.cols - 1, Math.max(0, Math.round(c))), Math.min(p.rows - 1, Math.max(0, Math.round(r)))];
}

function grid(p: KarofeldProps): Square[][] {
  return Array.from({ length: p.rows }, (_, r) => Array.from({ length: p.cols }, (_, c) => clean(p.cells?.[r]?.[c])));
}

export function sane(props: Partial<KarofeldProps> | undefined): KarofeldProps {
  const look = props?.look === "kreise" || props?.look === "punkte" || props?.look === "iso" ? props.look : "karos";
  const p: KarofeldProps = {
    cols: clamp(props?.cols, 1, 30, DEFAULTS.cols),
    rows: clamp(props?.rows, 1, 40, DEFAULTS.rows),
    size: clamp(props?.size, 4, 16, DEFAULTS.size),
    look,
    seed: typeof props?.seed === "number" && Number.isFinite(props.seed) ? Math.trunc(props.seed) : 1,
    caret: props?.caret,
    cells: props?.cells,
  };
  const cells = grid(p);
  const caret = caretOf(p);
  const held = cells.some((row) => row.some((sq) => sq.sign || sq.mark || sq.line || sq.fill || sq.thick));
  return { ...p, caret, ...(held ? { cells } : { cells: undefined }) };
}

function finish(p: KarofeldProps, cells: Square[][], cols: number, rows: number, caret: [number, number]): KarofeldProps {
  return sane({ ...p, cols, rows, cells, caret });
}

// The font size in mm for a square of `size` mm.
export const fontOf = (size: number): number => size * 0.55;

// The block's box when every square is `size` mm.
export function boxOf(props: KarofeldProps): { w: number; h: number } {
  const p = sane(props);
  return { w: round(p.cols * p.size), h: round(p.rows * p.size) };
}

// Writes `ch` into the caret's square and steps on. A comma or a point attaches to the digit and steps nowhere.
// Undefined when `ch` is not a digit, a sign, a comma or a point.
export function typeKaro(props: KarofeldProps, ch: string): KarofeldProps | undefined {
  const p = sane(props);
  const cells = grid(p);
  const [c, r] = caretOf(p);
  if (ch === "," || ch === ".") {
    const here = cells[r][c];
    const prev: [number, number] | undefined = here.sign ? undefined : c > 0 ? [c - 1, r] : r > 0 ? [p.cols - 1, r - 1] : undefined;
    const at = prev ?? (here.sign ? ([c, r] as [number, number]) : undefined);
    if (!at) return undefined;
    const sq = cells[at[1]][at[0]];
    if (!sq.sign || !DIGITS.includes(sq.sign)) return undefined;
    cells[at[1]][at[0]] = { ...sq, mark: ch };
    return finish(p, cells, p.cols, p.rows, [c, r]);
  }
  const sign = signOf(ch);
  if (!sign) return undefined;
  const sq: Square = { ...cells[r][c], sign };
  if (!DIGITS.includes(sign)) delete sq.mark;
  cells[r][c] = sq;
  const caret: [number, number] = c + 1 < p.cols ? [c + 1, r] : r + 1 < p.rows ? [0, r + 1] : [c, r];
  return finish(p, cells, p.cols, p.rows, caret);
}

// The caret goes to the first square of the next row. On the last row it stays.
export function entered(props: KarofeldProps): KarofeldProps {
  const p = sane(props);
  const [c, r] = caretOf(p);
  return r + 1 >= p.rows ? { ...p, caret: [c, r] } : { ...p, caret: [0, r + 1] };
}

// An empty square at the caret; the rest of the row shifts right. The grid gains a column.
export function insertedSign(props: KarofeldProps): KarofeldProps {
  const p = sane(props);
  const cells = grid(p);
  const [c, r] = caretOf(p);
  if (p.cols >= 30) {
    cells[r] = [...cells[r].slice(0, c), {}, ...cells[r].slice(c, -1)];
    return finish(p, cells, p.cols, p.rows, [c, r]);
  }
  const next = cells.map((row, i) => (i === r ? [...row.slice(0, c), {}, ...row.slice(c)] : [...row, {}]));
  return finish(p, next, p.cols + 1, p.rows, [c, r]);
}

// The caret's square goes; the rest of the row shifts left.
export function deletedSign(props: KarofeldProps): KarofeldProps {
  const p = sane(props);
  const cells = grid(p);
  const [c, r] = caretOf(p);
  cells[r] = [...cells[r].slice(0, c), ...cells[r].slice(c + 1), {}];
  let cols = p.cols;
  const blank = (sq?: Square) => !sq?.sign && !sq?.mark && !sq?.line && !sq?.fill && !sq?.thick?.some(Boolean);
  if (cols > 1 && cells.every((row) => blank(row[cols - 1]))) {
    cols -= 1;
    for (let i = 0; i < cells.length; i++) cells[i] = cells[i].slice(0, cols);
  }
  return finish(p, cells, cols, p.rows, [Math.min(c, cols - 1), r]);
}

// Backspace: the sign before the caret goes, and the rest of its row shifts left.
export function backspaced(props: KarofeldProps): KarofeldProps {
  const p = sane(props);
  const [c, r] = caretOf(p);
  if (c === 0 && r === 0) return deletedSign(p);
  const prev: [number, number] = c > 0 ? [c - 1, r] : [p.cols - 1, r - 1];
  return deletedSign({ ...p, caret: prev });
}

// An empty row at the caret; the rows below shift down.
export function insertedRow(props: KarofeldProps): KarofeldProps {
  const p = sane(props);
  if (p.rows >= 40) return p;
  const cells = grid(p);
  const [, r] = caretOf(p);
  cells.splice(r, 0, Array.from({ length: p.cols }, () => ({})));
  return finish(p, cells, p.cols, p.rows + 1, [0, r]);
}

// The caret's row goes; the rows below shift up. The last row stays, empty of signs it is not.
export function deletedRow(props: KarofeldProps): KarofeldProps {
  const p = sane(props);
  if (p.rows <= 1) return p;
  const cells = grid(p);
  const [, r] = caretOf(p);
  cells.splice(r, 1);
  return finish(p, cells, p.cols, cells.length, [0, Math.min(r, cells.length - 1)]);
}

// The caret's square takes the marks. `null` clears a fill or a mark.
export function painted(
  props: KarofeldProps,
  patch: { line?: boolean; thick?: boolean[]; fill?: string | null; mark?: KaroMark | null },
): KarofeldProps {
  const p = sane(props);
  const cells = grid(p);
  const [c, r] = caretOf(p);
  const sq: Square = { ...cells[r][c] };
  if (patch.line !== undefined) sq.line = patch.line;
  if (patch.thick) sq.thick = patch.thick;
  if (patch.fill === null) delete sq.fill;
  else if (typeof patch.fill === "string") sq.fill = patch.fill;
  if (patch.mark === null) delete sq.mark;
  else if (patch.mark) sq.mark = patch.mark;
  cells[r][c] = sq;
  return finish(p, cells, p.cols, p.rows, [c, r]);
}

// A line through (x0, y0) in direction (dx, dy), cut to the rectangle.
function segment(x0: number, y0: number, dx: number, dy: number, w: number, h: number): [number, number, number, number] | undefined {
  const hits: [number, number][] = [];
  const push = (x: number, y: number) => {
    if (x < -0.05 || y < -0.05 || x > w + 0.05 || y > h + 0.05) return;
    const pt: [number, number] = [round(Math.min(w, Math.max(0, x))), round(Math.min(h, Math.max(0, y)))];
    if (!hits.some((q) => q[0] === pt[0] && q[1] === pt[1])) hits.push(pt);
  };
  if (dx !== 0) {
    push(0, y0 + ((0 - x0) / dx) * dy);
    push(w, y0 + ((w - x0) / dx) * dy);
  }
  if (dy !== 0) {
    push(x0 + ((0 - y0) / dy) * dx, 0);
    push(x0 + ((h - y0) / dy) * dx, h);
  }
  if (hits.length < 2) return undefined;
  return [hits[0][0], hits[0][1], hits[1][0], hits[1][1]];
}

// The isometric lines across a cols-by-rows field, in the field's own millimetres.
export function isoLines(p: { cols: number; rows: number; size: number }): [number, number, number, number][] {
  const w = p.cols * p.size;
  const h = p.rows * p.size;
  const lines: [number, number, number, number][] = [];
  for (let y = 0; y <= h + 0.01; y += p.size * SIN) lines.push([0, round(Math.min(h, y)), w, round(Math.min(h, y))]);
  const n = Math.ceil((w + h) / p.size) + 2;
  for (let i = -n; i <= n; i++) {
    for (const dx of [0.5, -0.5]) {
      const seg = segment(i * p.size, 0, dx, SIN, w, h);
      if (seg && Math.hypot(seg[2] - seg[0], seg[3] - seg[1]) > 0.5) lines.push(seg);
    }
  }
  return lines;
}

export type Figure = { look: Look; lines: number; circles: number; dots: number };

// What each Darstellung draws, so a test can tell them apart without a browser.
export function figure(props: KarofeldProps): Figure {
  const p = sane(props);
  if (p.look === "punkte") return { look: p.look, lines: 0, circles: 0, dots: p.cols * p.rows };
  if (p.look === "iso") return { look: p.look, lines: isoLines(p).length, circles: 0, dots: 0 };
  const lines = p.cols + 1 + p.rows + 1;
  return { look: p.look, lines, circles: p.look === "kreise" ? p.cols * p.rows : 0, dots: 0 };
}

function isoPoints(x: number, y: number, p: KarofeldProps): [number, number][] {
  const w = p.cols * p.size;
  const h = p.rows * p.size;
  const pts: [number, number][] = [];
  for (let r = 0; r * p.size * SIN <= h + 0.01; r++) {
    for (let c = -r; c < 80; c++) {
      const px = c * p.size + r * p.size * 0.5;
      if (px > w + 0.01) break;
      if (px < -0.01) continue;
      pts.push([round(x + px), round(y + r * p.size * SIN)]);
    }
  }
  return pts;
}

// The grid points of the field, in page millimetres. A shape's end snaps to these.
export function gridPoints(origin: [number, number], props: KarofeldProps): [number, number][] {
  const p = sane(props);
  const [x, y] = origin;
  if (p.look === "iso") return isoPoints(x, y, p);
  const pts: [number, number][] = [];
  for (let r = 0; r <= p.rows; r++) for (let c = 0; c <= p.cols; c++) pts.push([round(x + c * p.size), round(y + r * p.size)]);
  return pts;
}

// The grid point within `reach` mm of `at`, the nearest when several are.
export function snapped(points: [number, number][], at: [number, number], reach: number): [number, number] | undefined {
  let best: [number, number] | undefined;
  let dist = reach;
  for (const pt of points) {
    const d = Math.hypot(pt[0] - at[0], pt[1] - at[1]);
    if (best === undefined ? d <= dist : d < dist) {
      best = pt;
      dist = d;
    }
  }
  return best;
}
