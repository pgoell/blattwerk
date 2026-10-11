// The gaps of a Lückentext: pure helpers over a text's paragraphs and a table's cells. A gap is a flag on a run, and a
// whole cell of a table is a gap.
import type { Para, Run } from "./sheet";

// A word: letters and digits, with an apostrophe or a hyphen between two of them.
const WORD = /[\p{L}\p{M}\p{N}]+(?:['’-][\p{L}\p{M}\p{N}]+)*/gu;

// Whether every run with text is a gap. A text with no words is none.
export const allGap = (paras: Para[]) => {
  const runs = paras.flatMap((p) => p.runs).filter((r) => r.text);
  return runs.length > 0 && runs.every((r) => r.gap);
};

// Every run with text becomes a gap, or loses its gap.
export const allGaps = (paras: Para[], on: boolean): Para[] =>
  paras.map((p) => ({ ...p, runs: p.runs.map((r) => (on && r.text ? { ...r, gap: true } : without(r))) }));

// Takes the gap flag off a run.
const without = ({ gap, ...run }: Run): Run => run;

// Cuts a run into pieces at the places where a word starts or ends. The pieces keep the run's other settings.
const cut = (r: Run, from: number, picked: boolean[]): Run[] => {
  const out: Run[] = [];
  for (let i = 0; i < r.text.length; i++) {
    const on = picked[from + i];
    const last = out.at(-1);
    if (last && !!last.gap === on) last.text += r.text[i];
    else out.push({ ...without(r), text: r.text[i], ...(on && { gap: true }) });
  }
  return out;
};

// Every n-th word of the text is a gap, counted through all paragraphs in order. Gaps made before are taken away first.
export const everyNth = (paras: Para[], n: number): Para[] => {
  let count = 0;
  return allGaps(paras, false).map((p) => {
    const text = p.runs.map((r) => r.text).join("");
    const picked = Array<boolean>(text.length).fill(false);
    for (const { 0: found, index = 0 } of text.matchAll(WORD)) if (++count % n === 0) picked.fill(true, index, index + found.length);
    let at = 0;
    return {
      ...p,
      runs: p.runs.flatMap((r) => {
        const from = at;
        at += r.text.length;
        return cut(r, from, picked);
      }),
    };
  });
};

// Every cell with text is a gap, or none is. Nothing is returned when no cell is one, so a sheet with none saves as it was.
export const allCells = (cells: string[][], on: boolean) => keepIfAny(cells.map((row) => row.map((text) => on && !!text)));

// Every n-th cell with text is a gap, counted row by row.
export const everyNthCell = (cells: string[][], n: number) => {
  let count = 0;
  return keepIfAny(cells.map((row) => row.map((text) => !!text && ++count % n === 0)));
};

// Whether every cell with text is a gap. A table with no words is none.
export const allCellGap = (cells: string[][], gaps?: boolean[][]) => {
  const held = cells.flatMap((row, r) => row.flatMap((text, c) => (text ? [!!gaps?.[r]?.[c]] : [])));
  return held.length > 0 && held.every(Boolean);
};

const keepIfAny = (gaps: boolean[][]) => (gaps.some((row) => row.some(Boolean)) ? gaps : undefined);
