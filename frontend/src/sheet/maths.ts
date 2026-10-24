// The maths exercises a block stores: the limits, and what the generator made of them.

import type { Box } from "./box";

export type Op = keyof typeof SIGNS;
// The lowest and the highest digit a place may hold.
export type Range = [number, number];
// A written exercise on squared paper. A cell is [column, row, character, kind], a line [from column, to column,
// above row, kind]; kind 0 is printed on the sheet, 1 is the answer key's and 2 a small carry of the answer key's.
export type Grid = {
  /** Width of the squared grid, in squares. */
  cols: number;
  /** Height of the squared grid, in squares. */
  rows: number;
  /** The characters in the squares, each as [column, row, character, kind], counted from 0. Kind 0 prints on the sheet, 1 is the answer key's and 2 a small carry of the answer key's. */
  cells: [number, number, string, number][];
  /** The lines of the grid, each as [from column, to column, row it lies above, kind], counted from 0; kind as for cells. */
  lines: [number, number, number, number][];
};
// `hide` is the number a gap stands for, the result when absent. `rest` is what a division leaves. A task of three
// numbers has `op2` and `c`: it reads `a op b op2 c`, with `paren` as the brackets say, "left" for `(a op b) op2 c`
// and "right" for `a op (b op2 c)`. A task of two has none of these. `family` numbers the family the task belongs to
// (0 for the first), and a task with no family has none: its exercises stand on their own.
export type Calc = {
  /** The operation between a and b: "+" plus, "-" minus, "*" times or "/" divided by. */
  op: Op;
  /** The first number of the task. */
  a: number;
  /** The second number of the task. */
  b: number;
  /** The result of a op b, the number a gap hides when no other is named in hide. */
  result: number;
  /** What a division leaves over, 0 when it divides evenly. */
  rest: number;
  /** The number a gap stands for: "a", "b" or "c". Left out, the gap hides the result. */
  hide?: "a" | "b" | "c";
  /** The working on squared paper for this task. Left out, the task has none. */
  grid?: Grid;
  /** The second operation of a task of three numbers, between b and c. Left out for a task of two numbers. */
  op2?: Op;
  /** The third number of a task of three numbers. Left out for a task of two numbers. */
  c?: number;
  /** The brackets of a task of three numbers: "left" for (a op b) op2 c, "right" for a op (b op2 c). */
  paren?: "left" | "right";
  /** Which family of tasks this task belongs to, counted from 0. Left out, the task stands on its own. */
  family?: number;
};
// One side of a comparison: a plain number, or a term with its sign and its two numbers.
export type Side = {
  /** The number on this side. With no op it is the whole side. */
  value: number;
  /** The sign of the term on this side. Left out, the side is the plain number in value. */
  op?: Op;
  /** The first number of the term. */
  a?: number;
  /** The second number of the term. */
  b?: number;
};
// A comparison: the two sides and the sign between them, which the pupil writes in the ring.
export type Compare = {
  /** The side left of the sign. */
  left: Side;
  /** The side right of the sign. */
  right: Side;
  /** The sign the pupil writes in the ring: "<" less than, ">" more than or "=" equal. */
  sign: "<" | ">" | "=";
};
export type Exercise = Calc | Compare;
// The generator's limits, as the server takes them: `a` and `b` hold the digits each number may have, units first.
// `sides`, `close` and `equal` only matter for a comparison, and blocks saved before them have none. `c` holds the
// digits of the third number, and `numbers` is 2 or 3 numbers in a task (blocks saved before have 2). `pvs` is Punkt
// vor Strich, and `brackets` the mit Klammern that goes with it. Blocks saved before have none of these.
// `decimals` and `money` set the places after the comma (see decimalsOf), and `af`, `bf` and `cf` hold the digits
// of those places for the first, second and third number, Zehntel first. `family` makes families of two or three tasks
// (none by default), and `moves` says which number of a Nachbaraufgabe moves, "a" by default. `gaps` says what a
// gap may hide: the numbers "a", "b" and "c", or the "result". `zero` lets 0 in as a number and as a result, `one`
// lets 1 in as a factor and as a divisor, and `distinct` keeps equal numbers out. Blocks saved before have none of
// these: the gap hides any number and never the result, and 0, 1 and equal numbers are in.
export type Limits = {
  /** The operations the tasks may use: "+" plus, "-" minus, "*" times and "/" divided by. At least one. */
  ops: Op[];
  /** The Zahlenraum: no number or result lies above it. The editor offers 10, 20, 100, 1000 and 1000000.
   * @minimum 1
   * @maximum 1000000
   */
  max: number;
  /** The digits the first number may have, one range of 0 to 9 per place, units first. A place left out takes any digit. */
  a: Range[];
  /** The digits the second number may have, one range of 0 to 9 per place, units first. A place left out takes any digit. */
  b: Range[];
  /** The digits the third number may have, one range of 0 to 9 per place, units first, for tasks of three numbers. Left out, any digit. */
  c?: Range[];
  /** Whether a plus or minus task must carry (Übertrag): "none" never, "required" always, "either" both kinds. */
  carry: "none" | "required" | "either";
  /** Whether a division leaves a remainder. false, the default, gives even divisions only. */
  rest: boolean;
  /** How each task is written: "row" as a line of numbers, "gap" as a line with a gap to fill, "written" as a column calculation on squared paper, "compare" as comparisons with a ring to fill. */
  format: "row" | "gap" | "written" | "compare";
  /** How many tasks the block makes.
   * @minimum 1
   * @maximum 100
   */
  count: number;
  /** The number the tasks are drawn from. The same seed and limits give the same tasks; a new seed draws new ones. */
  seed: number;
  /** What stands on each side of a comparison: "nn" number and number, "tn" term and number, "tt" term and term. Default "tn". Only comparisons use it. */
  sides?: "nn" | "tn" | "tt";
  /** Whether the sides of a comparison lie close together, 1 or 2 units or tens apart. Default false. Only comparisons use it. */
  close?: boolean;
  /** Whether comparisons have equal sides: "none" never, "some" about one in five. Default "some". Only comparisons use it. */
  equal?: "none" | "some";
  /** How many numbers a task has: 2 or 3. Default 2. */
  numbers?: 2 | 3;
  /** Whether times and divide tasks mix with plus and minus tasks, with the times or divide worked out first (Punkt vor Strich). Default false. */
  pvs?: boolean;
  /** Whether about half of the tasks put brackets round the plus or minus part (Klammern). Default false. */
  brackets?: boolean;
  /** Places after the comma in plus and minus tasks: 0 for whole numbers, 1 for tenths or 2 for hundredths. Default 0. */
  decimals?: 0 | 1 | 2;
  /** Whether the numbers are money, always with two places after the comma. Default false. */
  money?: boolean;
  /** The digits of the first number's places after the comma, tenths first, one range of 0 to 9 per place. Left out, any digit. */
  af?: Range[];
  /** The digits of the second number's places after the comma, tenths first, one range of 0 to 9 per place. Left out, any digit. */
  bf?: Range[];
  /** The digits of the third number's places after the comma, tenths first, one range of 0 to 9 per place. Left out, any digit. */
  cf?: Range[];
  /** Families of related tasks: "none" makes single tasks, "swap" a task with its swapped numbers, "reverse" with its opposite operation, "neighbour" with its neighbouring tasks. A family has two or three tasks. Default "none". */
  family?: "none" | "swap" | "reverse" | "neighbour";
  /** Which number a neighbouring task moves: "a" the first, the default, or "b" the second. */
  moves?: "a" | "b";
  /** What a gap may hide: any of the numbers "a", "b" and "c", or the "result". Left out, a gap hides any number and never the result. */
  gaps?: ("a" | "b" | "c" | "result")[];
  /** Whether 0 may be a number and a result. Default true. */
  zero?: boolean;
  /** Whether 1 may be a factor or a divisor in times and divide tasks. Default true. */
  one?: boolean;
  /** Whether tasks with equal numbers are left out. Default false. */
  distinct?: boolean;
  /** Whether times and divide tasks stay in the small one-times table (Kleines Einmaleins): every factor, divisor and quotient from 1 to 10. Default false. */
  small?: boolean;
};
// What the generator made of the limits. With fewer exercises than asked for, `loosen` names the limits in the way.
export type Made = {
  /** The exercises the server made for the limits, in the order they stand on the sheet. */
  exercises: Exercise[];
  /** The limits in the way when fewer exercises came than asked for, by name, such as "max" or "carry". null when the count is met. */
  loosen: string[] | null;
};
// `numbering` counts the exercises of the block; `size` is the font size of a row or a gap in points.
export type MathsProps = Limits & Made & {
  /** Number of columns the exercises stand in side by side across the block.
   * @minimum 1
   * @maximum 6
   */
  columns: number;
  /** Font size of a row or a gap, in pt. The editor steps it by 2 pt and never goes below 8.
   * @minimum 8
   */
  size: number;
  /** How the exercises are numbered on the sheet, as the editor's numbering control sets it. */
  numbering?: string;
};
export type MathsBlock = Box & {
  type: "maths";
  /** The maths block's limits, layout and exercises. */
  props: MathsProps;
};
// The signs as German schools write them.
export const SIGNS = { "+": "+", "-": "−", "*": "·", "/": ":" };
