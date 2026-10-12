// Lückenwörter: the letters of a Lernwort that give way to gaps, chosen from a seed. The same seed and word hide the
// same letters everywhere, so the editor and the PDF agree.
import type { Run } from "./sheet";
import { shuffled } from "./bank";

// The modes of Lückenwörter: one letter to a word, every second letter, or all vowels.
export type Holes = "one" | "second" | "vowels";

// A word as scramble.ts finds it, and a letter with the marks that belong to it.
const WORD = /[\p{L}\p{M}\p{N}\xAD]+(?:['’-][\p{L}\p{M}\p{N}\xAD]+)*/gu;
const LETTER = /\p{L}\p{M}*/gu;
const VOWELS = "aeiouäöü";

// A hash of the word's text, so that the same word hides the same letters wherever it stands.
const hash = (text: string) => {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h;
};

// The places among a word's letters that are hidden, counted from 0. The first letter is never the one to go with
// "one": a word of two letters loses its second.
function places(word: string, letters: string[], mode: Holes, seed: number): number[] {
  const rng = (seed ^ hash(word)) >>> 0;
  if (mode === "vowels") return letters.flatMap((ch, i) => (VOWELS.includes(ch.toLowerCase()) ? [i] : []));
  if (mode === "second") return letters.flatMap((_, i) => (i % 2 === (rng & 1) ? [i] : []));
  const [at] = shuffled(Array.from({ length: letters.length - 1 }, (_, i) => i + 1), rng);
  return [at];
}

// The runs of one entry of the list: each hidden letter is a run of its own with `gap`, and the text between them
// is plain. A word of fewer than two letters stays whole. Joined, the runs give the text back in NFC.
export function holed(text: string, mode: Holes, seed: number): Run[] {
  const nfc = text.normalize("NFC");
  const cuts: [number, number][] = [];
  for (const { 0: word, index = 0 } of nfc.matchAll(WORD)) {
    const found = [...word.matchAll(LETTER)];
    if (found.length < 2) continue;
    const letters = found.map((m) => m[0]);
    for (const i of places(word, letters, mode, seed)) cuts.push([index + found[i].index, index + found[i].index + letters[i].length]);
  }
  const runs: Run[] = [];
  let at = 0;
  for (const [from, to] of cuts) {
    if (from > at) runs.push({ text: nfc.slice(at, from) });
    runs.push({ text: nfc.slice(from, to), gap: true });
    at = to;
  }
  if (at < nfc.length) runs.push({ text: nfc.slice(at) });
  return runs;
}
