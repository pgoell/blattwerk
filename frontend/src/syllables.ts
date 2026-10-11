// German words split into the syllables a child speaks. Its own module: the bows (#60) and the syllable colours
// (#61) share it. It holds the hyphenation patterns, so the app loads it only where a sheet asks for syllables.
//
// The method: the TeX patterns for the reformed spelling find the breaks a book would print ("Fens-ter",
// "Haus-tür"). They were made to leave two letters at each end of a word and they keep some vowels together,
// so a rule of this module then parts every piece that still holds two spoken vowels ("A-bend", "Ra-di-o",
// "The-a-ter"). Nothing here goes over the network.
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
// A letter with the marks typed after it ("a" and its two dots), so a text counts the same composed or not.
const LETTER = /\P{M}\p{M}*|\p{M}+/gu;

const VOWELS = new Set("aeiouyäöüéèà");
// Two vowels spoken as one: the diphthongs, the doubled vowels, and "ou" and "oi" of French words.
const ONE = new Set(["ei", "ai", "au", "äu", "eu", "ie", "aa", "ee", "oo", "ey", "ay", "oy", "ou", "oi"]);
// Consonants written with several letters, which stay together: "A-sche", "E-cke".
const UNITS = ["sch", "ch", "ck", "ph", "th", "qu"];
// Words that end in "ie" spoken as two vowels ("Fa-mi-li-e"). Most end in one ("Me-lo-die"), and only the stress
// tells them apart, which the spelling does not show.
const I_E = /(famil|lin|lil|petersil|ser|fol|kastan|komöd|stud)ie$/;
// The "en" a word ends in is a syllable of its own after "ie" and "ee": "kni-en", "Me-lo-di-en", "Se-en".
// Not in "schien".
const I_EN = /(?<!sch)[ie]en$/;
// Words no rule gets, with their breaks: two vowels that are one in a word from abroad, "een" and "ien" that
// are one syllable, and an egg ("Ei") the patterns read as the ending of "Bas-te-lei".
const EXCEPT = ["team", "jeans", "toast", "pfui", "ka-kao", "wien", "queen", "hal-lo-ween", "spie-gel-ei", "nest-ei"];
const except = new Map(EXCEPT.map((word) => [word.replaceAll("-", ""), [...word.matchAll(/-/g)].map((m, i) => m.index - i)]));

// A vowel: not the "u" of "qu", and not a "y" before a vowel ("Yo-ga").
const vowel = (c: string[], i: number) => VOWELS.has(c[i]) && !(c[i] === "u" && c[i - 1] === "q") && !(c[i] === "y" && VOWELS.has(c[i + 1]));
// Where the syllable starts that holds the vowel at `to`, when consonants from `from` on stand before it: at the
// last of them, "A-bend", "Ad-ler".
const onset = (c: string[], from: number, to: number) => to - (UNITS.find((unit) => to - unit.length >= from && c.slice(to - unit.length, to).join("") === unit)?.length ?? 1);

// The breaks of a word given as its letters, in lower case: counts of letters.
function own(c: string[]): number[] {
  const word = c.join("");
  const known = except.get(word);
  if (known) return known;
  const out: number[] = [];
  let at = 0;
  for (const part of hyphenate(word).split(MARK).slice(0, -1)) out.push((at += [...part].length));
  if (I_E.test(word)) out.push(c.length - 1);
  if (I_EN.test(word)) out.push(c.length - 2);
  // Each piece so far holds one spoken vowel: a break goes in before each further one.
  let from = 0;
  for (const to of [...out.sort((a, b) => a - b), c.length]) {
    let last = -1;
    for (let i = from; i < to; ) {
      if (!vowel(c, i)) {
        i++;
        continue;
      }
      const len = i + 1 < to && vowel(c, i + 1) && ONE.has(c[i] + c[i + 1]) ? 2 : 1;
      if (last >= 0) out.push(i === last ? i : onset(c, last, i));
      last = i += len;
    }
    from = to;
  }
  // No vowel, no syllable: such a piece joins the next one ("con-struc-tor"), the last one the one before ("geht's").
  const kept: number[] = [];
  const spoken = (start: number, end: number) => c.slice(start, end).some((_, i) => vowel(c, start + i));
  for (const to of [...new Set(out)].sort((a, b) => a - b)) if (spoken(kept.at(-1) ?? 0, to)) kept.push(to);
  if (kept.length && !spoken(kept[kept.length - 1], c.length)) kept.pop();
  return kept;
}

const cache = new Map<string, number[]>();

// The name a word's own split is stored under.
export const keyOf = (word: string) => word.toLowerCase();
// The places a word breaks at, as counts of characters from its start: [1] for "Abend", [] for "Maus".
// The same for a word in upper and in lower case. Every render asks for every word, so an answer is kept.
export function split(word: string): number[] {
  let out = cache.get(word);
  if (!out) {
    const letters = word.match(LETTER) ?? [];
    // The place of each letter in the word as it came.
    const place = [0];
    for (const letter of letters) place.push(place[place.length - 1] + letter.length);
    out = own(letters.map((letter) => [...letter.normalize("NFC").toLowerCase()][0])).map((at) => place[at]);
    cache.set(word, out);
  }
  return out;
}
// The places a word breaks at: the teacher's where the word has them, the module's own otherwise.
// A sheet may come from anywhere: only a list the sheet itself holds for the word counts (not what every object
// has, as "constructor"), and of it the whole numbers inside the word, each once, in order.
export function cuts(word: string, breaks?: Breaks): number[] {
  const own: unknown = breaks && Object.hasOwn(breaks, keyOf(word)) ? breaks[keyOf(word)] : undefined;
  if (!Array.isArray(own)) return split(word);
  return [...new Set(own.filter((at): at is number => Number.isInteger(at) && at > 0 && at < word.length))].sort((a, b) => a - b);
}
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
