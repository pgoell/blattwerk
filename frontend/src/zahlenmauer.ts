// The Zahlenmauer: the numbers of each wall and which stones show theirs. A pure function of the block's settings
// and its seed, so the editor, the thumbnail and the PDF draw the same walls.
import type { ZahlenmauerProps } from "./sheet";

// A wall: every stone's number by stone index, and whether the stone shows it. `wrong` says the numbers the teacher
// typed allow no wall.
export type Wall = { numbers: number[]; given: boolean[]; wrong: boolean };
// What gives more walls when fewer fit than asked for: a larger Zahlenraum, fewer base stones.
export type Loosen = "max" | "base";
export type Made = { walls: Wall[]; loosen: Loosen[] };

// How many stones a wall with `base` stones in its lowest row has.
export const stones = (base: number) => (base * (base + 1)) / 2;
// The index of a stone: rows count from the bottom, row 0 is the base row, and a row runs from the left.
export const at = (base: number, row: number, col: number) => row * base - (row * (row - 1)) / 2 + col;

// STUB: the generator's part replaces the three bodies below.
export function sane(p: ZahlenmauerProps): ZahlenmauerProps {
  return { ...p, base: p.base === 4 || p.base === 5 ? p.base : 3, count: p.count || 4, columns: p.columns || 2, max: p.max || 20, op: p.op === "*" ? "*" : "+", given: p.given === "mix" || p.given === "free" ? p.given : "base", empty: p.empty === true, seed: p.seed || 0 };
}

export function fixes(base: number, given: boolean[]): boolean {
  return given.slice(0, base).every(Boolean);
}

export function made(props: ZahlenmauerProps): Made {
  const p = sane(props);
  const walls = Array.from({ length: p.count }, (_, w) => {
    const numbers: number[] = Array.from({ length: p.base }, (_, i) => 1 + ((p.seed + w + i) % 3));
    for (let r = 1; r < p.base; r++) for (let c = 0; c < p.base - r; c++) numbers.push(numbers[at(p.base, r - 1, c)] + numbers[at(p.base, r - 1, c + 1)]);
    const given = p.given === "free" && p.free ? p.free : numbers.map((_, i) => i < p.base);
    return { numbers, given, wrong: false };
  });
  return { walls, loosen: [] };
}
