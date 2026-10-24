// What a text or a shape stores, and how its paragraphs are kept.

import { holed } from "../holes";
import type { Breaks } from "../syllables";
import type { Align, Valign, Kind, Box, Corner } from "./box";
import type { Block } from "./doc";
import type { Tints, Font, Fade } from "./look";

export type List = "bullet" | "number";
// A stretch of a text with a look of its own. `bold` and `italic` stand in for the block's, on or off; an underline
// and a colour lie on top of the block's. `gap` makes the stretch a gap of a Lückentext: the pupil's sheet shows a line
// to write on in its place, as wide as its words, the editor shows the words in grey and the answer key in its colour.
export type Run = {
  /** The words of this stretch. In a gap, the answer: the pupil's sheet shows a line in its place. */
  text: string;
  /** True makes the stretch bold, false makes it plain. Absent takes the block's setting. */
  bold?: boolean;
  /** True makes the stretch italic, false makes it upright. Absent takes the block's setting. */
  italic?: boolean;
  /** True underlines the stretch, on top of the block's own underline. Absent means no extra underline. */
  underline?: boolean;
  /** Colour of the stretch as a hex colour, such as "#e02424", on top of the block's colour. Absent takes the block's colour. */
  color?: string;
  /** True makes the stretch a gap of a Lückentext. On the pupil's sheet it is a line to write on, as wide as its words. The editor shows the words in grey, the answer key in the gap's colour. */
  gap?: boolean;
};
// A paragraph of a text: an item of a list with `list`, moved in by `level` steps, 0 to 2.
export type Para = {
  /** The stretches of the paragraph in reading order, each with its own look. */
  runs: Run[];
  /** Makes the paragraph an item of a list: "bullet" for a dot, "number" for a count. Absent means no list. */
  list?: List;
  /** How far the paragraph is moved in, in steps, from 0 (flush left) to 2. Absent means 0.
   * @minimum 0
   * @maximum 2
   */
  level?: number;
};
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
export type TextProps = {
  /** The words of the text as one plain string, with no look of their own. Always the same words as `rich`. */
  text: string;
  /** The paragraphs with their own looks. Absent when one look covers the whole text: `text` then holds all of it. */
  rich?: Para[];
  /** True draws a bow under each syllable of each word (Silbenbögen). Absent means off. */
  syllables?: boolean;
  /** The words the teacher split by hand into syllables. Absent means the program alone splits the words. */
  breaks?: Breaks;
  /** The two colours the syllables take in turn, the first and then the second, such as blue and red. Absent means the syllables are not coloured in turn. */
  tints?: Tints;
  /** True carries the colour turn on from word to word through the text. Absent means each word starts again with the first colour. */
  tintsAcross?: boolean;
  /** Every gap in the text is at least this many mm wide, so a pupil has room to write. Absent or 0 means each gap is only as wide as its word. Capped at 200 mm.
   * @maximum 200
   */
  gapWidth?: number;
  /** Seed for the box of hidden words set under the text (Lösungswörter). The box shows the words shuffled in an order this seed sets. Absent means no box. */
  bank?: number;
  /** Numbers the lines of the text as they break, in the margin. 1 numbers every line, 5 every fifth line. Absent means no numbers. */
  lines?: number;
  /** The number of the first line, for the numbering in `lines`. Absent means 1.
   * @minimum 1
   * @maximum 9999
   */
  linesFrom?: number;
  /** Seed for the scrambled words (Schüttelwörter). Each word shows its letters in another order, the same on every draw. Absent means no scrambling. */
  mix?: number;
  /** True keeps the first letter of each scrambled word in place. Absent means the first letter is scrambled too. */
  mixFirst?: boolean;
  /** True sets the letters of the scrambled words in capitals. */
  mixCaps?: boolean;
  /** Where the pupil writes each scrambled word: "after" puts a line after it, "under" a line under it. Absent means no line, except that a list draws it after each word. */
  mixLine?: "after" | "under";
  /** True makes the text draw the sheet's Lernwörter, one word to a paragraph (Text aus Lernwörtern). Its own text stays as it is and is not shown. */
  list?: boolean;
  /** The number of columns the list words fill, column by column. Absent means 1.
   * @minimum 1
   * @maximum 4
   */
  listCols?: number;
  /** Lückenwörter for a linked text: "one" gives one letter of each word as a gap, "second" every second letter, "vowels" the vowels. Absent means no gaps. */
  holes?: "one" | "second" | "vowels";
  /** Seed that picks which letters become gaps under `holes`. The same seed gives the same gaps on every draw. Absent means 0. */
  holeSeed?: number;
  /** Font size of the text in pt (points). */
  size: number;
  /** Horizontal alignment of the lines in the box: "left", "center" or "right". */
  align: Align;
  /** Typeface, one of the keys of FONTS, such as "andika" (the school print). Absent means andika. */
  font?: Font;
  /** True sets the whole text in bold. Absent means off. */
  bold?: boolean;
  /** True sets the whole text in italic. Absent means off. */
  italic?: boolean;
  /** True underlines the whole text. Absent means off. */
  underline?: boolean;
  /** Colour of the text as a hex colour, such as "#222222". Absent means #222222. */
  color?: string;
  /** Distance from one line of the text to the next, as a multiple of the font size. Absent means 1.3.
   * @minimum 1
   * @maximum 3
   */
  spacing?: number;
  /** Vertical place of the text in its box: "top", "middle" or "bottom". Absent means top. */
  valign?: Valign;
  /** Outline of the box the text sits in: "rect", "rounded", "circle", "triangle", "star" or "bubble". Absent means rect. */
  kind?: Kind;
  /** Colour inside the box as a hex colour. "none" or absent means no fill. */
  fill?: string;
  /** How solid the fill is: 0 is invisible, 1 is solid. Absent means 1.
   * @minimum 0
   * @maximum 1
   */
  opacity?: number;
  /** Colour of the border as a hex colour. "none" or absent means no border. */
  stroke?: string;
  /** How solid the border is: 0 is invisible, 1 is solid. Absent means 1.
   * @minimum 0
   * @maximum 1
   */
  strokeOpacity?: number;
  /** True keeps a circle's, triangle's or star's text inside its outline, shrunk to fit, rather than growing the shape. Absent means off. */
  inside?: boolean;
  /** Where a speech bubble's tail ends, as shares of the box's width and height: [across, down]. Across runs from 0 at the left edge to 1 at the right, down from 0 at the top to 1 at the foot of the box. The tip may lie one box beyond each edge: across and down from -1 to 2. Absent means [0.2, 1]. */
  tail?: [number, number];
  /** How deep a star's points cut in: the distance of its inner corners from the middle, as a share of its points'. Absent means 0.38.
   * @minimum 0.1
   * @maximum 0.9
   */
  inner?: number;
  /** Where a triangle's tip stands across its top, as a share of the width: 0 over the left corner, 1 over the right. Absent means 0.5, the middle.
   * @minimum 0
   * @maximum 1
   */
  tip?: number;
  /** How round a rounded box's corners are: the corner's radius as a share of the box's shorter side, 0 square, 0.5 half the shorter side. Absent means a radius of 4 mm.
   * @minimum 0
   * @maximum 0.5
   */
  corner?: number;
  /** True fits the box to its text (An Text anpassen): as wide as its longest line, up to the page's right margin, and as high as its lines, growing and shrinking as the text changes. For a box of outline rect, rounded or bubble. Absent means off: the box keeps its width and only grows. */
  fit?: boolean;
  /** Set by the editor on a shape whose text the teacher has sized: the text then keeps at least 10 pt. Absent means off. */
  floor?: boolean;
  /** Width of the border in mm. Absent means 0.5.
   * @minimum 0.25
   * @maximum 3
   */
  strokeWidth?: number;
  /** Style of the border: "dashed" for dashes, "dotted" for dots. Absent means a solid border. */
  dash?: "dashed" | "dotted";
  /** Nachspuren: the text prints in grey to write over. true is plain grey, "outline" a thin outline of the letters, "dotted" dotted letters (in fonts that have them, else grey). Absent means no trace text. */
  trace?: boolean | "outline" | "dotted";
  /** How the grey of a trace text fades: "row" fades each row from left to right, "rows" fades the rows step by step down the block. Absent means no fade. Needs `trace`. */
  fade?: Fade;
};
export type TextBlock = Box & {
  type: "text";
  /** The text box's words and look. */
  props: TextProps;
};
// A shape can hold text: centred and in the middle unless set otherwise. A line or arrow runs from the corner
// `from` of its box to the opposite one. It can have a tick at each end and say how long it is, on the sheet
// ("show") or on the answer key alone ("key").
export type ShapeBlock = Box & { type: "shape";
  /** The shape's form, fill and border, and the text it may hold: every field of a text block may stand here too. */
  props: Partial<TextProps> & {
  /** What to draw: a frame ("rect", "rounded", "circle", "triangle", "star", "bubble") or a line ("line", a plain line, "arrow", a line with a head at its end, "double", a line with a head at each end). */
  kind: Kind;
  /** Colour inside the shape as a hex colour. "none" means no fill. */
  fill: string;
  /** Colour of the outline, or of the line, as a hex colour. "none" means no outline. */
  stroke: string;
  /** Width of the outline, or of the line, in mm.
   * @minimum 0.25
   * @maximum 3
   */
  strokeWidth: number;
  /** For a line or an arrow: the corner of the box where it starts, "nw" top left, "ne" top right, "sw" bottom left, "se" bottom right. The line runs to the opposite corner. Absent means "nw". */
  from?: Corner;
  /** True puts a short cross stroke at each end of a line. Absent means no ticks. */
  ticks?: boolean;
  /** Prints the length of a line: "show" on the sheet, "key" on the answer key only. Absent means no length. */
  label?: "show" | "key";
} };
// A sheet may come from anywhere: 1 to 4 columns, and anything else is 1.
export const listColsOf = (p: { listCols?: unknown }) => (typeof p.listCols === "number" && Number.isInteger(p.listCols) && p.listCols >= 1 && p.listCols <= 4 ? p.listCols : 1);
// The Lückenwörter mode, or none: a stored mode nobody knows is none.
export const holesOf = (p: { holes?: unknown }) => (p.holes === "one" || p.holes === "second" || p.holes === "vowels" ? p.holes : undefined);
// The line after or under a mixed word: the stored one, else "after" for a linked text, and none for any other.
export const lineOf = (p: { mixLine?: unknown; list?: unknown }): "after" | "under" | undefined =>
  p.mixLine === "after" || p.mixLine === "under" ? p.mixLine : p.list === true ? "after" : undefined;
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
