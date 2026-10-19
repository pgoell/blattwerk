// The Rechenrad generator: a wheel with a centre and rings of segments. The centre holds an operator and a number such
// as "+7"; each ring's number, worked with the centre, gives the number of the next ring out in the same segment. A pure
// function of the block's settings and its seed, so that the editor, the thumbnail and the PDF draw the same wheels.
//
// The contract of #823, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "rechenrad", props: RechenradProps }`.
// - `count` Rechenräder (1 to 6, default 2) in `columns` side by side (1 to 3, default 2).
// - `rings`: the number rings, 2 (default) or 3. Ring 1 is the inner one, ring `rings` the outer one.
// - `segments` per wheel: 4 to 12 (default 8).
// - `max`, the Zahlenraum: one of 10, 20, 100, 1000 (default 20). Any other value gives 20. No number the generator
//   draws is above it.
// - `op`, the Rechenart: "+" (default), "-", "*" (Mal) or ":" (Geteilt). "*" and ":" need max 20 or more, else "+".
// - `task`, the Aufgabentyp: "outer" (default: the outer ring empty), "inner" (the inner ring empty), "middle" (the
//   middle ring empty, only with 3 rings, else "outer") or "mixed" (one empty box per segment, in a ring drawn per
//   segment). The centre always shows.
// - `typed`: numbers the teacher typed, each entry [wheel from 0, ring 0 to 3 (0 is the centre's number), segment 0 to
//   11 (0 for the centre), value 0 to 9999].
// - `seed` alone gives the wheels.
//
// A segment's chain: x1 in ring 1, x(r+1) = xr op c, with c the centre's number. The centre shows as opLabel, e.g.
// "+7", "−7" (U+2212), "·7" (U+00B7) or ":7". Segments count clockwise from the top: segment 0 begins at 12 o'clock.
//
// The generator `made` (memo of 50, `rng` from zahlenmauer.ts), per wheel, every draw in this order whatever is typed,
// so that the wheels after a typed one stay as they were:
// - c: "+" and "-" a whole number from 1 to floor(max / (2 · (rings − 1))); "*" and ":" from 2 to 10 with
//   c^(rings − 1) ≤ max / 2, and of those only the ones with floor(max / c^(rings − 1)) + 1 ≥ segments when any has
//   that (so that the segments can differ). A typed centre number wins over the drawn one (the draw still happens).
// - Per segment the inner number x1: "+" from 0 to max − (rings − 1)·c; "-" from (rings − 1)·c to max; "*" from 0 to
//   floor(max / c^(rings − 1)); ":" x1 = y · c^(rings − 1) with y from 0 to floor(max / c^(rings − 1)). Up to 10 draws
//   for a number that no other segment of the wheel has. With a typed c these ranges may be empty: then the segment
//   takes 0 and, unless the segment is typed, the wheel is `wrong`.
// - With task "mixed", per segment the ring of its empty box, from 1 to `rings`.
// - Typed numbers win, also outside the Zahlenraum. A segment with a typed ring number takes its chain from its innermost
//   typed ring, outward by op and inward by the inverse op. The wheel is `wrong` when a chain number is not whole, not
//   finite or below 0 (a typed centre 0 with ":", or with "*" inward), or a typed number differs from its chain. Then
//   no box ever shows NaN or Infinity. A wrong wheel's key shows no answers: its empty boxes stay empty.
//
// The drawing (sheet.tsx `Rechenrad`, on screen, print and in the key alike): `div.rechenrad` holds one svg. Each
// wheel `g.wheel[data-wheel=i]` (class `wrong`) has `g.centre` with a circle and `text.given` (the op label), and each
// box `g.box[data-ring=r][data-segment=s]` a ring sector path and, when it shows, a text. A shown number has class
// `given` in #222; in the key a missing one has class `answer` in #c0392b. Every answer of a Rechenrad is the only right
// one (the centre always shows), so the key has no note "Auch andere Lösungen sind richtig."
//
// Units: the centre circle has radius C0 = 9, each ring is W = 12 wide, so the wheel's radius is R = C0 + rings · W and
// a wheel is F = 2R square. Wheels side by side are CG = 8 apart, rows RG = 6 apart.

import { rng } from "./zahlenmauer";

/** A number the teacher typed: the wheel's index (from 0), the ring (0 is the centre's number, 1 the inner ring, up to 3), the segment (from 0, clockwise from the top; 0 for the centre), the value (0 to 9999). */
export type RechenradTyped = [number, number, number, number];
export type RechenradProps = {
  /** Number of Rechenräder on the sheet, side by side in rows of `columns`. Default 2.
   * @minimum 1
   * @maximum 6
   */
  count: number;
  /** Number of Rechenräder per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** The number rings around the centre: 2 (an inner and an outer ring) or 3 (inner, middle, outer). Each ring's number, worked with the centre, gives the next ring's. Default 2.
   * @minimum 2
   * @maximum 3
   */
  rings: number;
  /** Segments per Rechenrad, the spokes of the wheel. Default 8.
   * @minimum 4
   * @maximum 12
   */
  segments: number;
  /** The Zahlenraum: the largest number the generator puts in a ring, one of 10, 20, 100 or 1000. Any other value gives 20. Default 20. */
  max: number;
  /** The Rechenart of the centre: "+" (Plus), "-" (Minus), "*" (Mal) or ":" (Geteilt). "*" and ":" need max 20 or more, else "+". Default "+". */
  op: "+" | "-" | "*" | ":";
  /** The Aufgabentyp: "outer" the outer ring is empty, "inner" the inner ring is empty (the pupils work back), "middle" the middle ring is empty (only with 3 rings, else "outer"), "mixed" one empty box per segment in a ring drawn at random. The centre always shows. Default "outer". */
  task: "outer" | "inner" | "middle" | "mixed";
  /** Seed for the random wheels. The same seed always gives the same wheels. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [wheel index from 0, ring from 0 (0 is the centre's number, 1 the inner ring), segment from 0 clockwise from the top (0 for the centre), value 0 to 9999]. Typed numbers win over the drawn ones; a wheel whose numbers do not fit its centre is marked wrong and its key shows no answers. */
  typed?: RechenradTyped[];
};

export type Op = RechenradProps["op"];
// A wheel: its centre number, its rings' numbers (ring[r - 1][s] for ring r, segment s), which boxes show, and whether
// its typed numbers do not fit.
export type Wheel = { centre: number; rings: number[][]; given: boolean[][]; wrong: boolean };
export type Made = { wheels: Wheel[] };

export const DEFAULTS: Omit<RechenradProps, "seed"> = { count: 2, columns: 2, rings: 2, segments: 8, max: 20, op: "+", task: "outer" };

const OPS: Op[] = ["+", "-", "*", ":"];

// Whether x is a whole number from lo to hi.
const whole = (x: number, lo: number, hi: number) => Number.isInteger(x) && x >= lo && x <= hi;

// The settings as a rechenrad block can take them, whatever a stored sheet holds: a wrong value gives its default, a
// typed entry that is not four whole numbers in range is dropped, and of two for the same box the last one stays.
export function sane(p: RechenradProps): RechenradProps {
  const count = whole(p.count, 1, 6) ? p.count : DEFAULTS.count;
  const columns = whole(p.columns, 1, 3) ? p.columns : DEFAULTS.columns;
  const rings = p.rings === 3 ? 3 : 2;
  const segments = whole(p.segments, 4, 12) ? p.segments : DEFAULTS.segments;
  const max = [10, 20, 100, 1000].includes(p.max) ? p.max : DEFAULTS.max;
  const op = OPS.includes(p.op) && (p.op === "+" || p.op === "-" || max >= 20) ? p.op : "+";
  const task = p.task === "inner" || p.task === "mixed" || (p.task === "middle" && rings === 3) ? p.task : "outer";
  const typed = new Map<string, RechenradTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 4 || !t.every((x) => Number.isInteger(x))) continue;
      const [c, r, s, v] = t;
      if (c < 0 || c >= count || r < 0 || r > 3 || s < 0 || s > 11 || (r === 0 && s !== 0) || v < 0 || v > 9999) continue;
      typed.delete(`${c}:${r}:${s}`);
      typed.set(`${c}:${r}:${s}`, [c, r, s, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count,
    columns,
    rings,
    segments,
    max,
    op,
    task,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// The label of the centre: "+7", "−7" (U+2212), "·7" (U+00B7) or ":7".
const SIGN: Record<Op, string> = { "+": "+", "-": "−", "*": "·", ":": ":" };
export function opLabel(op: Op, c: number): string {
  return `${SIGN[op]}${c}`;
}

// The drawing in svg units. `vbW` and `vbH` are the viewBox.
export function layout(p: Pick<RechenradProps, "count" | "columns" | "rings">) {
  const [C0, W, CG, RG] = [9, 12, 8, 6];
  const R = C0 + p.rings * W;
  const F = 2 * R;
  const rows = Math.ceil(p.count / p.columns);
  const vbW = p.columns * F + (p.columns - 1) * CG + 1;
  const vbH = rows * F + (rows - 1) * RG + 1;
  return { C0, W, R, F, CG, RG, rows, vbW, vbH };
}

// The angle in radians where segment s of S begins, clockwise from 12 o'clock (in svg, y down).
export function edgeAngle(s: number, S: number): number {
  return -Math.PI / 2 + (2 * Math.PI * s) / S;
}

// The middle of the box in ring r (from 1), segment s of S, of a wheel whose middle is (cx, cy).
export function cellAt(r: number, s: number, S: number, cx: number, cy: number, C0: number, W: number): [number, number] {
  const a = edgeAngle(s + 0.5, S);
  const rad = C0 + (r - 0.5) * W;
  return [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
}

// The default block is drawn at the scale S0 at 180 mm wide. A block of width w draws its wheels at that scale, and its
// height grows with the rows, so that they keep that size.
const S0 = 180 / layout(DEFAULTS).vbW;

// The height in mm of a block of width w with the props p, at which its wheels draw at least at the default scale.
export function heightFor(p: RechenradProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// The wheels of the settings. The same settings give the same wheels on every call. Placeholder until the generator
// lands: every number 0, nothing wrong.
export function made(props: RechenradProps): Made {
  const p = sane(props);
  rng(p.seed);
  const wheels: Wheel[] = Array.from({ length: p.count }, () => ({
    centre: 1,
    rings: Array.from({ length: p.rings }, () => Array.from({ length: p.segments }, () => 0)),
    given: Array.from({ length: p.rings }, (_, r) => Array.from({ length: p.segments }, () => r < p.rings - 1)),
    wrong: false,
  }));
  return { wheels };
}
