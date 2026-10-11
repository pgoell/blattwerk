// The solution words of a Lückentext: their reading order, their seeded order, and a table's gap flags.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { cellEntries, draw, entries, moves, shuffled, type Shown } from "./bank";
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

describe("shuffled without a list to avoid", () => {
  it("gives the order it gave before", () => {
    expect(shuffled(["a", "b", "c", "d"], 7)).toEqual(["c", "b", "d", "a"]);
  });
});

describe("shuffled that avoids a list", () => {
  const two = fc.array(fc.constantFrom("a", "b", "c"), { minLength: 2, maxLength: 6 }).filter((xs) => new Set(xs).size > 1);

  it("never gives the list to avoid when the items differ", () => {
    fc.assert(
      fc.property(two, fc.integer(), (items, seed) => {
        expect(shuffled(items, seed, items)).not.toEqual(items);
      }),
    );
  });

  it("never gives the list to avoid for another list either", () => {
    fc.assert(
      fc.property(two, fc.integer(), fc.integer(), (items, seed, other) => {
        const avoid = shuffled(items, other);
        expect(shuffled(items, seed, avoid)).not.toEqual(avoid);
      }),
    );
  });

  it("gives what it gives without the list when that already differs", () => {
    fc.assert(
      fc.property(fc.array(fc.constantFrom("a", "b", "c"), { maxLength: 6 }), fc.integer(), fc.array(fc.constantFrom("a", "b", "c"), { maxLength: 6 }), (items, seed, avoid) => {
        const plain = shuffled(items, seed);
        fc.pre(JSON.stringify(plain) !== JSON.stringify(avoid));
        expect(shuffled(items, seed, avoid)).toEqual(plain);
      }),
    );
  });

  it("gives the items as shuffled when they are all the same", () => {
    expect(shuffled(["x", "x"], 1, ["x", "x"])).toEqual(["x", "x"]);
  });

  it("gives the items as shuffled when there are fewer than two", () => {
    expect(shuffled(["x"], 1, ["x"])).toEqual(["x"]);
    expect(shuffled([], 1, [])).toEqual([]);
  });
});

describe("moves", () => {
  it("is true when one held item shows another way under the seed", () => {
    expect(moves([{ seed: 1, show: (s) => String(s % 2) }], 2)).toBe(true);
  });

  it("is false when no held item changes under the seed", () => {
    expect(moves([{ seed: 1, show: () => "a" }, { seed: 3, show: () => "same" }], 4)).toBe(false);
  });

  it("is false for the seed the items have", () => {
    expect(moves([{ seed: 5, show: (s) => String(s % 7) }], 5)).toBe(false);
  });

  it("is true for an item with no seed", () => {
    expect(moves([{ show: () => "same" }], 9)).toBe(true);
  });
});

describe("draw", () => {
  // A stub random generator that gives these seeds in turn, each as the 1 + floor(r * 2147483647) draw reads it.
  const seeds = (...want: number[]) => {
    let at = 0;
    return () => (want[Math.min(at++, want.length - 1)] - 0.5) / 2147483647;
  };
  // Item A changes with the seed's parity, item B with its residue mod 3. A is at seed 2 and B at seed 1.
  const a: Shown = { seed: 2, show: (s) => String(s % 2) };
  const b: Shown = { seed: 1, show: (s) => String(s % 3) };

  it("never gives a held seed", () => {
    fc.assert(
      fc.property(fc.array(fc.integer({ min: 1, max: 2147483647 }), { minLength: 1, maxLength: 5 }), (held) => {
        const shown = held.map((seed) => ({ seed, show: (s: number) => String(s % 7) }));
        expect(held).not.toContain(draw(shown));
      }),
    );
  });

  it("takes the first seed under which every held item changes", () => {
    // Seed 6 leaves A unchanged, seed 5 changes both.
    expect(draw([a, b], seeds(6, 5))).toBe(5);
  });

  it("gives a seed when no item ever changes", () => {
    const still: Shown = { seed: 1, show: () => "same" };
    const seed = draw([still], seeds(4, 9));
    expect(seed).toBe(4);
  });

  it("takes the first seed when nothing is held", () => {
    expect(draw([], () => 0.5)).toBe(1 + Math.floor(0.5 * 2147483647));
  });

  it("gives a seed from 1 to 2147483647", () => {
    fc.assert(
      fc.property(fc.array(fc.integer({ min: 1, max: 2147483647 }), { maxLength: 3 }), (held) => {
        const seed = draw(held.map((s) => ({ seed: s, show: (x: number) => String(x % 5) })));
        expect(Number.isInteger(seed) && seed >= 1 && seed <= 2147483647).toBe(true);
      }),
    );
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
  it("gives garbage in the flags the shape of the cells", () => {
    expect(spliced({ ...props, gaps: ["x", [0, true]] as unknown as boolean[][] }, "col", 2, true).gaps).toEqual([[false, false, false], [false, true, false]]);
  });
});
