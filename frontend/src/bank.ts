// The solution words of a Lückentext: the words hidden in its gaps, and the order they stand in under the text.
import type { Para } from "./sheet";

// The hidden words of a text in reading order: each stretch of gap runs in a paragraph is one word, trimmed, and an
// empty one is left out. A word hidden twice stands twice.
export function entries(paras: Para[]): string[] {
  return paras.flatMap((para) => {
    const words: string[] = [];
    let open = false;
    for (const run of para.runs) {
      if (run.gap !== true) open = false;
      else {
        if (!open) words.push("");
        words[words.length - 1] += run.text;
        open = true;
      }
    }
    return words.map((word) => word.trim()).filter(Boolean);
  });
}

// The hidden words of a table: the text of each gap cell, trimmed, row by row. An empty cell is left out.
export function cellEntries(cells: string[][], gaps: boolean[][] | undefined): string[] {
  return cells.flatMap((row, r) => row.flatMap((text, c) => (gaps?.[r]?.[c] === true && text.trim() ? [text.trim()] : [])));
}

const same = <T>(a: T[], b: T[]) => a.length === b.length && a.every((x, i) => x === b[i]);

// The items in a seeded order (Fisher-Yates over mulberry32): the same seed and list give the same order everywhere.
// With `not`, the order is never that one (when the items differ): a shuffle that gives it back looks like no shuffle.
export function shuffled<T>(items: T[], seed: number, not?: T[]): T[] {
  let a = seed | 0;
  const next = () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = ((t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t) | 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  // One pass over the list, in place, on from wherever the generator stands.
  const pass = (out: T[]) => {
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(next() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  };
  let out = pass([...items]);
  if (!not || items.every((item) => item === items[0]) || !same(out, not)) return out;
  for (let n = 0; n < 64 && same(out, not); n++) out = pass(out);
  // Rotating by one place changes any list that has two different items.
  return same(out, not) ? [...out.slice(1), out[0]] : out;
}

// What a block shows under a seed, and the seed it has now.
export type Shown = { seed?: number; show: (seed: number) => string };

// Whether a seed shows any of the held items in another way than its own seed does.
export const moves = (held: Shown[], seed: number) => held.some((h) => h.seed === undefined || h.show(seed) !== h.show(h.seed));

// A seed for a new draw. It tries up to 40 seeds, and takes the first under which every held item changes (an item with
// no seed always counts as changed). If none changes all, it takes the seed that changes the most.
export function draw(held: Shown[] = [], random: () => number = Math.random): number {
  const taken = new Set(held.map((h) => h.seed));
  const fresh = () => {
    let seed: number;
    do {
      seed = 1 + Math.floor(random() * 2147483647);
    } while (taken.has(seed));
    return seed;
  };
  const changed = (seed: number) => held.filter((h) => h.seed === undefined || h.show(seed) !== h.show(h.seed)).length;
  let best = 0;
  let most = -1;
  for (let i = 0; i < 40; i++) {
    const seed = fresh();
    const n = changed(seed);
    if (n === held.length) return seed;
    if (n > most) [best, most] = [seed, n];
  }
  return best;
}
