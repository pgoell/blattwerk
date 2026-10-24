// The sheet document, and reading one that an older build saved.

import type { Breaks } from "../syllables";
import { type Box, tall } from "./box";
import { RULINGS, kindOf, rowsOf } from "./look";
import type { MathsBlock, Range } from "./maths";
import { type RulingBlock, listOf, rowsNeeded } from "./ruling";
import type { TableBlock } from "./table";
import type { SuchselBlock, ZahlenmauerBlock, RechendreieckBlock, ZahlenhausBlock, ZahlenketteBlock, PfeilbildBlock, OperatorfeldBlock, RechenradBlock, RechentabelleBlock, MagischesQuadratBlock, MalquadratBlock, ZerlegungsfeldBlock, HalbschriftlichBlock, ZehnerfeldBlock, ZahlenstrahlBlock, HunderterfeldBlock, UhrBlock, SelbstkontrolleBlock } from "./tasks";
import type { TextBlock, ShapeBlock } from "./text";

// The words of a name line, as a new one has them. A line's `fields` replace them.
export const FIELDS = ["Name", "Datum", "Klasse"];
export type NameBlock = Box & {
  type: "name";
  /** The line the pupil writes their name (and date, class) on. */
  props: {
    /** The words of the name line in order, such as "Name", "Datum" and "Klasse". Left out, the line uses FIELDS. */
    fields?: string[];
    /** The fields the line leaves out, as indexes into its words from 0, such as [2] for a line without "Klasse". At least one field stays shown. Absent means every field shows. */
    hidden?: number[];
  };
};
export type PointsBlock = Box & {
  type: "points";
  /** A box the teacher writes the points scored in, beside the most there are. */
  props: {
    /** The most points the task gives, printed in the box. */
    max: number;
    /** Marks the box as the sheet's total: it shows the sum of all the task boxes. Left out, it is a task box. */
    total?: boolean;
  };
};
export type SymbolBlock = Box & {
  type: "symbol";
  /** Which symbol (a pictogram such as a pencil or scissors) the block shows, scaled to the box. */
  props: {
    /** The OpenMoji code of the symbol, its file name in the symbol set, such as "270F" for a pencil. See SYMBOLS for all of them. */
    code: string;
  };
};
// `ratio` is the picture's width over its height; `cut` the share cropped off its left, top, right and bottom.
export type ImageBlock = Box & {
  type: "image";
  /** Which uploaded picture the block shows, and how it is cropped. */
  props: {
    /** The id of the uploaded picture file, as the server stores it. */
    upload: number;
    /** The picture's width over its height, from the picture as uploaded. 1 for a square. */
    ratio: number;
    /** Four numbers for the share cropped off the left, top, right and bottom: each a fraction of the picture, 0 for none. */
    cut: number[];
    /**
     * How solid the picture prints: 1 for full strength, 0 for see-through. Left out, 1.
     * @minimum 0
     * @maximum 1
     */
    opacity?: number;
  };
};
export type Block = TextBlock | ShapeBlock | RulingBlock | NameBlock | PointsBlock | SymbolBlock | ImageBlock | MathsBlock | TableBlock | SuchselBlock | ZahlenmauerBlock | RechendreieckBlock | ZahlenhausBlock | ZahlenketteBlock | PfeilbildBlock | OperatorfeldBlock | RechenradBlock | RechentabelleBlock | MagischesQuadratBlock | MalquadratBlock | ZerlegungsfeldBlock | HalbschriftlichBlock | ZehnerfeldBlock | ZahlenstrahlBlock | HunderterfeldBlock | UhrBlock | SelbstkontrolleBlock;
export type Axis = "x" | "y";
// The teacher's own guide lines, in mm.
export type Guides = {
  /** The upright guide lines, each the distance in mm from the paper's left edge. */
  x: number[];
  /** The flat guide lines, each the distance in mm from the paper's top edge. */
  y: number[];
};
// A page can have guide lines of its own, beside the sheet's, and a grid and a format of its own in place of the
// sheet's. `ground` is the picture the page lies on, under every block.
export type Page = {
  /** The blocks printed on this page, drawn in order. */
  blocks: Block[];
  /** The page's own guide lines in mm, beside the sheet's. Left out, the page has none of its own. */
  guides?: Guides;
  /** The grid's cell on this page in mm, in place of the sheet's. 0 for no grid. Left out, the sheet's grid applies. */
  grid?: number;
  /** Lays this page on its side, 297 by 210 mm, in place of the sheet's format. Left out, the sheet's format applies. */
  landscape?: boolean;
  /** The picture this page lies on, under every block. Left out, the page is blank. */
  ground?: Ground;
};
// The picture a page lies on. It fills the page and keeps its proportions. `cut` is the share cropped off each
// edge, as for an image block. `turns` is quarter turns clockwise. The editor fades it to 1, 0.5 or 0.25.
export type Ground = {
  /** The id of the uploaded picture file, as the server stores it. */
  upload: number;
  /** The picture's width over its height, from the picture as stored. 1 for a square. */
  ratio: number;
  /** Four numbers for the share cropped off the left, top, right and bottom: each a fraction of the picture, 0 for none. */
  cut: number[];
  /** Quarter turns clockwise, from 0 to 3. Left out, none.
   * @minimum 0
   * @maximum 3
   */
  turns?: number;
  /** How solid the ground prints: 1 for full strength, 0.5 or 0.25 so the blocks stand out. Left out, 1.
   * @minimum 0
   * @maximum 1
   */
  opacity?: number;
  /** Shift from the centred ground, in mm: across, then down. Left out, the ground stays centred. */
  at?: [number, number];
  /** How much larger the ground is than the size that fills the page and keeps its proportions. 1 fills the page. Left out, 1.
   * @minimum 0.25
   * @maximum 4
   */
  scale?: number;
};
// The pages, and what every page shares: guide lines, the grid's cell in mm (0 for none), and whether the A4 lies
// on its side.
// `words` holds the sheet's Lernwörter as the teacher typed them, a line of the list to an entry. Sheets saved
// before have none.
export type Doc = {
  /** The pages of the sheet, in print order. */
  pages: Page[];
  /** The guide lines on every page, in mm: `x` for the upright lines, `y` for the flat ones, each from the paper's edge. */
  guides: Guides;
  /** The grid's cell on every page in mm. 0 for no grid. */
  grid: number;
  /** Lays the A4 sheet on its side, 297 by 210 mm, for every page that has no format of its own. Left out, upright. */
  landscape?: boolean;
  /** The sheet's Lernwörter (words to learn), one to a line as typed. Left out, the sheet has none. */
  words?: string[];
  // The mends of the sheet: a word split by hand holds in every block. A block's own `breaks` win over these.
  /** The word breaks set by hand for the whole sheet: each word in lower case, with the places it breaks at, as counts of characters. Left out, the module's own breaks apply. */
  breaks?: Breaks;
  /** The page numbers printed on each page. Left out, none are printed. */
  pageNumbers?: {
    /** Whether page numbers print at all. Left out, they do not. */
    on?: boolean;
    /** Where the number prints: "bottom" centred at the foot, "right" at the foot's right, "outer" at the outer foot corner (left on even pages, right on odd), "top" at the top right. Left out, "bottom". */
    at?: "bottom" | "right" | "outer" | "top";
    /** How the number reads: "n" for 2, "seite" for Seite 2, "of" for 2 / 5, "seiteVon" for Seite 2 von 5. Left out, "n". */
    form?: "n" | "seite" | "of" | "seiteVon";
    /** Leaves the number off the first page. Left out, the first page is numbered. */
    notFirst?: boolean;
    /** Prints the number in black. Left out, it is grey. */
    black?: boolean;
  };
};
export type PageNumbers = NonNullable<Doc["pageNumbers"]>;
// The server counts a sheet's saved documents in `version`.
export type Sheet = { id: number; user_id: number; title: string; updated: string; version: number; doc: Doc };
// A page's width and height in mm: A4, upright or on its side.
export const sizeOf = (doc: Doc, n: number) => ((doc.pages[n].landscape ?? doc.landscape) ? [297, 210] : [210, 297]);
// The margin a new block keeps, and a ruling that fills the page.
export const EMPTY: Doc = { pages: [{ blocks: [] }], guides: { x: [], y: [] }, grid: 0 };

// A maths block saved with no digit ranges takes any digit in each place of its Zahlenraum.
export function whole(b: Block): Block {
  // A Karo whose text needs more rows than it has grows to them, as a sheet saved before the kind changed did not.
  if (b.type === "ruling" && !RULINGS[kindOf(b.props.kind)].at && !listOf(b)) {
    const need = rowsNeeded(b);
    if (need > rowsOf(b)) return { ...b, ...tall(b, Math.round(need * RULINGS[kindOf(b.props.kind)].row * 100) / 100) };
  }
  if (b.type !== "maths" || (b.props.a && b.props.b)) return b;
  const any = Array.from(String(b.props.max), (): Range => [0, 9]);
  return { ...b, props: { ...b.props, a: b.props.a ?? any, b: b.props.b ?? any } };
}
// Templates saved before sheets had pages hold one page's blocks.
export const read = ({ pages, blocks, guides, grid, landscape, words, pageNumbers, breaks }: Doc & { blocks?: Block[] }): Doc => ({
  pages: (pages ?? [{ blocks: blocks! }]).map((page) => ({ ...page, blocks: page.blocks.map(whole) })),
  // A sheet from the API may lack its guides and grid, or hold them wrong: then it has none.
  guides: guides && typeof guides === "object" && Array.isArray(guides.x) && Array.isArray(guides.y) ? guides : { x: [], y: [] },
  grid: typeof grid === "number" ? grid : 0,
  landscape,
  words,
  pageNumbers,
  // A sheet may come from anywhere: only a plain object of mends is kept.
  breaks: breaks && typeof breaks === "object" && !Array.isArray(breaks) ? breaks : undefined,
});
// The Lernwörter a sheet's blocks print: an entry holds one word, or several split by commas or semicolons. Blanks
// around a word go, and so does an entry with no word. A list that is no list of texts holds no word.
export const wordsIn = (doc: { words?: unknown }): string[] =>
  Array.isArray(doc.words) ? doc.words.flatMap((line) => (typeof line === "string" ? line.split(/[,;\n]/) : [])).map((w) => w.trim()).filter(Boolean) : [];
