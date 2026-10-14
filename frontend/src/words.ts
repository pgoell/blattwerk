// The model of the Lernwörter: how a block takes the sheet's list, lets it go, and how a sheet lays out a ready
// Lernwörter page. Pure functions, so the editor and the tests share them.
import { MARGIN, RULINGS, dir, kindOf, listOf, rowsOf, shownParas, startOf, stored, tall, tied, wordsIn, type Block, type Box, type Doc, type ListMode, type Ruling, type RulingBlock, type TextProps } from "./sheet";

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
  return tall(b, round(Math.max(1, Math.floor(most / RULINGS[kindOf(b.props.kind)].row + 0.05)) * RULINGS[kindOf(b.props.kind)].row));
}

// The words a linked block does not show: a row holds one word, so the rest are cut off. A run-on block shows from its `from`.
export const short = (b: RulingBlock, words: string[]): number => (listOf(b) ? Math.max(0, words.length - startOf(b) - rowsOf(b)) : 0);

// Whether a run-on block of the same mode among `all` goes on from the word after the last row of `b`.
const runsOn = (b: RulingBlock, all: RulingBlock[]) => all.some((o) => o.props.from !== undefined && listOf(o) === listOf(b) && startOf(o) === startOf(b) + rowsOf(b));

// The most words of the list that one of the `blocks` cuts off. A block that a run-on block of its mode among `all`
// goes on from, at the word after its last row, cuts off none.
export function unshown(blocks: RulingBlock[], words: string[], all: RulingBlock[] = blocks): number {
  return Math.max(0, ...blocks.map((b) => (runsOn(b, all) ? 0 : short(b, words))));
}

// A linked ruling grows by a row for each word the list has past its rows, as far as the page margin and the top of
// a block below it that it overlaps. It never shrinks, and a locked ruling or one a run-on block among `all` (the
// rulings of every page) goes on from keeps its height.
export function follow(blocks: Block[], words: string[], W: number, H: number, all: Block[] = blocks): Block[] {
  const rulings = all.filter((o): o is RulingBlock => o.type === "ruling");
  return blocks.map((b) => {
    if (b.type !== "ruling" || !listOf(b) || b.locked || runsOn(b, rulings)) return b;
    const need = words.length - startOf(b);
    if (need <= rowsOf(b)) return b;
    const { row } = RULINGS[kindOf(b.props.kind)];
    const edge = Math.min(...blocks.filter((o) => o !== b && o.y >= b.y + b.h && o.x < b.x + b.w && o.x + o.w > b.x).map((o) => o.y));
    const room = Math.min(filled(b, W, H).h ?? b.h, edge - b.y);
    const rows = Math.min(need, Math.floor(room / row + 0.05));
    if (rows <= rowsOf(b)) return b;
    return { ...b, ...tall(b, round(rows * row)) } as Block;
  });
}

// A block takes the list in `mode`. An unlinked block that is free to grow gets a row for each word, up to the
// most the page leaves it when filled, and never fewer rows than it has. A linked block only changes its mode.
export function linked(b: RulingBlock, mode: ListMode, words: string[], W: number, H: number): RulingBlock {
  const props = { ...b.props, list: mode };
  if (listOf(b) || b.locked) return { ...b, props };
  const { row } = RULINGS[kindOf(b.props.kind)];
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
  // A run-on block keeps only the words it shows.
  const own = b.props.from === undefined ? words : words.slice(startOf(b), startOf(b) + rowsOf(b));
  const props: RulingBlock["props"] = { ...b.props, text: own.join("\n") };
  delete props.list;
  delete props.trace;
  delete props.folds;
  delete props.from;
  if (mode !== "copy" && mode !== "fold") props.trace = true;
  return { ...b, props };
}

// A text or a shape cut loose from the list keeps the words as its own text, and loses its list settings. With no
// word to keep it has its own text again: a block copied in a window that knows no list brings none. Mixed words
// keep the line they had on the list. Lückenwörter stay, as gaps of the block's own text at the letters they hid.
export function looseText<P extends Partial<TextProps>>(p: P, words: string[]): P {
  const props: Partial<TextProps> = { ...p };
  if (words.length) {
    const kept = stored(shownParas({ ...p, list: true } as TextProps, words));
    props.text = kept.text;
    if (kept.rich) props.rich = kept.rich;
    else delete props.rich;
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
// A list longer than one page's rows runs on: each further page holds the three rulings again, each from the word
// after the last one shown, and no heading. A short list gives one page, as before.
export function blatt(words: string[], W: number, H: number): Fresh[][] {
  const x = MARGIN;
  const w = W - 2 * MARGIN;
  // The room for the three rulings, with a gap of 6 mm between them.
  const third = (H - MARGIN - (MARGIN + 32) - 2 * 6) / 3;
  // The first Lineatur that gives every word its own row in a third, else the lines.
  const kind: Ruling = (["l2", "l3", "l4", "lines"] as Ruling[]).find((k) => Math.floor(third / RULINGS[k].row) >= words.length) ?? "lines";
  const { row } = RULINGS[kind];
  const perPage = Math.max(1, Math.floor(third / row));
  const pages = Math.max(1, Math.ceil(words.length / perPage));
  return Array.from({ length: pages }, (_, p): Fresh[] => {
    const first = p * perPage;
    const rows = Math.max(1, Math.min(perPage, words.length - first));
    const from = p > 0 ? { from: first } : {};
    let y = p === 0 ? MARGIN + 32 : MARGIN;
    const rulings = (["copy", "trace", "row"] as ListMode[]).map((list): Fresh => {
      const block = { type: "ruling" as const, x, y, w, h: rows * row, props: { kind, color: "#222222", list, ...from } };
      y += rows * row + 6;
      return block;
    });
    if (p > 0) return rulings;
    return [
      { type: "text", x, y: MARGIN, w, h: 12, props: { text: "Lernwörter", size: 20, align: "left", bold: true } },
      { type: "name", x, y: MARGIN + 16, w, h: 10, props: {} },
      ...rulings,
    ];
  });
}
