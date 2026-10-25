// What `squares` gives a Karo: one square for a character a reader sees.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { squares } from "./ruling";

const SHY = "\u00AD";
const ZWJ = "\u200D";

// The rule before a hidden character was skipped: one square for every code point. A plain text, with none of
// those characters, keeps the squares it had.
function byCodePoint(text: string, cols: number): [number, number, string, number][] {
  const out: [number, number, string, number][] = [];
  const chars = [...text];
  const hyphen = (j: number) => (chars[j] === "-" && j > 0 && chars[j - 1] !== " " && /\p{L}/u.test(chars[j + 1] ?? "")) || chars[j] === "\u2013" || chars[j] === "\u2014";
  const before = (j: number) => chars[j] === "\u2014" && j > 0 && chars[j - 1] !== " " && chars[j - 1] !== "\n";
  let [x, y, i] = [0, 0, 0];
  chars.forEach((ch, n) => {
    if (ch === "\n") [x, y] = [0, y + 1];
    else if (ch !== " " && (n === 0 || chars[n - 1] === " " || chars[n - 1] === "\n" || hyphen(n - 1) || before(n))) {
      let len = 0;
      for (let j = n; j < chars.length && chars[j] !== " " && chars[j] !== "\n" && !(j > n && before(j)); j++) {
        len = j - n + 1;
        if (hyphen(j)) break;
      }
      const unit = len + (chars[n + len] === " " ? 1 : 0);
      if (x > 0 && x + unit > cols) [x, y] = [0, y + 1];
    }
    if (ch !== "\n") {
      if (x === cols) [x, y] = [0, y + 1];
      out.push([x++, y, ch, i]);
    }
    i += ch.length;
  });
  return out;
}

const plain = fc.array(fc.constantFrom("a", "b", "c", " ", "\n", "-", "\u2013", "\u2014", "ä", "3"), { maxLength: 24 }).map((cs) => cs.join(""));

describe("squares", () => {
  it("keeps a plain text on the squares it had", () => {
    fc.assert(
      fc.property(plain, fc.integer({ min: 1, max: 12 }), (text, cols) => {
        expect(squares(text, cols)).toEqual(byCodePoint(text, cols));
      }),
    );
  });

  it("still breaks a word at a hyphen a reader sees", () => {
    expect(squares("Mathe-Heft", 8).map(([x, y, ch]) => [x, y, ch])).toEqual([
      [0, 0, "M"],
      [1, 0, "a"],
      [2, 0, "t"],
      [3, 0, "h"],
      [4, 0, "e"],
      [5, 0, "-"],
      [0, 1, "H"],
      [1, 1, "e"],
      [2, 1, "f"],
      [3, 1, "t"],
    ]);
  });

  it("gives a soft hyphen no square, so the next letter keeps its column", () => {
    // "Fe­nster": the soft hyphen lies inside the first syllable. Its offset is 2, and no square stands there.
    expect(squares(`Fe${SHY}nster`, 10).map(([, , ch, o]) => [ch, o])).toEqual([
      ["F", 0],
      ["e", 1],
      ["n", 3],
      ["s", 4],
      ["t", 5],
      ["e", 6],
      ["r", 7],
    ]);
    // Five squares. Counted, the soft hyphen would push the last letter onto the next row.
    expect(squares(`abcd${SHY}e`, 5).map(([x, y, ch]) => [x, y, ch])).toEqual([
      [0, 0, "a"],
      [1, 0, "b"],
      [2, 0, "c"],
      [3, 0, "d"],
      [4, 0, "e"],
    ]);
  });

  it("gives a zero width joiner no square", () => {
    const man = "\u{1F468}";
    const woman = "\u{1F469}";
    expect(squares(`a${ZWJ}b`, 4).map(([, , ch, o]) => [ch, o])).toEqual([
      ["a", 0],
      ["b", 2],
    ]);
    expect(squares(man + ZWJ + woman, 4).map(([, , ch, o]) => [ch, o])).toEqual([
      [man, 0],
      [woman, man.length + ZWJ.length],
    ]);
  });

  it("keeps a combining mark on the letter before it", () => {
    // A decomposed "Bäume": the dots stay on the a, and the square shows the composed letter.
    expect(squares("Ba\u0308ume", 10).map(([, , ch, o]) => [ch, o])).toEqual([
      ["B", 0],
      ["ä", 1],
      ["u", 3],
      ["m", 4],
      ["e", 5],
    ]);
    expect(squares("a\u0308\u0301", 4).map(([, , ch, o]) => [ch, o])).toEqual([["ä\u0301", 0]]);
    // A mark with no letter before it is its own square: there is nothing to put it on.
    expect(squares("\u0308a", 4).map(([, , ch]) => ch)).toEqual(["\u0308", "a"]);
  });
});
