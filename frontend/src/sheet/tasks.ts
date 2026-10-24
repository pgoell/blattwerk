// The stored form of the task blocks. Suchsel and Zahlenmauer keep their props here; the others point at the module that makes them.

import type { HalbschriftlichProps } from "../halbschriftlich";
import type { HunderterfeldProps } from "../hunderterfeld";
import type { MagischesQuadratProps } from "../magischesquadrat";
import type { MalquadratProps } from "../malquadrat";
import type { OperatorfeldProps } from "../operatorfeld";
import type { PfeilbildProps } from "../pfeilbild";
import type { RechendreieckProps } from "../rechendreieck";
import type { RechenradProps } from "../rechenrad";
import type { RechentabelleProps } from "../rechentabelle";
import type { SelbstkontrolleProps } from "../selbstkontrolle";
import type { UhrProps } from "../uhr";
import type { ZahlenhausProps } from "../zahlenhaus";
import type { ZahlenketteProps } from "../zahlenkette";
import type { ZahlenstrahlProps } from "../zahlenstrahl";
import type { ZehnerfeldProps } from "../zehnerfeld";
import type { ZerlegungsfeldProps } from "../zerlegungsfeld";
import type { Box } from "./box";

// A word search (Suchsel): a grid of `cols` by `rows` squares, each 6 to 20, with the words hidden in it and other
// letters around them. `words` holds the words as the teacher typed them, a line of the field to an entry, as the
// sheet's Lernwörter are held. `ways` is how the words may run, each level with the ones before: across only, down
// too, the diagonals too, backwards too. `caps` shows every letter as a capital, else every letter small. With
// `umlauts` ä, ö, ü and ß stay; else they become AE, OE, UE and SS. `show` prints the hidden words under the grid,
// or only how many there are. The layout comes from `seed` alone (suchsel.ts), so every draw gives the same grid.
export type Ways = "across" | "down" | "diag" | "back";
export type SuchselProps = {
  /** The words to hide in the grid, one entry per word, as the teacher typed them. */
  words: string[];
  /** Number of squares across the grid.
   * @minimum 6
   * @maximum 20
   */
  cols: number;
  /** Number of squares down the grid.
   * @minimum 6
   * @maximum 20
   */
  rows: number;
  /** The directions the words may run: "across" only, "down" too, "diag" (diagonal) too, or "back" (backwards) too. Each level includes the ones before. */
  ways: Ways;
  /** Whether every letter shows as a capital. If not, every letter is small. */
  caps: boolean;
  /** Whether ä, ö, ü and ß stay. If not, they become AE, OE, UE and SS. */
  umlauts: boolean;
  /** Whether the hidden words print under the grid ("words") or only how many there are ("count"). */
  show: "words" | "count";
  /** The number that sets the layout of the grid. The same seed gives the same grid. */
  seed: number;
};
export type SuchselBlock = Box & {
  type: "suchsel";
  /** The word search's settings: the grid, the words and how they run. */
  props: SuchselProps;
};
// A Zahlenmauer: walls of stones in rows, each stone the sum (or with `op` "*" the product) of the two under it.
// `base` is the number of stones in the lowest row, `count` the walls of the block and `columns` how many stand side
// by side. No stone is above `max`. `given` says which stones show their number: the base row, per wall a mix that
// needs the way back, or with "free" the stones `free` flags, a flag per stone index, the same for every wall. With
// `empty` no stone shows a number. `typed` holds the numbers the teacher typed into stones: wall (from 0), stone
// index, value. A stone's index counts from the base row's left end up, a row at a time (zahlenmauer.ts). The walls
// come from `seed` alone, so every draw gives the same ones.
export type Typed = [number, number, number];
export type ZahlenmauerProps = {
  /** Number of stones in the lowest row of each wall: 3, 4 or 5. */
  base: 3 | 4 | 5;
  /** Number of walls in the block.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of walls standing side by side.
   * @minimum 1
   * @maximum 4
   */
  columns: number;
  /** The Zahlenraum: no stone lies above it. One of 10, 20, 100 or 1000. */
  max: number;
  /** How a stone is made from the two under it: "+" the sum, "*" the product. */
  op: "+" | "*";
  /** Which stones show a number: "base" the base row only, "mix" per wall a mix that needs the way back, "free" the stones marked in free. */
  given: "base" | "mix" | "free";
  /** Per stone index, true shows that stone's number when given is "free". The same for every wall. */
  free?: boolean[];
  /** Whether no stone shows a number. Default false. */
  empty: boolean;
  /** The number that sets the walls. The same seed gives the same walls. */
  seed: number;
  /** Numbers the teacher typed into stones, each as [wall, stone index, value], counted from 0. A stone's index counts from the left end of the base row, a row at a time. */
  typed?: Typed[];
};
export type ZahlenmauerBlock = Box & {
  type: "zahlenmauer";
  /** The wall block's settings: the stones, the walls and the numbers shown. */
  props: ZahlenmauerProps;
};
// A Rechendreieck: its stored shape is the contract at the top of rechendreieck.ts.
export type RechendreieckBlock = Box & {
  type: "rechendreieck";
  /** The calculation triangles (Rechendreiecke) and which of their fields are given. */
  props: RechendreieckProps;
};
// A Zahlenhaus: its stored shape is the contract at the top of zahlenhaus.ts.
export type ZahlenhausBlock = Box & {
  type: "zahlenhaus";
  /** The number houses (Zahlenhäuser): a roof number and floors of two boxes that add up to it, and which boxes are given. */
  props: ZahlenhausProps;
};
// A Zahlenkette: its stored shape is the contract at the top of zahlenkette.ts.
export type ZahlenketteBlock = Box & {
  type: "zahlenkette";
  /** The number chains (Zahlenketten): rings in a row, each step adding or taking away the same number, and which rings are given. */
  props: ZahlenketteProps;
};
// A Pfeilbild: its stored shape is the contract at the top of pfeilbild.ts.
export type PfeilbildBlock = Box & {
  type: "pfeilbild";
  /** The arrow pictures (Pfeilbilder): boxes joined by arrows, each arrow labelled with an operator, and which boxes and operators are given. */
  props: PfeilbildProps;
};
// An Operatorfeld: its stored shape is the contract at the top of operatorfeld.ts.
export type OperatorfeldBlock = Box & {
  type: "operatorfeld";
  /** The operator fields (Operatorfelder): number boxes joined by operators, in a ring or around a centre, and which numbers and operators are given. */
  props: OperatorfeldProps;
};
// A Rechenrad: its stored shape is the contract at the top of rechenrad.ts.
export type RechenradBlock = Box & {
  type: "rechenrad";
  /** The calculation wheels (Rechenräder): a centre with an operator and a number, and rings of segments where each ring's number worked with the centre gives the next ring's, and which ring or boxes are empty. */
  props: RechenradProps;
};
// A Rechentabelle: its stored shape is the contract at the top of rechentabelle.ts.
export type RechentabelleBlock = Box & {
  type: "rechentabelle";
  /** The calculation tables (Plus-, Minus-, Mal- and Geteilt-Tabellen): row values down the left, column values along the top, the operator in the corner, and each result cell the row value worked with the column value; which values and cells are given. */
  props: RechentabelleProps;
};
// A Magisches Quadrat: its stored shape is the contract at the top of magischesquadrat.ts.
export type MagischesQuadratBlock = Box & {
  type: "magischesquadrat";
  /** The magic squares (Magische Quadrate): 3×3 or 5×5 squares where every row, column and both diagonals have the same sum, the Zielzahl; which cells are given, and optionally the Zielzahl above. */
  props: MagischesQuadratProps;
};
// A Malquadrat: its stored shape is the contract at the top of malquadrat.ts.
export type MalquadratBlock = Box & {
  type: "malquadrat";
  /** The Malquadrate (Einmaleins-Rätsel): row numbers down the left, column numbers along the top, the products (or sums) inside, the sum of each row and column outside and the total in the corner; which numbers are given. */
  props: MalquadratProps;
};
// A Zerlegungsfeld: its stored shape is the contract at the top of zerlegungsfeld.ts.
export type ZerlegungsfeldBlock = Box & {
  type: "zerlegungsfeld";
  /** The Zerlegungsfelder (Zehnerübergang in zwei Schritten): each task a + b with the split of b into the part to the full ten and the rest, then the two steps; which boxes are given. */
  props: ZerlegungsfeldProps;
};
// A Halbschriftlich block: its stored shape is the contract at the top of halbschriftlich.ts.
export type HalbschriftlichBlock = Box & {
  type: "halbschriftlich";
  /** The Halbschriftlich tasks (semi-written addition and subtraction): each task a + b = r and its steps place by place, the highest place first; Karo or plain, place letters, tint, signs of the steps for the pupils. */
  props: HalbschriftlichProps;
};
// A Zehnerfeld block: its stored shape is the contract at the top of zehnerfeld.ts.
export type ZehnerfeldBlock = Box & {
  type: "zehnerfeld";
  /** The Zehnerfeld tasks: Plus and Minus on a Zehnerfeld, Zwanzigerfeld or Hunderterfeld of dots, the task line under each field; Aufgabentyp, Zahlenraum, Zehnerübergang, Trennlinien, Farben, dots set by hand. */
  props: ZehnerfeldProps;
};
// A Zahlenstrahl: its stored shape is the contract at the top of zahlenstrahl.ts.
export type ZahlenstrahlBlock = Box & {
  type: "zahlenstrahl";
  /** The number line (Zahlenstrahl): its range, ticks and the tasks on it. */
  props: ZahlenstrahlProps;
};
// A Hunderterfeld: its stored shape is the contract at the top of hunderterfeld.ts.
export type HunderterfeldBlock = Box & {
  type: "hunderterfeld";
  /** The hundred square (Hunderterfeld or Hundertertafel) and what the pupil fills in. */
  props: HunderterfeldProps;
};
// An Uhr: its stored shape is the contract at the top of uhr.ts.
export type UhrBlock = Box & {
  type: "uhr";
  /** The clock faces, their times and the task: read the time or draw the hands. */
  props: UhrProps;
};
// A Selbstkontrolle: its stored shape is the contract at the top of selbstkontrolle.ts.
export type SelbstkontrolleBlock = Box & {
  type: "selbstkontrolle";
  /** The self-check (Selbstkontrolle): a key that tells the pupil whether the answers of the linked blocks are right. */
  props: SelbstkontrolleProps;
};
