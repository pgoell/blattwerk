import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { MARGIN, RULINGS, rowsOf, type Block, type Doc, type Ruling, type RulingBlock, type TextBlock, type TextProps } from "./sheet";
import { blatt, filled, follow, landed, linked, loose, looseText, pasted, short, unshown } from "./words";

const block = (kind: Ruling, h: number, props: Partial<RulingBlock["props"]> = {}, extra: Partial<RulingBlock> = {}): RulingBlock => ({
  id: "r",
  type: "ruling",
  x: 20,
  y: 20,
  w: 150,
  h,
  z: 1,
  locked: false,
  props: { kind, color: "#222222", ...props },
  ...extra,
});
const words = (n: number) => Array.from({ length: n }, (_, i) => `wort${i}`);
const doc = (ws?: string[]): Doc => ({ pages: [{ blocks: [] }], guides: { x: [], y: [] }, grid: 0, ...(ws && { words: ws }) });
const plain = block("l4", 20);
const linkedBlock = block("l4", 20, { list: "copy", text: "x" });

describe("pasted", () => {
  it("splits a list by commas, semicolons and line breaks, trims it and drops the blanks", () => {
    expect(pasted("Hund, Katze;Maus\r\n\n Igel ")).toEqual(["Hund", "Katze", "Maus", "Igel"]);
  });

  it("gives entries with no blank ends, no separator and no empty entry", () => {
    fc.assert(
      fc.property(fc.string(), (text) => {
        for (const w of pasted(text)) {
          expect(w).not.toBe("");
          expect(w).not.toMatch(/[,;\r\n]/);
          expect(w).toBe(w.trim());
        }
      }),
    );
  });
});

describe("short", () => {
  it("counts the words a linked block does not show", () => {
    expect(short(block("l4", 30, { list: "copy" }), words(5))).toBe(2);
  });

  it("counts nothing for an unlinked block", () => {
    expect(short(block("l4", 30), words(5))).toBe(0);
  });

  it("counts nothing when every word has a row", () => {
    expect(short(block("l4", 30, { list: "copy" }), words(2))).toBe(0);
  });
});

describe("short from a run-on block", () => {
  it("counts the words after the block's own rows", () => {
    expect(short(block("l4", 30, { list: "copy", from: 2 }), words(5))).toBe(0);
    expect(short(block("l4", 30, { list: "copy", from: 0 }), words(9))).toBe(6);
  });
});

describe("unshown", () => {
  const run = (from: number | undefined, h = 30) => block("l4", h, { list: "copy", ...(from !== undefined && { from }) });

  it("counts nothing when a run-on page shows the words the first page cannot", () => {
    expect(unshown([run(undefined), run(3)], words(5))).toBe(0);
  });

  it("counts the words the last block of a run cannot show", () => {
    expect(unshown([run(undefined), run(3)], words(9))).toBe(3);
  });

  it("counts a short block though another block of its mode shows every word (review of #571)", () => {
    expect(unshown([block("l4", 60, { list: "copy" }), block("l4", 10, { list: "copy" })], words(3))).toBe(2);
  });

  it("counts a picked block that goes on as showing all, when the run-on block is on the sheet", () => {
    expect(unshown([run(undefined)], words(5), [run(undefined), run(3)])).toBe(0);
    expect(unshown([run(undefined)], words(5))).toBe(2);
  });

  it("counts nothing for a sheet with no linked block", () => {
    expect(unshown([block("l4", 30)], words(9))).toBe(0);
  });
});

describe("linked", () => {
  it("grows an unlinked block to a row for each word and keeps its text", () => {
    const out = linked(block("l4", 20, { text: "eigen" }), "copy", words(5), 210, 297);
    expect(out.h).toBe(50);
    expect(out.props.list).toBe("copy");
    expect(out.props.text).toBe("eigen");
  });

  it("stops the grown block at the bottom margin, in whole rows", () => {
    const out = linked(plain, "copy", words(40), 210, 297);
    expect(out.y + out.h).toBeLessThanOrEqual(297 - MARGIN);
    expect(out.h / RULINGS.l4.row).toBe(Math.round(out.h / RULINGS.l4.row));
  });

  it("keeps the height of a locked block", () => {
    const out = linked(block("l4", 20, {}, { locked: true }), "copy", words(5), 210, 297);
    expect(out.h).toBe(20);
    expect(out.props.list).toBe("copy");
  });

  it("keeps the height of a block already linked when the mode changes", () => {
    const out = linked(block("l4", 20, { list: "copy" }), "row", words(40), 210, 297);
    expect(out.h).toBe(20);
    expect(out.props.list).toBe("row");
  });

  it("keeps the height of a block with more rows than words", () => {
    const out = linked(block("l4", 100), "copy", words(5), 210, 297);
    expect(out.h).toBe(100);
    expect(out.props.list).toBe("copy");
  });

  it("never loses rows, and never runs past the bottom margin when the block did not", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 60 }), fc.constantFrom(...(Object.keys(RULINGS) as Ruling[])), (n, kind) => {
        const start = block(kind, 2 * RULINGS[kind].row);
        const out = linked(start, "copy", words(n), 210, 297);
        expect(rowsOf(out)).toBeGreaterThanOrEqual(rowsOf(start));
        expect(out.y + out.h).toBeLessThanOrEqual(297 - MARGIN);
      }),
    );
  });
});

describe("loose", () => {
  it("cuts a copy block loose with its words as text, no trace and no list", () => {
    const out = loose(block("l4", 20, { list: "copy", trace: true }), ["Hund", "Katze"]);
    expect(out.props.text).toBe("Hund\nKatze");
    expect("trace" in out.props).toBe(false);
    expect("list" in out.props).toBe(false);
  });

  it("keeps trace on for a trace block", () => {
    const out = loose(block("l4", 20, { list: "trace" }), ["Hund"]);
    expect(out.props.trace).toBe(true);
    expect("list" in out.props).toBe(false);
  });

  it("keeps trace on for a row block", () => {
    expect(loose(block("l4", 20, { list: "row" }), ["Hund"]).props.trace).toBe(true);
  });

  it("gives an unlinked block back as the same object", () => {
    expect(loose(plain, ["Hund"])).toBe(plain);
  });

  it("cuts a fold block loose with no trace, and its folds go", () => {
    const out = loose(block("l4", 20, { list: "fold", folds: 3 }), ["Hund"]);
    expect(out.props.text).toBe("Hund");
    expect("trace" in out.props).toBe(false);
    expect("folds" in out.props).toBe(false);
    expect("list" in out.props).toBe(false);
  });
});

describe("looseText", () => {
  it("gives a text its words as its own text, and drops its list settings and rich text", () => {
    const out = looseText({ text: "x", rich: [{ runs: [{ text: "x" }] }], list: true, listCols: 3, size: 14, align: "left" }, ["Hund", "Katze"]);
    expect(out).toEqual({ text: "Hund\nKatze", size: 14, align: "left" });
  });

  it("keeps the look of a text the words are cut from", () => {
    const out = looseText({ text: "", list: true, bold: true, mix: 9, size: 12 }, ["Igel"]);
    expect(out).toEqual({ text: "Igel", bold: true, mix: 9, size: 12, mixLine: "after" });
  });

  it("keeps the Lückenwörter as gaps of its own text, at the letters they hid", () => {
    const out = looseText<Partial<TextProps>>({ text: "", list: true, holes: "one", holeSeed: 7, size: 14 }, ["Hund", "Katze"]);
    expect(out.text).toBe("Hund\nKatze");
    expect(out.rich).toHaveLength(2);
    for (const [i, word] of ["Hund", "Katze"].entries()) {
      const runs = out.rich![i].runs;
      expect(runs.filter((r) => r.gap)).toHaveLength(1);
      expect(runs.map((r) => r.text).join("")).toBe(word);
    }
    expect("holes" in out).toBe(false);
    expect("holeSeed" in out).toBe(false);
    expect("list" in out).toBe(false);
  });

  it("with no words keeps the own text and the rich text, and still drops the list settings", () => {
    const rich = [{ runs: [{ text: "eigen" }] }];
    const out = looseText({ text: "eigen", rich, list: true, listCols: 2, holes: "one", holeSeed: 4, size: 14 }, []);
    expect(out).toEqual({ text: "eigen", rich, size: 14 });
  });

  it("gives a mixed linked text the line after each word, unless it has a line", () => {
    expect(looseText({ text: "", list: true, mix: 7 }, ["Igel"])).toEqual({ text: "Igel", mix: 7, mixLine: "after" });
    expect(looseText({ text: "", list: true, mix: 7, mixLine: "under" }, ["Igel"])).toEqual({ text: "Igel", mix: 7, mixLine: "under" });
  });
});

describe("landed for texts and shapes", () => {
  const text = (props: Partial<TextBlock["props"]>): TextBlock => ({ id: "t", type: "text", x: 20, y: 20, w: 100, h: 40, z: 1, locked: false, props: { text: "", size: 14, align: "left", ...props } });
  const linkedText = text({ list: true, listCols: 2, holes: "vowels", holeSeed: 3, text: "eigen" });

  it("leaves a linked text alone when the copied list is the sheet's own", () => {
    const out = landed([linkedText], ["Hund"], doc(["Hund"]));
    expect(out.blocks).toEqual([linkedText]);
    expect(out.words).toBeUndefined();
  });

  it("brings the copied list along to a sheet with none, and keeps a linked text linked", () => {
    const out = landed([linkedText], ["Hund"], doc());
    expect(out.blocks).toEqual([linkedText]);
    expect(out.words).toEqual(["Hund"]);
  });

  it("cuts a linked text loose with the copied words when the lists differ", () => {
    const out = landed([linkedText], ["Maus"], doc(["Hund"]));
    const rich = [{ runs: [{ text: "M" }, { text: "a", gap: true }, { text: "u", gap: true }, { text: "s" }] }];
    expect(out.blocks[0]).toEqual({ ...linkedText, props: { text: "Maus", size: 14, align: "left", rich } });
  });

  it("cuts a linked shape loose too, and leaves an unlinked text and a line as they are", () => {
    const shape = { ...text({ list: true, text: "x" }), type: "shape", props: { kind: "rect", fill: "none", stroke: "#000000", strokeWidth: 0.5, list: true, text: "x", size: 14, align: "left" } } as Block;
    const plainText = text({ text: "frei" });
    const line = { ...text({}), type: "shape", props: { kind: "line", fill: "none", stroke: "#000000", strokeWidth: 0.5, size: 14, align: "left" } } as Block;
    const out = landed([shape, plainText, line], ["Maus"], doc(["Hund"]));
    expect(out.blocks[0].props).toEqual({ kind: "rect", fill: "none", stroke: "#000000", strokeWidth: 0.5, text: "Maus", size: 14, align: "left" });
    expect(out.blocks[1]).toBe(plainText);
    expect(out.blocks[2]).toBe(line);
  });

  it("keeps a plain text with rich text when the copied list is cut loose elsewhere", () => {
    const rich = text({ rich: [{ runs: [{ text: "fett", bold: true }] }], text: "fett" });
    expect(landed([linkedText, rich], ["Maus"], doc(["Hund"])).blocks[1]).toBe(rich);
  });
});

describe("landed", () => {
  const blocks: Block[] = [linkedBlock, plain];
  const cut = (text: string): Block[] => [{ ...linkedBlock, props: { kind: "l4", color: "#222222", text } }, plain];

  it("leaves blocks alone when none is a linked ruling", () => {
    const out = landed([plain], ["Hund"], doc(["Katze"]));
    expect(out.blocks).toEqual([plain]);
    expect(out.words).toBeUndefined();
  });

  it("brings the copied list along when the sheet has no words", () => {
    const from = ["Hund, Katze", "Maus"];
    const out = landed(blocks, from, doc());
    expect(out.blocks).toBe(blocks);
    expect(out.words).toBe(from);
  });

  it("keeps the blocks when both lists are the same", () => {
    const out = landed(blocks, ["Hund, Katze"], doc(["Hund", "Katze"]));
    expect(out.blocks).toBe(blocks);
    expect(out.words).toBeUndefined();
  });

  it("cuts the linked blocks loose with the copied words when the lists differ", () => {
    const out = landed(blocks, ["Maus"], doc(["Hund"]));
    expect(out.blocks[0].type === "ruling" && out.blocks[0].props.text).toBe("Maus");
    expect(out.blocks[0].type === "ruling" && "list" in out.blocks[0].props).toBe(false);
    expect(out.blocks[1]).toBe(plain);
    expect(out.words).toBeUndefined();
  });

  it.each([undefined, "Hund", 5])("cuts the linked blocks loose with no text when the copied list is %s and the sheet has words", (from) => {
    const out = landed(blocks, from, doc(["Hund"]));
    expect(out.blocks[0].type === "ruling" && out.blocks[0].props.text).toBe("");
    expect(out.words).toBeUndefined();
  });

  it.each([undefined, "Hund", 5])("leaves the blocks as they are when the copied list is %s and the sheet has no words", (from) => {
    const out = landed(cut("x"), from, doc());
    expect(out.blocks).toEqual(cut("x"));
    expect(out.words).toBeUndefined();
  });
});

describe("blatt", () => {
  const rulings = (out: ReturnType<typeof blatt>) => out[0].slice(2) as RulingBlock[];

  it("gives 3 words the l2 Lineatur, three blocks of 3 rows", () => {
    const out = rulings(blatt(words(3), 210, 297));
    expect(out.map((b) => b.props.kind)).toEqual(["l2", "l2", "l2"]);
    expect(out.map((b) => b.h)).toEqual([48, 48, 48]);
  });

  it("gives 6 words the l3 Lineatur", () => {
    expect(rulings(blatt(words(6), 210, 297))[0].props.kind).toBe("l3");
  });

  it("gives 30 words the lines, as many rows as fit a third, and runs on to a second page", () => {
    const pages = blatt(words(30), 210, 297);
    expect(pages.length).toBe(4);
    expect(rulings(pages).map((b) => b.props.kind)).toEqual(["lines", "lines", "lines"]);
    expect(rulings(pages).map((b) => b.h)).toEqual([72, 72, 72]);
  });

  it("gives a run-on page the next words of each mode, with no heading", () => {
    const pages = blatt(words(30), 210, 297);
    const second = pages[1] as RulingBlock[];
    expect(second.map((b) => b.type)).toEqual(["ruling", "ruling", "ruling"]);
    expect(second.map((b) => b.props.list)).toEqual(["copy", "trace", "row"]);
    expect(second.map((b) => b.props.from)).toEqual([9, 9, 9]);
    expect(pages[0].slice(2).map((b) => (b as RulingBlock).props.from)).toEqual([undefined, undefined, undefined]);
  });

  it("gives a page of rows for every word, once, in each mode", () => {
    const pages = blatt(words(30), 210, 297);
    for (const mode of ["copy", "trace", "row"]) {
      const shown = pages.flatMap((page) => page.filter((b) => b.type === "ruling" && (b.props as RulingBlock["props"]).list === mode)).map((b) => (b.props as RulingBlock["props"]).from ?? 0);
      expect(shown).toEqual(pages.map((_, p) => p * 9));
    }
  });

  it.each([3, 6, 30])("ends every block above the bottom margin with %i words, portrait and landscape", (n) => {
    for (const [W, H] of [[210, 297], [297, 210]]) {
      for (const b of blatt(words(n), W, H).flat()) expect(b.y + b.h).toBeLessThanOrEqual(H - MARGIN);
    }
  });

  it("puts no two blocks over each other", () => {
    for (const out of blatt(words(30), 210, 297)) {
      for (let i = 1; i < out.length; i++) expect(out[i - 1].y + out[i - 1].h).toBeLessThanOrEqual(out[i].y);
    }
  });

  it("takes the modes copy, trace and row in order", () => {
    expect(rulings(blatt(words(3), 210, 297)).map((b) => b.props.list)).toEqual(["copy", "trace", "row"]);
  });
});

describe("filled", () => {
  it("fills a block to the bottom margin in whole rows", () => {
    const out = filled(plain, 210, 297);
    expect(out.h).toBe(260);
  });
});

describe("follow", () => {
  const lernwoerter = (props: Partial<RulingBlock["props"]> = {}, extra: Partial<RulingBlock> = {}) => block("l1", 120, { list: "copy", ...props }, { y: 55, ...extra });
  const below = block("l4", 20, {}, { id: "below", y: 200 });

  it("grows a linked ruling by a row for each word it lacks", () => {
    const out = follow([lernwoerter()], words(7), 210, 297);
    expect(out[0].h).toBe(140);
  });

  it("stops the ruling at the bottom margin", () => {
    const out = follow([lernwoerter()], words(14), 210, 297);
    expect(out[0].h).toBe(220);
    expect(out[0].y + out[0].h).toBeLessThanOrEqual(297 - MARGIN);
  });

  it("stops the ruling at the top of a block below it that it overlaps", () => {
    const out = follow([lernwoerter(), below], words(14), 210, 297);
    expect(out[0].h).toBe(140);
    expect(out[1]).toBe(below);
  });

  it("never shrinks a ruling with more rows than words", () => {
    expect(follow([lernwoerter()], words(2), 210, 297)[0].h).toBe(120);
  });

  it("keeps a locked ruling as it is", () => {
    expect(follow([lernwoerter({}, { locked: true })], words(14), 210, 297)[0].h).toBe(120);
  });

  it("keeps the height of a ruling that a run-on ruling goes on from", () => {
    const first = lernwoerter();
    const runOn = block("l1", 60, { list: "copy", from: 6 }, { id: "next", y: 175 });
    const out = follow([first, runOn], words(14), 210, 297);
    expect(out[0].h).toBe(120);
  });

  it("keeps a turned ruling as it is", () => {
    expect(follow([lernwoerter({}, { angle: 180 })], words(14), 210, 297)[0].h).toBe(120);
  });

  it("stops at a block that lies over the ruling's foot or round it", () => {
    const over = block("l4", 40, {}, { id: "over", y: 150 });
    expect(follow([lernwoerter(), over], words(14), 210, 297)[0].h).toBe(120);
    const frame = block("l4", 150, {}, { id: "frame", y: 50 });
    expect(follow([lernwoerter(), frame], words(14), 210, 297)[0].h).toBe(120);
  });

  it("keeps the height of a ruling whose run-on ruling lies on the next page", () => {
    const first = lernwoerter();
    const runOn = block("l1", 60, { list: "copy", from: 6 }, { id: "next", y: 15 });
    const out = follow([first], words(14), 210, 297, [first, runOn]);
    expect(out[0].h).toBe(120);
  });
});
