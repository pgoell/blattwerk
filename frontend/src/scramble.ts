// Schüttelwörter: the letters of each word of a text in a new order, from a seed. The same seed and word give the same
// order everywhere, so the editor and the PDF agree.
import type { Para, Run } from "./sheet";
import { shuffled } from "./bank";

// The settings of Schüttelwörter: the seed, whether the first letter stays, and whether all letters are capitals.
export type Mix = { seed: number; first?: boolean; caps?: boolean };
// A part of a paragraph: runs as they are, or one word with its letters mixed; `source` is that word as typed.
export type Part = { runs: Run[]; source?: string };

// A letter with the marks that belong to it, so that they move with it.
const LETTER = /\p{L}\p{M}*/gu;
// A word: letters, marks, digits and soft hyphens, with an apostrophe or a hyphen between two of them.
const WORD = /[\p{L}\p{M}\p{N}\xAD]+(?:['’-][\p{L}\p{M}\p{N}\xAD]+)*/gu;
const SOFT = /\xAD/g;

// A hash of the word's text, so that the same word gets the same order wherever it stands.
const hash = (text: string) => {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h;
};

// One word with its letters in the seeded order. Marks, apostrophes and hyphens stay where they are.
export function word(source: string, seed: number, first?: boolean): string {
  const text = source.normalize("NFC").replace(SOFT, "");
  const letters = text.match(LETTER) ?? [];
  if (letters.length < 3) return text;
  const keep = first ? 1 : 0;
  const rest = letters.slice(keep);
  const mixed = [...letters.slice(0, keep), ...shuffled(rest, (seed ^ hash(text)) | 0, rest)];
  let at = 0;
  return text.replace(LETTER, () => mixed[at++]);
}

// Each paragraph as its parts, in order. A word with a letter that touches no gap is one part with its `source`; all
// else is parts without one.
export function mixed(paras: Para[], mix: Mix): Part[][] {
  return paras.map((para) => {
    const runs = para.runs.map((r) => ({ ...r, text: r.text.normalize("NFC") })).filter((r) => r.text);
    const joined = runs.map((r) => r.text).join("");
    const gap = runs.flatMap((r) => Array<boolean>(r.text.length).fill(r.gap === true));
    const found = [...joined.matchAll(WORD)].map(({ 0: typed, index = 0 }) => ({ start: index, end: index + typed.length, typed: typed.replace(SOFT, "") }));
    // The word each character belongs to, or -1 for none.
    const owner = Array<number>(joined.length).fill(-1);
    found.forEach(({ start, end, typed }, i) => {
      if (/\p{L}/u.test(typed) && !gap.slice(start, end).includes(true)) owner.fill(i, start, end);
    });
    // Pieces are cut at the run and at the word's edges; the parts hold the pieces of one word, or the pieces between.
    const parts: { word: number; runs: Run[] }[] = [];
    let at = 0;
    for (const { text, ...look } of runs) {
      let from = 0;
      for (let i = 1; i <= text.length; i++) {
        if (i < text.length && owner[at + i] === owner[at + from]) continue;
        const piece = { ...look, text: text.slice(from, i) };
        const last = parts.at(-1);
        if (last?.word === owner[at + from]) last.runs.push(piece);
        else parts.push({ word: owner[at + from], runs: [piece] });
        from = i;
      }
      at += text.length;
    }
    return parts.map(({ word: w, runs: pieces }): Part => {
      if (w < 0) return { runs: pieces };
      const { typed } = found[w];
      const shown = word(typed, mix.seed, mix.first);
      const all = mix.caps ? shown.toLocaleUpperCase("de") : shown;
      // Each piece takes as many characters as it had of the typed word; the last takes the rest.
      let used = 0;
      const out = pieces.flatMap((piece, k) => {
        const n = k < pieces.length - 1 ? piece.text.replace(SOFT, "").length : all.length;
        const text = all.slice(used, used + n);
        used += text.length;
        return text ? [{ ...piece, text }] : [];
      });
      return { runs: out, source: typed };
    });
  });
}
