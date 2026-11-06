// What a Stellenwerttafel stores, and the box one task takes on the page.
import { PLACES } from "../zahlzerlegung";

/** A number the teacher typed: the task's index (from 0) and the number (0 to 9999; one that does not fit the settings gives an empty task). */
export type StellenwerttafelTyped = [number, number];
export type StellenwerttafelProps = {
  /** Number of tasks (tables) on the sheet, side by side in rows of `columns`. Default 4.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of tasks per row. Default 2.
   * @minimum 1
   * @maximum 4
   */
  columns: number;
  /** The Zahlenraum: 1000 (columns H Z E, numbers 1 to 999) or 10000 (columns T H Z E, numbers 1 to 9999). Default 1000. */
  max: number;
  /** The Aufgabentyp: "read" the table shows the dots (Plättchen) and the pupil writes the number; "lay" the number shows and the pupil draws its dots in the empty table; "move" the table shows the dots, the pupil moves one dot to another column and writes every number that makes (the answer key lists them all). Default "read". */
  task: "read" | "lay" | "move";
  /** Plättchen: the most dots of one task (the sum of its digits), 1 to 36, so tasks like "lege Zahlen mit höchstens 4 Plättchen" stay in range. Default 9.
   * @minimum 1
   * @maximum 36
   */
  dots: number;
  /** Leere Stellen: false every column holds at least one dot (no digit 0); true a column may be empty (306, 45). Default false. */
  zero: boolean;
  /** Seed for the random numbers. The same seed always gives the same tasks. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [task index from 0, number 0 to 9999]. A typed number wins over the seed and may have empty columns (306) whatever `zero` says; one outside the Zahlenraum, with more dots than `dots`, or with no move in "move" gives an empty task and a hint in the editor. */
  typed?: StellenwerttafelTyped[];
};

// A task: its number, its digits per column (the dots, highest column first), its moves rising ("move" only, else
// empty), whether its typed number does not fit, and whether it is an empty drawn task. n and digits are 0 when wrong
// or none.
export type Task = { n: number; digits: number[]; moves: number[]; wrong: boolean; none: boolean };
export type Made = { tasks: Task[]; none: boolean };

export const DEFAULTS: Omit<StellenwerttafelProps, "seed"> = { count: 4, columns: 2, max: 1000, task: "read", dots: 9, zero: false };
// The Aufgabentypen with the panel's words.
export const TASKS: [StellenwerttafelProps["task"], string][] = [
  ["read", "Plättchen gegeben, Zahl schreiben"],
  ["lay", "Zahl gegeben, Plättchen legen"],
  ["move", "Ein Plättchen verschieben"],
];

export function sane(p: StellenwerttafelProps): StellenwerttafelProps {
  const typed = new Map<number, StellenwerttafelTyped>();
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
    max: p.max === 10000 ? 10000 : 1000,
    task: p.task === "lay" || p.task === "move" ? p.task : "read",
    dots: Number.isInteger(p.dots) && p.dots >= 1 && p.dots <= 36 ? p.dots : DEFAULTS.dots,
    zero: typeof p.zero === "boolean" ? p.zero : DEFAULTS.zero,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(typed.size ? { typed: [...typed.values()] } : {}),
  };
}

// The columns of the Zahlenraum, highest first: H Z E, and T in front for 10000.
export function placesOf(p: StellenwerttafelProps): { v: number; letter: string }[] {
  const all = PLACES.map((pl) => ({ v: pl.v, letter: pl.letter }));
  return sane(p).max === 10000 ? all : all.slice(1);
}

// The table's sizes in units (mm at scale 1), as the contract in ../stellenwerttafel.ts gives them.
const CW = 16;
const HH = 6;
const BH = 14;
const R = 1.4;
const SW = 5;
const NB = 16;
const G = 3;
const CG = 8;
const RG = 6;

export function layout(p: StellenwerttafelProps) {
  const s = sane(p);
  const k = placesOf(s).length;
  const TBW = k * CW;
  const TBH = HH + BH;
  const move = s.task === "move";
  const TW = move ? TBW : TBW + SW + NB;
  const TH = move ? TBH + G + (k - 1) * 8 + (k - 2) * 2 : TBH;
  const across = Math.min(s.columns, s.count);
  const rows = Math.ceil(s.count / s.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = rows * TH + (rows - 1) * RG + 1;
  return { k, CW, HH, BH, TBW, TBH, R, SW, NB, G, TW, TH, CG, RG, across, rows, vbW, vbH };
}

export function heightFor(p: StellenwerttafelProps, w: number): number {
  const l = layout(p);
  return l.vbH * Math.min(w / l.vbW, 1);
}

export function widthFor(p: StellenwerttafelProps): number {
  return Math.min(layout(p).vbW, 180);
}
