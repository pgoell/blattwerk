// What a Zahlzerlegung stores, and the box one task takes on the page.
/** A number the teacher typed: the task's index (from 0) and the number (0 to 9999; one that does not fit the settings gives no task). */
export type ZahlzerlegungTyped = [number, number];
export type ZahlzerlegungProps = {
  /** Number of tasks on the sheet, side by side in rows of `columns`. Default 6.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of tasks per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** The Zahlenraum: 100 (Zehner and Einer, numbers 10 to 99), 1000 (Hunderter, Zehner, Einer, numbers 100 to 999) or 10000 (Tausender too, numbers 1000 to 9999). Default 1000. */
  max: number;
  /** The Aufgabentyp: "split" the number shows and the pupil writes its place values (348 = __ + __ + __; a typed number with a 0 place keeps that gap and the key writes 0, 306 = 300 + 0 + 6); "join" the place values show in order and the pupil writes the number (400 + 30 + 5 = __); "shuffled" the place values show out of order (8 + 400 + 50 = __); "places" the digits show with the place letters, a place with 0 left out, every second task out of order (3 H 7 Z 2 E = __, 8 Z 4 H = __); "gap" one place value is missing (600 + __ + 4 = 674); "zero" numbers with a 0 in a place, the pupil writes every digit (506 = __ H __ Z __ E); "bundle" one place has more than 9 (4 H 12 Z 3 E = __). Every gap has the same width; the answer key fills them in. Default "split". */
  task: "split" | "join" | "shuffled" | "places" | "gap" | "zero" | "bundle";
  /** Seed for the random numbers. The same seed always gives the same tasks. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [task index from 0, number 0 to 9999]. A typed number wins over the seed; one that does not fit the Zahlenraum and the Aufgabentyp gives no task and a hint in the editor. */
  typed?: ZahlzerlegungTyped[];
};

// A task: its number, its digits per place, its counts per place ("bundle": the bundled counts; else the digits), the
// shown places in their order (place indices, highest place 0), the index in that order of the gap of "gap" (−1
// otherwise), whether its typed number does not fit. n, digits and counts are 0 when wrong.
export type Task = { n: number; digits: number[]; counts: number[]; order: number[]; gap: number; wrong: boolean };
export type Made = { tasks: Task[]; none: boolean };
export type Item = { kind: "given" | "gap" | "sign" | "letter"; x: number; w: number; text: string };

export const DEFAULTS: Omit<ZahlzerlegungProps, "seed"> = { count: 6, columns: 2, max: 1000, task: "split" };
// The places, highest first: their value and their letter.
export const PLACES = [
  { v: 1000, letter: "T" },
  { v: 100, letter: "H" },
  { v: 10, letter: "Z" },
  { v: 1, letter: "E" },
] as const;
// The Aufgabentypen with the panel's words.
export const TYPES: [ZahlzerlegungProps["task"], string][] = [
  ["split", "Zerlegen (348 = 300 + 40 + 8)"],
  ["join", "Zusammensetzen (400 + 30 + 5)"],
  ["shuffled", "Durcheinander (8 + 400 + 50)"],
  ["places", "Stellenwerte (3 H 7 Z 2 E)"],
  ["gap", "Lücke (600 + __ + 4 = 674)"],
  ["zero", "Stellen mit 0 (506 = 5 H 0 Z 6 E)"],
  ["bundle", "Bündeln ★★★ (4 H 12 Z 3 E)"],
];

export function sane(p: ZahlzerlegungProps): ZahlzerlegungProps {
  const typed = new Map<number, ZahlzerlegungTyped>();
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
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 3 ? p.columns : DEFAULTS.columns,
    max: p.max === 100 || p.max === 10000 ? p.max : 1000,
    task: TYPES.some(([t]) => t === p.task) ? p.task : DEFAULTS.task,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(typed.size ? { typed: [...typed.values()] } : {}),
  };
}

export function placesOf(p: ZahlzerlegungProps): { v: number; letter: string }[] {
  const all = PLACES.map((pl) => ({ v: pl.v, letter: pl.letter }));
  const k = String(sane(p).max).length - 1;
  return all.slice(all.length - k);
}

export function layout(p: ZahlzerlegungProps) {
  const s = sane(p);
  const k = placesOf(s).length;
  const NW = 3 * k + 4;
  const DW = 8;
  const LT = 5;
  const SW = 5;
  const LH = 8;
  const TW =
    s.task === "split"
      ? NW + SW + k * NW + (k - 1) * SW
      : s.task === "join" || s.task === "shuffled" || s.task === "gap"
        ? (k + 1) * NW + k * SW
        : k * (DW + LT) + SW + NW;
  const CG = 10;
  const RG = 5;
  const across = Math.min(s.columns, s.count);
  const rows = Math.ceil(s.count / s.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = rows * LH + (rows - 1) * RG + 1;
  return { k, NW, DW, LT, SW, LH, TW, CG, RG, across, rows, vbW, vbH };
}

export function heightFor(p: ZahlzerlegungProps, w: number): number {
  const l = layout(p);
  return l.vbH * Math.min(w / l.vbW, 1);
}

export function widthFor(p: ZahlzerlegungProps): number {
  return Math.min(layout(p).vbW, 180);
}
