// Properties of the sheet model: what `read` makes of a stored sheet, and the steps of undo and redo.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { alike, bare, fresh, redone, returned, stepped, undone, type Hist, type Step } from "./history";
import { EMPTY, read, type Block, type Doc } from "./sheet";

// The old sheets and templates of tests/corpus, as the server holds them.
const files = import.meta.glob<{ doc: Doc }>("../../tests/corpus/*.json", { eager: true, import: "default" });
const corpus = Object.entries(files).map(([path, file]) => [path.split("/").at(-1)!, file.doc] as const);
// The document as a save sends it.
const sent = (doc: Doc): Doc => JSON.parse(JSON.stringify(doc));

// A maths block as sheets held it at some time: with both digit ranges, with one, or with none.
const maths = fc.record({ max: fc.constantFrom(10, 20, 100, 1000), a: fc.constant([[0, 9]]), b: fc.constant([[1, 5]]) }, { requiredKeys: ["max"], noNullPrototype: true }).map((props) => ({ id: "m", type: "maths", x: 15, y: 15, w: 100, h: 20, z: 0, locked: false, props }) as unknown as Block);
// A template saved before sheets had pages: one page's blocks, and no pages.
const old = (blocks: Block[]) => ({ blocks, guides: { x: [], y: [] }, grid: 5 }) as unknown as Doc;
const stored = fc.oneof<fc.Arbitrary<Doc>[]>(
  fc.constantFrom(EMPTY, ...corpus.map(([, doc]) => doc), ...corpus.map(([, doc]) => old(doc.pages[0].blocks))),
  fc.array(maths, { maxLength: 3 }).map((blocks) => ({ ...EMPTY, pages: [{ blocks }] })),
  fc.array(maths, { maxLength: 3 }).map(old),
);

describe("read", () => {
  it("has files to read", () => expect(corpus.length).toBeGreaterThan(0));

  it("twice makes what once makes", () => {
    fc.assert(fc.property(stored, (doc) => void expect(read(read(doc))).toStrictEqual(read(doc))));
  });

  // As tests/test_corpus.py asks of the editor in a browser: what it saves is what the server held.
  it.each(corpus)("and a save give %s back unchanged", (_, doc) => {
    expect(sent(read(doc))).toStrictEqual(doc);
  });

  it("turns an old template into pages and fills a maths block's digit ranges", () => {
    const text = { id: "t", type: "text", x: 15, y: 15, w: 50, h: 10, z: 0, locked: false, props: { text: "x", size: 14, align: "left" } };
    const sums = { id: "m", type: "maths", x: 15, y: 30, w: 100, h: 20, z: 1, locked: false, props: { max: 100, b: [[1, 5]] } };
    const made = read({ ...old([text, sums] as unknown as Block[]), landscape: true });
    expect(sent(made)).toStrictEqual({
      pages: [{ blocks: [text, { ...sums, props: { max: 100, a: [[0, 9], [0, 9], [0, 9]], b: [[1, 5]] } }] }],
      guides: { x: [], y: [] },
      grid: 5,
      landscape: true,
    });
    expect("blocks" in made).toBe(false);
  });

  it("leaves what it was given as it was", () => {
    fc.assert(
      fc.property(stored, (doc) => {
        const given = structuredClone(doc);
        read(given);
        expect(given).toStrictEqual(doc);
      }),
    );
  });
});

// The editor's `update`, `undo` and `redo` without the drawing: the history, the key of the gesture under way, and
// what redo held when that gesture began.
type State = { h: Hist; key: string; ahead: Step[] };
const start = (doc: Doc): State => ({ h: { past: [], doc, future: [] }, key: "", ahead: [] });
function change(s: State, fn: (doc: Doc) => Doc, key = ""): State {
  const doc = fn(s.h.doc);
  if (alike(doc, s.h.doc)) return key !== "" && key === s.key ? s : { ...s, key: "" };
  const merge = key !== "" && key === s.key;
  if (merge && alike(bare(doc, s.h.past.at(-1)!.doc), s.h.past.at(-1)!.doc)) return { ...s, h: returned(s.h, s.ahead), key: "" };
  return { h: stepped(s.h, doc, merge, 0, 0), key, ahead: merge ? s.ahead : s.h.future };
}
const undo = (s: State): State => (s.h.past.length ? { ...s, h: undone(s.h), key: "" } : s);
const redo = (s: State): State => (s.h.future.length ? { ...s, h: redone(s.h), key: "" } : s);

// Changes the first page's block `i`, counted round, if there is one.
const block = (i: number, fn: (b: Block) => Block) => (doc: Doc): Doc => {
  const [first, ...rest] = doc.pages;
  return first.blocks.length ? { ...doc, pages: [{ ...first, blocks: first.blocks.map((b, n) => (n === i % first.blocks.length ? fn(b) : b)) }, ...rest] } : doc;
};
const blocks = (fn: (bs: Block[]) => Block[]) => (doc: Doc): Doc => ({ ...doc, pages: [{ ...doc.pages[0], blocks: fn(doc.pages[0].blocks) }, ...doc.pages.slice(1)] });
const text = (id: string) => ({ id, type: "text", x: 15, y: 15, w: 50, h: 10, z: 0, locked: false, props: { text: "x", size: 14, align: "left" } }) as Block;
// A new text, with an id no block of the page has: one more than the highest that was made here.
const add = blocks((bs) => [...bs, text(`new-${Math.max(0, ...bs.map((b) => Number(b.id.split("new-")[1] ?? 0))) + 1}`)]);
// A prop set as the panel sets it: one the block does not name, set to what the block shows, is left out.
const coloured = (color: string) => (b: Block) => ({ ...b, props: { ...b.props, ...fresh(b, { color }) } }) as Block;

type Act = (s: State) => State;
const mm = fc.integer({ min: -20, max: 20 });
const key = fc.constantFrom("", "drag", "colour");
const nth = fc.nat(50);
// Changes that leave the sheet as it is: the same sheet, a copy of it, a key that holds nothing, a move by
// nothing, the colour a text shows with none named, and a block away that is not there.
const same: ((doc: Doc) => Doc)[] = [
  (doc) => doc,
  (doc) => structuredClone(doc),
  (doc) => ({ ...doc, landscape: doc.landscape }),
  block(0, (b) => ({ ...b, x: b.x + 0, mark: b.mark })),
  block(0, (b) => (b.type === "text" && b.props.color === undefined ? coloured("#222222")(b) : b)),
  blocks((bs) => bs.filter((b) => b.id !== "none")),
];
const idle: fc.Arbitrary<Act> = fc.tuple(fc.constantFrom(...same), key).map(([fn, k]) => (s) => change(s, fn, k));
// Changes of the sheet that need no key: each is a step of its own, unless it happens to change nothing.
const plain: fc.Arbitrary<Act> = fc.oneof(
  fc.tuple(nth, mm, mm).map(([i, x, y]): Act => (s) => change(s, block(i, (b) => ({ ...b, x: b.x + x, y: b.y + y })))),
  fc.tuple(nth, fc.integer({ min: 1, max: 100 }), fc.integer({ min: 1, max: 100 })).map(([i, w, h]): Act => (s) => change(s, block(i, (b) => ({ ...b, w, h })))),
  fc.tuple(nth, fc.constantFrom("#222222", "#ff0000", "#0000ff")).map(([i, c]): Act => (s) => change(s, block(i, coloured(c)))),
  fc.constant<Act>((s) => change(s, add)),
  nth.map((i): Act => (s) => change(s, (doc) => blocks((bs) => bs.filter((_, n) => n !== i % bs.length))(doc))),
  fc.constantFrom(0, 5, 10).map((grid): Act => (s) => change(s, (doc) => ({ ...doc, grid }))),
);
// The same within a gesture: a drag, a colour picker, and a gesture that goes back to where it began.
const held: fc.Arbitrary<Act> = fc.oneof(
  fc.tuple(nth, mm, mm).map(([i, x, y]): Act => (s) => change(s, block(i, (b) => ({ ...b, x: b.x + x, y: b.y + y })), "drag")),
  fc.tuple(nth, fc.constantFrom("#222222", "#ff0000", "#0000ff")).map(([i, c]): Act => (s) => change(s, block(i, coloured(c)), "colour")),
  key.map((k): Act => (s) => change(s, (doc) => (k !== "" && k === s.key ? s.h.past.at(-1)!.doc : doc), k)),
);
const walk = fc.constantFrom<Act>(undo, redo);
const runOf = (...acts: fc.Arbitrary<Act>[]) => fc.array(fc.oneof(...acts), { maxLength: 30 });
const first = fc.constantFrom(EMPTY, ...corpus.map(([, doc]) => read(doc)));
const play = (doc: Doc, acts: Act[]) => acts.reduce((s, act) => act(s), start(doc));
// Any run of actions from a sheet, and where it ends.
const played = fc.tuple(first, runOf(plain, held, idle, walk)).map(([doc, acts]) => play(doc, acts));
const times = (n: number, act: Act, s: State) => Array.from({ length: n }).reduce<State>(act, s);

describe("undo and redo", () => {
  it("undo then redo gives the same sheet, and so does redo then undo", () => {
    fc.assert(
      fc.property(played, ({ h }) => {
        if (h.past.length) expect(redone(undone(h))).toStrictEqual(h);
        if (h.future.length) expect(undone(redone(h))).toStrictEqual(h);
      }),
    );
  });

  it("undo of every step and redo of every step give the same sheet", () => {
    fc.assert(
      fc.property(played, (s) => {
        const n = s.h.past.length;
        expect(times(n, redo, times(n, undo, s)).h).toStrictEqual(s.h);
      }),
    );
  });

  it("undo of every step gives the first sheet, and each undo the sheet before its step", () => {
    fc.assert(
      fc.property(first, runOf(plain, idle), (doc, acts) => {
        // Every sheet the run passed through, told apart by what a save would send and not by `alike`.
        const seen = [doc];
        let s = start(doc);
        for (const act of acts) {
          s = act(s);
          if (JSON.stringify(s.h.doc) !== JSON.stringify(seen.at(-1))) seen.push(s.h.doc);
        }
        expect(s.h.past.length).toBe(seen.length - 1);
        for (const before of seen.reverse().slice(1)) {
          s = undo(s);
          expect(s.h.doc).toBe(before);
        }
        expect(s.h.doc).toBe(doc);
        expect(s.h.past).toEqual([]);
      }),
    );
  });

  it("a change after an undo empties redo", () => {
    fc.assert(
      fc.property(played, key, (s, k) => {
        const back = undo(change(s, add));
        expect(back.h.future.length).toBeGreaterThan(0);
        expect(change(back, add, k).h.future).toEqual([]);
      }),
    );
  });

  it("a change that leaves the sheet alike adds no step and keeps redo", () => {
    fc.assert(
      fc.property(played, fc.constantFrom(...same), key, (s, fn, k) => void expect(change(s, fn, k).h).toBe(s.h)),
    );
  });

  it("a sheet is alike what a save sends of it, and no other", () => {
    fc.assert(
      fc.property(played, ({ h }) => {
        expect(alike(h.doc, sent(h.doc))).toBe(true);
        for (const step of [...h.past, ...h.future]) expect(alike(h.doc, step.doc)).toBe(JSON.stringify(h.doc) === JSON.stringify(step.doc));
      }),
    );
  });

  it("a gesture is one step, and undo gives the sheet before it", () => {
    fc.assert(
      fc.property(played, fc.array(fc.integer({ min: 1, max: 20 }), { minLength: 1, maxLength: 5 }), (s, moves) => {
        // A drag of a new block ever further right never comes back to its start.
        const before = change(s, add);
        const after = moves.reduce((at, x) => change(at, block(before.h.doc.pages[0].blocks.length - 1, (b) => ({ ...b, x: b.x + x })), "drag"), before);
        expect(after.h.past.length).toBe(before.h.past.length + 1);
        expect(undo(after).h.doc).toBe(before.h.doc);
      }),
    );
  });

  it("a gesture that ends where it began leaves no step and keeps redo", () => {
    fc.assert(
      fc.property(played, mm, (s, x) => {
        fc.pre(x !== 0 && s.h.doc.pages[0].blocks.length > 0);
        const from = s.h.doc.pages[0].blocks[0].x;
        const away = change({ ...s, key: "" }, block(0, (b) => ({ ...b, x: from + x })), "drag");
        expect(away.h.past.length).toBe(s.h.past.length + 1);
        const home = change(away, block(0, (b) => ({ ...b, x: from })), "drag");
        expect(home.h).toStrictEqual(s.h);
        expect(home.h.doc).toBe(s.h.doc);
      }),
    );
  });

  it("a colour moved away and back to the one a block showed leaves no step", () => {
    fc.assert(
      fc.property(played, (s) => {
        // A new text names no colour and shows #222222.
        const from = change(s, add);
        const n = from.h.doc.pages[0].blocks.length - 1;
        const away = change(from, block(n, coloured("#ff0000")), "colour");
        expect(away.h.past.length).toBe(from.h.past.length + 1);
        expect(change(away, block(n, coloured("#222222")), "colour").h).toStrictEqual(from.h);
      }),
    );
  });
});
