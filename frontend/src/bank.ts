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

// The items in a seeded order (Fisher-Yates over mulberry32): the same seed and list give the same order everywhere.
export function shuffled<T>(items: T[], seed: number): T[] {
  const out = [...items];
  let a = seed | 0;
  const next = () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = ((t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t) | 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
