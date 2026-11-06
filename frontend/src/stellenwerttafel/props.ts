// What a Stellenwerttafel stores, and the box one task takes on the page.
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

// The implementation fills in, as the contract in ../stellenwerttafel.ts says:
// - `sane(p): StellenwerttafelProps`: a wrong value gives its default; `typed` only when it has entries.
// - `placesOf(p): { v: number; letter: string }[]`: the columns of the Zahlenraum, highest first (from zahlzerlegung's
//   `PLACES`).
// - `layout(p)`: { k, CW, HH, BH, TBW, TBH, R, SW, NB, G, TW, TH, CG, RG, across, rows, vbW, vbH }.
// - `heightFor(p, w: number): number` and `widthFor(p): number` (min(vbW, 180)).
