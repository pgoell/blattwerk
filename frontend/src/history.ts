// The editor's undo and redo: what counts as a change of the sheet, and the moves between its steps.
import { boxed, type Block, type Doc } from "./sheet";

// A step of undo holds the sheet on its far side, and the page in use before and after its change.
export type Step = { doc: Doc; from: number; to: number };
export type Hist = { past: Step[]; doc: Doc; future: Step[] };

// Whether two sheets, or parts of them, are the same once saved: a key that holds nothing is saved as no key.
export function alike(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (!a || !b || typeof a !== "object" || typeof b !== "object" || Array.isArray(a) !== Array.isArray(b)) return false;
  const [x, y] = [a, b] as Record<string, unknown>[];
  return x.length === y.length && Object.keys({ ...x, ...y }).every((key) => alike(x[key], y[key]));
}
// What a text or a shape is drawn with, and the panel shows, where it names nothing. A shape's words say more.
const SHOWN = { valign: "top", kind: "rect", font: "andika", color: "#222222", spacing: 1.3, strokeWidth: 0.5, opacity: 1 };
// The props that change a block. One the block does not name, set to what the block shows there, is left out:
// a press on "Oben" for a text that stands at the top is no change. Of any other block only the script is known,
// and the colour of a table's words, which is the sheet's: a line or a Lineatur made elsewhere that names no width
// or colour is drawn by the browser's own.
export const fresh = (b: Block, props: object) => {
  const text = boxed(b);
  const shown: Record<string, unknown> = text ? { ...SHOWN, ...text } : { font: "andika", ...(b.type === "table" && { color: "#222222" }) };
  return Object.fromEntries(Object.entries(props).filter(([name, to]) => (b.props as Record<string, unknown>)[name] !== undefined || to !== shown[name]));
};
// The sheet without the props that a block of `start` does not name and shows as they are set: a colour moved
// away and back to the one the block showed is back at its start.
export const bare = (doc: Doc, start: Doc): Doc => ({
  ...doc,
  pages: doc.pages.map((p, n) => ({
    ...p,
    blocks: p.blocks.map((b) => {
      const was = start.pages[n]?.blocks.find((o) => o.id === b.id);
      return was ? ({ ...b, props: fresh(was, b.props) } as Block) : b;
    }),
  })),
});

// A change to `doc`: a step of its own, or with `merge` one more of the gesture that made the last step. Redo goes.
export const stepped = (h: Hist, doc: Doc, merge: boolean, from: number, to: number): Hist => ({ past: merge ? h.past : [...h.past, { doc: h.doc, from, to }], doc, future: [] });
// The last step taken back for good, as by a gesture that ends where it began: redo holds `ahead`, what it held
// before the gesture.
export const returned = (h: Hist, ahead: Step[]): Hist => ({ past: h.past.slice(0, -1), doc: h.past.at(-1)!.doc, future: ahead });
// Undo of the step `last`, the last of `past`, and redo of `next`, the first of `future`.
export const undone = (h: Hist, last = h.past.at(-1)!): Hist => ({ past: h.past.slice(0, -1), doc: last.doc, future: [{ ...last, doc: h.doc }, ...h.future] });
export const redone = (h: Hist, next = h.future[0]): Hist => ({ past: [...h.past, { ...next, doc: h.doc }], doc: next.doc, future: h.future.slice(1) });
