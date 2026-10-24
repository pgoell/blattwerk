// A block's box on the page: where it sits, how big it is, and how a turn or a flip moves it.

import type { CSSProperties } from "react";

// One page's blocks, as the sheet document stores them: mm from the page's top-left corner. `mark` is the numbering
// before a block: a counting one such as "1.", "a)" or "(1)", or a symbol's code. `angle` turns the box about its
// centre, in degrees clockwise from 0 up to 360. `flipX` and `flipY` mirror a picture or a symbol in its box.
// `keep` is set when the block keeps its width over its height, as PowerPoint's 'Lock aspect ratio'. Absent means off.
export type Box = {
  /** Unique id of the block on its sheet. */
  id: string;
  /** Distance in mm from the left edge of the page to the left edge of the block, before any turn. The page is 210 mm wide upright. */
  x: number;
  /** Distance in mm from the top edge of the page to the top edge of the block, before any turn. The page is 297 mm tall upright. */
  y: number;
  /** Width of the block in mm, before any turn. */
  w: number;
  /** Height of the block in mm, before any turn. */
  h: number;
  /** Stacking order on the page: a block with a higher z lies over one with a lower z. */
  z: number;
  /** True when the block is locked, so the editor does not move, resize or turn it. Absent means not locked. */
  locked: boolean;
  /** Numbering printed before the block on paper, such as "1.", "a)" or "(1)", or a symbol's code. Absent means none. */
  mark?: string;
  /** The ids of the groups the block belongs to, the outermost group first. Absent when the block is in no group. */
  group?: string[];
  /** Turn of the block about its centre, in degrees clockwise. 0 is upright, 90 a quarter turn. Absent means 0.
   * @minimum 0
   * @maximum 360
   */
  angle?: number;
  /** True mirrors the block from left to right inside its box, so a picture or a symbol faces the other way. Absent means not mirrored. */
  flipX?: boolean;
  /** True mirrors the block from top to bottom inside its box. Absent means not mirrored. */
  flipY?: boolean;
  /** True keeps the width in proportion to the height when the block is resized, as PowerPoint's Lock aspect ratio does. Absent means off. */
  keep?: boolean;
};
// "double" is an arrow with a head at both ends.
export type Kind = "rect" | "rounded" | "circle" | "triangle" | "star" | "bubble" | "line" | "arrow" | "double";
export type Corner = "nw" | "ne" | "sw" | "se";
export type Align = "left" | "center" | "right";
export type Valign = "top" | "middle" | "bottom";
export const MARGIN = 15;
// The pixels per mm of the PDF. Every page is laid out at this scale and drawn at another by a transform, so a
// line of text breaks at the same word in the PDF, at every zoom and in a thumbnail.
export const K = 96 / 25.4;
// A turned block's box turns as a whole. A flip mirrors only what the box shows: Moveable cannot take hold of a
// mirrored box, and a numbering must stay readable.
export const turned = (b: Box): CSSProperties | undefined => (b.angle ? { transform: `rotate(${b.angle}deg)` } : undefined);
// The cosine and sine of a block's angle.
export const dir = (b: { angle?: number }) => [Math.cos(((b.angle ?? 0) * Math.PI) / 180), Math.sin(((b.angle ?? 0) * Math.PI) / 180)];
// A new height for a block: the edge it starts at stays, as in PowerPoint. A turned block turns about its centre,
// and a new height moves that: the centre goes down the block's own axis, so that edge stays in its place on the
// page and the far edge moves alone.
export function tall(b: Box, h: number): Partial<Box> {
  if (!b.angle) return { h };
  const [c, s] = dir(b);
  const half = (h - b.h) / 2;
  return { h, x: Math.round((b.x - s * half) * 100) / 100, y: Math.round((b.y + (c - 1) * half) * 100) / 100 };
}
// A new width for a block: `at` is the share of the width that stays in place (0 the left edge, 0.5 the middle, 1 the right).
export function fitWidth(b: Box, w: number, at: number): Partial<Box> {
  return { w, x: Math.round((b.x + (b.w - w) * at) * 100) / 100 };
}
export const flipped = (b: Box): CSSProperties | undefined => (b.flipX || b.flipY ? { transform: `scale(${b.flipX ? -1 : 1}, ${b.flipY ? -1 : 1})` } : undefined);
