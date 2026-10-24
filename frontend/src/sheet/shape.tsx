// A shape's outline and its tail, and how far the box reaches once they are counted.

import { shuffled } from "../bank";
import { mathsHeight } from "../height";
import { type Box, dir, tall, type Kind } from "./box";
import type { MathsBlock, MathsProps } from "./maths";
import type { TextProps } from "./text";
import type { CSSProperties, SVGAttributes } from "react";

// A block's box with its bubble's tail taken in, turned about the block's own centre: the centre of the grown box on
// the page, and its half sides, which are the sides of the box before the turn.
export function reachOf(b: Box & { props?: object }) {
  const [c, s] = dir(b);
  const [up, right, down, left] = b.props ? tailReach({ w: b.w, h: b.h, props: b.props as Partial<TextProps>, flipX: b.flipX, flipY: b.flipY }) : [0, 0, 0, 0];
  const [dx, dy] = [(right - left) / 2, (down - up) / 2];
  return { x: b.x + b.w / 2 + dx * c - dy * s, y: b.y + b.h / 2 + dx * s + dy * c, hw: (b.w + left + right) / 2, hh: (b.h + up + down) / 2 };
}
// The lowest point in mm of a block's box on its page: of a turned block, its lowest corner.
export function lowest(b: Box & { props?: object }) {
  const [c, s] = dir(b);
  const r = reachOf(b);
  return r.y + Math.abs(r.hw * s) + Math.abs(r.hh * c);
}
// The right edge of a block's outline, turned or not.
export function rightmost(b: Box & { props?: object }) {
  const [c, s] = dir(b);
  const r = reachOf(b);
  return r.x + Math.abs(r.hw * c) + Math.abs(r.hh * s);
}
// Whether a maths block with these props would end lower than it does and below the paper's edge, `H` mm down.
// A sheet prints one page a page: what hangs below is cut, so the panel and the painter refuse such a change.
export function overFoot(b: MathsBlock, props: MathsProps, H: number) {
  const h = mathsHeight(props);
  if (h === mathsHeight(b.props)) return false;
  const low = lowest({ ...b, ...tall(b, h) });
  return low > H + 0.01 && low > lowest(b) + 0.01;
}
// The dashes or dots of a stroke so many mm wide. Dots need round ends to show.
export const dashes = (dash: TextProps["dash"], width: number) => (dash === "dashed" ? `${width * 4} ${width * 3}` : dash === "dotted" ? `0 ${width * 2.5}` : undefined);
// A fill as CSS: its colour, see-through by its opacity.
export const tint = (colour: string | undefined, opacity = 1) =>
  colour?.length === 7 && opacity < 1 ? `rgb(${[1, 3, 5].map((i) => parseInt(colour.slice(i, i + 2), 16)).join(" ")} / ${opacity})` : colour;
export const clear = ({ fill, opacity }: TextProps) => tint(fill, opacity);
// The classes of an element, from the names that are set.
export const classes = (...names: (string | false | 0 | undefined)[]) => names.filter(Boolean).join(" ");
// Every gap of a block is at least this many mm wide: a finite number above 0, at most 200. Else none.
export const gapWidth = (mm: unknown) => (typeof mm === "number" && Number.isFinite(mm) && mm > 0 ? Math.min(mm, 200) : 0);
// The step of a text's line numbers: a whole number from 1 to 100. A sheet may come from anywhere: else none.
export const stepOf = (n: unknown) => (typeof n === "number" && Number.isInteger(n) && n >= 1 && n <= 100 ? n : 0);
// The number of a text's first line: 1 unless it is a whole number from 1 to 9999.
export const fromOf = (n: unknown) => (typeof n === "number" && Number.isInteger(n) && n >= 1 && n <= 9999 ? n : 1);
// The width in px of a block's gaps, for the CSS of `.even .gap`.
export const gapVar = (mm: number, k: number) => (mm ? ({ "--gap": `${mm * k}px` } as CSSProperties) : {});
// The box of the solution words under a text: each word once, in the seeded order of its block. Where another order
// exists, the box never stands in reading order: the words are shuffled again until they do not.
export function Bank({ words, seed }: { words: string[]; seed: number }) {
  return <div className="bank">{shuffled(words, seed, words).map((word, i) => <span key={i}>{word}</span>)}</div>;
}

// The dashes of a box's border. The middle of the stroke is `w` by `h` mm, half the stroke's width inside the box.
export function Ring({ w, h, edge, p }: { w: number; h: number; edge: number; p: TextProps }) {
  const r = p.kind === "rounded" ? Math.max(0, Math.min(radiusOf(p, w + edge, h + edge) - edge / 2, w / 2, h / 2)) : 0;
  const [rx, ry] = p.kind === "circle" ? [w / 2, h / 2] : [r, r];
  return <Dashes way={around(edge / 2, edge / 2, edge / 2 + w, edge / 2 + h, rx, ry)} edge={edge} p={p} fill="none" />;
}
// The way round a box with round corners, as points: clockwise, and it ends where the top left corner does. The
// browser and the PDF each measure the way along a curve their own way, and the dots after one printed further
// along than the screen had them. So a quarter turn is 45 short lines: those measure the same everywhere. A
// bubble's `tail` lies in the foot.
// `after` counts the corners the way passes before the tail: 2 for the foot, 1 for the right side, 3 for the left side
// and 4 for the top.
export function around(left: number, top: number, right: number, low: number, rx: number, ry: number, tail: number[][] = [], after = 2) {
  const turn = (x: number, y: number, from: number) =>
    Array.from({ length: rx ? 46 : 1 }, (_, i) => [x + rx * Math.sin(((from + i / 45) * Math.PI) / 2), y - ry * Math.cos(((from + i / 45) * Math.PI) / 2)]);
  const corners = [turn(right - rx, top + ry, 0), turn(right - rx, low - ry, 1), turn(left + rx, low - ry, 2), turn(left + rx, top + ry, 3)];
  return [...corners.slice(0, after).flat(), ...tail, ...corners.slice(after).flat()];
}
// The dashes along a way round, which starts at its last point: a box with square corners is a `<rect>`, a triangle
// and a star start at their last corner. They stretch or shrink a little so that a whole number of them goes around:
// the last one meets the first.
export function Dashes({ way, edge, p, ...look }: { way: number[][]; edge: number; p: TextProps } & SVGAttributes<SVGElement>) {
  const length = way.reduce((sum, [x, y], i) => sum + Math.hypot(x - way.at(i - 1)![0], y - way.at(i - 1)![1]), 0);
  const each = edge * (p.dash === "dashed" ? 7 : 2.5);
  const fit = length / Math.max(1, Math.round(length / each)) / each;
  // A dash that starts right where the way does has the end of the last one before it, a hair long: a doubled dot
  // in print, and on the screen a join that fills a box's corner. So the way starts a hair inside the last gap.
  const all = { stroke: p.stroke, strokeOpacity: p.strokeOpacity, strokeWidth: edge, strokeDasharray: dashes(p.dash, edge * fit), strokeDashoffset: -edge / 100, strokeLinecap: p.dash === "dotted" ? ("round" as const) : undefined, ...look };
  if (way.length !== 4) return <path d={`M${[way.at(-1), ...way.slice(0, -1)].join(" L")} Z`} strokeLinejoin="round" {...all} />;
  // Four points are a box's own corners: no outline has four.
  const [[right], [, low], , [left, top]] = way;
  return <rect x={left} y={top} width={right - left} height={low - top} {...all} />;
}

// The outlines CSS cannot draw, in a box `w` by `h` mm and `e` mm inside it, so the stroke stays in the box. Each
// one's way round as points, which its dashes go along. The triangle has its tip at the top. The star is a
// five-point one stretched to the box. The bubble is a round box over the top three quarters, with a tail down to
// the lower left. The props `tip`, `inner` and `tail` move the tip, the inner corners and the tail (see the validators).
export const POINTS: Partial<Record<Kind, (w: number, h: number, e: number, p: Partial<TextProps>) => number[][]>> = {
  triangle: (w, h, e, p) => {
    const tip = tipOf(p);
    return [[tip === undefined ? w / 2 : clamp(tip * w, e, w - e), e], [w - e, h - e], [e, h - e]];
  },
  star: (w, h, e, p) => {
    const inner = innerOf(p) ?? 0.38;
    return Array.from({ length: 10 }, (_, i) => {
      const [r, a] = [i % 2 ? inner : 1, (i * Math.PI) / 5];
      // An upright star reaches sin 72° to each side, and cos 36° below its middle.
      return [e + (w - 2 * e) * (0.5 + (r * Math.sin(a)) / 1.902), e + ((h - 2 * e) * (1 - r * Math.cos(a))) / 1.809];
    });
  },
  bubble: (w, h, e, p) => {
    const [r, low] = [Math.min(4, w / 5, h / 4), e + 0.75 * (h - 2 * e)];
    const { edge, pts } = bubbleTail(w, h, e, r, low, tailOf(p));
    return around(e, e, w - e, low, r, r, pts, { top: 4, right: 1, foot: 2, left: 3 }[edge]);
  },
};
// Drawn solid: the same points for a polygon, or a path with true arcs.
export const OUTLINES: Partial<Record<Kind, (w: number, h: number, e: number, p: Partial<TextProps>) => string>> = {
  triangle: (w, h, e, p) => POINTS.triangle!(w, h, e, p).join(" "),
  star: (w, h, e, p) => POINTS.star!(w, h, e, p).join(" "),
  bubble: (w, h, e, p) => {
    const [r, right, low] = [Math.min(4, w / 5, h / 4), w - e, e + 0.75 * (h - 2 * e)];
    const arc = (x: number, y: number) => `A${r},${r} 0 0 1 ${x},${y}`;
    const { edge, pts } = bubbleTail(w, h, e, r, low, tailOf(p));
    // The tail's three points go in the way the body goes round: its first, its tip, its last.
    const [a, tip, b] = pts;
    const out = `L${tip[0]},${tip[1]} L${b[0]},${b[1]}`;
    return [
      `M${e + r},${e}`,
      edge === "top" ? `H${a[0]} L${tip[0]},${tip[1]} L${b[0]},${b[1]}` : "",
      `H${right - r} ${arc(right, e + r)}`,
      edge === "right" ? `V${a[1]} ${out}` : "",
      `V${low - r} ${arc(right - r, low)}`,
      edge === "foot" ? `H${a[0]} ${out}` : "",
      `H${e + r} ${arc(e, low - r)}`,
      edge === "left" ? `V${a[1]} ${out}` : "",
      `V${e + r} ${arc(e + r, e)} Z`,
    ].filter(Boolean).join(" ");
  },
};
// The bubble's tail as points: from its base on the right, to its tip, back to its base on the left. The base is 0.15
// of the width wide, on the foot of the body, between its round corners. Absent, the tail is the one it always had.
// The tail's edge of the body it sits on, and its three points in the way the body goes round. A tip above the body
// puts the tail on its top, a tip beside it (above the foot) on that side, anything else on the foot.
export function bubbleTail(w: number, h: number, e: number, r: number, low: number, tail?: [number, number]): { edge: "top" | "right" | "foot" | "left"; pts: number[][] } {
  if (!tail) return { edge: "foot", pts: [[0.4 * w, low], [0.2 * w, h - e], [0.25 * w, low]] };
  // A tip in the box keeps inside the stroke, as it always did; one outside goes where it is.
  const within = tail[0] >= 0 && tail[0] <= 1 && tail[1] >= 0 && tail[1] <= 1;
  const [tipX, tipY] = within ? [clamp(tail[0] * w, e, w - e), clamp(tail[1] * h, low, h - e)] : [tail[0] * w, tail[1] * h];
  // The base lies right of a tip at a fifth of the width, as the tail always did, and slides to its left as the tip
  // goes to four fifths: no jump on the way.
  const from = tipX + 0.05 * w - 0.25 * w * clamp((tipX / w - 0.2) / 0.6, 0, 1);
  const [lo, hi] = [e + r, w - e - r - 0.15 * w];
  const base = hi < lo ? (w - 0.15 * w) / 2 : clamp(from, lo, hi);
  if (tipY < e) return { edge: "top", pts: [[base, e], [tipX, tipY], [base + 0.15 * w, e]] };
  if (tipY < low && (tipX < e || tipX > w - e)) {
    // On a side the base is 0.15 of the height, its middle level with the tip, kept on the side's straight part.
    const [top, bottom] = [e + r, low - r - 0.15 * h];
    const y = clamp(tipY - 0.075 * h, top, bottom);
    if (tipX < e) return { edge: "left", pts: [[e, y + 0.15 * h], [tipX, tipY], [e, y]] };
    return { edge: "right", pts: [[w - e, y], [tipX, tipY], [w - e, y + 0.15 * h]] };
  }
  return { edge: "foot", pts: [[base + 0.15 * w, low], [tipX, tipY], [base, low]] };
}
// A value kept within a range.
export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
// A sheet may come from anywhere: a tail is two numbers, each kept from -1 to 2 (one box beyond each edge). Anything
// else is none, and so is a number that is no number for `tip` and `inner`, which keep their range too.
export function tailOf(p: Partial<TextProps>): [number, number] | undefined {
  const t = p.tail;
  if (!Array.isArray(t) || t.length !== 2 || !Number.isFinite(t[0]) || !Number.isFinite(t[1])) return undefined;
  return inBody(clamp(t[0], -1, 2), clamp(t[1], -1, 2));
}
// A tip in the box above the body's foot goes down to it, as before #778: a tail into the body draws none.
export const inBody = (x: number, y: number): [number, number] => [x, x >= 0 && x <= 1 && y >= 0 && y < 0.75 ? 0.75 : y];
// How far a bubble's tail reaches past its box, in mm: top, right, bottom and left. None for a tail inside the box.
export function tailReach(b: { w: number; h: number; props: Partial<TextProps>; flipX?: boolean; flipY?: boolean }): [number, number, number, number] {
  if (b.props.kind !== "bubble") return [0, 0, 0, 0];
  const [tx, ty] = tailOf(b.props) ?? [0.2, 1];
  // The stroke stands half its width round the tip: a whole width covers its join.
  const stroke = typeof b.props.strokeWidth === "number" && Number.isFinite(b.props.strokeWidth) ? b.props.strokeWidth : 0.5;
  const out = (mm: number) => (mm > 0 ? mm + stroke : 0);
  const [up, right, down, left] = [out(-ty * b.h), out((tx - 1) * b.w), out((ty - 1) * b.h), out(-tx * b.w)];
  // Flipped, the outline is drawn mirrored in the box: its reach swaps sides with it.
  return [b.flipY ? down : up, b.flipX ? left : right, b.flipY ? up : down, b.flipX ? right : left];
}
export function innerOf(p: Partial<TextProps>): number | undefined {
  const v = p.inner;
  return typeof v === "number" && Number.isFinite(v) ? clamp(v, 0.1, 0.9) : undefined;
}
export function tipOf(p: Partial<TextProps>): number | undefined {
  const v = p.tip;
  return typeof v === "number" && Number.isFinite(v) ? clamp(v, 0, 1) : undefined;
}
// The rectangle inside a shape's outline where its text lies, as the mm the box keeps from it: top, right, bottom and
// left. A circle keeps the square inscribed in it, a triangle the half that holds its base, a star the box of its inner
// points. Flipped top to bottom, the top and the bottom swap; flipped left to right, a triangle's tip moved off the
// middle swaps its sides.
export function fitOf(kind: Kind | undefined, w: number, h: number, flipY?: boolean, p?: Partial<TextProps>, flipX?: boolean): [number, number, number, number] {
  let fit: [number, number, number, number] = [0, 0, 0, 0];
  if (kind === "circle") {
    const [across, down] = [(w * (1 - Math.SQRT1_2)) / 2, (h * (1 - Math.SQRT1_2)) / 2];
    fit = [down, across, down, across];
  } else if (kind === "triangle") {
    // The tip's share of the width sets the two sides of the base's half: the middle gives w / 4 each.
    const tip = tipOf(p ?? {}) ?? 0.5;
    fit = [h / 2, ((1 - tip) * w) / 2, 0, (tip * w) / 2];
  } else if (kind === "star") {
    const inner = POINTS.star!(w, h, 0, p ?? {}).filter((_, i) => i % 2 === 1);
    const [xs, ys] = [inner.map(([x]) => x), inner.map(([, y]) => y)];
    fit = [Math.min(...ys), w - Math.max(...xs), h - Math.max(...ys), Math.min(...xs)];
  }
  if (flipX) fit = [fit[0], fit[3], fit[2], fit[1]];
  return flipY ? [fit[2], fit[1], fit[0], fit[3]] : fit;
}
// A rounded box's corner radius in mm: the share of its shorter side, 4 mm where none is set, at most half that side.
export const radiusOf = (p: Partial<TextProps>, w: number, h: number) => Math.min(p.corner === undefined ? 4 : p.corner * Math.min(w, h), Math.min(w, h) / 2);
// Where a shape's adjust handle stands, in mm from the box's top left, unflipped and unturned: the triangle's tip, the
// star's upper left inner corner, the bubble's tail tip, the rounded box's corner. Another kind has none.
export function handleOf(kind: Kind | undefined, w: number, h: number, p: Partial<TextProps>): [number, number] | undefined {
  if (kind === "triangle") return [(tipOf(p) ?? 0.5) * w, 0];
  if (kind === "rounded") return [radiusOf(p, w, h), 0];
  if (kind === "star") {
    const [x, y] = POINTS.star!(w, h, 0, p)[9]!;
    return [x, y];
  }
  if (kind === "bubble") {
    const [tx, ty] = tailOf(p) ?? [0.2, 1];
    return [tx * w, ty * h];
  }
  return undefined;
}
// The inverse of `handleOf`: the prop that puts the handle at `at` in the same frame, kept in range and rounded.
export function adjusted(kind: Kind | undefined, w: number, h: number, at: [number, number]): Partial<TextProps> {
  const [x, y] = at;
  const thou = (v: number) => Math.round(v * 1000) / 1000;
  if (kind === "triangle") return { tip: thou(clamp(x / w, 0, 1)) };
  if (kind === "rounded") return { corner: thou(clamp(x / Math.min(w, h), 0, 0.5)) };
  if (kind === "bubble") return { tail: inBody(thou(clamp(x / w, -1, 2)), thou(clamp(y / h, -1, 2))) };
  if (kind === "star") {
    // The point in POINTS.star's unit square, projected on the ray from its middle through inner corner 9.
    const [u, v] = [(x / w - 0.5) * 1.902, 1 - (y * 1.809) / h];
    const [s, c] = [Math.sin((9 * Math.PI) / 5), Math.cos((9 * Math.PI) / 5)];
    return { inner: Math.round(clamp(u * s + v * c, 0.1, 0.9) * 100) / 100 };
  }
  return {};
}
// The one element of an outline: a path when `d` starts as one.
export const Outline = ({ d, ...look }: { d: string } & SVGAttributes<SVGElement>) => (d[0] === "M" ? <path d={d} {...look} /> : <polygon points={d} {...look} />);

// The module that splits words into syllables holds the hyphenation patterns, so it loads only once a block asks
// for syllables. Until it is there such a block shows its words without bows.
