// The Zahlzerlegung generator: numbers split into their place values (348 = 300 + 40 + 8, 3 H 4 Z 8 E) for Klasse 2
// to 4. A pure function of the block's settings and its seed, so that the editor, the thumbnail and the PDF draw the
// same tasks.
//
// The contract of #1078, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "zahlzerlegung", props: ZahlzerlegungProps }`.
// - `count` tasks (1 to 12, default 6) in `columns` side by side (1 to 3, default 2).
// - `max`, the Zahlenraum: 100, 1000 or 10000 (default 1000); any other value gives 1000. The places, highest first:
//   with 100 Z and E (values [10, 1]), with 1000 H, Z and E, with 10000 T, H, Z and E. k is their number (2, 3, 4).
//   Every number of a task has exactly k digits: 10^(k−1) ≤ n < max, its leading digit 1 to 9.
// - `task`, the Aufgabentyp (default "split"); d are n's digits per place, highest first:
//   - "split" Zerlegen: "348 = __ + __ + __", one gap per place, in place order; the key 300, 40, 8. A typed number
//     with a 0 place keeps that place's gap and the key writes 0 in it (306 = 300 + 0 + 6), so the number of gaps
//     never shows how many zeros there are.
//   - "join" Zusammensetzen: "400 + 30 + 5 = __", the parts in place order; the key n.
//   - "shuffled" Durcheinander: "8 + 400 + 50 = __", the parts in an order that is not the place order; the key n.
//   - "places" Stellenwerte: "3 H 7 Z 2 E = __"; a place whose digit is 0 is left out ("4 H 8 Z" for 480); tasks with
//     an even index (0, 2, ...) in place order, those with an odd index out of order ("8 Z 4 H") when two or more
//     places show; the key n.
//   - "gap" Lücke: "600 + __ + 4 = 674", the parts in place order, one of them a gap; the key that part.
//   - "zero" Stellen mit 0: "506 = __ H __ Z __ E", one gap per place, each for one digit; the key 5, 0, 6. Every gap
//     shows whatever the digit, so the gaps never give away how many zeros there are.
//   - "bundle" Bündeln (★★★): "4 H 12 Z 3 E = __", the counts c per place in place order, every place shown (zeros
//     too); the key n = Σ c·value.
// - `typed`: numbers the teacher typed, each entry [task 0 to 11, value 0 to 9999]. An entry that is not two whole
//   numbers in range is dropped; of two for the same task the last one stays; an entry of a task the block lacks
//   stays stored and plays no part.
// - A change of `max` in the panel drops `typed` in the same undo step. Varianten B to D drop `typed`, as for every
//   block. `seed` alone gives the drawn tasks.
//
// The rule every task keeps, drawn or typed (a "part" is a number d·10^j with d 1 to 9: a single place value):
// - "split", "join", "shuffled", "gap": n has k digits and no digit 0; its parts are its k place values, all > 0.
//   A typed "split" number needs k digits only; a 0 place gives the part 0.
// - "places": n has k digits; the places shown are those with d > 0, each with its digit 1 to 9 as count.
// - "zero": n has k digits and at least one digit 0 in a place that is not the first (506, 840, 70).
// - "bundle": counts c, one per place: the first 1 to 9, exactly one other place 10 to 19, the rest 0 to 9, and
//   n = Σ c·value < max (so 4 H 12 Z 3 E = 523; 9 H 12 Z is 1020 and never comes).
//
// The drawn tasks (`made`, memo of 50, `rng` from zahlenmauer.ts). P is the list of every candidate that keeps the
// rule (numbers n for every type but "bundle", count tuples for "bundle"), built by plain loops in rising order (for
// "bundle" the first place outermost, each count rising from 0, the first from 1, to 19); never by trying random
// numbers, so a drawn task never breaks a rule. P is never empty for any setting. Per task i, whatever is typed, so
// that the tasks after a typed one stay as they were, in this order:
// 1. up to 20 tries, each one draw P[floor(next() · |P|)]; a try whose n equals an earlier task's drawn n is dropped,
//    and after 20 tries the last one stays (a repeated number keeps every rule);
// 2. one draw r = next() for the order: with m parts shown, the m! orders in lexicographic order of the place indices
//    (index 0 the place order); "shuffled", and "places" at an odd index, take order 1 + floor(r · (m! − 1)) when
//    m ≥ 2, else the place order; every other type takes the place order;
// 3. one draw g = next() for the gap: "gap" takes the part at floor(g · m) in the shown order as the gap.
//
// Typed numbers win over the seed. A task with a typed entry v is the teacher's own and keeps its drawn order and gap
// draws. For every type but "bundle" it fits when v keeps the rule above; for "bundle" its counts are the drawn
// counts when their n is v, else the first tuple of the same plain walk whose n is v; none: it does not fit. A task
// whose v does not fit is `wrong`: it draws no number, on the pupils' sheet and in the key, only its signs and every
// number place as an empty gap (never a false number). `made` never fails: a setting always gives tasks (`none` is
// false; it is there for the shape the panel shares with the other blocks).
//
// The line of a task is `items(p, t)`: a list of items left to right, each { kind, x, w, text } with x and w in mm
// from the line's left. Kinds: "given" (a number the sheet shows, text its digits), "gap" (an empty box; text the
// answer the key writes in it, "" for a wrong task), "sign" ("+" or "="), "letter" (a place's letter T, H, Z or E).
// Widths: a number (given or gap) NW = 3 · k + 4 (10, 13, 16); a count (given or gap, before a letter) DW = 8; a
// letter LT = 5; a sign SW = 5. Every gap of a task that is not wrong has the same width in a block (NW, or DW with
// "zero"), so a gap never gives
// away its answer. The item lists:
// - "split": given n, "=", then per part a gap (NW), "+" between.  TW = NW + SW + k·NW + (k−1)·SW.
// - "join", "shuffled", "gap": per part a given (NW) or, at the gap of "gap", a gap (NW), "+" between, "=", then
//   given n ("gap") or a gap with n ("join", "shuffled").  TW = (k+1)·NW + k·SW.
// - "places": per shown place a given count (DW) and its letter (LT), then "=", a gap with n.
//   TW = k·(DW+LT) + SW + NW (the room of k places, whatever shows).
// - "zero": given n, "=", per place a gap with its digit (DW) and its letter.  TW = NW + SW + k·(DW+LT).
// - "bundle": per place a given count (DW) and its letter, "=", a gap with n.  TW = k·(DW+LT) + SW + NW.
// A wrong task has the items of the same type with every number a gap of its kind's width and text "", and the k
// places of the place order ("places" shows all k).
//
// Layout, in units (1 unit = 1 mm at scale 1): a task line is TW wide and LH = 8 high; tasks side by side CG = 10
// apart, rows RG = 5 apart; across = min(columns, count), rows = ceil(count / columns); vbW = across · TW + (across −
// 1) · CG + 1, vbH = rows · LH + (rows − 1) · RG + 1 (+1 for the stroke; the drawing sits at 0.5, 0.5). A new block
// is inserted at min(vbW, 180) wide; `heightFor(p, w)` is vbH · min(w / vbW, 1).
//
// The drawing (sheet/blocks/zahlzerlegung.tsx, on screen, in print and in the key alike): `div.zahlzerlegung` (with
// `.solved` in the key) holds one svg with viewBox 0 0 vbW vbH. Each task `g.task[data-task=i]` (class `wrong` when
// it holds) at x (i mod across) · (TW + CG), y floor(i / across) · (LH + RG), its items at their x:
// - "given": `text.given` (#222, size 5.5, centred in its width, baseline at 6);
// - "gap": `rect.gap` of w × 8, fill white, stroke #222 of 0.3; in the key its text as `text.answer` (centred, size 5.5)
//   when it is not "";
// - "sign": `text.eq` (#222, size 5.5, centred); "letter": `text.letter` (#222, size 5.5, centred).
// A whole number (an item NW wide) takes the sheet's place colours; a count before its letter does not.
//
// The panel (pages/Zahlzerlegung.tsx), whose words the tests take as selectors: steppers "Eine Aufgabe weniger" /
// "Eine Aufgabe mehr" ("6 Aufgaben", "1 Aufgabe"), "Weniger Aufgaben nebeneinander" / "Mehr Aufgaben nebeneinander"
// ("2 nebeneinander"); select "Zahlenraum" ("bis 100", "bis 1000", "bis 10 000"; a change drops `typed` in the same
// undo step); select "Aufgabentyp" with the options of TYPES; with 2 or more tasks select "Aufgabe" ("Aufgabe 1"
// ...), the task the field below sets; number field "Zahl" showing the task's n (the typed number for a wrong task), up to 4
// digits; it is one undo step per task (key `typed:i`), its text kept as a draft while it has focus; emptying it
// removes the task's entry. Hint (p.hint, role=status) per wrong task "Aufgabe i: Die Zahl passt nicht zu den
// Einstellungen.". Buttons "Eigene Zahlen entfernen" (with typed), "Neu würfeln" (changes only the seed). Every
// setting is one undo step.

export {
  DEFAULTS,
  PLACES,
  TYPES,
  heightFor,
  layout,
  placesOf,
  sane,
  widthFor,
  type Item,
  type Made,
  type Task,
  type ZahlzerlegungProps,
  type ZahlzerlegungTyped,
} from "./zahlzerlegung/props";
export { items, made } from "./zahlzerlegung/tasks";
