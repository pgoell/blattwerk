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
// numbers are spread evenly across the line in the order of `arrows` in `Made`, each over the middle of a gap
// between two ticks), with a short stub under it; the
// pupil draws the arrow to the right tick. The answer key draws that arrow, from the stub to the tick.
//
// Random tasks: never on the first tick, never two on one tick; boxes first, on ticks that show no number where
// there are enough, then arrows on the ticks left. Two boxes never overlap: a tick whose box would clash with one
// already chosen is passed over, so a close line gets fewer boxes. Fewer ticks than tasks: as many as there are ticks to take.
//
// The geometry, in mm from the block's top left; the svg's units are mm, so the drawing on screen and in print is
// the same to the tenth of a mm at any zoom:
// - The ticks spread exactly over the block's width less `LEFT` and `RIGHT`: tick i of n stands at `xOf(i, n, w)`.
//   The arrow head ends at `w - 1`. Widening the block widens the gaps; the numbers keep their size.
// - The line lies `below(p, w)` mm above the block's bottom, `BELOW` at least, more when a box hangs lower. A long
//   tick reaches 3 mm above and below it, a small one 1.5.
//   Numbers and boxes stand under it, arrows' numbers and arcs above it. A box that would cover a number shown
//   beside it stands one row lower, a thin line from its tick down to it. An arrow's stub ends 2 mm above the ticks.
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

import { rng } from "./zahlenmauer";

/** A task on a tick: "box" an empty box to write the number in, "arrow" an arrow to draw to the tick. */
export type Task = "box" | "arrow";
/** A tick the teacher picked in "free" mode: [the tick's number, its task]. */
export type Mark = [number, Task];
export type ZahlenstrahlProps = {
  /** The number of the first tick, from 0 up. The line starts here. Default 0.
   * @minimum 0
   * @maximum 999999
   */
  start: number;
  /** The number of the last tick, above `start`. The last tick is the last multiple of `minor` that is not above it. Default 20.
   * @minimum 0
   * @maximum 1000000
   */
  end: number;
  /** The step between two ticks (small ticks), in whole numbers. Default 1.
   * @minimum 1
   * @maximum 1000000
   */
  minor: number;
  /** The step between two long ticks. A multiple of `minor`. A tick is long when its number minus `start` is a multiple of it. The first tick is always long. Default 5. */
  major: number;
  /** Which ticks show their number. "all": every tick. "major": the long ticks. "ends": the first and the last tick. "none": no tick. Default "major". */
  labels: "all" | "major" | "ends" | "none";
  /** Font size of the numbers, in pt. Does not change with the block's size. Default 12.
   * @minimum 8
   * @maximum 24
   */
  size: number;
  /** Draws a break mark (two short slanted strokes) left of the first tick. Only shown when `start` is above 0. Default false. */
  cut: boolean;
  /** "random": boxes and arrows go on ticks chosen from the seed. "free": the ticks in `marks` get their task. Default "random". */
  tasks: "random" | "free";
  /** Number of boxes placed on the line with `tasks` "random". Default 3.
   * @minimum 0
   * @maximum 12
   */
  boxes: number;
  /** Number of arrows placed on the line with `tasks` "random". Default 0.
   * @minimum 0
   * @maximum 6
   */
  arrows: number;
  /** The ticks picked in "free" mode, each [number, "box" or "arrow"]. An entry that is not a tick is kept but not drawn. */
  marks?: Mark[];
  /** Draws jump arcs above the line, from the first tick on. Default false. */
  jumps: boolean;
  /** Width of each jump arc, a multiple of `minor`. Default `major`. */
  jump?: number;
  /** A text for each jump arc, by index. A missing or empty entry shows "+" and the jump width. */
  arcs?: (string | null)[];
  /** Seed for the random tasks. The same seed always gives the same tasks. */
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
export const BELOW = 18;

// The x of tick i of n in a block w mm wide. One tick stands at LEFT.
export function xOf(i: number, n: number, w: number): number {
  return n < 2 ? LEFT : LEFT + (i * (w - LEFT - RIGHT)) / (n - 1);
}

// The x of each of k arrow numbers among n ticks in a block w mm wide: the even spot, moved to the middle of the
// nearest gap between two ticks, each gap used once, left to right. With fewer gaps than arrows (free tasks can set
// an arrow on every tick), the even spot, so no two numbers stand on one place.
export function arrowXs(k: number, n: number, w: number): number[] {
  if (k === 0) return [];
  const span = w - LEFT - RIGHT;
  const even = Array.from({ length: k }, (_, i) => ((i + 1) * (n - 1)) / (k + 1));
  if (n < 2 || k > n - 1) return Array.from({ length: k }, (_, i) => LEFT + ((i + 1) * span) / (k + 1));
  // The nearest gap; a tie (the spot on a tick) takes the lower gap.
  const gap = even.map((t) => {
    const u = t - 0.5;
    const g = u - Math.floor(u) === 0.5 ? Math.floor(u) : Math.round(u);
    return Math.min(n - 2, Math.max(0, g));
  });
  for (let i = 1; i < k; i++) gap[i] = Math.max(gap[i], gap[i - 1] + 1);
  gap[k - 1] = Math.min(gap[k - 1], n - 2);
  for (let i = k - 2; i >= 0; i--) gap[i] = Math.min(gap[i], gap[i + 1] - 1);
  return gap.map((g) => xOf(g + 0.5, n, w));
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

// The width in mm of a box for the number `value` at `size` pt.
export function boxWidth(value: number, size: number): number {
  return Math.max(8, 3 + String(value).length * 0.6 * ((size * 25.4) / 72));
}

// The box under tick i of a line in a block w mm wide with numbers `size` pt: its x, its width and height, its top
// `dy` mm below the line, and whether it is lowered over a number shown beside it. The drawing and `below` share it.
export function boxUnder(ticks: Tick[], i: number, w: number, size: number) {
  const FS = (size * 25.4) / 72;
  const x = xOf(i, ticks.length, w);
  const bw = boxWidth(ticks[i].value, size);
  const bh = Math.max(6, 1.6 * FS);
  const covers = ticks.some((o, j) => o.label && !o.task && j !== i && Math.abs(xOf(j, ticks.length, w) - x) < bw / 2 + (String(o.value).length * 0.55 * FS) / 2 + 0.5);
  return { x, bw, bh, covers, dy: covers ? 5 + 1.35 * FS + 0.5 : 3.5 };
}

// The mm the line lies above the block's bottom: `BELOW`, or lower when a box or a number under the line reaches
// further down, with half a mm to spare. `p` is already sane.
export function below(p: ZahlenstrahlProps, w: number): number {
  const { ticks } = made(p, w);
  const FS = (p.size * 25.4) / 72;
  let low = BELOW;
  if (ticks.some((t) => t.label && !t.task)) low = Math.max(low, 5 + 1.55 * FS + 0.5);
  ticks.forEach((t, i) => {
    if (t.task === "box") {
      const b = boxUnder(ticks, i, w, p.size);
      low = Math.max(low, b.dy + b.bh + 0.5);
    }
  });
  return low;
}

// The settings as a Zahlenstrahl can take them, whatever a stored sheet holds: a value of the wrong kind or out of
// range gives its default (an `end` not above `start` gives `start + 20`; a `major` or `jump` that is no multiple of
// `minor` gives `minor * 5` and `major`), a `marks` entry that is not a whole number and a task is dropped, and of
// two for one number the last stays; an `arcs` entry that is not a string becomes null.
export function sane(p: ZahlenstrahlProps): ZahlenstrahlProps {
  const r = (p ?? {}) as unknown as Record<string, unknown>;
  const start = whole(r.start, 0, MAX - 1, DEFAULTS.start);
  const given = whole(r.end, 0, MAX, DEFAULTS.end);
  const end = given > start ? given : Math.min(start + 20, MAX);
  const minor = whole(r.minor, 1, MAX, DEFAULTS.minor);
  const major = multipleOf(r.major, minor) ? (r.major as number) : minor * 5;
  const jump = multipleOf(r.jump, minor) ? (r.jump as number) : undefined;
  const marks = new Map<number, Task>();
  if (Array.isArray(r.marks))
    for (const m of r.marks) if (Array.isArray(m) && isWhole(m[0]) && (m[1] === "box" || m[1] === "arrow")) marks.set(m[0], m[1]);
  return {
    start,
    end,
    minor,
    major,
    labels: pick(r.labels, ["all", "major", "ends", "none"] as const, DEFAULTS.labels),
    size: whole(r.size, 8, 24, DEFAULTS.size),
    cut: typeof r.cut === "boolean" ? r.cut : DEFAULTS.cut,
    tasks: pick(r.tasks, ["random", "free"] as const, DEFAULTS.tasks),
    boxes: whole(r.boxes, 0, 12, DEFAULTS.boxes),
    arrows: whole(r.arrows, 0, 6, DEFAULTS.arrows),
    marks: [...marks],
    jumps: typeof r.jumps === "boolean" ? r.jumps : DEFAULTS.jumps,
    jump,
    arcs: Array.isArray(r.arcs) ? r.arcs.map((a) => (typeof a === "string" ? a : null)) : undefined,
    seed: isWhole(r.seed) ? r.seed : 0,
  };
}

const isWhole = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v);
const whole = (v: unknown, lo: number, hi: number, dflt: number): number => (isWhole(v) && v >= lo && v <= hi ? v : dflt);
const pick = <T extends string>(v: unknown, list: readonly T[], dflt: T): T => list.find((x) => x === v) ?? dflt;
// A whole positive number that `of` divides.
const multipleOf = (v: unknown, of: number): boolean => isWhole(v) && v >= 1 && v % of === 0;

// Shuffled with `rnd`, the input left as it is.
function shuffle<T>(xs: T[], rnd: () => number): T[] {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// The random boxes first, on ticks that show no number where there are enough, then the arrows, on the ticks left.
// Never the first tick.
function placeRandom(ticks: Tick[], boxes: number, arrows: number, rnd: () => number, w: number, size: number): void {
  const open = ticks.map((_, i) => i).filter((i) => i > 0);
  const quiet = shuffle(
    open.filter((i) => !ticks[i].label),
    rnd,
  );
  const loud = shuffle(
    open.filter((i) => ticks[i].label),
    rnd,
  );
  // A box clashes with another when their x ranges meet: the centres lie nearer than half their widths together.
  const n = ticks.length;
  const clear = (i: number, j: number) =>
    Math.abs(xOf(i, n, w) - xOf(j, n, w)) >= (boxWidth(ticks[i].value, size) + boxWidth(ticks[j].value, size)) / 2;
  const chosen: number[] = [];
  for (const i of [...quiet, ...loud]) {
    if (chosen.length === boxes) break;
    if (chosen.every((j) => clear(i, j))) chosen.push(i);
  }
  for (const i of chosen) ticks[i].task = "box";
  const rest = shuffle(
    open.filter((i) => !ticks[i].task),
    rnd,
  );
  for (const i of rest.slice(0, arrows)) ticks[i].task = "arrow";
}

// The ticks with their tasks, the arrow numbers in their order, and the arcs, in a block w mm wide. No ticks above
// LIMIT. `p` is already sane.
export function made(p: ZahlenstrahlProps, w: number): Made {
  const n = count(p);
  if (n > LIMIT) return { ticks: [], arrows: [], arcs: [] };
  const rnd = rng(p.seed);
  const ticks = Array.from({ length: n }, (_, i): Tick => {
    const value = p.start + i * p.minor;
    const long = (value - p.start) % p.major === 0;
    const label = p.labels === "all" || (p.labels === "major" && long) || (p.labels === "ends" && (i === 0 || i === n - 1));
    return { value, long, label };
  });
  if (p.tasks === "free") {
    const free = new Map(p.marks ?? []);
    for (const t of ticks) {
      const task = free.get(t.value);
      if (task) t.task = task;
    }
  } else {
    placeRandom(ticks, p.boxes, p.arrows, rnd, w, p.size);
  }
  const arrows = shuffle(
    ticks.filter((t) => t.task === "arrow").map((t) => t.value),
    rnd,
  );
  const arcs: Arc[] = [];
  if (p.jumps) {
    const jump = p.jump ?? p.major;
    const last = ticks[n - 1].value;
    for (let a = p.start, i = 0; a + jump <= last; a += jump, i++) arcs.push({ from: a, to: a + jump, label: p.arcs?.[i] ?? `+${jump}` });
  }
  return { ticks, arrows, arcs };
}
