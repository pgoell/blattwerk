// Lückenwörter: which letters of a Lernwort give way to gaps, and that the runs give the word back.
import { describe, expect, it } from "vitest";
import type { Run } from "./sheet";
import { holed } from "./holes";

const gaps = (runs: Run[]) => runs.filter((r) => r.gap === true).map((r) => r.text);
const joined = (runs: Run[]) => runs.map((r) => r.text).join("");
const SEEDS = Array.from({ length: 30 }, (_, i) => i + 1);

describe("holed", () => {
  it("never hides the first letter, and hides one letter of each word of 2 or more letters", () => {
    for (const seed of SEEDS) {
      expect(gaps(holed("Hund Igel Schmetterling", "one", seed))).toHaveLength(3);
      for (const word of ["Hund", "Igel", "Schmetterling"]) {
        const runs = holed(word, "one", seed);
        expect(runs.filter((r) => r.gap)).toHaveLength(1);
        expect(runs[0].gap).not.toBe(true);
      }
    }
  });

  it("gives the same letters for the same seed, and other letters for some other seed", () => {
    expect(holed("Schmetterling", "one", 7)).toEqual(holed("Schmetterling", "one", 7));
    const picks = new Set(SEEDS.map((seed) => JSON.stringify(holed("Schmetterling", "one", seed))));
    expect(picks.size).toBeGreaterThan(1);
  });

  it("hides every second letter, the odd or the even places as the seed says", () => {
    const word = "Schmetterling";
    const picks = new Set(SEEDS.map((seed) => JSON.stringify(gaps(holed(word, "second", seed)))));
    expect(picks.size).toBe(2);
    for (const seed of SEEDS) {
      const runs = holed(word, "second", seed);
      expect(runs.every((r, i) => r.text.length === 1 && (r.gap === true) === (i % 2 === (runs[0].gap ? 0 : 1)))).toBe(true);
    }
  });

  it("hides exactly the vowels, capitals and umlauts included, whatever the seed", () => {
    for (const seed of SEEDS) {
      expect(gaps(holed("Äpfel Öl Übung Haus", "vowels", seed))).toEqual(["Ä", "e", "Ö", "Ü", "u", "a", "u"]);
    }
  });

  it("keeps digits, hyphens, apostrophes and blanks, and a one-letter word", () => {
    expect(holed("12", "vowels", 3)).toEqual([{ text: "12" }]);
    expect(holed("a", "one", 3)).toEqual([{ text: "a" }]);
    expect(gaps(holed("Ka-ta 3's", "vowels", 3))).toEqual(["a", "a"]);
    expect(joined(holed("Ka-ta 3's", "vowels", 3))).toBe("Ka-ta 3's");
  });

  it("gives each hidden letter a run of its own, also two next to each other", () => {
    expect(holed("Auge", "vowels", 1)).toEqual([{ text: "A", gap: true }, { text: "u", gap: true }, { text: "g" }, { text: "e", gap: true }]);
  });

  it("gives the text back when its runs are joined, in NFC", () => {
    for (const mode of ["one", "second", "vowels"] as const) {
      for (const text of ["Hund", "Bär Ärger", "Schmetterling, Igel!", "Schule 2 - Katze's Haus", "Auge"]) {
        expect(joined(holed(text.normalize("NFD"), mode, 11))).toBe(text.normalize("NFC"));
      }
    }
  });
});
