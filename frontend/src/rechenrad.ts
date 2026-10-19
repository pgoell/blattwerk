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
// - Per segment the ring of its empty box for task "mixed", from 1 to `rings`, drawn whatever the task, so that a
//   change of the task keeps every wheel's numbers.
// - Typed numbers win, also outside the Zahlenraum. A segment with a typed ring number takes its chain from its innermost
//   typed ring, outward by op and inward by the inverse op. The wheel is `wrong` when a chain number is not whole, not
//   finite or below 0 (a typed centre 0 with ":", or with "*" inward), or a typed number differs from its chain. A
//   typed number shows as typed. A box whose number is made up (such a chain number, or no inner number fits a typed
//   centre) holds 0 and stays empty, also where its ring shows: no box ever shows NaN, Infinity or a false number.
//   Typed numbers of a ring the wheel does not have (after fewer rings) stay stored and play no part. A wrong wheel's key shows no answers: its empty boxes stay empty.
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

// The inverse operator: + and -, * and : swap.
const INV: Record<Op, Op> = { "+": "-", "-": "+", "*": ":", ":": "*" };

// The result of x op c.
const apply = (op: Op, x: number, c: number): number => (op === "+" ? x + c : op === "-" ? x - c : op === "*" ? x * c : x / c);

// A random pick from a non-empty list.
function pick<T>(xs: T[], next: () => number): T {
  return xs[Math.floor(next() * xs.length)];
}

// The centre numbers the draw takes: 1 up to max / (2 · (rings − 1)) for "+" and "-"; for "*" and ":" 2 to 10 with c^(rings − 1) ≤ max / 2, narrowed when some c gives the segments room.
function centreDraw(p: RechenradProps): number[] {
  if (p.op === "+" || p.op === "-") return Array.from({ length: Math.floor(p.max / (2 * (p.rings - 1))) }, (_, i) => i + 1);
  const all = Array.from({ length: 9 }, (_, i) => i + 2).filter((c) => c ** (p.rings - 1) * 2 <= p.max);
  const fit = all.filter((c) => Math.floor(p.max / c ** (p.rings - 1)) + 1 >= p.segments);
  return fit.length ? fit : all;
}

// The inner numbers x1 the draw takes with the centre number c; empty when c leaves no room (a typed c).
function innerRange(p: Pick<RechenradProps, "op" | "max" | "rings">, c: number): number[] {
  const k = c ** (p.rings - 1);
  const out: number[] = [];
  if (p.op === "+") for (let x = 0; x <= p.max - (p.rings - 1) * c; x++) out.push(x);
  else if (p.op === "-") for (let x = (p.rings - 1) * c; x <= p.max; x++) out.push(x);
  else if (c >= 1) for (let y = 0; y <= Math.floor(p.max / k); y++) out.push(p.op === "*" ? y : y * k);
  return out;
}

// One Rechenrad, the i-th: its draws in the fixed order, then its typed numbers laid over them.
function wheelOf(p: RechenradProps, i: number, next: () => number): Wheel {
  const R = p.rings;
  const S = p.segments;
  const mine = (p.typed ?? []).filter(([w]) => w === i);
  const cDrawn = pick(centreDraw(p), next);
  // The draws of the inner numbers use the generated c, so that a typed c never changes how many draws follow.
  const shadow = innerRange(p, cDrawn);
  const us: number[] = [];
  const drawn: number[] = [];
  for (let s = 0; s < S; s++) {
    let u = 0;
    let x = 0;
    for (let t = 0; t < 10; t++) {
      u = next();
      x = shadow[Math.floor(u * shadow.length)];
      if (!drawn.includes(x)) break;
    }
    us.push(u);
    drawn.push(x);
  }
  const hidden = Array.from({ length: S }, () => 1 + Math.floor(next() * R));
  const centreTyped = mine.find(([, r]) => r === 0);
  const c = centreTyped ? centreTyped[3] : cDrawn;
  const range = innerRange(p, c);
  let wrong = p.op === ":" && c === 0;
  // A box whose number is made up (not whole, below 0, or no inner number fits the centre) shows 0 and stays empty.
  const madeUp: boolean[][] = Array.from({ length: R }, () => Array.from({ length: S }, () => false));
  const rings: number[][] = Array.from({ length: R }, () => Array.from({ length: S }, () => 0));
  for (let s = 0; s < S; s++) {
    // Typed numbers of rings this wheel no longer has stay stored but play no part.
    const typed = new Map<number, number>();
    for (const [, r, seg, v] of mine) if (r >= 1 && r <= R && seg === s) typed.set(r, v);
    // vals[r] is the chain's number of ring r in this segment, NaN where none fits.
    const vals: number[] = [0];
    if (typed.size) {
      // The chain runs from the innermost typed ring: outward by op, inward by the inverse.
      const k = Math.min(...typed.keys());
      vals[k] = typed.get(k) ?? 0;
      for (let r = k + 1; r <= R; r++) vals[r] = apply(p.op, vals[r - 1], c);
      for (let r = k - 1; r >= 1; r--) vals[r] = apply(INV[p.op], vals[r + 1], c);
    } else {
      vals[1] = range.length ? range[Math.floor(us[s] * range.length)] : NaN;
      for (let r = 2; r <= R; r++) vals[r] = apply(p.op, vals[r - 1], c);
    }
    for (let r = 1; r <= R; r++) {
      const t = typed.get(r);
      const x = vals[r];
      const ok = Number.isInteger(x) && x >= 0;
      // A typed number wins and shows as typed; one its chain does not give makes the wheel wrong.
      if (t !== undefined) {
        wrong ||= t !== x;
        rings[r - 1][s] = t;
      } else {
        wrong ||= !ok;
        madeUp[r - 1][s] = !ok;
        rings[r - 1][s] = ok ? x : 0;
      }
    }
  }
  const given = Array.from({ length: R }, (_, r) =>
    Array.from({ length: S }, (_, s) => {
      if (madeUp[r][s]) return false;
      if (p.task === "inner") return r !== 0;
      if (p.task === "middle") return r !== 1;
      if (p.task === "mixed") return r !== hidden[s] - 1;
      return r !== R - 1;
    }),
  );
  return { centre: c, rings, given, wrong };
}

// The wheels of the settings. The same settings give the same wheels on every call.
const memo = new Map<string, Made>();

export function made(props: RechenradProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const next = rng(p.seed);
  const out: Made = { wheels: Array.from({ length: p.count }, (_, i) => wheelOf(p, i, next)) };
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}
