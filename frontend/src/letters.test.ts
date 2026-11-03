// Zeichen markieren: which letters take a colour, and that punctuation does not.
import { describe, expect, it } from "vitest";
import { inked, type LetterMarks } from "./letters";

const RED = "#e02424";
const BLUE = "#1a56db";
const GREEN = "#2f9e44";
const ORANGE = "#f08c00";
const PURPLE = "#7048e8";

const coloured = (text: string, marks: LetterMarks) => inked(text, marks).filter((part) => part.color);

describe("inked", () => {
  it("gives the text back, coloured or not", () => {
    const marks: LetterMarks = { vowels: RED, groups: [{ letters: "sch", where: "start", color: GREEN }] };
    for (const text of ["", "Hallo!", "Schule, Ei und die Maus!", "Ärger", "Fuß", "a\u0308", "Schu\u00ADle"])
      expect(inked(text, marks).map((part) => part.text).join("")).toBe(text);
  });

  it("colours the vowels a e i o u and not the umlauts", () => {
    expect(coloured("Hallo!", { vowels: RED })).toEqual([
      { text: "a", color: RED },
      { text: "o", color: RED },
    ]);
    expect(coloured("Ärger", { vowels: RED })).toEqual([{ text: "e", color: RED }]);
    expect(coloured("HALLO", { vowels: RED })).toEqual([
      { text: "A", color: RED },
      { text: "O", color: RED },
    ]);
  });

  it("colours the umlauts ä ö ü on their own", () => {
    expect(coloured("Ärger", { umlauts: BLUE })).toEqual([{ text: "Ä", color: BLUE }]);
    expect(coloured("schön", { umlauts: BLUE })).toEqual([{ text: "ö", color: BLUE }]);
    expect(coloured("a\u0308", { umlauts: BLUE })).toEqual([{ text: "a\u0308", color: BLUE }]);
    expect(coloured("Hallo", { umlauts: BLUE })).toEqual([]);
  });

  it("colours every other letter as a consonant, ß and y included", () => {
    expect(coloured("Typ Fuß!", { consonants: GREEN })).toEqual([
      { text: "Typ", color: GREEN },
      { text: "F", color: GREEN },
      { text: "ß", color: GREEN },
    ]);
    expect(coloured("aeiouäöü", { consonants: GREEN })).toEqual([]);
  });

  it("colours the first letter and the last letter of each word", () => {
    expect(coloured("Maus rennt", { first: ORANGE })).toEqual([
      { text: "M", color: ORANGE },
      { text: "r", color: ORANGE },
    ]);
    expect(coloured("Maus rennt", { last: PURPLE })).toEqual([
      { text: "s", color: PURPLE },
      { text: "t", color: PURPLE },
    ]);
    expect(coloured("I", { first: ORANGE, last: PURPLE, vowels: RED })).toEqual([{ text: "I", color: ORANGE }]);
    expect(coloured("I", { last: PURPLE })).toEqual([{ text: "I", color: PURPLE }]);
  });

  it("colours up to three letter groups, anywhere or at a word's start or end", () => {
    const groups: LetterMarks["groups"] = [
      { letters: "sch", where: "start", color: GREEN },
      { letters: "ei", where: "any", color: ORANGE },
      { letters: "ie", where: "end", color: PURPLE },
    ];
    expect(coloured("Schule, Ei und die Maus!", { vowels: RED, groups })).toEqual([
      { text: "Sch", color: GREEN },
      { text: "u", color: RED },
      { text: "e", color: RED },
      { text: "Ei", color: ORANGE },
      { text: "u", color: RED },
      { text: "ie", color: PURPLE },
      { text: "au", color: RED },
    ]);
    expect(coloured("rasch", { groups: [{ letters: "sch", where: "start", color: GREEN }] })).toEqual([]);
    expect(coloured("rasch", { groups: [{ letters: "sch", where: "any", color: GREEN }] })).toEqual([{ text: "sch", color: GREEN }]);
    expect(coloured("Tisch", { groups: [{ letters: "sch", where: "end", color: GREEN }] })).toEqual([{ text: "sch", color: GREEN }]);
    expect(coloured("liegen", { groups: [{ letters: "ie", where: "end", color: PURPLE }] })).toEqual([]);
    expect(coloured("SCHULE", { groups: [{ letters: "Sch", where: "start", color: GREEN }] })).toEqual([{ text: "SCH", color: GREEN }]);
  });

  it("lets a group win over the first letter, and the first letter over a vowel", () => {
    expect(coloured("Schule", { first: ORANGE, groups: [{ letters: "sch", where: "start", color: GREEN }] })).toEqual([{ text: "Sch", color: GREEN }]);
    expect(coloured("Apfel", { first: ORANGE, vowels: RED })).toEqual([
      { text: "A", color: ORANGE },
      { text: "e", color: RED },
    ]);
    expect(coloured("sä", { last: ORANGE, umlauts: BLUE })).toEqual([{ text: "ä", color: ORANGE }]);
  });

  it("leaves punctuation, digits and spaces uncoloured", () => {
    const marks: LetterMarks = { vowels: RED, umlauts: BLUE, consonants: GREEN, first: ORANGE, last: PURPLE };
    const parts = inked("Hallo, 3!", marks);
    expect(parts.map((part) => part.text).join("")).toBe("Hallo, 3!");
    for (const part of parts) if (/[^a-zA-ZäöüÄÖÜß]/.test(part.text)) expect(part.color).toBeUndefined();
    expect(coloured("Hallo, 3!", marks).every((part) => /^\p{L}+$/u.test(part.text))).toBe(true);
  });

  it("keeps a soft hyphen inside the word and ignores a fourth group and a bad colour", () => {
    expect(coloured("Schu\u00ADle", { vowels: RED, groups: [{ letters: "sch", where: "start", color: GREEN }] })).toEqual([
      { text: "Sch", color: GREEN },
      { text: "u", color: RED },
      { text: "e", color: RED },
    ]);
    expect(coloured("xx", {
      groups: [
        { letters: "a", where: "any", color: RED },
        { letters: "b", where: "any", color: BLUE },
        { letters: "c", where: "any", color: GREEN },
        { letters: "xx", where: "any", color: ORANGE },
      ],
    })).toEqual([]);
    expect(inked("a", { vowels: "red" })).toEqual([{ text: "a" }]);
    expect(inked("a", null)).toEqual([{ text: "a" }]);
  });

  it("lets the longer group win, and the earlier one when they are the same length", () => {
    expect(coloured("sch", {
      groups: [
        { letters: "s", where: "any", color: RED },
        { letters: "sch", where: "any", color: GREEN },
      ],
    })).toEqual([{ text: "sch", color: GREEN }]);
    expect(coloured("ab", {
      groups: [
        { letters: "a", where: "any", color: RED },
        { letters: "b", where: "any", color: BLUE },
      ],
    })).toEqual([
      { text: "a", color: RED },
      { text: "b", color: BLUE },
    ]);
  });
});
