// The model of the Lernwörter: how a block takes the sheet's list, lets it go, and how a sheet lays out a ready
// Lernwörter page. Pure functions, so the editor and the tests share them.
import { MARGIN, RULINGS, dir, listOf, rowsOf, tall, tied, wordsIn, type Block, type Box, type Doc, type ListMode, type Ruling, type RulingBlock, type TextProps } from "./sheet";

const round = (n: number) => Math.round(n * 100) / 100;

// A pasted list becomes lines for the list field. Commas, semicolons and line breaks each end an entry, so a list
// copied from a table or a sentence lands one word to a row.
export const pasted = (text: string): string[] => text.split(/[,;\r\n]/).map((w) => w.trim()).filter(Boolean);

// How far a point can go until it meets a margin, moving `by` each step. No limit where it does not move.
export const room = (at: number, by: number, max: number) => (Math.abs(by) < 1e-9 ? Infinity : ((by > 0 ? max - MARGIN : MARGIN) - at) / by);

// A ruling grows down its own axis, which a turn points anywhere on the page, until a corner of its far edge
// would cross the margin it grows towards. Whole rows, and one at least.
export function filled(b: RulingBlock, W: number, H: number): Partial<Box> {
  const [c, s] = dir(b);
  // The corner the block starts at; the other end of that edge lies its width along.
  const [x, y] = [b.x + (b.w - b.w * c + b.h * s) / 2, b.y + (b.h - b.w * s - b.h * c) / 2];
  const most = Math.min(room(x, -s, W), room(x + b.w * c, -s, W), room(y, c, H), room(y + b.w * s, c, H));
  return tall(b, round(Math.max(1, Math.floor(most / RULINGS[b.props.kind].row + 0.05)) * RULINGS[b.props.kind].row));
}

// The words a linked block does not show: a row holds one word, so the rest are cut off.
export const short = (b: RulingBlock, words: string[]): number => (listOf(b) ? Math.max(0, words.length - rowsOf(b)) : 0);

// A block takes the list in `mode`. An unlinked block that is free to grow gets a row for each word, up to the
// most the page leaves it when filled, and never fewer rows than it has. A linked block only changes its mode.
export function linked(b: RulingBlock, mode: ListMode, words: string[], W: number, H: number): RulingBlock {
  const props = { ...b.props, list: mode };
  if (listOf(b) || b.locked) return { ...b, props };
  const { row } = RULINGS[b.props.kind];
  const most = Math.floor((filled(b, W, H).h ?? b.h) / row + 0.05);
  const rows = Math.max(rowsOf(b), Math.min(words.length, most));
  if (rows <= rowsOf(b)) return { ...b, props };
  return { ...b, ...tall(b, round(rows * row)), props };
}

// A block cut loose from the list keeps the words as its own text. Trace and row stay grey over the text, as
// they did on the list; copy and fold have no grey text, so their trace goes. A fold's columns go with the list.
export function loose(b: RulingBlock, words: string[]): RulingBlock {
  const mode = listOf(b);
  if (!mode) return b;
  const props: RulingBlock["props"] = { ...b.props, text: words.join("\n") };
  delete props.list;
  delete props.trace;
  delete props.folds;
  if (mode !== "copy" && mode !== "fold") props.trace = true;
  return { ...b, props };
}

// A text or a shape cut loose from the list keeps the words as its own text, and loses its list settings. With no
// word to keep it has its own text again: a block copied in a window that knows no list brings none. Mixed words
// keep the line they had on the list.
export function looseText<P extends Partial<TextProps>>(p: P, words: string[]): P {
  const props: Partial<TextProps> = { ...p };
  if (words.length) {
    props.text = words.join("\n");
    delete props.rich;
  }
  if (p.list === true && p.mix !== undefined && p.mixLine === undefined) props.mixLine = "after";
  delete props.list;
  delete props.listCols;
  delete props.holes;
  delete props.holeSeed;
  return props as P;
}

// A paste must not bring other words than the sheet it lands on. The copied list comes along when the sheet has
// none; a block keeps a list only when the two lists are the same, and otherwise is cut loose with its words.
export function landed(blocks: Block[], from: unknown, doc: Doc): { blocks: Block[]; words?: string[] } {
  if (!blocks.some(tied)) return { blocks };
  const theirs = wordsIn({ words: from });
  const ours = wordsIn(doc);
  if (ours.length === 0 && theirs.length > 0) return { blocks, words: from as string[] };
  if (ours.length === theirs.length && ours.every((w, i) => w === theirs[i])) return { blocks };
  const cut = (b: Block): Block => {
    if (b.type === "ruling") return loose(b, theirs);
    return b.type === "text" || b.type === "shape" ? ({ ...b, props: looseText(b.props, theirs) } as Block) : b;
  };
  return { blocks: blocks.map((b) => (tied(b) ? cut(b) : b)) };
}

// The blocks of a ready Lernwörter sheet: a heading, a name line, and three rulings that take the list in copy,
// trace and row. Each ruling is as tall as the room of a third of the page, or as many rows as there are words.
type Fresh = Omit<Block, "id" | "z" | "locked">;
export function blatt(words: string[], W: number, H: number): Fresh[] {
  const x = MARGIN;
  const w = W - 2 * MARGIN;
  // The room for the three rulings, with a gap of 6 mm between them.
  const third = (H - MARGIN - (MARGIN + 32) - 2 * 6) / 3;
  // The first Lineatur that gives every word its own row in a third, else the lines.
  const kind: Ruling = (["l2", "l3", "l4", "lines"] as Ruling[]).find((k) => Math.floor(third / RULINGS[k].row) >= words.length) ?? "lines";
  const { row } = RULINGS[kind];
  const rows = Math.max(1, Math.min(words.length, Math.floor(third / row)));
  let y = MARGIN + 32;
  const rulings = (["copy", "trace", "row"] as ListMode[]).map((list) => {
    const block = { type: "ruling" as const, x, y, w, h: rows * row, props: { kind, color: "#222222", list } };
    y += rows * row + 6;
    return block;
  });
  return [
    { type: "text", x, y: MARGIN, w, h: 12, props: { text: "Lernwörter", size: 20, align: "left", bold: true } },
    { type: "name", x, y: MARGIN + 16, w, h: 10, props: {} },
    ...rulings,
  ];
}
