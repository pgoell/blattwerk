import { describe, expect, it } from "vitest";
import { MARGIN, rowsOf, type Block, type Doc, type RulingBlock } from "./sheet";
import { blatt, follow, followDoc } from "./words";

const words = (n: number) => Array.from({ length: n }, (_, i) => `wort${i}`);

function laid(n: number): Block[] {
  return blatt(words(n), 210, 297)[0].map((b, i) => ({ ...b, id: `b${i}`, z: i + 1, locked: false }) as Block);
}

function lines(blocks: Block[]): RulingBlock[] {
  return blocks.filter((b): b is RulingBlock => b.type === "ruling").sort((a, b) => a.y - b.y);
}

describe("a stacked Lernwörter-Blatt", () => {
  it("gives every ruling the new word when the page can hold the stack", () => {
    const out = lines(follow(laid(5), words(6), 210, 297));
    expect(out.map(rowsOf)).toEqual([6, 6, 6]);
    expect(out[2].y + out[2].h).toBeLessThanOrEqual(282);
  });

  it("does not give the spare room under the stack to the bottom ruling alone", () => {
    const out = lines(follow(laid(6), words(7), 210, 297));
    expect(out.map(rowsOf)).toEqual([6, 6, 6]);
  });

  it("runs the word that does not fit on to a new page of every ruling", () => {
    const blocks = laid(6);
    const doc: Doc = { pages: [{ blocks }], guides: { x: [], y: [] }, grid: 0, words: words(7) };
    const out = followDoc(doc);
    expect(lines(out.pages[0].blocks).map(rowsOf)).toEqual([6, 6, 6]);
    expect(out.pages).toHaveLength(2);
    const next = lines(out.pages[1].blocks);
    expect(next.map((b) => b.props.list)).toEqual(["copy", "trace", "row"]);
    expect(next.map((b) => b.props.from)).toEqual([6, 6, 6]);
    expect(next.map(rowsOf)).toEqual([1, 1, 1]);
    expect(next[2].y + next[2].h).toBeLessThanOrEqual(297 - MARGIN);
    expect(out.pages[1].blocks.filter((b) => b.type !== "ruling")).toEqual([]);
  });

  it("keeps running on until every word has a row", () => {
    const doc: Doc = { pages: [{ blocks: laid(6) }], guides: { x: [], y: [] }, grid: 0, words: words(14) };
    const out = followDoc(doc);
    const copy = out.pages.flatMap((p) => lines(p.blocks).filter((b) => b.props.list === "copy"));
    expect(copy.reduce((n, b) => n + rowsOf(b), 0)).toBe(14);
    expect(copy.map((b) => b.props.from ?? 0)).toEqual([0, 6, 13]);
    for (const page of out.pages) {
      const stack = lines(page.blocks);
      for (let i = 1; i < stack.length; i++) expect(stack[i - 1].y + stack[i - 1].h).toBeLessThanOrEqual(stack[i].y);
      expect(stack[stack.length - 1].y + stack[stack.length - 1].h).toBeLessThanOrEqual(297 - MARGIN);
    }
  });

  it("grows into a wide gap and leaves the ruling below where it is", () => {
    const upper: RulingBlock = { id: "u", type: "ruling", x: 15, y: 40, w: 180, h: 20, z: 1, locked: false, props: { kind: "l4", color: "#222222", list: "copy" } };
    const lower: RulingBlock = { ...upper, id: "l", y: 90, h: 10, z: 2 };
    const out = follow([upper, lower], words(4), 210, 297);
    expect(out[0]).toMatchObject({ y: 40, h: 40 });
    expect(out[1]).toMatchObject({ y: 90, h: 40 });
  });
});
