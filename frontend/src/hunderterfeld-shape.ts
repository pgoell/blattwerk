// Which cells a Hundertertafel draws and which numbers it hides (#844).
// A page starts at 0 or at 1, 101, 201, … 901. A cut is the clicked cells, a rectangle, one row or one column.
// A hide rule is one row, one column, one of the two diagonals, or a picture.

import { musterCells } from "./hunderterfeld-muster";

export const STARTS = [0, 1, 101, 201, 301, 401, 501, 601, 701, 801, 901] as const;
export type Start = (typeof STARTS)[number];

const MAIN = [0, 11, 22, 33, 44, 55, 66, 77, 88, 99];
const ANTI = [9, 18, 27, 36, 45, 54, 63, 72, 81, 90];

// Row n (1 to 10 from the top) or column n (1 to 10 from the left).
export function bandCells(n: number, row: boolean): number[] {
  return Array.from({ length: 10 }, (_, k) => (row ? (n - 1) * 10 + k : n - 1 + 10 * k));
}

// The rectangle of `wide` by `tall` whose top-left cell is `anchor`. Past the edge it is clipped.
export function rectCells(anchor: number, wide: number, tall: number): number[] {
  const r0 = Math.floor(anchor / 10);
  const c0 = anchor % 10;
  const cells: number[] = [];
  for (let r = r0; r < Math.min(10, r0 + tall); r++) for (let c = c0; c < Math.min(10, c0 + wide); c++) cells.push(r * 10 + c);
  return cells;
}

// The cells a cut draws. "cells" is the stored list; the others build one.
export function cutOf(form: string, shape: number[], anchor: number, wide: number, tall: number, place: number): number[] {
  if (form === "rect") return rectCells(anchor, wide, tall);
  if (form === "row") return bandCells(place, true);
  if (form === "column") return bandCells(place, false);
  return shape;
}

// Cells a row, column, diagonal or picture hides. Null when `show` is not one of those.
export function hideOf(show: string, cover: number, muster: string): Set<number> | null {
  if (show === "row") return new Set(bandCells(cover, true));
  if (show === "column") return new Set(bandCells(cover, false));
  if (show === "diagonal") return new Set(cover === 2 ? ANTI : MAIN);
  if (show === "muster") return new Set(musterCells(muster));
  return null;
}
