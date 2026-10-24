// The Rechentabelle generator: Plus-, Minus-, Mal- and Geteilt-Tabellen. Each result cell is its row's value worked with
// its column's value, and the corner shows the operator. A pure function of the block's settings and its seed, so that
// the editor, the thumbnail and the PDF draw the same tables.
//
// The contract of #824, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "rechentabelle", props: RechentabelleProps }`.
// - `count` Rechentabellen (1 to 4, default 2) in `columns` side by side (1 to 3, default 2).
// - `rows` row values and `cols` column values per table, each 2 to 10 (default 4).
// - `op`, the Rechenart: "+" (default), "-", "*" (Mal) or ":" (Geteilt). Cell (i, j) is row i op column j.
// - Plus and Minus: `max`, the Zahlenraum, one of 10, 20, 100, 1000 (default 20; any other value gives 20), and
//   `carry`, the Übertrag per place, [Zehnerübergang, Hunderterübergang] (each a `CarryRule`): "none" no cell carries
//   into that place, "required" every cell does, "either" (default) no rule. The Hunderterübergang counts from max
//   1000 and is "either" below (a cell of 100 at most carries into the Hunderter only as 100 itself). "none" at the
//   top place that counts holds for every place above it too: bis 100 "Ohne Zehnerübergang" has no 20 + 80 = 100,
//   bis 1000 "Ohne Hunderterübergang" no 100 + 900 = 1000. What a cell carries is `carryList`,
//   as maths.py `carries`: Plus a digit sum above 9, Minus a digit of the row value below the column value's digit
//   (with the borrow); a place the numbers do not reach carries 0. Plus: every value and every cell from 1 to max.
//   Minus: every value from 1 to max, every cell 0 or more.
// - Mal and Geteilt: `reihen`, the Einmaleins-Reihen, a list of distinct numbers 1 to 10 (default [2, 4, 5, 10]; an
//   empty or wrong list gives the default). The column values are the Reihen: with `order` "related" (default) in the
//   order of FAMILY (related Reihen side by side: 1, 2, 4, 8, 3, 6, 9, 5, 10, 7), with "random" in a drawn order. The
//   row values are the Erstfaktoren of `first`: "all" (default) 1 to 10, "kings" the Königsaufgaben 1, 2, 5, 10,
//   "near" the Königsaufgaben ± 1: 3, 4, 6, 9; in a drawn order. A list shorter than the table's values starts again
//   (in a new drawn order for the rows), so values repeat only then.
//   Mal: cell = row · column. Geteilt: the row value is a dividend q · d, with q the row's Erstfaktor and d a column value
//   drawn per row; cell = row : column when that is whole, else the cell has no whole answer and is struck through
//   (on the sheet and in the key alike).
// - `hideRows` (0 to rows − 1) row values and `hideCols` (0 to cols − 1) column values are hidden, drawn at random
//   (default 0). Per hidden row value, one result cell of that row in a shown column is given, and per hidden column
//   value one in a shown row, so that the pupils can work the hidden value back. In Geteilt only a cell with a whole
//   answer is given; a hidden value with no such cell shows after all.
// - `tint`: "none" (default), "blue", "green", "yellow", "red" or "purple": the value cells take TINT[tint][0], the
//   corner the darker TINT[tint][1]; the result cells stay white.
// - `typed`: numbers the teacher typed, each entry [table from 0, row 0 to 10, column 0 to 10, value 0 to 9999]. Row 0
//   column j is column value j (from 1), row i column 0 row value i (from 1), row i column j the result cell (i, j);
//   [t, 0, 0, v] is not an entry.
// - `seed` alone gives the tables.
//
// The generator `made` (memo of 50, `rng` from zahlenmauer.ts), per table, every draw in this order whatever is typed,
// so that the tables after a typed one stay as they were:
// - The values. Plus and Minus: up to 200 tries, each draws the column values one after the other (distinct), then the
//   row values (distinct, each up to 50 draws for one that fits every column value with the rules). When no try fits,
//   the carry rule still holds: an exact depth-first search over the columns in a drawn order (`exactValues`) finds
//   distinct values if such a set exists; else 200 tries where values may repeat, then the first column value and
//   row value that fit, repeated. `loose` "distinct" when both carry rules are "either" (only the Zahlenraum is too
//   small), else "carry" (values repeat under the rule). Mal and
//   Geteilt: the column order (drawn also with "related", so that the order setting keeps the draws), the row order,
//   and for Geteilt one d per row (up to 10 draws for a dividend no other row has).
// - The hidden values: a drawn order of the rows and one of the columns (the first hideRows and hideCols are hidden),
//   then one draw per row and one per column for the given cell of a hidden value.
// - Typed numbers win, also outside the Zahlenraum and against the carry rule; a typed value shows unless hidden, a
//   typed cell shows on the sheet. The table is `wrong` when a cell is below 0 (Minus), a column value is 0 (Geteilt),
//   a row or column value is 0 with Mal or Geteilt (0 times anything is 0, so a hidden value would have more than one
//   answer), or a typed cell differs from its row and column (or is typed where Geteilt has no whole answer). Such a
//   cell, below
//   0 or with a divisor 0, is `madeUp`: it holds 0 and stays empty, also in the key: no cell ever shows NaN, Infinity
//   or a false number. A wrong table's key shows no answers. Typed numbers of rows or columns the table does not have
//   (after fewer rows or columns) stay stored and play no part.
//
// The drawing (sheet.tsx `Rechentabelle`, on screen, print and in the key alike): `div.rechentabelle` holds one svg.
// Each table `g.table[data-table=i]` (class `wrong`) has `g.corner` (a rect and `text.given`, the op label), a value
// cell `g.head[data-row][data-col]` per row value (data-col 0) and column value (data-row 0), and a result cell
// `g.cell[data-row][data-col]` (rows and columns from 1). Each has a rect and, when it shows, a text: class `given` in
// #222, in the key a missing one class `answer` in #c0392b. A struck cell has `line.strike` from corner to corner and
// no text. Every answer has one right value (each hidden value has its own given cell), so the key has no note "Auch
// andere Lösungen sind richtig."
//
// Units: a cell is CELL = 10 square, a table (cols + 1) · CELL wide and (rows + 1) · CELL high, tables side by side
// CG = 8 apart, rows of tables RG = 6 apart.
//
// The panel (pages/Rechentabelle.tsx), whose words the tests take as selectors: steppers "Eine Tabelle weniger/mehr"
// ("2 Tabellen"), "Weniger Tabellen nebeneinander" / "Mehr Tabellen nebeneinander" ("2 nebeneinander"), "Eine Zeile
// weniger/mehr" ("4 Zeilen"), "Eine Spalte weniger/mehr" ("4 Spalten"), "Ein versteckter Zeilenwert weniger/mehr"
// ("0 Zeilenwerte versteckt"), "Ein versteckter Spaltenwert weniger/mehr" ("0 Spaltenwerte versteckt"); selects
// "Rechenart", "Zahlenraum" (Plus and Minus), two selects "Zehnerübergang" and "Hunderterübergang" (shown with max 1000),
// each with the options "either" "Egal", "required" "Mit", "none" "Ohne";
// "Anordnung" and "Erstfaktor" (Mal and Geteilt), "Farbe";
// checkboxes "2er-Reihe" and so on (Mal and Geteilt; the last checked one is disabled); select "Rechentabelle für
// eigene Zahlen"; number fields "Spaltenwert j", "Zeilenwert i", "Zeile i, Spalte j" (from 1). Hints (p.hint,
// role=status): per wrong table "Rechentabelle i: Die Zahlen passen nicht zusammen."; loose "carry" "Mit dieser
// Übertrag-Regel gibt es nicht genug verschiedene Zahlen: manche Werte kommen zweimal vor."; loose "distinct" "Der
// Zahlenraum ist zu klein: manche Werte kommen zweimal vor."; Mal and Geteilt with cols > reihen or rows > the Erstfaktoren "Mehr Zeilen oder
// Spalten als Reihen oder Erstfaktoren: Werte wiederholen sich." Fewer rows or columns than hidden values lowers the
// hidden count in the same step.

import { rng } from "./zahlenmauer";
import { carryList, FAMILY, FIRST, tablesOf } from "./rechentabelle/fill";
export { carryList, FAMILY, FIRST };

/** A number the teacher typed: the table's index (from 0), the row (0 is the column values' row), the column (0 is the row values' column), the value (0 to 9999). */
export type RechentabelleTyped = [number, number, number, number];
export type RechentabelleProps = {
  /** Number of Rechentabellen on the sheet, side by side in rows of `columns`. Default 2.
   * @minimum 1
   * @maximum 4
   */
  count: number;
  /** Number of Rechentabellen per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** Rows per table: the row values down the left side. Default 4.
   * @minimum 2
   * @maximum 10
   */
  rows: number;
  /** Columns per table: the column values along the top. Default 4.
   * @minimum 2
   * @maximum 10
   */
  cols: number;
  /** The Rechenart in the corner: "+" (Plus), "-" (Minus, row value minus column value), "*" (Mal) or ":" (Geteilt, row value divided by column value; a cell with no whole answer is struck through). Default "+". */
  op: "+" | "-" | "*" | ":";
  /** Plus and Minus: the Zahlenraum, the largest number in the table, one of 10, 20, 100 or 1000. Any other value gives 20. Default 20. */
  max: number;
  /** Plus and Minus: the Übertrag per place, [Zehnerübergang, Hunderterübergang]: "none" no cell carries into that place, "required" every cell does, "either" no rule. The Hunderterübergang counts only with max 1000, else it is "either". "none" at the top place that counts also rules out every place above it. Default ["either", "either"]. */
  carry: [CarryRule, CarryRule];
  /** Mal and Geteilt: the Einmaleins-Reihen, distinct numbers 1 to 10, as the column values. Default [2, 4, 5, 10]. */
  reihen: number[];
  /** Mal and Geteilt: the order of the Reihen along the top: "related" related Reihen side by side (1, 2, 4, 8, 3, 6, 9, 5, 10, 7), "random" a random order. Default "related". */
  order: "related" | "random";
  /** Mal and Geteilt: the Erstfaktoren down the left side: "all" 1 to 10, "kings" only the Königsaufgaben 1, 2, 5, 10, "near" the Königsaufgaben plus or minus 1: 3, 4, 6, 9. Default "all". */
  first: "all" | "kings" | "near";
  /** How many row values are hidden; a given result cell in each such row lets the pupils work it back. 0 to rows − 1. Default 0.
   * @minimum 0
   * @maximum 9
   */
  hideRows: number;
  /** How many column values are hidden; a given result cell in each such column lets the pupils work it back. 0 to cols − 1. Default 0.
   * @minimum 0
   * @maximum 9
   */
  hideCols: number;
  /** A tint: "none", or one base colour ("blue", "green", "yellow", "red", "purple") for the value cells, darker in the corner; the result cells stay white. Default "none". */
  tint: "none" | "blue" | "green" | "yellow" | "red" | "purple";
  /** Seed for the random tables. The same seed always gives the same tables. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [table index from 0, row from 0, column from 0, value 0 to 9999]: row 0 holds the column values, column 0 the row values, the others the result cells. Typed numbers win over the drawn ones; a table whose numbers do not fit is marked wrong and its key shows no answers. */
  typed?: RechentabelleTyped[];
};

export type CarryRule = "none" | "required" | "either";
export type Op = RechentabelleProps["op"];
export type Tint = RechentabelleProps["tint"];
// A table: its row and column values, its result cells (cells[i][j] for row i + 1 and column j + 1, 0 where struck or
// made up), which of them show, and whether its typed numbers do not fit.
export type Table = {
  rows: number[];
  cols: number[];
  cells: number[][];
  /** Geteilt: no whole answer, struck through. */
  struck: boolean[][];
  /** Below 0 or a divisor 0: the cell stays empty, also in the key. */
  madeUp: boolean[][];
  /** Whether the cell shows on the pupils' sheet. */
  given: boolean[][];
  rowShown: boolean[];
  colShown: boolean[];
  wrong: boolean;
};
export type Made = { tables: Table[]; loose: null | "carry" | "distinct" };

export const DEFAULTS: Omit<RechentabelleProps, "seed"> = {
  count: 2,
  columns: 2,
  rows: 4,
  cols: 4,
  op: "+",
  max: 20,
  carry: ["either", "either"],
  reihen: [2, 4, 5, 10],
  order: "related",
  first: "all",
  hideRows: 0,
  hideCols: 0,
  tint: "none",
};

const OPS: Op[] = ["+", "-", "*", ":"];
// Per tint the value cells' colour and the corner's darker one.
export const TINT: Record<Exclude<Tint, "none">, [string, string]> = {
  blue: ["#d6e6f7", "#a9c8ec"],
  green: ["#d8f0d8", "#a8dba8"],
  yellow: ["#fbf0c4", "#f3dc84"],
  red: ["#f7d9d6", "#eeaaa4"],
  purple: ["#e6dcf3", "#c8b4e6"],
};

// Whether x is a whole number from lo to hi.
const whole = (x: number, lo: number, hi: number) =>
  Number.isInteger(x) && x >= lo && x <= hi;

// The settings as a rechentabelle block can take them, whatever a stored sheet holds: a wrong value gives its default,
// a typed entry that is not four whole numbers in range is dropped, and of two for the same cell the last one stays.
export function sane(p: RechentabelleProps): RechentabelleProps {
  const count = whole(p.count, 1, 4) ? p.count : DEFAULTS.count;
  const columns = whole(p.columns, 1, 3) ? p.columns : DEFAULTS.columns;
  const rows = whole(p.rows, 2, 10) ? p.rows : DEFAULTS.rows;
  const cols = whole(p.cols, 2, 10) ? p.cols : DEFAULTS.cols;
  const op = OPS.includes(p.op) ? p.op : DEFAULTS.op;
  const max = [10, 20, 100, 1000].includes(p.max) ? p.max : DEFAULTS.max;
  const isRule = (x: unknown): x is CarryRule =>
    x === "none" || x === "required" || x === "either";
  const carry: [CarryRule, CarryRule] =
    Array.isArray(p.carry) && p.carry.length === 2 && p.carry.every(isRule)
      ? [...p.carry]
      : [...DEFAULTS.carry];
  if (max < 1000) carry[1] = "either";
  const ok =
    Array.isArray(p.reihen) &&
    p.reihen.length > 0 &&
    p.reihen.every((n) => whole(n, 1, 10)) &&
    new Set(p.reihen).size === p.reihen.length;
  const reihen = ok ? [...p.reihen] : [...DEFAULTS.reihen];
  const order = p.order === "random" ? "random" : "related";
  const first = p.first === "kings" || p.first === "near" ? p.first : "all";
  const hideRows = whole(p.hideRows, 0, rows - 1)
    ? p.hideRows
    : whole(p.hideRows, 0, 9)
      ? rows - 1
      : 0;
  const hideCols = whole(p.hideCols, 0, cols - 1)
    ? p.hideCols
    : whole(p.hideCols, 0, 9)
      ? cols - 1
      : 0;
  const tint =
    typeof p.tint === "string" && Object.hasOwn(TINT, p.tint) ? p.tint : "none";
  const typed = new Map<string, RechentabelleTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (
        !Array.isArray(t) ||
        t.length !== 4 ||
        !t.every((x) => Number.isInteger(x))
      )
        continue;
      const [c, r, s, v] = t;
      if (
        c < 0 ||
        c >= count ||
        r < 0 ||
        r > 10 ||
        s < 0 ||
        s > 10 ||
        (r === 0 && s === 0) ||
        v < 0 ||
        v > 9999
      )
        continue;
      typed.delete(`${c}:${r}:${s}`);
      typed.set(`${c}:${r}:${s}`, [c, r, s, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count,
    columns,
    rows,
    cols,
    op,
    max,
    carry,
    reihen,
    order,
    first,
    hideRows,
    hideCols,
    tint,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// The corner's label: "+", "−" (U+2212), "·" (U+00B7) or ":".
const SIGN: Record<Op, string> = { "+": "+", "-": "−", "*": "·", ":": ":" };
export function opLabel(op: Op): string {
  return SIGN[op];
}

// The drawing in svg units. `vbW` and `vbH` are the viewBox; `TW` and `TH` one table's size.
export function layout(
  p: Pick<RechentabelleProps, "count" | "columns" | "rows" | "cols">,
) {
  const [CELL, CG, RG] = [10, 8, 6];
  const TW = (p.cols + 1) * CELL;
  const TH = (p.rows + 1) * CELL;
  const across = Math.min(p.columns, p.count);
  const lines = Math.ceil(p.count / p.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = lines * TH + (lines - 1) * RG + 1;
  return { CELL, CG, RG, TW, TH, lines, vbW, vbH };
}

// The default block is drawn at the scale S0 at 180 mm wide. A block of width w draws its tables at that scale, and its
// height grows with the rows, so that they keep that size.
const S0 = 180 / layout(DEFAULTS).vbW;

// The height in mm of a block of width w with the props p, at which its tables draw at least at the default scale.
export function heightFor(p: RechentabelleProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// The tables of the settings. The same settings give the same tables on every call.
const memo = new Map<string, Made>();

export function made(props: RechentabelleProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const next = rng(p.seed);
  const out = tablesOf(p, next);
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}

