// The sheet document and how a page of it draws, shared by the editor, the list's thumbnails and the PDF.
import { Fragment, createContext, useContext, useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore, type CSSProperties, type FocusEvent, type ReactNode, type SVGAttributes } from "react";
import type { Breaks } from "./syllables";
import { heightsOf, rectOf, spansOf, type Span } from "./cells";
import { edged, linesOf, type Lines, type Pen } from "./edges";
import { edgesSpliced } from "./borders";
import { cellEntries, entries, shuffled } from "./bank";
import { mixed, type Part } from "./scramble";
import { holed } from "./holes";
import { laid, sane } from "./suchsel";
import { at, layout as wallLayout, made as walled, sane as saneWall } from "./zahlenmauer";
import { FIELDS as RECHEN_FIELDS, layout, made as drawnRechen, sane as saneRechen, type RechendreieckProps } from "./rechendreieck";
import { TINT, dotAt, made as drawnFeld, sane as saneFeld, type HunderterfeldProps } from "./hunderterfeld";
import { CELL_H, CELL_W, INK as UHR_INK, RED, hands, sane as saneUhr, timesOf, written, type UhrProps } from "./uhr";
import { checked, lettersOf, sane as saneSelbst, type SelbstkontrolleProps } from "./selbstkontrolle";
import { LEFT as STRAHL_LEFT, arrowXs, below, boxUnder, made as drawnStrahl, sane as saneStrahl, xOf, type ZahlenstrahlProps } from "./zahlenstrahl";
import { decimal, decimalsOf, GAP } from "./decimal";
import { Scissors } from "lucide-react";

// One page's blocks, as the sheet document stores them: mm from the page's top-left corner. `mark` is the numbering
// before a block: a counting one such as "1.", "a)" or "(1)", or a symbol's code. `angle` turns the box about its
// centre, in degrees clockwise from 0 up to 360. `flipX` and `flipY` mirror a picture or a symbol in its box.
// `keep` is set when the block keeps its width over its height, as PowerPoint's 'Lock aspect ratio'. Absent means off.
export type Box = { id: string; x: number; y: number; w: number; h: number; z: number; locked: boolean; mark?: string; group?: string[]; angle?: number; flipX?: boolean; flipY?: boolean; keep?: boolean };
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
// `lines` numbers the lines of the text as they break, left of the box (Zeilennummern): every line with 1, every fifth
// with 5. Absent is off. `linesFrom` is the number of the first line (Beginnt bei): absent is 1, and an integer 1 to
// 9999 is the other numbers, anything else counts as 1. The numbers stand on the lines whose number is a multiple of `lines`.
// `mix` is the seed of the scrambled words (Schüttelwörter): each word shows its letters in another order, the same
// on every draw. `mixFirst` keeps each word's first letter in place, `mixCaps` sets the letters in capitals. `mixLine`
// puts a line after each mixed word ("after") or under it ("under"), which the pupil writes the word on. The answer
// key shows the word the teacher typed on the line, or in place of the mixed word when there is no line.
// Sheets saved before have none of these.
// `list` makes the text draw the sheet's Lernwörter, one word to a paragraph (Text aus Lernwörtern); its own `text` and
// `rich` rest. `listCols` sets the words in 1 to 4 columns, which fill column by column. `holes` is the Lückenwörter
// mode of a linked text: letters give way to gaps, chosen from `holeSeed`. Only a linked text has these looks.
export type TextProps = { text: string; rich?: Para[]; syllables?: boolean; breaks?: Breaks; tints?: Tints; tintsAcross?: boolean; gapWidth?: number; bank?: number; lines?: number; linesFrom?: number; mix?: number; mixFirst?: boolean; mixCaps?: boolean; mixLine?: "after" | "under"; list?: boolean; listCols?: number; holes?: "one" | "second" | "vowels"; holeSeed?: number; size: number; align: Align; font?: Font; bold?: boolean; italic?: boolean; underline?: boolean; color?: string; spacing?: number; valign?: Valign; kind?: Kind; fill?: string; opacity?: number; stroke?: string; strokeOpacity?: number; inside?: boolean; strokeWidth?: number; dash?: "dashed" | "dotted"; trace?: boolean | "outline" | "dotted"; fade?: Fade };
export type TextBlock = Box & { type: "text"; props: TextProps };
// A shape can hold text: centred and in the middle unless set otherwise. A line or arrow runs from the corner
// `from` of its box to the opposite one. It can have a tick at each end and say how long it is, on the sheet
// ("show") or on the answer key alone ("key").
export type ShapeBlock = Box & { type: "shape"; props: Partial<TextProps> & { kind: Kind; fill: string; stroke: string; strokeWidth: number; from?: Corner; ticks?: boolean; label?: "show" | "key" } };
// As many rows as fit the block's height are drawn. `text` is written on the rows, on Karo a character to a
// square, and grey with `trace` so the children can write over it. Karo is always in print.
// With `list` the block takes its words from the sheet's Lernwörter, one to a row, and `text` and `trace` rest: "copy"
// prints each word at its row's start to copy beside, "trace" prints it once in grey to write over, "row" in grey
// again and again to the row's end. "fold" is the Knickblatt: each word at its row's start, cut at the first column,
// with `folds` empty columns to write in (2 or 3) and a dashed fold line between the words and them.
export type ListMode = "copy" | "trace" | "row" | "fold";
// `from` is the index of the first word of the list the block shows, for a run-on Lineatur on a later page.
export type RulingBlock = Box & { type: "ruling"; props: { kind: Ruling; color: string; text?: string; font?: Font; trace?: boolean | "outline" | "dotted"; fade?: Fade; list?: ListMode; from?: number; folds?: number; house?: boolean; houseTint?: "room" | "all"; band?: boolean; bandColor?: string; syllables?: boolean; breaks?: Breaks; tints?: Tints; tintsAcross?: boolean } };
// The index of the first word a Lineatur shows: 0 unless it has a whole, non-negative `from`.
export const startOf = (b: RulingBlock): number => {
  const from = b.props.from ?? 0;
  return Number.isInteger(from) && from >= 0 ? from : 0;
};
// The words of a name line, as a new one has them. A line's `fields` replace them.
export const FIELDS = ["Name", "Datum", "Klasse"];
export type NameBlock = Box & { type: "name"; props: { fields?: string[] } };
export type PointsBlock = Box & { type: "points"; props: { max: number; total?: boolean } };
export type SymbolBlock = Box & { type: "symbol"; props: { code: string } };
// `ratio` is the picture's width over its height; `cut` the share cropped off its left, top, right and bottom.
export type ImageBlock = Box & { type: "image"; props: { upload: number; ratio: number; cut: number[]; opacity?: number } };
export type Op = keyof typeof SIGNS;
// The lowest and the highest digit a place may hold.
export type Range = [number, number];
// A written exercise on squared paper. A cell is [column, row, character, kind], a line [from column, to column,
// above row, kind]; kind 0 is printed on the sheet, 1 is the answer key's and 2 a small carry of the answer key's.
export type Grid = { cols: number; rows: number; cells: [number, number, string, number][]; lines: [number, number, number, number][] };
// `hide` is the number a gap stands for, the result when absent. `rest` is what a division leaves. A task of three
// numbers has `op2` and `c`: it reads `a op b op2 c`, with `paren` as the brackets say, "left" for `(a op b) op2 c`
// and "right" for `a op (b op2 c)`. A task of two has none of these. `family` numbers the family the task belongs to
// (0 for the first), and a task with no family has none: its exercises stand on their own.
export type Calc = { op: Op; a: number; b: number; result: number; rest: number; hide?: "a" | "b" | "c"; grid?: Grid; op2?: Op; c?: number; paren?: "left" | "right"; family?: number };
// One side of a comparison: a plain number, or a term with its sign and its two numbers.
export type Side = { value: number; op?: Op; a?: number; b?: number };
// A comparison: the two sides and the sign between them, which the pupil writes in the ring.
export type Compare = { left: Side; right: Side; sign: "<" | ">" | "=" };
export type Exercise = Calc | Compare;
// The generator's limits, as the server takes them: `a` and `b` hold the digits each number may have, units first.
// `sides`, `close` and `equal` only matter for a comparison, and blocks saved before them have none. `c` holds the
// digits of the third number, and `numbers` is 2 or 3 numbers in a task (blocks saved before have 2). `pvs` is Punkt
// vor Strich, and `brackets` the mit Klammern that goes with it. Blocks saved before have none of these.
// `decimals` and `money` set the places after the comma (see decimalsOf), and `af`, `bf` and `cf` hold the digits
// of those places for the first, second and third number, Zehntel first. `family` makes families of two or three tasks
// (none by default), and `moves` says which number of a Nachbaraufgabe moves, "a" by default. `gaps` says what a
// gap may hide: the numbers "a", "b" and "c", or the "result". `zero` lets 0 in as a number and as a result, `one`
// lets 1 in as a factor and as a divisor, and `distinct` keeps equal numbers out. Blocks saved before have none of
// these: the gap hides any number and never the result, and 0, 1 and equal numbers are in.
export type Limits = {
  ops: Op[];
  max: number;
  a: Range[];
  b: Range[];
  c?: Range[];
  carry: "none" | "required" | "either";
  rest: boolean;
  format: "row" | "gap" | "written" | "compare";
  count: number;
  seed: number;
  sides?: "nn" | "tn" | "tt";
  close?: boolean;
  equal?: "none" | "some";
  numbers?: 2 | 3;
  pvs?: boolean;
  brackets?: boolean;
  decimals?: 0 | 1 | 2;
  money?: boolean;
  af?: Range[];
  bf?: Range[];
  cf?: Range[];
  family?: "none" | "swap" | "reverse" | "neighbour";
  moves?: "a" | "b";
  gaps?: ("a" | "b" | "c" | "result")[];
  zero?: boolean;
  one?: boolean;
  distinct?: boolean;
  small?: boolean;
};
export { decimalsOf } from "./decimal";
// What the generator made of the limits. With fewer exercises than asked for, `loosen` names the limits in the way.
export type Made = { exercises: Exercise[]; loosen: string[] | null };
// `numbering` counts the exercises of the block; `size` is the font size of a row or a gap in points.
export type MathsProps = Limits & Made & { columns: number; size: number; numbering?: string };
export type MathsBlock = Box & { type: "maths"; props: MathsProps };
// `cells` holds the texts, a row of columns at a time. `cols` holds each column's share of the block's width, in
// parts of their sum. A row is as high as its highest cell needs, and the rows share equally what room the block
// has beyond that. `line` is the colour of the lines, and `head` sets the first row in bold. A cell holds no runs, so
// a whole cell is a gap: `gaps` holds a flag for each cell, a row of columns at a time as `cells` does.
// `rows` holds a lowest height in mm for each row; a row still grows when its text needs more.
export type TableBlock = Box & { type: "table"; props: { cells: string[][]; cols: number[]; size: number; align: Align; font?: Font; color?: string; line: string; head?: boolean; syllables?: boolean; breaks?: Breaks; tints?: Tints; tintsAcross?: boolean; gaps?: boolean[][]; gapWidth?: number; bank?: number; trace?: boolean | "outline" | "dotted"; fade?: Fade; spans?: Span[]; rows?: number[] } & Lines };
// A word search (Suchsel): a grid of `cols` by `rows` squares, each 6 to 20, with the words hidden in it and other
// letters around them. `words` holds the words as the teacher typed them, a line of the field to an entry, as the
// sheet's Lernwörter are held. `ways` is how the words may run, each level with the ones before: across only, down
// too, the diagonals too, backwards too. `caps` shows every letter as a capital, else every letter small. With
// `umlauts` ä, ö, ü and ß stay; else they become AE, OE, UE and SS. `show` prints the hidden words under the grid,
// or only how many there are. The layout comes from `seed` alone (suchsel.ts), so every draw gives the same grid.
export type Ways = "across" | "down" | "diag" | "back";
export type SuchselProps = { words: string[]; cols: number; rows: number; ways: Ways; caps: boolean; umlauts: boolean; show: "words" | "count"; seed: number };
export type SuchselBlock = Box & { type: "suchsel"; props: SuchselProps };
// A Zahlenmauer: walls of stones in rows, each stone the sum (or with `op` "*" the product) of the two under it.
// `base` is the number of stones in the lowest row, `count` the walls of the block and `columns` how many stand side
// by side. No stone is above `max`. `given` says which stones show their number: the base row, per wall a mix that
// needs the way back, or with "free" the stones `free` flags, a flag per stone index, the same for every wall. With
// `empty` no stone shows a number. `typed` holds the numbers the teacher typed into stones: wall (from 0), stone
// index, value. A stone's index counts from the base row's left end up, a row at a time (zahlenmauer.ts). The walls
// come from `seed` alone, so every draw gives the same ones.
export type Typed = [number, number, number];
export type ZahlenmauerProps = { base: 3 | 4 | 5; count: number; columns: number; max: number; op: "+" | "*"; given: "base" | "mix" | "free"; free?: boolean[]; empty: boolean; seed: number; typed?: Typed[] };
export type ZahlenmauerBlock = Box & { type: "zahlenmauer"; props: ZahlenmauerProps };
// A Rechendreieck: its stored shape is the contract at the top of rechendreieck.ts.
export type RechendreieckBlock = Box & { type: "rechendreieck"; props: RechendreieckProps };
// A Zahlenstrahl: its stored shape is the contract at the top of zahlenstrahl.ts.
export type ZahlenstrahlBlock = Box & { type: "zahlenstrahl"; props: ZahlenstrahlProps };
// A Hunderterfeld: its stored shape is the contract at the top of hunderterfeld.ts.
export type HunderterfeldBlock = Box & { type: "hunderterfeld"; props: HunderterfeldProps };
// An Uhr: its stored shape is the contract at the top of uhr.ts.
export type UhrBlock = Box & { type: "uhr"; props: UhrProps };
// A Selbstkontrolle: its stored shape is the contract at the top of selbstkontrolle.ts.
export type SelbstkontrolleBlock = Box & { type: "selbstkontrolle"; props: SelbstkontrolleProps };
export type Block = TextBlock | ShapeBlock | RulingBlock | NameBlock | PointsBlock | SymbolBlock | ImageBlock | MathsBlock | TableBlock | SuchselBlock | ZahlenmauerBlock | RechendreieckBlock | ZahlenstrahlBlock | HunderterfeldBlock | UhrBlock | SelbstkontrolleBlock;
export type Axis = "x" | "y";
// The teacher's own guide lines, in mm.
export type Guides = Record<Axis, number[]>;
// A page can have guide lines of its own, beside the sheet's, and a grid and a format of its own in place of the
// sheet's.
export type Page = { blocks: Block[]; guides?: Guides; grid?: number; landscape?: boolean };
// The pages, and what every page shares: guide lines, the grid's cell in mm (0 for none), and whether the A4 lies
// on its side.
// `words` holds the sheet's Lernwörter as the teacher typed them, a line of the list to an entry. Sheets saved
// before have none.
export type Doc = {
  pages: Page[];
  guides: Guides;
  grid: number;
  landscape?: boolean;
  words?: string[];
  pageNumbers?: { on?: boolean; at?: "bottom" | "right" | "outer" | "top"; form?: "n" | "seite" | "of" | "seiteVon"; notFirst?: boolean; black?: boolean };
};
export type PageNumbers = NonNullable<Doc["pageNumbers"]>;
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
// Self-hosted: Andika, Playwrite and Fibel (Druckschrift Nord and Süd) under the SIL Open Font License, Urff's
// Grundschrift under CC BY 3.0. The number is how far a font's baseline lies below the middle of a line of text, in
// em: half of its ascent less its descent. Text on a ruling needs it to stand on the line. A fourth number is the
// scale a Lineatur draws the font at, for a font whose small letters are not half its size high (0.5 over its
// x-height); text blocks, shapes and tables draw every font at its own size, since a paragraph cuts what stands out
// of its line.
export const FONTS = {
  andika: ["Druckschrift", "Andika", 0.415],
  nord: ["Druckschrift Nord", "Fibel Nord", 0.2888, 1.2703],
  sued: ["Druckschrift Süd", "Fibel Sued", 0.2888, 1.2703],
  grund: ["Grundschrift", "Playwrite DE Grund Variable", 0.4545],
  urff: ["Grundschrift (Urff)", "Grundschrift Urff", 0.299, 1.1628],
  va: ["Vereinfachte Ausgangsschrift", "Playwrite DE VA Variable", 0.46],
  sas: ["Schulausgangsschrift", "Playwrite DE SAS Variable", 0.4515],
  la: ["Lateinische Ausgangsschrift", "Playwrite DE LA Variable", 0.4545],
} as const;
// A sheet may come from anywhere: a font nobody knows draws as Druckschrift. The block keeps the name it has.
export const fontOf = (font: unknown): Font => (typeof font === "string" && Object.hasOwn(FONTS, font) ? (font as Font) : "andika");
// The scale a Lineatur draws a font at: 1 for the fonts without a fourth number.
export const fontScale = (font: Font) => (FONTS[font] as readonly [string, string, number, number?])[3] ?? 1;
// How far the ink of a font hangs left of where its letter starts, in em, for the letter j of the joined scripts.
// Measured in Chromium with canvas measureText (actualBoundingBoxLeft) at 1000 px, over printable ASCII and
// ÄÖÜäöüßẞ€§°; the largest value, rounded up to two decimals.
const LEFT: Record<Font, number> = { andika: 0.1, nord: 0, sued: 0, grund: 0.1, urff: 0.05, va: 0.21, sas: 0.24, la: 0.29 };
// How far the ink of a font reaches above and below its baseline, in em (#487). Measured in Chromium with
// canvas measureText, at 1000 px, over the regular, bold and italic cut and each of the printable ASCII
// characters and ÄÖÜäöüßẞ€§°; the largest of the three cuts, rounded up to three decimals.
const INK: Record<Font, readonly [number, number]> = {
  andika: [0.985, 0.25],
  nord: [0.75, 0.25],
  sued: [0.75, 0.25],
  grund: [1.157, 0.469],
  urff: [0.954, 0.282],
  va: [1.218, 0.516],
  sas: [1.125, 0.438],
  la: [1.157, 0.469],
};
// How far a font's ink reaches left of its place or right of its advance, in em, the largest over ASCII and the
// German capitals and signs (#76). Measured in Chromium with canvas measureText at 1000 px, regular cut, rounded up
// to two decimals.
const SIDE: Partial<Record<Font, number>> = { andika: 0.04, nord: 0.02, sued: 0.02, grund: 0.1, urff: 0.06, va: 0.21, sas: 0.24, la: 0.29 };
// Trace text (Nachspurtext), for the children to write over, in a text, a shape, a table and a Lineatur. A block
// stores `trace`: true for grey, "outline" for letters with a line around them and no fill (Umriss), "dotted" for the
// font's own dotted cut (gepunktet). Sheets saved before have true or nothing. `fade` makes the trace text lighter
// step by step until it is gone: "row" along each row, "rows" from row to row.
export type Trace = "grey" | "outline" | "dotted";
export type Fade = "row" | "rows";
// The fonts with a dotted cut, and its family. No other font is dotted: dots on a letter's outline are not what a
// child traces.
const DOTTED: Partial<Record<Font, string>> = { urff: "Grundschrift Urff Punkt" };
// How far the dotted cut's ink reaches left of its place and right of its advance, in em: its start dots reach
// further than SIDE measures for the regular cut. Measured in Chromium with canvas measureText at 1000 px, over
// ASCII and ÄÖÜäöüßẞ€§°: 0.032 left and 0.042 right, rounded up to two decimals and taken as one for both sides.
const DOTTED_SIDE = 0.05;
export const dottedFamily = (font?: Font): string | undefined => DOTTED[fontOf(font)];
// The look a block's trace text has. A sheet may come from anywhere: a value nobody knows is no trace text, and
// "dotted" in a font without a dotted cut is grey.
export const traceOf = (p: { trace?: unknown; font?: Font }): Trace | undefined =>
  p.trace === true ? "grey" : p.trace === "outline" ? "outline" : p.trace === "dotted" ? (dottedFamily(p.font) ? "dotted" : "grey") : undefined;
// The way a block's trace text fades, or none: a text that is no trace text does not fade.
export const fadeOf = (p: { trace?: unknown; fade?: unknown; font?: Font }): Fade | undefined =>
  traceOf(p) && (p.fade === "row" || p.fade === "rows") ? p.fade : undefined;
// How much of its ink part i of n keeps: the first all, the last none.
export const fadeAt = (i: number, n: number) => (n > 1 ? Math.max(0, 1 - i / (n - 1)) : 1);
// The mask that fades trace text. "row" goes from left to right; "rows" steps down, one step to a row, from `at` (a
// CSS length for the first row's top) with `rowPx` for each row.
const fadeMask = (fade: Fade, n: number, rowPx: number, at: (px: number) => string) => {
  // A sheet may come from anywhere: a count that is no number, or a huge one, draws at most 200 rows.
  const rows = Math.min(200, Math.max(1, Math.floor(n) || 1));
  return fade === "row"
    ? "linear-gradient(to right, #000, transparent 75%)"
    : `linear-gradient(to bottom, ${Array.from({ length: rows }, (_, i) => `rgba(0,0,0,${fadeAt(i, rows)}) ${at(i * rowPx)}, rgba(0,0,0,${fadeAt(i, rows)}) ${at((i + 1) * rowPx)}`).join(", ")}, transparent ${at(rows * rowPx)})`;
};
// The look of a trace text in outline: stroke first, the fill white over it, then multiplied, so the white vanishes
// and what lies under the letters shows through.
const OUTLINE: CSSProperties = { WebkitTextFillColor: "#fff", WebkitTextStroke: ".07em", paintOrder: "stroke fill", mixBlendMode: "multiply" };
// The font menu's groups, in order.
export const FONT_GROUPS = [
  ["Druckschriften", ["andika", "nord", "sued"]],
  ["Grund- und Schreibschriften", ["grund", "urff", "va", "sas", "la"]],
] as const;
// One row of each ruling: its height, and where its lines lie in mm from the row's top; Karo has squares instead.
// Lineatur 1 to 4 follow DIN 16552-1: four lines 5 mm apart, four lines 4 mm apart, a band of 3.5 mm, single lines
// 10 mm apart. The gap to the next row's lines (5, 4 and 8 mm) lies half above and half below, so blocks stack.
// In Lineatur 1 and 2 that gap is as wide as a zone, so the middle band is tinted, as in the schoolbooks: without
// it no one could tell where a row begins.
// Text stands on `base`, in a font of `size` mm. Every font's small letters are half its size high, so they fill
// the band of Lineatur 1 to 3; single lines have no band and take small letters 0.3 of a row high. On Karo a
// character is 0.75 of its square, as in a written exercise.
// `zones` are four heights in mm from a row's top: they bound the roof, the room and the cellar of a house drawn on
// each row. Lineatur 1 to 3 have them; Lineatur 4, the single lines and Karo have none, so they take no house.
// `band` says whether the middle band is tinted by default (`band > 0`). A block may switch the band on or off.
export const RULINGS = {
  l1: { name: "Lineatur 1 (Klasse 1)", row: 20, at: [2.5, 7.5, 12.5, 17.5], zones: [2.5, 7.5, 12.5, 17.5], band: 5, base: 12.5, size: 10 },
  l2: { name: "Lineatur 2 (Klasse 2)", row: 16, at: [2, 6, 10, 14], zones: [2, 6, 10, 14], band: 4, base: 10, size: 8 },
  l3: { name: "Lineatur 3 (Klasse 3)", row: 11.5, at: [4, 7.5], zones: [0.5, 4, 7.5, 11], band: 0, base: 7.5, size: 7 },
  l4: { name: "Lineatur 4 (Klasse 4)", row: 10, at: [10], zones: undefined, band: 0, base: 10, size: 6 },
  lines: { name: "Linien, 8 mm", row: 8, at: [8], zones: undefined, band: 0, base: 8, size: 4.8 },
  k5: { name: "Karo 5 mm", row: 5, at: undefined, zones: undefined, band: 0, base: 0, size: 3.75 },
  k7: { name: "Karo 7 mm", row: 7, at: undefined, zones: undefined, band: 0, base: 0, size: 5.25 },
};
// A Lineatur of a kind nobody knows draws as Lineatur 1, the kind a new one has.
export const kindOf = (kind: unknown): Ruling => (typeof kind === "string" && Object.hasOwn(RULINGS, kind) ? (kind as Ruling) : "l1");
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
export const read = ({ pages, blocks, guides, grid, landscape, words, pageNumbers }: Doc & { blocks?: Block[] }): Doc => ({
  pages: (pages ?? [{ blocks: blocks! }]).map((page) => ({ ...page, blocks: page.blocks.map(whole) })),
  guides,
  grid,
  landscape,
  words,
  pageNumbers,
});
// The Lernwörter a sheet's blocks print: an entry holds one word, or several split by commas or semicolons. Blanks
// around a word go, and so does an entry with no word. A list that is no list of texts holds no word.
export const wordsIn = (doc: { words?: unknown }): string[] =>
  Array.isArray(doc.words) ? doc.words.flatMap((line) => (typeof line === "string" ? line.split(/[,;\n]/) : [])).map((w) => w.trim()).filter(Boolean) : [];
// The mode a Lineatur takes the Lernwörter in, or none: a stored mode nobody knows is none.
export const listOf = (b: RulingBlock): ListMode | undefined =>
  b.props.list === "copy" || b.props.list === "trace" || b.props.list === "row" || b.props.list === "fold" ? b.props.list : undefined;
// Whether a block draws the sheet's Lernwörter: a Lineatur with a list mode, or a text or shape with `list: true`.
export const tied = (b: Block) => (b.type === "ruling" ? listOf(b) !== undefined : boxed(b)?.list === true);
// A sheet may come from anywhere: 1 to 4 columns, and anything else is 1.
export const listColsOf = (p: { listCols?: unknown }) => (typeof p.listCols === "number" && Number.isInteger(p.listCols) && p.listCols >= 1 && p.listCols <= 4 ? p.listCols : 1);
// The Lückenwörter mode, or none: a stored mode nobody knows is none.
export const holesOf = (p: { holes?: unknown }) => (p.holes === "one" || p.holes === "second" || p.holes === "vowels" ? p.holes : undefined);
// The empty columns of a Knickblatt: 3 when `folds` says so, else 2.
export const foldsOf = (b: RulingBlock): 2 | 3 => (b.props.folds === 3 ? 3 : 2);
// A house stands on a row of a kind with zones, when the block says so. A sheet may come from anywhere, so the flag reads strictly.
export const houseOf = (b: RulingBlock): boolean => !!RULINGS[kindOf(b.props.kind)].zones && b.props.house === true;
// The tint of a house: the room alone, or roof, room and cellar. Any other stored value is no tint.
export const houseTintOf = (b: RulingBlock): "room" | "all" | undefined =>
  houseOf(b) && (b.props.houseTint === "room" || b.props.houseTint === "all") ? b.props.houseTint : undefined;
// The middle band is tinted when the block says so, else as the kind does by default. A kind with no zones has none.
export const bandOf = (b: RulingBlock): boolean =>
  !!RULINGS[kindOf(b.props.kind)].zones && (typeof b.props.band === "boolean" ? b.props.band : RULINGS[kindOf(b.props.kind)].band > 0);
// The band's own colour, when one is picked: a six digit hex colour. Anything else is none.
export const bandColorOf = (b: RulingBlock): string | undefined =>
  typeof b.props.bandColor === "string" && /^#[0-9a-f]{6}$/i.test(b.props.bandColor) ? b.props.bandColor : undefined;
// The colour at 12 % on white, as the band paints it: what the colour field shows while no colour is picked.
export const shade = (color: string): string =>
  /^#[0-9a-f]{6}$/i.test(color) ? `#${[1, 3, 5].map((i) => Math.round(255 - 0.12 * (255 - parseInt(color.slice(i, i + 2), 16))).toString(16).padStart(2, "0")).join("")}` : "#ebebeb";
// The three light tints of a house: its roof, its room and its cellar.
export const HOUSE = { roof: "#f6c4bd", room: "#fcefb4", cellar: "#d9cdbd" };
// A house is one and a half rooms wide, and a room is the band between a row's second and third zone line.
export const houseWidth = (kind: Ruling): number => {
  const z = RULINGS[kind].zones;
  return z ? 1.5 * (z[2] - z[1]) : 0;
};
// How far the text starts from a block's left, in mm: past the house, 0.2 of a room of air, and the font's j, whose
// ink hangs left of its letter. The 0.02 em covers half the stroke of an outline trace (0.035 em). None with no house.
export const indentOf = (b: RulingBlock): number => {
  const kind = kindOf(b.props.kind);
  const z = RULINGS[kind].zones;
  const font = fontOf(b.props.font);
  return houseOf(b) && z ? houseWidth(kind) + 0.2 * (z[2] - z[1]) + (LEFT[font] + 0.02) * RULINGS[kind].size * fontScale(font) : 0;
};
// The line after or under a mixed word: the stored one, else "after" for a linked text, and none for any other.
export const lineOf = (p: { mixLine?: unknown; list?: unknown }): "after" | "under" | undefined =>
  p.mixLine === "after" || p.mixLine === "under" ? p.mixLine : p.list === true ? "after" : undefined;
// The Lernwörter of the sheet a block is drawn on. `Paper` sets them; the editor sets its own.
export const Words = createContext<string[]>([]);
// The whole sheet, for a Selbstkontrolle that checks the blocks of it. `Paper` and the Editor set it.
export const Whole = createContext<Doc>(EMPTY);
// The letter boxes of this block, one per task, when a "word" Selbstkontrolle of the sheet links it.
const useLetters = (id: string) => lettersOf(useContext(Whole)).get(id);
// A letter box in the drawing's own units: a square at (x, y), the letter in its middle in the answer key.
function LetterBox({ x, y, side, task, letter, solved }: { x: number; y: number; side: number; task: number; letter: string; solved: boolean }) {
  return (
    <g className="letter" data-task={task}>
      <rect x={x} y={y} width={side} height={side} fill="white" stroke="#222" strokeWidth={0.4} />
      {solved && <text x={x + side / 2} y={y + side / 2} fontSize={0.6 * side} textAnchor="middle" dominantBaseline="central" fill="#c0392b">{letter}</text>}
    </g>
  );
}
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
// The paragraphs a text draws: a linked text has one to a word of the sheet's list, with its hidden letters as gap
// runs when Lückenwörter is on. Any other text draws its own paragraphs.
export const shownParas = (p: TextProps, words: string[]): Para[] => {
  if (p.list !== true) return parasOf(p);
  const holes = holesOf(p);
  const seed = typeof p.holeSeed === "number" && Number.isFinite(p.holeSeed) ? p.holeSeed : 0;
  return words.map((word) => ({ runs: holes ? holed(word, holes, seed) : [{ text: word }] }));
};
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
export const rowsOf = (b: RulingBlock) => Math.floor(b.h / RULINGS[kindOf(b.props.kind)].row + 0.05);
export const colsOf = (b: RulingBlock) => Math.floor(b.w / RULINGS[kindOf(b.props.kind)].row + 0.05);
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
  // With families, each family is one item of the grid: as tall as its most tasks, with a gap of 0.9 lines to the next.
  const sizes = new Map<number, number>();
  for (const e of p.exercises) if (!("sign" in e) && e.family !== undefined) sizes.set(e.family, (sizes.get(e.family) ?? 0) + 1);
  if (sizes.size) {
    const lines = Math.ceil(sizes.size / p.columns);
    return Math.max(10, Math.round(lines * (Math.max(...sizes.values()) * 1.8 + 0.9) * p.size * PT));
  }
  const lines = Math.ceil(p.exercises.length / p.columns);
  // A comparison is a row of its own, with no squared paper.
  const rows = Math.max(0, ...p.exercises.map((e) => ("sign" in e ? 0 : e.grid?.rows ?? 0)));
  return Math.max(10, Math.round(lines * (p.format === "written" ? (rows + 1) * KARO : p.size * PT * 2.4)));
}
// The lowest point in mm of a block's box on its page: of a turned block, its lowest corner.
export function lowest(b: Box) {
  const [c, s] = dir(b);
  return b.y + b.h / 2 + (Math.abs(b.w * s) + Math.abs(b.h * c)) / 2;
}
// The right edge of a block's outline, turned or not.
export function rightmost(b: Box) {
  const [c, s] = dir(b);
  return b.x + b.w / 2 + (Math.abs(b.w * c) + Math.abs(b.h * s)) / 2;
}
// Whether a maths block with these props would end lower than it does and below the paper's edge, `H` mm down.
// A sheet prints one page a page: what hangs below is cut, so the panel and the painter refuse such a change.
export function overFoot(b: MathsBlock, props: MathsProps, H: number) {
  const h = mathsHeight(props);
  if (h === mathsHeight(b.props)) return false;
  const low = lowest({ ...b, ...tall(b, h) });
  return low > H + 0.01 && low > lowest(b) + 0.01;
}
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
// WebKit keeps the fraction of a line's baseline, Chromium (the print) puts it on a whole pixel: the text of a
// Lineatur then lies up to a pixel lower on the screen than in the print (issue #499). Measured once.
let keepsFraction: boolean | undefined;
// Each font's whole-pixel ascent and descent by family and size, from a canvas.
const metrics = new Map<string, [number, number]>();
function keepsFractions() {
  if (keepsFraction === undefined) {
    if (typeof document === "undefined") return false;
    // Monospace: the measure does not wait for a font to load.
    const p = document.createElement("p");
    p.style.cssText = "position:absolute;visibility:hidden;margin:0;white-space:pre;font:48.0113px monospace;line-height:75.5906px";
    const strut = document.createElement("span");
    strut.style.cssText = "display:inline-block;width:1px;height:0";
    p.append(strut, "a");
    document.body.append(p);
    const at = strut.getBoundingClientRect().top - p.getBoundingClientRect().top;
    p.remove();
    keepsFraction = at !== Math.floor(at);
  }
  return keepsFraction;
}
// The fraction in px of a first row's baseline: half the line height plus half the difference of ascent and
// descent. None while the font is not loaded, since the canvas would measure another font.
function baselineFraction(family: string | undefined, size: number, lineHeight: number) {
  if (!family || !keepsFractions() || !document.fonts.check(`${size}px "${family}"`)) return 0;
  const key = `${family}|${size}`;
  if (!metrics.has(key)) {
    const ctx = document.createElement("canvas").getContext("2d")!;
    ctx.font = `${size}px "${family}"`;
    const n = ctx.measureText("n");
    metrics.set(key, [n.fontBoundingBoxAscent, n.fontBoundingBoxDescent]);
  }
  const [ascent, descent] = metrics.get(key)!;
  const baseline = lineHeight / 2 + (ascent - descent) / 2;
  // A browser whose canvas does not tell a font's ascent takes nothing off.
  return Number.isFinite(baseline) ? baseline - Math.floor(baseline) : 0;
}
// Where the text on a ruling lies in its block: a line of text to a row, the baseline on the row's writing line.
// The box ends below the last row's descenders, so text past the last row is cut off.
// On Karo the field only takes the typing: its letters are unseen and as wide as a square, so the caret stands
// between the squares, and `Lines` draws the characters.
export function writtenStyle(b: RulingBlock, k: number): CSSProperties {
  const { row, at, base, size } = RULINGS[kindOf(b.props.kind)];
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
  const font = FONTS[fontOf(b.props.font)];
  const s = fontScale(fontOf(b.props.font));
  const top = base - row / 2 - font[2] * size * s;
  const look = traceOf(b.props);
  const fade = fadeOf(b.props);
  const mask = fade && fadeMask(fade, rowsOf(b), row * k, (px) => `${px}px`);
  // The text starts right of a house. Border-box keeps the padding inside the full width of the box.
  const indent = indentOf(b);
  const family = look === "dotted" ? dottedFamily(b.props.font) : font[1];
  const fraction = baselineFraction(family, size * s * k, row * k);
  // An outline or a dotted cut reaches past the box's left edge: the box takes `ext` px more to the left and its
  // padding takes them back, so no letter moves. Whole px, as the cut is (see `.frame` in styles.css).
  const reach = look === "outline" ? Math.max(SIDE[fontOf(b.props.font)] ?? 0, 0.12) + 0.035 : look === "dotted" ? DOTTED_SIDE : 0;
  const ext = reach ? Math.ceil(reach * size * s * k) + 1 : 0;
  return {
    ...((indent > 0 || ext > 0) && { paddingLeft: indent * k + ext, boxSizing: "border-box" as const }),
    ...(ext > 0 && { left: -ext, width: `calc(100% + ${ext}px)` }),
    fontFamily: family,
    fontSize: size * s * k,
    lineHeight: `${row * k}px`,
    top: top * k - fraction,
    height: (rowsOf(b) * row - top + Math.max(0, base + size / 2 - row)) * k,
    color: look === "grey" ? "#aaaaaa" : undefined,
    ...(look === "outline" && OUTLINE),
    ...(mask && { WebkitMaskImage: mask, maskImage: mask }),
  };
}
export const textStyle = (p: TextProps, k: number): CSSProperties => {
  // A dotted trace is the font's own dotted cut, regular and upright, so a bold or italic setting does not smear it.
  const dotted = traceOf(p) === "dotted";
  return {
    fontFamily: dotted ? dottedFamily(p.font) : FONTS[fontOf(p.font)][1],
    fontSize: p.size * PT * k,
    fontWeight: p.bold && !dotted ? 700 : 400,
    fontStyle: p.italic && !dotted ? "italic" : "normal",
    textDecoration: p.underline ? "underline" : "none",
    textAlign: p.align,
    color: p.color,
    lineHeight: p.spacing ?? 1.3,
  };
};
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
const tint = (colour: string | undefined, opacity = 1) =>
  colour?.length === 7 && opacity < 1 ? `rgb(${[1, 3, 5].map((i) => parseInt(colour.slice(i, i + 2), 16)).join(" ")} / ${opacity})` : colour;
const clear = ({ fill, opacity }: TextProps) => tint(fill, opacity);

// Drawn from the start corner along its own axis; a wide unseen stroke is what a finger grabs. The length stands
// over the middle, turned so it never reads upside down.
function Line({ block, k, solved }: { block: ShapeBlock; k: number; solved: boolean }) {
  const { kind, stroke, strokeOpacity, strokeWidth, dash, ticks, label } = block.props;
  const [x, y] = [far(block, 1, false) ? block.w : 0, far(block, 0, false) ? block.h : 0];
  const angle = (Math.atan2(block.h - 2 * y, block.w - 2 * x) * 180) / Math.PI;
  const length = Math.hypot(block.w, block.h);
  const head = kind === "line" ? 0 : 2 + strokeWidth * 3;
  // A double arrow has a head at its start too.
  const tail = kind === "double" ? head : 0;
  return (
    <svg>
      <g transform={`scale(${k}) translate(${x} ${y}) rotate(${angle})`} stroke={stroke} strokeOpacity={strokeOpacity} strokeWidth={strokeWidth} fill={stroke}>
        <line x2={length} stroke="transparent" strokeWidth={10} />
        <line x1={tail || undefined} x2={length - head} strokeDasharray={dashes(dash, strokeWidth)} strokeLinecap={dash === "dotted" ? "round" : undefined} />
        {/* The heads fade with the line; its length above it stays solid. */}
        {head > 0 && <polygon stroke="none" fillOpacity={strokeOpacity} points={`${length},0 ${length - head},${-head / 2} ${length - head},${head / 2}`} />}
        {tail > 0 && <polygon stroke="none" fillOpacity={strokeOpacity} points={`0,0 ${tail},${-tail / 2} ${tail},${tail / 2}`} />}
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
// The element of a frame that holds its text.
const TEXT_IN = ":scope > p, :scope > .body > p, :scope > .rich, :scope > .body > .rich";
const textIn = (frame: HTMLElement) => frame.querySelector<HTMLElement>(TEXT_IN) ?? undefined;
// The lines a frame's text has: its height past the padding, over its line height. Scrolled height, so a text too long
// counts all its lines. Undefined until the text is drawn.
function linesIn(frame: HTMLElement) {
  const text = textIn(frame);
  if (!text) return undefined;
  const style = getComputedStyle(text);
  const line = parseFloat(style.lineHeight);
  if (!(line > 0)) return undefined;
  const n = Math.round((text.scrollHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom)) / line);
  return Number.isFinite(n) && n > 0 ? n : undefined;
}
// A text or a shape with its text. The editor passes the field the text is typed in.
function Frame({ block, k, solved, children }: { block: TextBlock | ShapeBlock; k: number; solved: boolean; children?: ReactNode }) {
  const p = boxed(block)!;
  const tints = pairOf(p.tints);
  const width = gapWidth(p.gapWidth);
  // A linked text draws the sheet's Lernwörter, one to a paragraph, in columns, and grows to hold them. Its own text
  // rests, and so do the solution words of that text.
  const sheet = useContext(Words);
  const linked = p.list === true;
  // A bubble keeps its lowest quarter for its tail: its text lies in a row three times as high as the empty one under
  // it, so the body holds it however much there is. Flipped top to bottom the tail is the top quarter, and the empty
  // row lies over the text (`.frame.tailed` in styles.css names the row of the text).
  const tailed = p.kind === "bubble";
  const words = !linked && typeof p.bank === "number" && Number.isFinite(p.bank) ? entries(parasOf(p)) : [];
  const paras = shownParas(p, sheet);
  const cols = linked ? listColsOf(p) : undefined;
  // Lückenwörter: every hidden letter is a gap of its own, and a linked text with them takes no scrambled words.
  const holes = linked && holesOf(p) !== undefined;
  // A sheet may come from anywhere: a mix that is no number, or a line that is neither word, draws the plain text.
  const scramble = typeof p.mix === "number" && Number.isFinite(p.mix) && !holes;
  const line = lineOf(p);
  const [down, across, edge] = inset(p, block.type === "shape");
  // Only a shape made since #128 keeps its text inside its outline: one saved before prints all its text as it did.
  const [fitTop, fitRight, fitBottom, fitLeft] = p.inside === true ? fitOf(p.kind, block.w, block.h, block.flipY) : [0, 0, 0, 0];
  // Such a shape never grows for its text: its type shrinks to fit the inner box (see `fitText`).
  const inside = p.inside === true && (p.kind === "circle" || p.kind === "triangle" || p.kind === "star");
  // The ink of the font that a line of this spacing does not hold reaches out of the paragraph: the clip and the padding
  // reach `up` and `down` em further, so no dot and no foot is lost (#487). A line centred on the middle of the
  // line box, which lies `c` em above the baseline, holds the ink from `s / 2` em each side of that middle.
  const font = fontOf(p.font);
  const s = typeof p.spacing === "number" && Number.isFinite(p.spacing) ? p.spacing : 1.3;
  // Under a fiftieth of the size it counts as none: Andika's lowest sign reaches 0.015 em out of a line of 1.3, less
  // than a pixel at any size a sheet uses, and its texts stay as sheets saved before drew them.
  const reach = (v: number) => (v < 0.02 ? 0 : v);
  // An outline stands half its stroke (.07em) outside the letter: 0.035 em each way, past the threshold.
  const stroke = traceOf(p) === "outline" ? 0.035 : 0;
  const above = reach(Math.max(0, INK[font][0] - FONTS[font][2] - s / 2)) + stroke;
  const below = reach(Math.max(0, INK[font][1] + FONTS[font][2] - s / 2)) + stroke;
  // How far a joined script's letters reach past their place to each side, and the outline's stroke with them.
  // A plain text takes the side reach only in a joined script, where a letter reaches 0.1 em or more past its place: a
  // print font's plain text draws as it did before. An outline takes it in every font, and 0.12 em at least: Andika's
  // j reaches further in its outline than the upright cut's measure says. A slanted text leans 0.15 em further.
  // A dotted look takes the dotted cut's reach the same way (DOTTED_SIDE).
  const dotted = traceOf(p) === "dotted";
  const wide = Math.max(SIDE[font] ?? 0, stroke > 0 ? 0.12 : 0, dotted ? DOTTED_SIDE : 0);
  const side = stroke > 0 || dotted || wide >= 0.1 ? wide + stroke + (p.italic ? 0.15 : 0) : 0;
  // A pixel more each way (below): a browser smooths the edge of a letter over the row beside it.
  const tight = above > 0 || below > 0 || side > 0;
  // An outline's stroke and a dotted cut's dots reach a pixel past the measured ink, and a pixel more with the page's
  // rounding (#503): the paragraph takes one pixel more above and below for them.
  const fringe = stroke > 0 || dotted ? 2 : 1;
  // A trace text fades along its rows: a row is the font's size times its spacing, and `--ink-up` is the room above the first.
  // The rows are the lines the text has once it is drawn (`lines`), and the block's height until then.
  const fade = fadeOf(p);
  const rowMM = p.size * PT * (p.spacing ?? 1.3);
  const frameRef = useRef<HTMLDivElement>(null);
  const [lines, setLines] = useState<number>();
  useLayoutEffect(() => {
    const frame = frameRef.current;
    const n = fade === "rows" && frame ? linesIn(frame) : undefined;
    if (n !== undefined) setLines(n);
    // Too long even at the smallest type: the frame tells the editor by how many px, and the editor grows the shape.
    const over = inside && frame ? fitText(frame, least.current, block.h * k) : 0;
    // Zero when it fits: the editor then lifts the page foot's warning for it.
    if (inside && frame) frame.dispatchEvent(new CustomEvent("overfit", { bubbles: true, detail: Math.max(0, over) / k }));
  });
  // The share of its size the type may shrink to, and the shape's height in px, for a font that comes in later.
  const least = useRef(1);
  least.current = leastOf(p.size);
  const high = useRef(0);
  high.current = block.h * k;
  useLayoutEffect(() => {
    if (!inside) return;
    const again = () => frameRef.current && fitText(frameRef.current, least.current, high.current);
    document.fonts.ready.then(again);
    document.fonts.addEventListener("loadingdone", again);
    return () => document.fonts.removeEventListener("loadingdone", again);
  }, [inside]);
  useEffect(() => {
    const frame = frameRef.current;
    if (fade !== "rows" || !frame) return;
    let gone = false;
    const measure = () => {
      const n = linesIn(frame);
      if (n !== undefined) setLines(n);
    };
    const resized = new ResizeObserver(measure);
    resized.observe(frame);
    const text = textIn(frame);
    if (text) resized.observe(text);
    document.fonts.ready.then(() => !gone && measure());
    return () => {
      gone = true;
      resized.disconnect();
    };
  }, [fade]);
  const estimate = Math.round((block.h - 2 * down) / rowMM);
  const mask = fade && Number.isFinite(rowMM) && rowMM > 0 && fadeMask(fade, lines ?? estimate, rowMM * k, (px) => `calc(var(--ink-up, 0px) + ${px}px)`);
  // A kind nobody knows draws as a rectangle, also one that names a part of every object ("toString").
  const d = Object.hasOwn(OUTLINES, p.kind ?? "") ? OUTLINES[p.kind!]?.(block.w, block.h, edge / 2) : undefined;
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
  const text = (
    <>
      {children ??
        (linked && !paras.length ? (
          <div className="rich nolist" />
        ) : scramble ? (
          <Rich paras={paras} mix={mixed(paras, { seed: p.mix!, first: p.mixFirst === true, caps: p.mixCaps === true })} line={line} solved={solved} cols={cols} />
        ) : linked || p.rich ? (
          <Rich paras={paras} holes={holes} cols={cols} />
        ) : (
          <p>{p.text}</p>
        ))}
      {words.length > 0 && <Bank words={words} seed={p.bank!} />}
    </>
  );
  return (
    <div
      ref={frameRef}
      className={classes("frame", tints && "tinted", solved && "solved", width && "even", linked && "listed", tailed && "tailed", tight && "tight", inside && "inside")}
      data-trace={traceOf(p)}
      data-fade={fade}
      style={{
        ...textStyle(p, k),
        ...(inside && { fontSize: `calc(${p.size * PT * k}px * var(--fit, 1))` }),
        ...(tight && { "--ink-up": `calc(${above}em + ${fringe}px)`, "--ink-down": `calc(${below}em + ${fringe}px)`, "--ink-side": side > 0 ? `calc(${side}em + 1px)` : "0px" }),
        ...gapVar(width, k),
        ...(mask && ({ "--fade": mask } as CSSProperties)),
        // A linked text grows to hold its words, past the height it is stored with.
        ...(linked && { height: "auto", minHeight: "100%" }),
        background: d ? undefined : clear(p),
        border: own ? `${edge * k}px ${p.dash} ${tint(p.stroke, p.strokeOpacity)}` : undefined,
        boxShadow: solid ? `inset 0 0 0 ${edge * k}px ${tint(p.stroke, p.strokeOpacity)}` : undefined,
        borderRadius: radius,
        // A pixel outside the box, so a stroke flush with its edge stays whole (see .frame in styles.css), and round
        // as the box, so a text too long for a circle ends at the circle. A bow under the last line hangs below a
        // box that is just as high as its text.
        clipPath: `inset(${tight ? `calc(-1px - ${above}em) ${side > 0 ? `calc(-1px - ${side}em)` : "-1px"} ${below > 0 ? `calc(-1px - ${p.syllables ? ".3em - " : ""}${below}em)` : p.syllables ? "calc(-1px - .3em)" : "-1px"} ${side > 0 ? `calc(-1px - ${side}em)` : "-1px"}` : p.syllables ? "-1px -1px calc(-1px - .3em)" : "-1px"} round ${radius})`,
        padding: `${(down - room + fitTop) * k}px ${(across - room + fitRight) * k}px ${(down - room + fitBottom) * k}px ${(across - room + fitLeft) * k}px`,
        ...(tailed
          ? { display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gridTemplateRows: block.flipY ? "1fr 3fr" : "3fr 1fr", gridTemplateAreas: block.flipY ? '"." "words"' : '"words" "."' }
          : { justifyContent: UP[p.valign ?? "top"] }),
        ...((d || ring) && { position: "relative", isolation: "isolate" }),
      }}
    >
      {d && (
        // A linked text's outline goes with its frame when the words make that higher than the block.
        <svg className="outline" viewBox={`0 0 ${block.w} ${block.h}`} preserveAspectRatio={linked ? "none" : undefined} style={{ ...over, ...flipped(block) }}>
          {p.dash && edge > 0 ? (
            <Dashes way={POINTS[p.kind!]!(block.w, block.h, edge / 2)} edge={edge} p={p} fill={p.fill ?? "none"} fillOpacity={p.opacity ?? 1} />
          ) : (
            <Outline d={d} fill={p.fill ?? "none"} fillOpacity={p.opacity ?? 1} stroke={p.stroke ?? "none"} strokeOpacity={p.strokeOpacity} strokeWidth={p.strokeWidth ?? 0.5} strokeDasharray={dashes(p.dash, p.strokeWidth ?? 0.5)} strokeLinecap={p.dash === "dotted" ? "round" : undefined} strokeLinejoin="round" />
          )}
        </svg>
      )}
      {ring && (
        <svg className="dashes" viewBox={`0 0 ${block.w} ${block.h}`} style={over}>
          <Ring w={block.w - edge} h={block.h - edge} edge={edge} p={p} />
        </svg>
      )}
      {/* A bubble's text and its solution words stand in its body one under the other, as in any other frame. */}
      {tailed ? <div className="body" style={{ justifyContent: UP[p.valign ?? "top"] }}>{text}</div> : text}
      {(p.syllables || tints) && <Bows block={block} base={FONTS[fontOf(p.font)][2]} breaks={p.breaks} syllables={p.syllables} tints={tints} tintsAcross={p.tintsAcross} solved={solved} />}
    </div>
  );
}

// The smallest type a shape shrinks its text to, in pt: a child still reads it. A text set smaller keeps its size.
const LEAST = 10;
// The share of a text's size it may shrink to.
const leastOf = (size: number) => Math.min(1, LEAST / size) || 1;
// Shrinks a frame's type (`--fit`) until its lines fit its height and no word runs past its width, down to the share
// `least`. Each round measures the type it has and takes the share it is too big by. Up to three rounds: a line of a
// pixel does not shrink. Gives what the lines still reach past the room at the smallest type, in px: the editor grows
// the shape by it, as it grows a rectangle. `high` is the shape's height in px: a frame being written in is as high
// as its text.
function fitText(el: HTMLElement, least: number, high: number) {
  el.style.removeProperty("--fit");
  // A turned block lies level for the measure, so its lines run across.
  const block = el.parentElement!;
  const was = block.style.transform;
  block.style.transform = "none";
  // The room inside the padding: a text past its foot is no scroll of the frame, so the lines are measured.
  const box = el.getBoundingClientRect();
  const pad = getComputedStyle(el);
  // The desk's zoom: the screen measures in its px, the frame's sizes are in its own.
  const zoom = box.width / el.offsetWidth || 1;
  const [top, bottom] = [box.top + parseFloat(pad.paddingTop) * zoom, box.top + (high - parseFloat(pad.paddingBottom)) * zoom];
  if (bottom - top < 3) {
    block.style.transform = was;
    return 0;
  }
  // A paragraph is no taller than its frame, so its lines are measured where they lie, past its foot.
  const lowest = () =>
    Math.max(
      ...[...el.querySelectorAll<HTMLElement>("p")].map((p) => {
        const r = document.createRange();
        r.selectNodeContents(p);
        return Math.max(...[...r.getClientRects()].map((q) => q.bottom));
      }),
    );
  let scale = 1;
  for (let round = 0; round < 3; round++) {
    const tall = (lowest() - top) / (bottom - top);
    const wide = [...el.querySelectorAll<HTMLElement>("p")].map((p) => p.scrollWidth / p.clientWidth);
    const across = Math.max(...wide);
    // Too high: down to the smallest type. A word too wide shrinks past it: a word is never cut.
    const next = Math.min(across > 1.01 ? scale / across : scale, tall > 1.01 ? Math.max(least, scale / tall) : scale);
    if (!(next < scale)) break;
    scale = next;
    el.style.setProperty("--fit", String(scale));
  }
  const past = (lowest() - bottom) / zoom;
  block.style.transform = was;
  return past > 1 ? past : 0;
}
// The classes of an element, from the names that are set.
const classes = (...names: (string | false | 0 | undefined)[]) => names.filter(Boolean).join(" ");
// Every gap of a block is at least this many mm wide: a finite number above 0, at most 200. Else none.
const gapWidth = (mm: unknown) => (typeof mm === "number" && Number.isFinite(mm) && mm > 0 ? Math.min(mm, 200) : 0);
// The step of a text's line numbers: a whole number from 1 to 100. A sheet may come from anywhere: else none.
export const stepOf = (n: unknown) => (typeof n === "number" && Number.isInteger(n) && n >= 1 && n <= 100 ? n : 0);
// The number of a text's first line: 1 unless it is a whole number from 1 to 9999.
export const fromOf = (n: unknown) => (typeof n === "number" && Number.isInteger(n) && n >= 1 && n <= 9999 ? n : 1);
// The width in px of a block's gaps, for the CSS of `.even .gap`.
const gapVar = (mm: number, k: number) => (mm ? ({ "--gap": `${mm * k}px` } as CSSProperties) : {});
// The box of the solution words under a text: each word once, in the seeded order of its block. Where another order
// exists, the box never stands in reading order: the words are shuffled again until they do not.
function Bank({ words, seed }: { words: string[]; seed: number }) {
  return <div className="bank">{shuffled(words, seed, words).map((word, i) => <span key={i}>{word}</span>)}</div>;
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
  const all = { stroke: p.stroke, strokeOpacity: p.strokeOpacity, strokeWidth: edge, strokeDasharray: dashes(p.dash, edge * fit), strokeDashoffset: -edge / 100, strokeLinecap: p.dash === "dotted" ? ("round" as const) : undefined, ...look };
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
// The rectangle inside a shape's outline where its text lies, as the mm the box keeps from it: top, right, bottom and
// left. A circle keeps the square inscribed in it, a triangle the half that holds its base, a star the box of its inner
// points. Flipped top to bottom, the top and the bottom swap.
export function fitOf(kind: Kind | undefined, w: number, h: number, flipY?: boolean): [number, number, number, number] {
  let fit: [number, number, number, number] = [0, 0, 0, 0];
  if (kind === "circle") {
    const [across, down] = [(w * (1 - Math.SQRT1_2)) / 2, (h * (1 - Math.SQRT1_2)) / 2];
    fit = [down, across, down, across];
  } else if (kind === "triangle") fit = [h / 2, w / 4, 0, w / 4];
  else if (kind === "star") {
    const inner = POINTS.star!(w, h, 0).filter((_, i) => i % 2 === 1);
    const [xs, ys] = [inner.map(([x]) => x), inner.map(([, y]) => y)];
    fit = [Math.min(...ys), w - Math.max(...xs), h - Math.max(...ys), Math.min(...xs)];
  }
  return flipY ? [fit[2], fit[1], fit[0], fit[3]] : fit;
}
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
        const [first, start] = spot(from);
        // The end lies in the node of the syllable's last letter, not at the start of the next.
        const [last, stop] = spot(from + module.shown(piece.text).length - 1);
        // A mixed word has no syllables: a syllable that starts or ends in its letters gets neither bow nor colour,
        // and the colours of the words after it go on as if it had none, in the key too.
        if (first.parentElement!.closest(".mixed") || last.parentElement!.closest(".mixed")) continue;
        const colour = tints?.[count++ % 2];
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
    // A shape that shrinks its text sets the share after the bows are drawn: a new share is drawn for again.
    let fit = own.parentElement!.style.getPropertyValue("--fit");
    const shrunk = new MutationObserver(() => {
      const now = own.parentElement!.style.getPropertyValue("--fit");
      if (now !== fit) later();
      fit = now;
    });
    shrunk.observe(own.parentElement!, { attributes: true, attributeFilter: ["style"] });
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
      shrunk.disconnect();
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

// The numbers are 0.7 em of their text: small, so they stay out of the way of the text.
const NUMBER_EM = 0.7;
// The line numbers of a text, beside `svg`, which is the block's own. The lines are counted as they break, over all
// the paragraphs of the text: an empty paragraph is no line. In columns the numbers count the rows of the grid.
// A number stands on every `step`th line that lies in the box; a line cut off below the box has none. Measured like
// the bows, in the block's own pixels.
function numbering(svg: SVGSVGElement, block: TextBlock) {
  const host = svg.parentElement!.querySelector<HTMLElement>(":scope > .frame")!;
  const step = stepOf(block.props.lines);
  const turn = svg.parentElement!.style.transform;
  svg.parentElement!.style.transform = "none";
  const { left, top } = svg.getBoundingClientRect();
  const box = host.getBoundingClientRect();
  const scale = box.width / host.offsetWidth;
  const em = parseFloat(getComputedStyle(host).fontSize);
  // Half the height of a line, on the screen.
  const near = (parseFloat(getComputedStyle(host).lineHeight) * scale) / 2;
  const base = FONTS[fontOf(block.props.font)][2];
  const shown: SVGTextElement[] = [];
  let count = fromOf(block.props.linesFrom) - 1;
  // The rows not yet numbered. In columns the words of all paragraphs make one grid, so their rows are numbered
  // together, top to bottom; otherwise each paragraph is numbered as it comes.
  let rows: { top: number; bottom: number }[] = [];
  const columns = block.props.list === true && listColsOf(block.props) > 1;
  const number = () => {
    rows.sort((a, b) => a.top - b.top);
    for (const row of rows) {
      count++;
      const middle = (row.top + row.bottom) / 2;
      if (count % step || middle <= box.top || middle >= box.bottom) continue;
      const text = document.createElementNS(SVG, "text");
      text.setAttribute("class", "ln");
      text.dataset.line = String(count);
      text.setAttribute("text-anchor", "end");
      // Two mm left of the box, which is laid out at K pixels a mm.
      text.setAttribute("x", `${-2 * K}`);
      text.setAttribute("y", `${((middle - top) / scale + base * em).toFixed(2)}`);
      text.setAttribute("font-size", `${(NUMBER_EM * em).toFixed(2)}`);
      text.setAttribute("font-family", "Andika");
      text.setAttribute("fill", GREYS[1]);
      text.textContent = String(count);
      shown.push(text);
    }
    rows = [];
  };
  for (const p of scale ? host.querySelectorAll("p") : [])
    if (!p.querySelector("p")) {
      const nodes: Text[] = [];
      const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      // The line under a scrambled word is no line of the text: its word lies in the column under the mixed one.
      while (walk.nextNode()) {
        const el = walk.currentNode.parentElement!;
        if (el.tagName !== "TEXTAREA" && !el.closest(".mix.under .gap")) nodes.push(walk.currentNode as Text);
      }
      // A line is a row of rects that the text's words lie in. Spaces are no words: a line of spaces alone is as
      // empty as one with nothing, in a paragraph or between two line breaks. Two words stand in one line when
      // their tops are less than half a line apart: the box of a school script's letters is two lines high and
      // more, in WebKit above all, so it reaches over its neighbours.
      const range = document.createRange();
      for (const node of nodes)
        for (const word of node.data.matchAll(/\S+/g)) {
          range.setStart(node, word.index);
          range.setEnd(node, word.index + word[0].length);
          for (const rect of range.getClientRects()) if (rect.right > rect.left && !rows.some((row) => Math.abs(rect.top - row.top) < near)) rows.push({ top: rect.top, bottom: rect.bottom });
        }
      if (!columns) number();
    }
  if (columns) number();
  svg.parentElement!.style.transform = turn;
  svg.replaceChildren(...shown);
  svg.classList.remove("unsplit");
}
// A change inside the bows is no change of the letters: the bows are redrawn inside the frame and move none.
const inBows = (node: Node) => (node instanceof Element ? node : node.parentElement)?.closest(".bows");
// The line numbers of a text that asks for them, drawn beside its box as the bows are. `unsplit` stands while they
// are not those of the text shown, so the PDF waits for them.
export function Numbers({ block }: { block: TextBlock }) {
  const svg = useRef<SVGSVGElement>(null);
  const tools = useRef({ draw: () => {}, seen: () => {}, drawn: () => {} });
  useLayoutEffect(() => {
    const own = svg.current!;
    const host = own.parentElement!.querySelector<HTMLElement>(":scope > .frame")!;
    let frame = 0;
    // One measure a frame, however much changed.
    const later = () => {
      own.classList.add("unsplit");
      frame ||= requestAnimationFrame(() => tools.current.draw());
    };
    // The frame and what lies in it: a font that comes in breaks the lines anew and makes the text higher or
    // lower, in a frame that stays as it is. WebKit sends no event for such a font.
    // A size the numbers are drawn for already is no news: an element says its size once when it is first watched.
    const sizes = new Map<Element, string>();
    const span = (el: Element) => `${(el as HTMLElement).offsetWidth} ${(el as HTMLElement).offsetHeight}`;
    const resized = new ResizeObserver((entries) => entries.some(({ target }) => sizes.get(target) !== span(target)) && later());
    const changed = new MutationObserver((records) => records.some((record) => !inBows(record.target)) && later());
    changed.observe(host, { characterData: true, childList: true, subtree: true });
    document.fonts.addEventListener("loadingdone", later);
    // What React just wrote into the text is drawn for at once, so no frame shows old numbers and none measures
    // twice. The text may lie in a new element since: that one is watched from now on.
    tools.current.seen = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      changed.takeRecords();
      sizes.clear();
      for (const el of [host, ...host.children]) {
        sizes.set(el, span(el));
        resized.observe(el);
      }
    };
    // A font still on its way breaks the lines anew when it comes in: until then the numbers are not yet those
    // of the text, and say so.
    let gone = false;
    tools.current.drawn = () => {
      if (document.fonts.status !== "loading") return;
      own.classList.add("unsplit");
      document.fonts.ready.then(() => gone || later());
    };
    return () => {
      gone = true;
      cancelAnimationFrame(frame);
      resized.disconnect();
      changed.disconnect();
      document.fonts.removeEventListener("loadingdone", later);
    };
  }, []);
  useLayoutEffect(() => {
    tools.current.draw = () => {
      tools.current.seen();
      numbering(svg.current!, block);
      tools.current.drawn();
    };
    svg.current!.classList.add("unsplit");
    tools.current.draw();
  }, [block.props, block.w, block.h, block.angle]);
  return <svg ref={svg} className="numbers unsplit" aria-hidden />;
}

// The runs of a paragraph in groups: consecutive gap runs share one group, every other run has one of its own. With
// `single` every run has a group of its own, so each hidden letter of Lückenwörter is a gap of its own.
const runGroups = (runs: Run[], single = false) =>
  runs.reduce<Run[][]>((all, r) => {
    const last = all.at(-1);
    if (!single && r.gap === true && last?.[0].gap === true) last.push(r);
    else all.push([r]);
    return all;
  }, []);

// A word in a sentence that is wider than its paragraph breaks at the block's edge, as a lone word does: the class
// `wide` lets it (`.mix.wide` in styles.css). The sizes are read in layout px (offsetWidth, clientWidth), which neither
// a turn of the block nor the editor's zoom changes. Every word's class is taken off first, so each is measured in the
// same state and the class does not flip back and forth.
function markWide(root: HTMLElement) {
  const mixes = [...root.querySelectorAll<HTMLElement>(".mix")];
  mixes.forEach((mix) => mix.classList.remove("wide"));
  const wide = mixes.map((mix) => {
    const p = mix.closest("p")!;
    const style = getComputedStyle(p);
    const room = p.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    return mix.offsetWidth > room;
  });
  mixes.forEach((mix, i) => mix.classList.toggle("wide", wide[i]));
}

// A text's paragraphs, in the markup the editor's field makes of them, so one stylesheet draws both. What a sheet
// stores is drawn as text alone, never as markup of its own. `mix` holds the parts of each paragraph in place of its
// runs (see `mixed`): a part with a `source` is one scrambled word, the others are runs as they are. `holes` marks
// Lückenwörter, and `cols` sets a linked text's words in that many columns, filled column by column.
function Rich({ paras, mix, line, solved, holes, cols }: { paras: Para[]; mix?: Part[][]; line?: "after" | "under"; solved?: boolean; holes?: boolean; cols?: number }) {
  const root = useRef<HTMLDivElement>(null);
  // Measured after every render: the class is set again whenever React has written the paragraphs anew.
  useLayoutEffect(() => {
    if (root.current) markWide(root.current);
  });
  // Again when the block's size changes, and when the fonts are in: a font changes the widths, not the block's size.
  // Registered in a layout effect, which runs before Print's effect waits for the fonts, so the PDF is printed after it.
  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    const observer = new ResizeObserver(() => markWide(el));
    observer.observe(el);
    document.fonts.ready.then(() => markWide(el));
    return () => observer.disconnect();
  }, []);
  const or = (set: boolean | undefined, on: string, off: string) => (set === undefined ? undefined : set ? on : off);
  const run = ({ text, bold, italic, underline, color }: Run, key: number) => (
    <span key={key} style={{ fontWeight: or(bold, "700", "400"), fontStyle: or(italic, "italic", "normal"), textDecoration: underline ? "underline" : undefined, color }}>
      {text}
    </span>
  );
  // Consecutive gap runs make one gap: its outer span draws the line, its inner one holds the words.
  const gaps = (runs: Run[]) =>
    runGroups(runs, holes).map((group, g) =>
      group[0].gap === true ? (
        <span key={g} className="gap" data-gap="true">
          <span>{group.map((r, j) => run(r, j))}</span>
        </span>
      ) : (
        run(group[0], g)
      ),
    );
  // A scrambled word: the mixed letters, or the word as typed where the key shows it in their place, and a line for
  // the word as typed, after or under the mixed one.
  const scrambled = (source: string, runs: Run[], j: number) => (
    <span key={j} className={classes("mix", line === "under" && "under")} data-mix={source}>
      {solved && !line ? <span className="mixkey">{source}</span> : <span className="mixed">{runs.map((r, k) => run(r, k))}</span>}
      {line && (
        <>
          {" "}
          <span className="gap line">
            <span>{source}</span>
            {/* Drawn, not a background: a browser lays a thin gradient paler on the screen than the print has it. */}
            <svg aria-hidden>
              <line y1="50%" x2="100%" y2="50%" />
            </svg>
          </span>
        </>
      )}
    </span>
  );
  const grid: CSSProperties | undefined =
    cols && cols > 1 ? { display: "grid", gridAutoFlow: "column", gridTemplateRows: `repeat(${Math.ceil(paras.length / cols)}, auto)`, gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, columnGap: "1em" } : undefined;
  // A paragraph whose one scrambled word stands alone, with nothing but spaces about it: that word breaks at the
  // block's edge, as a word in a column does (`.lone` in styles.css).
  const lone = (i: number) => {
    const parts = mix?.[i] ?? [];
    return parts.filter((part) => part.source !== undefined).length === 1 && parts.every((part) => part.source !== undefined || part.runs.every((r) => !r.text.trim()));
  };
  return (
    <div ref={root} className={classes("rich", holes && "holes")} style={grid}>
      {paras.map((para, i) => (
        <p key={i} className={lone(i) ? "lone" : undefined} data-list={para.list} data-level={para.level || undefined}>
          {mix
            ? mix[i].map((part, j) => <Fragment key={j}>{part.source !== undefined ? scrambled(part.source, part.runs, j) : gaps(part.runs)}</Fragment>)
            : gaps(para.runs)}
          {/* A paragraph with no text is still a line high. */}
          {!para.runs.length && <br />}
        </p>
      ))}
    </div>
  );
}

// Drawn in mm: the SVG's own scale takes it to the block's size. The editor passes the field the text is typed in.
function Lines({ block, k, children }: { block: RulingBlock; k: number; children?: ReactNode }) {
  const { row, at, zones, size } = RULINGS[kindOf(block.props.kind)];
  const { text = "" } = block.props;
  const rows = rowsOf(block);
  const cols = colsOf(block);
  // A block set to the list shows the list alone: with no word in it, empty rows, and not its own text, which the
  // editor could not open there.
  const words = useContext(Words);
  const mode = listOf(block);
  // Karo draws its trace text in the squares, which have no dotted cut: a dotted trace there is grey. A Lernwörter
  // list draws its own look, so it has none.
  const karoLook = !at && !mode ? traceOf({ trace: block.props.trace }) : undefined;
  const karoFade = karoLook ? fadeOf(block.props) : undefined;
  const s = fontScale(fontOf(block.props.font));
  // A Knickblatt has its first column for the words and `folds` empty ones after it, all of the same width. On Karo
  // the first column is a whole number of squares, and the words are cut to it.
  const fold = mode === "fold";
  const folds = foldsOf(block);
  const first = at ? block.w / (folds + 1) : Math.max(1, Math.floor(cols / (folds + 1))) * row;
  const plain = mode === "copy" || fold;
  const shown = words.slice(startOf(block), startOf(block) + rows);
  const cut = (word: string) => [...word].slice(0, fold ? Math.round(first / row) : cols).join("");
  // On Karo a row of the list is its word, cut to the squares, and in "row" as often as whole words fit.
  const karo = mode === "row"
    ? shown.map((word) => {
        const c = cut(word);
        const reps = Math.max(1, Math.floor((cols + 1) / ([...c].length + 1)));
        return Array.from({ length: reps }, () => c).join(" ");
      }).join("\n")
    : shown.map(cut).join("\n");
  const each = (n: number) => Array.from({ length: n }, (_, i) => i * row);
  const ys = at ? each(rows).flatMap((top) => at.map((y) => top + y)) : each(rows + 1);
  const list = useRef<HTMLDivElement>(null);
  // A word wider than its column is pressed narrower, its letters as high as before, so it stays in the lines and
  // the house. The ratio does not depend on the scale k, so the thumbnail and the print press alike. Only a Knickblatt's
  // word has a width set, so the other lists are left alone. Measured after every render, and again when the fonts are in.
  const press = () => {
    for (const span of list.current?.querySelectorAll<HTMLElement>(".row > span") ?? []) {
      // The word inside is the one scaled: the span is the clip, and a scaled clip would cut the word.
      const word = span.firstElementChild as HTMLElement | null;
      if (!word) continue;
      word.style.transform = "";
      // The widths as laid out, not as drawn: a turned block's outline would measure wrong.
      const room = parseFloat(getComputedStyle(span).width);
      const natural = parseFloat(getComputedStyle(word).width);
      word.style.transform = natural > room ? `scaleX(${room / natural})` : "";
    }
  };
  useLayoutEffect(press);
  useLayoutEffect(() => {
    document.fonts.ready.then(press);
    document.fonts.addEventListener("loadingdone", press);
    return () => document.fonts.removeEventListener("loadingdone", press);
  }, []);
  const listed = mode && at && (
    <div ref={list} className="written listed" style={{ ...writtenStyle({ ...block, props: { ...block.props, trace: undefined, fade: undefined } }, k), color: plain ? undefined : "#aaaaaa" }}>
      {shown.map((word, i) => (
        <div className="row" key={i} style={{ height: row * k }}>
          {mode === "row"
            ? Array.from({ length: Math.min(200, Math.ceil(block.w / (size * s * 0.3 * Math.max(1, word.length))) + 1) }, (_, j) => <span key={j}>{word}</span>)
            : <span style={fold ? { width: Math.max(0, first - indentOf(block)) * k, overflow: "hidden" } : undefined}>{fold ? <span style={{ display: "inline-block", transformOrigin: "left" }}>{word}</span> : word}</span>}
        </div>
      ))}
    </div>
  );
  return (
    <div>
      <svg className="ruling" data-trace={karoLook} data-fade={karoFade} viewBox={`0 0 ${block.w} ${block.h}`} stroke={block.props.color} strokeWidth={0.2}>
        {/* The middle band lies between a row's second and third line. */}
        {zones && bandOf(block) && each(rows).map((top) => <rect key={top} className="band" y={top + zones[1]} width={block.w} height={zones[2] - zones[1]} fill={bandColorOf(block) ?? block.props.color} fillOpacity={bandColorOf(block) ? 1 : 0.12} stroke="none" />)}
        {ys.map((y) => (
          <line key={y} x2={at ? block.w : cols * row} y1={y} y2={y} />
        ))}
        {/* A house stands on each row's left end, over the lines: its roof, its room and its cellar. */}
        {zones && houseOf(block) && each(rows).map((top) => {
          const w = houseWidth(kindOf(block.props.kind));
          const tint = houseTintOf(block);
          return (
            <g key={top} className="house">
              <polygon className="roof" points={`0,${top + zones[1]} ${w / 2},${top + zones[0]} ${w},${top + zones[1]}`} fill={tint === "all" ? HOUSE.roof : "none"} strokeLinejoin="round" />
              <rect className="room" x={0} y={top + zones[1]} width={w} height={zones[2] - zones[1]} fill={tint ? HOUSE.room : "none"} strokeLinejoin="round" />
              <rect className="cellar" x={0} y={top + zones[2]} width={w} height={zones[3] - zones[2]} fill={tint === "all" ? HOUSE.cellar : "none"} strokeLinejoin="round" />
            </g>
          );
        })}
        {!at && each(cols + 1).map((x) => <line key={x} x1={x} x2={x} y2={rows * row} />)}
        {!at && cols > 0 && squares(mode ? karo : text, cols).map(([x, y, ch], i) => y < rows && (
          <text key={-i - 1} x={(x + 0.5) * row} y={(y + 0.5) * row} fontFamily="Andika" fontSize={size} textAnchor="middle" dominantBaseline="central" fill={mode ? (plain ? "currentColor" : "#aaaaaa") : karoLook === "grey" ? "#aaaaaa" : karoLook === "outline" ? "none" : "currentColor"} stroke={karoLook === "outline" ? "currentColor" : "none"} strokeWidth={karoLook === "outline" ? size * 0.035 : undefined} opacity={karoFade && fadeAt(karoFade === "row" ? x : y, karoFade === "row" ? cols : rows)}>
            {ch}
          </text>
        ))}
        {/* The fold line between the words and the first empty column, and the lines between the empty columns:
            twice as thick as the rows' lines, so they show on Karo, where they lie on a line of the squares. */}
        {fold && (
          <>
            <line className="fold" x1={first} x2={first} y1={0} y2={rows * row} strokeWidth={0.4} strokeDasharray="2 1.5" />
            {Array.from({ length: folds - 1 }, (_, i) => (i + 2) * first).map((x) => (
              <line key={x} className="col" x1={x} x2={x} y1={0} y2={rows * row} strokeWidth={0.4} />
            ))}
            <text className="knick" x={first} y={-1} textAnchor="middle" fontFamily="Andika" fontSize={8 * PT} stroke="none" fill="#555555">
              knicken
            </text>
          </>
        )}
      </svg>
      {mode ? listed : (
        <>
          {children ?? (at && text && <p className="written" data-trace={traceOf(block.props)} data-fade={fadeOf(block.props)} style={writtenStyle(block, k)}>{text}</p>)}
          {/* The editor's field holds the text as a value, which no bow can measure: a hidden copy of it does. */}
          {at && text && (block.props.syllables || block.props.tints) && (
            <>
              {/* With colours the copy shows and the field's letters go clear, as in a table's open cell, so the colours stay while typing. */}
              {children && <p className={classes("written", "copy", pairOf(block.props.tints) && "shown")} aria-hidden="true" data-trace={traceOf(block.props)} style={{ ...writtenStyle(block, k), visibility: pairOf(block.props.tints) ? undefined : "hidden" }}>{text}</p>}
              <Bows block={block} base={FONTS[fontOf(block.props.font)][2]} breaks={block.props.breaks} syllables={block.props.syllables} tints={pairOf(block.props.tints)} tintsAcross={block.props.tintsAcross} />
            </>
          )}
        </>
      )}
    </div>
  );
}

// The lines are the borders of the cells, so they close at every corner. The rows have no set height: the grid
// makes each as high as its cells need and stretches them all by the same share of what is left. A text lies in
// the middle of its cell's height. The editor passes the field for the cell `at`, counted row by row: the cell's
// own text, unseen, keeps the field as high as its lines.
function Table({ block, k, at, reach, solved, children }: { block: TableBlock; k: number; at?: number; reach?: number; solved: boolean; children?: ReactNode }) {
  const { cells, cols, line, head, syllables, breaks, tintsAcross, gaps } = block.props;
  const tints = pairOf(block.props.tints);
  const width = gapWidth(block.props.gapWidth);
  const words = typeof block.props.bank === "number" && Number.isFinite(block.props.bank) ? cellEntries(cells, gaps) : [];
  const heights = heightsOf(block.props);
  // A table with one of the new keys draws its lines in svgs laid over the cells, so the borders of the cells go
  // transparent: they keep their pixel in the layout and only the ink goes. An old table gets none of this.
  const styled = edged(block.props);
  const lineAt = linesOf(block.props);
  const plain = linesOf({ ...block.props, edges: undefined })("v", 0, 0);
  // One line of the grid, from one end to the other. A dashed or dotted line is drawn from each end to its middle,
  // so that the dashes start fresh at both ends and every corner gets a piece of dash from each side.
  const rim = (side: string, pen: Pen, [a, b, mid]: string[][]) => {
    if (pen.style === "none") return null;
    const w = pen.width * k;
    const pieces = pen.style === "solid" ? [[a, b]] : [[a, mid], [b, mid]];
    const dashes = pen.style === "dashed" ? { strokeDasharray: `${3 * w} ${4 * w}`, strokeDashoffset: 1.5 * w } : pen.style === "dotted" ? { strokeDasharray: `0 ${2.5 * w}` } : {};
    // The period of the dashes, which `fit` changes so that a whole number of them lies on the edge.
    const period = pen.style === "dashed" ? 7 * w : pen.style === "dotted" ? 2.5 * w : undefined;
    return pieces.map(([p, q], i) => (
      <line key={i} data-side={side} data-style={pen.style} data-period={period} data-w={w} x1={p[0]} y1={p[1]} x2={q[0]} y2={q[1]} stroke={line} strokeWidth={w} strokeLinecap={pen.style === "dotted" ? "round" : "square"} {...dashes} />
    ));
  };
  // Each dashed or dotted line gets a whole number of periods along its edge, so that the two halves meet in the
  // middle of a dash or a gap and no dash is doubled. It reads the sizes the layout already has, and does not change them.
  const host = useRef<HTMLDivElement>(null);
  const fit = (el: HTMLElement) => {
    const zoom = el.getBoundingClientRect().width / el.offsetWidth || 1;
    for (const svg of el.querySelectorAll<SVGSVGElement>(":scope > svg.edge")) {
      // Not clientWidth: that is whole pixels, and a column is seldom a whole number of them wide.
      const { width, height } = svg.getBoundingClientRect();
      const [across, down] = [width / zoom, height / zoom];
      for (const line of svg.querySelectorAll<SVGLineElement>("line[data-period]")) {
        const side = line.dataset.side;
        const length = side === "top" || side === "bottom" ? across : down;
        if (!(length > 0)) continue;
        const period = Number(line.dataset.period);
        const w = Number(line.dataset.w);
        // A dot right at the end of its half is not drawn, by either half: so the dots are an odd number of
        // periods, and the middle of the edge lies between two of them.
        const n = length / period;
        const f = n / Math.max(1, line.dataset.style === "dotted" ? 2 * Math.round((n - 1) / 2) + 1 : Math.round(n));
        if (line.dataset.style === "dashed") {
          // An edge shorter than two of its line's widths has room for the caps of one dash and no more.
          const dash = Math.max(0, 4 * w * f - w);
          line.setAttribute("stroke-dasharray", `${dash} ${7 * w * f - dash}`);
          line.setAttribute("stroke-dashoffset", String(dash / 2));
        } else line.setAttribute("stroke-dasharray", `0 ${2.5 * w * f}`);
      }
    }
  };
  useLayoutEffect(() => {
    if (styled && host.current) fit(host.current);
  });
  // The sizes change when a font comes in or a row grows, and the fit follows them.
  useLayoutEffect(() => {
    const el = host.current;
    if (!styled || !el) return;
    const watch = new ResizeObserver(() => fit(el));
    watch.observe(el);
    el.querySelectorAll(":scope > svg.edge").forEach((svg) => watch.observe(svg));
    // The page that prints waits for the fonts and no longer: the fit is asked for before it, so it runs first.
    document.fonts.ready.then(() => fit(el));
    return () => watch.disconnect();
  }, [styled, cells.length, cols.length]);
  const TOP = [["0", "0"], ["100%", "0"], ["50%", "0"]];
  const BOTTOM = [["0", "100%"], ["100%", "100%"], ["50%", "100%"]];
  const LEFT = [["0", "0"], ["0", "100%"], ["0", "50%"]];
  const RIGHT = [["100%", "0"], ["100%", "100%"], ["100%", "50%"]];
  const style = {
    ...textStyle({ text: "", ...block.props }, k),
    borderColor: styled ? "transparent" : line,
    gridTemplateColumns: cols.map((c) => `minmax(0, ${c}fr)`).join(" "),
    ...(heights && { gridTemplateRows: heights.map((h) => `minmax(${h * k}px, auto)`).join(" ") }),
    "--edge": `${0.25 * k}px`,
    ...gapVar(width, k),
  };
  // A gap cell holds its text as a gap does; the open cell's field goes after it.
  const wrap = (text: string, i: number) => (gaps?.[Math.floor(i / cols.length)]?.[i % cols.length] === true ? <span className="gap" data-gap="true"><span>{text}</span></span> : text);
  // A trace text fades cell by cell: along the row for "row", from row to row for "rows". The lines stay solid.
  const fade = fadeOf(block.props);
  const shade = (i: number): CSSProperties | undefined =>
    fade && { opacity: fade === "row" ? fadeAt(i % cols.length, cols.length) : fadeAt(Math.floor(i / cols.length), cells.length) };
  // A merged cell is drawn once, over the cells it covers: those are not drawn, and each drawn cell takes its place in the grid.
  const spans = spansOf(block.props);
  const anchors = new Map(spans.map((s) => [s[0] * cols.length + s[1], s]));
  const covered = new Set(spans.flatMap(([r, c, h, w]) => Array.from({ length: h * w }, (_, n) => (r + Math.floor(n / w)) * cols.length + c + (n % w)).slice(1)));
  const place = (i: number) => spans.length > 0 && { gridRow: `${Math.floor(i / cols.length) + 1} / span ${anchors.get(i)?.[2] ?? 1}`, gridColumn: `${(i % cols.length) + 1} / span ${anchors.get(i)?.[3] ?? 1}` };
  // The cells of a selection of two or more are picked. The selection is whole, so a cell lies in it by its row and column.
  const area = at !== undefined && reach !== undefined ? rectOf(block.props, at, reach) : undefined;
  const picked = (i: number) => {
    if (!area || (area[2] - area[0] + 1) * (area[3] - area[1] + 1) < 2) return false;
    const r = Math.floor(i / cols.length);
    const c = i % cols.length;
    return r >= area[0] && r <= area[2] && c >= area[1] && c <= area[3];
  };
  return (
    <div ref={host} className={classes("table", tints && "tinted", solved && "solved", width && "even", styled && "edged")} data-trace={traceOf(block.props)} data-fade={fade} style={style as CSSProperties}>
      {cells.flat().map((text, i) => {
        const span = anchors.get(i);
        if (covered.has(i)) return null;
        return (
          <div key={i} data-cell={i} data-span={span && `${span[2]}x${span[3]}`} className={picked(i) ? "picked" : undefined} style={{ fontWeight: head && i < cols.length ? 700 : undefined, ...(place(i) || undefined) }}>
            {i === at ? <p className="open" style={shade(i)}>{wrap(text, i)}&#8203;{children}</p> : <p style={shade(i)}>{wrap(text, i)}</p>}
          </div>
        );
      })}
      {(syllables || tints) && <Bows block={block} base={FONTS[fontOf(block.props.font)][2]} breaks={breaks} syllables={syllables} tints={tints} tintsAcross={tintsAcross} solved={solved} />}
      {words.length > 0 && <Bank words={words} seed={block.props.bank!} />}
      {/* Each grid position: its top and left line, and at the rim the bottom and right ones. The scissors sit at the top left. */}
      {styled && cells.flatMap((_, r) => cols.map((_c, c) => (
        <svg key={`e${r}-${c}`} className="edge" data-edge={r * cols.length + c} style={{ gridRow: `${r + 1} / ${r + 2}`, gridColumn: `${c + 1} / ${c + 2}` }}>
          <g transform="translate(-0.5 -0.5)">
            {rim("top", lineAt("h", r, c), TOP)}
            {rim("left", lineAt("v", r, c), LEFT)}
            {r === cells.length - 1 && rim("bottom", lineAt("h", r + 1, c), BOTTOM)}
            {c === cols.length - 1 && rim("right", lineAt("v", r, c + 1), RIGHT)}
            {r === 0 && c === 0 && block.props.cut === true && (
              <g className="scissors">
                <Scissors size={4 * k} x={-4.5 * k} y={-2 * k} color={line} />
              </g>
            )}
          </g>
        </svg>
      )))}
      {/* The box of solution words takes the table's style on its left, right and bottom: its top is the table's bottom. */}
      {styled && words.length > 0 && (
        <svg className="edge" data-edge="bank" style={{ gridRow: `${cells.length + 1} / ${cells.length + 2}`, gridColumn: "1 / -1" }}>
          <g transform="translate(-0.5 -0.5)">
            {rim("left", plain, LEFT)}
            {rim("right", plain, RIGHT)}
            {rim("bottom", plain, BOTTOM)}
          </g>
        </svg>
      )}
    </div>
  );
}

// A number of an exercise, or the gap in its place. The answer key fills the gap.
// With Geld a number has its euro after it, outside the gap. The rest of a division is never a decimal.
function Part({ e, part, solved, d, money }: { e: Calc; part: "a" | "b" | "c" | "result" | "rest"; solved: boolean; d: number; money: boolean }) {
  const gap = part === "rest" || part === (e.hide ?? "result");
  const text = part === "rest" ? decimal(e.rest, 0) : decimal(e[part] as number, d, money);
  const euro = money && part !== "rest" ? " €" : "";
  return <>{gap ? <u>{solved && text}</u> : text}{euro}</>;
}

// One side of a comparison as it reads: a number, or a term with its sign.
const side = (s: Side) => (s.op ? `${decimal(s.a as number, 0)} ${SIGNS[s.op] ?? s.op} ${decimal(s.b as number, 0)}` : decimal(s.value, 0));

// A written exercise: squared paper with a character to a square. All of a block's exercises get the same paper.
// A square is `S` units wide: with a square of one unit a digit is under a unit high, and Chromium sets so small a
// type a whole square too high, on the screen and in every PDF (issue #446).
function Karo({ grid, cols, rows, k, solved }: { grid: Grid; cols: number; rows: number; k: number; solved: boolean }) {
  const S = 10;
  const each = (n: number) => Array.from({ length: n + 1 }, (_, i) => i * S);
  return (
    <svg width={cols * KARO * k} height={rows * KARO * k} viewBox={`0 0 ${cols * S} ${rows * S}`} style={{ width: `calc(${cols * KARO * k}px * var(--fit, 1))`, height: `calc(${rows * KARO * k}px * var(--fit, 1))` }}>
      <g stroke="#9db4c8" strokeWidth={0.03 * S}>
        {each(cols).map((x) => <line key={x} x1={x} x2={x} y2={rows * S} />)}
        {each(rows).map((y) => <line key={-y - 1} x2={cols * S} y1={y} y2={y} />)}
      </g>
      {grid.lines.map(([x1, x2, y, kind], i) => (solved || !kind) && <line key={i} className={kind ? "answer" : ""} x1={x1 * S} x2={x2 * S} y1={y * S} y2={y * S} stroke="currentColor" strokeWidth={0.08 * S} />)}
      {grid.cells.map(([x, y, ch, kind], i) => (solved || !kind) && (
        <text key={i} className={kind ? "answer" : ""} x={(x + 0.5) * S} y={(y + 0.5) * S} fontSize={(kind === 2 ? 0.45 : 0.75) * S} textAnchor="middle" dominantBaseline="central" fill="currentColor">
          {ch}
        </text>
      ))}
    </svg>
  );
}

// The scale each maths block draws at, by block id: below 1 when its tasks are too wide for it. The panel shows it as a hint.
// It is measured on the screen and kept nowhere in the document.
const scales = new Map<string, number>();
const scaleListeners = new Set<() => void>();
export function subscribe(listen: () => void) {
  scaleListeners.add(listen);
  return () => void scaleListeners.delete(listen);
}
export const scaleOf = (id: string) => scales.get(id) ?? 1;

function Maths({ block, k, solved }: { block: MathsBlock; k: number; solved: boolean }) {
  const p = block.props;
  const letters = useLetters(block.id);
  const cols = Math.max(0, ...p.exercises.map((e) => ("sign" in e ? 0 : e.grid?.cols ?? 0)));
  const rows = Math.max(0, ...p.exercises.map((e) => ("sign" in e ? 0 : e.grid?.rows ?? 0)));
  const d = decimalsOf(p);
  const money = d > 0 && !!p.money;
  const root = useRef<HTMLDivElement>(null);
  // A gap holds the longest number, with its comma and its places after it. Each group gap of its thousands takes a bit more.
  const groupGaps = decimal(p.max, 0).split(GAP).length - 1;
  const style = { fontSize: `calc(${p.size * PT * k}px * var(--fit, 1))`, gridTemplateColumns: `repeat(${p.columns}, 1fr)`, "--gap": `${String(p.max).length + 1.5 + (d ? d + 1 : 0) + 0.3 * groupGaps}ch` };
  const num = { solved, d, money };
  // Tasks wider than the block shrink the type, as PowerPoint shrinks a text. Everything inside is in em, so the
  // width is linear in the scale and one measurement is enough.
  function fit() {
    const el = root.current;
    if (!el) return;
    el.style.removeProperty("--fit");
    // The numbers take the width of the widest one, in em so it scales with the type. offsetWidth is the laid out
    // width, whole pixels and blind to a turn of the block; one pixel more holds the fraction it drops.
    el.style.removeProperty("--num");
    const marks = [...el.querySelectorAll<HTMLElement>("b")];
    if (marks.length) el.style.setProperty("--num", `${(Math.max(...marks.map((b) => b.offsetWidth)) + 1) / parseFloat(getComputedStyle(el).fontSize)}em`);
    // A block with no width to speak of has no scale: it would come out below nothing.
    const over = el.clientWidth > 2 && el.scrollWidth > el.clientWidth + 1;
    // Two pixels of room: the paper's outer line lies half outside its svg, and the block cuts what leaves it.
    const scale = over ? (el.clientWidth - 2) / el.scrollWidth : 1;
    if (over) el.style.setProperty("--fit", String(scale));
    if (scales.get(block.id) !== scale) {
      scales.set(block.id, scale);
      scaleListeners.forEach((listen) => listen());
    }
  }
  useLayoutEffect(() => {
    fit();
  });
  // The fonts load after the first layout, and a wider letter makes a wider task. A cut loads when it is first
  // needed: the bold one with the numbering.
  useLayoutEffect(() => {
    document.fonts.ready.then(fit);
    document.fonts.addEventListener("loadingdone", fit);
    return () => document.fonts.removeEventListener("loadingdone", fit);
  }, []);
  // The numbering runs through every task. With families, the tasks of one family stand together in one grid item.
  const task = (e: Exercise, i: number) => (
    <div key={i}>
      {p.numbering && <b><Count mark={p.numbering} n={i + 1} /></b>}
      {"sign" in e ? (
        // The ring is empty for the pupil to write the sign in; the answer key writes it there.
        <span>
          {side(e.left)} <i className="ring">{solved && e.sign}</i> {side(e.right)}
        </span>
      ) : e.grid ? (
        <Karo grid={e.grid} cols={cols} rows={rows} k={k} solved={solved} />
      ) : e.op2 ? (
        // The brackets stand against their numbers, as written: `(2 + 3) · 4` or `2 · (3 + 4)`.
        <span>
          {e.paren === "left" && "("}<Part e={e} part="a" {...num} /> {SIGNS[e.op] ?? e.op} {e.paren === "right" && "("}<Part e={e} part="b" {...num} />{e.paren === "left" && ")"} {SIGNS[e.op2] ?? e.op2} <Part e={e} part="c" {...num} />{e.paren === "right" && ")"} = <Part e={e} part="result" {...num} />
        </span>
      ) : (
        <span>
          <Part e={e} part="a" {...num} /> {SIGNS[e.op] ?? e.op} <Part e={e} part="b" {...num} /> = <Part e={e} part="result" {...num} />
          {e.rest > 0 && <> R <Part e={e} part="rest" {...num} /></>}
        </span>
      )}
      {letters && <span className="letter" data-task={i}>{solved ? letters[i] ?? "" : ""}</span>}
    </div>
  );
  // Consecutive exercises of one family share a group; a task with no family is a group of its own.
  const groups: number[][] = [];
  let prev: number | undefined;
  p.exercises.forEach((e, i) => {
    const family = "sign" in e ? undefined : e.family;
    if (family !== undefined && family === prev) groups[groups.length - 1].push(i);
    else groups.push([i]);
    prev = family;
  });
  const families = p.exercises.some((e) => !("sign" in e) && e.family !== undefined);
  return (
    // The format's class has a name of its own: `gap` and `written` are a text's gap and a Lineatur's text.
    <div ref={root} className={`maths maths-${p.format}${solved ? " solved" : ""}`} style={style as CSSProperties}>
      {groups.map((g) => (families ? <div key={g[0]} className="family">{g.map((i) => task(p.exercises[i], i))}</div> : task(p.exercises[g[0]], g[0])))}
      {!p.exercises.length && <span className="hint">Keine Aufgabe möglich</span>}
    </div>
  );
}

// A word search: squared paper with a letter to a square, the hidden words ringed once solved, and the words or
// their count under the grid. It draws in its own units, so it scales to the room its block gives it. A square is
// `S` units wide: with a square of one unit the letters are under a unit high, and Chromium sets so small a type a
// whole square too high.
function Suchsel({ block, k, solved }: { block: SuchselBlock; k: number; solved: boolean }) {
  const p = sane(block.props);
  const { grid, hidden } = laid(p);
  const S = 10;
  const [wide, high] = [p.cols * S, p.rows * S];
  const each = (n: number) => Array.from({ length: n - 1 }, (_, i) => (i + 1) * S);
  return (
    <div className={`suchsel${solved ? " solved" : ""}`} style={{ fontSize: 12 * PT * k }}>
      <svg viewBox={`0 0 ${wide} ${high}`} preserveAspectRatio="xMidYMin meet" style={{ aspectRatio: `${p.cols} / ${p.rows}` }}>
        <g className="mesh" stroke="#9db4c8" strokeWidth={0.3}>
          {each(p.cols).map((x) => <line key={`x${x}`} x1={x} x2={x} y1={0} y2={high} />)}
          {each(p.rows).map((y) => <line key={`y${y}`} x1={0} x2={wide} y1={y} y2={y} />)}
        </g>
        <rect className="edge" x={0} y={0} width={wide} height={high} fill="none" stroke="#222" strokeWidth={0.6} />
        {grid.map((row, r) => row.map((letter, c) => (
          <text key={`${c},${r}`} data-at={`${c},${r}`} x={(c + 0.5) * S} y={(r + 0.5) * S} fontSize={0.62 * S} textAnchor="middle" dominantBaseline="central" fill="#222">{letter}</text>
        )))}
        {solved && hidden.map((h) => {
          const n = h.letters.length;
          const length = ((n - 1) * Math.hypot(h.dc, h.dr) + 0.8) * S;
          const cx = (h.col + 0.5 + (h.dc * (n - 1)) / 2) * S;
          const cy = (h.row + 0.5 + (h.dr * (n - 1)) / 2) * S;
          const angle = (Math.atan2(h.dr, h.dc) * 180) / Math.PI;
          return (
            <rect key={`${h.word}${h.col},${h.row}`} className="ring answer" data-word={h.word} data-col={h.col} data-row={h.row} data-dc={h.dc} data-dr={h.dr} data-n={n}
              x={cx - length / 2} y={cy - 0.4 * S} width={length} height={0.8 * S} rx={0.4 * S} ry={0.4 * S} strokeWidth={0.6} transform={`rotate(${angle} ${cx} ${cy})`} />
          );
        })}
      </svg>
      {p.show === "words" && hidden.length > 0 && (
        <ul className="found">{hidden.map((h) => <li key={`${h.word}${h.col},${h.row}`}>{h.word}</li>)}</ul>
      )}
      {p.show === "count" && hidden.length > 0 && (
        <p className="found">Finde {hidden.length} {hidden.length === 1 ? "Wort" : "Wörter"}.</p>
      )}
    </div>
  );
}

// A Zahlenmauer: its walls in columns, row by row, in its own units. A stone is twice as wide as high, and a row
// sits half a stone right of the one under it, so a wall is as wide as its base row. The svg scales with the block.
function Zahlenmauer({ block, solved }: { block: ZahlenmauerBlock; k: number; solved: boolean }) {
  const p = saneWall(block.props);
  const { walls } = walled(p);
  const { S, wallW, wallH, gap, vbW, vbH } = wallLayout(p);
  const letters = useLetters(block.id);
  // A wrong wall gives no task, and a block with `empty` none: the letter boxes number the walls that have one.
  let next = 0;
  const task = walls.map((w) => (w.wrong || p.empty || w.given.every(Boolean) ? -1 : next++));
  return (
    <div className={`zahlenmauer${solved ? " solved" : ""}`}>
      {/* Half a unit of room around the walls, so the lines at the edge show whole. */}
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {walls.map((w, i) => {
          const [x0, y0] = [(i % p.columns) * (wallW + gap), Math.floor(i / p.columns) * (wallH + gap)];
          const stones = Array.from({ length: p.base }, (_, r) => Array.from({ length: p.base - r }, (_, c) => {
            const s = at(p.base, r, c);
            const [x, y] = [x0 + r * S + c * 2 * S, y0 + (p.base - 1 - r) * S];
            const shows = !p.empty && (w.given[s] || (solved && !w.wrong));
            return (
              <g key={s} className="stone" data-stone={s} data-row={r} data-col={c}>
                <rect x={x} y={y} width={2 * S} height={S} fill="white" stroke="#222" strokeWidth={0.4} />
                {shows && (
                  <text x={x + S} y={y + S / 2} fontSize={0.6 * S} textAnchor="middle" dominantBaseline="central"
                    fill={w.given[s] ? "#222" : "#c0392b"} className={w.given[s] ? "given" : "answer"}>{w.numbers[s]}</text>
                )}
              </g>
            );
          }));
          // The box stands at the right end of the top row, in the empty corner above the stones beside it.
          const t = task[i];
          return (
            <g key={i} className={`wall${w.wrong ? " wrong" : ""}`} data-wall={i}>
              {stones.flat()}
              {letters && t >= 0 && <LetterBox x={x0 + (p.base + 1.2) * S} y={y0} side={0.8 * S} task={t} letter={letters[t] ?? ""} solved={solved} />}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// A Rechendreieck: its triangles in columns, in its own units. A triangle has sides of 60 units: its inner fields
// are circles just inside the corners, its outer fields rectangles beyond the middle of each side. The svg scales
// with the block.
function Rechendreieck({ block, solved }: { block: RechendreieckBlock; k: number; solved: boolean }) {
  const p = saneRechen(block.props);
  const { triangles } = drawnRechen(p);
  const { GAP, RING, BOX, corner, inner, outer, minX, cellW, cellH, cols, vbW, vbH } = layout(p);
  const letters = useLetters(block.id);
  // A wrong triangle gives no task, and a block with `empty` none: the letter boxes number the triangles that have one.
  let next = 0;
  const task = triangles.map((tri) => (tri.wrong || p.empty || tri.given.every(Boolean) ? -1 : next++));
  return (
    <div className={`rechendreieck${solved ? " solved" : ""}`}>
      {/* Half a unit of room around the triangles, so the lines at the edge show whole. */}
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {triangles.map((tri, t) => {
          const [x, y] = [(t % cols) * (cellW + GAP) - minX, Math.floor(t / cols) * (cellH + GAP)];
          return (
            <g key={t} className={`triangle${tri.wrong ? " wrong" : ""}`} data-triangle={t} transform={`translate(${x} ${y})`}>
              <polygon points={corner.map((c) => c.join(",")).join(" ")} fill="none" stroke="#222" strokeWidth={0.6} />
              {/* The box stands at the top left of the triangle's cell, its side the height of an outer field. */}
              {letters && task[t] >= 0 && <LetterBox x={minX} y={0} side={BOX[1]} task={task[t]} letter={letters[task[t]] ?? ""} solved={solved} />}
              {Array.from({ length: RECHEN_FIELDS }, (_, j) => {
                const [cx, cy] = j < 3 ? inner[j] : outer[j - 3];
                const shows = !p.empty && (tri.given[j] || (solved && !tri.wrong));
                return (
                  <g key={j} className="field" data-field={j}>
                    {j < 3
                      ? <circle cx={cx} cy={cy} r={RING} fill="white" stroke="#222" strokeWidth={0.4} />
                      : <rect x={cx - BOX[0] / 2} y={cy - BOX[1] / 2} width={BOX[0]} height={BOX[1]} fill="white" stroke="#222" strokeWidth={0.4} />}
                    {shows && (
                      <text x={cx} y={cy} fontSize={5.5} textAnchor="middle" dominantBaseline="central"
                        fill={tri.given[j] ? "#222" : "#c0392b"} className={tri.given[j] ? "given" : "answer"}>{tri.numbers[j]}</text>
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// A Zahlenstrahl, drawn in the block's mm as the contract at the top of zahlenstrahl.ts says.
function Zahlenstrahl({ block, solved }: { block: ZahlenstrahlBlock; k: number; solved: boolean }) {
  const p = saneStrahl(block.props);
  const { w } = block;
  const { ticks, arrows, arcs } = drawnStrahl(p, w);
  const FS = (p.size * 25.4) / 72;
  const tickX = (v: number) => xOf((v - p.start) / p.minor, ticks.length, w);
  // An arc's height above the line: a wide jump stays a flat arc.
  const rise = (a: { from: number; to: number }) => Math.min(((tickX(a.to) - tickX(a.from)) / 2) * 0.7, 6);
  // The room the line needs below it, and above it for its ticks, or its arcs and their numbers (an arrow's number
  // keeps inside by itself). A block too short for both, saved so or held at the page's foot, draws the whole line a
  // little smaller, so nothing leaves it.
  const room = below(p, w);
  const h = Math.max(block.h, room + Math.max(3.5, ...arcs.map((a) => rise(a) + 2 + 0.8 * FS)));
  const y = h - room;
  const cut = p.cut && p.start > 0;
  const axs = arrowXs(arrows.length, ticks.length, w);
  // An arrow's number stands on the baseline y - 7.6, raised when its digits would pass the block's top; its stub
  // runs from under the digits to y - 5, and is left out where a short block leaves no room for it.
  const base = Math.max(y - 7.6, 0.75 * FS);
  return (
    <div className={`zahlenstrahl${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${w} ${h}`}>
        <line className="axis" x1={cut ? 0.5 : STRAHL_LEFT - 2} y1={y} x2={w - 2.5} y2={y} stroke="#222" strokeWidth={0.4} />
        <path className="head" d={`M ${w - 3.2} ${y - 1.2} L ${w - 1} ${y} L ${w - 3.2} ${y + 1.2} Z`} fill="#222" />
        {cut && (
          <g className="cut" stroke="#222" strokeWidth={0.4}>
            <line x1={2.1} y1={y + 1.6} x2={2.9} y2={y - 1.6} />
            <line x1={3.1} y1={y + 1.6} x2={3.9} y2={y - 1.6} />
          </g>
        )}
        {ticks.map((t, i) => {
          const x = xOf(i, ticks.length, w);
          const reach = t.long ? 3 : 1.5;
          // The box's size, and a box that would cover a number shown beside it, which goes one row lower.
          const { bw, bh, covers, dy } = t.task === "box" ? boxUnder(ticks, i, w, p.size) : { bw: 0, bh: 0, covers: false, dy: 0 };
          const top = y + dy;
          // The leader stops short of a shown number's digits where one stands on it. A digit is taken as 0.65 em wide,
          // more than Andika's, so a line that only grazes a number breaks too.
          const through = covers && ticks.some((o, j) => o.label && !o.task && j !== i && Math.abs(xOf(j, ticks.length, w) - x) <= (String(o.value).length * 0.65 * FS) / 2 + 0.5);
          const gapTop = y + 4.5;
          const gapBottom = y + 5 + 0.75 * FS + 0.5;
          return (
            <g key={t.value} className={`tick${t.long ? " long" : ""}`} data-value={t.value}>
              <line x1={x} y1={y - reach} x2={x} y2={y + reach} stroke="#222" strokeWidth={0.4} />
              {t.label && !t.task && (
                <text className="label" x={x} y={y + 5} fontSize={FS} textAnchor="middle" dominantBaseline="hanging" fill="#222">{t.value}</text>
              )}
              {t.task === "box" && (
                <g className="box">
                  {covers && !through && <line x1={x} y1={y + reach} x2={x} y2={top} stroke="#222" strokeWidth={0.2} />}
                  {covers && through && (
                    <>
                      <line x1={x} y1={y + reach} x2={x} y2={gapTop} stroke="#222" strokeWidth={0.2} />
                      <line x1={x} y1={gapBottom} x2={x} y2={top} stroke="#222" strokeWidth={0.2} />
                    </>
                  )}
                  <rect x={x - bw / 2} y={top} width={bw} height={bh} fill="none" stroke="#222" strokeWidth={0.3} />
                  {solved && (
                    <text className="answer" x={x} y={top + bh / 2} fontSize={FS} textAnchor="middle" dominantBaseline="central" fill="#c0392b">{t.value}</text>
                  )}
                </g>
              )}
            </g>
          );
        })}
        {arrows.map((v, k) => {
          const ax = axs[k];
          return (
            <g key={v} className="arrow" data-value={v}>
              <text className="given" x={ax} y={base} fontSize={FS} textAnchor="middle" fill="#222">{v}</text>
              {base + 0.4 < y - 5 && <line x1={ax} y1={Math.max(base + 0.4, y - 7)} x2={ax} y2={y - 5} stroke="#222" strokeWidth={0.4} />}
              {solved && <path className="answer" d={`M ${ax} ${y - 5} L ${tickX(v)} ${y - 0.5}`} fill="none" stroke="#c0392b" strokeWidth={0.4} />}
            </g>
          );
        })}
        {arcs.map((a) => {
          const [x1, x2] = [tickX(a.from), tickX(a.to)];
          const [rx, ry] = [(x2 - x1) / 2, rise(a)];
          return (
            <g key={`${a.from}-${a.to}`} className="arc" data-from={a.from} data-to={a.to}>
              <path d={`M ${x1} ${y - 0.5} A ${rx} ${ry} 0 0 1 ${x2} ${y - 0.5}`} fill="none" stroke="#222" strokeWidth={0.3} />
              <text x={x1 + rx} y={y - ry - 2} fontSize={FS} textAnchor="middle" fill="#222">{a.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// An Uhr, drawn as the contract at the top of uhr.ts says: one svg, a cell of 100 by 130 per clock.
function Uhr({ block, solved }: { block: UhrBlock; k: number; solved: boolean }) {
  const p = saneUhr(block.props);
  const letters = useLetters(block.id);
  const times = timesOf(p);
  const cols = Math.min(p.cols, times.length);
  const rows = Math.ceil(times.length / cols);
  // A point of the face at `r` from the centre, `deg` degrees clockwise from 12.
  const polar = (r: number, deg: number) => [50 + r * Math.sin((deg * Math.PI) / 180), 50 - r * Math.cos((deg * Math.PI) / 180)];
  const hour = (n: number, r: number) => polar(r, 30 * ((n - (n > 12 ? 12 : 0)) % 12));
  return (
    <div className={`uhr${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${CELL_W * cols} ${CELL_H * rows}`}>
        {times.map((t, i) => {
          const [hourDeg, minuteDeg] = hands(t);
          const [hx, hy] = polar(p.ring && p.numbers !== "none" ? 13 : 25, hourDeg);
          const [mx, my] = polar(40, minuteDeg);
          const text = written(t, p);
          const size = Math.min(10, 180 / text.length);
          const numbers = p.numbers === "all" ? [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] : p.numbers === "quarters" ? [3, 6, 9, 12] : [];
          const ring = p.ring && p.numbers !== "none" ? [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24] : [];
          return (
            <g key={i} className="clock" data-i={i} data-time={t} transform={`translate(${CELL_W * (i % cols)} ${CELL_H * Math.floor(i / cols)})`}>
              <circle className="face" cx={50} cy={50} r={46} fill="none" stroke={UHR_INK} strokeWidth={1.2} />
              <g className="ticks">
                {Array.from({ length: 60 }, (_, m) => m)
                  .filter((m) => m % 5 === 0 || p.minutes)
                  .map((m) => {
                    const hourTick = m % 5 === 0;
                    const [x1, y1] = polar(46, 6 * m);
                    const [x2, y2] = polar(hourTick ? 39 : 42.5, 6 * m);
                    return <line key={m} x1={x1} y1={y1} x2={x2} y2={y2} stroke={UHR_INK} strokeWidth={hourTick ? 1.2 : 0.5} />;
                  })}
              </g>
              {numbers.map((n) => {
                const [x, y] = hour(n, 33);
                return (
                  <text key={`n${n}`} className="number" data-n={n} x={x} y={y} fontSize={10} textAnchor="middle" dominantBaseline="central" fill={UHR_INK}>
                    {n}
                  </text>
                );
              })}
              {ring.map((n) => {
                const [x, y] = hour(n, 22);
                return (
                  <text key={`r${n}`} className="number" data-n={n} x={x} y={y} fontSize={5.5} textAnchor="middle" dominantBaseline="central" fill={UHR_INK}>
                    {n}
                  </text>
                );
              })}
              {p.task === "read" && (
                <>
                  <line className="hour" x1={50} y1={50} x2={hx} y2={hy} stroke={UHR_INK} strokeWidth={4.5} strokeLinecap="round" />
                  <line className="minute" x1={50} y1={50} x2={mx} y2={my} stroke={UHR_INK} strokeWidth={1.6} strokeLinecap="round" />
                </>
              )}
              {p.task === "draw" && solved && (
                <>
                  <line className="hour" x1={50} y1={50} x2={hx} y2={hy} stroke={RED} strokeWidth={4.5} strokeLinecap="round" />
                  <line className="minute" x1={50} y1={50} x2={mx} y2={my} stroke={RED} strokeWidth={1.6} strokeLinecap="round" />
                </>
              )}
              <circle className="hub" cx={50} cy={50} r={2.5} fill={UHR_INK} />
              {letters && p.task === "read" && <LetterBox x={84} y={2} side={14} task={i} letter={letters[i] ?? ""} solved={solved} />}
              {p.task === "draw" && (
                <text className="task" x={50} y={120} fontSize={size} textAnchor="middle" fill={UHR_INK}>
                  {text}
                </text>
              )}
              {p.task === "read" && p.answer === "box" && !solved && (
                <text className="task" x={50} y={120} fontSize={10} textAnchor="middle" fill={UHR_INK}>
                  __:__ Uhr
                </text>
              )}
              {p.task === "read" && p.answer === "box" && solved && (
                <text className="answer" x={50} y={120} fontSize={size} textAnchor="middle" fill={RED}>
                  {text}
                </text>
              )}
              {p.task === "read" && p.answer === "line" && (
                <line className="answer" x1={12} y1={122} x2={88} y2={122} stroke={UHR_INK} strokeWidth={0.6} />
              )}
              {p.task === "read" && p.answer === "line" && solved && (
                <text className="answer" x={50} y={120} fontSize={size} textAnchor="middle" fill={RED}>
                  {text}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// A Selbstkontrolle, drawn as the contract at the top of selbstkontrolle.ts says. Its text is in Andika at its size,
// and a content taller than the block shrinks it, as Maths does. Its hint shows in the editor only: Paper hides it.
function Selbstkontrolle({ block, k, solved }: { block: SelbstkontrolleBlock; k: number; solved: boolean }) {
  const p = saneSelbst(block.props);
  const doc = useContext(Whole);
  const check = checked(p, doc);
  const root = useRef<HTMLDivElement>(null);
  function fit() {
    const el = root.current;
    if (!el) return;
    el.style.removeProperty("--fit");
    // A block with no height to speak of has no scale: it would come out below nothing.
    // Too tall or too wide (a long table): it takes the smaller of the two scales. Lines of a pixel do not shrink
    // with the type, so it measures again, up to three times.
    let fit = 1;
    for (let round = 0; round < 3; round++) {
      const tall = el.clientHeight > 2 && el.scrollHeight > el.clientHeight + 1 ? (el.clientHeight - 2) / el.scrollHeight : 1;
      // The content's own width: turned, a table too wide spills to the left, where the block's scrollWidth misses it.
      const inner = (el.querySelector(".inner") as HTMLElement | null)?.scrollWidth ?? 0;
      const spill = Math.max(el.scrollWidth, inner);
      const wide = el.clientWidth > 2 && spill > el.clientWidth + 1 ? (el.clientWidth - 2) / spill : 1;
      if (Math.min(tall, wide) >= 1) break;
      fit *= Math.min(tall, wide);
      el.style.setProperty("--fit", String(fit));
    }
  }
  useLayoutEffect(() => {
    fit();
  });
  useLayoutEffect(() => {
    document.fonts.ready.then(fit);
    document.fonts.addEventListener("loadingdone", fit);
    return () => document.fonts.removeEventListener("loadingdone", fit);
  }, []);
  const whole = check.lost.length === 0;
  const hint = check.lost.length ? "Die Selbstkontrolle hat ihre Quelle verloren." : check.empty ? "Wähle rechts die Blöcke, die die Selbstkontrolle prüft." : check.fault;
  return (
    <div ref={root} className={`selbstkontrolle${solved ? " solved" : ""}${p.turn === "none" ? "" : ` ${p.turn}`}`} style={{ fontSize: `calc(${p.size * PT * k}px * var(--fit, 1))` }}>
      {whole && p.turn === "fold" && <div className="fold">Hier umknicken</div>}
      <div className="inner">
        {whole && p.title && <h3 className="title">{p.title}</h3>}
        {whole && p.form === "mixed" && <ul className="mixed">{check.mixed.map((text, i) => <li key={i}><span className="tick" />{text}</li>)}</ul>}
        {whole && p.form === "sum" && <ul className="sums">{check.sums.map(([label, text], i) => <li key={i}>{`${label}: ${text}`}</li>)}</ul>}
        {whole && p.form === "word" && !check.fault && (
          <>
            <table className="word">
              <tbody>
                <tr className="results">{check.table.map(([text], i) => <td key={i}>{text}</td>)}</tr>
                <tr className="letters">{check.table.map(([, letter], i) => <td key={i}>{letter}</td>)}</tr>
              </tbody>
            </table>
            {solved && <p className="answer">{p.word}</p>}
          </>
        )}
      </div>
      {/* Outside the turned content and out of the flow: it reads upright and does not shrink the type. */}
      {hint && <p className="hint">{hint}</p>}
    </div>
  );
}

// A Hunderterfeld, drawn as the contract at the top of hunderterfeld.ts says. Its lines are 0.3 and its outer frame
// 0.6 of a 100 field, so they keep that share when a cut-out makes the field smaller.
function Hunderterfeld({ block, solved }: { block: HunderterfeldBlock; k: number; solved: boolean }) {
  const p = saneFeld(block.props);
  const { cells, frame, filled } = drawnFeld(p);
  const line = (0.3 * frame[2]) / 100;
  // The frame grows by a line on each side, so no line lies on the svg's edge, where it would be cut in half and
  // fall on other pixels in print than on screen.
  const [fx, fy, side] = frame;
  return (
    <div className={`hunderterfeld${solved ? " solved" : ""}`}>
      <svg viewBox={[fx - line, fy - line, side + 2 * line, side + 2 * line].join(" ")}>
        {p.look === "punkte"
          ? filled.map((on, i) => (
              <circle
                key={i}
                className={`dot${on ? " filled" : ""}`}
                data-i={i}
                cx={dotAt(i % 10)}
                cy={dotAt(Math.floor(i / 10))}
                r={3.6}
                fill={on ? "#222" : "none"}
                stroke={on ? "none" : "#222"}
                strokeWidth={0.4}
              />
            ))
          : cells
              .filter((c) => c.drawn)
              .map((c) => {
                const x = (c.i % 10) * 10;
                const y = Math.floor(c.i / 10) * 10;
                return (
                  <g key={c.i} className="cell" data-i={c.i} data-value={c.value} data-tint={c.tint || undefined}>
                    <rect x={x} y={y} width={10} height={10} fill={c.tint ? TINT[c.tint] : "none"} stroke="#222" strokeWidth={line} />
                    {c.shown && (
                      <text className="given" x={x + 5} y={y + 5} fontSize={4} textAnchor="middle" dominantBaseline="central" fill="#222">
                        {c.value}
                      </text>
                    )}
                    {!c.shown && solved && (
                      <text className="answer" x={x + 5} y={y + 5} fontSize={4} textAnchor="middle" dominantBaseline="central" fill="#c0392b">
                        {c.value}
                      </text>
                    )}
                  </g>
                );
              })}
        {p.look === "tafel" && !p.cut && <rect className="frame" x={line} y={line} width={100 - 2 * line} height={100 - 2 * line} fill="none" stroke="#222" strokeWidth={2 * line} />}
      </svg>
    </div>
  );
}

// What a block shows, at `k` pixels per mm. Sizes inside a block are in em of a font size set to the scale.
// `solved` fills in the answers of the maths exercises. `at` is the cell of a table that the editor's field is for.
export function Draw({ block, k, solved = false, at, reach, children }: { block: Block; k: number; solved?: boolean; at?: number; reach?: number; children?: ReactNode }) {
  if (block.type === "maths") return <Maths block={block} k={k} solved={solved} />;
  if (block.type === "suchsel") return <Suchsel block={block} k={k} solved={solved} />;
  if (block.type === "zahlenmauer") return <Zahlenmauer block={block} k={k} solved={solved} />;
  if (block.type === "rechendreieck") return <Rechendreieck block={block} k={k} solved={solved} />;
  if (block.type === "zahlenstrahl") return <Zahlenstrahl block={block} k={k} solved={solved} />;
  if (block.type === "hunderterfeld") return <Hunderterfeld block={block} k={k} solved={solved} />;
  if (block.type === "uhr") return <Uhr block={block} k={k} solved={solved} />;
  if (block.type === "selbstkontrolle") return <Selbstkontrolle block={block} k={k} solved={solved} />;
  if (block.type === "table") return <Table block={block} k={k} at={at} reach={reach} solved={solved}>{children}</Table>;
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
        {/* The word with its space as one piece of text, as before: the PDF sets each piece on its own. */}
        / {children ?? block.props.max}
        {block.props.max === 1 ? " Punkt" : " Punkte"}
      </div>
    );
  if (block.type === "image") {
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
          style={{ width: `${100 / w}%`, height: `${100 / h}%`, left: `${(-100 * l) / w}%`, top: `${(-100 * t) / h}%`, clipPath, opacity: block.props.opacity }}
        />
      </div>
    );
  }
  // A block of a type this script does not know: a newer Blattomat made it, and it stays as it is in the sheet.
  return <div className="unknown">Dieser Block braucht eine neuere Version von Blattomat.</div>;
}

// A score as it is typed: a whole number from 1 to 999, or else none.
export const score = (text: string) => (/^\s*\d{1,3}\s*$/.test(text) && +text >= 1 ? +text : undefined);

// The field of a score, in a box or in the panel. However it ends, it keeps the typed score when that is a whole number
// from 1 to 999; any other text leaves the old one. On the sheet Escape keeps it too, as Enter does; in the panel (with
// `steps`) Escape gives up what was typed, as every panel number field does. `change` gets the score and makes no step
// when the sheet has it already. `end` runs after Enter, `blur` on leaving the field. `steps` adds the buttons that
// count by one, each from the sheet's own number, after the typed score is kept.
export function ScoreInput({ max, change, end, blur, steps }: { max: number; change: (max: number) => void; end?: () => void; blur?: (e: FocusEvent<HTMLInputElement>) => void; steps?: (by: number) => void }) {
  const [draft, setDraft] = useState(String(max));
  const [round, setRound] = useState(0);
  // What is typed, the score shown by the sheet, whether Escape ended the field, and whether the teacher typed in it.
  // A field nobody typed in sends nothing: in the panel its max is the first picked box's, and sending that would set
  // every picked box to it.
  const typed = useRef(String(max));
  const shown = useRef(max);
  const off = useRef(false);
  const dirty = useRef(false);
  const latest = useRef({ change, end, blur, steps });
  latest.current = { change, end, blur, steps };
  shown.current = max;
  // A press of a button counts too, though the first box's number may stay as it was: the field then shows the sheet's.
  useEffect(() => {
    typed.current = String(max);
    dirty.current = false;
    setDraft(String(max));
  }, [max, round]);
  // Runs on Enter, on a blur and when the field goes, so a score is kept once for each way the field ends.
  function keep() {
    if (off.current || !dirty.current) return;
    const next = score(typed.current);
    if (next === undefined) {
      typed.current = String(shown.current);
      return setDraft(typed.current);
    }
    dirty.current = false;
    latest.current.change(next);
  }
  // The field goes on the press that ends it, which takes no blur with it: so its score is kept as it leaves.
  useEffect(() => keep, []);
  function press(by: number) {
    keep();
    setRound((n) => n + 1);
    latest.current.steps?.(by);
  }
  return (
    <>
      {steps && <button aria-label="Ein Punkt weniger" onClick={() => press(-1)}>−</button>}
    <input
      className="score"
      inputMode="numeric"
      aria-label="Punkte"
      value={draft}
      onChange={(e) => {
        dirty.current = true;
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
          // Enter is a choice, also of the number that stands there: several picked boxes all take it.
          dirty.current = true;
          keep();
          latest.current.end?.();
        }
        if (e.key !== "Escape") return;
        if (steps) {
          // What was typed is given up: a later visit of the field that types nothing sends nothing.
          off.current = true;
          dirty.current = false;
          typed.current = String(shown.current);
          setDraft(typed.current);
        } else {
          // The sheet keeps a valid score, as Enter does; the field then ends with no more to keep.
          dirty.current = true;
          keep();
          off.current = true;
        }
        e.currentTarget.blur();
      }}
    />
      {steps && <button aria-label="Ein Punkt mehr" onClick={() => press(1)}>＋</button>}
    </>
  );
}

// A block's numbering stands to the left of its box, so the box keeps its place and its snap lines. `n` is the
// number of a counted block; a symbol has none. Beside a text it starts as far down as the text's first line, and
// beside a line its middle is level with the line's start.
export function Mark({ block, k, n }: { block: Block; k: number; n?: number }) {
  if (!block.mark) return null;
  const style = textStyle(boxed(block) ?? { text: "", size: 14, align: "left" }, k);
  // The line numbers stand between the mark and the box: the mark moves left of their column.
  const column = block.type === "text" && stepOf(block.props.lines) > 0 ? `calc(.4em + ${(2 + 1.6 * NUMBER_EM * block.props.size * PT) * k}px)` : undefined;
  return (
    <b className="mark" style={{ ...style, textDecoration: "none", paddingTop: block.type === "text" ? inset(block.props, false)[0] * k : 0, paddingRight: column, translate: isLine(block) ? "0 -50%" : undefined }}>
      {n ? <Count mark={block.mark} n={n} /> : <img src={symbol(block.mark)} alt="" />}
    </b>
  );
}

// A sheet's page numbers: off unless `on` is true. A value nobody knows reads as the default.
export const pageNumbersOf = (doc: Doc) => {
  const p = doc.pageNumbers ?? {};
  return {
    on: p.on === true,
    at: (["bottom", "right", "outer", "top"] as const).find((at) => at === p.at) ?? "bottom",
    form: (["n", "seite", "of", "seiteVon"] as const).find((form) => form === p.form) ?? "n",
    notFirst: p.notFirst === true,
    black: p.black === true,
  };
};
// The text and place of a page's number, or nothing when the sheet shows none on that page. Pages count from 1.
export const folioOf = (doc: Doc, page: number) => {
  const f = pageNumbersOf(doc);
  if (!f.on || (f.notFirst && page === 0)) return undefined;
  const [w] = sizeOf(doc, page);
  const n = page + 1;
  const m = doc.pages.length;
  const text = { n: `${n}`, seite: `Seite ${n}`, of: `${n} / ${m}`, seiteVon: `Seite ${n} von ${m}` }[f.form];
  const pos: CSSProperties =
    f.at === "bottom" ? { left: 0, width: w * K, textAlign: "center", bottom: 6 * K }
    : f.at === "top" ? { right: 15 * K, top: 6 * K }
    : f.at === "outer" && n % 2 === 0 ? { left: 15 * K, bottom: 6 * K }
    : { right: 15 * K, bottom: 6 * K };
  return { text, pos, at: f.at, black: f.black };
};
// A page's number, the first child of its `.scaled` div, so the blocks draw over it.
export function PageNumber({ doc, page }: { doc: Doc; page: number }) {
  const f = folioOf(doc, page);
  return f ? (
    <span className="folio" aria-hidden style={{ ...f.pos, fontSize: 9 * PT * K, color: f.black ? "#000000" : "#707070" }}>
      {f.text}
    </span>
  ) : null;
}

// A page with nothing to take hold of, at `k` pixels per mm: page one drawn small in the list, every page at its
// true size in the PDF, where it needs no transform. The answer key says on each page that it is one; with the page
// number at the top right, it moves to the top left.
export function Paper({ doc, k, page = 0, solved = false, letter }: { doc: Doc; k: number; page?: number; solved?: boolean; letter?: string }) {
  const all = read(doc);
  const ns = numbers(all);
  const [w, h] = sizeOf(all, page);
  const moved = solved && folioOf(all, page)?.at === "top";
  return (
    <Words.Provider value={wordsIn(all)}>
    <Whole.Provider value={all}>
    <div className={w > h ? "paper wide" : "paper"} style={{ width: w * k, height: h * k }}>
      <div className="scaled" style={{ width: w * K, height: h * K, transform: k === K ? undefined : `scale(${k / K})` }}>
        <PageNumber doc={all} page={page} />
        {all.pages[page].blocks.map((b) => (
          <div key={b.id} className="block" style={{ left: b.x * K, top: b.y * K, width: b.w * K, height: b.h * K, zIndex: b.z, ...turned(b) }}>
            <Draw block={b} k={K} solved={solved} />
            {b.type === "text" && stepOf(b.props.lines) > 0 && <Numbers block={b} />}
            <Mark block={b} k={K} n={ns.get(b.id)} />
          </div>
        ))}
        {solved && <b className="key" style={{ top: 5 * K, ...(moved ? { left: 15 * K } : { right: 15 * K }), fontSize: 11 * PT * K }}>{letter ? `Lösungen ${letter}` : "Lösungen"}</b>}
        {letter && <b className="variant" style={{ position: "absolute", bottom: 5 * K, right: 8 * K, fontSize: 8 * PT * K }}>{letter}</b>}
      </div>
    </div>
    </Whole.Provider>
    </Words.Provider>
  );
}
