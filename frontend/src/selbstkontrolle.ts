// The Selbstkontrolle: a block that a teacher links to maths blocks of the same sheet, so the child can check her own
// results. A pure function of its settings, its seed and the linked blocks as the sheet holds them, so it follows
// when a linked block rolls new tasks, changes its limits or prints as another variant, and the editor, the
// thumbnail and the PDF draw the same block.
//
// The contract of #89, which the model, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "selbstkontrolle", props: SelbstkontrolleProps }`. Nothing of a linked block is
// stored here but its id, and nothing of this block is stored in a linked block.
// - `form`: "mixed" Lösungen durcheinander, "word" Lösungswort, "sum" Kontrollsumme (default "mixed").
// - `links`: the ids of the linked blocks, in the order the teacher ticked them (default []). An id may name a block
//   of any page of the sheet. The order that counts is the sheet's (`ordered`), not this one.
// - `word`: the Lösungswort as typed (default ""). Only with "word".
// - `title`: the heading (default "Selbstkontrolle"); an empty one prints no heading.
// - `size`: the font size in pt of everything but the heading, 8 to 24 (default 14). The heading is 1.2 times it.
// - `turn`: "none", "upside" the whole content turned by 180 degrees, "fold" a dashed fold line along the block's
//   top with "Hier umknicken" over it and the content under it turned by 180 degrees, so the child folds it back
//   and reads it only when she turns the sheet (default "none").
// - `seed`: with the results alone it gives the shuffle of "mixed" and of the table of "word".
// Wrong kinds and values out of range give their default in `sane`, which never throws on any stored value.
//
// Results (`tasksOf`): a linked block's tasks in its own reading order, each task the list of what the child writes
// in, its key result first. A result is `{ text, value }`: `text` as the block prints it in the answer key, `value`
// the number for a sum, absent where there is none (a sign, a time).
// - "maths" (Rechenpäckchen, Rechnen in Zeilen, Lückenaufgaben, schriftlich, Vergleichen): one task per exercise,
//   one result: the part the gap hides (`hide`, the result when absent); with a rest the text "<q> R <r>" and the
//   value q (the rest is not added); a comparison gives its sign "<", ">" or "=" with no value. Decimals as
//   `decimal(n, decimalsOf(p), money)` prints them, with " €" for Geld, the value the number.
// - "zahlenmauer": one task per wall, its stones the child fills (not `given`), from the top row down and each row
//   left to right; so the key result is the highest empty stone. A wall that is `wrong`, or a block with `empty`,
//   gives no task (the key prints no answers there either).
// - "rechendreieck": one task per triangle, its fields the child fills in index order (0 to 5). A `wrong` triangle
//   or `empty` gives none.
// - "zahlenstrahl": one task per box (in `Made.ticks` order), the tick's number. An arrow is drawn, not written: no
//   result.
// - "hunderterfeld": one task per cell the child fills (Tafel: hidden cells; Ausschnitt: the cells of the shape but
//   the given one), in index order, the cell's number. Punkte: no task.
// - "uhr" with task "read": one task per clock, the time as `written` gives it, no value. With "draw": no task.
// - Any other block, or a missing one: undefined.
// `worded(b)` says whether a block's tasks take a letter box (form "word"): maths, zahlenmauer, rechendreieck and uhr.
// A Zahlenstrahl's boxes and a Hunderterfeld's cells sit in one drawing with no room beside each task, so the
// Lösungswort leaves them out (the panel says so beside them); "mixed" and "sum" take them.
//
// The check (`checked(p, doc)`):
// - `lost`: the ids of `links` that name no block of the sheet. While any is lost the block draws nothing in
//   print or in the answer key, and in the editor only the line "Die Selbstkontrolle hat ihre Quelle verloren."
// - `sources`: the linked blocks found, in sheet order (`ordered`: page, then y, then x, then id).
// - "mixed": `mixed`, the texts of every result of every source, as often as they occur, shuffled by `seed`.
// - "sum": `sums`, per source with at least one value, `[label, text]`: the label as `labelOf` gives it, the text
//   the sum of its values, printed as its results are (decimals, " €"). A source with results but no value (an
//   Uhr, comparisons) gives no line.
// - "word": the tasks are those of the worded sources in sheet order. `letters` maps each worded source's id to a
//   letter per task (the word's letter at that task's place, or "" while there is a fault). `table`: one
//   `[text, letter]` per distinct key result, shuffled by `seed`, when there is no fault. `fault`, the first that
//   holds, in German: no word typed "Gib ein Lösungswort ein.", the word's length (its letters, spaces left out,
//   upper case) not the task count "Das Wort hat <n> Buchstaben, die Aufgaben sind <m>.", two tasks with the same key
//   result and different letters "Aufgabe <i> und <j> haben dasselbe Ergebnis <text>, das Wort braucht dort <A> und
//   <B>." (tasks counted from 1 across the sources). Two different results may share a letter.
// - With no link: `empty` is true; the editor shows "Wähle rechts die Blöcke, die die Selbstkontrolle prüft." and
//   print shows nothing but the heading.
// `labelOf(b, doc)`: the block type's name ("Rechnen", "Zahlenmauer", "Rechendreieck", "Zahlenstrahl",
// "Hunderterfeld", "Uhr"), with " <n>" (1 up, sheet order) when the sheet has more than one block of that type.
//
// The drawing, on screen and in print alike (`Draw` in sheet.tsx): `div.selbstkontrolle` (with `.solved` in the
// answer key, `.upside` or `.fold` as `turn` says) holds `div.fold` (the dashed line and its words) with "fold",
// then `div.inner` (turned by 180 degrees with "upside" and "fold"), which holds `h3.title` when the title is not
// empty, then:
// - "mixed": `ul.mixed` with one `li` per result: `span.tick` (an empty square to tick) and the text.
// - "word": `table.word` of two rows, `tr.results` with one `td` per entry of `table` and `tr.letters` with its
//   letter; in the answer key a `p.answer` with the word in #c0392b under it.
// - "sum": `ul.sums` with one `li` per line, "<label>: <text>".
// - A fault, `lost` or `empty`: `p.hint` with its line in the editor only (print and the answer key leave it out).
// Text in Andika, at `size` pt; a content taller than the block shrinks its type to fit, as Rechnen does (`--fit`).
//
// Letter boxes: with "word", each task of a worded source gets an empty square for its letter, drawn by the source
// itself; in the answer key the letter stands in it
// in #c0392b. Each box has class `letter` and `data-task` i (from 0 within the source). Maths: a `span.letter` of
// 1.4 em after each exercise's text. Zahlenmauer: a square of one stone's height at the right end of the wall's top
// row. Rechendreieck: a square of the outer field's height at the top left of the triangle's cell. Uhr: a square
// of 14 units at (84, 2) of the clock's cell. None of them moves or covers what the block drew before, and a block
// that no "word" Selbstkontrolle links draws as before.
// The whole sheet reaches the drawing through `Whole`, a `createContext<Doc>` in sheet.tsx beside `Words`, provided
// in `Paper` and in the Editor's page (beside its `Words.Provider`). A source block reads `lettersOf(doc)` from it
// (memoised per doc) and draws its boxes only when its id is in the map. When two "word" Selbstkontrollen link one
// source, the first in sheet order gives its letters.
//
// Variants: variants.py gives the Selbstkontrolle a seed of its own per variant, as every seeded maths block. A
// variant's tasks differ from the stored ones, so a word that works on the stored sheet may fault on variant B: the
// Variants dialog names that block as a block the variant cannot fill (as for a Suchsel), and the variant prints the
// letter boxes empty and no table.
//
// The dock adds a block of 180 by 30 mm under "Mathe-Blöcke". The block grows downward when `form`, `links` or
// `word` change and its content needs more room (`heightFor`, a special case in the Editor's `grown` as the
// Zahlenstrahl's is, since it needs the doc), to the page's foot at most; it never shrinks by
// itself, and the teacher resizes it as a text block.
//
// The panel (pages/Selbstkontrolle.tsx), by aria-label: "Überschrift" (text input), "Form" (select: "mixed"
// Lösungen durcheinander, "word" Lösungswort, "sum" Kontrollsumme), for "word" "Lösungswort" (text input),
// "Schriftgröße" (number input), "Drucken" (select: "none" Normal, "upside" Auf dem Kopf, "fold" Mit Knicklinie),
// "Neu mischen" (button, a new seed; for "mixed" and "word"), and a checkbox per maths block of the sheet, in sheet
// order, labelled by `labelOf` (and " (Seite <n>)" when the sheet has more than one page): ticked when linked; a
// block not `worded` shows "(nicht im Lösungswort)" beside it with "word". A lost link shows as a ticked checkbox
// "Gelöschter Block" that unlinks it. `p.hint.warn[role=status]` shows the fault. Each change is one undo step;
// typing into one field is one step.
//
// The props type lives here; sheet.tsx imports it (and draws the block), never the other way round but for types.

import type { Block, Doc } from "./sheet";

export type Form = "mixed" | "word" | "sum";
export type Turn = "none" | "upside" | "fold";
export type SelbstkontrolleProps = { form: Form; links: string[]; word: string; title: string; size: number; turn: Turn; seed: number };

export const DEFAULTS: Omit<SelbstkontrolleProps, "seed"> = { form: "mixed", links: [], word: "", title: "Selbstkontrolle", size: 14, turn: "none" };

export type Result = { text: string; value?: number };
export type Check = {
  empty: boolean;
  lost: string[];
  sources: Block[];
  mixed: string[];
  sums: [string, string][];
  letters: Map<string, string[]>;
  table: [string, string][];
  fault?: string;
};

export function sane(p: SelbstkontrolleProps): SelbstkontrolleProps {
  void p;
  throw new Error("todo");
}

export function tasksOf(b: Block): Result[][] | undefined {
  void b;
  throw new Error("todo");
}

export const worded = (b: Block): boolean => b.type === "maths" || b.type === "zahlenmauer" || b.type === "rechendreieck" || b.type === "uhr";

export function ordered(doc: Doc, ids: string[]): Block[] {
  void doc, ids;
  throw new Error("todo");
}

export function labelOf(b: Block, doc: Doc): string {
  void b, doc;
  throw new Error("todo");
}

export function checked(p: SelbstkontrolleProps, doc: Doc): Check {
  void p, doc;
  throw new Error("todo");
}

// The letters of every block that a "word" Selbstkontrolle of the sheet links: id to a letter per task.
export function lettersOf(doc: Doc): Map<string, string[]> {
  void doc;
  throw new Error("todo");
}

export function heightFor(p: SelbstkontrolleProps, doc: Doc, w: number): number {
  void p, doc, w;
  throw new Error("todo");
}
