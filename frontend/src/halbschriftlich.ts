// The Halbschriftlich generator: semi-written addition and subtraction. The second number is added (or taken away)
// place by place, the highest place first: 345 + 123 is 345 + 100 = 445, 445 + 20 = 465, 465 + 3 = 468. A pure
// function of the block's settings and its seed, so that the editor, the thumbnail and the PDF draw the same tasks.
//
// The contract of #828, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "halbschriftlich", props: HalbschriftlichProps }`.
// - `count` tasks (1 to 12, default 6) in `columns` side by side (1 to 3, default 2).
// - `op`, the Rechenart: "+" (Plus, default) or "-" (Minus). The sheet shows "+" or "−" (U+2212).
// - `max`, the Zahlenraum of the first number and the result: 100 or 1000 (default 1000; any other value gives 1000).
// - `digits`, the places of the second number: 1, 2 or 3 (default 3; any other value gives the default). A drawn second
//   number has exactly that many digits (2: 10 to 99). 3 counts only with max 1000; with max 100 it acts as 2 (and
//   stays stored).
// - `einer`, the Übergang (Übertrag) at the Einer, crossing a ten: "any" (default), "yes" or "no". `zehner`, the
//   Übergang at the Zehner, crossing a hundred: the same values. `zehner` counts only with max 1000 (any digits: 395 + 7
//   crosses a hundred too); with max 100 it acts as "any" (and stays stored). Any other value gives "any".
// - `grid`, Karo: true (default) draws the 5 mm squares behind the tasks; false draws plain white with a box per number.
// - `head`, Stellenwerte: false (default); true draws a row of place letters (T H Z E) above each task's numbers.
// - `tint`: false (default); true tints the second number and its parts in the steps.
// - `ops`: true (default) prints the step lines' signs ("+" or "−" and "=") on the pupils' sheet; false leaves them out
//   there, so the pupils write them (the slots stay). The key always shows the full steps.
// - `typed`: numbers the teacher typed, each entry [task from 0, position 0 to 2, value 0 to 9999]. The positions: 0 the
//   first number a, 1 the second number b, 2 the result r. An entry that is not three whole numbers, or whose task is
//   not 0 to 11, position not 0 to 2 or value not 0 to 9999, is dropped; of two for the same task and position the last
//   one stays. An entry of a task the block does not have (after fewer tasks) stays stored and plays no part.
// - `seed` alone gives the drawn tasks.
//
// The steps of a task (a, b): one step per digit of b that is not 0, the highest place first. The part of a step is
// that digit times its place value (b = 305 gives the parts 300 and 5). Step j goes from s(j) to s(j + 1), with s(0) = a,
// s(j + 1) = s(j) + part j for Plus and s(j) − part j for Minus; the last s is r. So 345 + 103 has two steps.
//
// The rule every task keeps, drawn or typed: a ≥ 1, b ≥ 1; Plus r = a + b ≤ 9999; Minus r = a − b ≥ 0.
// The Übergang at place p (p = 0 the Einer, 1 the Zehner) is the Übertrag of written arithmetic out of place p: the task
// crosses a multiple of 10^(p+1) in some step. With m = 10^(p+1): Plus crosses exactly when (a mod m) + (b mod m) ≥ m;
// Minus exactly when (a mod m) < (b mod m). So a carry that runs on counts at every place it reaches: 385 + 17
// (385 + 10 = 395, 395 + 7 = 402) and 395 + 7 cross a hundred, and "Übergang bei den Zehnern: ohne" never gives them.
// "yes" needs the crossing, "no" forbids it.
//
// The drawn tasks (`made`, memo of 50, `rng` from zahlenmauer.ts). The drawn task keeps, besides the rule: a ≤ max,
// b has exactly k digits (k = `digits` as it acts), Plus r ≤ max, and the `einer` and `zehner` rules as they act.
// For each a from 1 to max let n(a) be the count of b that fit with a. A is the list of a with n(a) ≥ 1, in rising order.
// The lists are computed exactly (a plain walk of every a and every b of k digits), never by trying random tasks, so a
// drawn task never breaks a rule. If A is empty, no task fits the settings: `none` is true, no draws are made, every
// task not the teacher's own is empty (no given number, no answer, also in the key).
// Per task i, every draw in this order whatever is typed, so that the tasks after a typed one stay as they were: up to
// 20 tries, each one draw a = A[floor(next() · |A|)] and then one draw for b, the floor(next() · n(a))-th b (from 0)
// that fits with a in rising order; a try whose (a, b) equals an earlier task's drawn (a, b) is dropped, and after 20
// tries the last one stays (a repeated task keeps every rule).
// A drawn task gives a and b; the pupil writes r and the steps.
//
// Typed numbers win over the seed. A task with at least one typed entry is the teacher's own: exactly its typed
// positions are given, the drawn ones are not. The panel, at the first number typed into a task, stores that task's
// drawn given positions (a and b) as typed entries with it, so that nothing the sheet showed goes away (not when `none`).
// A teacher's own task is worked out by `solve` from its typed positions alone against the rule alone (`max`, `digits`,
// `einer` and `zehner` only steer the draw), exactly, by counting with no search budget: any two of a, b, r fix the
// task (one solution or none); one alone gives a count (a typed: Plus b from 1 to cap − a, Minus b from 1 to a; b
// typed: Plus a from 1 to cap − b, Minus a from b to cap; r typed: Plus a from 1 to r − 1, Minus a from r + 1 to cap),
// which can be 0, 1 (Minus a = 1, Plus r = 2) or more. No solution: `wrong`. One: the task's values and steps. Two or more: `many`, the values shown are the drawn task's
// when it fits the typed numbers, else the solution of the smallest a and then the smallest b; the key says "Auch andere
// Lösungen sind richtig." and the panel "Es gibt mehr als eine Lösung.". A wrong task shows its typed numbers on the
// pupils' sheet; the other boxes stay empty, also in the key: never a false number.
//
// Layout, in squares of Q = 5 units (1 unit = 1 mm at the default scale, so Karo is 5 mm): a number column is D = 4
// squares wide always (every value is 0 to 9999, so the width never changes with the numbers). A task line is the columns [number D][sign 1][number D][= 1][number D]: TW = (3 · D + 2) · Q wide. A digit sits in its
// own square, the number right-aligned in its column. S = the most steps of any task, at least k. A task's rows top
// down: with `head` one row of place letters, then the task line (row of line 0), then S step lines (line j + 1 is step
// j), then one note row (room for the key's note, so the key and the sheet have the same height): TH = (head ? 1 : 0)
// + 1 + S + 1 squares. Tasks side by side CG = Q apart, rows of tasks RG = Q apart; vbW = across · TW + (across − 1) ·
// CG + 1, vbH = rows · TH + (rows − 1) · RG + 1 (+1 for the stroke; the drawing sits at 0.5, 0.5).
// The default block is drawn at scale 1 (Karo 5 mm), inserted at its vbW wide; a narrower block scales down, a wider
// one stays at scale 1.
//
// The drawing (sheet.tsx `Halbschriftlich`, on screen, print and in the key alike): `div.halbschriftlich` holds one svg.
// With `grid`, `g.karo` draws the square lines over the whole viewBox (stroke #9fb4c8, 0.15). Each task
// `g.task[data-task=i]` (class `wrong`, class `many`, class `none` for an empty drawn task when `none`). A number slot is
// `g.slot[data-line=l][data-pos=p]` (line 0 the task: p 0 a, 1 b, 2 r; line j + 1 step j: p 0 s(j), 1 part j, 2 s(j+1)):
// without `grid` a white rect with stroke #222 of 0.3 around its D squares; with `tint` the slots of p 1 have a
// `rect.tint` fill #9cc3f5 at fill-opacity 0.35 under the digits (see-through, so the Karo squares show); the digits as one `text` per slot (class `given` in #222, in the key an
// empty position class `answer` in #c0392b), letter-spaced so that each digit sits in its square, size Q · 0.75.
// Every drawn line has `text.op` ("+" or "−") in its sign square and `text.eq` ("=") in its = square.
// Line 0 draws with its signs (an empty task under `none` without them). Step lines on the pupils' sheet: the task's own
// steps (S lines for a wrong task, an empty one, or one with many answers, room for any of them), each with its empty slots, and with `ops` also its `text.op` and `text.eq`; `ops` changes only the
// signs. In the key: the task's own steps with their signs and every number as `answer`; a wrong or empty task's key
// is its pupils' sheet. With `none` the sheet shows no words for it: the empty tasks stay blank, the panel says why. With `head`
// `text.head` letters ("E", "Z", "H", "T" from the right) in #555, size Q · 0.6, over each of the three number columns.
// In the key a task with `many` and not wrong has `text.note` "Auch andere Lösungen sind richtig." in its note row.
//
// The panel (pages/Halbschriftlich.tsx), whose words the tests take as selectors: steppers "Eine Aufgabe weniger" /
// "Eine Aufgabe mehr" ("6 Aufgaben", "1 Aufgabe"), "Weniger Aufgaben nebeneinander" / "Mehr Aufgaben nebeneinander"
// ("2 nebeneinander"); select "Rechenart" ("Plus", "Minus"; a change drops `typed` in the same undo step); select
// "Zahlenraum" ("bis 100", "bis 1000"); select "Stellen der zweiten Zahl" ("einstellig", "zweistellig", with bis 1000
// also "dreistellig"; it shows k as it acts, so a stored 3 with bis 100 reads "zweistellig"; a choice stores its number); select "Übergang bei den Einern" ("egal", "mit Übergang", "ohne Übergang"); with bis 1000
// select "Übergang bei den Zehnern" (the same words); checkboxes "Karo", "Stellenwerte
// zeigen", "Zweite Zahl färben", "Rechenzeichen der Schritte drucken"; select "Aufgabe für eigene Zahlen" (with 2 or
// more tasks, "Aufgabe 1" ...); number fields "Erste Zahl", "Zweite Zahl", "Ergebnis" showing the given numbers (typed or
// drawn), the other fields empty; each field is one undo step (key `typed:i:p`). Hints (p.hint, role=status): with
// `none` "Mit diesen Einstellungen gibt es keine Aufgabe."; per wrong task "Aufgabe i: Die Zahlen passen nicht
// zusammen."; per task with many and not wrong "Aufgabe i: Es gibt mehr als eine Lösung." Buttons "Eigene Zahlen
// entfernen" (with typed), "Neu würfeln" (changes only the seed). Every setting is one undo step.

export {
  DEFAULTS,
  MAXES,
  NAMES,
  acts,
  opLabel,
  sane,
  type HalbschriftlichProps,
  type HalbschriftlichTyped,
  type Made,
  type Rule,
  type Task,
} from "./halbschriftlich/props";
export { heightFor, layout, made, solve, steps, widthFor, type Solved } from "./halbschriftlich/draw";
