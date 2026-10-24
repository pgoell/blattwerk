// School fonts and rulings, and the CSS that seats writing on a line. The metric tables stay here.

import { PT } from "../height";
import type { RulingBlock } from "./ruling";
import type { TextProps } from "./text";
import type { CSSProperties } from "react";

export type Font = keyof typeof FONTS;
export type Ruling = "l1" | "l2" | "l3" | "l4" | "lines" | "k5" | "k7";
// The two colours the syllables of a text take in turn.
export type Tints = [string, string];
// Blue then red, as the schoolbooks print syllables, and the pair for a copy in black and white: the grey is as
// dark as a copier still prints and as light as the eye still tells from the black.
export const TINTS: Tints = ["#1a56db", "#e02424"];
export const GREYS: Tints = ["#000000", "#707070"];
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
export const LEFT: Record<Font, number> = { andika: 0.1, nord: 0, sued: 0, grund: 0.1, urff: 0.05, va: 0.21, sas: 0.24, la: 0.29 };
// How far the ink of a font reaches above and below its baseline, in em (#487). Measured in Chromium with
// canvas measureText, at 1000 px, over the regular, bold and italic cut and each of the printable ASCII
// characters and ÄÖÜäöüßẞ€§°; the largest of the three cuts, rounded up to three decimals.
export const INK: Record<Font, readonly [number, number]> = {
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
// Andika's j reaches 0.094 em left (#489).
export const SIDE: Partial<Record<Font, number>> = { andika: 0.1, nord: 0.02, sued: 0.02, grund: 0.1, urff: 0.06, va: 0.21, sas: 0.24, la: 0.29 };
// Trace text (Nachspurtext), for the children to write over, in a text, a shape, a table and a Lineatur. A block
// stores `trace`: true for grey, "outline" for letters with a line around them and no fill (Umriss), "dotted" for the
// font's own dotted cut (gepunktet). Sheets saved before have true or nothing. `fade` makes the trace text lighter
// step by step until it is gone: "row" along each row, "rows" from row to row.
export type Trace = "grey" | "outline" | "dotted";
export type Fade = "row" | "rows";
// The fonts with a dotted cut, and its family. No other font is dotted: dots on a letter's outline are not what a
// child traces.
export const DOTTED: Partial<Record<Font, string>> = { urff: "Grundschrift Urff Punkt" };
// How far the dotted cut's ink reaches left of its place and right of its advance, in em: its start dots reach
// further than SIDE measures for the regular cut. Measured in Chromium with canvas measureText at 1000 px, over
// ASCII and ÄÖÜäöüßẞ€§°: 0.032 left and 0.042 right, rounded up to two decimals and taken as one for both sides.
export const DOTTED_SIDE = 0.05;
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
export const fadeMask = (fade: Fade, n: number, rowPx: number, at: (px: number) => string) => {
  // A sheet may come from anywhere: a count that is no number, or a huge one, draws at most 200 rows.
  const rows = Math.min(200, Math.max(1, Math.floor(n) || 1));
  return fade === "row"
    ? "linear-gradient(to right, #000, transparent 75%)"
    : `linear-gradient(to bottom, ${Array.from({ length: rows }, (_, i) => `rgba(0,0,0,${fadeAt(i, rows)}) ${at(i * rowPx)}, rgba(0,0,0,${fadeAt(i, rows)}) ${at((i + 1) * rowPx)}`).join(", ")}, transparent ${at(rows * rowPx)})`;
};
// The look of a trace text in outline: stroke first, the fill white over it, then multiplied, so the white vanishes
// and what lies under the letters shows through.
export const OUTLINE: CSSProperties = { WebkitTextFillColor: "#fff", WebkitTextStroke: ".07em", paintOrder: "stroke fill", mixBlendMode: "multiply" };
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
export const RULINGS: Record<Ruling, { name: string; row: number; at?: number[]; zones?: number[]; band: number; base: number; size: number }> = {
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
// How many rows of its ruling fit a block. Moveable's pixels leave a height a hair short of a full row.
export const rowsOf = (b: RulingBlock) => Math.floor(b.h / RULINGS[kindOf(b.props.kind)].row + 0.05);
export const colsOf = (b: RulingBlock) => Math.floor(b.w / RULINGS[kindOf(b.props.kind)].row + 0.05);
// WebKit keeps the fraction of a line's baseline, Chromium (the print) puts it on a whole pixel: the text of a
// Lineatur then lies up to a pixel lower on the screen than in the print (issue #499). Measured once.
export let keepsFraction: boolean | undefined;
// Each font's whole-pixel ascent and descent by family and size, from a canvas.
export const metrics = new Map<string, [number, number]>();
export function keepsFractions() {
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
export function baselineFraction(family: string | undefined, size: number, lineHeight: number) {
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
      // Half a px of slack, so the last square's letter fits; a whole square is far wider, so no extra letter fits.
      width: colsOf(b) * row * k + 0.5,
      height: rowsOf(b) * row * k,
      whiteSpace: "break-spaces",
      overflowWrap: "anywhere",
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
  // A plain or grey text reaches as far as its font's letters (#489).
  const reach = look === "outline" ? Math.max(SIDE[fontOf(b.props.font)] ?? 0, 0.12) + 0.035 : look === "dotted" ? DOTTED_SIDE : (SIDE[fontOf(b.props.font)] ?? 0);
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
