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
//   gives no task (the key prints no answers there either), nor does a wall with no empty stone.
// - "rechendreieck": one task per triangle, its fields the child fills in index order (0 to 5). A `wrong` triangle,
//   `empty` or a triangle with no empty field gives none.
// Each block's props but Rechnen's pass its own `sane` first, as its drawing does, so odd stored props give what the
// block draws. Rechnen has no `sane`: an exercise with neither a number in its gap nor a sign gives no task, and limits
// with no `ops` count as whole numbers.
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
// - With no link: `empty` is true; the editor shows "Wähle rechts unter „Blöcke“ die Blöcke, die die Selbstkontrolle
//   prüft.", or, when `bare` (no block of the sheet gives tasks yet), "Füge zuerst Aufgaben ein, dann wähle sie rechts
//   unter „Blöcke“.", and print shows nothing but the heading.
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
// Text in Andika, at `size` pt; a content taller or wider than the block shrinks its type to fit, as Rechnen does
// (`--fit`).
//
// Letter boxes: with "word", each task of a worded source gets an empty square for its letter, drawn by the source
// itself; in the answer key the letter stands in it
// in #c0392b. Each box has class `letter` and `data-task` i (from 0 within the source). Maths: a `span.letter` of
// 1.4 em after each exercise's text. Zahlenmauer: a square of 0.8 of a stone's height, 0.2 stones right of the top
// stone and level with its top, clear of every stone. Rechendreieck: a square of the outer field's height at the top left of the triangle's cell. Uhr: a square
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
// A Selbstkontrolle copied (paste, Ctrl+D, Seite duplizieren, Ctrl+drag) together with a block it links links that
// block's copy; copied alone it keeps its links.
//
// The dock adds a block of 180 by 30 mm under "Mathe-Blöcke". The block grows downward when `form`, `links`,
// `word`, `size`, `title` or `turn` change and its content needs more room (`heightFor`, a special case in the Editor's `grown` as the
// Zahlenstrahl's is, since it needs the doc), to the page's foot at most; it never shrinks by
// itself, and the teacher resizes it as a text block.
//
// The panel (pages/Selbstkontrolle.tsx), top to bottom: the heading, then the line "Die Kinder prüfen ihre Ergebnisse
// selbst: die Selbstkontrolle zeigt die Lösungen der Blöcke, die du unten wählst." (`p.hint`, panel only, not on the
// sheet), then the heading "Blöcke" with the choice: a lost link as a ticked checkbox "Gelöschter Block" that unlinks
// it, then a checkbox per maths block of the sheet, in sheet order, labelled by `labelOf` (and " (Seite <n>)" when the
// sheet has more than one page): ticked when linked; a block not `worded` shows "(nicht im Lösungswort)" beside it with
// "word". With no maths block and no lost link, the line "Auf dem Blatt ist noch kein Aufgabenblock. Füge zuerst
// Aufgaben ein: Rechnen, Zahlenmauer, Rechendreieck, Zahlenstrahl, Hunderterfeld oder Uhr." (`p.hint`). Then, by
// aria-label: "Überschrift" (text input), "Form" (select: "mixed"
// Lösungen durcheinander, "word" Lösungswort, "sum" Kontrollsumme), for "word" "Lösungswort" (text input),
// "Schriftgröße" (number input), "Drucken" (select: "none" Normal, "upside" Auf dem Kopf, "fold" Mit Knicklinie),
// "Neu mischen" (button, a new seed; for "mixed" and "word"). `p.hint.warn[role=status]` shows the fault. Each change is one undo step;
// typing into one field is one step.
//
// The props type lives here; sheet.tsx imports it (and draws the block), never the other way round but for types.

import type { Block, Doc } from "./sheet";
import { decimal, decimalsOf } from "./decimal";
import { at, rng, made as wallsOf, sane as saneWall } from "./zahlenmauer";
import { made as trianglesOf, sane as saneDreieck } from "./rechendreieck";
import { made as strahlOf, sane as saneStrahl } from "./zahlenstrahl";
import { made as feldOf, sane as saneFeld } from "./hunderterfeld";
import { sane as saneUhr, timesOf, written } from "./uhr";

const PT = 25.4 / 72; // mm per point

export type Form = "mixed" | "word" | "sum";
export type Turn = "none" | "upside" | "fold";
export type SelbstkontrolleProps = {
  /** How the child checks her results. "mixed": the results in a shuffled list, each with a box to tick. "word": a Lösungswort with a letter box under each task. "sum": one control sum per linked block. Default "mixed". */
  form: Form;
  /** Ids of the linked maths blocks of the sheet, in the order the teacher ticked them. Default none. */
  links: string[];
  /** The Lösungswort the child builds from the letters, as the teacher typed it. Used with form "word" only. Default "". */
  word: string;
  /** The heading of the block. An empty heading prints none. Default "Selbstkontrolle". */
  title: string;
  /** Font size of the text in pt, except the heading, which is 1.2 times it. Default 14.
   * @minimum 8
   * @maximum 24
   */
  size: number;
  /** Turns the block for the child to read it later. "none": not turned. "upside": the whole content turned by 180 degrees. "fold": a dashed fold line along the top, with "Hier umknicken" over it, and the content turned by 180 degrees under it, so the child folds it back. Default "none". */
  turn: Turn;
  /** Seed for the shuffle of form "mixed" and of the table of form "word". The same seed always gives the same order. */
  seed: number;
};

export const DEFAULTS: Omit<SelbstkontrolleProps, "seed"> = { form: "mixed", links: [], word: "", title: "Selbstkontrolle", size: 14, turn: "none" };

export type Result = { text: string; value?: number };
export type Check = {
  empty: boolean;
  /** No block of the sheet gives tasks yet, so the hint asks for them first. */
  bare: boolean;
  lost: string[];
  sources: Block[];
  mixed: string[];
  sums: [string, string][];
  letters: Map<string, string[]>;
  table: [string, string][];
  fault?: string;
};

const pick = <T extends string>(v: unknown, options: readonly T[], fallback: T): T => (options as readonly unknown[]).includes(v) ? (v as T) : fallback;

export function sane(p: SelbstkontrolleProps): SelbstkontrolleProps {
  const r = (p ?? {}) as unknown as Record<string, unknown>;
  return {
    form: pick(r.form, ["mixed", "word", "sum"] as const, DEFAULTS.form),
    links: Array.isArray(r.links) ? r.links.filter((id): id is string => typeof id === "string") : [],
    word: typeof r.word === "string" ? r.word : DEFAULTS.word,
    title: typeof r.title === "string" ? r.title : DEFAULTS.title,
    size: typeof r.size === "number" && r.size >= 8 && r.size <= 24 ? r.size : DEFAULTS.size,
    turn: pick(r.turn, ["none", "upside", "fold"] as const, DEFAULTS.turn),
    seed: Number.isSafeInteger(r.seed) ? (r.seed as number) : 0,
  };
}

export function tasksOf(b: Block): Result[][] | undefined {
  switch (b.type) {
    case "maths": {
      const p = b.props;
      const [d, money] = moneyOf(b);
      const euro = money ? " €" : "";
      // A client wrote the exercises: what is not a task with a number or a sign to find gives no result.
      const tasks = (Array.isArray(p.exercises) ? p.exercises : []).filter(
        (e) => !!e && typeof e === "object" && ("sign" in e || typeof e[e.hide ?? "result"] === "number"),
      );
      return tasks.map((e): Result[] => {
        if ("sign" in e) return [{ text: String(e.sign) }];
        if (e.rest > 0) return [{ text: `${decimal(e.result, d, money)}${euro} R ${decimal(e.rest, 0)}`, value: e.result }];
        const v = e[e.hide ?? "result"] as number;
        return [{ text: decimal(v, d, money) + euro, value: v }];
      });
    }
    case "zahlenmauer": {
      const p = saneWall(b.props);
      if (p.empty) return [];
      const out: Result[][] = [];
      for (const w of wallsOf(p).walls) {
        if (w.wrong) continue;
        const task: Result[] = [];
        for (let r = p.base - 1; r >= 0; r--) {
          for (let c = 0; c < p.base - r; c++) {
            const s = at(p.base, r, c);
            if (!w.given[s]) task.push({ text: String(w.numbers[s]), value: w.numbers[s] });
          }
        }
        if (task.length) out.push(task);
      }
      return out;
    }
    case "rechendreieck": {
      const p = saneDreieck(b.props);
      if (p.empty) return [];
      const out: Result[][] = [];
      for (const t of trianglesOf(p).triangles) {
        if (t.wrong) continue;
        const task: Result[] = [];
        t.numbers.forEach((n, j) => {
          if (!t.given[j]) task.push({ text: String(n), value: n });
        });
        if (task.length) out.push(task);
      }
      return out;
    }
    case "zahlenstrahl":
      return strahlOf(saneStrahl(b.props), b.w).ticks.filter((t) => t.task === "box").map((t) => [{ text: String(t.value), value: t.value }]);
    case "hunderterfeld": {
      const p = saneFeld(b.props);
      if (p.look === "punkte") return [];
      return feldOf(p).cells.filter((c) => c.drawn && !c.shown).map((c) => [{ text: String(c.value), value: c.value }]);
    }
    case "uhr": {
      const p = saneUhr(b.props);
      if (p.task !== "read") return [];
      return timesOf(p).map((t) => [{ text: written(t, p) }]);
    }
    default:
      return undefined;
  }
}

export const worded = (b: Block): boolean => b.type === "maths" || b.type === "zahlenmauer" || b.type === "rechendreieck" || b.type === "uhr";

// Every block of the sheet with its page, in sheet order: page, then y, then x, then id.
const placed = (doc: Doc) => doc.pages.flatMap((pg, page) => pg.blocks.map((b) => ({ b, page })));
const inOrder = (x: { b: Block; page: number }, y: { b: Block; page: number }) =>
  x.page - y.page || x.b.y - y.b.y || x.b.x - y.b.x || (x.b.id < y.b.id ? -1 : x.b.id > y.b.id ? 1 : 0);

export function ordered(doc: Doc, ids: string[]): Block[] {
  const want = new Set(ids);
  return placed(doc).filter(({ b }) => want.has(b.id)).sort(inOrder).map(({ b }) => b);
}

const NAMES: Record<string, string> = { maths: "Rechnen", zahlenmauer: "Zahlenmauer", rechendreieck: "Rechendreieck", zahlenstrahl: "Zahlenstrahl", hunderterfeld: "Hunderterfeld", uhr: "Uhr" };

export function labelOf(b: Block, doc: Doc): string {
  const name = NAMES[b.type] ?? b.type;
  const same = ordered(doc, placed(doc).filter(({ b: o }) => o.type === b.type).map(({ b: o }) => o.id));
  if (same.length < 2) return name;
  return `${name} ${same.findIndex((o) => o.id === b.id) + 1}`;
}

// A shuffle by seed: Fisher-Yates over the seeded generator of zahlenmauer.ts.
function shuffle<T>(xs: T[], seed: number): T[] {
  const out = [...xs];
  const r = rng(seed);
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// Decimals and " €" of a block's results, as its answer key prints them.
// Stored limits without `ops` (a client wrote them) count as whole numbers.
const moneyOf = (b: Block): [number, boolean] => {
  if (b.type !== "maths" || !Array.isArray(b.props.ops)) return [0, false];
  const d = decimalsOf(b.props);
  return [d, d > 0 && !!b.props.money];
};

export function checked(p: SelbstkontrolleProps, doc: Doc): Check {
  const q = sane(p);
  const all = new Set(doc.pages.flatMap((pg) => pg.blocks.map((b) => b.id)));
  const sources = ordered(doc, q.links);
  const tasks = sources.map((b) => tasksOf(b) ?? []);

  const mixed = shuffle(tasks.flat().flat().map((r) => r.text), q.seed);

  const sums: [string, string][] = [];
  sources.forEach((b, i) => {
    const values = tasks[i].flat().map((r) => r.value).filter((v): v is number => v !== undefined);
    if (!values.length) return;
    const [d, money] = moneyOf(b);
    sums.push([labelOf(b, doc), decimal(values.reduce((a, v) => a + v, 0), d, money) + (money ? " €" : "")]);
  });

  // One entry per worded task of the sheet, in sheet order: its block and its key result.
  const wordTasks: { id: string; text: string }[] = [];
  sources.forEach((b, i) => {
    if (worded(b)) for (const task of tasks[i]) wordTasks.push({ id: b.id, text: task[0].text });
  });
  const L = Array.from(q.word.replace(/\s/g, "").toUpperCase());
  const N = wordTasks.length;
  let fault: string | undefined;
  if (q.form !== "word") fault = undefined;
  else if (q.word.trim() === "") fault = "Gib ein Lösungswort ein.";
  else if (L.length !== N) fault = `Das Wort hat ${L.length} Buchstaben, die Aufgaben sind ${N}.`;
  else {
    for (let j = 0; j < N && !fault; j++) {
      for (let i = 0; i < j && !fault; i++) {
        if (wordTasks[i].text === wordTasks[j].text && L[i] !== L[j]) {
          fault = `Aufgabe ${i + 1} und ${j + 1} haben dasselbe Ergebnis ${wordTasks[j].text}, das Wort braucht dort ${L[i]} und ${L[j]}.`;
        }
      }
    }
  }

  const letters = new Map<string, string[]>();
  const table: [string, string][] = [];
  if (q.form === "word") {
    wordTasks.forEach((t, k) => {
      const a = letters.get(t.id) ?? [];
      a.push(fault ? "" : L[k]);
      letters.set(t.id, a);
      if (!fault && !table.some(([x]) => x === t.text)) table.push([t.text, L[k]]);
    });
  }

  return {
    empty: q.links.length === 0,
    bare: !placed(doc).some(({ b }) => tasksOf(b) !== undefined),
    lost: q.links.filter((id) => !all.has(id)),
    sources,
    mixed,
    sums,
    letters,
    table: shuffle(table, q.seed),
    fault,
  };
}

// The letters of every block that a "word" Selbstkontrolle of the sheet links: id to a letter per task.
// Each "word" block in sheet order; a source an earlier one took keeps its letters, and a block with a lost link
// prints nothing, so it gives no boxes. Kept per doc: every source block asks on each draw.
const lettered = new WeakMap<Doc, Map<string, string[]>>();
export function lettersOf(doc: Doc): Map<string, string[]> {
  const known = lettered.get(doc);
  if (known) return known;
  const out = new Map<string, string[]>();
  for (const { b } of placed(doc).sort(inOrder)) {
    if (b.type !== "selbstkontrolle" || b.props?.form !== "word") continue;
    const c = checked(b.props, doc);
    if (c.lost.length) continue;
    for (const [id, letters] of c.letters) if (!out.has(id)) out.set(id, letters);
  }
  lettered.set(doc, out);
  return out;
}

// The height in mm the content needs at width `w` mm: a line is 1.2 times the size in points.
export function heightFor(p: SelbstkontrolleProps, doc: Doc, w: number): number {
  const q = sane(p);
  const c = checked(q, doc);
  // In em of the size, as styles.css lays it: lines of 1.3, a heading of 1.2 em with .3 em under it, the fold line's
  // words at .8 em, a table cell of a line with .3 em padding, the box of the mixed list .4 em inside and .3 em between
  // its rows.
  const em = q.size * PT;
  // A lost link draws nothing, a faulty word only its heading: the block grows for what it draws.
  if (c.lost.length) return 2;
  let h = (q.title ? 1.2 * 1.3 + 0.3 : 0) + (q.turn === "fold" ? 0.8 * 1.3 : 0);
  if (q.form === "sum") h += c.sums.length * 1.3;
  // Two table rows, and room for the key's word under them (1.4 em on a line of 1.3, .3 em above), so the key
  // keeps the sheet's type size.
  else if (q.form === "word") h += c.fault ? 0 : 2 * 1.6 + 1.4 * 1.3 + 0.3;
  else {
    // Items in rows: each as wide as its tick box, its text and the gap to the next, a row filled left to right.
    let rows = 0;
    let cur = 0;
    for (const t of c.mixed) {
      const iw = (0.9 + 0.4 + 0.6 * t.length + 1.2) * em;
      if (rows === 0 || cur + iw > w - 1.2 * em) {
        rows++;
        cur = 0;
      }
      cur += iw;
    }
    h += rows * 1.3 + Math.max(0, rows - 1) * 0.3 + 0.8;
  }
  return h * em + 2;
}
