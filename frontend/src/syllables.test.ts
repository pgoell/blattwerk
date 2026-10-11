import fc from "fast-check";
import { expect, it } from "vitest";
import { cuts, keyOf, pieces, split, words } from "./syllables";
import { WORDS } from "./syllables.words";

// A word with its breaks written in, as the list has them.
const dashed = (word: string, at = split(word)) => [0, ...at].map((from, i) => word.slice(from, at[i])).join("-");
const LIST = Object.values(WORDS).flat();
// Words of the list the module splits wrong. None.
const KNOWN = new Set<string>();

it("holds enough words of each kind, each once", () => {
  expect(LIST.length).toBeGreaterThanOrEqual(220);
  expect(new Set(LIST).size).toBe(LIST.length);
  for (const [kind, list] of Object.entries(WORDS)) expect(list.length, kind).toBeGreaterThanOrEqual(12);
});

it("splits each word of the list as school does", () => {
  const wrong = LIST.filter((want) => dashed(want.replaceAll("-", "")) !== want).map((want) => `${want}: ${dashed(want.replaceAll("-", ""))}`);
  expect(wrong.filter((line) => !KNOWN.has(line.split(":")[0]))).toEqual([]);
  // A word that has come right leaves KNOWN.
  expect([...KNOWN].filter((want) => !wrong.some((line) => line.startsWith(`${want}:`)))).toEqual([]);
});

it("keeps to its rules and its exceptions outside the list", () => {
  // "ie" and "ee" at a word's end: one vowel, or two where the stress lies before it or "en" follows.
  for (const want of ["Me-lo-die", "Me-lo-di-en", "Groß-fa-mi-li-e", "Fa-mi-li-en", "Ko-lo-nie", "Fe-en", "I-de-en", "schien", "Wien", "Bie-nen"]) expect(dashed(want.replaceAll("-", ""))).toBe(want);
  // Two vowels that are one, in words from abroad.
  for (const want of ["Team", "Jeans", "Toast", "Ka-kao", "Toi-let-te", "Hal-lo-ween"]) expect(dashed(want.replaceAll("-", ""))).toBe(want);
  // A consonant of several letters goes whole to the next syllable; "qu" and "y" before a vowel are consonants.
  for (const want of ["A-sche", "E-cho", "A-qua-ri-um", "Yo-ga", "Ad-ler"]) expect(dashed(want.replaceAll("-", ""))).toBe(want);
  // No vowel, no syllable.
  expect(split("pst")).toEqual([]);
  expect(split("")).toEqual([]);
});

it("keeps an answer, so a word asked for again costs nothing", () => {
  expect(split("Regenbogen")).toBe(split("Regenbogen"));
});

it("splits a word the same in upper case, in lower case and capitalised", () => {
  for (const want of LIST) {
    const word = want.replaceAll("-", "");
    // "ß" has no capital that keeps the word's length.
    if (word.includes("ß")) continue;
    expect(split(word.toUpperCase()), word).toEqual(split(word));
    expect(split(word.toLowerCase()), word).toEqual(split(word));
  }
  expect(split("ABEND")).toEqual([1]);
  expect(split("abend")).toEqual([1]);
});

it("counts in the characters of the text as it came, composed or not", () => {
  // "ä" as one character, and as "a" with the dots as a character of their own.
  expect(dashed("Äpfel".normalize("NFC"))).toBe("Äp-fel");
  expect(dashed("Äpfel".normalize("NFD"))).toBe("Äp-fel".normalize("NFD"));
  expect(dashed("Mäuse".normalize("NFD"))).toBe("Mäu-se".normalize("NFD"));
  expect(dashed("über".normalize("NFD"))).toBe("ü-ber".normalize("NFD"));
  expect(split("Kühe".normalize("NFD"))).toEqual([3]);
  expect(pieces("Bär".normalize("NFD"))).toEqual([{ text: "Bär".normalize("NFD"), syl: true, word: 0 }]);
});

it("gives a text again from its pieces", () => {
  const text = fc.oneof(fc.string({ unit: "grapheme" }), fc.array(fc.constantFrom(...LIST.map((w) => w.replaceAll("-", "")), " ", ", ", "3", "'", "’", "\n", "ä", "-")).map((a) => a.join("")));
  fc.assert(
    fc.property(text, (s) => {
      const got = pieces(s);
      expect(got.map((p) => p.text).join("")).toBe(s);
      expect(got.every((p) => p.text.length > 0)).toBe(true);
      // The syllables are the words, in order.
      expect(got.filter((p) => p.syl).map((p) => p.text).join("")).toBe((s.match(/[\p{L}\p{M}]+(?:['’][\p{L}\p{M}]+)*/gu) ?? []).join(""));
    }),
  );
});

it("makes no syllable of a number or of punctuation", () => {
  expect(pieces("3 Mäuse, 12 Eier!")).toEqual([
    { text: "3 ", syl: false },
    { text: "Mäu", syl: true, word: 0 },
    { text: "se", syl: true, word: 0 },
    { text: ", 12 ", syl: false },
    { text: "Ei", syl: true, word: 1 },
    { text: "er", syl: true, word: 1 },
    { text: "!", syl: false },
  ]);
  expect(pieces("12 + 3 = 15?").some((p) => p.syl)).toBe(false);
  expect(words("Die 3 Mäuse (und 2 Eier).")).toEqual(["Die", "Mäuse", "und", "Eier"]);
  // A hyphen parts two words.
  expect(pieces("Hals-Nasen-Arzt").filter((p) => p.syl).map((p) => p.text)).toEqual(["Hals", "Na", "sen", "Arzt"]);
});

it("keeps an apostrophe inside its word", () => {
  expect(words("Wie geht's, Oma?")).toEqual(["Wie", "geht's", "Oma"]);
  expect(pieces("geht’s").map((p) => p.text)).toEqual(["geht’s"]);
  expect(pieces("'Abend'").map((p) => p.text)).toEqual(["'", "A", "bend", "'"]);
  expect(pieces("Oma's Haus").map((p) => p.text)).toEqual(["O", "ma's", " ", "Haus"]);
});

it("makes no syllable without a vowel", () => {
  for (const word of ["geht's", "gibt's", "hat's", "wie's", "hab'n", "s'ist", "geht’s"]) expect(split(word), word).toEqual([]);
  expect(pieces("Wie geht's?").map((p) => p.text)).toEqual(["Wie", " ", "geht's", "?"]);
  // A consonant alone inside a word goes to the syllable after it.
  expect(dashed("constructor")).toBe("con-struc-tor");
  const vowels = /[aeiouyäöü]/i;
  for (const want of [...LIST, "constructor", "Konstruktion", "Angstschweiß", "Herbststurm"]) {
    const word = want.replaceAll("-", "");
    for (const p of pieces(word)) expect(vowels.test(p.text), `${word}: ${p.text}`).toBe(true);
  }
});

it("tells an egg from the ending of Bäckerei", () => {
  for (const want of ["Spie-gel-ei", "Rühr-ei", "Os-ter-ei", "Hüh-ner-ei", "Nest-ei", "Spie-gel-ei-er", "Bä-cke-rei", "Bü-che-rei", "Ma-le-rei", "Po-li-zei", "Bas-te-lei"]) expect(dashed(want.replaceAll("-", ""))).toBe(want);
});

it("takes no harm from breaks that are no breaks", () => {
  // A word every object has a member for.
  for (const word of ["constructor", "toString", "valueOf", "__proto__", "hasOwnProperty"]) {
    expect(cuts(word, {}), word).toEqual(split(word));
    expect(pieces(`Der ${word} hier`, {}).map((p) => p.text).join("")).toBe(`Der ${word} hier`);
  }
  // What a sheet from elsewhere may hold.
  const junk = (value: unknown) => cuts("Abend", { abend: value } as never);
  for (const value of ["12", 3, null, true, { 0: 1, length: 1 }]) expect(junk(value)).toEqual([1]);
  expect(junk([3, 1])).toEqual([1, 3]);
  expect(junk([2, 2, 2])).toEqual([2]);
  expect(junk([1.5, "2", null, Number.NaN, Infinity, 3])).toEqual([3]);
  expect(pieces("Abend", { abend: [3, 1, 3] }).map((p) => p.text)).toEqual(["A", "be", "nd"]);

  const names = ["constructor", "toString", "valueOf", "__proto__", "hasOwnProperty"];
  const text = fc.array(fc.constantFrom("Abend", "Fenster", "geht's", "Mäuse", ...names, " ", ", ", "3")).map((a) => a.join(""));
  const given = text.chain((s) => fc.tuple(fc.constant(s), fc.dictionary(fc.constantFrom(...words(s).map(keyOf), ...names), fc.oneof(fc.jsonValue(), fc.array(fc.integer({ min: -2, max: 20 }))))));
  fc.assert(
    fc.property(given, ([s, breaks]) => {
      const got = pieces(s, breaks as never);
      expect(got.map((p) => p.text).join("")).toBe(s);
      expect(got.every((p) => p.text.length > 0)).toBe(true);
    }),
  );
});

it("takes the teacher's breaks over its own", () => {
  expect(cuts("Abend")).toEqual([1]);
  expect(cuts("Abend", { abend: [2] })).toEqual([2]);
  expect(cuts("ABEND", { abend: [] })).toEqual([]);
  expect(cuts("Fenster", { abend: [2] })).toEqual([4]);
  // A place before the word's start, at its start, at its end or past it is none.
  expect(cuts("Abend", { abend: [-1, 0, 2, 5, 9] })).toEqual([2]);
  expect(keyOf("Abend")).toBe("abend");
  expect(pieces("Abend", { abend: [3] }).map((p) => p.text)).toEqual(["Abe", "nd"]);
});

it("gives each word of a text once, in order", () => {
  expect(words("Die Maus, die 3 Mäuse und die Maus")).toEqual(["Die", "Maus", "die", "Mäuse", "und"]);
  expect(words("12, 13!")).toEqual([]);
});
