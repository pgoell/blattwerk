// The sheet document and how a page of it draws, shared by the editor, the list's thumbnails and the PDF.
import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore, type CSSProperties, type FocusEvent, type ReactNode, type SVGAttributes } from "react";
import type { Breaks } from "./syllables";
import { cellEntries, entries, shuffled } from "./bank";

// One page's blocks, as the sheet document stores them: mm from the page's top-left corner. `mark` is the numbering
// before a block: a counting one such as "1.", "a)" or "(1)", or a symbol's code. `angle` turns the box about its
// centre, in degrees clockwise from 0 up to 360. `flipX` and `flipY` mirror a picture or a symbol in its box.
export type Box = { id: string; x: number; y: number; w: number; h: number; z: number; locked: boolean; mark?: string; group?: string[]; angle?: number; flipX?: boolean; flipY?: boolean };
// "double" is an arrow with a head at both ends.
export type Kind = "rect" | "rounded" | "circle" | "triangle" | "star" | "bubble" | "line" | "arrow" | "double";
export type Corner = "nw" | "ne" | "sw" | "se";
export type Align = "left" | "center" | "right";
export type Font = keyof typeof FONTS;
export type Ruling = keyof typeof RULINGS;
export type Valign = "top" | "middle" | "bottom";
// The two colours the syllables of a text take in turn.
export type Tints = [string, string];
// Blue then red, as the schoolbooks print syllables, and the pair for a copy in black and white: the grey is as
// dark as a copier still prints and as light as the eye still tells from the black.
export const TINTS: Tints = ["#1a56db", "#e02424"];
export const GREYS: Tints = ["#000000", "#707070"];
export type List = "bullet" | "number";
// A stretch of a text with a look of its own. `bold` and `italic` stand in for the block's, on or off; an underline
// and a colour lie on top of the block's. `gap` makes the stretch a gap of a Lückentext: the pupil's sheet shows a line
// to write on in its place, as wide as its words, the editor shows the words in grey and the answer key in its colour.
export type Run = { text: string; bold?: boolean; italic?: boolean; underline?: boolean; color?: string; gap?: boolean };
// A paragraph of a text: an item of a list with `list`, moved in by `level` steps, 0 to 2.
export type Para = { runs: Run[]; list?: List; level?: number };
// Sheets saved before text had these settings lack them: a text is then Andika, black, with lines 1.3 apart.
// A text has what a shape has, as a PowerPoint text box does: a fill and a border ("none" or absent for neither,
// the border 0.5 mm wide unless set), dashes, and round corners with `kind`. `opacity` is how solid the fill is,
// from 0 (unseen) to 1 or absent (solid); the border and the text are always solid.
// `rich` holds the text's paragraphs once a part of it has a look of its own, or it has a list. `text` always holds
// the same words plain, and is all that a sheet saved before has.
// `syllables` draws a bow under each syllable of each word (Silbenbögen); `breaks` holds the words the teacher
// split by hand. `tints` colours the syllables in turn (Silbenfarbe): the pair of colours, and with `tintsAcross`
// the turn runs on from word to word through the block's text, where else each word starts with the first.
// `gapWidth` makes every gap of the text at least so many mm wide, and `bank` adds a box with the hidden words under
// the text (Lösungswörter): it is the seed their order is shuffled by.
// Sheets saved before have none of these.
export type TextProps = { text: string; rich?: Para[]; syllables?: boolean; breaks?: Breaks; tints?: Tints; tintsAcross?: boolean; gapWidth?: number; bank?: number; size: number; align: Align; font?: Font; bold?: boolean; italic?: boolean; underline?: boolean; color?: string; spacing?: number; valign?: Valign; kind?: Kind; fill?: string; opacity?: number; stroke?: string; strokeWidth?: number; dash?: "dashed" | "dotted" };
export type TextBlock = Box & { type: "text"; props: TextProps };
// A shape can hold text: centred and in the middle unless set otherwise. A line or arrow runs from the corner
// `from` of its box to the opposite one. It can have a tick at each end and say how long it is, on the sheet
// ("show") or on the answer key alone ("key").
export type ShapeBlock = Box & { type: "shape"; props: Partial<TextProps> & { kind: Kind; fill: string; stroke: string; strokeWidth: number; from?: Corner; ticks?: boolean; label?: "show" | "key" } };
// As many rows as fit the block's height are drawn. `text` is written on the rows, on Karo a character to a
// square, and grey with `trace` so the children can write over it. Karo is always in print.
export type RulingBlock = Box & { type: "ruling"; props: { kind: Ruling; color: string; text?: string; font?: Font; trace?: boolean } };
// The words of a name line, as a new one has them. A line's `fields` replace them.
export const FIELDS = ["Name", "Datum", "Klasse"];
export type NameBlock = Box & { type: "name"; props: { fields?: string[] } };
export type PointsBlock = Box & { type: "points"; props: { max: number } };
export type SymbolBlock = Box & { type: "symbol"; props: { code: string } };
// `ratio` is the picture's width over its height; `cut` the share cropped off its left, top, right and bottom.
export type ImageBlock = Box & { type: "image"; props: { upload: number; ratio: number; cut: number[] } };
export type Op = keyof typeof SIGNS;
// The lowest and the highest digit a place may hold.
export type Range = [number, number];
// A written exercise on squared paper. A cell is [column, row, character, kind], a line [from column, to column,
// above row, kind]; kind 0 is printed on the sheet, 1 is the answer key's and 2 a small carry of the answer key's.
export type Grid = { cols: number; rows: number; cells: [number, number, string, number][]; lines: [number, number, number, number][] };
// `hide` is the number a gap stands for, the result when absent. `rest` is what a division leaves.
export type Exercise = { op: Op; a: number; b: number; result: number; rest: number; hide?: "a" | "b"; grid?: Grid };
// The generator's limits, as the server takes them: `a` and `b` hold the digits each number may have, units first.
export type Limits = {
  ops: Op[];
  max: number;
  a: Range[];
  b: Range[];
  carry: "none" | "required" | "either";
  rest: boolean;
  format: "row" | "gap" | "written";
  count: number;
  seed: number;
};
// What the generator made of the limits. With fewer exercises than asked for, `loosen` names the limits in the way.
export type Made = { exercises: Exercise[]; loosen: string[] | null };
// `numbering` counts the exercises of the block; `size` is the font size of a row or a gap in points.
export type MathsProps = Limits & Made & { columns: number; size: number; numbering?: string };
export type MathsBlock = Box & { type: "maths"; props: MathsProps };
// `cells` holds the texts, a row of columns at a time. `cols` holds each column's share of the block's width, in
// parts of their sum. A row is as high as its highest cell needs, and the rows share equally what room the block
// has beyond that. `line` is the colour of the lines, and `head` sets the first row in bold. A cell holds no runs, so
// a whole cell is a gap: `gaps` holds a flag for each cell, a row of columns at a time as `cells` does.
export type TableBlock = Box & { type: "table"; props: { cells: string[][]; cols: number[]; size: number; align: Align; font?: Font; color?: string; line: string; head?: boolean; syllables?: boolean; breaks?: Breaks; tints?: Tints; tintsAcross?: boolean; gaps?: boolean[][]; gapWidth?: number; bank?: number } };
export type Block = TextBlock | ShapeBlock | RulingBlock | NameBlock | PointsBlock | SymbolBlock | ImageBlock | MathsBlock | TableBlock;
export type Axis = "x" | "y";
// The teacher's own guide lines, in mm.
export type Guides = Record<Axis, number[]>;
// A page can have guide lines of its own, beside the sheet's, and a grid and a format of its own in place of the
// sheet's.
export type Page = { blocks: Block[]; guides?: Guides; grid?: number; landscape?: boolean };
// The pages, and what every page shares: guide lines, the grid's cell in mm (0 for none), and whether the A4 lies
// on its side.
export type Doc = { pages: Page[]; guides: Guides; grid: number; landscape?: boolean };
// The server counts a sheet's saved documents in `version`.
export type Sheet = { id: number; user_id: number; title: string; updated: string; version: number; doc: Doc };

// A page's width and height in mm: A4, upright or on its side.
export const sizeOf = (doc: Doc, n: number) => ((doc.pages[n].landscape ?? doc.landscape) ? [297, 210] : [210, 297]);
// The margin a new block keeps, and a ruling that fills the page.
export const MARGIN = 15;
export const PT = 25.4 / 72; // mm per point
// The pixels per mm of the PDF. Every page is laid out at this scale and drawn at another by a transform, so a
// line of text breaks at the same word in the PDF, at every zoom and in a thumbnail.
export const K = 96 / 25.4;
// Self-hosted, all under the SIL Open Font License: Andika for print, Playwrite for the four school scripts.
// The number is how far a font's baseline lies below the middle of a line of text, in em: half of its ascent less
// its descent. Text on a ruling needs it to stand on the line.
export const FONTS = {
  andika: ["Druckschrift", "Andika", 0.415],
  grund: ["Grundschrift", "Playwrite DE Grund Variable", 0.4545],
  va: ["Vereinfachte Ausgangsschrift", "Playwrite DE VA Variable", 0.46],
  sas: ["Schulausgangsschrift", "Playwrite DE SAS Variable", 0.4515],
  la: ["Lateinische Ausgangsschrift", "Playwrite DE LA Variable", 0.4545],
} as const;
// One row of each ruling: its height, and where its lines lie in mm from the row's top; Karo has squares instead.
// Lineatur 1 to 4 follow DIN 16552-1: four lines 5 mm apart, four lines 4 mm apart, a band of 3.5 mm, single lines
// 10 mm apart. The gap to the next row's lines (5, 4 and 8 mm) lies half above and half below, so blocks stack.
// In Lineatur 1 and 2 that gap is as wide as a zone, so the middle band is tinted, as in the schoolbooks: without
// it no one could tell where a row begins.
// Text stands on `base`, in a font of `size` mm. Every font's small letters are half its size high, so they fill
// the band of Lineatur 1 to 3; single lines have no band and take small letters 0.3 of a row high. On Karo a
// character is 0.75 of its square, as in a written exercise.
export const RULINGS = {
  l1: { name: "Lineatur 1 (Klasse 1)", row: 20, at: [2.5, 7.5, 12.5, 17.5], band: 5, base: 12.5, size: 10 },
  l2: { name: "Lineatur 2 (Klasse 2)", row: 16, at: [2, 6, 10, 14], band: 4, base: 10, size: 8 },
  l3: { name: "Lineatur 3 (Klasse 3)", row: 11.5, at: [4, 7.5], band: 0, base: 7.5, size: 7 },
  l4: { name: "Lineatur 4 (Klasse 4)", row: 10, at: [10], band: 0, base: 10, size: 6 },
  lines: { name: "Linien, 8 mm", row: 8, at: [8], band: 0, base: 8, size: 4.8 },
  k5: { name: "Karo 5 mm", row: 5, at: undefined, band: 0, base: 0, size: 3.75 },
  k7: { name: "Karo 7 mm", row: 7, at: undefined, band: 0, base: 0, size: 5.25 },
};
// The signs as German schools write them.
export const SIGNS = { "+": "+", "-": "−", "*": "·", "/": ":" };
// The side of a square of a written exercise, in mm.
export const KARO = 5;
// A numbering counts in numbers, "1", or letters, "a", and has one of these looks; "#o" is a ring around it.
export const LOOKS = ["#", "#.", "#)", "(#)", "#o"];
export const lookOf = (mark: string) => mark.replace(/[1a]/, "#");
// Whether a mark counts; a symbol's code does not.
export const counts = (mark?: string): mark is string => !!mark && LOOKS.includes(lookOf(mark));
export const EMPTY: Doc = { pages: [{ blocks: [] }], guides: { x: [], y: [] }, grid: 0 };

// A maths block saved with no digit ranges takes any digit in each place of its Zahlenraum.
function whole(b: Block): Block {
  if (b.type !== "maths" || (b.props.a && b.props.b)) return b;
  const any = Array.from(String(b.props.max), (): Range => [0, 9]);
  return { ...b, props: { ...b.props, a: b.props.a ?? any, b: b.props.b ?? any } };
}
// Templates saved before sheets had pages hold one page's blocks.
export const read = ({ pages, blocks, guides, grid, landscape }: Doc & { blocks?: Block[] }): Doc => ({
  pages: (pages ?? [{ blocks: blocks! }]).map((page) => ({ ...page, blocks: page.blocks.map(whole) })),
  guides,
  grid,
  landscape,
});
export const isLine = (b: Block): b is ShapeBlock => b.type === "shape" && (b.props.kind === "line" || b.props.kind === "arrow" || b.props.kind === "double");
// Whether a line's start, or its end, sits at the bottom (axis 0) or the right (axis 1) of its box.
export const far = (b: ShapeBlock, axis: 0 | 1, end: boolean) => ((b.props.from ?? "nw")[axis] === "se"[axis]) !== end;
// The text and the frame of a text, or of a shape that is no line.
export function boxed(b: Block): TextProps | undefined {
  if (b.type === "text") return b.props;
  // `isLine` tells the compiler that every shape it turns down is no shape, so the props are read first.
  const props = b.type === "shape" ? b.props : undefined;
  if (props && !isLine(b)) return { text: "", size: 14, align: "center", valign: "middle", ...props };
}
// A text's paragraphs: with no `rich`, one to a line.
export const parasOf = (p: TextProps): Para[] => p.rich ?? p.text.split("\n").map((text) => ({ runs: text ? [{ text }] : [] }));
// What a block keeps of its paragraphs: the plain text always, `rich` only when it says more than the text does.
export function stored(paras: Para[]) {
  const plain = paras.every((p) => !p.list && p.runs.every((r) => Object.keys(r).length === 1));
  return { text: paras.map((p) => p.runs.map((r) => r.text).join("")).join("\n"), rich: plain ? undefined : paras };
}
// Makes every paragraph of a text an item of a list, or with no `list` takes the lists away.
export const listed = (p: TextProps, list?: List) =>
  stored(parasOf(p).map(({ runs, level }) => ({ runs, ...(list && { list, ...(level && { level }) }) })));
// Takes from every run the settings that `props` names, so the block's own show in the whole text.
export const cleared = (paras: Para[], props: object) =>
  stored(paras.map((p) => ({ ...p, runs: p.runs.map((r) => Object.fromEntries(Object.entries(r).filter(([name]) => !(name in props))) as Run) })));
export const symbol = (code: string) => `/openmoji/${code}.svg`;
// A turned block's box turns as a whole. A flip mirrors only what the box shows: Moveable cannot take hold of a
// mirrored box, and a numbering must stay readable.
export const turned = (b: Box): CSSProperties | undefined => (b.angle ? { transform: `rotate(${b.angle}deg)` } : undefined);
// The cosine and sine of a block's angle.
export const dir = (b: { angle?: number }) => [Math.cos(((b.angle ?? 0) * Math.PI) / 180), Math.sin(((b.angle ?? 0) * Math.PI) / 180)];
// A new height for a block: the edge it starts at stays, as in PowerPoint. A turned block turns about its centre,
// and a new height moves that: the centre goes down the block's own axis, so that edge stays in its place on the
// page and the far edge moves alone.
export function tall(b: Box, h: number): Partial<Box> {
  if (!b.angle) return { h };
  const [c, s] = dir(b);
  const half = (h - b.h) / 2;
  return { h, x: Math.round((b.x - s * half) * 100) / 100, y: Math.round((b.y + (c - 1) * half) * 100) / 100 };
}
const flipped = (b: Box): CSSProperties | undefined => (b.flipX || b.flipY ? { transform: `scale(${b.flipX ? -1 : 1}, ${b.flipY ? -1 : 1})` } : undefined);
// How many rows of its ruling fit a block. Moveable's pixels leave a height a hair short of a full row.
export const rowsOf = (b: RulingBlock) => Math.floor(b.h / RULINGS[b.props.kind].row + 0.05);
export const colsOf = (b: RulingBlock) => Math.floor(b.w / RULINGS[b.props.kind].row + 0.05);
// The square each character of a Karo's text stands in, as [column, row, character]: a row is filled, then the
// next begins.
export function squares(text: string, cols: number) {
  const out: [number, number, string][] = [];
  let [x, y] = [0, 0];
  for (const ch of text) {
    if (ch === "\n" || x === cols) [x, y] = [0, y + 1];
    if (ch !== "\n") out.push([x++, y, ch]);
  }
  return out;
}
// The height in mm a maths block needs for its exercises.
export function mathsHeight(p: MathsProps) {
  const lines = Math.ceil(p.exercises.length / p.columns);
  const rows = Math.max(0, ...p.exercises.map((e) => e.grid?.rows ?? 0));
  return Math.max(10, Math.round(lines * (p.format === "written" ? (rows + 1) * KARO : p.size * PT * 2.4)));
}
export const sum = (ns: number[]) => ns.reduce((all, n) => all + n, 0);
// A table's props with an empty row or column more, before the one at `i`, or without the one at `i`. A new column
// is as wide as the others are on average, and the block keeps its width: the widths are shares of it.
// A row or column that comes or goes takes its gap flags along: a new one has no gap.
export function spliced({ cells, cols, gaps, ...rest }: TableBlock["props"], axis: "row" | "col", i: number, add: boolean): TableBlock["props"] {
  const put = <T,>(all: T[], one: T) => [...all.slice(0, i), ...(add ? [one] : []), ...all.slice(add ? i : i + 1)];
  const flags = gaps && { gaps: axis === "row" ? put(gaps, cols.map(() => false)) : gaps.map((row) => put(row, false)) };
  if (axis === "row") return { ...rest, cols, cells: put(cells, cols.map(() => "")), ...flags };
  return { ...rest, cells: cells.map((row) => put(row, "")), cols: put(cols, sum(cols) / cols.length), ...flags };
}
// Where the text on a ruling lies in its block: a line of text to a row, the baseline on the row's writing line.
// The box ends below the last row's descenders, so text past the last row is cut off.
// On Karo the field only takes the typing: its letters are unseen and as wide as a square, so the caret stands
// between the squares, and `Lines` draws the characters.
export function writtenStyle(b: RulingBlock, k: number): CSSProperties {
  const { row, at, base, size } = RULINGS[b.props.kind];
  if (!at)
    return {
      fontFamily: "Geist Mono Variable",
      fontSize: size * k,
      lineHeight: `${row * k}px`,
      // Geist Mono's characters are 0.6 em wide.
      letterSpacing: (row - 0.6 * size) * k,
      top: 0,
      width: colsOf(b) * row * k,
      height: rowsOf(b) * row * k,
      whiteSpace: "break-spaces",
      lineBreak: "anywhere",
      color: "transparent",
      caretColor: "#222222",
    };
  const font = FONTS[b.props.font ?? "andika"];
  const top = base - row / 2 - font[2] * size;
  return {
    fontFamily: font[1],
    fontSize: size * k,
    lineHeight: `${row * k}px`,
    top: top * k,
    height: (rowsOf(b) * row - top + Math.max(0, base + size / 2 - row)) * k,
    color: b.props.trace ? "#aaaaaa" : undefined,
  };
}
export const textStyle = (p: TextProps, k: number): CSSProperties => ({
  fontFamily: FONTS[p.font ?? "andika"][1],
  fontSize: p.size * PT * k,
  fontWeight: p.bold ? 700 : 400,
  fontStyle: p.italic ? "italic" : "normal",
  textDecoration: p.underline ? "underline" : "none",
  textAlign: p.align,
  color: p.color,
  lineHeight: p.spacing ?? 1.3,
});
// How far in mm a text keeps its letters from its box's edge, down and across: its border, and the room a
// PowerPoint text box leaves. A text with neither fill nor border stays where sheets saved before had it.
export function inset(p: TextProps, shape: boolean) {
  const [filled, edged] = [p.fill, p.stroke].map((c) => !!c && c !== "none");
  const edge = edged ? (p.strokeWidth ?? 0.5) : 0;
  return shape || filled || edged ? [1.3 + edge, 2.5 + edge, edge] : [0, 0, 0];
}
// The count before each numbered block. Blocks count in reading order, page after page; the letters start over
// after each number, so tasks can have parts.
export function numbers(doc: Doc) {
  const out = new Map<string, number>();
  const count = { "1": 0, a: 0 };
  for (const page of doc.pages)
    for (const b of [...page.blocks].sort((a, b) => a.y - b.y || a.x - b.x)) {
      if (!counts(b.mark)) continue;
      const kind = b.mark.includes("1") ? "1" : "a";
      if (kind === "1") count.a = 0;
      out.set(b.id, ++count[kind]);
    }
  return out;
}
// The `n`th number or letter of a numbering, in its look.
export function Count({ mark, n }: { mark: string; n: number }) {
  const text = mark.replace("o", "").replace(/[1a]/, (c) => (c === "1" ? String(n) : String.fromCharCode(97 + ((n - 1) % 26))));
  return mark.endsWith("o") ? <span className="ring">{text}</span> : <>{text}</>;
}

// The dashes or dots of a stroke so many mm wide. Dots need round ends to show.
const dashes = (dash: TextProps["dash"], width: number) => (dash === "dashed" ? `${width * 4} ${width * 3}` : dash === "dotted" ? `0 ${width * 2.5}` : undefined);
// A fill as CSS: its colour, see-through by its opacity.
const clear = ({ fill, opacity = 1 }: TextProps) =>
  fill?.length === 7 && opacity < 1 ? `rgb(${[1, 3, 5].map((i) => parseInt(fill.slice(i, i + 2), 16)).join(" ")} / ${opacity})` : fill;

// Drawn from the start corner along its own axis; a wide unseen stroke is what a finger grabs. The length stands
// over the middle, turned so it never reads upside down.
function Line({ block, k, solved }: { block: ShapeBlock; k: number; solved: boolean }) {
  const { kind, stroke, strokeWidth, dash, ticks, label } = block.props;
  const [x, y] = [far(block, 1, false) ? block.w : 0, far(block, 0, false) ? block.h : 0];
  const angle = (Math.atan2(block.h - 2 * y, block.w - 2 * x) * 180) / Math.PI;
  const length = Math.hypot(block.w, block.h);
  const head = kind === "line" ? 0 : 2 + strokeWidth * 3;
  // A double arrow has a head at its start too.
  const tail = kind === "double" ? head : 0;
  return (
    <svg>
      <g transform={`scale(${k}) translate(${x} ${y}) rotate(${angle})`} stroke={stroke} strokeWidth={strokeWidth} fill={stroke}>
        <line x2={length} stroke="transparent" strokeWidth={10} />
        <line x1={tail || undefined} x2={length - head} strokeDasharray={dashes(dash, strokeWidth)} strokeLinecap={dash === "dotted" ? "round" : undefined} />
        {head > 0 && <polygon stroke="none" points={`${length},0 ${length - head},${-head / 2} ${length - head},${head / 2}`} />}
        {tail > 0 && <polygon stroke="none" points={`0,0 ${tail},${-tail / 2} ${tail},${tail / 2}`} />}
        {ticks && [...(tail ? [] : [0]), ...(head ? [] : [length])].map((at) => <line key={at} x1={at} x2={at} y1={-1.5} y2={1.5} />)}
        {(label === "show" || (label === "key" && solved)) && (
          <text x={length / 2} y={-2} transform={Math.abs(angle) > 90 ? `rotate(180 ${length / 2} 0)` : undefined} textAnchor="middle" fontFamily="Andika" fontSize={12 * PT} stroke="none" fill={label === "key" ? "#c0392b" : undefined}>
            {(Math.round(length * 10) / 100).toLocaleString("de")} cm
          </text>
        )}
      </g>
    </svg>
  );
}

const UP = { top: "flex-start", middle: "center", bottom: "flex-end" };
// A text or a shape with its text. The editor passes the field the text is typed in.
function Frame({ block, k, solved, children }: { block: TextBlock | ShapeBlock; k: number; solved: boolean; children?: ReactNode }) {
  const p = boxed(block)!;
  const tints = pairOf(p.tints);
  const width = gapWidth(p.gapWidth);
  const words = typeof p.bank === "number" && Number.isFinite(p.bank) ? entries(parasOf(p)) : [];
  const [down, across, edge] = inset(p, block.type === "shape");
  const d = OUTLINES[p.kind!]?.(block.w, block.h, edge / 2);
  // A browser lays a CSS border out on whole pixels: 0.5 mm printed as 0.26 mm. A shadow inside the box is as wide
  // as it is set, so that draws a solid border.
  const solid = !d && !p.dash && edge > 0;
  // Each browser draws the dashes of a CSS border its own way, so a box's dashes are drawn over it, as a line's are.
  // A box no larger than two strokes has no room for them, and keeps the border.
  const ring = !d && !!p.dash && edge > 0 && Math.min(block.w, block.h) > 2 * edge;
  // An outline is no border, so the padding alone keeps the text where a border would.
  const own = d || ring || solid ? 0 : edge;
  // Sheets saved before had a CSS border, which the print rounded down to whole pixels. The padding leaves the room
  // that border took, not the stroke's, so their texts keep their place and break their lines where they did.
  const room = ring || solid ? edge - Math.max(1, Math.floor(edge * k)) / k : own;
  const over: CSSProperties = { position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: -1 };
  const radius = p.kind === "circle" ? "50%" : p.kind === "rounded" ? `${4 * k}px` : 0;
  return (
    <div
      className={classes("frame", tints && "tinted", solved && "solved", width && "even")}
      style={{
        ...textStyle(p, k),
        ...gapVar(width, k),
        background: d ? undefined : clear(p),
        border: own ? `${edge * k}px ${p.dash} ${p.stroke}` : undefined,
        boxShadow: solid ? `inset 0 0 0 ${edge * k}px ${p.stroke}` : undefined,
        borderRadius: radius,
        // A pixel outside the box, so a stroke flush with its edge stays whole (see .frame in styles.css), and round
        // as the box, so a text too long for a circle ends at the circle. A bow under the last line hangs below a
        // box that is just as high as its text.
        clipPath: `inset(${p.syllables ? "-1px -1px calc(-1px - .3em)" : "-1px"} round ${radius})`,
        padding: `${(down - room) * k}px ${(across - room) * k}px`,
        justifyContent: UP[p.valign ?? "top"],
        ...((d || ring) && { position: "relative", isolation: "isolate" }),
      }}
    >
      {d && (
        <svg className="outline" viewBox={`0 0 ${block.w} ${block.h}`} style={{ ...over, ...flipped(block) }}>
          {p.dash && edge > 0 ? (
            <Dashes way={POINTS[p.kind!]!(block.w, block.h, edge / 2)} edge={edge} p={p} fill={p.fill ?? "none"} fillOpacity={p.opacity ?? 1} />
          ) : (
            <Outline d={d} fill={p.fill ?? "none"} fillOpacity={p.opacity ?? 1} stroke={p.stroke ?? "none"} strokeWidth={p.strokeWidth ?? 0.5} strokeDasharray={dashes(p.dash, p.strokeWidth ?? 0.5)} strokeLinecap={p.dash === "dotted" ? "round" : undefined} strokeLinejoin="round" />
          )}
        </svg>
      )}
      {ring && (
        <svg className="dashes" viewBox={`0 0 ${block.w} ${block.h}`} style={over}>
          <Ring w={block.w - edge} h={block.h - edge} edge={edge} p={p} />
        </svg>
      )}
      {children ?? (p.rich ? <Rich paras={p.rich} /> : <p>{p.text}</p>)}
      {words.length > 0 && <Bank words={words} seed={p.bank!} />}
      {(p.syllables || tints) && <Bows block={block} base={FONTS[p.font ?? "andika"][2]} breaks={p.breaks} syllables={p.syllables} tints={tints} tintsAcross={p.tintsAcross} solved={solved} />}
    </div>
  );
}

// The classes of an element, from the names that are set.
const classes = (...names: (string | false | 0 | undefined)[]) => names.filter(Boolean).join(" ");
// Every gap of a block is at least this many mm wide: a finite number above 0, at most 200. Else none.
const gapWidth = (mm: unknown) => (typeof mm === "number" && Number.isFinite(mm) && mm > 0 ? Math.min(mm, 200) : 0);
// The width in px of a block's gaps, for the CSS of `.even .gap`.
const gapVar = (mm: number, k: number) => (mm ? ({ "--gap": `${mm * k}px` } as CSSProperties) : {});
// The box of the solution words under a text: each word once, in the seeded order of its block.
function Bank({ words, seed }: { words: string[]; seed: number }) {
  return <div className="bank">{shuffled(words, seed).map((word, i) => <span key={i}>{word}</span>)}</div>;
}

// The dashes of a box's border. The middle of the stroke is `w` by `h` mm, half the stroke's width inside the box.
function Ring({ w, h, edge, p }: { w: number; h: number; edge: number; p: TextProps }) {
  const r = p.kind === "rounded" ? Math.max(0, Math.min(4 - edge / 2, w / 2, h / 2)) : 0;
  const [rx, ry] = p.kind === "circle" ? [w / 2, h / 2] : [r, r];
  return <Dashes way={around(edge / 2, edge / 2, edge / 2 + w, edge / 2 + h, rx, ry)} edge={edge} p={p} fill="none" />;
}
// The way round a box with round corners, as points: clockwise, and it ends where the top left corner does. The
// browser and the PDF each measure the way along a curve their own way, and the dots after one printed further
// along than the screen had them. So a quarter turn is 45 short lines: those measure the same everywhere. A
// bubble's `tail` lies in the foot.
function around(left: number, top: number, right: number, low: number, rx: number, ry: number, tail: number[][] = []) {
  const turn = (x: number, y: number, from: number) =>
    Array.from({ length: rx ? 46 : 1 }, (_, i) => [x + rx * Math.sin(((from + i / 45) * Math.PI) / 2), y - ry * Math.cos(((from + i / 45) * Math.PI) / 2)]);
  return [...turn(right - rx, top + ry, 0), ...turn(right - rx, low - ry, 1), ...tail, ...turn(left + rx, low - ry, 2), ...turn(left + rx, top + ry, 3)];
}
// The dashes along a way round, which starts at its last point: a box with square corners is a `<rect>`, a triangle
// and a star start at their last corner. They stretch or shrink a little so that a whole number of them goes around:
// the last one meets the first.
function Dashes({ way, edge, p, ...look }: { way: number[][]; edge: number; p: TextProps } & SVGAttributes<SVGElement>) {
  const length = way.reduce((sum, [x, y], i) => sum + Math.hypot(x - way.at(i - 1)![0], y - way.at(i - 1)![1]), 0);
  const each = edge * (p.dash === "dashed" ? 7 : 2.5);
  const fit = length / Math.max(1, Math.round(length / each)) / each;
  // A dash that starts right where the way does has the end of the last one before it, a hair long: a doubled dot
  // in print, and on the screen a join that fills a box's corner. So the way starts a hair inside the last gap.
  const all = { stroke: p.stroke, strokeWidth: edge, strokeDasharray: dashes(p.dash, edge * fit), strokeDashoffset: -edge / 100, strokeLinecap: p.dash === "dotted" ? ("round" as const) : undefined, ...look };
  if (way.length !== 4) return <path d={`M${[way.at(-1), ...way.slice(0, -1)].join(" L")} Z`} strokeLinejoin="round" {...all} />;
  // Four points are a box's own corners: no outline has four.
  const [[right], [, low], , [left, top]] = way;
  return <rect x={left} y={top} width={right - left} height={low - top} {...all} />;
}

// The outlines CSS cannot draw, in a box `w` by `h` mm and `e` mm inside it, so the stroke stays in the box. Each
// one's way round as points, which its dashes go along. The triangle has its tip at the top. The star is a
// five-point one stretched to the box. The bubble is a round box over the top three quarters, with a tail down to
// the lower left.
const POINTS: Partial<Record<Kind, (w: number, h: number, e: number) => number[][]>> = {
  triangle: (w, h, e) => [[w / 2, e], [w - e, h - e], [e, h - e]],
  star: (w, h, e) =>
    Array.from({ length: 10 }, (_, i) => {
      const [r, a] = [i % 2 ? 0.38 : 1, (i * Math.PI) / 5];
      // An upright star reaches sin 72° to each side, and cos 36° below its middle.
      return [e + (w - 2 * e) * (0.5 + (r * Math.sin(a)) / 1.902), e + ((h - 2 * e) * (1 - r * Math.cos(a))) / 1.809];
    }),
  bubble: (w, h, e) => {
    const [r, low] = [Math.min(4, w / 5, h / 4), e + 0.75 * (h - 2 * e)];
    return around(e, e, w - e, low, r, r, [[0.4 * w, low], [0.2 * w, h - e], [0.25 * w, low]]);
  },
};
// Drawn solid: the same points for a polygon, or a path with true arcs.
const OUTLINES: Partial<Record<Kind, (w: number, h: number, e: number) => string>> = {
  triangle: (w, h, e) => POINTS.triangle!(w, h, e).join(" "),
  star: (w, h, e) => POINTS.star!(w, h, e).join(" "),
  bubble: (w, h, e) => {
    const [r, right, low] = [Math.min(4, w / 5, h / 4), w - e, e + 0.75 * (h - 2 * e)];
    const arc = (x: number, y: number) => `A${r},${r} 0 0 1 ${x},${y}`;
    return `M${e + r},${e} H${right - r} ${arc(right, e + r)} V${low - r} ${arc(right - r, low)} H${0.4 * w} L${0.2 * w},${h - e} L${0.25 * w},${low} H${e + r} ${arc(e, low - r)} V${e + r} ${arc(e + r, e)} Z`;
  },
};
// The one element of an outline: a path when `d` starts as one.
const Outline = ({ d, ...look }: { d: string } & SVGAttributes<SVGElement>) => (d[0] === "M" ? <path d={d} {...look} /> : <polygon points={d} {...look} />);

// The module that splits words into syllables holds the hyphenation patterns, so it loads only once a block asks
// for syllables. Until it is there such a block shows its words without bows.
type Splitter = typeof import("./syllables");
let splitter: Splitter | undefined;
let loading: Promise<Splitter> | undefined;
const waiting = new Set<() => void>();
export const splitting = () =>
  (loading ??= import("./syllables").then(
    (module) => {
      splitter = module;
      waiting.forEach((tell) => tell());
      return module;
    },
    // A load that failed is tried again by the next block that asks.
    (failed) => {
      loading = undefined;
      throw failed;
    },
  ));
const listen = (tell: () => void) => (waiting.add(tell), () => void waiting.delete(tell));
// The splitter once it is loaded, for a block with `on`; it loads at the first block that asks.
export function useSplitter(on?: boolean) {
  const module = useSyncExternalStore(listen, () => splitter);
  useEffect(() => void (on && splitting().catch(() => {})), [on]);
  return on ? module : undefined;
}
const SVG = "http://www.w3.org/2000/svg";
// A sheet may come from anywhere: a pair is two colours of six hex digits, in lower case, and anything else is none.
export function pairOf(tints: unknown): Tints | undefined {
  if (!Array.isArray(tints) || tints.length !== 2) return undefined;
  const [a, b] = tints;
  const hex = (c: unknown): c is string => typeof c === "string" && /^#[0-9a-f]{6}$/i.test(c);
  return hex(a) && hex(b) ? [a.toLowerCase(), b.toLowerCase()] : undefined;
}
// Each colour is one highlight in the document's registry, named by the colour. Its rule goes into a style element
// the module makes at the first one. A browser without the registry paints no colours.
let tinting: HTMLStyleElement | undefined;
const rules = new Map<Highlight, [string, Text]>();
function highlight(colour: string): Highlight | undefined {
  if (!("highlights" in CSS)) return undefined;
  const name = `tint-${colour.slice(1).toLowerCase()}`;
  let mark = CSS.highlights.get(name);
  if (!mark) {
    mark = new Highlight();
    CSS.highlights.set(name, mark);
    tinting ??= document.head.appendChild(document.createElement("style"));
    const rule = document.createTextNode(`::highlight(${name}){color:${colour}}`);
    tinting.append(rule);
    rules.set(mark, [name, rule]);
  }
  return mark;
}
// A range a block coloured, in the highlight it went into: the block takes it back before it draws anew. A colour
// that no letter has any more goes with its rule: a drag through the colour field passes hundreds of them.
type Mark = [Highlight, globalThis.Range];
const unmark = (marks: Mark[]) =>
  marks.forEach(([mark, range]) => {
    mark.delete(range);
    const [name, rule] = rules.get(mark) ?? [];
    if (mark.size || !rule) return;
    CSS.highlights.delete(name!);
    rule.remove();
    rules.delete(mark);
  });
type Draw = { base: number; breaks?: Breaks; syllables?: boolean; tints?: Tints; tintsAcross?: boolean; solved?: boolean };
// Draws a bow under each syllable of the text beside `svg`: every paragraph of a frame, of a table's cells and of
// the field a text is typed in. The words stay as they are. A span around a syllable would move its letters:
// WebKit shapes each text node alone, which costs the joins and the kerning of a school script. So each syllable
// is measured where it stands and its bow drawn over it, in the block's own pixels: the zoom is divided out, and a
// turned block is measured level. The same pass colours the syllables in turn (Silbenfarbe) and returns the ranges
// it coloured, so a bow and its colour always fall on the same syllable.
function bows(svg: SVGSVGElement, module: Splitter, { base, breaks, syllables, tints, tintsAcross: across }: Draw): Mark[] {
  const host = svg.parentElement!;
  const block = host.closest<HTMLElement>(".block");
  const turn = block?.style.transform;
  if (turn) block!.style.transform = "none";
  const { left, top } = svg.getBoundingClientRect();
  const scale = host.getBoundingClientRect().width / host.offsetWidth;
  const drawn: SVGPathElement[] = [];
  const marks: Mark[] = [];
  // The turn of the colours: `count` syllables so far, and the cell the last paragraph lay in.
  let cell: Element | null | undefined;
  let count = 0;
  // A table's open cell holds its text unseen around the field: the field's paragraphs are the ones to draw.
  for (const p of scale ? host.querySelectorAll("p") : [])
    if (!p.querySelector("p")) {
      // A paragraph starts the turn anew, unless the turn runs across the text: then only a new cell does.
      if (!across || p.closest("[data-cell]") !== cell) count = 0;
      cell = p.closest("[data-cell]");
      const nodes: Text[] = [];
      const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      // The field of a table's open cell holds the cell's text once more: its own letters are not the ones to count.
      while (walk.nextNode()) if (walk.currentNode.parentElement!.tagName !== "TEXTAREA") nodes.push(walk.currentNode as Text);
      // Where each text node starts in the paragraph's text: a word is split whole, whatever runs it lies in.
      const starts = nodes.map(((at) => (node) => (at += node.length) - node.length)(0));
      const spot = (at: number) => {
        const i = starts.filter((start) => start <= at).length - 1;
        return [nodes[i], at - starts[i]] as const;
      };
      // A text node is hand coloured when an element between it and the paragraph has a colour of its own.
      const handed = (node: Text) => {
        for (let el = node.parentElement; el && el !== p; el = el.parentElement) if (el.style.color) return true;
        return false;
      };
      let at = 0;
      let word: number | undefined;
      for (const piece of module.pieces(nodes.map((node) => node.data).join(""), breaks)) {
        const from = at;
        at += piece.text.length;
        if (!piece.syl) continue;
        if (piece.word !== word) {
          word = piece.word;
          if (!across) count = 0;
        }
        const colour = tints?.[count++ % 2];
        const [first, start] = spot(from);
        // The end lies in the node of the syllable's last letter, not at the start of the next.
        const [last, stop] = spot(from + module.shown(piece.text).length - 1);
        // A gap shows neither bow nor colour, so the hidden letters stay hidden, a syllable that
        // starts or ends in a gap too; the answer key shows both.
        const hidden = first.parentElement!.closest(".gap") || last.parentElement!.closest(".gap");
        if (hidden && !host.closest(".solved")) continue;
        // A hand colour keeps its letters: each stretch of the syllable without one gets a range of its own.
        const mark = colour ? highlight(colour) : undefined;
        if (mark) {
          const stretch: globalThis.Range[] = [];
          let open: globalThis.Range | undefined;
          for (const node of nodes.slice(nodes.indexOf(first), nodes.indexOf(last) + 1)) {
            if (handed(node)) open = undefined;
            else {
              if (!open) {
                open = document.createRange();
                open.setStart(node, node === first ? start : 0);
                stretch.push(open);
              }
              open.setEnd(node, node === last ? stop + 1 : node.length);
            }
          }
          for (const part of stretch) {
            mark.add(part);
            marks.push([mark, part]);
          }
        }
        if (!syllables) continue;
        const range = document.createRange();
        range.setStart(first, start);
        range.setEnd(last, stop + 1);
        // A rect for each line the syllable stands in: one, unless a word too long for its line broke in it. A
        // syllable that two runs share has a rect for each run, side by side, and still one bow.
        const lines: { left: number; right: number; top: number; bottom: number }[] = [];
        for (const { left, right, top, bottom } of range.getClientRects()) {
          const line = lines.find((line) => (top + bottom) / 2 > line.top && (top + bottom) / 2 < line.bottom);
          if (line) [line.left, line.right] = [Math.min(line.left, left), Math.max(line.right, right)];
          else if (right > left) lines.push({ left, right, top, bottom });
        }
        const look = getComputedStyle(first.parentElement!);
        const em = parseFloat(look.fontSize);
        for (const line of lines) {
          // The baseline lies `base` em below the middle of the letters' box, whatever the line spacing. The bow
          // ends .04em inside the syllable, so two bows never meet, .1em below the baseline, and hangs .16em
          // lower in its middle; under a narrow letter it is flatter.
          const [x, to] = [(line.left - left) / scale + 0.04 * em, (line.right - left) / scale - 0.04 * em];
          const y = ((line.top + line.bottom) / 2 - top) / scale + (base + 0.1) * em;
          const deep = Math.min(0.16 * em, (to - x) / 2);
          const path = document.createElementNS(SVG, "path");
          path.setAttribute("class", "syl");
          path.dataset.syl = module.plain(piece.text);
          // A curve hangs half as deep as the point it is drawn towards.
          path.setAttribute("d", `M${x.toFixed(2)},${y.toFixed(2)} Q${((x + to) / 2).toFixed(2)},${(y + 2 * deep).toFixed(2)} ${to.toFixed(2)},${y.toFixed(2)}`);
          // A bow takes the colour of its syllable, where the syllable's first letter has no hand colour of its own.
          path.setAttribute("stroke", colour && !handed(first) ? colour : look.color);
          // As thick as the letters ask, and never thinner than 0.15 mm, which still prints.
          path.setAttribute("stroke-width", `${Math.max(0.05 * em, 0.15 * K)}`);
          drawn.push(path);
        }
      }
    }
  if (turn) block!.style.transform = turn;
  svg.replaceChildren(...drawn);
  svg.classList.remove("unsplit");
  return marks;
}
// The bows of a block that asks for them. `base` is how far the font's baseline lies below the middle of a line,
// in em. They are measured anew only when something moved a letter or gave it another colour: `block` is the
// block as the sheet holds it, and a pick, or a letter typed into another block, leaves it the same. What React
// does not hold is watched: the text as the teacher types it, the block's size while it is dragged, and a font
// that comes in. `unsplit` stands while the bows are not those of the text shown, so the PDF, a test and a picture
// of the page can wait for them. It draws the bows when `syllables` is on, and the colours when there is a pair of
// `tints`; with the colours alone it draws no bow, and its ranges go when the block goes or its colours change.
function Bows({ block, ...how }: { block: Box & { props: object } } & Draw) {
  const { solved } = how;
  const module = useSplitter(true);
  const svg = useRef<SVGSVGElement>(null);
  const tools = useRef({ draw: () => {}, seen: () => {} });
  const size = useRef([0, 0]);
  const marks = useRef<Mark[]>([]);
  // With no splitter the block has no bows, and says it is done: a page prints without bows sooner than not at
  // all. A load that failed is asked for again here, at the next change of the block and not before, so a server
  // that is down is not asked with every frame. Chromium keeps a failed module for as long as the page lives and
  // asks no server again, so there the bows come with a reload.
  const draw = () => {
    const own = svg.current!;
    size.current = [own.parentElement!.offsetWidth, own.parentElement!.offsetHeight];
    // The old ranges go once the new ones are in: a colour that stays is never without a letter, and keeps its rule.
    const old = marks.current;
    marks.current = module ? bows(own, module, how) : [];
    unmark(old);
    if (!module)
      splitting().catch(() => {
        own.replaceChildren();
        own.classList.remove("unsplit");
      });
  };
  useLayoutEffect(() => {
    const own = svg.current!;
    let frame = 0;
    // One measure a frame, however much changed.
    const later = () => {
      own.classList.add("unsplit");
      frame ||= requestAnimationFrame(() => tools.current.draw());
    };
    // A size that React set is drawn for already.
    const resized = new ResizeObserver(() => (own.parentElement!.offsetWidth !== size.current[0] || own.parentElement!.offsetHeight !== size.current[1]) && later());
    resized.observe(own.parentElement!);
    // The bows drawn are a change too, and not one to draw anew for.
    const changed = new MutationObserver((records) => records.some((record) => !own.contains(record.target)) && later());
    changed.observe(own.parentElement!, { characterData: true, childList: true, subtree: true });
    document.fonts.addEventListener("loadingdone", later);
    // What React just wrote into the text is drawn for at once, so no frame shows old bows and none measures twice.
    tools.current.seen = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      changed.takeRecords();
    };
    return () => {
      cancelAnimationFrame(frame);
      resized.disconnect();
      changed.disconnect();
      document.fonts.removeEventListener("loadingdone", later);
      unmark(marks.current);
    };
  }, []);
  useLayoutEffect(() => {
    tools.current.draw = () => {
      tools.current.seen();
      draw();
    };
    svg.current!.classList.add("unsplit");
    tools.current.draw();
    // The place of a block moves no letter in it.
  }, [module, block.props, block.w, block.h, block.angle, solved]);
  return <svg ref={svg} className="bows unsplit" aria-hidden />;
}
// Resolves once every block's bows are drawn. The PDF waits for it.
export const bowed = () =>
  new Promise<void>((done) => {
    const look = () => (document.querySelector(".unsplit") ? requestAnimationFrame(look) : done());
    requestAnimationFrame(look);
  });

// The runs of a paragraph in groups: consecutive gap runs share one group, every other run has one of its own.
const runGroups = (runs: Run[]) =>
  runs.reduce<Run[][]>((all, r) => {
    const last = all.at(-1);
    if (r.gap === true && last?.[0].gap === true) last.push(r);
    else all.push([r]);
    return all;
  }, []);

// A text's paragraphs, in the markup the editor's field makes of them, so one stylesheet draws both. What a sheet
// stores is drawn as text alone, never as markup of its own.
function Rich({ paras }: { paras: Para[] }) {
  const or = (set: boolean | undefined, on: string, off: string) => (set === undefined ? undefined : set ? on : off);
  const run = ({ text, bold, italic, underline, color }: Run, key: number) => (
    <span key={key} style={{ fontWeight: or(bold, "700", "400"), fontStyle: or(italic, "italic", "normal"), textDecoration: underline ? "underline" : undefined, color }}>
      {text}
    </span>
  );
  return (
    <div className="rich">
      {paras.map((para, i) => (
        <p key={i} data-list={para.list} data-level={para.level || undefined}>
          {/* Consecutive gap runs make one gap: its outer span draws the line, its inner one holds the words. */}
          {runGroups(para.runs).map((group, g) =>
            group[0].gap === true ? (
              <span key={g} className="gap" data-gap="true">
                <span>{group.map((r, j) => run(r, j))}</span>
              </span>
            ) : (
              run(group[0], g)
            ),
          )}
          {/* A paragraph with no text is still a line high. */}
          {!para.runs.length && <br />}
        </p>
      ))}
    </div>
  );
}

// Drawn in mm: the SVG's own scale takes it to the block's size. The editor passes the field the text is typed in.
function Lines({ block, k, children }: { block: RulingBlock; k: number; children?: ReactNode }) {
  const { row, at, band, size } = RULINGS[block.props.kind];
  const { text = "", trace } = block.props;
  const rows = rowsOf(block);
  const cols = colsOf(block);
  const each = (n: number) => Array.from({ length: n }, (_, i) => i * row);
  const ys = at ? each(rows).flatMap((top) => at.map((y) => top + y)) : each(rows + 1);
  return (
    <div>
      <svg className="ruling" viewBox={`0 0 ${block.w} ${block.h}`} stroke={block.props.color} strokeWidth={0.2}>
        {/* The middle band lies between a row's second and third line. */}
        {band > 0 && each(rows).map((top) => <rect key={top} y={top + at![1]} width={block.w} height={band} fill={block.props.color} fillOpacity={0.12} stroke="none" />)}
        {ys.map((y) => (
          <line key={y} x2={at ? block.w : cols * row} y1={y} y2={y} />
        ))}
        {!at && each(cols + 1).map((x) => <line key={x} x1={x} x2={x} y2={rows * row} />)}
        {!at && cols > 0 && squares(text, cols).map(([x, y, ch], i) => y < rows && (
          <text key={-i - 1} x={(x + 0.5) * row} y={(y + 0.5) * row} fontFamily="Andika" fontSize={size} textAnchor="middle" dominantBaseline="central" stroke="none" fill={trace ? "#aaaaaa" : "currentColor"}>
            {ch}
          </text>
        ))}
      </svg>
      {children ?? (at && text && <p className="written" style={writtenStyle(block, k)}>{text}</p>)}
    </div>
  );
}

// The lines are the borders of the cells, so they close at every corner. The rows have no set height: the grid
// makes each as high as its cells need and stretches them all by the same share of what is left. A text lies in
// the middle of its cell's height. The editor passes the field for the cell `at`, counted row by row: the cell's
// own text, unseen, keeps the field as high as its lines.
function Table({ block, k, at, solved, children }: { block: TableBlock; k: number; at?: number; solved: boolean; children?: ReactNode }) {
  const { cells, cols, line, head, syllables, breaks, tintsAcross, gaps } = block.props;
  const tints = pairOf(block.props.tints);
  const width = gapWidth(block.props.gapWidth);
  const words = typeof block.props.bank === "number" && Number.isFinite(block.props.bank) ? cellEntries(cells, gaps) : [];
  const style = {
    ...textStyle({ text: "", ...block.props }, k),
    borderColor: line,
    gridTemplateColumns: cols.map((c) => `minmax(0, ${c}fr)`).join(" "),
    "--edge": `${0.25 * k}px`,
    ...gapVar(width, k),
  };
  // A gap cell holds its text as a gap does; the open cell's field goes after it.
  const wrap = (text: string, i: number) => (gaps?.[Math.floor(i / cols.length)]?.[i % cols.length] === true ? <span className="gap" data-gap="true"><span>{text}</span></span> : text);
  return (
    <div className={classes("table", tints && "tinted", solved && "solved", width && "even")} style={style as CSSProperties}>
      {cells.flat().map((text, i) => (
        <div key={i} data-cell={i} style={{ fontWeight: head && i < cols.length ? 700 : undefined }}>
          {i === at ? <p className="open">{wrap(text, i)}&#8203;{children}</p> : <p>{wrap(text, i)}</p>}
        </div>
      ))}
      {(syllables || tints) && <Bows block={block} base={FONTS[block.props.font ?? "andika"][2]} breaks={breaks} syllables={syllables} tints={tints} tintsAcross={tintsAcross} solved={solved} />}
      {words.length > 0 && <Bank words={words} seed={block.props.bank!} />}
    </div>
  );
}

// A number of an exercise, or the gap in its place. The answer key fills the gap.
function Part({ e, part, solved }: { e: Exercise; part: "a" | "b" | "result" | "rest"; solved: boolean }) {
  const gap = part === "rest" || part === (e.hide ?? "result");
  return gap ? <u>{solved && e[part]}</u> : <>{e[part]}</>;
}

// A written exercise: squared paper with a character to a square. All of a block's exercises get the same paper.
function Karo({ grid, cols, rows, k, solved }: { grid: Grid; cols: number; rows: number; k: number; solved: boolean }) {
  const each = (n: number) => Array.from({ length: n + 1 }, (_, i) => i);
  return (
    <svg width={cols * KARO * k} height={rows * KARO * k} viewBox={`0 0 ${cols} ${rows}`}>
      <g stroke="#9db4c8" strokeWidth={0.03}>
        {each(cols).map((x) => <line key={x} x1={x} x2={x} y2={rows} />)}
        {each(rows).map((y) => <line key={-y - 1} x2={cols} y1={y} y2={y} />)}
      </g>
      {grid.lines.map(([x1, x2, y, kind], i) => (solved || !kind) && <line key={i} className={kind ? "answer" : ""} x1={x1} x2={x2} y1={y} y2={y} stroke="currentColor" strokeWidth={0.08} />)}
      {grid.cells.map(([x, y, ch, kind], i) => (solved || !kind) && (
        <text key={i} className={kind ? "answer" : ""} x={x + 0.5} y={y + 0.5} fontSize={kind === 2 ? 0.45 : 0.75} textAnchor="middle" dominantBaseline="central" fill="currentColor">
          {ch}
        </text>
      ))}
    </svg>
  );
}

function Maths({ block, k, solved }: { block: MathsBlock; k: number; solved: boolean }) {
  const p = block.props;
  const cols = Math.max(0, ...p.exercises.map((e) => e.grid?.cols ?? 0));
  const rows = Math.max(0, ...p.exercises.map((e) => e.grid?.rows ?? 0));
  const style = { fontSize: p.size * PT * k, gridTemplateColumns: `repeat(${p.columns}, 1fr)`, "--gap": `${String(p.max).length + 1.5}ch` };
  return (
    <div className={`maths ${p.format}${solved ? " solved" : ""}`} style={style as CSSProperties}>
      {p.exercises.map((e, i) => (
        <div key={i}>
          {p.numbering && <b><Count mark={p.numbering} n={i + 1} /></b>}
          {e.grid ? (
            <Karo grid={e.grid} cols={cols} rows={rows} k={k} solved={solved} />
          ) : (
            <span>
              <Part e={e} part="a" solved={solved} /> {SIGNS[e.op]} <Part e={e} part="b" solved={solved} /> = <Part e={e} part="result" solved={solved} />
              {e.rest > 0 && <> R <Part e={e} part="rest" solved={solved} /></>}
            </span>
          )}
        </div>
      ))}
      {!p.exercises.length && <span className="hint">Keine Aufgabe möglich</span>}
    </div>
  );
}

// What a block shows, at `k` pixels per mm. Sizes inside a block are in em of a font size set to the scale.
// `solved` fills in the answers of the maths exercises. `at` is the cell of a table that the editor's field is for.
export function Draw({ block, k, solved = false, at, children }: { block: Block; k: number; solved?: boolean; at?: number; children?: ReactNode }) {
  if (block.type === "maths") return <Maths block={block} k={k} solved={solved} />;
  if (block.type === "table") return <Table block={block} k={k} at={at} solved={solved}>{children}</Table>;
  if (block.type === "text" || (block.type === "shape" && !isLine(block))) return <Frame block={block} k={k} solved={solved}>{children}</Frame>;
  if (block.type === "shape") return <Line block={block} k={k} solved={solved} />;
  if (block.type === "ruling") return <Lines block={block} k={k}>{children}</Lines>;
  if (block.type === "symbol") return <img src={symbol(block.props.code)} alt="" draggable={false} style={flipped(block)} />;
  // While a name line is written in, `children` holds one field for each word, in the word's place of the line.
  if (block.type === "name")
    return (
      <div className="fields" style={{ fontSize: 12 * PT * k }}>
        {(block.props.fields ?? FIELDS).map((field, i) => (
          <span key={i}>
            {field}:{(children as ReactNode[] | undefined)?.[i] ?? <i />}
          </span>
        ))}
      </div>
    );
  // The words' row is the box between its lines, in an even count of pixels: so they stand whole pixels below the
  // box's top. A part of a pixel Chromium rounds one way on a sharp screen and another in print.
  // While the score is written in, `children` is its field in place of the number.
  if (block.type === "points")
    return (
      <div className="points" style={{ fontSize: 12 * PT * k, lineHeight: `${2 * Math.round((block.h * k) / 2 - 1)}px` }}>
        / {children ?? block.props.max} Punkte
      </div>
    );
  const [l, t, r, b] = block.props.cut;
  const [w, h] = [1 - l - r, 1 - t - b];
  // The picture clips itself at its cut. The box clips on whole pixels: alone it let a strip of the part that is
  // cut off, up to a pixel wide, show beyond the cut and print. A whole picture is left as it was.
  const clipPath = l || t || r || b ? `inset(${[t, r, b, l].map((share) => `${share * 100}%`).join(" ")})` : undefined;
  return (
    <div className="picture" style={flipped(block)}>
      <img
        src={`/api/uploads/${block.props.upload}`}
        alt=""
        draggable={false}
        style={{ width: `${100 / w}%`, height: `${100 / h}%`, left: `${(-100 * l) / w}%`, top: `${(-100 * t) / h}%`, clipPath }}
      />
    </div>
  );
}

// A score as it is typed: a whole number from 1 to 999, or else none.
export const score = (text: string) => (/^\s*\d{1,3}\s*$/.test(text) && +text >= 1 ? +text : undefined);

// The field of a score, in a box or in the panel. However it ends, except by Escape, it keeps the typed score when that is
// a whole number from 1 to 999; any other text leaves the old one. `change` gets the score and makes no step when the
// sheet has it already. `end` runs after Enter, `blur` on leaving the field.
export function ScoreInput({ max, change, end, blur }: { max: number; change: (max: number) => void; end?: () => void; blur?: (e: FocusEvent<HTMLInputElement>) => void }) {
  const [draft, setDraft] = useState(String(max));
  // What is typed, the score shown by the sheet, the score last sent to it, and whether Escape ended the field.
  const typed = useRef(String(max));
  const shown = useRef(max);
  const sent = useRef<number>(undefined);
  const off = useRef(false);
  const latest = useRef({ change, end, blur });
  latest.current = { change, end, blur };
  shown.current = max;
  useEffect(() => {
    typed.current = String(max);
    sent.current = undefined;
    setDraft(String(max));
  }, [max]);
  // Runs on Enter, on a blur and when the field goes, so a score is kept once for each way the field ends.
  function keep() {
    if (off.current) return;
    const next = score(typed.current);
    if (next === undefined) {
      typed.current = String(shown.current);
      return setDraft(typed.current);
    }
    if (next === sent.current) return;
    sent.current = next;
    latest.current.change(next);
  }
  // The field goes on the press that ends it, which takes no blur with it: so its score is kept as it leaves.
  useEffect(() => keep, []);
  return (
    <input
      className="score"
      inputMode="numeric"
      aria-label="Punkte"
      value={draft}
      onChange={(e) => {
        typed.current = e.target.value;
        setDraft(e.target.value);
      }}
      onFocus={() => (off.current = false)}
      onBlur={(e) => {
        keep();
        latest.current.blur?.(e);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === "F2") {
          keep();
          latest.current.end?.();
        }
        if (e.key !== "Escape") return;
        off.current = true;
        typed.current = String(shown.current);
        setDraft(typed.current);
        e.currentTarget.blur();
      }}
    />
  );
}

// A block's numbering stands to the left of its box, so the box keeps its place and its snap lines. `n` is the
// number of a counted block; a symbol has none. Beside a text it starts as far down as the text's first line, and
// beside a line its middle is level with the line's start.
export function Mark({ block, k, n }: { block: Block; k: number; n?: number }) {
  if (!block.mark) return null;
  const style = textStyle(boxed(block) ?? { text: "", size: 14, align: "left" }, k);
  return (
    <b className="mark" style={{ ...style, textDecoration: "none", paddingTop: block.type === "text" ? inset(block.props, false)[0] * k : 0, translate: isLine(block) ? "0 -50%" : undefined }}>
      {n ? <Count mark={block.mark} n={n} /> : <img src={symbol(block.mark)} alt="" />}
    </b>
  );
}

// A page with nothing to take hold of, at `k` pixels per mm: page one drawn small in the list, every page at its
// true size in the PDF, where it needs no transform. The answer key says on each page that it is one.
export function Paper({ doc, k, page = 0, solved = false }: { doc: Doc; k: number; page?: number; solved?: boolean }) {
  const all = read(doc);
  const ns = numbers(all);
  const [w, h] = sizeOf(all, page);
  return (
    <div className={w > h ? "paper wide" : "paper"} style={{ width: w * k, height: h * k }}>
      <div className="scaled" style={{ width: w * K, height: h * K, transform: k === K ? undefined : `scale(${k / K})` }}>
        {all.pages[page].blocks.map((b) => (
          <div key={b.id} className="block" style={{ left: b.x * K, top: b.y * K, width: b.w * K, height: b.h * K, zIndex: b.z, ...turned(b) }}>
            <Draw block={b} k={K} solved={solved} />
            <Mark block={b} k={K} n={ns.get(b.id)} />
          </div>
        ))}
        {solved && <b className="key" style={{ top: 5 * K, right: 15 * K, fontSize: 11 * PT * K }}>Lösungen</b>}
      </div>
    </div>
  );
}
