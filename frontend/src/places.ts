// The Montessori place colours of a whole number, and which digit takes which.
//
// Einer, Zehner and Hunderter are green, blue and red. Tausender is green too, and a colour of its own, so a
// teacher can tell the thousands from the units. From the ten-thousands on, the colours follow the same threes:
// blue, red, then green again at the millions. A number with a comma is a decimal and stays the ink it already has.

import { GAP } from "./decimal";

export const NAMES = ["einer", "zehner", "hunderter", "tausender"] as const;
export type PlaceName = (typeof NAMES)[number];
export type PlaceColors = Record<PlaceName, string>;
// What a sheet stores. A missing colour means the Montessori one. `on` left out means the colours stay off.
export type Places = {
  /** Turns the place colours on. Left out, they stay off. */
  on?: boolean;
  /** Colour of the units (Einer), as "#rrggbb". Left out, the Montessori green. */
  einer?: string;
  /** Colour of the tens (Zehner), as "#rrggbb". Left out, the Montessori blue. */
  zehner?: string;
  /** Colour of the hundreds (Hunderter), as "#rrggbb". Left out, the Montessori red. */
  hunderter?: string;
  /** Colour of the thousands (Tausender), as "#rrggbb". Left out, the Montessori green. */
  tausender?: string;
};
export type Run = { text: string; color?: string; place?: PlaceName };
export type GridCell = { x: number; y: number; ch: string; kind: number; decimal?: boolean };
export type Tint = { color: string; place: PlaceName };

// The stamp-game colours: units and thousands green, tens blue, hundreds red.
export const MONTESSORI: PlaceColors = {
  einer: "#009640",
  zehner: "#0057a8",
  hunderter: "#e30613",
  tausender: "#009640",
};

const HEX = /^#[0-9a-fA-F]{6}$/;
const DIGIT = /^\d$/;

// The place of a digit counted from the right, 0 for the units.
export function placeName(index: number): PlaceName {
  if (index === 3) return "tausender";
  const mod = index % 3;
  if (mod === 1) return "zehner";
  if (mod === 2) return "hunderter";
  return "einer";
}

// The colours a sheet actually draws with, or none while the switch is off. A colour that is not six hex digits
// is dropped, and the Montessori one stands in its place.
export function placeColors(doc: { places?: unknown }): PlaceColors | null {
  const stored = storedPlaces(doc.places);
  if (!stored?.on) return null;
  return {
    einer: stored.einer ?? MONTESSORI.einer,
    zehner: stored.zehner ?? MONTESSORI.zehner,
    hunderter: stored.hunderter ?? MONTESSORI.hunderter,
    tausender: stored.tausender ?? MONTESSORI.tausender,
  };
}

// The place colours worth keeping on the sheet. Anything else is dropped, and nothing at all is left out.
export function storedPlaces(raw: unknown): Places | undefined {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return undefined;
  const rec = raw as Record<string, unknown>;
  const out: Places = {};
  if (rec.on === true) out.on = true;
  for (const name of NAMES) {
    const value = rec[name];
    if (typeof value === "string" && HEX.test(value)) out[name] = value.toLowerCase();
  }
  return out.on || NAMES.some((name) => out[name]) ? out : undefined;
}

// The runs of `text`. A digit of a whole number carries its place colour. A decimal, a sign or a word does not.
// With the colours off, the text is one run.
export function runs(text: string, colors: PlaceColors | null): Run[] {
  if (!colors || !text) return [{ text }];
  const out: Run[] = [];
  const push = (chunk: string, place?: PlaceName) => {
    if (!chunk) return;
    const last = out[out.length - 1];
    if (last && !last.place && !place) last.text += chunk;
    else out.push(place ? { text: chunk, color: colors[place], place } : { text: chunk });
  };
  let i = 0;
  while (i < text.length) {
    if (!DIGIT.test(text[i])) {
      push(text[i]);
      i++;
      continue;
    }
    let j = i;
    let comma = false;
    const at: number[] = [];
    while (j < text.length) {
      const ch = text[j];
      if (DIGIT.test(ch)) {
        at.push(j);
        j++;
        continue;
      }
      // A grouping gap belongs to the whole number. A comma with digits after it makes the number a decimal.
      if (ch === GAP && !comma && DIGIT.test(text[j + 1] ?? "")) {
        j++;
        continue;
      }
      if (ch === "," && !comma && DIGIT.test(text[j + 1] ?? "")) {
        comma = true;
        j++;
        continue;
      }
      break;
    }
    if (comma) push(text.slice(i, j));
    else {
      const count = at.length;
      let seen = 0;
      for (let k = i; k < j; k++) {
        if (DIGIT.test(text[k])) push(text[k], placeName(count - 1 - seen++));
        else push(text[k]);
      }
    }
    i = j;
  }
  return out.length ? out : [{ text }];
}

const keyOf = (cell: GridCell) => `${cell.x},${cell.y}`;

// The colour of each single digit in a squared sum. A number is coloured from its own right. A one-digit carry
// takes the place of its column, lined up with the units (the column left of the comma, or else the rightmost
// digit). A decimal number takes none. A cell of several characters is left to the string, which draws it.
export function gridTint(cells: GridCell[], colors: PlaceColors | null): Map<string, Tint> {
  const tint = new Map<string, Tint>();
  if (!colors) return tint;
  const comma = cells.find((cell) => cell.ch === ",");
  const digits = cells.filter((cell) => cell.kind !== 2 && DIGIT.test(cell.ch));
  const units = comma ? comma.x - 1 : Math.max(-1, ...digits.map((cell) => cell.x));
  const rows = new Map<number, GridCell[]>();
  for (const cell of cells) {
    const row = rows.get(cell.y);
    if (row) row.push(cell);
    else rows.set(cell.y, [cell]);
  }
  for (const row of rows.values()) {
    const line = [...row].sort((a, b) => a.x - b.x);
    let i = 0;
    while (i < line.length) {
      const cell = line[i];
      if (!DIGIT.test(cell.ch) && cell.ch !== ",") {
        i++;
        continue;
      }
      const token = [cell];
      let j = i + 1;
      while (j < line.length && line[j].x === token[token.length - 1].x + 1 && (DIGIT.test(line[j].ch) || line[j].ch === ",")) token.push(line[j++]);
      // A comma in its own square, or a comma or point hung on a digit, makes the number a decimal.
      if (!token.some((part) => part.ch === "," || part.decimal)) {
        const ones = token.filter((part) => DIGIT.test(part.ch));
        if (ones.length === 1 && ones[0].kind === 2) {
          const index = units - ones[0].x;
          if (index >= 0) tint.set(keyOf(ones[0]), { color: colors[placeName(index)], place: placeName(index) });
        } else {
          ones.forEach((digit, index) => {
            const place = placeName(ones.length - 1 - index);
            tint.set(keyOf(digit), { color: colors[place], place });
          });
        }
      }
      i = j;
    }
  }
  return tint;
}
