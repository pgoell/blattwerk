// The solution words of a Lückentext: their reading order, their seeded order, and a table's gap flags.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { cellEntries, entries, shuffled } from "./bank";
import { spliced } from "./sheet";

const run = (text: string, gap?: boolean) => ({ text, ...(gap === undefined ? {} : { gap }) });

describe("entries", () => {
  it("joins consecutive gap runs into one word and leaves out empty ones", () => {
    const paras = [{ runs: [run("Der "), run("Hund", true), run("Ha", true), run(" bellt "), run(" ", true), run("laut", true)] }];
    expect(entries(paras)).toEqual(["HundHa", "laut"]);
  });

  it("gives a word hidden twice twice, in reading order across paragraphs", () => {
    const paras = [{ runs: [run("a", true), run(" b"), run("a", true)] }, { runs: [run("c", true)] }];
    expect(entries(paras)).toEqual(["a", "a", "c"]);
  });

  it("does not count a gap run that is not a gap", () => {
    expect(entries([{ runs: [run("Hund", "yes" as unknown as boolean)] }])).toEqual([]);
  });
});

describe("cellEntries", () => {
  it("takes the trimmed text of each gap cell, row by row", () => {
    const cells = [["Hund ", "x"], ["", "katze"]];
    expect(cellEntries(cells, [[true, false], [true, true]])).toEqual(["Hund", "katze"]);
  });

  it("is empty without gap flags", () => {
    expect(cellEntries([["a"]], undefined)).toEqual([]);
  });
});

describe("shuffled", () => {
  const items = Array.from({ length: 12 }, (_, i) => `w${i}`);

  it("keeps every item", () => {
    fc.assert(
      fc.property(fc.array(fc.string()), fc.integer(), (list, seed) => {
        expect(shuffled(list, seed).sort()).toEqual([...list].sort());
      }),
    );
  });

  it("gives the same order for the same seed and list", () => {
    expect(shuffled(items, 7)).toEqual(shuffled(items, 7));
  });

  it("gives another order for another seed", () => {
    expect(shuffled(items, 7)).not.toEqual(shuffled(items, 8));
  });
});

describe("spliced", () => {
  const props = { cells: [["a", "b"], ["c", "d"]], cols: [1, 1], size: 10, align: "left" as const, line: "#000", gaps: [[true, false], [false, true]] };

  it("keeps the gap flags parallel when a row comes", () => {
    expect(spliced(props, "row", 1, true).gaps).toEqual([[true, false], [false, false], [false, true]]);
  });

  it("keeps the gap flags parallel when a column goes", () => {
    expect(spliced(props, "col", 0, false).gaps).toEqual([[false], [true]]);
  });

  it("leaves gaps absent when the table has none", () => {
    expect("gaps" in spliced({ ...props, gaps: undefined }, "row", 0, true)).toBe(false);
  });
});
