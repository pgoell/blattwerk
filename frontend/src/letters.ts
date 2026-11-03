// Colours letters in a text (Zeichen markieren). Vowels are a, e, i, o, u. Umlauts are ä, ö, ü
// and are not vowels here, so each kind can have its own colour. Every other letter is a consonant.
// A word is a run of letters. A soft hyphen stays inside the word, so a break a table inserts does
// not split it. Punctuation, digits and spaces are never coloured: they keep the text's own colour.

export type Where = "any" | "start" | "end";

/** One group of letters the teacher named, such as "sch", with where it matches and its colour. */
export type LetterGroup = {
  /** The letters to colour, such as "sch" or "ei". Capitals do not matter. A space or a mark is left out when matching. */
  letters: string;
  /** Where the letters match: "any" anywhere in a word, "start" at a word's start, "end" at a word's end. */
  where: Where;
  /** Colour of the letters as a hex colour, such as "#e02424". */
  color: string;
};

/** Which letters of a text are coloured, and in which colour. Absent fields colour nothing. */
export type LetterMarks = {
  /** Colour of the vowels a, e, i, o and u, as a hex colour such as "#e02424". Absent means those vowels are not coloured. Umlauts are not vowels here. */
  vowels?: string;
  /** Colour of the umlauts ä, ö and ü, as a hex colour such as "#1a56db". Absent means the umlauts are not coloured. */
  umlauts?: string;
  /** Colour of every other letter, as a hex colour such as "#2f9e44". Absent means those letters are not coloured. */
  consonants?: string;
  /** Colour of the first letter of each word, as a hex colour such as "#f08c00". Absent means the first letter is not coloured for its place. */
  first?: string;
  /** Colour of the last letter of each word, as a hex colour such as "#7048e8". Absent means the last letter is not coloured for its place. */
  last?: string;
  /** Up to three groups of letters, each with a place and a colour. A fourth group and any group after it are left out. */
  groups?: LetterGroup[];
};

/** A stretch of text, with a colour when a mark covers it. */
export type Ink = { text: string; color?: string };

const VOWELS = new Set(["a", "e", "i", "o", "u"]);
const UMLAUTS = new Set(["ä", "ö", "ü"]);
const HEX = /^#[0-9a-fA-F]{6}$/;
const WORD = /\p{L}[\p{L}\p{M}\u00AD\u200D]*/gu;
const GRAPHEME = /\p{L}\p{M}*/gu;

export const COLOURS = {
  vowels: "#e02424",
  umlauts: "#1a56db",
  consonants: "#2f9e44",
  first: "#f08c00",
  last: "#7048e8",
} as const;

export const GROUP_COLOURS = ["#e02424", "#1a56db", "#2f9e44"] as const;

export const hex = (value: unknown): string | undefined =>
  typeof value === "string" && HEX.test(value) ? value.toLowerCase() : undefined;

type Group = { letters: string; where: Where; color: string };
type Sane = {
  vowels?: string;
  umlauts?: string;
  consonants?: string;
  first?: string;
  last?: string;
  groups: Group[];
};

// What a stored value colours. A sheet may come from anywhere: a bad colour, a fourth group or a
// group that is not letters colours nothing. An empty group the teacher is still typing is left out.
export function sane(raw: unknown): Sane | undefined {
  if (!raw || typeof raw !== "object") return undefined;
  const marks = raw as LetterMarks;
  const groups: Group[] = [];
  for (const item of Array.isArray(marks.groups) ? marks.groups : []) {
    if (groups.length === 3 || !item || typeof item !== "object") continue;
    const letters = String(item.letters ?? "").normalize("NFC").toLowerCase().replace(/[^\p{L}\p{M}]/gu, "");
    const where = item.where === "start" || item.where === "end" || item.where === "any" ? item.where : undefined;
    const color = hex(item.color);
    if (!letters || !where || !color) continue;
    groups.push({ letters, where, color });
  }
  const out: Sane = {
    vowels: hex(marks.vowels),
    umlauts: hex(marks.umlauts),
    consonants: hex(marks.consonants),
    first: hex(marks.first),
    last: hex(marks.last),
    groups,
  };
  if (!out.vowels && !out.umlauts && !out.consonants && !out.first && !out.last && !groups.length) return undefined;
  return out;
}

// What the panel stores. An empty group stays, so the field the teacher is typing in does not vanish.
export function tidy(raw: LetterMarks): LetterMarks | undefined {
  const groups = (Array.isArray(raw.groups) ? raw.groups : []).slice(0, 3).flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const where = item.where === "start" || item.where === "end" || item.where === "any" ? item.where : "any";
    return [{ letters: typeof item.letters === "string" ? item.letters : "", where, color: hex(item.color) ?? COLOURS.vowels }];
  });
  const out: LetterMarks = {};
  const vowels = hex(raw.vowels);
  const umlauts = hex(raw.umlauts);
  const consonants = hex(raw.consonants);
  const first = hex(raw.first);
  const last = hex(raw.last);
  if (vowels) out.vowels = vowels;
  if (umlauts) out.umlauts = umlauts;
  if (consonants) out.consonants = consonants;
  if (first) out.first = first;
  if (last) out.last = last;
  if (groups.length) out.groups = groups;
  return vowels || umlauts || consonants || first || last || groups.length ? out : undefined;
}

type Grapheme = { start: number; end: number; ch: string };

function graphemes(word: string, base: number): Grapheme[] {
  return [...word.matchAll(GRAPHEME)].map((found) => ({
    start: base + (found.index ?? 0),
    end: base + (found.index ?? 0) + found[0].length,
    ch: found[0].normalize("NFC").toLowerCase(),
  }));
}

// One colour per letter. A group wins over the place, the place over the kind. A longer group
// wins over a shorter one, and an earlier group when they cover the same letters.
function coloursOf(gs: Grapheme[], marks: Sane): (string | undefined)[] {
  const flat = gs.map((g) => g.ch).join("");
  const map: number[] = [];
  gs.forEach((g, i) => {
    for (let n = 0; n < g.ch.length; n++) map.push(i);
  });
  const best: ({ color: string; len: number; order: number } | undefined)[] = gs.map(() => undefined);
  marks.groups.forEach((group, order) => {
    const letters = group.letters.normalize("NFC").toLowerCase();
    let from = 0;
    while (letters && from <= flat.length - letters.length) {
      const at = flat.indexOf(letters, from);
      if (at < 0) break;
      const end = at + letters.length;
      const ok = group.where === "any" || (group.where === "start" && at === 0) || (group.where === "end" && end === flat.length);
      if (ok) {
        const [startG, endG] = [map[at], map[end - 1]];
        const len = endG - startG + 1;
        for (let i = startG; i <= endG; i++) {
          const have = best[i];
          if (!have || len > have.len || (len === have.len && order < have.order)) best[i] = { color: group.color, len, order };
        }
      }
      from = at + 1;
    }
  });
  return gs.map((g, i) => {
    if (best[i]) return best[i].color;
    if (i === 0 && marks.first) return marks.first;
    if (i === gs.length - 1 && marks.last) return marks.last;
    if (UMLAUTS.has(g.ch)) return marks.umlauts;
    if (VOWELS.has(g.ch)) return marks.vowels;
    return marks.consonants;
  });
}

// The text in stretches. A stretch has a colour when a mark covers it. Joined, the stretches are the text.
export function inked(text: string, raw: unknown): Ink[] {
  const marks = sane(raw);
  if (!marks || !text) return [{ text }];
  const cuts: { start: number; end: number; color?: string }[] = [];
  let cursor = 0;
  for (const found of text.matchAll(WORD)) {
    const index = found.index ?? 0;
    if (index > cursor) cuts.push({ start: cursor, end: index });
    const gs = graphemes(found[0], index);
    const colors = coloursOf(gs, marks);
    let local = index;
    gs.forEach((g, i) => {
      if (g.start > local) cuts.push({ start: local, end: g.start });
      cuts.push({ start: g.start, end: g.end, color: colors[i] });
      local = g.end;
    });
    const end = index + found[0].length;
    if (end > local) cuts.push({ start: local, end });
    cursor = end;
  }
  if (cursor < text.length) cuts.push({ start: cursor, end: text.length });
  const merged: { start: number; end: number; color?: string }[] = [];
  for (const cut of cuts) {
    if (cut.start === cut.end) continue;
    const last = merged.at(-1);
    if (last && last.color === cut.color && last.end === cut.start) last.end = cut.end;
    else merged.push({ start: cut.start, end: cut.end, color: cut.color });
  }
  if (!merged.length) return [{ text }];
  return merged.map((cut) => ({ text: text.slice(cut.start, cut.end), ...(cut.color && { color: cut.color }) }));
}

// The colour of each place in the text a Karo square looks up, by its offset in UTF-16 units.
export function inkAt(text: string, raw: unknown): Map<number, string> {
  const map = new Map<number, string>();
  let at = 0;
  for (const part of inked(text, raw)) {
    if (part.color) for (let i = 0; i < part.text.length; i++) map.set(at + i, part.color);
    at += part.text.length;
  }
  return map;
}
