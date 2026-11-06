// What a Stellenwert-Bild stores, and the box one task takes on the page.
/** A number the teacher typed: the task's index (from 0) and the number (0 to 9999; one that does not fit the settings gives no task). */
export type StellenwertbildTyped = [number, number];
export type StellenwertbildProps = {
  /** Number of tasks (pictures) on the sheet, side by side in rows of `columns`. Default 4.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of tasks per row. Default 2.
   * @minimum 1
   * @maximum 4
   */
  columns: number;
  /** The Zahlenraum: 100 (two places, Zehner and Einer; numbers 10 to 99) or 1000 (three places, Hunderter, Zehner and Einer; numbers 100 to 999). Default 1000. */
  max: number;
  /** The Aufgabentyp: "read" the picture of Hunderterplatten, Zehnerstangen and Einerwürfel shows and the pupil writes the number; "draw" the number shows and the pupil draws it as square (Hunderter), stroke (Zehner) and dot (Einer). Default "read". */
  task: "read" | "draw";
  /** Stellenwerttafel: true puts a table of the places (H Z E) before the number box of a "read" task, for the pupil to write the digits in. Plays no part with "draw". Default true. */
  table: boolean;
  /** Stellen mit 0: false every number has no digit 0; true every number has a 0 in a place that is not the first (305, 260). Default false. */
  zero: boolean;
  /** Bündeln: true gives every picture more than 9 pieces in exactly one place (2 H 14 Z 6 E), so the pupil exchanges first; the answer key shows the number and the exchanged form (3 H 4 Z 6 E). With "draw" the task shows that form as text. Default false. */
  bundle: boolean;
  /** Seed for the random numbers. The same seed always gives the same tasks. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [task index from 0, number 0 to 9999]. A typed number wins over the seed; one that does not fit the Zahlenraum and Bündeln gives no task and a hint in the editor. */
  typed?: StellenwertbildTyped[];
};

// A task: its counts per place (the picture), its number, its digits per place (the exchanged form), whether its
// typed number does not fit, and whether it is an empty drawn task. Counts, digits and n are 0 when wrong or none.
export type Task = { counts: number[]; n: number; digits: number[]; wrong: boolean; none: boolean };
export type Made = { tasks: Task[]; none: boolean };

export const DEFAULTS: Omit<StellenwertbildProps, "seed"> = {
  count: 4,
  columns: 2,
  max: 1000,
  task: "read",
  table: true,
  zero: false,
  bundle: false,
};
// The places, highest first: their value and their letter.
export const PLACES = [
  { v: 100, letter: "H" },
  { v: 10, letter: "Z" },
  { v: 1, letter: "E" },
] as const;

// The exports the drawing, the panel and the insert use; the implementation fills them in as the contract in
// ../stellenwertbild.ts says:
// - `sane(p): StellenwertbildProps`: a wrong value gives its default; `typed` only when it has entries.
// - `placesOf(p): { v: number; letter: string }[]`: the places of the Zahlenraum, highest first.
// - `formOf(p, counts: number[]): string`: "2 H 14 Z 6 E", one "<count> <letter>" per place, joined by spaces.
// - `layout(p)`: { s, ZG, zones: { v, x, w, h }[], PW, PH, G, NB, LW, LH, KL, FW, TW, TH, CG, RG, rows, across, vbW, vbH }
//   (KL 0 unless "read" with `bundle`; FW 0 unless "draw" with `bundle`; zones x from the picture's left).
// - `heightFor(p, w: number): number` and `widthFor(p): number` (vbW).
export function sane(p: StellenwertbildProps): StellenwertbildProps {
  const typed = new Map<number, StellenwertbildTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 2 || !t.every((x) => Number.isInteger(x))) continue;
      const [i, v] = t;
      if (i < 0 || i > 11 || v < 0 || v > 9999) continue;
      typed.set(i, [i, v]);
    }
  }
  return {
    count: Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : DEFAULTS.count,
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 4 ? p.columns : DEFAULTS.columns,
    max: p.max === 100 ? 100 : 1000,
    task: p.task === "draw" ? "draw" : "read",
    table: typeof p.table === "boolean" ? p.table : DEFAULTS.table,
    zero: typeof p.zero === "boolean" ? p.zero : DEFAULTS.zero,
    bundle: typeof p.bundle === "boolean" ? p.bundle : DEFAULTS.bundle,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(typed.size ? { typed: [...typed.values()] } : {}),
  };
}

export function placesOf(p: StellenwertbildProps): { v: number; letter: string }[] {
  const all = PLACES.map((pl) => ({ v: pl.v, letter: pl.letter }));
  return sane(p).max === 100 ? all.slice(1) : all;
}

export function formOf(p: StellenwertbildProps, counts: number[]): string {
  return placesOf(p)
    .map((pl, k) => `${counts[k]} ${pl.letter}`)
    .join(" ");
}

const ZG = 4;
const CELL = 1.2;

export function layout(p: StellenwertbildProps) {
  const s = sane(p);
  const draw = s.task === "draw";
  const hundreds = s.max === 1000;
  const defs = [
    ...(hundreds ? [{ v: 100, w: 40, h: 40 }] : []),
    { v: 10, w: 24, h: s.bundle ? 26 : 12 },
    { v: 1, w: 10.8, h: s.bundle ? 8.4 : 3.6 },
  ];
  let x = 0;
  const zones = defs.map((d) => {
    const z = { v: d.v, x, w: d.w, h: d.h };
    x += d.w + ZG;
    return z;
  });
  const last = zones[zones.length - 1];
  const PW = last.x + last.w;
  const PH = Math.max(draw ? 20 : 0, ...zones.map((z) => z.h));
  const G = 3;
  const NB = 16;
  const KL = !draw && s.bundle ? 6 : 0;
  const FW = draw && s.bundle ? (hundreds ? 34 : 22) : 0;
  let LW = NB;
  let LH = 8;
  if (!draw && s.table) {
    LW = placesOf(s).length * 8 + 5 + NB;
    LH = 13;
  } else if (draw && s.bundle) {
    LW = FW + 5 + NB;
  }
  const TW = Math.max(PW, LW);
  const TH = PH + G + LH + KL;
  const CG = 8;
  const RG = 6;
  const across = Math.min(s.columns, s.count);
  const rows = Math.ceil(s.count / s.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = rows * TH + (rows - 1) * RG + 1;
  return { s: CELL, ZG, zones, PW, PH, G, NB, LW, LH, KL, FW, TW, TH, CG, RG, rows, across, vbW, vbH };
}

export function heightFor(p: StellenwertbildProps, w: number): number {
  const l = layout(p);
  return l.vbH * Math.min(w / l.vbW, 1);
}

export function widthFor(p: StellenwertbildProps): number {
  return layout(p).vbW;
}
