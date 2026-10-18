// The Zahlenhaus: the numbers of each house and which boxes show theirs. A pure function of the block's settings
// and its seed, so the editor, the thumbnail and the PDF draw the same houses.
//
// The contract of #819, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "zahlenhaus", props: ZahlenhausProps }`.
// - `count` houses (1 to 12, default 4) in `columns` side by side (1 to 6, default 4).
// - `floors` Stockwerke under the roof (2 to 10, default 4). Each floor has two boxes whose numbers add up to the roof.
// - `max`, the Zahlenraum: the largest roof of a generated house, a whole number from 2 to 1000 (default 10). The panel
//   offers 10, 20 and 100, and "Eigener" for any other.
// - `given` says which boxes show their number: "side" the roof and the left box of each floor (Dach und eine Seite),
//   "roof" the roof only (nur Dach), "mix" the roof and one box of each floor, its side from the seed per floor
//   (gemischt), "free" the boxes `free` flags, a flag per box index, the same for every house. Default "side".
// - `typed` holds the numbers the teacher typed into boxes: house (from 0), box index, value (0 to 9999).
// - `seed` alone gives the houses, so every draw gives the same ones.
//
// A box's index: 0 the roof, then floor f (0 the top floor, under the roof) has its left box at 1 + 2f and its right
// box at 2 + 2f. A house has 1 + 2 * floors boxes.
//
// A generated house: its roof is drawn from the seed between lo = min(max, max(2, floors - 1)) and max. Its floors are
// splits of the roof (a, roof - a), a from 0 to roof, no two floors of a house alike while the roof has enough splits
// (roof + 1 of them), in an order from the seed. Two houses of a block may have the same roof.
//
// With typed numbers (manual mode): the roof is the typed roof, else the generated one. A floor with both boxes typed
// keeps both. A floor with one box typed gets roof minus that number in the other. A floor with none typed keeps its
// generated left number a, taken modulo roof + 1 so a smaller typed roof keeps the floors apart, and gets roof minus
// that on the right. `wrong[f]` is true when floor f
// does not add up to the roof: both typed with another sum, or one typed above the roof.
//
// The props type lives here; sheet.tsx imports it (and draws the block), never the other way round but for types.
//
// The drawing, on screen and in print alike (`Draw` in sheet.tsx): `div.zahlenhaus` (with `.solved` in the answer key)
// holds one svg; each house is `g.house[data-house=i]` (with `.wrong` when a floor is wrong), each box
// `g.box[data-box=j]` (with `.wrong` on the boxes of a wrong floor), its number a `text.given` (#222) when the box is
// given, or a `text.answer` (#c0392b) in the answer key when it is not and its floor is not wrong. The roof is a
// triangle over the two boxes' width with its number inside. The dock adds a block of 120 by 55 mm.

import { rng } from "./zahlenmauer";

/** A number the teacher typed into a box: the house's index (from 0), the box's index (0 the roof, then 1 + 2f and 2 + 2f for floor f), the value (0 to 9999). */
export type HausTyped = [number, number, number];
export type ZahlenhausProps = {
  /** Number of houses on the sheet, side by side in rows of `columns`. Default 4.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of houses per row. Default 4.
   * @minimum 1
   * @maximum 6
   */
  columns: number;
  /** Number of floors (Stockwerke) under the roof. Each floor has two boxes that add up to the roof. Default 4.
   * @minimum 2
   * @maximum 10
   */
  floors: number;
  /** The Zahlenraum: the largest roof number of a generated house, a whole number from 2 to 1000. The editor offers 10, 20 and 100, or any other. Default 10.
   * @minimum 2
   * @maximum 1000
   */
  max: number;
  /** Which boxes show their number. "side": the roof and the left box of each floor (easy). "roof": the roof only, the pupil finds the splits. "mix": the roof and one box of each floor, left or right from the seed. "free": the boxes flagged in `free`. Default "side". */
  given: "side" | "roof" | "mix" | "free";
  /** With `given` "free": one flag per box, index 0 the roof, then 1 + 2f the left and 2 + 2f the right box of floor f (0 the top floor). A flagged box shows its number. The same for every house. Missing or of another length: the roof and the left boxes. */
  free?: boolean[];
  /** Seed for the random houses. The same seed always gives the same houses. */
  seed: number;
  /** Numbers the teacher typed into boxes. Each entry is [house index from 0, box index, value 0 to 9999]. A floor that does not add up to the roof is marked wrong. */
  typed?: HausTyped[];
};

// A house: every box's number by box index, whether the box shows it, and per floor whether it does not add up.
export type House = { numbers: number[]; given: boolean[]; wrong: boolean[] };
export type Made = { houses: House[] };

export const DEFAULTS: Omit<ZahlenhausProps, "seed"> = { count: 4, columns: 4, floors: 4, max: 10, given: "side" };

// How many boxes a house with `floors` floors has.
export const boxes = (floors: number) => 1 + 2 * floors;

// The flags of the "side" boxes: the roof and each floor's left box.
export const sideFlags = (floors: number) => Array.from({ length: boxes(floors) }, (_, i) => i === 0 || i % 2 === 1);

// The settings as a house block can take them, whatever a stored sheet holds: a wrong value gives its default, `free`
// of another length or with a value not a boolean gives the "side" boxes, a `typed` entry that is not three whole
// numbers in range is dropped, and of two for the same box the last one stays.
export function sane(p: ZahlenhausProps): ZahlenhausProps {
  const floors = Number.isInteger(p.floors) && p.floors >= 2 && p.floors <= 10 ? p.floors : DEFAULTS.floors;
  const free = Array.isArray(p.free) && p.free.length === boxes(floors) && p.free.every((f) => typeof f === "boolean") ? p.free : sideFlags(floors);
  const typed = new Map<string, HausTyped>();
  const count = Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : DEFAULTS.count;
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [h, b, v] = t;
      if (h < 0 || h >= count || b < 0 || b >= boxes(floors) || v < 0 || v > 9999) continue;
      typed.delete(`${h}:${b}`);
      typed.set(`${h}:${b}`, [h, b, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count,
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 6 ? p.columns : DEFAULTS.columns,
    floors,
    max: Number.isInteger(p.max) && p.max >= 2 && p.max <= 1000 ? p.max : DEFAULTS.max,
    given: p.given === "roof" || p.given === "mix" || p.given === "free" ? p.given : "side",
    free,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// The drawing in svg units: a box is S square, a house two boxes wide, its roof S high over its floors. `vbW` and
// `vbH` are the viewBox of the whole drawing.
export function layout(p: Pick<ZahlenhausProps, "count" | "columns" | "floors">) {
  const S = 10;
  const [houseW, houseH, gap] = [2 * S, (p.floors + 1) * S, S];
  const rows = Math.max(1, Math.ceil(p.count / p.columns));
  const vbW = p.columns * houseW + (p.columns - 1) * gap + 1;
  const vbH = rows * houseH + (rows - 1) * gap + 1;
  return { S, houseW, houseH, gap, rows, vbW, vbH };
}

// The default block (4 houses of 4 floors in a row, 120 by 55 mm) draws its boxes at the scale S0. A block of width w
// draws them at the same scale, and its height grows with the rows and floors, so that they keep that size.
const DEFAULT_LAYOUT = layout(DEFAULTS);
const S0 = Math.min(120 / DEFAULT_LAYOUT.vbW, 55 / DEFAULT_LAYOUT.vbH);

// The height in mm of a block of width w with the props p, at which its boxes draw at least at the default scale.
export function heightFor(p: ZahlenhausProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// The houses of the settings. The same settings give the same houses on every call.
const memo = new Map<string, Made>();

export function made(props: ZahlenhausProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const next = rng(p.seed);
  const B = boxes(p.floors);
  const lo = Math.min(p.max, Math.max(2, p.floors - 1));
  const houses: House[] = [];
  for (let h = 0; h < p.count; h++) {
    const genRoof = lo + Math.floor(next() * (p.max - lo + 1));
    // The splits 0 to genRoof, shuffled; the floors take them in order, repeating the list when there are too few.
    const splits = Array.from({ length: genRoof + 1 }, (_, a) => a);
    for (let i = splits.length - 1; i > 0; i--) {
      const j = Math.floor(next() * (i + 1));
      [splits[i], splits[j]] = [splits[j], splits[i]];
    }
    const given = p.given === "side" ? sideFlags(p.floors) : p.given === "free" ? [...(p.free as boolean[])] :Array.from({ length: B }, (_, i) => i === 0);
    // The side of each floor that "mix" gives, drawn for every `given`, so that another choice keeps the same houses.
    const sides = Array.from({ length: p.floors }, () => next() < 0.5);
    if (p.given === "mix") sides.forEach((left, f) => (given[left ? 1 + 2 * f : 2 + 2 * f] = true));
    const typed = new Map((p.typed ?? []).filter(([x]) => x === h).map(([, b, v]) => [b, v] as const));
    const roof = typed.get(0) ?? genRoof;
    const numbers = [roof, ...Array.from({ length: B - 1 }, () => 0)];
    const wrong = Array.from({ length: p.floors }, () => false);
    for (let f = 0; f < p.floors; f++) {
      const [L, R] = [1 + 2 * f, 2 + 2 * f];
      const [tl, tr] = [typed.get(L), typed.get(R)];
      if (tl !== undefined && tr !== undefined) {
        [numbers[L], numbers[R]] = [tl, tr];
        wrong[f] = tl + tr !== roof;
      } else if (tl !== undefined) {
        numbers[L] = tl;
        numbers[R] = tl > roof ? 0 : roof - tl;
        wrong[f] = tl > roof;
      } else if (tr !== undefined) {
        numbers[R] = tr;
        numbers[L] = tr > roof ? 0 : roof - tr;
        wrong[f] = tr > roof;
      } else {
        numbers[L] = splits[f % splits.length] % (roof + 1);
        numbers[R] = roof - numbers[L];
      }
    }
    houses.push({ numbers, given, wrong });
  }
  const out: Made = { houses };
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}
