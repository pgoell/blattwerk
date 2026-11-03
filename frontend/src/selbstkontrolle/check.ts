// The answer key of a Selbstkontrolle: the linked blocks in sheet order, and what the child should find.
import type { Block, Doc } from "../sheet";
import { decimal } from "../decimal";
import { rng } from "../zahlenmauer";
import { sane, type Check, type Result, type SelbstkontrolleProps } from "./props";
import { shapeBox, type ShapeLook } from "./shape";
import { moneyOf, tasksOf, worded } from "./tasks";

const PT = 25.4 / 72; // mm per point


// Every block of the sheet with its page, in sheet order: page, then y, then x, then id.
const placed = (doc: Doc) => doc.pages.flatMap((pg, page) => pg.blocks.map((b) => ({ b, page })));
const inOrder = (x: { b: Block; page: number }, y: { b: Block; page: number }) =>
  x.page - y.page || x.b.y - y.b.y || x.b.x - y.b.x || (x.b.id < y.b.id ? -1 : x.b.id > y.b.id ? 1 : 0);

export function ordered(doc: Doc, ids: string[]): Block[] {
  const want = new Set(ids);
  return placed(doc).filter(({ b }) => want.has(b.id)).sort(inOrder).map(({ b }) => b);
}

const NAMES: Record<string, string> = {
  maths: "Rechnen",
  zahlenmauer: "Zahlenmauer",
  zahlenhaus: "Zahlenhaus",
  zahlenkette: "Zahlenkette",
  rechendreieck: "Rechendreieck",
  rechentabelle: "Rechentabelle",
  pfeilbild: "Pfeilbild",
  operatorfeld: "Operatorfeld",
  rechenrad: "Rechenrad",
  magischesquadrat: "Magisches Quadrat",
  malquadrat: "Malquadrat",
  zerlegungsfeld: "Zerlegungsfeld",
  halbschriftlich: "Halbschriftlich rechnen",
  zehnerfeld: "Zehnerfeld",
  textaufgabe: "Textaufgabe",
  diagramm: "Diagramm",
  zahlenstrahl: "Zahlenstrahl",
  hunderterfeld: "Hunderterfeld",
  uhr: "Uhr",
};

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

// `n` numbers that are not results, written as the linked blocks write theirs. The same seed gives the same ones.
function decoys(results: Result[], n: number, seed: number, decimals: number, money: boolean): string[] {
  if (n <= 0) return [];
  const taken = new Set(results.map((r) => r.text));
  const values = results.flatMap((r) => (r.value === undefined ? [] : [Math.abs(r.value)]));
  const euro = money ? " €" : "";
  const fmt = (v: number) => decimal(v, decimals, money) + euro;
  const pool: string[] = [];
  const cap = Math.max(40, ...(values.length ? values : [0])) + n + 30;
  for (let v = 0; v <= cap && pool.length < n * 4; v++) {
    const text = fmt(v);
    if (!taken.has(text)) pool.push(text);
  }
  return shuffle(pool, seed).slice(0, n);
}

export function checked(p: SelbstkontrolleProps, doc: Doc): Check {
  const q = sane(p);
  const all = new Set(doc.pages.flatMap((pg) => pg.blocks.map((b) => b.id)));
  const sources = ordered(doc, q.links);
  const tasks = sources.map((b) => tasksOf(b) ?? []);

  const real = tasks.flat().flat();
  let decimals = 0;
  let money = false;
  sources.forEach((b, i) => {
    if (!tasks[i].some((task) => task.some((r) => r.value !== undefined))) return;
    const [d, euro] = moneyOf(b);
    decimals = Math.max(decimals, d);
    money = money || euro;
  });
  const extra = q.form === "mixed" ? decoys(real, q.wrongs, q.seed, decimals, money) : [];
  const mixed = shuffle([...real.map((r) => r.text), ...extra], q.seed);

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
  else if (q.look === "snake" || q.look === "caterpillar" || q.look === "train") {
    const box = shapeBox(q.look as ShapeLook, c.mixed.length);
    const svg = c.mixed.length ? (w * box.h) / box.w : 0;
    return h * em + svg + 2;
  } else {
    // Items in rows: each as wide as its tick box, its text and the gap to the next, a row filled left to right.
    // A plain box has no tick.
    const tick = q.look === "box" ? 0 : 0.9 + 0.4;
    let rows = 0;
    let cur = 0;
    for (const t of c.mixed) {
      const iw = (tick + 0.6 * t.length + 1.2) * em;
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
