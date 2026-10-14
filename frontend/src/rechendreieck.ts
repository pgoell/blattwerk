// The Rechendreieck: the numbers of each triangle and which fields show theirs. A pure function of the block's
// settings and its seed, so the editor, the thumbnail and the PDF draw the same triangles.
//
// The contract of #83, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "rechendreieck", props: RechendreieckProps }`.
// - `count` triangles (1 to 12, default 4) in `columns` side by side (1 to 4, default 4).
// - `max`, the Zahlenraum (10, 20, 100 or 1000, default 20): no outer number of a generated triangle is above it.
// - `given` says which fields show their number: "inner" the three inner (leicht), "mix" two inner and one outer that
//   fixes the third (mittel), "outer" the three outer (schwer), "free" the fields `free` flags, a flag per field index,
//   the same for every triangle. Default "inner".
// - With `empty` no field shows a number.
// - `typed` holds the numbers the teacher typed into fields: triangle (from 0), field index, value (0 to 9999).
// - `seed` alone gives the triangles, so every draw gives the same ones.
//
// A field's index: 0 to 2 the inner fields at the corners (top, bottom left, bottom right), 3 to 5 the outer fields
// beside the sides (left, bottom, right). Outer field 3 + s is the sum of the inner fields SIDES[s].
//
// A generated triangle has whole inner numbers from 1 up (two inner fields of one triangle may hold the same number),
// no two triangles of a block have the same inner numbers, and a block always gets all `count` triangles (bis 10 has
// over a hundred), so nothing needs loosening. Its given fields fix it: exactly one triangle of whole numbers from 0 up
// shows them (for "free" only when `fixes(free)`, else the panel warns). "mix" picks per triangle, from the seed, the
// inner field left out and one of the two outer fields beside it. With typed numbers a triangle holds every typed number, and its other inner fields keep their generated
// numbers where they can: of the triangles of whole numbers 0 to 9999 that hold the typed numbers, the one nearest the
// generated inner numbers (the least sum of the differences), on a tie the one with the smallest inner numbers in
// index order. When no triangle holds them, `wrong` is true and the numbers are the generated ones with the typed ones
// in their fields. Finding it needs no general search: enumerate one inner number, the typed sums give the rest.
//
// The props type lives here; sheet.tsx imports it (and draws the block), never the other way round but for types.
//
// The drawing, on screen and in print alike (`Draw` in sheet.tsx): `div.rechendreieck` (with `.solved` in the answer
// key) holds one svg; each triangle is `g.triangle[data-triangle=i]` (with `.wrong` when wrong), each field
// `g.field[data-field=j]`, its number a `text.given` (#222) when the field is given, or a `text.answer` (#c0392b) in
// the answer key when it is not. With `empty` no text at all. The dock adds a block of 180 by 50 mm.

export type Typed = [number, number, number];
export type RechendreieckProps = {
  count: number;
  columns: number;
  max: number;
  given: "inner" | "mix" | "outer" | "free";
  free?: boolean[];
  empty: boolean;
  seed: number;
  typed?: Typed[];
};

// A triangle: every field's number by field index, and whether the field shows it. `wrong` says the numbers the
// teacher typed allow no triangle.
export type Triangle = { numbers: number[]; given: boolean[]; wrong: boolean };
export type Made = { triangles: Triangle[] };

export const FIELDS = 6;
// The inner fields at the ends of each side: outer field 3 + s is the sum of SIDES[s].
export const SIDES: [number, number][] = [
  [0, 1],
  [1, 2],
  [2, 0],
];
// A field's name in the panel, by field index.
export const NAMES = ["innen oben", "innen links", "innen rechts", "außen links", "außen unten", "außen rechts"];
export const ZAHLENRAUM = [10, 20, 100, 1000];
export const DEFAULTS: Omit<RechendreieckProps, "seed"> = { count: 4, columns: 4, max: 20, given: "inner", empty: false };

// The settings as a triangle block can take them, whatever a stored sheet holds: a wrong value gives its default,
// `free` of another length or with a value not a boolean gives the inner fields, a `typed` entry that is not three
// whole numbers in range is dropped, and of two for the same field the last one stays.
export function sane(p: RechendreieckProps): RechendreieckProps {
  const free = Array.isArray(p.free) && p.free.length === FIELDS && p.free.every((f) => typeof f === "boolean") ? p.free : Array.from({ length: FIELDS }, (_, i) => i < 3);
  const count = Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : DEFAULTS.count;
  const typed = new Map<string, Typed>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [w, f, v] = t;
      if (w < 0 || w >= count || f < 0 || f >= FIELDS || v < 0 || v > 9999) continue;
      typed.delete(`${w}:${f}`);
      typed.set(`${w}:${f}`, [w, f, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count,
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 4 ? p.columns : DEFAULTS.columns,
    max: ZAHLENRAUM.includes(p.max) ? p.max : DEFAULTS.max,
    given: p.given === "mix" || p.given === "outer" || p.given === "free" ? p.given : "inner",
    free,
    empty: p.empty === true,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// True when the given fields allow exactly one triangle: their rows over the inner numbers have rank 3.
// PLACEHOLDER: the generator's subagent replaces it.
export function fixes(given: boolean[]): boolean {
  return given.filter(Boolean).length >= 3;
}

// The triangles of the block. The same settings give the same triangles on every call.
// PLACEHOLDER so that the drawing and the panel have triangles: the generator's subagent replaces it.
export function made(props: RechendreieckProps): Made {
  const p = sane(props);
  let a = p.seed | 0;
  const next = () => ((a = (Math.imul(a, 1103515245) + 12345) | 0) >>> 0) / 4294967296;
  const triangles = Array.from({ length: p.count }, (_, t): Triangle => {
    const inner = [0, 1, 2].map(() => 1 + Math.floor(next() * Math.floor(p.max / 2)));
    const numbers = [...inner, ...SIDES.map(([x, y]) => inner[x] + inner[y])];
    for (const [w, f, v] of p.typed ?? []) if (w === t) numbers[f] = v;
    const given = p.given === "free" ? [...(p.free as boolean[])] : Array.from({ length: FIELDS }, (_, i) => (p.given === "outer" ? i >= 3 : p.given === "mix" ? i === 0 || i === 1 || i === 4 : i < 3));
    return { numbers, given, wrong: false };
  });
  return { triangles };
}
