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
//   are multiples of `step` in 0 to 1439 (in 60 to 779, 1:00 to 12:59, with format "12" and "words"), different
//   from each other while there are enough.
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
//   stroke 1.6; the hour hand at 30·(h mod 12) + m/2 degrees, length 25 (19 with the ring), stroke 4.5. So the
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
// `count` or `cols` change; the clocks grow or shrink to fit it, and the teacher resizes the block.
//
// The panel (pages/Uhr.tsx), by aria-label: "Zahlen" (select: "all" 1 bis 12, "quarters" 12, 3, 6, 9, "none"
// Keine), "Minutenstriche" (checkbox), "13 bis 24" (checkbox, disabled with "none"), "Aufgabe" (select: "read"
// Uhrzeit ablesen, "draw" Zeiger einzeichnen), for "read" "Antwort" (select: "box" __:__ Uhr, "line" Linie),
// "Schreibweise" (select: "12" 3:30 Uhr, "24" 15:30 Uhr, "words" In Worten), for "words" "Form" (select: "nach"
// viertel nach drei, "viertel" viertel vier), "Uhren" and "Spalten" (number inputs), "Zeiten" (select: "random"
// Zufällig, "free" Selbst wählen), for "random" "Schritte" (select: "60" Volle Stunden, "30" Halbe Stunden, "15"
// Viertelstunden, "5" 5 Minuten, "1" 1 Minute) and "Neu würfeln"; for "free" a text input per clock, "Uhr <i>" from
// 1, holding `h:mm` (hours 0 to 23); a time that does not parse is not stored and the input shows it red
// (`aria-invalid`). Switching to "free" stores the times the clocks show into `times`. Each change is one undo
// step; typing into one field is one step.
//
// The props type lives here; sheet.tsx imports it (and draws the block), never the other way round but for types.

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

// The props as they draw: any stored value gives whole props in range.
// STUB: the model's subagent writes it as the contract says.
export function sane(p: UhrProps): UhrProps {
  return { ...DEFAULTS, ...(p ?? {}) };
}

// The time each clock shows, `count` of them. `p` is already sane.
// STUB: the model's subagent writes it as the contract says.
export function timesOf(p: UhrProps): number[] {
  return Array.from({ length: p.count }, (_, i) => p.times?.[i] ?? (60 + i * 75) % 1440);
}

// The angles of the hands in degrees, clockwise from 12: [hour, minute].
export function hands(t: number): [number, number] {
  const [h, m] = [Math.floor(t / 60), t % 60];
  return [30 * (h % 12) + m / 2, 6 * m];
}

// The time in words, as the contract says.
// STUB: the model's subagent writes it as the contract says.
export function inWords(t: number, region: UhrProps["region"]): string {
  void region;
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")} Uhr`;
}

// The time as `p.format` writes it: `3:30 Uhr`, `15:30 Uhr`, or in words.
// STUB: the model's subagent writes it as the contract says.
export function written(t: number, p: Pick<UhrProps, "format" | "region">): string {
  if (p.format === "words") return inWords(t, p.region);
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")} Uhr`;
}

// `h:mm` (hours 0 to 23) as minutes, or undefined when it does not parse.
// STUB: the model's subagent writes it as the contract says.
export function parsed(text: string): number | undefined {
  const m = /^(\d{1,2}):(\d{2})$/.exec(text.trim());
  return m && +m[1] < 24 && +m[2] < 60 ? +m[1] * 60 + +m[2] : undefined;
}
