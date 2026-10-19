// The format panel's settings for the school blocks, and the numbering any block can have.
import { Fragment, useEffect, useRef, useState } from "react";
import { AlignVerticalJustifyCenter, AlignVerticalJustifyEnd, AlignVerticalJustifyStart, FlipHorizontal2, FlipVertical2, List as Bullets, ListOrdered, Lock, LockOpen, RotateCcw, Scissors, RotateCw, TextAlignCenter, TextAlignEnd, TextAlignStart, type LucideIcon } from "lucide-react";
import Numbering from "../components/Numbering";
import { allCellGap, allGap } from "../gaps";
import { cellEntries, draw, entries, moves, shuffled, type Shown } from "../bank";
import { mixed, word } from "../scramble";
import { pastPaper } from "../insert";
import { FONTS, FONT_GROUPS, GREYS, K, MARGIN, PT, RULINGS, ScoreInput, TINTS, bandColorOf, bandOf, boxed, counts, dir, dottedFamily, fadeOf, far, type ShapeBlock, fontOf, houseOf, houseTintOf, traceOf, type Fade, foldsOf, holesOf, isLine, kindOf, lineOf, listColsOf, listOf, lowest, mathsHeight, overFoot, pairOf, parasOf, rightmost, rowsNeeded, rowsOf, shade, shownParas, stepOf, fromOf, sum, symbol, tall, useSplitter, type Align, type Axis, type Block, type Box, type Corner, type Font, type List, type ListMode, type MathsProps, type Ruling, type RulingBlock, type TableBlock, type TextProps, type Valign, type Doc } from "../sheet";
import type { Marks, Picked } from "./Field";
import Maths from "./Maths";
import Suchsel from "./Suchsel";
import Zahlenmauer from "./Zahlenmauer";
import Zahlenhaus from "./Zahlenhaus";
import Rechendreieck from "./Rechendreieck";
import Zahlenstrahl from "./Zahlenstrahl";
import Hunderterfeld from "./Hunderterfeld";
import Uhr from "./Uhr";
import Selbstkontrolle from "./Selbstkontrolle";
import { filled, room, unshown } from "../words";
import { SYMBOLS } from "../symbols";
import { holed } from "../holes";
import { rectOf, spanAt, widthsOf, type Rect } from "../cells";
import type { Border } from "../borders";
import type { LineStyle, Pen } from "../edges";
import type { Owed } from "../saves";

type Props = {
  sel: Block[];
  // Keeps a maths change the session ran out on, for the editor to redo after the login (saves.ts `owe`).
  owe: (entry: Owed) => void;
  // Sets props on every selected block of one type.
  style: (type: Block["type"], props: object, key?: string, only?: string[]) => void;
  // Adds `by` to the score of each picked score box, each from its own number.
  bump: (by: number) => void;
  // Sets what a text and a shape share on every selected one of them.
  look: (props: object, key?: string) => void;
  // Sets the trace text's look on every picked block that carries text, in one step.
  traced: (props: object) => void;
  // Makes the picked texts and shapes take the sheet's Lernwörter as their text, or cut them loose with their words.
  link: (on: boolean) => void;
  // Sets props on the picked texts and shapes that take the Lernwörter, as `look` does for all of them.
  feed: (props: object, key?: string) => void;
  // Sets bold, italic, underline or colour on the words picked in the text being edited, or else as `look` does.
  paint: (props: Marks, key?: string) => void;
  // Mends a word's split on every block of the sheet, or with no counts takes the mend back to the module's own split.
  mendWord: (keys: string[], counts: number[] | undefined, id: string) => void;
  // Makes a list of the paragraphs the caret stands in, or else of all the selected texts.
  itemize: (kind: List) => void;
  // Makes the picked words, the cell being edited or else every selected text a gap, or takes the gap off.
  gap: (on: boolean) => void;
  // Makes every n-th word of every selected text a gap.
  every: (n: number) => void;
  // What is picked in the text being edited.
  part?: Picked;
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
  // Adds a row or a column to a table before the one at `i`, or takes the one at `i` away.
  rank: (b: TableBlock, axis: "row" | "col", i: number, add: boolean, after?: boolean) => void;
  // The cell of the table being edited, counted row by row.
  cell?: number;
  // The far corner of the cells picked with the open one, if any.
  reach?: number;
  // Makes the picked cells one cell, or brings the open merged cell back to single cells.
  merge: () => void;
  unmerge: () => void;
  // The height in mm of each row of the table being edited, as its grid lays them out.
  laid: number[];
  // The ids of the blocks whose text the page's foot cuts short.
  full: string[];
  // The ids of the shapes whose word does not print whole, wherever they stand.
  cramped: string[];
  // The ids of the picked shapes whose text grew them back after a smaller size from this panel.
  held: string[];
  // Tells the editor which blocks this panel resizes.
  onSize: (ids: string[]) => void;
  // Sets the width of the picked columns, or the height of the picked rows, in mm; or evens them out.
  sizeCells: (axis: "col" | "row", mm: number) => void;
  evenCells: (axis: "col" | "row") => void;
  // The line style and width of every picked table, or the one line of its `key` in a drag; Schneidelinien on or off.
  lines: (patch: { style?: LineStyle; width?: number }, key?: string) => void;
  cutting: (on: boolean) => void;
  // Draws the pen on the chosen borders of the table being edited.
  // Absent unless one table that is not locked is picked alone.
  border?: (which: Border, pen: Pen) => void;
  // Starts or ends crop mode; absent unless one picture that is not locked is selected.
  crop?: () => void;
  // The sheet's Lernwörter, and the mode each picked Lineatur takes them in: none cuts it loose with its words.
  words: string[];
  // Every Lineatur of the sheet: a picked one that a run-on Lineatur goes on from cuts off no word.
  lineaturen: RulingBlock[];
  list: (mode?: ListMode) => void;
  // Shows the list of the Lernwörter in the panel.
  toList: () => void;
  cropping: boolean;
  // Turns what is selected by so many degrees: a group picked whole as one, a loose block about its own centre.
  spin: (by: number) => void;
  // Mirrors what is selected across or down: a group picked whole as one, a loose block in itself.
  mirror: (axis: Axis) => void;
  // Whether the block is a thing by itself: loose, or picked out of its group.
  alone: (b: Block) => boolean;
  // Whether a new width sets the height to match, in the fields and on the handles.
  lock: boolean;
  setLock: (on: boolean) => void;
  // Where X and Y count from: the page's top left corner, or its centre. Kept by the editor, not in the sheet.
  from: "corner" | "centre";
  setFrom: (from: "corner" | "centre") => void;
  // The width and height in mm of the page in use.
  size: number[];
  // The whole sheet, for the maths blocks a Selbstkontrolle can check.
  doc: Doc;
};

const ALIGNS: [Align, string, LucideIcon][] = [["left", "Links", TextAlignStart], ["center", "Mitte", TextAlignCenter], ["right", "Rechts", TextAlignEnd]];
const LISTS: [List, string, LucideIcon][] = [["bullet", "Aufzählung", Bullets], ["number", "Nummerierung", ListOrdered]];
const VALIGNS: [Valign, string, LucideIcon][] = [["top", "Oben", AlignVerticalJustifyStart], ["middle", "Mitte", AlignVerticalJustifyCenter], ["bottom", "Unten", AlignVerticalJustifyEnd]];
// The turns by a quarter and the two flips: a flip has no degrees.
const TURNS: [string, LucideIcon, number][] = [["Rechtsdrehung 90°", RotateCw, 90], ["Linksdrehung 90°", RotateCcw, -90], ["Horizontal spiegeln", FlipHorizontal2, 0], ["Vertikal spiegeln", FlipVertical2, 0]];
const round = (n: number) => Math.round(n * 100) / 100;
// The hints for a maths block that grows past the margin's foot or the paper's edge, by type: a name sentence, then the take-away.
const FOOT: Record<string, [string, string]> = {
  zahlenhaus: ["Das Zahlenhaus ragt unten über den Rand.", "Nimm weniger Häuser oder Stockwerke oder schiebe es nach oben."],
  zahlenmauer: ["Die Zahlenmauer ragt unten über den Rand.", "Nimm weniger Mauern oder Grundsteine oder schiebe sie nach oben."],
  rechendreieck: ["Das Rechendreieck ragt unten über den Rand.", "Nimm weniger Dreiecke oder schiebe es nach oben."],
  uhr: ["Die Uhr ragt unten über den Rand.", "Nimm weniger Uhren oder schiebe sie nach oben."],
};
// An angle as a block stores it: from 0 up to 360.
export const norm = (a: number) => round(((a % 360) + 360) % 360) % 360;
// The box around several blocks.
export const bounds = (bs: Box[]) => {
  const [x, y] = [Math.min(...bs.map((b) => b.x)), Math.min(...bs.map((b) => b.y))];
  return { x, y, w: Math.max(...bs.map((b) => b.x + b.w)) - x, h: Math.max(...bs.map((b) => b.y + b.h)) - y };
};
// The level box around a turned block's outline. It has the block's centre.
export const outline = <T extends Box>(b: T): T => {
  const [c, s] = dir(b).map(Math.abs);
  const [w, h] = [b.w * c + b.h * s, b.w * s + b.h * c];
  return { ...b, x: b.x + (b.w - w) / 2, y: b.y + (b.h - h) / 2, w, h };
};
// The corner a line starts at after a quarter turn clockwise.
const NEXT: Record<Corner, Corner> = { nw: "ne", ne: "se", se: "sw", sw: "nw" };
// A block on its side whose width and height differ by an odd count of hundredths has its outline half a
// hundredth off the sheet's hundredths. This is how far its stored place lies from the one it is meant to have,
// to the right and up: so four quarter turns lead back to the hundredth.
const lean = (b: Box) => ((b.angle ?? 0) % 180 === 90 && Math.round((b.w + b.h) * 100) % 2 ? Math.sign(b.w - b.h) * 0.005 : 0);
// The box around the blocks as they are meant to lie, turned or not: the frame a group shows.
export const hull = (bs: Box[]) => bounds(bs.map((b) => outline({ ...b, x: b.x - lean(b), y: b.y + lean(b) })));
// A quarter turn clockwise of the blocks as one. The box around them goes on its side about its middle, to the
// hundredth: half a hundredth too many goes away one time and comes back the next. In it each block's centre goes
// round and keeps its distances to the edges, so all stays on the hundredths. A line has no angle: its box goes on
// its side, and the line starts at the next corner.
const quarter = (bs: Block[]): Block[] => {
  const all = hull(bs);
  const d = Math.trunc(Math.round((all.w - all.h) * 100) / 2) / 100;
  return bs.map((b) => {
    const to = isLine(b) ? { ...b, w: b.h, h: b.w, props: { ...b.props, from: NEXT[b.props.from ?? "nw"] } } : { ...b, angle: norm((b.angle ?? 0) + 90) };
    // As far from the left as the centre was from the bottom, and as far from the top as it was from the left.
    const x = all.x + d + (all.y + all.h - (b.y + lean(b) + b.h / 2));
    const y = all.y - d + (b.x - lean(b) + b.w / 2 - all.x);
    return { ...to, x: round(x - to.w / 2 + lean(to)), y: round(y - to.h / 2 - lean(to)) };
  });
};
// A line's start and end on the page.
const endsOf = (b: ShapeBlock) => [
  [b.x + (far(b, 1, false) ? b.w : 0), b.y + (far(b, 0, false) ? b.h : 0)],
  [b.x + (far(b, 1, true) ? b.w : 0), b.y + (far(b, 0, true) ? b.h : 0)],
];
// The box a thing lines up by: a line draws its stroke round its ends and an arrow head there (a double's at both),
// so its box takes them in. Any other block lines up by its outline.
export const inked = (b: Block): Box => {
  if (!isLine(b)) return outline(b);
  const [s, e] = endsOf(b);
  const [dx, dy] = [e[0] - s[0], e[1] - s[1]];
  const len = Math.hypot(dx, dy) || 1;
  const [u, p] = [[dx / len, dy / len], [-dy / len, dx / len]];
  const sw = b.props.strokeWidth ?? 0.5;
  const head = b.props.kind === "line" ? 0 : 2 + sw * 3;
  const at = ([x, y]: number[], along: number, across: number) => [x + u[0] * along + p[0] * across, y + u[1] * along + p[1] * across];
  const points = [
    at(s, 0, sw / 2), at(s, 0, -sw / 2), at(e, 0, sw / 2), at(e, 0, -sw / 2),
    at(e, -head, head / 2), at(e, -head, -head / 2),
    ...(b.props.kind === "double" ? [at(s, head, head / 2), at(s, head, -head / 2)] : []),
    // Ticks stand 1.5 mm to each side of the ends (`Line` in sheet.tsx draws them).
    ...(b.props.ticks ? [s, e].flatMap((end) => [at(end, 0, 1.5), at(end, 0, -1.5)]) : []),
  ];
  // The length stands 2 mm over the middle, on the side that reads upright: its em box, with a char at most 0.6 em.
  if (b.props.label) {
    const fs = 12 * PT;
    const half = (`${(Math.round(len * 10) / 100).toLocaleString("de")} cm`.length * 0.6 * fs) / 2;
    const side = u[0] < 0 ? -1 : 1;
    const mid = [(s[0] + e[0]) / 2, (s[1] + e[1]) / 2];
    for (const along of [-half, half]) for (const across of [-2 - 1.2 * fs, -2 + 0.35 * fs]) points.push(at(mid, along, side * across));
  }
  const [xs, ys] = [points.map(([x]) => x), points.map(([, y]) => y)];
  const [x, y] = [Math.min(...xs), Math.min(...ys)];
  return { ...b, x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
};
// The blocks turned as one by `by` degrees about the middle of the box around them, as the handle turns a
// selection and PowerPoint a group: each block's centre goes round, and its angle goes on. One block turns on its
// spot. Quarters are exact, and a line goes by them only. `about` is the point to turn about, when the caller
// remembers one; without it, and for quarters, the middle of the level box around the blocks.
export const swung = (bs: Block[], by: number, about?: [number, number]): Block[] => {
  if (!about && by % 90 === 0) return Array.from({ length: (((by / 90) % 4) + 4) % 4 }).reduce<Block[]>(quarter, bs);
  const [cx, cy] = about ?? ((all) => [all.x + all.w / 2, all.y + all.h / 2])(hull(bs));
  const [c, s] = dir({ angle: by });
  const turnAbout = ([x, y]: number[]) => [cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c];
  return bs.map((b) => {
    if (isLine(b)) {
      // A line has no angle: its two ends go round, and its box and start follow them.
      const [[px, py], [qx, qy]] = endsOf(b).map(turnAbout);
      const from = ((py <= qy ? "n" : "s") + (px <= qx ? "w" : "e")) as Corner;
      return { ...b, x: round(Math.min(px, qx)), y: round(Math.min(py, qy)), w: round(Math.abs(px - qx)), h: round(Math.abs(py - qy)), props: { ...b.props, from } };
    }
    const [x, y] = [b.x + b.w / 2 - cx, b.y + b.h / 2 - cy];
    return { ...b, x: round(cx + x * c - y * s - b.w / 2), y: round(cy + x * s + y * c - b.h / 2), angle: norm((b.angle ?? 0) + by) };
  });
};
// The blocks scaled about the point (ox, oy): each one's place and size go with the factors. A turned block keeps its
// centre's way from the point and its own axes: its width takes the factor of the axis it lies along.
export const scaled = (bs: Block[], sx: number, sy: number, [ox, oy]: [number, number]): Block[] =>
  bs.map((b) => {
    if (isLine(b) || !b.angle) return { ...b, x: round(ox + (b.x - ox) * sx), y: round(oy + (b.y - oy) * sy), w: round(b.w * sx), h: round(b.h * sy) };
    const [c, s] = dir(b).map(Math.abs);
    const [w, h] = c >= s ? [b.w * sx, b.h * sy] : [b.w * sy, b.h * sx];
    const [cx, cy] = [ox + (b.x + b.w / 2 - ox) * sx, oy + (b.y + b.h / 2 - oy) * sy];
    return { ...b, x: round(cx - w / 2), y: round(cy - h / 2), w: round(w), h: round(h) };
  });
// A group that is turned scales in its own frame: it goes level about its middle, scales there, and turns back, so
// a line in it still lies along the box. A group is turned when all its blocks but the lines share one angle; one with
// blocks turned each their own way scales along the page, each block by the axis it lies along.
// `at` is the point that stays, in the level frame: the level box's top left corner unless one is given.
export const scaledGroup = (bs: Block[], sx: number, sy: number, at?: [number, number]): Block[] => {
  const { turn, about, level } = frameOf(bs);
  const lb = bounds(level);
  const o = at ?? [lb.x, lb.y];
  return turn ? swung(scaled(level, sx, sy, o), turn, about) : scaled(bs, sx, sy, o);
};
// A group's own frame: its blocks laid level about its middle when it is turned, as they are when it is not.
export const frameOf = (bs: Block[]) => {
  const angles = new Set(bs.filter((b) => !isLine(b)).map((b) => b.angle ?? 0));
  const turn = angles.size === 1 ? [...angles][0] : 0;
  const all = hull(bs);
  const about: [number, number] = [all.x + all.w / 2, all.y + all.h / 2];
  return { turn, about, level: turn ? swung(bs, -turn, about) : bs };
};
// A block's new place and size. A line in a turned group may start at another corner after the scale: it takes that too.
export const sized = (b: Block): [string, Partial<Box>] => [b.id, { x: b.x, y: b.y, w: b.w, h: b.h, ...(isLine(b) && ({ props: b.props } as Partial<Box>)) }];
// A block that keeps its own shape: its lock, or a picture, a symbol and a Hunderterfeld.
const kept = (b: Block) => !!b.keep ||b.type === "image" || b.type === "symbol" || b.type === "hunderterfeld";
// The blocks mirrored as one, across for `x` and down for `y`, about the middle of the box around them: each goes
// to the other side, and the box stays. A picture, a symbol, a shape and a text in an outline are mirrored in
// themselves too, as the page shows them, and their angle with them. A line's start changes corners instead. A
// shape's text stays readable, and so does all else: in a group it moves and leans the other way, alone it stays.
export const mirrored = (bs: Block[], axis: Axis): Block[] => {
  const swap: Record<Corner, Corner> = axis === "x" ? { nw: "ne", ne: "nw", sw: "se", se: "sw" } : { nw: "sw", sw: "nw", ne: "se", se: "ne" };
  const [flag, size] = axis === "x" ? (["flipX", "w"] as const) : (["flipY", "h"] as const);
  const all = hull(bs);
  return bs.map((b) => {
    const own = b.type === "image" || b.type === "symbol" || b.type === "shape" || drawn(b);
    if (!own && bs.length === 1) return b;
    // As far from the far edge as it was from the near one. A block on its side leans the same way after.
    const at = { [axis]: round(2 * all[axis] + all[size] - b[axis] - b[size] + (axis === "x" ? 2 : -2) * lean(b)) };
    // `isLine` tells the compiler that every shape it turns down is no shape, so the type is read first.
    // An outline mirrors as a picture does; a box looks the same either way.
    const flips = own && (b.type !== "shape" || drawn(b));
    if (isLine(b)) return { ...b, ...at, props: { ...b.props, from: swap[b.props.from ?? "nw"] } };
    // A level block names no angle, and stays so.
    return { ...b, ...at, ...(b.angle && { angle: norm(-b.angle) }), ...(flips && { [flag]: !b[flag] }) };
  });
};

// Whether the words picked in the field have a look, or with no field every selected text: as in PowerPoint, a
// look goes on unless all have it. A text has it when all its words do, of their own or through the block; one
// with no words has what the block has.
// What a size typed on these blocks is remembered by: their places, sizes and angles.
const signature = (bs: Block[]) => JSON.stringify(bs.map((b) => [b.id, b.x, b.y, b.w, b.h, b.angle ?? 0]));

export const has = (sel: Block[], part: Picked | undefined, name: "bold" | "italic" | "underline") =>
  part
    ? !!part.marks[name]
    : sel.every((b) => {
        const text = boxed(b);
        if (!text) return true;
        const runs = parasOf(text).flatMap((p) => p.runs);
        return runs.length ? runs.every((r) => r[name] ?? text[name]) : !!text[name];
      });

// Whether a text or a shape has a frame drawn as an outline, which a flip mirrors.
export const drawn = (b: Block) => (b.type === "shape" || b.type === "text") && ["triangle", "star", "bubble"].includes(b.props.kind ?? "rect");

// The one size that the lines from `from` to `to` share, or undefined where they differ by more than 0.005 mm.
const alike = (sizes: number[], from: number, to: number) => {
  const picked = sizes.slice(from, to + 1);
  return picked.every((s) => Math.abs(s - picked[0]) <= 0.005) ? picked[0] : undefined;
};

// The width and height in mm that the panel shows: the open cell's own, or the picked cells' shared sizes.
function sizeFields(t: TableBlock, cell: number, reach: number | undefined, laid: number[]): { width?: number; height?: number } {
  const [r, c, h, w] = spanAt(t.props, cell);
  const [r0, c0, r1, c1]: Rect = reach === undefined ? [r, c, r + h - 1, c + w - 1] : rectOf(t.props, cell, reach);
  const widths = widthsOf(t.props.cols, t.w);
  const width = reach === undefined ? sum(widths.slice(c0, c1 + 1)) : alike(widths, c0, c1);
  const height = !laid.length ? undefined : reach === undefined ? sum(laid.slice(r0, r1 + 1)) : alike(laid, r0, r1);
  return { width, height };
}

// The border buttons of the panel, each with the border it draws.
const BORDERS: [Border, string][] = [
  ["all", "Alle"],
  ["inner", "Innen"],
  ["outer", "Außen"],
  ["top", "Oben"],
  ["bottom", "Unten"],
  ["left", "Links"],
  ["right", "Rechts"],
  ["across", "Innen waagerecht"],
  ["down", "Innen senkrecht"],
];

export default function Format({ sel, style, bump, look, mendWord, traced, link, feed, paint, itemize, gap, every, part, place, rank, cell, reach, merge, unmerge, laid, full, cramped, held, onSize, sizeCells, evenCells, lines, cutting, border, crop, cropping, spin, mirror, alone, lock, setLock, from, setFrom, size: [W, H], doc, words, lineaturen, list, toList, owe }: Props) {
  // A locked block neither turns nor flips. A table stays level, a line turns by its ends, and only a picture, a
  // symbol, a shape or a text in an outline can flip. A group picked whole goes as one: a line in it goes round
  // with it by quarters, and whatever is in it changes sides in a flip.
  // The line style and width that a border button or the pen draws with while a cell is open. It starts at the table's.
  const [pen, setPen] = useState<Pen>({ style: "solid", width: 0.25 });
  // The size last typed for a group, with the blocks it was typed on: the frame may not land on it.
  const [typed, setTyped] = useState<{ sig: string; w?: number; h?: number }>();
  const fixed = sel.some((b) => b.locked);
  const level = fixed || sel.some((b) => b.type === "table" || (isLine(b) && alone(b)));
  const plain = fixed || !sel.some((b) => !alone(b) || b.type === "image" || b.type === "symbol" || b.type === "shape" || drawn(b));
  const of = <T extends Block["type"]>(type: T) => sel.filter((b): b is Extract<Block, { type: T }> => b.type === type);
  // The first block of a type shows its settings; a change goes to all of them.
  // A shape that is no line holds text as a text block does.
  const text = sel.map(boxed).find((p) => p);
  // Picked words show their own look, and the list is that of the caret's paragraph, or of the text's first.
  const shown = { ...text, ...part?.marks };
  const kind = text && (part ?? parasOf(text)[0]).list;
  const rulings = of("ruling");
  // The mode the Lineaturen take the Lernwörter in, when every picked one takes them; else none.
  const mode = rulings.length > 0 && rulings.every((b) => listOf(b)) ? listOf(rulings[0]) : undefined;
  // How many words of the list the most crowded Lineatur cannot show.
  const n = unshown(rulings, words, lineaturen);
  const tables = of("table");
  // The pen starts at the first table's lines each time a cell opens.
  const open = cell !== undefined;
  useEffect(() => {
    if (tables[0]) setPen({ style: tables[0].props.lineStyle ?? "solid", width: tables[0].props.lineWidth ?? 0.25 });
  }, [open]);
  // What the line controls show: the table's own lines with no cell open, else the pen.
  const lineShown: Pen = !open && tables[0] ? { style: tables[0].props.lineStyle ?? "solid", width: tables[0].props.lineWidth ?? 0.25 } : pen;
  // The border buttons draw on the open cell's rect (or the cells picked with it), or on the whole table with no cell open.
  // A rect of one cell or of one merged cell has no inner line, and one row or one column has no line across or down.
  const grid = tables[0]?.props;
  let rect: Rect = [0, 0, 0, 0];
  if (grid && cell === undefined) rect = [0, 0, grid.cells.length - 1, grid.cols.length - 1];
  else if (grid && cell !== undefined) {
    if (reach === undefined) {
      const [r, c, h, w] = spanAt(grid, cell);
      rect = [r, c, r + h - 1, c + w - 1];
    } else rect = rectOf(grid, cell, reach);
  }
  const [r0, c0, r1, c1] = rect;
  const first = grid ? spanAt(grid, r0 * grid.cols.length + c0) : undefined;
  const single = !!first && first[0] === r0 && first[1] === c0 && first[2] === r1 - r0 + 1 && first[3] === c1 - c0 + 1;
  const off = (which: Border) => (which === "across" ? single || r0 === r1 : which === "down" ? single || c0 === c1 : which === "inner" && (single || r0 === r1 || c0 === c1));
  const texts = of("text");
  // The line numbers are on unless all the texts have them, as bold: a step of 1 to 100 counts as having them.
  const numbered = texts.length > 0 && texts.every((b) => stepOf(b.props.lines) > 0);
  // The number of the first line, or none where the picked texts differ.
  const starts = texts.map((b) => fromOf(b.props.linesFrom));
  const start = starts.every((s) => s === starts[0]) ? starts[0] : undefined;
  const [points] = of("points");
  const [sign] = of("symbol");
  // The generator's limits belong to one block.
  const maths = sel.length === 1 && sel[0].type === "maths" ? sel[0] : undefined;
  const suchsel = sel.length === 1 && sel[0].type === "suchsel" ? sel[0] : undefined;
  // A maths drawing that would grow past the paper's edge keeps its props, and the panel says why (#911).
  // The change refused, the block it was for, and that block's props and height at the refusal: the hint stays while the block is as it was (#911).
  const [denied, setDenied] = useState<{ id: string; props: object; from: string }>();
  useEffect(() => setDenied(undefined), [sel.map((b) => b.id).join()]);
  const sig = (b: Block) => JSON.stringify([b.props, b.y]);
  const picked = (id: string, props?: object) => {
    const b = sel.find((x) => x.id === id);
    return b && props ? ({ ...b, props: { ...b.props, ...props } } as Block) : b;
  };
  // `back` puts a number back that was stored before, with the height the block had then, so no check refuses it.
  // Returns false when the change is refused.
  const grows = (type: Block["type"], props: object, key?: string, back?: number): boolean => {
    if (back !== undefined) {
      const b = sel.find((x) => x.type === type)!;
      style(type, props, key);
      place([[b.id, tall(b, back)]], key);
      setDenied((d) => d && { ...d, from: sig(picked(d.id, props)!) });
      return true;
    }
    const off = sel.filter((b) => b.type === type).find((b) => pastPaper(b, { ...b, props: { ...b.props, ...props } } as Block, H));
    if (off) setDenied({ id: off.id, props, from: sig(off) });
    else {
      setDenied(undefined);
      style(type, props, key);
    }
    return !off;
  };
  const refusedBlock = denied && picked(denied.id);
  const paperHint = !!denied && !!refusedBlock && sig(refusedBlock) === denied.from && pastPaper(refusedBlock, { ...refusedBlock, props: { ...refusedBlock.props, ...denied.props } } as Block, H);
  const wall = sel.length === 1 && sel[0].type === "zahlenmauer" ? sel[0] : undefined;
  const haus = sel.length === 1 && sel[0].type === "zahlenhaus" ? sel[0] : undefined;
  const dreieck = sel.length === 1 && sel[0].type === "rechendreieck" ? sel[0] : undefined;
  const strahl = sel.length === 1 && sel[0].type === "zahlenstrahl" ? sel[0] : undefined;
  const feld = sel.length === 1 && sel[0].type === "hunderterfeld" ? sel[0] : undefined;
  const uhr = sel.length === 1 && sel[0].type === "uhr" ? sel[0] : undefined;
  const skb = sel.length === 1 && sel[0].type === "selbstkontrolle" ? sel[0] : undefined;
  const { mark } = sel[0];
  // The Silbenbögen and the Silbenfarbe stand once, with the text settings or else with the table's, and go to all
  // that hold words. What is mended by hand belongs to one block: another pick starts anew.
  const bows = <Syllables key={sel.find(syllabled)?.id} sel={sel} part={part} look={look} style={style} mendWord={mendWord} doc={doc} words={words} />;
  const gaps = <Gaps key={`gaps-${sel.find(worded)?.id}`}sel={sel} part={part} cell={cell} look={look} style={style} gap={gap} every={every} />;

  // A ruling keeps its rows when its type changes, and grows to the rows its text needs, up to the foot of the page.
  // A kind change keeps its rows and takes rows away only where the page foot cuts them short; the buttons give the rows themselves.
  const rule = (kind: Ruling, rows?: number) => {
    style("ruling", { kind }, "ruling");
    const row = RULINGS[kindOf(kind)].row;
    place(
      rulings.map((b) => {
        if (rows !== undefined) return [b.id, tall(b, round(Math.max(1, rows) * row))];
        const next = { ...b, props: { ...b.props, kind } };
        // Past the foot it keeps the rows that still fit, measured by its lowest corner, so a turned one as it lies.
        let n = Math.max(rowsOf(b), rowsNeeded(next));
        while (n > 1 && lowest({ ...b, ...tall(b, round(n * row)) }) > H - MARGIN + 0.01) n--;
        return [b.id, tall(b, round(Math.max(1, n) * row))];
      }),
      "ruling",
    );
  };
  // A ruling fills the room between the margins along the way it lies: both ends go out from its centre until a
  // corner would cross a margin. A slanted one stays as it is when it lies past a margin along its way and has
  // less room there than it is high.
  const wide = (b: RulingBlock): Partial<Box> => {
    const [c, s] = dir(b);
    // The middle of each long edge.
    const mids = [-1, 1].map((side) => [b.x + (b.w - side * b.h * s) / 2, b.y + (b.h + side * b.h * c) / 2]);
    const [back, on] = [-1, 1].map((way) => Math.min(...mids.flatMap(([x, y]) => [room(x, way * c, W), room(y, way * s, H)])));
    // Rounded down, so that no corner crosses.
    const w = Math.floor((back + on) * 100 + 1e-6) / 100;
    // A slanted one that fills the room to a hair stays too: its place is rounded, so a second press would find
    // a little room again, and the more of it the closer the block lies to level or upright. So its place is
    // rounded finer, to keep that hair thin.
    const hair = 0.02 + 0.0001 / Math.min(Math.abs(c), Math.abs(s));
    const slanted = Math.abs(c * s) > 1e-9;
    const fine = (n: number) => (slanted ? Math.round(n * 1e4) / 1e4 : round(n));
    if (!(w > 0 && w < Infinity) || (slanted && (((back < 0 || on < 0) && w < b.h) || [back, on].every((end) => Math.abs(end - b.w / 2) < hair)))) return {};
    // A level block keeps its y as it is.
    return { w, x: fine(b.x + (b.w - w + (on - back) * c) / 2), ...(Math.abs(s) > 1e-9 && { y: fine(b.y + ((on - back) * s) / 2) }) };
  };
  // A maths block's height follows its exercises when they need more or less room than before. A change that would
  // push it past the page's foot is refused: the PDF would cut what hangs below.
  // `key` makes the style and the height one undo step.
  const calc = (props: MathsProps, key = "maths") => {
    if (overFoot(maths!, props, H)) return false;
    style("maths", props, key);
    if (mathsHeight(props) !== mathsHeight(maths!.props)) place([[maths!.id, tall(maths!, mathsHeight(props))]], key);
    return true;
  };
  const number = (to?: string) => place(sel.map((b) => [b.id, { mark: to }]));

  // The fields for place, size and angle, as in PowerPoint's size pane. A field shows what all the blocks share.
  // A selection with a group in it is one thing: it shows the box around it, which only moves.
  const whole = sel.some((b) => b.group);
  const box = bounds(sel);
  // Its width and height are those of its own frame, the box it has at 0 degrees, as in PowerPoint.
  const own = whole ? bounds(frameOf(sel).level) : box;
  // What the panel shows for a group's side: what was typed, while the group is as it was left, else its frame.
  const shownOwn = (side: "w" | "h") => (typed && typed.sig === signature(sel) && typed[side] !== undefined ? typed[side] : round(own[side]));
  const shared = (of: (b: Block) => number) => (whole ? undefined : sel.every((b) => of(b) === of(sel[0])) ? of(sel[0]) : undefined);
  // A picture, a symbol and a Hunderterfeld always keep their shape.
  const shaped = sel.some((b) => b.type === "image" || b.type === "symbol" || b.type === "hunderterfeld");
  const keep = lock || shaped;
  const move = (axis: Axis, to: number) => place(sel.map((b) => [b.id, { [axis]: whole ? round(b[axis] + to - box[axis]) : to }]));
  // The distance from the page's corner to where X and Y count from: nothing, or half the page in Mitte.
  const offset = (axis: "x" | "y") => (from === "centre" ? (axis === "x" ? W : H) / 2 : 0);
  const shownAt = (axis: "x" | "y", v?: number) => (v === undefined ? undefined : round(v - offset(axis)));
  // The corner stays. A group scales about its top left corner, and with the lock all of it keeps its shape.
  // Loose blocks each keep their own shape.
  // A group scaled once by `f` on its sides; the field then shows what was typed, as the frame may not land on it.
  // `to` is the value of `side` the field shows after; the other side shows its own value, scaled when both scale.
  const scaleWhole = (side: "w" | "h", f: number, to: number) => {
    const both = lock || sel.some(kept);
    const out = scaledGroup(sel, ...(side === "w" ? [f, both ? f : 1] : [both ? f : 1, f]) as [number, number]);
    const other = side === "w" ? "h" : "w";
    const rest = both ? round(shownOwn(other) * f) : shownOwn(other);
    setTyped({ sig: signature(out), ...(side === "w" ? { w: to, h: rest } : { w: rest, h: to }) });
    place(out.map(sized));
  };
  const resize = (side: "w" | "h", to: number) => {
    const other = side === "w" ? "h" : "w";
    // A group of flat lines has no height to scale from.
    if (to <= 0 || (whole && own[side] <= 0)) return;
    onSize(sel.map((b) => b.id));
    if (whole) {
      scaleWhole(side, to / shownOwn(side), to);
      return;
    }
    place(sel.map((b) => [b.id, { [side]: to, ...(kept(b) && b[side] > 0 && { [other]: round((b[other] * to) / b[side]) }) }]));
  };
  // A percent scales the box from its top left corner, or about the group's; a loose block keeps its own shape when it is kept.
  const percent = (side: "w" | "h", p: number) => {
    if (!(p > 0)) return;
    onSize(sel.map((b) => b.id));
    const f = p / 100;
    // The side named scales; the other too when the shape is kept.
    const factors = (both: boolean): [number, number] => (side === "w" ? [f, both ? f : 1] : [both ? f : 1, f]);
    if (whole) {
      scaleWhole(side, f, shownOwn(side) * f);
      return;
    }
    // A loose block scales its own width and height, as its Breite and Höhe do, also when it is turned.
    const out = sel.map((b) => (([sx, sy]) => ({ ...b, w: round(b.w * sx), h: round(b.h * sy) }))(factors(kept(b))));
    place(out.map(sized));
  };
  // A picture goes back to the size it had when it came in, as the editor sets a new one: uncropped, cut
  // shares taken off, its place kept.
  const [only] = sel;
  const pic = sel.length === 1 && only.type === "image" ? only : undefined;
  const original = () => {
    if (!pic) return;
    const { ratio, cut } = pic.props;
    const w0 = Math.min(100, 100 * ratio);
    place([[pic.id, { w: round(w0 * (1 - cut[0] - cut[2])), h: round((w0 / ratio) * (1 - cut[1] - cut[3])) }]]);
  };
  const turned = sel.find((b) => !isLine(b));
  const angle = whole ? turned?.angle ?? 0 : shared((b) => b.angle ?? 0);
  const turn = (to: number) => norm(to) !== angle && (whole ? spin(norm(to) - (angle ?? 0)) : place(sel.map((b) => [b.id, { angle: norm(to) }])));

  // A picked Lineatur that lies over a block with text, outside its group, covers that text: nothing moves, so the panel says so.
  const page = doc.pages.find((p) => p.blocks.some((b) => b.id === sel[0]?.id))?.blocks ?? [];
  const carries = (b: Block) => b.type === "table" || b.type === "maths" || b.type === "ruling" || !!boxed(b)?.text;
  const covers = rulings.some((r) =>
    page.some(
      (b) =>
        b.id !== r.id &&
        carries(b) &&
        !b.group?.some((g) => r.group?.includes(g)) &&
        r.x < b.x + b.w && b.x < r.x + r.w && r.y < b.y + b.h && b.y < r.y + r.h,
    ),
  );
  // A picked Zahlenmauer that grows over another block, outside its group, covers it: nothing moves, as for a
  // Lineatur. A shape without text does not count, being a frame or a mark.
  const wallCovers = sel.some(
    (z) =>
      z.type === "zahlenmauer" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );

  const houseCovers = sel.some(
    (z) =>
      z.type === "zahlenhaus" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );

  return (
    <>
      {/* A block that hangs over the foot is cut in the PDF: the panel says so first, whatever the block. */}
      {sel.some((b) => lowest(b) > H + 0.01) && (
        <p className="hint warn" role="status" data-foot="over">
          {sel.length > 1 ? "Die Auswahl ragt unten über die Seite hinaus." : "Der Block ragt unten über die Seite hinaus."} Was unter dem Rand steht, wird nicht gedruckt.
        </p>
      )}
      {/* A maths block past the margin's foot says so, where the PDF still prints it whole up to the paper's edge. */}
      {(() => {
        const first = sel.find((b) => FOOT[b.type] && lowest(b) > H - MARGIN + 0.01);
        return first && !sel.some((b) => lowest(b) > H + 0.01) ? (
          <p className="hint warn" role="status" data-foot="haus">
            {FOOT[first.type].join(" ")}
          </p>
        ) : null;
      })()}
      {paperHint && refusedBlock && (
        <p className="hint warn" role="status" data-foot="paper">
          Das passt nicht mehr auf die Seite und wurde nicht übernommen. {FOOT[refusedBlock.type][1]}
        </p>
      )}
      {/* A text that the foot stops from growing says that its last words are cut. */}
      {sel.some((b) => full.includes(b.id)) && (
        <p className="hint warn" role="status" data-foot="full">
          Der Text passt nicht mehr in den Block: er reicht bis an den unteren Rand der Seite. Was nicht hineinpasst, wird nicht gedruckt.
        </p>
      )}
      {/* A shape whose text does not fit where it stands says so, at any place on the page. */}
      {sel.some((b) => cramped.includes(b.id) && !full.includes(b.id)) && (
        <p className="hint warn" role="status" data-shape="full">
          Der Text passt nicht in die Form. Was nicht hineinpasst, wird nicht gedruckt.
        </p>
      )}
      {rulings.some((b) => rowsNeeded(b) > rowsOf(b)) && (
        <p className="hint warn" role="status" data-rows="short">
          Der Text braucht mehr Zeilen, als die Lineatur hat. Was nicht hineinpasst, wird nicht gedruckt.
        </p>
      )}
      {covers && (
        <p className="hint warn" role="status" data-cover="over">
          Die Lineatur liegt über einem anderen Block. Verschiebe ihn oder mache die Lineatur kleiner.
        </p>
      )}
      {wallCovers && (
        <p className="hint warn" role="status" data-cover="wall">
          Die Zahlenmauer liegt über einem anderen Block. Verschiebe ihn oder mache die Zahlenmauer kleiner.
        </p>
      )}
      {houseCovers && (
        <p className="hint warn" role="status" data-cover="haus">
          Das Zahlenhaus liegt über einem anderen Block. Verschiebe ihn oder mache das Zahlenhaus kleiner.
        </p>
      )}
      {/* A shape that a smaller size made, and whose text grew it back, says why it stays as tall as its text. */}
      {sel.some((b) => held.includes(b.id)) && (
        <p className="hint" role="status" data-held="text">
          Der Text braucht diese Höhe. Mit kleinerer Schrift oder kürzerem Text lässt sich die Form kleiner stellen.
        </p>
      )}
      {/* A table that a new column made wider than the page is cut too, at the right edge. */}
      {sel.some((b) => b.type === "table" && rightmost(b) > W + 0.01) && (
        <p className="hint warn" role="status" data-edge="over">
          Die Tabelle ragt rechts über die Seite hinaus. Was neben dem Rand steht, wird nicht gedruckt.
        </p>
      )}
      <div className="geo">
        <h2>Position und Größe in mm</h2>
        <label>
          von
          <select aria-label="von" value={from} onChange={(e) => setFrom(e.target.value as "corner" | "centre")}>
            <option value="corner">Ecke oben links</option>
            <option value="centre">Mitte</option>
          </select>
        </label>
        <span />
        {/* In Mitte the place counts from the page's centre: a block at 15 mm shows -90 in a page 210 mm wide. */}
        <Num label="X" units value={shownAt("x", whole ? box.x : shared((b) => b.x))} disabled={fixed} onCommit={(n) => move("x", n + offset("x"))} />
        <Num label="Y" units value={shownAt("y", whole ? box.y : shared((b) => b.y))} disabled={fixed} onCommit={(n) => move("y", n + offset("y"))} />
        <Num label="Breite" units value={whole ? shownOwn("w") : shared((b) => b.w)} disabled={fixed || sel.some((b) => isLine(b) && alone(b))} onCommit={(n) => resize("w", n)} />
        <Num label="Höhe" units value={whole ? shownOwn("h") : shared((b) => b.h)} disabled={fixed || sel.some((b) => isLine(b) && alone(b))} onCommit={(n) => resize("h", n)} />
        <Num label="Drehung" value={angle} disabled={level} onCommit={turn} />
        <span>
          °
          <button className={keep ? "ib on" : "ib"} aria-label="Seitenverhältnis sperren" title="Seitenverhältnis sperren" aria-pressed={keep} disabled={fixed || shaped} onClick={() => setLock(!lock)}>
            {keep ? <Lock size={14} aria-hidden /> : <LockOpen size={14} aria-hidden />}
          </button>
        </span>
        {/* A percent always reads 100: it scales the selection once and shows 100 again. */}
        <Num label="Breite %" value={100} disabled={fixed} onCommit={(p) => percent("w", p)} />
        <Num label="Höhe %" value={100} disabled={fixed} onCommit={(p) => percent("h", p)} />
        {pic && (
          <button aria-label="Originalgröße" title="Originalgröße" disabled={fixed} onClick={original}>
            Originalgröße
          </button>
        )}
      </div>
      {text && (
        <>
          <h2>Schrift</h2>
          <FontSelect label="Schriftart" value={fontOf(text.font)} unknown={unknownFont(sel.map((b) => boxed(b)?.font))} onChange={(font) => look({ font })} />
          <div className="seg">
            <button aria-label="Schrift kleiner" onClick={() => look({ size: Math.max(8, text.size - 2) })}>−</button>
            <output>{text.size} pt</output>
            <button aria-label="Schrift größer" onClick={() => look({ size: text.size + 2 })}>＋</button>
          </div>
          <div className="seg">
            {([["bold", "Fett"], ["italic", "Kursiv"], ["underline", "Unterstrichen"]] as const).map(([prop, label]) => (
              <button key={prop} className={`${prop}${has(sel, part, prop) ? " on" : ""}`} aria-label={label} aria-pressed={has(sel, part, prop)} onClick={() => paint({ [prop]: !has(sel, part, prop) })}>
                {label[0]}
              </button>
            ))}
          </div>
          <div className="seg">
            {LISTS.map(([value, label, Icon]) => (
              <button key={value} className={kind === value ? "on" : ""} aria-label={label} title={label} aria-pressed={kind === value} onClick={() => itemize(value)}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg">
            {ALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={text.align === value ? "on" : ""} aria-label={label} title={label} aria-pressed={text.align === value} onClick={() => look({ align: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg">
            {VALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={(text.valign ?? "top") === value ? "on" : ""} aria-label={label} title={label} aria-pressed={(text.valign ?? "top") === value} onClick={() => look({ valign: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={shown.color ?? "#222222"} onChange={(e) => paint({ color: e.target.value }, "color")} />
          </label>
          <label>
            Zeilenabstand
            <input type="range" min={1} max={3} step={0.1} value={text.spacing ?? 1.3} onChange={(e) => look({ spacing: +e.target.value }, "spacing")} />
          </label>
          <TraceControls props={text} font={text.font} onChange={traced} />
          {bows}
          {gaps}
          <Fed sel={sel} words={words} toList={toList} look={look} link={link} feed={feed} />
          <Mix sel={sel} look={look} words={words} />
          {/* Only texts take line numbers. Off is no key, as on a text that never had them; on starts with every fifth line. */}
          {texts.length > 0 && (
            <>
              <button className={numbered ? "on" : ""} aria-pressed={numbered} onClick={() => style("text", { lines: numbered ? undefined : 5 }, "lines")}>
                Zeilennummern
              </button>
              {numbered && (
                <div className="seg">
                  <button className={stepOf(texts[0].props.lines) === 1 ? "on" : ""} aria-pressed={stepOf(texts[0].props.lines) === 1} onClick={() => style("text", { lines: 1 }, "lines")}>
                    Jede Zeile
                  </button>
                  <button className={stepOf(texts[0].props.lines) === 5 ? "on" : ""} aria-pressed={stepOf(texts[0].props.lines) === 5} onClick={() => style("text", { lines: 5 }, "lines")}>
                    Jede 5. Zeile
                  </button>
                </div>
              )}
              {numbered && (
                <Num label="Beginnt bei" value={start} disabled={false} onCommit={(n) => Number.isInteger(n) && n >= 1 && n <= 9999 && style("text", { linesFrom: n === 1 ? undefined : n }, "linesFrom")} />
              )}
            </>
          )}
        </>
      )}
      {rulings.length > 0 && (
        <>
          <h2>Lineatur</h2>
          <select aria-label="Art der Lineatur" value={kindOf(rulings[0].props.kind)} onChange={(e) => rule(e.target.value as Ruling)}>
            {Object.entries(RULINGS).map(([kind, { name }]) => (
              <option key={kind} value={kind}>
                {name}
              </option>
            ))}
          </select>
          <div className="seg">
            <button aria-label="Eine Zeile weniger" disabled={fixed} onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) - 1)}>−</button>
            <output>{rowsOf(rulings[0]) === 1 ? "1 Zeile" : `${rowsOf(rulings[0])} Zeilen`}</output>
            <button aria-label="Eine Zeile mehr" disabled={fixed} onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) + 1)}>＋</button>
          </div>
          <label>
            Farbe
            <input type="color" value={rulings[0].props.color} onChange={(e) => style("ruling", { color: e.target.value }, "color")} />
          </label>
          {/* The house and the band: only the kinds with zones have them. A press is one undo step, and a drag over the colour is one. */}
          {RULINGS[kindOf(rulings[0].props.kind)].zones && (
            <>
              <button className={houseOf(rulings[0]) ? "on" : ""} aria-pressed={houseOf(rulings[0])} onClick={() => style("ruling", { house: !houseOf(rulings[0]) })}>Häuschen</button>
              {houseOf(rulings[0]) && (
                <select aria-label="Häuschen einfärben" value={houseTintOf(rulings[0]) ?? "none"} onChange={(e) => style("ruling", { houseTint: e.target.value === "none" ? undefined : e.target.value })}>
                  <option value="none">Nicht eingefärbt</option>
                  <option value="room">Zimmer eingefärbt</option>
                  <option value="all">Dach, Zimmer und Keller eingefärbt</option>
                </select>
              )}
              <button className={bandOf(rulings[0]) ? "on" : ""} aria-pressed={bandOf(rulings[0])} onClick={() => style("ruling", { band: !bandOf(rulings[0]) })}>Mittelband einfärben</button>
              {bandOf(rulings[0]) && (
                <label>
                  Farbe des Mittelbands
                  <input type="color" value={bandColorOf(rulings[0]) ?? shade(rulings[0].props.color)} onChange={(e) => style("ruling", { bandColor: e.target.value }, "bandColor")} />
                </label>
              )}
            </>
          )}
          <div className="row">
            <button disabled={fixed} onClick={() => place(rulings.map((b) => [b.id, wide(b)]))}>Seitenbreite</button>
            <button disabled={fixed} onClick={() => place(rulings.map((b) => [b.id, filled(b, W, H)]))}>Bis Seitenende</button>
          </div>
          {/* The text of a Lineatur: its own, or the sheet's Lernwörter in one of three modes. A mode shows only when
              every picked Lineatur has it. */}
          <select aria-label="Text der Lineatur" value={mode ?? "own"} onChange={(e) => list(e.target.value === "own" ? undefined : (e.target.value as ListMode))}>
            <option value="own">Eigener Text</option>
            <option value="copy">Lernwörter abschreiben</option>
            <option value="trace">Lernwörter nachspuren</option>
            <option value="row">Lernwörter, ganze Zeile nachspuren</option>
            <option value="fold">Lernwörter als Knickblatt</option>
          </select>
          {mode === "fold" && (
            <div className="seg">
              {[2, 3].map((n) => (
                <button key={n} className={foldsOf(rulings[0]) === n ? "on" : ""} aria-label={`${n} Spalten zum Schreiben`} aria-pressed={foldsOf(rulings[0]) === n} onClick={() => style("ruling", { folds: n }, "folds")}>
                  {n}
                </button>
              ))}
            </div>
          )}
          {n > 0 && (
            <p className="hint" role="status">
              {n === 1 ? "1 Wort passt nicht in die Zeilen." : `${n} Wörter passen nicht in die Zeilen.`}
            </p>
          )}
          {mode && <button onClick={toList}>Lernwörter bearbeiten</button>}
          {!mode && <p className="hint">Lineatur anklicken und lostippen, um auf die Zeilen zu schreiben.</p>}
          {RULINGS[kindOf(rulings[0].props.kind)].at && (
            <FontSelect label="Schriftart auf den Zeilen" value={fontOf(rulings[0].props.font)} unknown={unknownFont(rulings.map((b) => b.props.font))} onChange={(font) => style("ruling", { font })} />
          )}
          {!mode && (
            <TraceControls props={rulings[0].props} font={RULINGS[kindOf(rulings[0].props.kind)].at ? fontOf(rulings[0].props.font) : "andika"} onChange={traced} />
          )}
          {!text && !tables.length && bows}
        </>
      )}
      {tables.length > 0 && (
        <>
          <h2>Tabelle</h2>
          {/* More or fewer rows and columns, for one table: each has cells of its own. They come and go at the end,
              or beside the cell being edited, as in PowerPoint. */}
          {tables.length === 1 &&
            (["Zeile", "Spalte"] as const).map((name, i) => {
              const axis = i ? "col" : "row";
              const n = [tables[0].props.cells.length, tables[0].props.cols.length];
              if (cell === undefined)
                return (
                  <div key={name} className="seg">
                    <button aria-label={`Eine ${name} weniger`} disabled={fixed} onClick={() => rank(tables[0], axis, n[i] - 1, false)}>−</button>
                    <output>{n[i] === 1 ? `1 ${name}` : `${n[i]} ${name}n`}</output>
                    <button aria-label={`Eine ${name} mehr`} disabled={fixed} onClick={() => rank(tables[0], axis, n[i], true)}>＋</button>
                  </div>
                );
              const [r, c, h, w] = spanAt(tables[0].props, cell);
              const at = i ? c : r;
              const after = i ? c + w : r + h;
              return (
                <div key={name} className="acts">
                  <button onClick={() => rank(tables[0], axis, at, true)}>{name} {i ? "links" : "darüber"}</button>
                  <button onClick={() => rank(tables[0], axis, after, true, true)}>{name} {i ? "rechts" : "darunter"}</button>
                </div>
              );
            })}
          {/* The last row or column stays. A disabled button would take the focus from the cell. */}
          {tables.length === 1 && cell !== undefined && (
            <div className="acts">
              <button aria-disabled={tables[0].props.cells.length < 2} onClick={() => rank(tables[0], "row", spanAt(tables[0].props, cell)[0], false)}>Zeile löschen</button>
              <button aria-disabled={tables[0].props.cols.length < 2} onClick={() => rank(tables[0], "col", spanAt(tables[0].props, cell)[1], false)}>Spalte löschen</button>
            </div>
          )}
          {tables.length === 1 && cell !== undefined && (
            <div className="acts">
              <button aria-disabled={reach === undefined} onClick={() => reach !== undefined && merge()}>Zellen verbinden</button>
              <button aria-disabled={!(spanAt(tables[0].props, cell)[2] * spanAt(tables[0].props, cell)[3] > 1)} onClick={() => spanAt(tables[0].props, cell)[2] * spanAt(tables[0].props, cell)[3] > 1 && unmerge()}>Zellen teilen</button>
            </div>
          )}
          {tables.length === 1 && cell !== undefined && (
            <>
              <Num label="Spaltenbreite" value={sizeFields(tables[0], cell, reach, laid).width} disabled={fixed} onCommit={(n) => n > 0 && sizeCells("col", n)} />
              <Num label="Zeilenhöhe" value={sizeFields(tables[0], cell, reach, laid).height} disabled={fixed} onCommit={(n) => n > 0 && sizeCells("row", n)} />
              <div className="acts">
                <button disabled={fixed} onClick={() => evenCells("col")}>Spalten gleichmäßig verteilen</button>
                <button disabled={fixed} onClick={() => evenCells("row")}>Zeilen gleichmäßig verteilen</button>
              </div>
            </>
          )}
          <FontSelect label="Schriftart der Tabelle" value={fontOf(tables[0].props.font)} unknown={unknownFont(tables.map((b) => b.props.font))} onChange={(font) => style("table", { font })} />
          <div className="seg">
            <button aria-label="Schrift kleiner" onClick={() => style("table", { size: Math.max(8, tables[0].props.size - 2) })}>−</button>
            <output>{tables[0].props.size} pt</output>
            <button aria-label="Schrift größer" onClick={() => style("table", { size: tables[0].props.size + 2 })}>＋</button>
          </div>
          <div className="seg">
            {ALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={tables[0].props.align === value ? "on" : ""} aria-label={label} title={label} aria-pressed={tables[0].props.align === value} onClick={() => style("table", { align: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={tables[0].props.color ?? "#222222"} onChange={(e) => style("table", { color: e.target.value }, "color")} />
          </label>
          <label>
            Linien
            <input type="color" value={tables[0].props.line} onChange={(e) => style("table", { line: e.target.value }, "line")} />
          </label>
          <label>
            Linienart
            <select
              aria-label="Linienart"
              value={lineShown.style}
              onChange={(e) => (open ? setPen({ ...pen, style: e.target.value as LineStyle }) : lines({ style: e.target.value as LineStyle }))}
            >
              <option value="solid">Durchgezogen</option>
              <option value="dashed">Gestrichelt</option>
              <option value="dotted">Gepunktet</option>
              <option value="none">Keine</option>
            </select>
          </label>
          <label>
            Linienstärke
            <input
              type="range"
              min={0.25}
              max={3}
              step={0.25}
              value={lineShown.width}
              onChange={(e) => (open ? setPen({ ...pen, width: +e.target.value }) : lines({ width: +e.target.value }, "lineWidth"))}
            />
          </label>
          <output>{lineShown.width.toFixed(2).replace(".", ",")} mm</output>
          {border && (
            <div role="group" aria-label="Rahmen" className="borders">
              {BORDERS.map(([which, label]) => (
                <button key={which} aria-disabled={off(which)} onClick={() => !off(which) && border(which, lineShown)}>
                  {label}
                </button>
              ))}
            </div>
          )}
          <button className={tables[0].props.cut ? "wide on" : "wide"} aria-pressed={!!tables[0].props.cut} onClick={() => cutting(!tables[0].props.cut)}>
            <Scissors size={14} aria-hidden />
            Schneidelinien
          </button>
          <button className={tables[0].props.head ? "on" : ""} aria-pressed={!!tables[0].props.head} onClick={() => style("table", { head: !tables[0].props.head })}>
            Kopfzeile
          </button>
          <TraceControls props={tables[0].props} font={tables[0].props.font} onChange={traced} />
          {!text && bows}
          {!text && gaps}
          <p className="hint">Doppelklick auf eine Zelle, um hineinzuschreiben.</p>
        </>
      )}
      {maths && <Maths key={maths.id} block={maths} apply={calc} foot={H} owe={owe} />}
      {suchsel && <Suchsel key={suchsel.id} block={suchsel} words={words} apply={(props, key) => style("suchsel", props, key)} />}
      {wall && <Zahlenmauer key={wall.id} block={wall} apply={(props, key) => grows("zahlenmauer", props, key)} />}
      {haus && <Zahlenhaus key={haus.id} block={haus} apply={(props, key) => grows("zahlenhaus", props, key)} />}
      {dreieck && <Rechendreieck key={dreieck.id} block={dreieck} apply={(props, key) => grows("rechendreieck", props, key)} />}
      {strahl && <Zahlenstrahl key={strahl.id} block={strahl} apply={(props, key) => style("zahlenstrahl", props, key)} />}
      {feld && <Hunderterfeld key={feld.id} block={feld} apply={(props, key) => style("hunderterfeld", props, key)} />}
      {uhr && <Uhr key={uhr.id} block={uhr} apply={(props, key, back) => grows("uhr", props, key, back)} />}
      {skb && <Selbstkontrolle key={skb.id} block={skb} doc={doc} apply={(props, key) => style("selbstkontrolle", props, key)} />}
      {points && (
        <>
          <h2>Punkte</h2>
          <div className="seg">
            <ScoreInput max={points.props.max} change={(max) => style("points", { max })} steps={bump} />
          </div>
        </>
      )}
      {sign && (
        <>
          <h2>Symbol</h2>
          <Symbols value={sign.props.code} onPick={(code) => style("symbol", { code })} />
        </>
      )}
      {crop && (
        <>
          <h2>Bild</h2>
          <button className={cropping ? "wide on" : "wide"} aria-pressed={cropping} onClick={crop}>
            {cropping ? "Fertig" : "Zuschneiden"}
          </button>
        </>
      )}
      <h2>Drehen</h2>
      <div className="seg">
        {TURNS.map(([label, Icon, by]) => (
          <button key={label} aria-label={label} title={label} disabled={by ? level : plain} onClick={() => (by ? spin(by) : mirror(label[0] === "H" ? "x" : "y"))}>
            <Icon size={14} aria-hidden />
          </button>
        ))}
      </div>
      <h2>Nummerierung</h2>
      <Numbering value={mark} onChange={number} symbol={() => number("2B50")} />
      {mark && !counts(mark) && <Symbols value={mark} onPick={number} />}
    </>
  );
}

// The trace text of a text, a shape, a table or a Lineatur: Aus, Grau, Umriss or Gepunktet. Gepunktet needs the font's
// dotted cut. Fading makes the trace lighter along the row or from row to row. Aus takes the fading along; the other
// choices set only their own keys.
const TRACE_CHOICE: Record<string, { trace?: true | "outline" | "dotted"; fade?: Fade }> = {
  off: { trace: undefined, fade: undefined },
  grey: { trace: true },
  outline: { trace: "outline" },
  dotted: { trace: "dotted" },
};
function TraceControls({ props, font, onChange }: { props: { trace?: unknown; fade?: unknown; font?: Font }; font: Font | undefined; onChange: (props: { trace?: true | "outline" | "dotted"; fade?: Fade }) => void }) {
  const trace = traceOf({ ...props, font }) ?? "off";
  const fade = fadeOf({ ...props, font });
  const dotted = !!dottedFamily(font);
  return (
    <>
      <select aria-label="Nachspurtext" value={trace} onChange={(e) => onChange(TRACE_CHOICE[e.target.value])}>
        <option value="off">Aus</option>
        <option value="grey">Grau</option>
        <option value="outline">Umriss</option>
        <option value="dotted" disabled={!dotted}>
          Gepunktet
        </option>
      </select>
      {!dotted && <p className="hint">Gepunktet gibt es nur in der Grundschrift (Urff).</p>}
      {trace !== "off" && (
        <button className={fade ? "on" : ""} aria-pressed={!!fade} onClick={() => onChange({ fade: fade ? undefined : "row" })}>
          Ausblenden
        </button>
      )}
      {fade && (
        <div className="seg">
          <button className={fade === "row" ? "on" : ""} aria-pressed={fade === "row"} onClick={() => onChange({ fade: "row" })}>
            In der Zeile
          </button>
          <button className={fade === "rows" ? "on" : ""} aria-pressed={fade === "rows"} onClick={() => onChange({ fade: "rows" })}>
            Von Zeile zu Zeile
          </button>
        </div>
      )}
    </>
  );
}

// A font menu in FONT_GROUPS' order, each font shown in its own face. The native select keeps the value and the keys;
// its list is ours, because macOS and iPadOS draw a native list in the system font.
const FONT_KEYS = FONT_GROUPS.flatMap(([, fonts]) => fonts) as readonly string[];
// The faces load when the pointer or the focus first comes to a font menu, so a name shows at once when its list
// opens. Not before: each face that comes measures the bows of every block anew. A face that fails shows its fallback.
let preloaded = false;
const preload = () => {
  if (preloaded) return;
  preloaded = true;
  for (const font of FONT_KEYS) document.fonts.load(`16px "${FONTS[font as Font][1]}"`).catch(() => {});
};
function FontSelect({ label, value: stored, unknown, onChange }: { label: string; value: unknown; unknown?: string; onChange: (font: string) => void }) {
  // A font nobody knows shows as Druckschrift, the font it draws in.
  const value = fontOf(stored);
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const wrap = useRef<HTMLDivElement>(null);
  const select = useRef<HTMLSelectElement>(null);
  // Where the finger came down, to tell a tap from a swipe.
  const touch = useRef<{ x: number; y: number } | undefined>(undefined);
  // The faces load now, so a name shows at once when the list opens. A face that fails shows its fallback.
  // A press outside the select and the list shuts the list with no change, and goes on to the page, as a press beside
  // the browser's own list does. It is heard first, so a press that the desk keeps to itself shuts the list too.
  useEffect(() => {
    if (!open) return;
    const outside = (e: PointerEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    addEventListener("pointerdown", outside, true);
    return () => removeEventListener("pointerdown", outside, true);
  }, [open]);
  const show = () => {
    preload();
    setHi(Math.max(0, FONT_KEYS.indexOf(value)));
    setOpen(true);
  };
  const pick = (font: string) => {
    setOpen(false);
    select.current?.focus();
    if (font !== value) onChange(font);
  };
  const toggle = () => (open ? setOpen(false) : show());
  // The keys of the closed select step through the fonts; the keys of the open list move and pick.
  const key = (e: React.KeyboardEvent<HTMLSelectElement>) => {
    const step = e.key === "ArrowDown" ? 1 : e.key === "ArrowUp" ? -1 : 0;
    if (!open) {
      // Enter is not one of them: on a closed menu it gives the keys back to the sheet.
      if ([" ", "F4"].includes(e.key) || (e.altKey && e.key === "ArrowDown")) {
        // The panel's own keys stay out: the list keeps the keyup too.
        e.preventDefault();
        e.stopPropagation();
        show();
      } else if (step && !e.altKey) {
        e.preventDefault();
        const next = FONT_KEYS[Math.min(FONT_KEYS.length - 1, Math.max(0, FONT_KEYS.indexOf(value) + step))];
        if (next !== value) onChange(next);
      }
      return;
    }
    if (e.key === "Tab") {
      setOpen(false);
      return;
    }
    // Every other key is the list's: the sheet and the drawer do not hear of it.
    e.preventDefault();
    e.stopPropagation();
    if (step) {
      setHi((h) => Math.min(FONT_KEYS.length - 1, Math.max(0, h + step)));
    } else if (["Home", "PageUp"].includes(e.key)) {
      setHi(0);
    } else if (["End", "PageDown"].includes(e.key)) {
      setHi(FONT_KEYS.length - 1);
    } else if (e.key === "Enter" || e.key === " ") {
      pick(FONT_KEYS[hi]);
    } else if (e.key === "Escape") {
      // The drawer stays open.
      setOpen(false);
    } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
      // A letter moves the highlight to the next font whose name starts with it, wrapping round.
      const letter = e.key.toLocaleLowerCase("de");
      const after = [...FONT_KEYS.slice(hi + 1), ...FONT_KEYS.slice(0, hi + 1)];
      const next = after.find((font) => FONTS[font as Font][0].toLocaleLowerCase("de").startsWith(letter));
      if (next) setHi(FONT_KEYS.indexOf(next));
    }
  };
  return (
    <>
      <div className="fontsel" ref={wrap}>
        <select
          ref={select}
          aria-label={label}
          value={value}
          style={{ fontFamily: FONTS[value][1] }}
          onChange={(e) => onChange(e.target.value)}
          onMouseDown={(e) => {
            if (e.button !== 0) return;
            e.preventDefault();
            select.current?.focus();
            toggle();
          }}
          data-open={open || undefined}
          onTouchStart={(e) => {
            const t = e.touches[0];
            touch.current = { x: t.clientX, y: t.clientY };
          }}
          onTouchEnd={(e) => {
            // A finger that moved is a scroll of the drawer, and opens nothing.
            const t = e.changedTouches[0];
            const start = touch.current;
            if (!t || !start || Math.hypot(t.clientX - start.x, t.clientY - start.y) >= 10) return;
            e.preventDefault();
            select.current?.focus();
            toggle();
          }}
          onKeyDown={key}
          onPointerEnter={preload}
          onFocus={preload}
        >
          {FONT_GROUPS.map(([group, fonts]) => (
            <optgroup key={group} label={group}>
              {fonts.map((font) => (
                <option key={font} value={font} style={{ fontFamily: FONTS[font][1] }}>
                  {FONTS[font][0]}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        {open && (
          <div role="listbox" aria-label={`Liste: ${label}`} className="fontlist">
            {FONT_GROUPS.map(([group, fonts]) => (
              <div role="group" aria-label={group} key={group}>
                <div role="heading" aria-level={3} className="fontgroup">
                  {group}
                </div>
                {fonts.map((font) => (
                  <div
                    role="option"
                    key={font}
                    aria-selected={font === value}
                    className={FONT_KEYS[hi] === font ? "hi" : undefined}
                    style={{ fontFamily: `${FONTS[font][1]}, Andika, sans-serif` }}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => pick(font)}
                  >
                    {FONTS[font][0]}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
      {unknown && (
        <p className="hint">
          Die Schrift „{unknown}“ kennt Blattomat nicht: Der Block druckt in Druckschrift.
          <button onClick={() => onChange("andika")}>In Druckschrift setzen</button>
        </p>
      )}
    </>
  );
}

// The first font of the picked blocks that the app does not know, if one holds one.
const unknownFont = (fonts: unknown[]) => fonts.find((f): f is string => typeof f === "string" && !Object.hasOwn(FONTS, f));

// What a block that holds words says of its syllables: a text, a shape with text and a table.
const worded = (b: Block) => (b.type === "table" ? b.props : boxed(b));
// A Lineatur takes the bows and the colours too, on its written line and on its Lernwörter list, Karo included.
const ruled = (b: Block) => (b.type === "ruling" ? b.props : undefined);
const syllabled = (b: Block) => ruled(b) ?? worded(b);
// A stored seed that is a finite number, or none: a seed that is no number counts as no seed.
const seedOf = (n: unknown) => (typeof n === "number" && Number.isFinite(n) ? n : undefined);
// A text and a shape take it through `look`, a table through `style`: the key they share makes one undo step,
// so there is always one, the names of the props where none is given.
const both = (held: Block[], look: Props["look"], style: Props["style"]) => (props: object, key = Object.keys(props).join()) => {
  if (held.some(boxed)) look(props, key);
  if (held.some((b) => b.type === "table")) style("table", props, key);
  const rulings = held.filter((b) => b.type === "ruling").map((b) => b.id);
  if (rulings.length) style("ruling", props, key, rulings);
};

// The gaps of a Lückentext for every selected block that holds words: the switch of the gaps, the width they all
// have, the box of solution words, and every n-th word. Each switch is on unless all have it, as bold. With a table
// cell open the switch is that cell's, and with a text open that of the picked words.
function Gaps({ sel, part, cell, look, style, gap, every }: Pick<Props, "sel" | "part" | "cell" | "look" | "style" | "gap" | "every">) {
  const held = sel.filter(worded);
  // The n of "Jedes n-te Wort", as typed.
  const [n, setN] = useState("5");
  if (!held.length) return null;
  const cells = cell !== undefined && sel.length === 1 && sel[0].type === "table" ? sel[0].props : undefined;
  const lit = part ? !!part.gap : cells ? !!cells.gaps?.[Math.floor(cell! / cells.cols.length)]?.[cell! % cells.cols.length] : held.every((b) => (b.type === "table" ? allCellGap(b.props.cells, b.props.gaps) : allGap(parasOf(boxed(b)!))));
  const same = held.every((b) => worded(b)!.gapWidth !== undefined);
  const bank = held.every((b) => worded(b)!.bank !== undefined);
  const set = both(held, look, style);
  // The widest gap drawn in the selected blocks, in whole mm, or 30 when none is drawn.
  const widest = () => {
    const drawn = [...document.querySelectorAll<HTMLElement>(".block.sel .gap")];
    return drawn.length ? Math.max(5, Math.ceil(Math.max(...drawn.map((el) => el.offsetWidth / K)))) : 30;
  };
  // A linked text or shape has no gaps of its own, so only its width shows.
  const linked = held.every((b) => boxed(b)?.list === true);
  return (
    <>
      {!linked && (
        <button className={lit ? "on" : ""} aria-pressed={lit} onClick={() => gap(!lit)}>
          Lücke
        </button>
      )}
      <button className={same ? "on" : ""} aria-pressed={same} onClick={() => set({ gapWidth: same ? undefined : widest() }, "gapWidth")}>
        Lücken gleich breit
      </button>
      {same && <Num label="Breite der Lücken" value={worded(held[0])!.gapWidth} disabled={false} onCommit={(to) => set({ gapWidth: Math.max(5, to) }, "gapWidthTo")} />}
      {!linked && (
        <div className="seg">
          {/* The number stays in the panel until a button uses it: Ctrl+Z is the field's own. */}
          <input type="number" aria-label="n" className="own" min={2} step={1} value={n} onChange={(e) => setN(e.target.value)} />
          <button onClick={() => every(Math.max(2, Math.round(+n) || 2))}>Jedes n-te Wort</button>
        </div>
      )}
      {!linked && (
        <button className={bank ? "on" : ""} aria-pressed={bank} onClick={() => set({ bank: bank ? undefined : draw() }, "bank")}>
          Lösungswörter
        </button>
      )}
      {!linked && bank && (
        <button
          onClick={() => {
            const shown = held.map((b) => ({ seed: seedOf(worded(b)!.bank), show: (seed: number) => shuffled(solutions(b), seed, solutions(b)).join("\n") }));
            const seed = draw(shown);
            if (moves(shown, seed)) set({ bank: seed }, "shuffle");
          }}
        >
          Neu mischen
        </button>
      )}
    </>
  );
}

// The solution words of a block: the cells of a table, or the words of a text or a shape, in reading order.
const solutions = (b: Block) => (b.type === "table" ? cellEntries(b.props.cells, b.props.gaps) : entries(parasOf(boxed(b)!)));

// The sheet's Lernwörter for a text or a shape: as its own text or as the list, in 1 to 4 columns, with letters hidden as
// gaps in one of three ways. Each switch is on only when all the picked ones have it. "Neu wählen" picks the hidden letters anew, in "one" only: the other two modes do not depend on the seed.
function Fed({ sel, words, toList, look, link, feed }: Pick<Props, "sel" | "words" | "toList" | "look" | "link" | "feed">) {
  const held = sel.flatMap((b) => {
    const p = boxed(b);
    return p ? [p] : [];
  });
  if (!held.length) return null;
  const linked = held.every((p) => p.list === true);
  const holes = held.every((p) => holesOf(p) !== undefined);
  const mode = holesOf(held[0]);
  const cols = listColsOf(held[0]);
  return (
    <>
      <select aria-label="Text des Textfelds" value={linked ? "list" : "own"} onChange={(e) => link(e.target.value === "list")}>
        <option value="own">Eigener Text</option>
        <option value="list">Text aus Lernwörtern</option>
      </select>
      {linked && (
        <>
          <div className="seg">
            {[1, 2, 3, 4].map((n) => (
              <button key={n} className={cols === n ? "on" : ""} aria-label={n === 1 ? "1 Spalte" : `${n} Spalten`} aria-pressed={cols === n} onClick={() => look({ listCols: n === 1 ? undefined : n }, "listCols")}>
                {n}
              </button>
            ))}
          </div>
          <button onClick={toList}>Lernwörter bearbeiten</button>
          <button className={holes ? "on" : ""} aria-pressed={holes} onClick={() => feed(holes ? { holes: undefined } : { holes: "one", holeSeed: seedOf(held[0].holeSeed) ?? draw(), mix: undefined }, "holes")}>
            Lückenwörter
          </button>
          {holes && mode && (
            <>
              <div className="seg">
                {([["one", "Ein Buchstabe"], ["second", "Jeder zweite"], ["vowels", "Alle Vokale"]] as const).map(([value, label]) => (
                  <button key={value} className={mode === value ? "on" : ""} aria-pressed={mode === value} onClick={() => feed({ holes: value }, "holesMode")}>
                    {label}
                  </button>
                ))}
              </div>
              {mode === "one" && (
                <button
                  onClick={() => {
                    const seed = seedOf(held[0].holeSeed);
                    const shown = words.map((w) => ({ seed, show: (s: number) => holed(w, mode, s).map((run) => (run.gap ? "_" : run.text)).join("") }));
                    const next = draw(shown);
                    if (moves(shown, next)) feed({ holeSeed: next }, "holesPick");
                  }}
                >
                  Neu wählen
                </button>
              )}
            </>
          )}
        </>
      )}
    </>
  );
}

// The words of a text that Schüttelwörter mixes, as typed and in reading order: a linked text has the sheet's words.
const sources = (p: TextProps, words: string[]) =>
  mixed(shownParas(p, words), { seed: 0 })
    .flat()
    .flatMap((part) => (part.source ? [part.source] : []));

// Schüttelwörter: the letters of each word in another order, for every selected text and shape. On unless all have a
// seed, as bold. Off keeps the settings stored, so the next press brings them back. "Neu schütteln" draws the best of
// 40 seeds, so in a long text a word can keep its order. A press that moves no word makes no step. A linked text with
// Lückenwörter is no mix: the gaps take its place.
function Mix({ sel, look, words: sheet }: Pick<Props, "sel" | "look" | "words">) {
  const held = sel.flatMap((b) => {
    const p = boxed(b);
    return p ? [p] : [];
  });
  if (!held.length) return null;
  const on = held.every((p) => seedOf(p.mix) !== undefined && !(p.list === true && holesOf(p)));
  const first = held.every((p) => p.mixFirst === true);
  const caps = held.every((p) => p.mixCaps === true);
  const linked = held.every((p) => p.list === true);
  const line = lineOf(held[0]);
  const lines = linked ? ([["after", "Linie dahinter"], ["under", "Linie darunter"]] as const) : ([[undefined, "Keine Linie"], ["after", "Linie dahinter"], ["under", "Linie darunter"]] as const);
  // One entry per word of each block, as the pupil sees it: in capitals where the caps are on.
  const words = (): Shown[] => held.flatMap((p) => sources(p, sheet).map((source) => ({ seed: seedOf(p.mix), show: (seed: number) => word(source, seed, p.mixFirst === true, p.mixCaps === true) })));
  return (
    <>
      <button className={on ? "on" : ""} aria-pressed={on} onClick={() => look(on ? { mix: undefined } : { mix: draw(), holes: undefined }, "mix")}>
        Schüttelwörter
      </button>
      {on && (
        <>
          <button className={first ? "on" : ""} aria-pressed={first} onClick={() => look({ mixFirst: first ? undefined : true }, "mixFirst")}>
            Erster Buchstabe bleibt
          </button>
          <button className={caps ? "on" : ""} aria-pressed={caps} onClick={() => look({ mixCaps: caps ? undefined : true }, "mixCaps")}>
            Großbuchstaben
          </button>
          <div className="seg">
            {lines.map(([value, label]) => (
              <button key={label} className={line === value ? "on" : ""} aria-pressed={line === value} onClick={() => look({ mixLine: value }, "mixLine")}>
                {label}
              </button>
            ))}
          </div>
          <button
            onClick={() => {
              const shown = words();
              const seed = draw(shown);
              if (moves(shown, seed)) look({ mix: seed }, "mixShuffle");
            }}
          >
            Neu schütteln
          </button>
        </>
      )}
    </>
  );
}

// The switches for the bows under the syllables and for their colours, for every selected block that holds words: on
// unless all have them, as bold. With Silbenfarbe on, the pair and the choices for it stand below. With one such block
// its words stand below too, each as it is split, to mend by hand: a click on a word shows its letters, and a click
// between two of them sets a break there or takes it away.
function Syllables({ sel, part, look, style, mendWord, doc, words }: Pick<Props, "sel" | "part" | "look" | "style" | "mendWord" | "doc" | "words">) {
  const held = sel.filter(syllabled);
  const bowsOn = held.every((b) => syllabled(b)!.syllables);
  // A stored pair that is garbage colours nothing, so the switch is off for it.
  const tintsOn = held.every((b) => pairOf(syllabled(b)!.tints));
  const pair = pairOf(held[0] && syllabled(held[0])!.tints) ?? TINTS;
  const greys = pair[0] === GREYS[0] && pair[1] === GREYS[1];
  const across = held.every((b) => syllabled(b)!.tintsAcross);
  const split = useSplitter(bowsOn || tintsOn);
  // The word whose letters show, as `breaks` names it.
  const [open, setOpen] = useState<string>();
  // The word the caret stands in opens with no click.
  useEffect(() => {
    if (split && part?.word) setOpen(split.keyOf(part.word));
  }, [split, part?.word]);
  const set = both(held, look, style);
  const one = split && held.length === 1 ? syllabled(held[0])! : undefined;
  const fixes = { ...doc.breaks, ...one?.breaks };
  // Whether the teacher split the word, under its key or under the old one: "constructor" is a word too, and every object has one.
  const own = (w?: string) => !!w && [split!.keyOf(w), split!.oldKeyOf(w)].some((key) => Object.hasOwn(fixes, key) && Array.isArray(fixes[key]));
  // Each word once, however it is written: a split holds for "Abend" and "abend" alike.
  const keys = new Set<string>();
  // A Lineatur on the Lernwörter list has the sheet's words, not a text of its own.
  const linked = !!one && held[0].type === "ruling" && listOf(held[0]) !== undefined;
  const all = one ? split!.words(linked ? words.join("\n") : "cells" in one ? one.cells.flat().join("\n") : one.text ?? "").filter((w) => !keys.has(split!.keyOf(w)) && keys.add(split!.keyOf(w))) : [];
  const word = all.find((w) => split!.keyOf(w) === open);
  // Sets or removes the break at `at`, or with none takes the word back to its own split. A word split as the
  // module splits it needs no entry. The mend holds for the word in every block of the sheet.
  const mend = (at?: number) => {
    const now = split!.cuts(word!, fixes);
    const next = at === undefined ? undefined : now.includes(at) ? now.filter((cut) => cut !== at) : [...now, at].sort((a, b) => a - b);
    const counts = next && split!.counted(word!, next);
    mendWord([split!.keyOf(word!), split!.oldKeyOf(word!)], counts && String(counts) !== String(split!.counted(word!, split!.split(word!))) ? counts : undefined, held[0].id);
  };
  return (
    <>
      {/* Off is no entry, as on a sheet that never had bows. */}
      <button className={bowsOn ? "on" : ""} aria-pressed={bowsOn} onClick={() => set({ syllables: bowsOn ? undefined : true }, "syllables")}>
        Silbenbögen
      </button>
      <button className={tintsOn ? "on" : ""} aria-pressed={tintsOn} onClick={() => set(tintsOn ? { tints: undefined, tintsAcross: undefined } : { tints: TINTS }, "tints")}>
        Silbenfarbe
      </button>
      {tintsOn && (
        <>
          <label>
            Erste Silbe
            <input type="color" value={pair[0]} onChange={(e) => set({ tints: [e.target.value, pair[1]] }, "tint0")} />
          </label>
          <label>
            Zweite Silbe
            <input type="color" value={pair[1]} onChange={(e) => set({ tints: [pair[0], e.target.value] }, "tint1")} />
          </label>
          <button className={greys ? "on" : ""} aria-pressed={greys} onClick={() => set({ tints: greys ? TINTS : GREYS }, "tints")}>
            Schwarz/Grau
          </button>
          <button className={across ? "on" : ""} aria-pressed={across} onClick={() => set({ tintsAcross: across ? undefined : true })}>
            Über Wortgrenzen
          </button>
        </>
      )}
      {one && all.length > 0 && (
        <>
          <p className="hint">Silbe falsch? Wort anklicken und Trennstellen setzen.</p>
          <div className="words">
            {all.map((w) => {
              const key = split!.keyOf(w);
              const cut = [0, ...split!.cuts(w, fixes), w.length];
              return (
                <button key={key} className={`${key === open ? "on" : ""}${own(w) ? " own" : ""}`} aria-pressed={key === open} title={own(w) ? "von Hand getrennt" : undefined} onClick={() => setOpen(key)}>
                  {cut.slice(1).map((end, i) => w.slice(cut[i], end)).join("·")}
                </button>
              );
            })}
          </div>
          {word && (
            <div className="gaps">
              {word.split("").map((letter, i) => {
                const cut = split!.cuts(word, fixes).includes(i);
                return (
                  <Fragment key={i}>
                    {/* No break before a mark that belongs to the letter before it. */}
                    {i > 0 && !/\p{M}/u.test(letter) && (
                      <button className={cut ? "on" : ""} aria-label={`${word.slice(0, i)}|${word.slice(i)}`} aria-pressed={cut} onClick={() => mend(i)}>
                        {cut ? "|" : "·"}
                      </button>
                    )}
                    {letter}
                  </Fragment>
                );
              })}
            </div>
          )}
          {word && own(word) && <button onClick={() => mend()}>Zurücksetzen</button>}
        </>
      )}
    </>
  );
}

// The size of each unit in mm, for a length typed with one: 72 pt is an inch.
const UNITS: Record<string, number> = { mm: 1, cm: 10, pt: 25.4 / 72, in: 25.4 };

// A field for a number. What is typed counts on Enter or when the field is left, and Escape drops it. An arrow up
// or down steps by one. `value` is absent where the selected blocks differ. With `units` a length may carry mm, cm,
// pt or in.
function Num({ label, value, disabled, units, onCommit }: { label: string; value?: number; disabled: boolean; units?: boolean; onCommit: (n: number) => void }) {
  const [draft, setDraft] = useState<string>();
  // Whether the mouse that is down brought the focus.
  const fresh = useRef(false);
  const input = useRef<HTMLInputElement>(null);
  // The field follows the sheet: a drag or an undo takes the place of what was typed. Not while the teacher types in
  // it: the end of a drag can land late, after the first key (#727), and Enter would then find nothing to set.
  useEffect(() => {
    if (document.activeElement !== input.current) setDraft(undefined);
  }, [value]);
  // Only digits with a comma or a point count: "1e3" and "Infinity" are numbers to JavaScript alone.
  const read = () => {
    const text = draft?.trim() ?? "";
    const unit = units && /^(-?\d+(?:[.,]\d+)?)\s*(mm|cm|pt|in)$/i.exec(text);
    if (unit) return round(Number(unit[1].replace(",", ".")) * UNITS[unit[2].toLowerCase()]);
    return /^-?\d+([.,]\d+)?$/.test(text) ? round(Number(text.replace(",", "."))) : NaN;
  };
  // Without a draft the blur that follows Enter finds nothing to set.
  const commit = (n: number) => {
    setDraft(undefined);
    if (!Number.isNaN(n) && n !== value) onCommit(n);
  };
  return (
    <label>
      {label}
      <input
        ref={input}
        className="mm"
        type="text"
        inputMode="decimal"
        disabled={disabled}
        value={draft ?? (value === undefined ? "" : String(round(value)).replace(".", ","))}
        onChange={(e) => setDraft(e.target.value)}
        onFocus={(e) => e.target.select()}
        // Safari puts the caret where the mouse comes up and so drops what the focus selected.
        onMouseDown={(e) => (fresh.current = document.activeElement !== e.target)}
        onMouseUp={(e) => {
          if (fresh.current) e.preventDefault();
          fresh.current = false;
        }}
        onBlur={() => draft !== undefined && commit(read())}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit(read());
          // Ctrl+Z and Ctrl+Y here undo and redo the sheet, whose step takes the place of what was typed.
          if (e.key === "Escape" || ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key))) setDraft(undefined);
          if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
          e.preventDefault();
          commit(round((draft === undefined ? (value ?? NaN) : read()) + (e.key === "ArrowUp" ? 1 : -1)));
        }}
      />
    </label>
  );
}

// Every symbol as a button, narrowed by a search through the German and English names.
function Symbols({ value, onPick }: { value: string; onPick: (code: string) => void }) {
  const [query, setQuery] = useState("");
  const found = SYMBOLS.filter(([, de, en]) => `${de} ${en}`.toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <>
      <input type="text" aria-label="Symbol suchen" placeholder="Suchen, z. B. Schere" value={query} onChange={(e) => setQuery(e.target.value)} />
      <div className="symbols">
        {found.map(([code, de]) => (
          <button key={code} className={code === value ? "on" : ""} aria-label={de} title={de} onClick={() => onPick(code)}>
            <img src={symbol(code)} alt="" />
          </button>
        ))}
      </div>
      {!found.length && <p className="hint">Kein Symbol gefunden.</p>}
    </>
  );
}
