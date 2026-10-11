// Schüttelwörter: the letters of a word in a new order, and a paragraph cut into the parts that get mixed.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import type { Para, Run } from "./sheet";
import { mixed, word } from "./scramble";

const letters = fc.array(fc.constantFrom(..."abcäöüß"), { minLength: 3, maxLength: 8 }).map((cs) => cs.join(""));
const runs = fc.array(
  fc.record({ text: fc.array(fc.constantFrom("a", "b", "Ä", " ", "-", "1", "2", ".", "’", "ß", "­"), { maxLength: 10 }).map((cs) => cs.join("")), gap: fc.option(fc.constant(true), { nil: undefined }), bold: fc.option(fc.boolean(), { nil: undefined }) }),
  { maxLength: 4 },
) as fc.Arbitrary<Run[]>;
const paras = fc.array(fc.record({ runs }), { maxLength: 3 }) as fc.Arbitrary<Para[]>;
const text = (parts: { runs: Run[] }[]) => parts.map((p) => p.runs.map((r) => r.text).join("")).join("");

describe("word", () => {
  it("keeps every letter", () => {
    fc.assert(
      fc.property(letters, fc.integer(), (w, seed) => {
        expect([...word(w, seed)].sort()).toEqual([...w].sort());
      }),
    );
  });

  it("gives the same order for the same seed and word", () => {
    expect(word("Schule", 7)).toBe(word("Schule", 7));
  });

  it("never gives the word itself for three or more letters that are not all the same", () => {
    fc.assert(
      fc.property(letters, fc.integer(), (w, seed) => {
        fc.pre(new Set(w).size > 1);
        expect(word(w, seed)).not.toBe(w);
      }),
    );
  });

  it("keeps the first letter when asked, and never gives the word itself after it", () => {
    fc.assert(
      fc.property(letters, fc.integer(), (w, seed) => {
        const rest = w.slice(1);
        expect(word(w, seed, true)[0]).toBe(w[0]);
        fc.pre(rest.length >= 2 && new Set(rest).size > 1);
        expect(word(w, seed, true)).not.toBe(w);
      }),
    );
  });

  it("leaves words of one or two letters as they are", () => {
    expect(word("a", 7)).toBe("a");
    expect(word("Ab", 7)).toBe("Ab");
    expect(word("12", 7)).toBe("12");
  });

  it("keeps the apostrophe where it stands", () => {
    expect(word("geht's", 7)[4]).toBe("'");
  });

  it("gives the same string for a composed and a decomposed umlaut", () => {
    expect(word("Bär", 7)).toBe(word("Bär", 7));
  });

  it("takes out a soft hyphen", () => {
    expect(word("Ha­us", 7)).not.toContain("­");
    expect([...word("Ha­us", 7)].sort()).toEqual(["H", "a", "s", "u"]);
  });

  it("gives the exact words for the seeds the tests pin", () => {
    expect(word("Hund", 7)).toBe("uHnd");
    expect(word("Hund", 7, true)).toBe("Hndu");
    expect(word("Schule", 7)).toBe("hcuSel");
    expect(word("Igel", 3)).toBe("egIl");
    expect(word("Bär", 7)).toBe("rBä");
  });
});

describe("mixed", () => {
  const mix = { seed: 7 };

  it("gives one list of parts for each paragraph, empty for an empty one", () => {
    fc.assert(
      fc.property(paras, (ps) => {
        expect(mixed(ps, mix)).toHaveLength(ps.length);
      }),
    );
    expect(mixed([{ runs: [] }], mix)).toEqual([[]]);
  });

  it("never gives an empty part or an empty run", () => {
    fc.assert(
      fc.property(paras, (ps) => {
        for (const parts of mixed(ps, mix))
          for (const part of parts) {
            expect(part.runs.length).toBeGreaterThan(0);
            for (const r of part.runs) expect(r.text).not.toBe("");
          }
      }),
    );
  });

  it("keeps as many characters as the paragraph has, with no soft hyphen in it", () => {
    fc.assert(
      fc.property(paras, (ps) => {
        const out = mixed(ps, mix);
        ps.forEach((p, i) => {
          const inText = p.runs.map((r) => r.text).join("");
          fc.pre(!inText.includes("­"));
          expect(text(out[i]).length).toBe(inText.normalize("NFC").length);
        });
      }),
    );
  });

  it("does not mix a word that touches a gap, and its part has no source", () => {
    const parts = mixed([{ runs: [{ text: "Hund " }, { text: "Igel", gap: true }] }], mix)[0];
    expect(parts[0].source).toBe("Hund");
    expect(parts.at(-1)?.source).toBeUndefined();
    expect(parts.at(-1)?.runs.at(-1)).toEqual({ text: "Igel", gap: true });
    const half = mixed([{ runs: [{ text: "Hu" }, { text: "nd", gap: true }] }], mix);
    expect(half).toEqual([[{ runs: [{ text: "Hu" }, { text: "nd", gap: true }] }]]);
  });

  it("gives one part for a word half bold, with both runs' settings", () => {
    const [parts] = mixed([{ runs: [{ text: "Hu" }, { text: "nd", bold: true }] }], mix);
    expect(parts).toHaveLength(1);
    expect(parts[0].source).toBe("Hund");
    expect(parts[0].runs.map((r) => [r.text.length, r.bold])).toEqual([
      [2, undefined],
      [2, true],
    ]);
  });

  it("gives the punctuation and spaces parts without a source", () => {
    const [parts] = mixed([{ runs: [{ text: "Hund, Igel. " }] }], mix);
    const bare = parts.filter((p) => p.source === undefined);
    expect(bare.map((p) => text([p]))).toEqual([", ", ". "]);
  });

  it("gives capitals with caps on, and SS for ß, without losing or doubling a letter", () => {
    const [parts] = mixed([{ runs: [{ text: "Straße" }] }], { seed: 7, caps: true });
    expect(parts[0].source).toBe("Straße");
    expect(text(parts)).toBe(word("Straße", 7).toLocaleUpperCase("de"));
    expect(text(parts)).toMatch(/^[A-Z]+$/);
    expect([...text(parts)].sort()).toEqual([...word("Straße", 7).toLocaleUpperCase("de")].sort());
  });

  it("gives a number like 12 no source", () => {
    expect(mixed([{ runs: [{ text: "12" }] }], mix)).toEqual([[{ runs: [{ text: "12" }] }]]);
  });

  it("takes a soft hyphen out of the word and keeps one word", () => {
    const [parts] = mixed([{ runs: [{ text: "Ha­us" }] }], mix);
    expect(parts).toHaveLength(1);
    expect(parts[0].source).toBe("Haus");
    expect(text(parts)).not.toContain("­");
  });
});
