// The sheet and its word list, while a page draws.

import { lettersOf } from "../selbstkontrolle";
import type { Breaks } from "../syllables";
import { type Doc, EMPTY } from "./doc";
import { createContext, useContext, useMemo } from "react";

// The Lernwörter of the sheet a block is drawn on. `Paper` sets them; the editor sets its own.
export const Words = createContext<string[]>([]);
// The whole sheet, for a Selbstkontrolle that checks the blocks of it. `Paper` and the Editor set it.
export const Whole = createContext<Doc>(EMPTY);
// The letter boxes of this block, one per task, when a "word" Selbstkontrolle of the sheet links it.
export const useLetters = (id: string) => lettersOf(useContext(Whole)).get(id);
// The mends a block draws with: the sheet's, and the block's own where it has one for the same word.
export const useBreaks = (own?: Breaks) => {
  const doc = useContext(Whole);
  return useMemo(() => ({ ...doc.breaks, ...own }), [doc.breaks, own]);
};
// A letter box in the drawing's own units: a square at (x, y), the letter in its middle in the answer key.
export function LetterBox({ x, y, side, task, letter, solved }: { x: number; y: number; side: number; task: number; letter: string; solved: boolean }) {
  return (
    <g className="letter" data-task={task}>
      <rect x={x} y={y} width={side} height={side} fill="white" stroke="#222" strokeWidth={0.4} />
      {solved && <text x={x + side / 2} y={y + side / 2} fontSize={0.6 * side} textAnchor="middle" dominantBaseline="central" fill="#c0392b">{letter}</text>}
    </g>
  );
}
