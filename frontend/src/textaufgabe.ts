// The Textaufgaben generator: a short story, a question, a Rechnung on Karo and an Antwort line.
// A pure function of the block's settings and its seed, so the editor, the thumbnail and the PDF
// draw the same tasks.
//
// The contract of #832, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "textaufgabe", props: TextaufgabeProps }`.
// - `count` tasks (1 to 4, default 2), one under the other.
// - `themes`: kurze Texte ("kurz"), Sachaufgaben ("sach"), Rätsel ("raetsel"), Zeit ("zeit"), Geld ("geld").
// - `ops` the Rechenarten, `steps` 1 or 2, `max` the Zahlenraum (10, 20, 100, 1000).
// - `numbers` "whole" or "decimal" (Kommazahlen). Geld is always cents. A Zeit stays a clock.
// - `carry` the Übertrag: "any", "yes" or "no". A ten, or a euro for cents. Mal and Geteilt ignore it.
// - `frage`, `rechnung`, `antwort`: shown to the pupil, or left blank. The Lösungen fill a blank part.
//   The story is always shown.
// - `sketch` draws a box above the Rechnung. `rows` is "auto" or the Rechnung's rows (1 to 8).
// - `manual` with `written`: the teacher edits Text, Frage, Rechnung and Antwort.
// - `zeit` picks Zeitpunkte, Dauern or both. `seed` picks the story and the numbers. Neu würfeln
//   changes the seed.
//
// The drawing (`div.textaufgabe`): one `article.task` per task, `p.text`, `p.frage`, an optional
// `div.sketch`, `div.rechnung` on 5 mm Karo, and `p.antwort`. A part the Lösungen fill has `span.answer`.

export { DEFAULTS, OPS, THEMES, heightFor, layout, rechnungRows, sane, visible, type Carry, type TextOp, type Part, type TextaufgabeProps, type TextaufgabeWritten, type Theme } from "./textaufgabe/props";
export { made, type Kind, type Made, type Step, type Task } from "./textaufgabe/make";
export { STORIES, type Story } from "./textaufgabe/pool";
