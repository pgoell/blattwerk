// The Zahlenstrahl: a line with an arrow head at the right, ticks, numbers under the ticks, and tasks on it. A pure
// function of the block's settings and its seed, so the editor, the thumbnail and the PDF draw the same line.
//
// The contract of #84, which the model, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "zahlenstrahl", props: ZahlenstrahlProps }`. All numbers are whole.
// - `start` and `end`: the numbers of the first and the last tick, 0 <= start < end <= 1000000 (default 0 and 20).
// - `minor`: the step of the small ticks, 1 up (default 1); `end - start` need not be a multiple: the last tick is
//   the last multiple of `minor` past `start` that is not above `end`.
// - `major`: the step of the long ticks, a multiple of `minor` (default 5). A tick is long when its number minus
//   `start` is a multiple of `major`. The first tick is always long.
// - `labels`: which ticks show their number: "all" every tick, "major" the long ones, "ends" the first and the last,
//   "none" none (default "major").
// - `size`: the numbers' font size in pt, 8 to 24 (default 12). It does not change with the block's size.
// - `cut`: a break mark (two short slanted strokes) across the line left of the first tick. Drawn only when
//   `start > 0` (default false).
// - `tasks`: "random" places `boxes` boxes and `arrows` arrows from the seed; "free" takes the ticks of `marks`
//   (default "random"). `boxes` 0 to 12 (default 3), `arrows` 0 to 6 (default 0).
// - `marks`: the ticks the teacher clicked, each `[number, "box" | "arrow"]`; only used with "free". An entry not on
//   a tick is kept in the props but not drawn.
// - `jumps`: jump arcs above the line from the first tick on, each `jump` wide (a multiple of `minor`, default
//   `major`), as many as fit before the last tick. `arcs` holds a label per arc by index; a missing or null entry
//   shows `+<jump>`. Default false.
// - `seed`: with the other props alone it gives the random tasks, so every draw gives the same ones.
//
// A box: the tick's number is hidden, a box stands under the tick for the pupil to write it in; the answer key
// writes the number into the box. An arrow: the number stands above the line, at a place of its own (the arrow
// numbers are spread evenly across the line in the order of `arrows` in `Made`), with a short stub under it; the
// pupil draws the arrow to the right tick. The answer key draws that arrow, from the stub to the tick.
//
// Random tasks: never on the first tick, never two on one tick; boxes first, on ticks that show no number where
// there are enough, then arrows on the ticks left. Fewer ticks than tasks: as many as there are ticks to take.
//
// The geometry, in mm from the block's top left; the svg's units are mm, so the drawing on screen and in print is
// the same to the tenth of a mm at any zoom:
// - The ticks spread exactly over the block's width less `LEFT` and `RIGHT`: tick i of n stands at `xOf(i, n, w)`.
//   The arrow head ends at `w - 1`. Widening the block widens the gaps; the numbers keep their size.
// - The line lies `BELOW` mm above the block's bottom. A long tick reaches 3 mm above and below it, a small one 1.5.
//   Numbers and boxes stand under it, arrows' numbers and arcs above it.
//
// The drawing, on screen and in print alike (`Draw` in sheet.tsx): `div.zahlenstrahl` (with `.solved` in the
// answer key) holds one `svg` with `viewBox="0 0 w h"`, w and h the block's mm. In it: `line.axis`, `path.head`,
// `g.cut` when the break mark shows, and per tick `g.tick[data-value=v]` (with class `long` for a long tick) that
// holds its `line`, its number as `text.label` (#222) when it shows one, and for a box `g.box` with a `rect` and in
// the answer key a `text.answer` (#c0392b) with the number. Per arrow `g.arrow[data-value=v]` with its number as
// `text.given` (#222) and its stub, and in the answer key a `path.answer` (#c0392b) to the tick. Per arc
// `g.arc[data-from=a][data-to=b]` with a `path` and a `text`. Numbers in Andika. The dock adds a block of 180 by 30 mm.
//
// The panel (pages/Zahlenstrahl.tsx), by aria-label: "Anfang", "Ende", "Schritt kleine Striche", "Schritt lange
// Striche" (number inputs), "Zahlen" (select: "all" Bei jedem Strich, "major" Bei langen Strichen, "ends" Anfang
// und Ende, "none" Keine), "Schriftgröße" (number input), "Bruchstelle" (checkbox, disabled while start is 0),
// "Aufgaben" (select: "random" Zufällig, "free" Selbst wählen); for "random": "Ein Kästchen weniger", "Ein Kästchen
// mehr", "Ein Pfeil weniger", "Ein Pfeil mehr", "Neu würfeln"; for "free": a button per tick, "Strich <v>", that
// cycles none, Kästchen, Pfeil, with `data-task` "box" or "arrow" when set; "Sprungbögen" (checkbox), and while on
// "Sprungweite" (number input) and a text input per arc, "Bogen <i>" from 1. A `p.hint.warn[role=status]` warns when
// `crowded(p, w)`. Each change is one undo step; typing into one field is one step.
//
// The props type lives here; sheet.tsx imports it (and draws the block), never the other way round but for types.

export type Task = "box" | "arrow";
export type Mark = [number, Task];
export type ZahlenstrahlProps = {
  start: number;
  end: number;
  minor: number;
  major: number;
  labels: "all" | "major" | "ends" | "none";
  size: number;
  cut: boolean;
  tasks: "random" | "free";
  boxes: number;
  arrows: number;
  marks?: Mark[];
  jumps: boolean;
  jump?: number;
  arcs?: (string | null)[];
  seed: number;
};

// A tick: its number, whether it is long, whether it shows its number, and the task on it.
export type Tick = { value: number; long: boolean; label: boolean; task?: Task };
// An arc from one tick's number to another's, with its label.
export type Arc = { from: number; to: number; label: string };
// `arrows`: the numbers of the arrow tasks in the order their numbers stand above the line, left to right.
export type Made = { ticks: Tick[]; arrows: number[]; arcs: Arc[] };

export const DEFAULTS: Omit<ZahlenstrahlProps, "seed"> = {
  start: 0,
  end: 20,
  minor: 1,
  major: 5,
  labels: "major",
  size: 12,
  cut: false,
  tasks: "random",
  boxes: 3,
  arrows: 0,
  jumps: false,
};
export const MAX = 1000000;
// More ticks than this are not drawn; the panel warns long before.
export const LIMIT = 2000;
// mm from the block's left edge to the first tick, and from the last tick to the block's right edge.
export const LEFT = 6;
export const RIGHT = 10;
// mm from the line to the block's bottom.
export const BELOW = 14;

// The x of tick i of n in a block w mm wide. One tick stands at LEFT.
export function xOf(i: number, n: number, w: number): number {
  return n < 2 ? LEFT : LEFT + (i * (w - LEFT - RIGHT)) / (n - 1);
}

// How many ticks the line has.
export function count(p: ZahlenstrahlProps): number {
  return Math.floor((p.end - p.start) / p.minor) + 1;
}

// Whether the ticks of a block w mm wide stand less than 1 mm apart.
export function crowded(p: ZahlenstrahlProps, w: number): boolean {
  const n = count(p);
  return n > 1 && (w - LEFT - RIGHT) / (n - 1) < 1;
}

// The settings as a Zahlenstrahl can take them, whatever a stored sheet holds: a value of the wrong kind or out of
// range gives its default (an `end` not above `start` gives `start + 20`; a `major` or `jump` that is no multiple of
// `minor` gives `minor * 5` and `major`), a `marks` entry that is not a whole number and a task is dropped, and of
// two for one number the last stays; an `arcs` entry that is not a string becomes null.
// PLACEHOLDER until the model is built: trusts the props.
export function sane(p: ZahlenstrahlProps): ZahlenstrahlProps {
  return { ...DEFAULTS, ...p };
}

// The ticks with their tasks, the arrow numbers in their order, and the arcs. No ticks above LIMIT.
// PLACEHOLDER until the model is built: the free marks only, the second tick a box when random.
export function made(p: ZahlenstrahlProps): Made {
  const n = count(p);
  if (n > LIMIT) return { ticks: [], arrows: [], arcs: [] };
  const free = new Map(p.tasks === "free" ? (p.marks ?? []) : []);
  const ticks = Array.from({ length: n }, (_, i): Tick => {
    const value = p.start + i * p.minor;
    const long = (value - p.start) % p.major === 0;
    const label = p.labels === "all" || (p.labels === "major" && long) || (p.labels === "ends" && (i === 0 || i === n - 1));
    const task = p.tasks === "free" ? free.get(value) : i === 1 && p.boxes > 0 ? "box" : undefined;
    return { value, long, label, ...(task && { task }) };
  });
  const arrows = ticks.filter((t) => t.task === "arrow").map((t) => t.value);
  const jump = p.jump ?? p.major;
  const arcs: Arc[] = [];
  if (p.jumps) for (let a = p.start, i = 0; a + jump <= ticks[n - 1].value; a += jump, i++) arcs.push({ from: a, to: a + jump, label: p.arcs?.[i] ?? `+${jump}` });
  return { ticks, arrows, arcs };
}
