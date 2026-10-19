// What a new block is when the editor's insert buttons make it, and how a block grows when its props change. The
// editor and the MCP server (frontend/mcp) both take blocks from here, so a block Claude adds is the block a teacher
// adds. No React: Node runs this file.
import { DEFAULTS as DREIECK, heightFor as heightForDreieck, sane as saneDreieck } from "./rechendreieck";
import { DEFAULTS as STRAHL, below, sane as saneStrahl } from "./zahlenstrahl";
import { DEFAULTS as FELD } from "./hunderterfeld";
import { DEFAULTS as UHR, heightFor as heightForUhr, sane as saneUhr } from "./uhr";
import { DEFAULTS as SELBST, heightFor as heightForSelbst, sane as saneSelbst } from "./selbstkontrolle";
import { heightFor as heightForMauer, sane as saneMauer } from "./zahlenmauer";
import { DEFAULTS as HAUS, heightFor as heightForHaus, sane as saneHaus } from "./zahlenhaus";
import { MARGIN, dir, lowest, tall, type Block, type Box, type Doc, type Kind } from "./sheet";

// A new block's type and settings with its size; `add` in the editor gives it its place.
export type Fresh<B = Block> = B extends Block ? Pick<B, "type" | "props"> & { w: number; h: number } : never;

const round = (n: number) => Math.round(n * 100) / 100;

// The shapes that frame a text: they hold it inside their outline (#128).
export const FRAMES: Kind[] = ["rect", "rounded", "circle", "triangle", "star", "bubble"];
// A new shape's width in mm, where it is not 60.
const WIDTHS: Partial<Record<Kind, number>> = { circle: 40, triangle: 40, star: 40 };

// What each insert button adds. The maths block (its exercises come from the server) and the picture (from an upload)
// are made where they are added.
export const INSERTS = {
  text: (): Fresh => ({ w: 80, h: 12, type: "text", props: { text: "", size: 14, align: "left" } }),
  heading: (): Fresh => ({ w: 180, h: 14, type: "text", props: { text: "", size: 24, align: "center", bold: true } }),
  symbol: (): Fresh => ({ w: 20, h: 20, type: "symbol", props: { code: "270F" } }),
  table: (): Fresh => ({ w: 180, h: 30, type: "table", props: { cells: Array.from({ length: 3 }, () => ["", "", ""]), cols: [1, 1, 1], size: 14, align: "center", line: "#222222" } }),
  ruling: (): Fresh => ({ w: 180, h: 60, type: "ruling", props: { kind: "l1", color: "#555555" } }),
  name: (): Fresh => ({ w: 180, h: 10, type: "name", props: {} }),
  points: (): Fresh => ({ w: 40, h: 12, type: "points", props: { max: 10 } }),
  suchsel: (seed: number): Fresh => ({ w: 120, h: 140, type: "suchsel", props: { words: [], cols: 10, rows: 10, ways: "down", caps: true, umlauts: true, show: "words", seed } }),
  zahlenmauer: (seed: number): Fresh => ({ w: 180, h: 60, type: "zahlenmauer", props: { base: 3, count: 4, columns: 2, max: 20, op: "+", given: "base", empty: false, seed } }),
  zahlenhaus: (seed: number): Fresh => ({ w: 120, h: 55, type: "zahlenhaus", props: { ...HAUS, seed } }),
  rechendreieck: (seed: number): Fresh => ({ w: 180, h: 50, type: "rechendreieck", props: { ...DREIECK, seed } }),
  zahlenstrahl: (seed: number): Fresh => ({ w: 180, h: 30, type: "zahlenstrahl", props: { ...STRAHL, seed } }),
  hunderterfeld: (seed: number): Fresh => ({ w: 100, h: 100, type: "hunderterfeld", props: { ...FELD, seed } }),
  uhr: (seed: number): Fresh => ({ w: 180, h: 58.5, type: "uhr", props: { ...UHR, seed } }),
  selbstkontrolle: (seed: number): Fresh => ({ w: 180, h: 30, type: "selbstkontrolle", props: { ...SELBST, seed } }),
  // "Strecke": a line with ticks.
  strecke: (): Fresh => ({ w: 50, h: 0, type: "shape", props: { kind: "line", fill: "none", stroke: "#222222", strokeWidth: 0.5, ticks: true } }),
  shape: (kind: Kind): Fresh => {
    const frame = FRAMES.includes(kind);
    return { w: WIDTHS[kind] ?? 60, h: frame ? 40 : 0, type: "shape", props: { kind, fill: "none", stroke: "#222222", strokeWidth: 0.5, ...(frame && { inside: true, floor: true }) } };
  },
  // The Lernwörter-Liste, a ruling of page width that folds the words, a row for each word that fits.
  wordList: (words: number, [W, H]: number[], row: number): Fresh => ({
    w: W - 2 * MARGIN,
    h: Math.max(1, Math.min(words, Math.floor((H - 2 * MARGIN) / row))) * row,
    type: "ruling",
    props: { kind: "l3", color: "#222222", list: "fold", folds: 2 },
  }),
};

// A new maths block: plus exercises up to 20, asked of the server with `limits`; then its props are the limits, what the
// server made and `look`, 180 mm wide and as high as `mathsHeight` says.
export const MATHS = {
  w: 180,
  limits: (seed: number) => ({ ops: ["+" as const], max: 20, a: [[0, 9], [0, 9]] as [number, number][], b: [[0, 9], [0, 9]] as [number, number][], carry: "either" as const, rest: false, format: "row" as const, count: 12, seed }),
  look: { columns: 3, size: 14 },
};

// The boxes the blocks fill on a page: a turned block counts with the box it fills, turned about its middle.
export const filled = (blocks: Box[]) =>
  blocks.map((b) => {
    const [c, s] = dir(b).map(Math.abs);
    const [w, h] = [b.w * c + b.h * s, b.w * s + b.h * c];
    return { x: b.x + (b.w - w) / 2, y: b.y + (b.h - h) / 2, w, h };
  });

// The z a new block takes on a page: above every block there.
export const topZ = (blocks: Block[]) => Math.max(0, ...blocks.map((b) => b.z)) + 1;

// The blocks that grow so that their drawing keeps the size of the default block's: the height their props need at
// width w, and the props that change it (#588, #598).
const GROWS: Partial<Record<Block["type"], [(props: any, w: number) => number, string[]]>> = {
  rechendreieck: [(p, w) => heightForDreieck(saneDreieck(p), w), ["count", "columns"]],
  zahlenmauer: [(p, w) => heightForMauer(saneMauer(p), w), ["count", "columns", "base"]],
  zahlenhaus: [(p, w) => heightForHaus(saneHaus(p), w), ["count", "columns", "floors"]],
  uhr: [(p, w) => heightForUhr(saneUhr(p), w), ["count", "cols"]],
};
// A maths block grows downward when a change in its panel needs more room, to the page's foot at most (`H`, the page's
// height), in the same undo step; it never shrinks by itself. A Zahlenstrahl grows by what its line rises, so the line
// keeps its place. `doc` is the sheet a Selbstkontrolle counts its tasks in.
export function grown(b: Block, next: Block, doc: Doc, H: number): Partial<Box> {
  const foot = Math.max(b.h, H - MARGIN - b.y);
  if (b.type === "zahlenstrahl" && next.type === "zahlenstrahl") {
    const more = below(saneStrahl(next.props), b.w) - below(saneStrahl(b.props), b.w);
    if (more > 0) return tall(b, round(Math.min(b.h + more, foot)));
  }
  // A Selbstkontrolle grows with its form, its links or its word, as its content needs, and needs the sheet to count its tasks.
  if (b.type === "selbstkontrolle" && next.type === "selbstkontrolle" && (["form", "links", "word", "size", "title", "turn"] as const).some((key) => next.props[key] !== b.props[key])) {
    const need = round(Math.min(heightForSelbst(saneSelbst(next.props), doc, b.w), foot));
    if (need > b.h) return tall(b, need);
  }
  const grow = GROWS[b.type];
  if (grow && b.type === next.type && grow[1].some((key) => (next.props as any)[key] !== (b.props as any)[key])) {
    // Every GROWS block may pass the foot: capped, its drawing would shrink to fit the room left.
    const need = round(grow[0](next.props, b.w));
    if (need > b.h) return tall(b, need);
  }
  return {};
}

// Whether a change of a GROWS block's props would grow it below the paper's edge, `H` mm down: what hangs there is
// not printed, so the panel refuses such a change, as it does for a maths block (#911).
export function pastPaper(b: Block, next: Block, H: number) {
  const grow = GROWS[b.type];
  if (!grow || b.type !== next.type || !grow[1].some((key) => (next.props as any)[key] !== (b.props as any)[key])) return false;
  const low = lowest({ ...b, ...tall(b, round(grow[0](next.props, b.w))) });
  return low > H + 0.01 && low > lowest(b) + 0.01;
}
