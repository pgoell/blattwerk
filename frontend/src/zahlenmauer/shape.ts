// The Zahlenmauer: the numbers of each wall and which stones show theirs. A pure function of the block's settings
// and its seed, so the editor, the thumbnail and the PDF draw the same walls.
import type { Typed, ZahlenmauerProps } from "../sheet";

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

// The settings as a wall can take them, whatever a stored sheet holds.
export function sane(p: ZahlenmauerProps): ZahlenmauerProps {
  const base = p.base === 4 || p.base === 5 ? p.base : 3;
  const n = stones(base);
  const free = Array.isArray(p.free) && p.free.length === n && p.free.every((f) => typeof f === "boolean") ? p.free : Array.from({ length: n }, (_, i) => i < base);
  const count = Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : 4;
  const typed = new Map<string, Typed>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [w, s, v] = t;
      if (w < 0 || w >= count || s < 0 || s >= n || v < 0 || v > 9999) continue;
      typed.delete(`${w}:${s}`);
      typed.set(`${w}:${s}`, [w, s, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    base,
    count,
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 4 ? p.columns : 2,
    max: [10, 20, 100, 1000].includes(p.max) ? p.max : 20,
    op: p.op === "*" ? "*" : "+",
    given: p.given === "mix" || p.given === "free" ? p.given : "base",
    free,
    empty: p.empty === true,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// The drawing in svg units: a stone is twice as wide as high, and a row sits half a stone right of the one under it.
// `vbW` and `vbH` are the viewBox of the whole drawing, with the half unit of room around the walls.
export function layout(p: Pick<ZahlenmauerProps, "base" | "count" | "columns">) {
  const S = 10;
  const [wallW, wallH, gap] = [p.base * 2 * S, p.base * S, 2 * S];
  const rows = Math.max(1, Math.ceil(p.count / p.columns));
  const vbW = p.columns * wallW + (p.columns - 1) * gap + 1;
  const vbH = rows * wallH + (rows - 1) * gap + 1;
  return { S, wallW, wallH, gap, rows, vbW, vbH };
}

// The default block (4 walls in 2 columns, 180 by 60 mm) draws its stones at the scale s0. A block of width w draws
// them at the same scale, and its height grows with the rows, so that they keep the size of the default block.
const DEFAULT_LAYOUT = layout({ base: 3, count: 4, columns: 2 });
const S0 = Math.min(180 / DEFAULT_LAYOUT.vbW, 60 / DEFAULT_LAYOUT.vbH);

// The height in mm of a block of width w with the props p, at which its stones draw at least at the default scale.
export function heightFor(p: ZahlenmauerProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}


// A seeded generator of numbers from 0 up to 1: mulberry32, as `rng` in suchsel.ts.
export function rng(seed: number) {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = ((t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t) | 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
