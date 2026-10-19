// The Zahlenkette: chains of rings whose numbers go up, down or times by a constant step. A pure function of the block's
// settings and its seed, so the editor, the thumbnail and the PDF draw the same chains.
//
// The contract of #820, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "zahlenkette", props: ZahlenketteProps }`.
// - `count` chains (Ketten, 1 to 12, default 4) in `columns` side by side (1 to 4, default 2).
// - `rings` rings per chain (4 to 12, default 6).
// - `max`, the Zahlenraum: one of 10, 20, 100, 1000 (default 20). Any other value gives 20.
// - `op`: "+", "-" or "*" (default "+"). "*" only with max 100 or more; under that `sane` makes it "+".
// - `step`, the fixed Schrittweite: for "+" and "-" a whole number from 1 to 1000, for "*" from 2 to 10. Missing: a
//   random step per chain. Out of range: dropped (random).
// - `showStep` (Schritt anschreiben): default false. true: each arc shows its step ("+3", "−3", "·2") on the pupil
//   sheet. false: the arcs are empty, and the answer key writes the step on them in red.
// - `given`: "start" (the first two rings), "ends" (the first and the last ring), "random" (per chain
//   max(2, round(rings / 3)) rings at places from the seed), "free" (the rings flagged in `free`, the same for every
//   chain). Default "start".
// - `free`: one flag per ring; of another length, the "start" flags.
// - `typed` holds the numbers the teacher typed into rings: chain (from 0), ring (from 0), value (0 to 9999).
// - `seed` alone gives the chains, so every draw gives the same ones.
//
// The generator `made` (memo of 50, `rng` from zahlenmauer.ts), per chain:
// - "+": the step s is the fixed one, or random in 1 to max(1, floor(max / (rings - 1))). The first number a is random
//   in 0 to max(0, max - s * (rings - 1)); the numbers a, a + s, a + 2s and so on.
// - "-": the "+" chain reversed: it starts at a + s * (rings - 1) and goes down by s.
// - "*": the step s is the fixed one, or random among 2 to 10 with s^(rings - 1) <= max (none: 2). The first number a
//   is random in 1 to max(1, floor(max / s^(rings - 1))); the numbers a, a * s, a * s^2 and so on.
// - Every number stays in the Zahlenraum. `over`: true when no chain of these settings fits it (a fixed step too big,
//   or more rings than the Zahlenraum has room for, as Mal with many rings). Such a chain is not drawn, and the panel
//   says why.
// - Typed chain (manual mode): the lowest typed ring is the anchor, and every other ring is the anchor plus or minus
//   (or times, or divided by) the step once per ring away from it. `wrong` is true when another typed ring disagrees,
//   a number goes below 0 or past max, or a backward Mal division is not whole. A wrong chain shows no answers in the key.
//
// The drawing, on screen and in print alike (sheet.tsx `Zahlenkette`): `div.zahlenkette` (`.solved` in the key) holds
// one svg; each chain `g.chain[data-chain=i]` (`.wrong` when wrong), each ring `g.ring[data-ring=j]` a circle with a
// `text.given` (#222) when the ring is given, or a `text.answer` (#c0392b) in the key when it is not and the chain is
// not wrong. Between rings j and j + 1 an arc above it, `g.arc[data-arc=j]`: a path, and its label `text.step` (#222)
// with showStep, or `text.answer` in the key without showStep (and the chain not wrong).
//
// Units: a ring is D = 10 across, the gap between two rings is G = 5 (the arc runs from ring centre to ring centre),
// the arc band is A = 6 above the rings. Chains side by side are CG = 8 apart, rows RG = 6 apart.

import { rng } from "./zahlenmauer";

/** A number the teacher typed into a ring: the chain's index (from 0), the ring's index (from 0), the value (0 to 9999). */
export type KetteTyped = [number, number, number];
export type ZahlenketteProps = {
  /** Number of chains (Ketten) on the sheet, side by side in rows of `columns`. Default 4.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of chains per row. Default 2.
   * @minimum 1
   * @maximum 4
   */
  columns: number;
  /** Number of rings per chain. Default 6.
   * @minimum 4
   * @maximum 12
   */
  rings: number;
  /** The Zahlenraum: the largest number a chain may reach, one of 10, 20, 100 or 1000. Any other value gives 20. Every number stays in it: a random step is one that fits, and a chain that cannot fit (a fixed step too big, or too many rings, as with "*") is not drawn. Default 20. */
  max: number;
  /** The operation: "+" adds the step, "-" takes it away, "*" multiplies by it. "*" needs max 100 or more, under that it becomes "+". Default "+". */
  op: "+" | "-" | "*";
  /** The fixed step (Schrittweite): for "+" and "-" a whole number from 1 to 1000, for "*" from 2 to 10. Missing: a random step per chain. Out of range: dropped.
   * @minimum 1
   * @maximum 1000
   */
  step?: number;
  /** Whether each arc shows its step on the pupil sheet. On: "+3", "−3" or "·2". Off: the arcs are empty, and the answer key writes the step on them in red. Default false. */
  showStep: boolean;
  /** Which rings show their number: "start" the first two, "ends" the first and the last, "random" a few per chain from the seed, "free" the rings flagged in `free`, the same for every chain. Default "start". */
  given: "start" | "ends" | "random" | "free";
  /** With `given` "free": one flag per ring, a flagged ring shows its number. The same for every chain. Missing or of another length: the first two rings. */
  free?: boolean[];
  /** Seed for the random chains. The same seed always gives the same chains. */
  seed: number;
  /** Numbers the teacher typed into rings. Each entry is [chain index from 0, ring index from 0, value 0 to 9999]. The lowest typed ring of a chain is its anchor. A chain whose numbers do not fit its step is marked wrong. */
  typed?: KetteTyped[];
};

// A chain: its numbers by ring, whether each ring shows its number, its step, and whether it is wrong or goes past max.
export type Chain = { numbers: number[]; given: boolean[]; step: number; wrong: boolean; over: boolean };
export type Made = { chains: Chain[] };

export const DEFAULTS: Omit<ZahlenketteProps, "seed"> = { count: 4, columns: 2, rings: 6, max: 20, op: "+", showStep: false, given: "start" };

// The flags of the "start" rings: the first two.
export const startFlags = (rings: number) => Array.from({ length: rings }, (_, i) => i < 2);

// Whether x is a whole number from lo to hi.
const whole = (x: number, lo: number, hi: number) => Number.isInteger(x) && x >= lo && x <= hi;

// The settings as a chain block can take them, whatever a stored sheet holds: a wrong value gives its default, `free` of
// another length or with a value not a boolean gives the "start" rings, a fixed step out of range is dropped, a typed
// entry that is not three whole numbers in range is dropped, and of two for the same ring the last one stays.
export function sane(p: ZahlenketteProps): ZahlenketteProps {
  const count = whole(p.count, 1, 12) ? p.count : DEFAULTS.count;
  const columns = whole(p.columns, 1, 4) ? p.columns : DEFAULTS.columns;
  const rings = whole(p.rings, 4, 12) ? p.rings : DEFAULTS.rings;
  const max = [10, 20, 100, 1000].includes(p.max) ? p.max : DEFAULTS.max;
  const op = p.op === "-" || p.op === "*" ? p.op : "+";
  const realOp = op === "*" && max < 100 ? "+" : op;
  const step = p.step !== undefined && (realOp === "*" ? whole(p.step, 2, 10) : whole(p.step, 1, 1000)) ? p.step : undefined;
  const free = Array.isArray(p.free) && p.free.length === rings && p.free.every((f) => typeof f === "boolean") ? p.free : startFlags(rings);
  const typed = new Map<string, KetteTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [c, r, v] = t;
      if (c < 0 || c >= count || r < 0 || r >= rings || v < 0 || v > 9999) continue;
      typed.delete(`${c}:${r}`);
      typed.set(`${c}:${r}`, [c, r, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count,
    columns,
    rings,
    max,
    op: realOp,
    step,
    showStep: p.showStep === true,
    given: p.given === "ends" || p.given === "random" || p.given === "free" ? p.given : "start",
    free,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// The label of an arc: "+3", "−3" (U+2212) or "·2" (U+00B7).
export function stepLabel(op: ZahlenketteProps["op"], step: number): string {
  return op === "*" ? `·${step}` : op === "-" ? `−${step}` : `+${step}`;
}

// The drawing in svg units: a ring is D across, rings are G apart, the arc band A high. `vbW` and `vbH` are the viewBox
// of the whole drawing.
export function layout(p: Pick<ZahlenketteProps, "count" | "columns" | "rings">) {
  const [D, G, A, CG, RG] = [10, 5, 6, 8, 6];
  const chainW = p.rings * D + (p.rings - 1) * G;
  const chainH = A + D;
  const rows = Math.max(1, Math.ceil(p.count / p.columns));
  const vbW = p.columns * chainW + (p.columns - 1) * CG + 1;
  const vbH = rows * chainH + (rows - 1) * RG + 1;
  return { D, G, A, chainW, chainH, CG, RG, rows, vbW, vbH };
}

// The default block (4 chains of 6 rings in 2 columns) is 180 by 39 mm and draws its rings at the scale S0. A block of
// width w draws them at the same scale, and its height grows with the rows, so that they keep that size.
const DEFAULT_LAYOUT = layout(DEFAULTS);
const S0 = Math.min(180 / DEFAULT_LAYOUT.vbW, 39 / DEFAULT_LAYOUT.vbH);

// The height in mm of a block of width w with the props p, at which its rings draw at least at the default scale.
export function heightFor(p: ZahlenketteProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// The Spalten a block of width w keeps for `rings` rings: its own, or fewer when the chains side by side would be too
// wide for the rings to keep the default size (at least 1).
export function fitColumns(p: Pick<ZahlenketteProps, "count" | "columns">, rings: number, w: number): number {
  let columns = p.columns;
  while (columns > 1 && layout({ ...p, columns, rings }).vbW * S0 > w + 0.01) columns--;
  return columns;
}

// The numbers 0 to n - 1 in an order from `next` (Fisher-Yates).
function permutation(n: number, next: () => number): number[] {
  const out = Array.from({ length: n }, (_, i) => i);
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// The step and the numbers of an untyped chain, from the seed unless the step is fixed.
// A random step takes only steps whose chain fits the Zahlenraum; when none does, or a fixed step does not, the chain
// has numbers past max and `made` flags it `over`.
function generated(p: ZahlenketteProps, next: () => number): { step: number; numbers: number[] } {
  const span = p.rings - 1;
  if (p.op === "*") {
    const fits = [2, 3, 4, 5, 6, 7, 8, 9, 10].filter((s) => s ** span <= p.max);
    const step = p.step ?? (fits.length ? fits[Math.floor(next() * fits.length)] : 2);
    const a = 1 + Math.floor(next() * Math.max(1, Math.floor(p.max / step ** span)));
    return { step, numbers: Array.from({ length: p.rings }, (_, k) => a * step ** k) };
  }
  const step = p.step ?? 1 + Math.floor(next() * Math.max(1, Math.floor(p.max / span)));
  const first = Math.floor(next() * (Math.max(0, p.max - step * span) + 1));
  const up = Array.from({ length: p.rings }, (_, k) => first + step * k);
  return { step, numbers: p.op === "-" ? up.reverse() : up };
}

// The flags of the given rings of one chain.
function givenFlags(p: ZahlenketteProps, next: () => number): boolean[] {
  const rings = p.rings;
  if (p.given === "ends") return Array.from({ length: rings }, (_, i) => i === 0 || i === rings - 1);
  if (p.given === "free") return [...(p.free as boolean[])];
  if (p.given === "random") {
    const pick = new Set(permutation(rings, next).slice(0, Math.max(2, Math.round(rings / 3))));
    return Array.from({ length: rings }, (_, i) => pick.has(i));
  }
  return startFlags(rings);
}

// The chains of the settings. The same settings give the same chains on every call.
const memo = new Map<string, Made>();

export function made(props: ZahlenketteProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const next = rng(p.seed);
  const chains: Chain[] = [];
  for (let c = 0; c < p.count; c++) {
    // The draws of every chain happen whatever its typed rings, so that the chains after it stay as they were.
    const gen = generated(p, next);
    const given = givenFlags(p, next);
    const typed = new Map((p.typed ?? []).filter(([x]) => x === c).map(([, r, v]) => [r, v] as const));
    let numbers = gen.numbers;
    let wrong = false;
    if (typed.size) {
      const k = Math.min(...typed.keys());
      const anchor = typed.get(k) as number;
      const { step } = gen;
      // The number of ring i, from the anchor.
      const at = (i: number): number => {
        const d = i - k;
        if (p.op === "*") return d >= 0 ? anchor * step ** d : anchor / step ** -d;
        return p.op === "+" ? anchor + step * d : anchor - step * d;
      };
      numbers = Array.from({ length: p.rings }, (_, i) => {
        const x = at(i);
        if (typed.has(i)) {
          wrong ||= typed.get(i) !== x;
          return typed.get(i) as number;
        }
        wrong ||= x < 0 || x > p.max || !Number.isInteger(x);
        return Math.max(0, Math.trunc(x));
      });
    }
    // A chain of the generator that leaves the Zahlenraum is not drawn; a typed chain that leaves it is wrong instead,
    // so that the teacher's numbers stay in view.
    const over = !typed.size && numbers.some((n) => n > p.max);
    chains.push({ numbers, given, step: gen.step, wrong, over });
  }
  const out: Made = { chains };
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}
