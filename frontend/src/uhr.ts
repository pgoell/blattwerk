// The Uhr: one or more clock faces in columns, each with a time, for reading or for drawing the hands. A pure
// function of the block's settings and its seed, so the editor, the thumbnail and the PDF draw the same clocks.
//
// The contract of #86, which the model, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "uhr", props: UhrProps }`. All numbers are whole. A time is the minutes since 0:00,
// 0 to 1439; the face shows it in 12 hours, so 3:30 and 15:30 look alike.
// - `numbers`: the face's numbers, "all" 1 to 12, "quarters" only 12, 3, 6 and 9, "none" none (default "all").
// - `minutes`: the 60 minute ticks on (default true); the 12 hour ticks are always drawn.
// - `ring`: a second ring with 13 to 24 inside the numbers (default false). Not drawn with `numbers` "none".
// - `task`: "read", the hands are drawn and the answer under the clock is empty; "draw", the time is written under
//   the clock and the face has no hands (default "read").
// - `answer`, the empty answer of "read": "box" a digital box `__:__ Uhr`, "line" a writing line (default "box").
// - `format`, how a time is written: "12" `3:30 Uhr` (hours 1 to 12), "24" `15:30 Uhr` (hours 0 to 23), "words"
//   in words (default "12"). Minutes have two digits.
// - `region`, the words' form (only with "words"): "nach" says "viertel nach drei" and "viertel vor vier", "viertel"
//   says "viertel vier" and "dreiviertel vier" (default "nach"). Everything else reads alike in both: see `inWords`.
// - `count`: how many clocks, 1 to 12 (default 4). `cols`: clocks per row, 1 to 6 (default 4); the rows fill from
//   the top left, row by row.
// - `step`: the minutes the random times keep to: 60 full hours, 30, 15, 5 or 1 (default 15).
// - `fill`: "random" takes every time from the seed; "free" takes clock i's time from `times[i]` and from the seed
//   where that entry is missing or no time (default "random"). `times`: minutes per clock, kept when `fill` changes.
// - `seed`: with the other props alone it gives the random times, so every draw gives the same ones. Random times
//   are multiples of `step` from 1:00 to 12:59 (60 to 779) whatever the format, different from each other while
//   there are enough. With format "24" and task "draw" a random time gets 12 hours added (modulo 24 hours) where a
//   coin from the same seed says so, so the 24-hour clock may show 13:00 to 23:59 or 0:00 to 0:59. The coin is drawn
//   for every clock whatever the format and task, so no other time moves with them. With format "24" and task
//   "read" the times stay 1:00 to 12:59, as the face shows.
// Wrong kinds and values out of range give their default in `sane`, which never throws on any stored value.
//
// The time words (`inWords`), `h` the hour 1 to 12 and `n` the next one, as the words of `HOURS`:
//   :00 "<h> Uhr" ("ein Uhr" at one), :05 "fünf nach <h>", :10 "zehn nach <h>", :15 "viertel nach <h>" | "viertel
//   <n>", :20 "zwanzig nach <h>", :25 "fünf vor halb <n>", :30 "halb <n>", :35 "fünf nach halb <n>", :40 "zwanzig
//   vor <n>", :45 "viertel vor <n>" | "dreiviertel <n>", :50 "zehn vor <n>", :55 "fünf vor <n>"; any other minute m
//   below 30 "<m> Minuten nach <h>" (m 1: "1 Minute nach <h>"), above 30 "<60-m> Minuten vor <n>" (60-m 1:
//   "1 Minute vor <n>"), the minutes in digits ("23 Minuten nach zwölf"). Lower case but the nouns "Uhr" and
//   "Minute(n)". Midnight and noon are "zwölf". `written(t, p)` gives the time as `format` says, every place that writes
//   a time (the task under the clock, the answer key) takes it from there.
//
// The geometry, in the svg's own units: clock i stands in the cell of 100 by 130 at (100·col, 130·row), the
// viewBox is `0 0 100·cols 130·rows` (cols the clocks of the first row: fewer clocks than `cols` give fewer
// columns), laid in the block centred at the largest size that fits (preserveAspectRatio meet), so a clock stays
// round on any resize. In a cell, from its top left:
// - The face: a circle at (50, 50), radius 46, stroke 1.2. Hour ticks from radius 46 to 39, stroke 1.2; minute ticks
//   from 46 to 42.5, stroke 0.5. Numbers 1 to 12 centred at radius 33, font size 10; the ring's 13 to 24 at radius
//   22, font size 5.5. A centre dot of radius 2.5.
// - The hands from the centre, at angle 0 for 12 o'clock and clockwise: the minute hand at 6·m degrees, length 40,
//   stroke 1.6; the hour hand at 30·(h mod 12) + m/2 degrees, length 25 (13 where the ring is drawn, so it ends short of the ring's numbers), stroke 4.5. So the
//   hour hand stands between the numbers as on a real clock, and on a black and white copy it is the short thick one.
//   Both with round caps.
// - Under the face, centred at x 50, baseline 120: "read" with "box" the text `__:__ Uhr` and "line" a line from
//   (12, 122) to (88, 122), stroke 0.6; "draw" the written time. The font size is 10, or 180 / (letters of the text)
//   where that is less, so a long time in words stays inside its cell.
//
// The answer key (`solved`): "read" writes the time (`written`) in #c0392b at the same place (over the line, or
// in place of `__:__ Uhr`); "draw" draws both hands in #c0392b.
//
// The drawing, on screen and in print alike (`Draw` in sheet.tsx): `div.uhr` (with `.solved` in the answer key)
// holds one `svg` with the viewBox above. Per clock `g.clock[data-i=i][data-time=t]` with `circle.face`,
// `g.ticks` (its `line`s), `text.number` per number (`data-n` the number), `line.hour` and `line.minute` (where the
// hands are drawn, in #222 or in the key #c0392b), `circle.hub`, and under the face `text.task` (the written time
// of "draw", or `__:__ Uhr`), `line.answer` for a writing line, and in the key `text.answer` (#c0392b). Numbers and
// text in Andika. The dock adds a block of 180 by 58.5 mm under "Mathe-Blöcke". The block keeps its size when
// `count` or `cols` change so the clocks keep the default block's size, to the page's foot at most, and it never
// shrinks by itself; the teacher resizes the block.
//
// The panel (pages/Uhr.tsx), by aria-label: "Zahlen" (select: "all" 1 bis 12, "quarters" 12, 3, 6, 9, "none"
// Keine), "Minutenstriche" (checkbox), "13 bis 24" (checkbox, disabled with "none"), "Aufgabe" (select: "read"
// Uhrzeit ablesen, "draw" Zeiger einzeichnen), for "read" "Antwort" (select: "box" __:__ Uhr, "line" Linie),
// "Schreibweise" (select: "12" 3:30 Uhr, "24" 15:30 Uhr, "words" In Worten), for "words" "Form" (select: "nach"
// viertel nach drei, "viertel" viertel vier), "Uhren" and "Spalten" (number inputs), "Zeiten" (select: "random"
// Zufällig, "free" Selbst wählen), for "random" "Schritte" (select: "60" Volle Stunden, "30" Halbe Stunden, "15"
// Viertelstunden, "5" 5 Minuten, "1" 1 Minute) and "Neu würfeln"; for "free" a text input per clock, "Uhr <i>" from
// 1, holding `h:mm` (hours 0 to 23); a time that does not parse is not stored and the input shows it red
// (`aria-invalid`). Switching to "free" stores into `times` the times typed before where a clock has one, and the
// time it shows for the others. Each change is one undo
// step; typing into one field is one step.
//
// The props type lives here; sheet.tsx imports it (and draws the block), never the other way round but for types.

import { rng } from "./zahlenmauer";

export type UhrProps = {
  numbers: "all" | "quarters" | "none";
  minutes: boolean;
  ring: boolean;
  task: "read" | "draw";
  answer: "box" | "line";
  format: "12" | "24" | "words";
  region: "nach" | "viertel";
  count: number;
  cols: number;
  step: 60 | 30 | 15 | 5 | 1;
  fill: "random" | "free";
  times?: number[];
  seed: number;
};

export const DEFAULTS: Omit<UhrProps, "seed"> = {
  numbers: "all",
  minutes: true,
  ring: false,
  task: "read",
  answer: "box",
  format: "12",
  region: "nach",
  count: 4,
  cols: 4,
  step: 15,
  fill: "random",
};
// A cell's size in the svg's units.
export const CELL_W = 100;
export const CELL_H = 130;
// The answer key's colour and the ink.
export const RED = "#c0392b";
export const INK = "#222";
// The hours' words, index 1 to 12.
export const HOURS = ["", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf"];


const isWhole = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v);
const whole = (v: unknown, lo: number, hi: number, dflt: number): number => (isWhole(v) && v >= lo && v <= hi ? v : dflt);
const pick = <T extends string | number>(v: unknown, list: readonly T[], dflt: T): T => list.find((x) => x === v) ?? dflt;
// A minute of the day, 0 to 1439.
const isTime = (v: unknown): v is number => isWhole(v) && v >= 0 && v <= 1439;

// The props as they draw: any stored value gives whole props in range. A bad entry of `times` becomes -1, so the
// other clocks keep their places; `timesOf` takes -1 as no time.
export function sane(p: UhrProps): UhrProps {
  const r = (p ?? {}) as unknown as Record<string, unknown>;
  return {
    numbers: pick(r.numbers, ["all", "quarters", "none"] as const, DEFAULTS.numbers),
    minutes: typeof r.minutes === "boolean" ? r.minutes : DEFAULTS.minutes,
    ring: typeof r.ring === "boolean" ? r.ring : DEFAULTS.ring,
    task: pick(r.task, ["read", "draw"] as const, DEFAULTS.task),
    answer: pick(r.answer, ["box", "line"] as const, DEFAULTS.answer),
    format: pick(r.format, ["12", "24", "words"] as const, DEFAULTS.format),
    region: pick(r.region, ["nach", "viertel"] as const, DEFAULTS.region),
    count: whole(r.count, 1, 12, DEFAULTS.count),
    cols: whole(r.cols, 1, 6, DEFAULTS.cols),
    step: pick(r.step, [60, 30, 15, 5, 1] as const, DEFAULTS.step),
    fill: pick(r.fill, ["random", "free"] as const, DEFAULTS.fill),
    times: Array.isArray(r.times) ? r.times.map((x) => (isTime(x) ? x : -1)) : undefined,
    seed: isWhole(r.seed) ? r.seed : 0,
  };
}

// The drawing's viewBox in svg units: a row of clocks is as wide as its columns, the rows as high as one clock each.
const layout = (p: UhrProps) => {
  const cols = Math.min(p.cols, p.count);
  return { vbW: CELL_W * cols, vbH: CELL_H * Math.ceil(p.count / cols) };
};
// The default block (4 clocks in 4 columns, 180 by 58.5 mm) draws its clocks at the scale s0.
const DEFAULT_LAYOUT = layout(sane({ ...DEFAULTS, seed: 0 }));
const S0 = Math.min(180 / DEFAULT_LAYOUT.vbW, 58.5 / DEFAULT_LAYOUT.vbH);

// The height in mm of a block of width w with the props p, at which its clocks draw at least at the default scale.
export function heightFor(p: UhrProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// The time each clock shows, `count` of them. `p` is already sane. Random times come from the seed; with "free" a
// clock keeps its own time from `times` where that is a whole minute of the day.
export function timesOf(p: UhrProps): number[] {
  const own = (i: number) => (p.fill === "free" && isTime(p.times?.[i]) ? (p.times as number[])[i] : undefined);
  const taken = new Set(Array.from({ length: p.count }, (_, i) => own(i)).filter((t): t is number => t !== undefined));
  const pool: number[] = [];
  for (let t = Math.ceil(60 / p.step) * p.step; t <= 779; t += p.step) if (!taken.has(t)) pool.push(t);
  const rnd = rng(p.seed);
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  // One coin per clock, drawn whatever the format and task, so the rest of the sequence does not depend on them.
  const coins = Array.from({ length: p.count }, () => rnd() < 0.5);
  const half = p.format === "24" && p.task === "draw";
  return Array.from({ length: p.count }, (_, i) => {
    const t = own(i);
    if (t !== undefined) return t;
    const r = pool[i % pool.length];
    return half && coins[i] ? (r + 720) % 1440 : r;
  });
}

// The angles of the hands in degrees, clockwise from 12: [hour, minute].
export function hands(t: number): [number, number] {
  const [h, m] = [Math.floor(t / 60), t % 60];
  return [30 * (h % 12) + m / 2, 6 * m];
}

// The time in words, as the contract says.
export function inWords(t: number, region: UhrProps["region"]): string {
  const h = Math.floor(t / 60) % 12 || 12;
  const n = (h % 12) + 1;
  const m = t % 60;
  const hour = h === 1 ? "ein" : HOURS[h];
  const H = HOURS[h];
  const N = HOURS[n];
  const nach = region === "nach";
  switch (m) {
    case 0:
      return `${hour} Uhr`;
    case 5:
      return `fünf nach ${H}`;
    case 10:
      return `zehn nach ${H}`;
    case 15:
      return nach ? `viertel nach ${H}` : `viertel ${N}`;
    case 20:
      return `zwanzig nach ${H}`;
    case 25:
      return `fünf vor halb ${N}`;
    case 30:
      return `halb ${N}`;
    case 35:
      return `fünf nach halb ${N}`;
    case 40:
      return `zwanzig vor ${N}`;
    case 45:
      return nach ? `viertel vor ${N}` : `dreiviertel ${N}`;
    case 50:
      return `zehn vor ${N}`;
    case 55:
      return `fünf vor ${N}`;
  }
  if (m < 30) return m === 1 ? `1 Minute nach ${H}` : `${m} Minuten nach ${H}`;
  const k = 60 - m;
  return k === 1 ? `1 Minute vor ${N}` : `${k} Minuten vor ${N}`;
}

// The time as `p.format` writes it: `3:30 Uhr`, `15:30 Uhr`, or in words.
export function written(t: number, p: Pick<UhrProps, "format" | "region">): string {
  if (p.format === "words") return inWords(t, p.region);
  const h = Math.floor(t / 60);
  const hour = p.format === "24" ? h : h % 12 || 12;
  return `${hour}:${String(t % 60).padStart(2, "0")} Uhr`;
}

// `h:mm` (hours 0 to 23) as minutes, or undefined when it does not parse.
export function parsed(text: string): number | undefined {
  const m = /^(\d{1,2}):(\d{2})$/.exec(text.trim());
  return m && +m[1] < 24 && +m[2] < 60 ? +m[1] * 60 + +m[2] : undefined;
}
