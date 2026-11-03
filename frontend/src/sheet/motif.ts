// A shape's Muster and the Lineatur that can fill it instead. Both are one tile, in mm, repeated across the box.
// The editor and the PDF draw the same tile.

export const MOTIFS = ["stripes", "dots", "checks", "waves"] as const;
export type Motif = (typeof MOTIFS)[number];
export const PAPERS = ["mm", "k5", "k7", "k10"] as const;
export type Paper = (typeof PAPERS)[number];
// The yellow a new colour fill takes, the same one the sheets already use, and the blue-grey of a new Lineatur.
export const COLOUR = "#ffd43b";
export const RULE = "#8aa4be";

export type Pen = { x1: number; y1: number; x2: number; y2: number; width: number };
export type Blob = { x: number; y: number; w: number; h: number } | { cx: number; cy: number; r: number } | { d: string; width: number };
export type Tile = { size: number; ground: boolean; pens: Pen[]; blobs: Blob[] };
export type FillMode = "none" | "color" | "pattern" | "ruling";

const known = <T extends string>(all: readonly T[], v: unknown): v is T => all.includes(v as T);

export function paperOf(p: { paper?: unknown }): Paper | undefined {
  return known(PAPERS, p.paper) ? p.paper : undefined;
}
// A Lineatur wins: a sheet that names both draws graph paper, not the Muster under it.
export function motifOf(p: { motif?: unknown; paper?: unknown }): Motif | undefined {
  if (paperOf(p)) return undefined;
  return known(MOTIFS, p.motif) ? p.motif : undefined;
}
export function fillMode(p: { fill?: unknown; motif?: unknown; paper?: unknown }): FillMode {
  if (paperOf(p)) return "ruling";
  if (motifOf(p)) return "pattern";
  return p.fill && p.fill !== "none" ? "color" : "none";
}
// One repeat in mm. Anything that is not a number is the 5 mm a new Muster has. A sheet may name one past the slider.
export function scaleOf(v: unknown): number {
  if (typeof v !== "number" || !Number.isFinite(v)) return 5;
  return Math.min(20, Math.max(2, v));
}
// Schwarz-Weiß is black. Otherwise the fill, when it is a colour; a missing one is the text's own black.
export function inkOf(fill: unknown, mono: boolean): string {
  if (mono) return "#000000";
  return typeof fill === "string" && /^#[0-9a-fA-F]{6}$/.test(fill) ? fill : "#222222";
}

export function motifTile(motif: Motif, scale: number): Tile {
  if (motif === "stripes") return { size: scale, ground: false, pens: [], blobs: [{ x: 0, y: 0, w: scale, h: scale / 2 }] };
  if (motif === "dots") return { size: scale, ground: false, pens: [], blobs: [{ cx: scale / 2, cy: scale / 2, r: scale / 6 }] };
  if (motif === "checks") {
    const half = scale / 2;
    return { size: scale, ground: false, pens: [], blobs: [{ x: 0, y: 0, w: half, h: half }, { x: half, y: half, w: half, h: half }] };
  }
  const [y, a] = [scale / 2, scale / 5];
  return { size: scale, ground: false, pens: [], blobs: [{ d: `M0 ${y} Q${scale / 4} ${y - a} ${scale / 2} ${y} T${scale} ${y}`, width: Math.max(0.25, scale / 12) }] };
}

// Lines of one weight, across and down. A line on the tile's edge would lose half its stroke to the next tile, so
// that one sits in by half its width. The others stand on their millimetre.
function grid(size: number, at: number[], widthAt: (n: number) => number): Pen[] {
  return at.flatMap((n) => {
    const width = widthAt(n);
    const pos = n === 0 ? width / 2 : n;
    return [{ x1: 0, y1: pos, x2: size, y2: pos, width }, { x1: pos, y1: 0, x2: pos, y2: size, width }];
  });
}

export function paperTile(paper: Paper): Tile {
  if (paper === "mm") {
    const at = Array.from({ length: 10 }, (_, i) => i);
    return { size: 10, ground: true, pens: grid(10, at, (n) => (n === 0 ? 0.3 : n === 5 ? 0.18 : 0.1)), blobs: [] };
  }
  const size = paper === "k5" ? 5 : paper === "k7" ? 7 : 10;
  return { size, ground: true, pens: grid(size, [0], () => 0.2), blobs: [] };
}

export function tileOf(p: { motif?: unknown; paper?: unknown; scale?: unknown }): Tile | undefined {
  const paper = paperOf(p);
  if (paper) return paperTile(paper);
  const motif = motifOf(p);
  return motif ? motifTile(motif, scaleOf(p.scale)) : undefined;
}
