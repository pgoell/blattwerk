// German words split into the syllables a child speaks. Its own module: the bows (#60) and the syllable colours
// (#61) share it. It holds the hyphenation patterns, so the app loads it only where a sheet asks for syllables.
import createHyphenator from "hyphen";
import patterns from "hyphen/patterns/de-1996";

// The teacher's own split of a word: the word in lower case, and the places it breaks at.
export type Breaks = Record<string, number[]>;
// A stretch of a text: a syllable of a word, or what stands between words. `word` counts the words of the text.
export type Piece = { text: string; syl: boolean; word?: number };

const MARK = "­";
const hyphenate = createHyphenator(patterns, { hyphenChar: MARK, minWordLength: 1 }) as (word: string) => string;
// A word: letters, and an apostrophe between two of them. Digits and punctuation are no word.
const WORD = /[\p{L}\p{M}]+(?:['’][\p{L}\p{M}]+)*/gu;

// The name a word's own split is stored under.
export const keyOf = (word: string) => word.toLowerCase();
// The places a word breaks at, as counts of characters from its start: [1] for "Abend", [] for "Maus".
export function split(word: string): number[] {
  const out: number[] = [];
  let at = 0;
  for (const part of hyphenate(word).split(MARK).slice(0, -1)) out.push((at += part.length));
  return out;
}
// The places a word breaks at: the teacher's where the word has them, the module's own otherwise.
export const cuts = (word: string, breaks?: Breaks) => breaks?.[keyOf(word)]?.filter((at) => at > 0 && at < word.length) ?? split(word);
// The words of a text, each once, in the order they first stand in it.
export const words = (text: string) => [...new Set(text.match(WORD) ?? [])];
// A text as its pieces, in order: joined they give the text again.
export function pieces(text: string, breaks?: Breaks): Piece[] {
  const out: Piece[] = [];
  let [end, n] = [0, 0];
  for (const { 0: word, index } of text.matchAll(WORD)) {
    if (index > end) out.push({ text: text.slice(end, index), syl: false });
    const at = [0, ...cuts(word, breaks), word.length];
    for (let i = 1; i < at.length; i++) out.push({ text: word.slice(at[i - 1], at[i]), syl: true, word: n });
    end = index + word.length;
    n++;
  }
  if (end < text.length) out.push({ text: text.slice(end), syl: false });
  return out;
}
