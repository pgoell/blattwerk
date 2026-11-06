// The Stellenwert-Bild generator: numbers as base-ten pictures (Hunderterplatte 100, Zehnerstange 10, Einerwürfel 1)
// for Klasse 2 and 3. A pure function of the block's settings and its seed, so that the editor, the thumbnail and
// the PDF draw the same tasks.
//
// The contract of #1076, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "stellenwertbild", props: StellenwertbildProps }`.
// - `count` tasks (1 to 12, default 4) in `columns` side by side (1 to 4, default 2).
// - `max`, the Zahlenraum: 100 or 1000 (default 1000); any other value gives 1000. The places: with 100 Z and E
//   (values [10, 1]), with 1000 H, Z and E (values [100, 10, 1]). The first place is the leading place.
// - `task`, the Aufgabentyp: "read" Bild gegeben, Zahl schreiben (default): the picture shows, the pupil writes the
//   number (and, with `table`, the digits in a Stellenwerttafel); "draw" Zahl gegeben, Bild zeichnen: the number
//   shows, the pupil draws it as square (H), stroke (Z) and dot (E) in an empty frame.
// - `table`, Stellenwerttafel: true (default) puts a table of the places (H Z E or Z E) before the number box of a
//   "read" task. With "draw" it plays no part and stays stored.
// - `zero`, Stellen mit 0: false (default) every drawn number has no digit 0; true every drawn number has a 0 in at
//   least one place that is not the leading place (305, 260, 40).
// - `bundle`, Bündeln: false (default). True: the picture of every task has more than 9 pieces in exactly one place
//   (2 H 14 Z 6 E), so the pupil exchanges first (Umtauschen).
// - `typed`: numbers the teacher typed, each entry [task 0 to 11, value 0 to 9999]. An entry that is not two whole
//   numbers in range is dropped; of two for the same task the last one stays; an entry of a task the block lacks
//   stays stored and plays no part.
// - A change of `max` in the panel drops `typed` in the same undo step. Varianten B to D drop `typed`, as for every
//   block. `seed` alone gives the drawn tasks.
//
// A task is its counts c (one per place: how many pieces the picture has of that place), its number n = Σ c·value,
// and its digits d (n's digits per place, the exchanged form; d has as many entries as there are places).
// The rule every task keeps, drawn or typed: the leading count is 1 to 9; n < max; without `bundle` every count is 0
// to 9 (so c = d); with `bundle` exactly one place that is not the leading place has a count of 10 to 19, the
// others 0 to 9. A drawn task keeps besides the rule the `zero` setting on its digits d. Typed numbers ignore `zero`
// (the teacher's number wins), as Zehnerfeld's typed numbers ignore `cross`.
//
// The drawn tasks (`made`, memo of 50, `rng` from zahlenmauer.ts). P is the list of every count tuple that keeps the
// rule and `zero`, built by plain nested loops over the counts, the leading place outermost, each count rising from
// 0 (the leading one from 1) to 19; never by trying random numbers, so a drawn task never breaks a rule. If P is
// empty, `none` is true, no draws are made, and every task not the teacher's own is empty (no picture, no number,
// also in the key). Per task i, whatever is typed, so that the tasks after a typed one stay as they were: up to 20
// tries, each one draw c = P[floor(next() · |P|)]; a try whose n equals an earlier task's drawn n is dropped, and
// after 20 tries the last one stays (a repeated number keeps every rule).
//
// Typed numbers win over the seed. A task with a typed entry v is the teacher's own; `solve` gives its counts against
// the rule alone: the drawn counts when their n is v, else the first tuple of the same plain walk (without the
// `zero` filter) whose n is v; none: `wrong`. A wrong task draws no picture and no number, on the pupils' sheet and
// in the key: never a false number. So with `bundle` 100 and 105 never fit (no place can take a bundle), 346 fits as
// 2 H 14 Z 6 E (the first of the walk); without `bundle` with max 1000 a number below 100 or above 999 never fits.
// Each task's answer is one: the key never says "Auch andere Lösungen sind richtig.".
//
// Layout, in units (1 unit = 1 mm at scale 1). A cell s = 1.2. The places sit left to right in zones, ZG = 4 apart:
// - H zone (max 1000 only): plates of 12 × 12 (10 × 10 cells); plate k at x (k mod 3) · 14, y floor(k / 3) · 14.
//   The zone is 40 wide and 40 high.
// - Z zone: rods of 1.2 × 12 (1 × 10 cells, standing); rod k at row floor(k / 10), column j = k mod 10, x j · 2.4 +
//   (j ≥ 5 ? 1.2 : 0), y row · 14. The zone is 24 wide, 12 high (26 with `bundle`).
// - E zone: cubes of 1.2 × 1.2; cube k at x (k mod 5) · 2.4, y floor(k / 5) · 2.4. The zone is 10.8 wide, 3.6 high
//   (8.4 with `bundle`).
// The picture PW = the zones' widths + ZG between them (82.8 with max 1000, 38.8 with 100) wide, PH = the highest
// zone's height high, but at least 20 with "draw" (room for the pupil's drawing); each zone's pieces start at its
// top left.
// The line under the picture, G = 3 below it: a number box NB = 16 by 8.
// - "read" with `table`: the table, one column of 8 per place, a head row of 5 (the letters H, Z, E) over a row of 8,
//   then the sign "=" in a square of 5, then the number box aligned with the table's lower row. LW = places · 8 + 5 +
//   16, LH = 13.
// - "read" without `table`: the number box alone. LW = 16, LH = 8.
// - "draw" without `bundle`: the number box with the number given. LW = 16, LH = 8.
// - "draw" with `bundle`: the counts as text, FW = 34 wide with max 1000 and 22 with 100 ("2 H 14 Z 6 E", "3 Z 14 E"),
//   then "=" in 5, then the empty number box. LW = FW + 5 + 16, LH = 8.
// - "read" with `bundle`: under the line, KL = 6 for the exchanged form, written in the key only.
// A task TW = max(PW, LW) wide, TH = PH + G + LH (+ KL) high; the picture and the line each centred in TW. Tasks side
// by side CG = 8 apart, rows of tasks RG = 6 apart; across = min(columns, count), rows = ceil(count / columns);
// vbW = across · TW + (across − 1) · CG + 1, vbH = rows · TH + (rows − 1) · RG + 1 (+1 for the stroke; the drawing
// sits at 0.5, 0.5). A new block is inserted at vbW wide (scale 1); `heightFor(p, w)` is vbH · min(w / vbW, 1).
//
// The drawing (sheet/blocks/stellenwertbild.tsx, on screen, in print and in the key alike): `div.stellenwertbild`
// (with `.solved` in the key) holds one svg with viewBox 0 0 vbW vbH. Each task `g.task[data-task=i]` (class `wrong`,
// class `none` as they hold).
// - "read": per piece one `g.piece[data-v=100|10|1]`: a rect of the piece's size, fill white, stroke #222 of 0.25,
//   with the inner cell lines (plate 9 + 9, rod 9) in #999 of 0.1. As many pieces of a place as its count c.
// - "draw": `rect.frame` of PW × PH, fill white, stroke #222 of 0.3, empty on the sheet. In the key, at the same slots
//   as the pieces would be, per digit d (the exchanged form): `.sym[data-v=100]` a square rect of 6 × 6 in the plate's
//   middle, `.sym[data-v=10]` a line down the rod's middle, `.sym[data-v=1]` a circle of r 0.6 in the cube's middle,
//   all in #c0392b, stroke 0.4 (the circle filled).
// - The table `g.table`: per place a `text.head` letter (#222, size 4) and a `g.cell[data-v=value]` (a rect, stroke
//   #222 of 0.3), with in the key the digit d as `text.answer`.
// - The number box `g.slot`: a rect of 16 × 8, stroke #222 of 0.3; its number as `text.given` (#222, size 5.5) on a
//   "draw" task without `bundle`, as `text.answer` (#c0392b, size 5.5) in the key of every other task.
// - `text.given.form` with "draw" and `bundle`: the counts, "2 H 14 Z 6 E" (places with count 0 too: "3 H 0 Z 14 E").
// - `text.answer.exchanged` with "read" and `bundle`, in the key only: "= 3 H 4 Z 6 E" (every place, zeros too).
// - `text.eq` the "=" signs, #222. A wrong or empty task draws none of the pieces, symbols, numbers or forms; its
//   frame, table and boxes stay, empty.
//
// The panel (pages/Stellenwertbild.tsx), whose words the tests take as selectors: steppers "Eine Aufgabe weniger" /
// "Eine Aufgabe mehr" ("4 Aufgaben", "1 Aufgabe"), "Weniger Aufgaben nebeneinander" / "Mehr Aufgaben nebeneinander"
// ("2 nebeneinander"); select "Zahlenraum" ("bis 100", "bis 1000"; a change drops `typed` in the same undo step);
// select "Aufgabentyp" ("read" "Bild gegeben, Zahl schreiben", "draw" "Zahl gegeben, Bild zeichnen"); with "read"
// checkbox "Stellenwerttafel"; checkbox "Stellen mit 0"; checkbox "Bündeln (mehr als 9)"; with 2 or more tasks select
// "Aufgabe" ("Aufgabe 1" ...), the task the field below sets; number field "Zahl" showing the task's n (empty for a
// wrong or empty task), up to 4 digits; it is one undo step per task (key `typed:i`), its text kept as a draft while
// it has focus; emptying it removes the task's entry. Hints (p.hint, role=status): with `none` "Mit diesen
// Einstellungen gibt es keine Aufgabe."; per wrong task "Aufgabe i: Die Zahl passt nicht zu den Einstellungen.".
// Buttons "Eigene Zahlen entfernen" (with typed), "Neu würfeln" (changes only the seed). Every setting is one undo step.

export {
  DEFAULTS,
  PLACES,
  formOf,
  heightFor,
  layout,
  placesOf,
  sane,
  widthFor,
  type Made,
  type StellenwertbildProps,
  type StellenwertbildTyped,
  type Task,
} from "./stellenwertbild/props";
export { made, solve, tuples } from "./stellenwertbild/tasks";
