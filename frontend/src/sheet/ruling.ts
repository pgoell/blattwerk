// A lineatur's word list, its squares, and the rows its text needs.

import type { Breaks } from "../syllables";
import { type Box, K, tall } from "./box";
import type { Block, Doc } from "./doc";
import { type Ruling, type Font, type Fade, type Tints, RULINGS, kindOf, colsOf, writtenStyle, rowsOf } from "./look";
import { boxed } from "./text";

// As many rows as fit the block's height are drawn. `text` is written on the rows, on Karo a character to a
// square, and grey with `trace` so the children can write over it. Karo is always in print.
// With `list` the block takes its words from the sheet's Lernwörter, one to a row, and `text` and `trace` rest: "copy"
// prints each word at its row's start to copy beside, "trace" prints it once in grey to write over, "row" in grey
// again and again to the row's end. "fold" is the Knickblatt: each word at its row's start, cut at the first column,
// with `folds` empty columns to write in (2 or 3) and a dashed fold line between the words and them.
export type ListMode = "copy" | "trace" | "row" | "fold";
// `from` is the index of the first word of the list the block shows, for a run-on Lineatur on a later page.
export type RulingBlock = Box & {
  type: "ruling";
  /** The Lineatur's kind and colour, and the words it may show on its rows. */
  props: {
    /** The ruled pattern (Lineatur) kind: its line pattern and school level, one of the RULINGS keys, such as "l1" for Lineatur 1 (Klasse 1). Required. */
    kind: Ruling;
    /** The colour of the lines, as a six digit hex colour such as #1a56db. */
    color: string;
    /** Text printed on the lines, in the block's font. Left out, the lines stand alone. */
    text?: string;
    /** The font of the text printed on the lines. Left out, the default font is used. */
    font?: Font;
    /** Trace text the pupil writes over: true for grey, "outline" or "dotted". Left out, no trace. */
    trace?: boolean | "outline" | "dotted";
    /** How the trace fades as the pupil writes on: "row" along each row, "rows" from row to row. Left out, it does not fade. */
    fade?: Fade;
    /** Takes its words from the sheet's words to learn (Lernwörter), one to a row, in the way the mode says. Left out, no list. */
    list?: ListMode;
    /**
     * Index of the first word to learn the block shows, counted from 0, so a ruled pattern run on over several pages picks up
     * where the last one stopped. Left out, 0.
     * @minimum 0
     */
    from?: number;
    /**
     * Number of empty columns to write in on a fold sheet (Knickblatt), after the words. 2 or 3. Any other value gives 2.
     * @minimum 2
     * @maximum 3
     */
    folds?: number;
    /** Draws a house on the lines of a kind with zones, marking its room, roof and cellar. Left out, no house. */
    house?: boolean;
    /** Tints the house: "room" for the room alone, "all" for roof, room and cellar. Left out, the house is not tinted. */
    houseTint?: "room" | "all";
    /** Whether the middle band between the lines is tinted. Left out, the kind's own default applies. */
    band?: boolean;
    /** The band's colour, as a six digit hex colour such as #ffe066. Left out, the line colour, paler, is used. */
    bandColor?: string;
    /** Draws an arc under each syllable of the text on the lines or in the squares. Left out, no arcs. */
    syllables?: boolean;
    /** The word breaks set by hand for the text on the lines or in the squares. They win over the sheet's breaks. Left out, the sheet's apply. */
    breaks?: Breaks;
    /** Two colours, such as #1a56db and #e02424, that colour the syllables in turn, on the lines or in the squares. Left out, no colour. */
    tints?: Tints;
    /** Carries the colour turn on from word to word, instead of starting again with each word. On the lines or in the squares. Left out, it starts again. */
    tintsAcross?: boolean;
  };
};
// The index of the first word a Lineatur shows: 0 unless it has a whole, non-negative `from`.
export const startOf = (b: RulingBlock): number => {
  const from = b.props.from ?? 0;
  return Number.isInteger(from) && from >= 0 ? from : 0;
};
// The mode a Lineatur takes the Lernwörter in, or none: a stored mode nobody knows is none.
export const listOf = (b: RulingBlock): ListMode | undefined =>
  b.props.list === "copy" || b.props.list === "trace" || b.props.list === "row" || b.props.list === "fold" ? b.props.list : undefined;
// Whether a block draws the sheet's Lernwörter: a Lineatur with a list mode, or a text or shape with `list: true`.
export const tied = (b: Block) => (b.type === "ruling" ? listOf(b) !== undefined : boxed(b)?.list === true);
// The empty columns of a Knickblatt: 3 when `folds` says so, else 2.
export const foldsOf = (b: RulingBlock): 2 | 3 => (b.props.folds === 3 ? 3 : 2);
// The square each character of a Karo's text stands in, as [column, row, character, offset]: a row is filled, then the
// next begins. The offset is where the character lies in the text, in UTF-16 units.
// A word moves whole to the next row when it and the space after it do not fit the rest of the row, as the field wraps
// it; a word longer than a row breaks in place. A hyphen between a letter and a letter ends a unit too, as the field
// breaks there ("3-4" does not). A space that finds its row full starts the next row.
// A soft hyphen and a zero width joiner are not written. A combining mark stays on the character before it, and the
// square shows that character composed, so neither takes a square of its own.
const SKIPPED = new Set(["\u00AD", "\u200D"]);
function seen(text: string): { ch: string; at: number }[] {
  const out: { ch: string; at: number }[] = [];
  let i = 0;
  for (const ch of text) {
    const prev = out.at(-1);
    if (/^\p{M}$/u.test(ch) && prev && prev.ch !== "\n") prev.ch = (prev.ch + ch).normalize("NFC");
    else if (!SKIPPED.has(ch)) out.push({ ch, at: i });
    i += ch.length;
  }
  return out;
}
export function squares(text: string, cols: number) {
  const out: [number, number, string, number][] = [];
  const chars = seen(text);
  // A dash ends a unit wherever it stands, and an em dash starts one too, as the field breaks before and after it.
  const hyphen = (j: number) => (chars[j].ch === "-" && j > 0 && chars[j - 1].ch !== " " && /\p{L}/u.test(chars[j + 1]?.ch ?? "")) || chars[j].ch === "–" || chars[j].ch === "—";
  const before = (j: number) => chars[j].ch === "—" && j > 0 && chars[j - 1].ch !== " " && chars[j - 1].ch !== "\n";
  let [x, y] = [0, 0];
  chars.forEach(({ ch, at }, n) => {
    if (ch === "\n") [x, y] = [0, y + 1];
    else if (ch !== " " && (n === 0 || chars[n - 1].ch === " " || chars[n - 1].ch === "\n" || hyphen(n - 1) || before(n))) {
      let len = 0;
      for (let j = n; j < chars.length && chars[j].ch !== " " && chars[j].ch !== "\n" && !(j > n && before(j)); j++) {
        len = j - n + 1;
        if (hyphen(j)) break;
      }
      const unit = len + (chars[n + len]?.ch === " " ? 1 : 0);
      if (x > 0 && x + unit > cols) [x, y] = [0, y + 1];
    }
    if (ch !== "\n") {
      if (x === cols) [x, y] = [0, y + 1];
      out.push([x++, y, ch, at]);
    }
  });
  return out;
}
// The rows a Lineatur's text needs. A Karo counts its squares; a lined kind takes the height the text has on the page,
// measured with the fonts in place. None with no text, a list, or no page to measure on.
export function rowsNeeded(b: RulingBlock): number {
  const { text } = b.props;
  if (listOf(b) || !text) return 0;
  const { row, at } = RULINGS[kindOf(b.props.kind)];
  if (!at) return Math.max(0, ...squares(text, colsOf(b)).map(([, y]) => y + 1));
  if (typeof document === "undefined") return 0;
  // A hidden block as wide as this one, so the copy takes the rules of `.block .written` and wraps as drawn.
  const block = document.createElement("div");
  block.className = "block";
  Object.assign(block.style, { position: "absolute", visibility: "hidden", left: "0", top: "0", width: `${b.w * K}px` });
  const p = document.createElement("p");
  p.className = "written";
  const style = Object.fromEntries(Object.entries(writtenStyle(b, K)).map(([name, v]) => [name, typeof v === "number" ? `${v}px` : v]));
  Object.assign(p.style, style, { height: "auto" });
  p.textContent = text;
  block.append(p);
  document.body.append(block);
  const lines = Math.round(p.scrollHeight / (row * K));
  block.remove();
  return lines;
}
// A sheet whose Lineatur on lines holds more text than its rows show, as one stored before its kind changed: each
// such block grows to the rows its text needs. It measures, so only once the fonts are in. The same doc when none grows.
export function lengthened(doc: Doc): Doc {
  let grew = false;
  const pages = doc.pages.map((p) => ({
    ...p,
    blocks: p.blocks.map((b) => {
      if (b.type !== "ruling" || !RULINGS[kindOf(b.props.kind)].at) return b;
      const need = rowsNeeded(b);
      if (need <= rowsOf(b)) return b;
      grew = true;
      return { ...b, ...tall(b, Math.round(need * RULINGS[kindOf(b.props.kind)].row * 100) / 100) };
    }),
  }));
  return grew ? { ...doc, pages } : doc;
}
