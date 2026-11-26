// A page as the template "Lernwörter" lays it out, for the tests of how linked rulings grow and run on.
import { MARGIN, RULINGS, type Block, type ListMode, type Ruling } from "./sheet";

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
