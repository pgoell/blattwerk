// The Suchsel layout: the letters of a word, the settings, the placing, the loosening, the fill and the second spelling.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import type { SuchselProps, Ways } from "./sheet";
import { type Hidden, laid, letters, sane } from "./suchsel";

const base: SuchselProps = { words: ["Hund", "Katze", "Maus", "Vogel", "Fisch"], cols: 10, rows: 10, ways: "across", caps: true, umlauts: true, show: "words", seed: 1 };

const word = fc.array(fc.constantFrom(..."ABEN"), { minLength: 3, maxLength: 8 }).map((cs) => cs.join(""));
const props = fc.record({
  words: fc.array(word, { minLength: 1, maxLength: 8 }),
  cols: fc.integer({ min: 6, max: 12 }),
  rows: fc.integer({ min: 6, max: 12 }),
  ways: fc.constantFrom<Ways>("across", "down", "diag", "back"),
  caps: fc.boolean(),
  umlauts: fc.boolean(),
  show: fc.constantFrom<"words" | "count">("words", "count"),
  seed: fc.integer(),
}) as fc.Arbitrary<SuchselProps>;

// An independent check, not the code under test: no run of a word in any of the eight directions uses a square that no
// hidden word covers.
const DIRS8 = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];
function clean(grid: string[][], hidden: Hidden[], words: string[], caps: boolean): boolean {
  const covered = new Set<string>();
  for (const h of hidden) for (let k = 0; k < h.letters.length; k++) covered.add(`${h.col + k * h.dc}:${h.row + k * h.dr}`);
  const rows = grid.length;
  const cols = grid[0].length;
  for (const w of words) {
    const want = [...(caps ? w.toUpperCase() : w.toLowerCase())];
    for (const [dc, dr] of DIRS8) {
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const squares: string[] = [];
          let fits = true;
          for (let k = 0; k < want.length && fits; k++) {
            const x = c + k * dc;
            const y = r + k * dr;
            fits = x >= 0 && y >= 0 && x < cols && y < rows && grid[y][x] === want[k];
            if (fits) squares.push(`${x}:${y}`);
          }
          if (fits && squares.some((s) => !covered.has(s))) return false;
        }
      }
    }
  }
  return true;
}

describe("letters", () => {
  it("keeps ß and the umlauts with caps and umlauts", () => {
    expect(letters("Straße", true, true)).toEqual(["S", "T", "R", "A", "ß", "E"]);
  });

  it("spells ß as SS in capitals without umlauts", () => {
    expect(letters("Straße", true, false)).toEqual(["S", "T", "R", "A", "S", "S", "E"]);
  });

  it("spells umlauts out and makes every letter small", () => {
    expect(letters("Äpfel", false, false)).toEqual(["a", "e", "p", "f", "e", "l"]);
  });

  it("drops blanks, hyphens and digits", () => {
    expect(letters("Eis-Tee 2", true, true)).toEqual(["E", "I", "S", "T", "E", "E"]);
  });
});

describe("sane", () => {
  it("clamps the size to 6 to 20", () => {
    expect(sane({ ...base, cols: 3, rows: 99 })).toMatchObject({ cols: 6, rows: 20 });
  });

  it("makes a size that is not a number 10", () => {
    expect(sane({ ...base, cols: Number.NaN })).toMatchObject({ cols: 10 });
  });

  it("makes an unknown ways across", () => {
    expect(sane({ ...base, ways: "zigzag" as Ways }).ways).toBe("across");
  });

  it("makes words that are no list an empty list", () => {
    expect(sane({ ...base, words: "Hund" as unknown as string[] }).words).toEqual([]);
  });
});

describe("laid", () => {
  it("gives the same layout for the same props", () => {
    expect(laid(base)).toEqual(laid({ ...base }));
  });

  it("gives another grid for another seed", () => {
    expect(laid(base).grid).not.toEqual(laid({ ...base, seed: 2 }).grid);
  });

  it("stands every hidden word in the grid along its line, inside the grid", () => {
    fc.assert(
      fc.property(props, (p) => {
        const out = laid(p);
        for (const h of out.hidden) {
          for (let k = 0; k < h.letters.length; k++) {
            const c = h.col + k * h.dc;
            const r = h.row + k * h.dr;
            expect(c >= 0 && c < p.cols && r >= 0 && r < p.rows).toBe(true);
            expect(out.grid[r][c]).toBe(h.letters[k]);
          }
        }
      }),
      { numRuns: 200 },
    );
  });

  it("runs every hidden word across when only across", () => {
    fc.assert(fc.property(props, (p) => laid({ ...p, ways: "across" }).hidden.every((h) => h.dc === 1 && h.dr === 0)), { numRuns: 200 });
  });

  it("runs every hidden word across or down when down", () => {
    fc.assert(
      fc.property(props, (p) => laid({ ...p, ways: "down" }).hidden.every((h) => (h.dc === 1 && h.dr === 0) || (h.dc === 0 && h.dr === 1))),
      { numRuns: 200 },
    );
  });

  it("runs every hidden word across, down or diagonally forwards when diag", () => {
    fc.assert(fc.property(props, (p) => laid({ ...p, ways: "diag" }).hidden.every((h) => h.dc === 1 || (h.dc === 0 && h.dr === 1))), { numRuns: 200 });
  });

  it("runs some hidden word backwards when back", () => {
    const backward = Array.from({ length: 20 }, (_, s) => laid({ ...base, ways: "back", seed: s + 1 }).hidden)
      .flat()
      .some((h) => h.dc === -1 || (h.dc === 0 && h.dr === -1));
    expect(backward).toBe(true);
  });

  it("asks for nothing when every word is hidden", () => {
    expect(laid(base).loosen).toEqual([]);
  });

  it("misses a 25-letter word on 6 by 6 and asks for a size", () => {
    const out = laid({ ...base, words: ["ABCDEFGHIJKLMNOPQRSTUVWXY"], cols: 6, rows: 6, ways: "back" });
    expect(out.missed).toEqual(["ABCDEFGHIJKLMNOPQRSTUVWXY"]);
    expect(out.loosen).toEqual(["size"]);
  });

  it("misses a 7-letter word on 6 columns across and asks for a size and ways", () => {
    const out = laid({ ...base, words: ["ABCDEFG"], cols: 6, rows: 10, ways: "across" });
    expect(out.loosen).toEqual(["size", "ways"]);
  });

  it("asks for a size, ways and fewer words when thirty words crowd 6 by 6", () => {
    const words = Array.from({ length: 30 }, (_, i) => [...i.toString(2).padStart(6, "0")].map((b) => (b === "1" ? "E" : "A")).join(""));
    const out = laid({ ...base, words, cols: 6, rows: 6, ways: "across" });
    expect(out.missed.length).toBeGreaterThan(0);
    expect(out.loosen).toEqual(["size", "ways", "words"]);
    expect(out.missed).toEqual(words.filter((w) => !out.hidden.some((h) => h.word === w)));
  });

  it("hides a word that is typed twice once", () => {
    expect(laid({ ...base, words: ["Hund", "hund", "HUND, Hund"] }).hidden.map((h) => h.word)).toEqual(["Hund"]);
  });

  it("keeps the words in the order typed", () => {
    expect(laid({ ...base, words: ["Katze", "Hund", "Maus"] }).hidden.map((h) => h.word)).toEqual(["Katze", "Hund", "Maus"]);
  });

  it("puts a word of two letters in short and never hides it", () => {
    const out = laid({ ...base, words: ["ab", "Hund"] });
    expect(out.short).toEqual(["ab"]);
    expect(out.hidden.map((h) => h.word)).toEqual(["Hund"]);
  });

  it("holds no second spelling of a word, in any direction, with caps false", () => {
    fc.assert(
      fc.property(props, (p) => {
        const out = laid({ ...p, caps: false });
        expect(clean(out.grid, out.hidden, p.words, false)).toBe(true);
      }),
      { numRuns: 200 },
    );
  });

  it("holds no second spelling of a word, in any direction", () => {
    fc.assert(
      fc.property(props, (p) => {
        const out = laid({ ...p, caps: true });
        expect(clean(out.grid, out.hidden, p.words, true)).toBe(true);
      }),
      { numRuns: 200 },
    );
  });

  it("lays 56 three-letter words on 20 by 20 out fast and without a second spelling", () => {
    const words: string[] = [];
    for (const x of "ENISRATD") for (const y of "ENISRATD") if (x !== y) words.push(`${x}${y}E`);
    for (const seed of [1, 2]) {
      const t = performance.now();
      const out = laid({ ...base, words, cols: 20, rows: 20, ways: "back", seed });
      // About 150 ms on a free machine; the limit leaves room for a loaded one.
      expect(performance.now() - t).toBeLessThan(3000);
      expect(clean(out.grid, out.hidden, words, true)).toBe(true);
    }
  });

  it("ends soon on a list that no fill can satisfy", () => {
    // E, any letter, E: whatever stands between two E spells a word, so the sweeps run to their end.
    const words = [..."ENISRATDHULCGMOBWFKZPVJYXQÜÄÖ"].map((l) => `E${l}E`);
    const t = performance.now();
    laid({ ...base, words, cols: 20, rows: 20, ways: "back", seed: 1 });
    expect(performance.now() - t).toBeLessThan(3000);
  });

  it("fills the empty squares by German letter frequency", () => {
    const out = laid({ ...base, cols: 20, rows: 20, words: ["Hund"], seed: 7 });
    const covered = new Set(out.hidden.flatMap((h) => h.letters.map((_, k) => `${h.col + k * h.dc},${h.row + k * h.dr}`)));
    const fills: string[] = [];
    out.grid.forEach((row, r) => row.forEach((l, c) => !covered.has(`${c},${r}`) && fills.push(l)));
    const count = (l: string) => fills.filter((x) => x === l).length;
    for (const l of "ABCDFGHIJKLMNOPRSTUVWZ") if (l !== "E") expect(count("E")).toBeGreaterThan(count(l));
    for (const rare of "QXY") for (const common of "ENISR") expect(count(rare)).toBeLessThan(count(common));
  });
});
