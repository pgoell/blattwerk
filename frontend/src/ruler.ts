// A line as a ruler (Lineal): centimetre ticks with numbers, and millimetre ticks on request.
// The ticks stand on one side of the line, the side a length label uses once it is turned to read
// upright. A line has no angle of its own: typing one keeps the centre and the length and moves the ends.

import type { Corner } from "./sheet/box";
import { far, type ShapeBlock } from "./sheet/text";

const round = (n: number) => Math.round(n * 100) / 100;

/** How far a tick reaches off the line, in mm. A centimetre is longest, a half shorter, a millimetre shortest. */
export const REACH = { cm: 4, half: 2.5, mm: 1.5 } as const;
export type TickKind = keyof typeof REACH;
/** A tick `at` mm from the line's start. `n` is the centimetre number, only on a centimetre tick. */
export type Tick = { at: number; kind: TickKind; reach: number; n?: number };
/** The number's size in pt, and the gap in mm from a tick's tip to that number's baseline. */
export const NUMBER_PT = 8;
export const NUMBER_GAP = 1;

// Centimetre ticks from 0, and with `mm` a tick at every whole millimetre that still lies on the line.
export function ticksOf(length: number, mm: boolean): Tick[] {
  if (!(length > 0) || !Number.isFinite(length)) return [];
  const last = Math.floor(length + 1e-6);
  const out: Tick[] = [];
  for (let at = 0; at <= last && at <= length + 1e-6; at++) {
    const cm = at % 10 === 0;
    if (!mm && !cm) continue;
    const kind: TickKind = cm ? "cm" : at % 5 === 0 ? "half" : "mm";
    out.push({ at, kind, reach: REACH[kind], ...(cm ? { n: at / 10 } : {}) });
  }
  return out;
}

// Degrees clockwise from pointing right, 0 up to 360, from the start corner to the opposite one.
export function lineAngle(b: ShapeBlock): number {
  const [sx, sy] = [far(b, 1, false) ? b.w : 0, far(b, 0, false) ? b.h : 0];
  const deg = (Math.atan2(b.h - 2 * sy, b.w - 2 * sx) * 180) / Math.PI;
  return ((deg % 360) + 360) % 360;
}

// What Drehung shows: a tenth of a degree, which is as close as the stored hundredths of a millimetre hold.
export function shownAngle(b: ShapeBlock): number {
  const tenth = Math.round(lineAngle(b) * 10) / 10;
  return tenth === 360 ? 0 : tenth;
}

// The line turned to `degrees`, about its centre, at the same length. The start corner follows the new ends.
export function aimed(b: ShapeBlock, degrees: number): Pick<ShapeBlock, "x" | "y" | "w" | "h" | "props"> {
  const len = Math.hypot(b.w, b.h);
  const rad = ((((degrees % 360) + 360) % 360) * Math.PI) / 180;
  const [dx, dy] = [len * Math.cos(rad), len * Math.sin(rad)];
  const [w, h] = [round(Math.abs(dx)), round(Math.abs(dy))];
  // A side that rounds away to nothing has no direction: the corner stays the level line's.
  const [sx, sy] = [w === 0 ? 1 : Math.sign(dx), h === 0 ? 1 : Math.sign(dy)];
  const from = `${sy >= 0 ? "n" : "s"}${sx >= 0 ? "w" : "e"}` as Corner;
  return {
    x: round(b.x + b.w / 2 - w / 2),
    y: round(b.y + b.h / 2 - h / 2),
    w,
    h,
    props: { ...b.props, from },
  };
}
