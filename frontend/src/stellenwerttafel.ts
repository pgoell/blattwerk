// The Stellenwerttafel mit Plättchen generator: numbers as dots (Plättchen) in the columns of a place-value table for
// Klasse 3 and 4. A pure function of the block's settings and its seed, so that the editor, the thumbnail and the PDF
// draw the same tasks.
//
// The contract of #1077, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "stellenwerttafel", props: StellenwerttafelProps }`.
// - `count` tasks (1 to 12, default 4) in `columns` side by side (1 to 4, default 2).
// - `max`, the Zahlenraum: 1000 or 10000 (default 1000); any other value gives 1000. The columns, highest first: with
//   1000 H, Z and E (values [100, 10, 1]), with 10000 T, H, Z and E. k is their number (3 or 4). The places come from
//   `PLACES` of zahlzerlegung.ts.
// - `task`, the Aufgabentyp: "read" Plättchen gegeben, Zahl schreiben (default): the table shows the dots, the pupil
//   writes the number; "lay" Zahl gegeben, Plättchen legen: the number shows, the table is empty, the pupil draws the
//   dots; "move" Ein Plättchen verschieben (PIKAS "Plättchen verschieben"): the table shows the dots, the pupil moves
//   one dot to another column and writes every number such a move makes.
// - `dots`, Plättchen: the most dots of a task, 1 to 36 (default 9); a wrong value gives 9. A task's dots are the sum
//   of its digits.
// - `zero`, Leere Stellen: false (default) every column of a drawn task holds at least one dot (every digit 1 to 9, so
//   n has k digits); true a column may be empty (a digit 0, a leading one too: 45 shows H empty).
// - `typed`: numbers the teacher typed, each entry [task 0 to 11, value 0 to 9999]. An entry that is not two whole
//   numbers in range is dropped; of two for the same task the last one stays; an entry of a task the block lacks
//   stays stored and plays no part.
// - A change of `max` in the panel drops `typed` in the same undo step. Varianten B to D drop `typed`, as for every
//   block. `seed` alone gives the drawn tasks.
//
// A task is its number n and its digits d (one per column, highest first; the dots of each column). The moves of a
// number: for every column i with d[i] ≥ 1 and every other column j with d[j] ≤ 8, the number with d[i] − 1 and
// d[j] + 1; they are all different, and `moves` lists them rising. A column never takes a tenth dot (no bundling);
// a column may end empty, whatever `zero` says (131 → 31).
//
// The rule every task keeps, drawn or typed: 1 ≤ n < max (at least one dot), the digit sum of n is at most `dots`,
// and with "move" n has at least one move (999 and 9999 have none). A drawn task keeps besides the rule `zero`.
// Typed numbers ignore `zero` (the teacher's number wins, as in Stellenwert-Bild): 306 fits with `zero` off too.
//
// The drawn tasks (`made`, memo of 50, `rng` from zahlenmauer.ts). P is the list of every n that keeps the rule and
// `zero`, built by one plain loop over n from 1 to max − 1 in rising order; never by trying random numbers, so a
// drawn task never breaks a rule. If P is empty (`zero` off and `dots` < k), `none` is true, no draws are made, and
// every task not the teacher's own is empty (no dot, no number, also in the key). Per task i, whatever is typed, so
// that the tasks after a typed one stay as they were: up to 20 tries, each one draw n = P[floor(next() · |P|)]; a try
// whose n equals an earlier task's drawn n is dropped, and after 20 tries the last one stays (a repeated number keeps
// every rule).
//
// Typed numbers win over the seed. A task with a typed entry v is the teacher's own: it fits when v keeps the rule
// (not `zero`); else it is `wrong`. A wrong task draws no dot, no number and no move, on the pupils' sheet and in the
// key: never a false number. Its table and boxes stay, empty.
//
// Layout, in units (1 unit = 1 mm at scale 1). The table: k columns CW = 16 wide; a head row HH = 6 (the letters) over
// a body row BH = 14; TBW = k · CW, TBH = HH + BH = 20. The dots of a column: slot q (0 to 8) at the centre x = column
// left + 4 + (q mod 3) · 4, y = body top + 3 + floor(q / 3) · 4, radius R = 1.4; a column of d dots fills slots 0 to
// d − 1.
// - "read" and "lay": right of the table the sign "=" in SW = 5, then the number box NB = 16 by 8, its middle at the
//   body's middle. TW = TBW + SW + NB, TH = TBH.
// - "move": under the table G = 3, the answer boxes: k − 1 rows of k boxes, each CW by 8 (under the table's columns),
//   rows 2 apart; that is k(k − 1) boxes (6 or 12, the most moves a number can have, so the boxes never tell how many
//   moves there are). TW = TBW, TH = TBH + G + (k − 1) · 8 + (k − 2) · 2.
// Tasks side by side CG = 8 apart, rows of tasks RG = 6 apart; across = min(columns, count), rows = ceil(count /
// columns); vbW = across · TW + (across − 1) · CG + 1, vbH = rows · TH + (rows − 1) · RG + 1 (+1 for the stroke; the
// drawing sits at 0.5, 0.5). A new block is inserted at min(vbW, 180) wide; `heightFor(p, w)` is vbH · min(w / vbW, 1).
//
// The drawing (sheet/blocks/stellenwerttafel.tsx, on screen, in print and in the key alike): `div.stellenwerttafel`
// (with `.solved` in the key) holds one svg with viewBox 0 0 vbW vbH. Each task `g.task[data-task=i]` (class `wrong`,
// class `none` as they hold) at x (i mod across) · (TW + CG), y floor(i / across) · (TH + RG).
// - The table `g.table`: per column a `text.head` letter (#222, size 4, centred in the head row) and a
//   `g.cell[data-v=value]` (a rect CW × BH, fill white, stroke #222 of 0.3), the head row framed alike.
// - The dots: `circle.dot[data-v=value]` of radius R, fill #222, in "read" and "move" on the sheet and in the key; in
//   "lay" only in the key, as `circle.dot.answer` in the Lösungsfarbe (#c0392b, var(--key)).
// - "read" and "lay": `text.eq` "=" (#222, size 5.5) and the number box `g.slot` (a rect NB × 8, stroke #222 of 0.3);
//   its number as `text.given` (#222, size 5.5) in "lay", as `text.answer` (#c0392b, size 5.5) in the key of "read".
//   Both in the sheet's place colours (SvgInk).
// - "move": each answer box `rect.box`; in the key, box b (row-major) holds the b-th move as `text.answer`.
// A wrong or empty task draws no dot, number or move; its table and boxes stay.
//
// The panel (pages/Stellenwerttafel.tsx), whose words the tests take as selectors: steppers "Eine Aufgabe weniger" /
// "Eine Aufgabe mehr" ("4 Aufgaben", "1 Aufgabe"), "Weniger Aufgaben nebeneinander" / "Mehr Aufgaben nebeneinander"
// ("2 nebeneinander"); select "Zahlenraum" ("bis 1000", "bis 10 000"; a change drops `typed` in the same undo step);
// select "Aufgabentyp" ("read" "Plättchen gegeben, Zahl schreiben", "lay" "Zahl gegeben, Plättchen legen", "move"
// "Ein Plättchen verschieben"); stepper "Weniger Plättchen" / "Mehr Plättchen" ("höchstens 9 Plättchen", "höchstens
// 1 Plättchen"), 1 to 36; checkbox "Leere Stellen"; with 2 or more tasks select "Aufgabe" ("Aufgabe 1" ...), the task
// the field below sets; number field "Zahl" showing the task's n (the typed number for a wrong task, empty for an
// empty task), up to 4 digits; it is one undo step per task (key `typed:i`), its text kept as a draft while it has
// focus; emptying it removes the task's entry. Hints (p.hint, role=status): with `none` "Mit diesen Einstellungen gibt
// es keine Aufgabe."; per wrong task "Aufgabe i: Die Zahl passt nicht zu den Einstellungen.". Buttons "Eigene Zahlen
// entfernen" (with typed), "Neu würfeln" (changes only the seed). Every setting is one undo step.

// The implementation adds `heightFor`, `layout`, `placesOf`, `sane`, `widthFor` from ./stellenwerttafel/props and
// `fits(p, v): boolean` (v keeps the rule), `moves(n, max): number[]` and `made(p): Made` from ./stellenwerttafel/tasks.
export { DEFAULTS, TASKS, type Made, type StellenwerttafelProps, type StellenwerttafelTyped, type Task } from "./stellenwerttafel/props";
