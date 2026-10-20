// The Zehnerfeld generator: Plus and Minus tasks on a field of dots (Zehnerfeld 1 × 10 or 2 × 5, Zwanzigerfeld 2 × 10,
// Hunderterfeld 10 × 10), for Klasse 1. A pure function of the block's settings and its seed, so that the editor, the
// thumbnail and the PDF draw the same tasks.
//
// A block of its own, not a look of the Hunderterfeld block (hunderterfeld.ts): that block is one Hundertertafel or
// one field of 100 dots with no task, and its props stay as they are, so old sheets open and print unchanged.
//
// The contract of #829, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "zehnerfeld", props: ZehnerfeldProps }`.
// - `count` tasks (1 to 12, default 4) in `columns` side by side (1 to 4, default 2). A task is one field with a task
//   line under it: [box a] [+ or −] [box b] [=] [box r].
// - `field`, the Typ: "zehn" Zehnerfeld 1 × 10, "zehn2" Zehnerfeld 2 × 5, "zwanzig" Zwanzigerfeld 2 × 10 (default),
//   "hundert" Hunderterfeld 10 × 10. C, the field's size, is 10, 10, 20 or 100. The field has `rows` × `cols` dots:
//   1 × 10, 2 × 5, 2 × 10, 10 × 10. Dot k (0 to C − 1) sits in row floor(k / cols), column k mod cols, so the dots
//   count row by row from the top left.
// - `op`, the Rechenart: "+" (Plus, default) or "-" (Minus). The sheet shows "+" or "−" (U+2212).
// - `task`, the Aufgabentyp: "dots" Punkte gegeben, Aufgabe schreiben (default): the field shows the dots, the three
//   boxes are empty; "write" Aufgabe gegeben, Punkte malen: a and b show in their boxes, r and the field are empty;
//   "mixed" gemischt: task i is "dots" for even i, "write" for odd i.
// - `max`, the Zahlenraum: 5, 10, 20, 50 or 100; any other value gives C. It acts as M = min(max, C) and stays stored.
// - `cross`, the Zehnerübergang: "any" egal (default), "yes" mit, "no" ohne. It counts only with C ≥ 20 (Zwanziger-
//   and Hunderterfeld); with C = 10 it acts as "any" and stays stored. Any other value gives "any".
// - `lines`, Trennlinien: true (default) draws a strong line after each five: between column 5 and 6 when a row has 10
//   dots, between row 5 and 6 when the field has 10 rows, and between the two rows of the 2 × 5 field.
// - `colors`, Farben: "color" Farbe (default) the colours COLOR, "grey" Graustufen the colours GREY, "own" eigene zwei
//   Farben `color1` and `color2` (each "#rrggbb", lower case; any other value gives COLOR's).
// - `manual`, Punkte selbst setzen: false (default). True: each field shows exactly its `marks`, no task's dots; the
//   three boxes stay empty, also in the key (a field the teacher set has no worked out answer). The signs show.
// - `marks`: the dots the teacher set, each entry [task 0 to 11, dot 0 to 99, mark 1 to 3]: 1 colour 1, 2 colour 2,
//   3 colour 1 struck through. An entry that is not three whole numbers in range is dropped; of two for the same task
//   and dot the last one stays. A dot not below C plays no part (and stays stored), as does a task the block lacks.
// - `typed`: numbers the teacher typed, each entry [task 0 to 11, position 0 to 2, value 0 to 100]. The positions: 0
//   the first number a, 1 the second number b, 2 the result r. Dropped and kept as `marks`.
// - `seed` alone gives the drawn tasks.
//
// The rule every task keeps, drawn or typed (C the field's size): Plus a ≥ 1, b ≥ 1, r = a + b ≤ C; Minus 1 ≤ a ≤ C,
// 1 ≤ b ≤ a, r = a − b (so r ≥ 0). The field shows the task: Plus dots 0 to a − 1 in colour 1 and dots a to a + b − 1
// in colour 2; Minus dots 0 to a − 1 in colour 1, and of them the dots a − b to a − 1 struck through. The other dots
// are empty.
// The Zehnerübergang: Plus a + b crosses a ten exactly when (a mod 10) + (b mod 10) > 10; Minus a − b exactly when
// the Plus task r + b crosses, (r mod 10) + (b mod 10) > 10. So 8 + 5 and 13 − 5 cross, 6 + 4 = 10, 16 + 4 = 20,
// 10 − 4 and 20 − 4 do not (they reach the full ten and do not go over it), and 45 + 30 does not (only the Einer count).
// "yes" needs the crossing, "no" forbids it.
//
// The drawn tasks (`made`, memo of 50, `rng` from zahlenmauer.ts). A drawn task keeps, besides the rule, the Zahlenraum
// (Plus r ≤ M, Minus a ≤ M) and the Zehnerübergang as it acts. P is the list of every pair (a, b) that keeps them,
// built by a plain walk of a from 1 to M and b from 1 to M, a first, then b, rising; never by trying random tasks, so
// a drawn task never breaks a rule. If P is empty (Zehnerfeld bis 5 with Minus never is; Zwanzigerfeld bis 10 "mit"
// is), `none` is true, no draws are made, and every task not the teacher's own is empty (no dots, no number, no signs,
// also in the key). Per task i, whatever is typed, so that the tasks after a typed one stay as they were: up to 20
// tries, each one draw (a, b) = P[floor(next() · |P|)]; a try equal to an earlier task's drawn pair is dropped, and
// after 20 tries the last one stays (a repeated task keeps every rule).
//
// Typed numbers win over the seed. A task with at least one typed entry is the teacher's own; `solve` works it out
// from its typed positions against the rule alone (`max` and `cross` only steer the draw), by a plain walk of every a
// and b from 1 to C: the drawn task when it fits the typed numbers, else the solution of the smallest a and then the
// smallest b; no solution: `wrong`. A wrong task draws no dots and no number (its boxes empty, its field empty), on
// the pupils' sheet and in the key: never a false number. The panel, at the first number typed into a task, stores
// the task's drawn a and b as typed entries with it (not when `none`), so that what the sheet showed stays.
// Every task of this block shows a and b (as dots or as numbers), so its answer is one: the key never says "Auch
// andere Lösungen sind richtig.".
//
// Layout, in units (1 unit = 1 mm at scale 1): a dot's square U = 6, dot radius 2.2. The field FW = cols · U wide,
// FH = rows · U high. The task line: three boxes of B = 10 by LH = 8 and two sign squares of 5: LW = 3 · B + 2 · 5 =
// 40. A task TW = max(FW, LW) wide, TH = FH + G + LH high, G = 3 between field and line; the field and the line each
// centred in TW. Tasks side by side CG = 6 apart, rows of tasks RG = 6 apart; across = min(columns, count), rows =
// ceil(count / columns); vbW = across · TW + (across − 1) · CG + 1, vbH = rows · TH + (rows − 1) · RG + 1 (+1 for the
// stroke; the drawing sits at 0.5, 0.5). A new block is inserted at vbW wide (scale 1); `heightFor(p, w)` is
// vbH · min(w / vbW, 1).
//
// The drawing (sheet.tsx `Zehnerfeld`, on screen, print and in the key alike): `div.zehnerfeld` (with `.solved` in the
// key) holds one svg with viewBox 0 0 vbW vbH. Each task `g.task[data-task=i]` (class `wrong`, class `none`, class
// `manual` as they hold). Its field `g.field`: a white rect with stroke #222 of 0.4 around it, the square lines inside
// in #bbb of 0.2, with `lines` one `line.trenn` per Trennlinie in #222 of 0.8; per dot `circle.dot[data-k=k]
// [data-mark=m]`, m 0 empty (fill white, stroke #888 of 0.3), 1 colour 1, 2 colour 2 (filled, no stroke), 3 colour 1
// struck through: the circle as 1 and over it `line.strike` from its lower left to its upper right, twice: white of
// 1.2, then #222 of 0.5, so that the stroke shows on any colour. The task line: `g.slot[data-pos=p]` per box, a white
// rect with stroke #222 of 0.3, its number as `text.given` (#222) or in the key `text.answer` (#c0392b), size 5.5;
// `text.op` and `text.eq` in the sign squares, #222 (not for an empty task under `none`).
// What shows: a "dots" task its dots on the sheet and the key, its boxes empty on the sheet, a, b and r as `answer` in
// the key. A "write" task a and b as `given`, its field empty on the sheet; in the key its dots and r as `answer`. In
// the key the dots are the same as on a "dots" sheet.
// Colours (`COLOR`, `GREY`): COLOR red #e3463b and blue #1d4ea6, whose greys (0.299 r + 0.587 g + 0.114 b) differ by
// at least 40 of 255, so a black and white copy keeps them apart; GREY #222222 and #9a9a9a, at least 40 apart from each
// other and from white, so Graustufen stay readable in print.
//
// The panel (pages/Zehnerfeld.tsx), whose words the tests take as selectors: steppers "Eine Aufgabe weniger" / "Eine
// Aufgabe mehr" ("4 Aufgaben", "1 Aufgabe"), "Weniger Aufgaben nebeneinander" / "Mehr Aufgaben nebeneinander" ("2
// nebeneinander"); select "Feld" ("zehn" "Zehnerfeld 1 × 10", "zehn2" "Zehnerfeld 2 × 5", "zwanzig" "Zwanzigerfeld
// 2 × 10", "hundert" "Hunderterfeld 10 × 10"); select "Rechenart" ("Plus", "Minus"; a change drops `typed` in the same
// undo step); select "Aufgabentyp" ("dots" "Punkte gegeben, Aufgabe schreiben", "write" "Aufgabe gegeben, Punkte
// malen", "mixed" "Gemischt"); select "Zahlenraum" ("bis 5" ... "bis 100", only the values up to C; it shows M);
// with C ≥ 20 select "Zehnerübergang" ("any" "egal", "yes" "mit Zehnerübergang", "no" "ohne Zehnerübergang"); checkbox
// "Trennlinien"; select "Farben" ("color" "Farbe", "grey" "Graustufen", "own" "Eigene Farben"), with "own" two colour
// inputs "Erste Farbe" and "Zweite Farbe"; checkbox "Punkte selbst setzen"; with 2 or more tasks select "Aufgabe"
// ("Aufgabe 1" ...), the task the fields below set. Without `manual`: number fields "Erste Zahl", "Zweite Zahl"
// showing the task's a and b (empty for a wrong or empty task); each field is one undo step (key `typed:i:p`), its
// text kept as a draft while it has focus. With `manual`: a grid `.punkte` of C buttons "Punkt n" (n from 1), each
// with `data-mark` 0 to 3; a click cycles the mark 0, 1, 2, 3, 0 and is one undo step. Hints (p.hint, role=status):
// with `none` "Mit diesen Einstellungen gibt es keine Aufgabe."; per wrong task "Aufgabe i: Die Zahlen passen nicht
// ins Feld.". Buttons "Eigene Zahlen entfernen" (with typed), "Neu würfeln" (changes only the seed). Every setting is
// one undo step.

/** A number the teacher typed: the task's index (from 0), the position (0 to 2), the value (0 to 100). */
export type ZehnerfeldTyped = [number, number, number];
/** A dot the teacher set: the task's index (from 0), the dot (0 to 99), the mark (1, 2 or 3). */
export type ZehnerfeldMark = [number, number, number];
export type Field = "zehn" | "zehn2" | "zwanzig" | "hundert";
export type Cross = "any" | "yes" | "no";
export type ZehnerfeldProps = {
  /** Number of tasks (fields) on the sheet, side by side in rows of `columns`. Default 4.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of tasks per row. Default 2.
   * @minimum 1
   * @maximum 4
   */
  columns: number;
  /** The Typ of field: "zehn" Zehnerfeld 1 × 10, "zehn2" Zehnerfeld 2 × 5, "zwanzig" Zwanzigerfeld 2 × 10, "hundert" Hunderterfeld 10 × 10. The dots count row by row from the top left. Default "zwanzig". */
  field: Field;
  /** The Rechenart: "+" (Plus: the first number's dots in colour 1, the second number's in colour 2) or "-" (Minus: the first number's dots in colour 1, the second number's of them struck through). Default "+". */
  op: "+" | "-";
  /** The Aufgabentyp: "dots" the field shows the dots and the pupil writes the task; "write" the task's two numbers show and the pupil paints the dots and writes the result; "mixed" the two by turns, starting with "dots". Default "dots". */
  task: "dots" | "write" | "mixed";
  /** The Zahlenraum: 5, 10, 20, 50 or 100, at most the field's size (10, 20 or 100). Plus results and Minus first numbers stay within it. Default 20. */
  max: number;
  /** The Zehnerübergang: "yes" every task crosses a ten (Plus: the Einer of both numbers add up to more than 10, as 8 + 5; Minus: the Einer of the result and the second number do, as 13 − 5), "no" none does (6 + 4 = 10 and 20 − 4 do not cross), "any" either. Counts only with the Zwanziger- and Hunderterfeld. Default "any". */
  cross: Cross;
  /** Trennlinien: true draws a strong line after each five dots, across and down. Default true. */
  lines: boolean;
  /** Farben: "color" red and blue, "grey" Graustufen (black and grey, for black and white copies), "own" the colours `color1` and `color2`. Default "color". */
  colors: "color" | "grey" | "own";
  /** The first colour with `colors` "own", as "#rrggbb". Default "#e3463b". */
  color1?: string;
  /** The second colour with `colors` "own", as "#rrggbb". Default "#1d4ea6". */
  color2?: string;
  /** Punkte selbst setzen: true shows in each field exactly the dots in `marks` and no task; the number boxes stay empty for the pupil. Default false. */
  manual: boolean;
  /** The dots the teacher set with `manual`. Each entry is [task index from 0, dot 0 to 99 counted row by row, mark 1 colour 1, 2 colour 2 or 3 colour 1 struck through]. */
  marks?: ZehnerfeldMark[];
  /** Seed for the random tasks. The same seed always gives the same tasks. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [task index from 0, position 0 to 2, value 0 to 100]. Positions: 0 the first number, 1 the second number, 2 the result. The other positions are worked out from them; a task whose typed numbers do not fit the field is marked wrong and shows no dots and no numbers. */
  typed?: ZehnerfeldTyped[];
};

// A task: [a, b, r] (0 where unknown), its kind as it shows ("dots" or "write"), its dots (C marks, 0 to 3, the task's
// own picture, also for a "write" task), whether its typed numbers do not fit, and whether it is an empty drawn task.
export type Task = { values: number[]; kind: "dots" | "write"; dots: number[]; wrong: boolean; none: boolean };
export type Made = { tasks: Task[]; none: boolean };

export const DEFAULTS: Omit<ZehnerfeldProps, "seed"> = {
  count: 4,
  columns: 2,
  field: "zwanzig",
  op: "+",
  task: "dots",
  max: 20,
  cross: "any",
  lines: true,
  colors: "color",
  manual: false,
};
export const MAXES = [5, 10, 20, 50, 100];
export const COLOR = ["#e3463b", "#1d4ea6"] as const;
export const GREY = ["#222222", "#9a9a9a"] as const;
// The field's rows and columns by Typ.
export const SHAPE: Record<Field, { rows: number; cols: number }> = {
  zehn: { rows: 1, cols: 10 },
  zehn2: { rows: 2, cols: 5 },
  zwanzig: { rows: 2, cols: 10 },
  hundert: { rows: 10, cols: 10 },
};

// The exports the drawing, the panel and the insert use; the generator fills them in:
// - `sane(p: ZehnerfeldProps): ZehnerfeldProps`: the sane settings (a wrong value gives its default, as the contract
//   says; `typed` and `marks` only when they have entries; `max`, `cross`, `color1`, `color2` stay as stored when valid).
// - `acts(p): { C: number; M: number; cross: Cross; rows: number; cols: number }`: the field and the rules as they act.
// - `colorsOf(p): [string, string]`: the two colours as they draw.
// - `crosses(op, a, b): boolean`: the Zehnerübergang of the contract.
// - `picture(op, a, b, C): number[]`: the C marks of the task's field.
// - `solve(op, known: (number | null)[], drawn: number[] | null, C): number[] | null`: a teacher's own task [a, b, r]
//   from its typed positions, or null when none fits; exact, by a plain walk.
// - `layout(p)`: { U, B, LH, G, FW, FH, LW, TW, TH, CG, RG, rows, across, vbW, vbH } as the contract says.
// - `heightFor(p, w: number): number` and `widthFor(p): number` (vbW).
// - `opLabel(op): string`: "+" or "−".
// - `made(p): Made`.
