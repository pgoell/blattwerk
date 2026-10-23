// Taking a model's words onto a text, and three copies of the page, with no request.
import { describe, expect, it } from "vitest";
import { changed, undone, type Hist } from "./history";
import { EMPTY, type Block, type Doc, type TextBlock } from "./sheet";
import { canHelp, levelled, taken } from "./texthelp";

const text = (over: Partial<TextBlock["props"]> & { text: string }, more: Partial<TextBlock> = {}): TextBlock => ({
  id: "a",
  type: "text",
  x: 20,
  y: 30,
  w: 80,
  h: 40,
  z: 1,
  locked: false,
  ...more,
  props: { size: 18, align: "left", font: "grund", color: "#222222", ...over },
});

const shape = (id: string): Block => ({
  id,
  type: "shape",
  x: 10,
  y: 80,
  w: 20,
  h: 20,
  z: 2,
  locked: false,
  props: { kind: "rect", fill: "none", stroke: "#222222", strokeWidth: 0.5, text: "nebenan", size: 14, align: "left" },
});

const docOf = (blocks: Block[], landscape = false): Doc => ({
  ...EMPTY,
  pages: [{ blocks, ...(landscape ? { landscape: true } : {}) }],
});

const ids = () => {
  let n = 0;
  return () => `n${n++}`;
};

describe("taken", () => {
  it("replaces the words and keeps the place, the font and the size", () => {
    const next = taken(text({ text: "Der Hund ist gross." }), "Der Hund ist klein.");
    expect(next.props.text).toBe("Der Hund ist klein.");
    expect(next.props.rich).toBeUndefined();
    expect(next.props.font).toBe("grund");
    expect(next.props.size).toBe(18);
    expect(next.props.align).toBe("left");
    expect(next.props.color).toBe("#222222");
    expect({ x: next.x, y: next.y, w: next.w, h: next.h }).toEqual({ x: 20, y: 30, w: 80, h: 40 });
  });

  it("keeps a run's look for as many characters as the new line has, and gives the rest to the last run", () => {
    const block = text({
      text: "Hallo Welt",
      rich: [{ runs: [{ text: "Hallo", bold: true }, { text: " Welt", italic: true, color: "#e02424" }] }],
    });
    expect(taken(block, "Hi").props.rich).toEqual([{ runs: [{ text: "Hi", bold: true }] }]);
    expect(taken(block, "Hi Welt").props.rich).toEqual([
      { runs: [{ text: "Hi We", bold: true }, { text: "lt", italic: true, color: "#e02424" }] },
    ]);
    expect(taken(block, "Hallo Welt!!!").props.rich).toEqual([
      { runs: [{ text: "Hallo", bold: true }, { text: " Welt!!!", italic: true, color: "#e02424" }] },
    ]);
  });

  it("drops a gap, keeps a list, and gives a new paragraph no look of its own", () => {
    const block = text({
      text: "Hallo",
      rich: [{ runs: [{ text: "Hallo", bold: true, gap: true }], list: "bullet", level: 1 }],
    });
    const next = taken(block, "Hi\nDu");
    expect(next.props.text).toBe("Hi\nDu");
    expect(next.props.rich).toEqual([
      { runs: [{ text: "Hi", bold: true }], list: "bullet", level: 1 },
      { runs: [{ text: "Du" }] },
    ]);
  });
});

describe("levelled", () => {
  it("keeps the page and adds three copies, marked with one, two and three symbols inside the right margin", () => {
    const check = {
      id: "k",
      type: "selbstkontrolle" as const,
      x: 15,
      y: 120,
      w: 40,
      h: 20,
      z: 3,
      locked: false,
      props: { form: "mixed" as const, links: ["a"], word: "", title: "Selbstkontrolle", size: 14, turn: "none" as const, seed: 1 },
    };
    const start = docOf([text({ text: "Der Hund ist gross." }, { group: ["g1"] }), { ...shape("s"), group: ["g1"] }, check]);
    const out = levelled(start, 0, "a", ["Niveau eins", "Niveau zwei", "Niveau drei"], "270F", ids());
    expect(out.pages[0]).toEqual(start.pages[0]);
    expect(out.pages).toHaveLength(4);
    out.pages.slice(1).forEach((page, i) => {
      const words = page.blocks.find((b) => b.type === "text");
      const marks = page.blocks.filter((b) => b.type === "symbol");
      expect(words && words.type === "text" && words.props.text).toBe(`Niveau ${["eins", "zwei", "drei"][i]}`);
      expect(words && words.type === "text" && words.props.font).toBe("grund");
      expect(marks).toHaveLength(i + 1);
      marks.forEach((mark) => {
        expect(mark.type === "symbol" && mark.props.code).toBe("270F");
        expect(mark.y).toBe(15);
        expect(mark.w).toBe(8);
        expect(mark.h).toBe(8);
      });
      const right = Math.max(...marks.map((mark) => mark.x + mark.w));
      expect(right).toBe(210 - 15);
      expect(page.blocks.find((b) => b.type === "shape" && b.props.text)).toMatchObject({ props: { text: "nebenan" } });
      const linked = page.blocks.find((b) => b.type === "selbstkontrolle");
      const copy = page.blocks.find((b) => b.type === "text");
      expect(linked && linked.type === "selbstkontrolle" && linked.props.links).toEqual(copy ? [copy.id] : []);
      expect(page.blocks.every((b) => b.id.startsWith("n"))).toBe(true);
      expect(new Set(page.blocks.filter((b) => b.group).map((b) => b.group![0])).size).toBe(1);
      expect(page.blocks[0].group![0]).not.toBe("g1");
    });
  });

  it("uses the star when the code is none of the sheet's symbols, and a Quer page's right edge", () => {
    const start = docOf([text({ text: "Hund" })], true);
    const out = levelled(start, 0, "a", ["a", "b", "c"], "nope", ids());
    const mark = out.pages[1].blocks.find((b) => b.type === "symbol");
    expect(mark && mark.type === "symbol" && mark.props.code).toBe("2B50");
    expect(mark && mark.x + mark.w).toBe(297 - 15);
  });

  it("is one undo step back to the page as it was", () => {
    const start = docOf([text({ text: "Hund" })]);
    const next = levelled(start, 0, "a", ["a", "b", "c"], "2B50", ids());
    const hist: Hist = { past: [], doc: start, future: [] };
    const step = changed(hist, { key: "", ahead: [] }, next, "", 0, 1);
    expect(step!.h.past).toHaveLength(1);
    expect(undone(step!.h).doc).toEqual(start);
  });

  it("leaves the sheet when the block is not on that page", () => {
    const start = docOf([text({ text: "Hund" })]);
    expect(levelled(start, 0, "missing", ["a", "b", "c"], "2B50", ids())).toBe(start);
  });
});

describe("canHelp", () => {
  it("is the one unlocked text that shows its own words", () => {
    const block = text({ text: "Hund" });
    expect(canHelp([block])).toBe(block);
    expect(canHelp([block, text({ text: "noch" })])).toBeUndefined();
    expect(canHelp([text({ text: "  " })])).toBeUndefined();
    expect(canHelp([text({ text: "Hund", list: true })])).toBeUndefined();
    expect(canHelp([text({ text: "Hund" }, { locked: true })])).toBeUndefined();
    expect(canHelp([shape("s")])).toBeUndefined();
    expect(canHelp([{ id: "m", type: "maths", x: 0, y: 0, w: 10, h: 10, z: 0, locked: false, props: { max: 20 } } as Block])).toBeUndefined();
  });
});
