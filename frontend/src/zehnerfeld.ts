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
// - `typed`: numbers the teacher typed, each entry [task 0 to 11, position 0 to 2, value 0 to 999]. The positions: 0
//   the first number a, 1 the second number b, 2 the result r. An entry that is not three whole numbers in range is
//   dropped; of two for the same task and position the last one stays; an entry of a task the block lacks stays
//   stored and plays no part.
// - A change of `field` or `op` in the panel drops `typed` in the same undo step (the typed pairs belong to the old
//   field and Rechenart). `marks` stay through every change: dot k keeps its index. Varianten B to D drop `typed`
//   and keep `marks`, as for every block.
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
// ("Aufgabe 1" ...), the task the fields below set. A colour input commits on change (one undo step), not per
// input event. Without `manual`: number fields "Erste Zahl", "Zweite Zahl"
// showing the task's a and b (empty for a wrong or empty task); each field is one undo step (key `typed:i:p`), its
// text kept as a draft while it has focus. With `manual`: a grid `.punkte` of C buttons "Punkt n" (n from 1), each
// with `data-mark` 0 to 3; a click cycles the mark 0, 1, 2, 3, 0 and is one undo step. Hints (p.hint, role=status):
// with `none` "Mit diesen Einstellungen gibt es keine Aufgabe."; per wrong task "Aufgabe i: Die Zahlen passen nicht
// ins Feld.". Buttons "Eigene Zahlen entfernen" (with typed), "Neu würfeln" (changes only the seed). Every setting is
// one undo step.

export {
  COLOR,
  DEFAULTS,
  GREY,
  MAXES,
  SHAPE,
  acts,
  colorsOf,
  heightFor,
  layout,
  opLabel,
  sane,
  widthFor,
  type Cross,
  type Field,
  type Made,
  type Task,
  type ZehnerfeldMark,
  type ZehnerfeldProps,
  type ZehnerfeldTyped,
} from "./zehnerfeld/props";
export { crosses, made, picture, solve } from "./zehnerfeld/tasks";
