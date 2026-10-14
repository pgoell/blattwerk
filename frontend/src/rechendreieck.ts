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

import { rng } from "./zahlenmauer";

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

// The row of a field over the three inner numbers: a unit row for an inner field, the sum of its two ends for an outer.
const row = (f: number): number[] => [0, 1, 2].map((i) => (f < 3 ? (i === f ? 1 : 0) : SIDES[f - 3].includes(i) ? 1 : 0));

const det3 = (a: number[], b: number[], c: number[]): number =>
  a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0]);

// True when the given fields allow exactly one triangle: their rows over the inner numbers have rank 3, that is some
// three of them give a determinant other than 0.
export function fixes(given: boolean[]): boolean {
  const rows = Array.from({ length: FIELDS }, (_, f) => f).filter((f) => given[f]).map(row);
  for (let i = 0; i < rows.length; i++)
    for (let j = i + 1; j < rows.length; j++)
      for (let k = j + 1; k < rows.length; k++) if (det3(rows[i], rows[j], rows[k]) !== 0) return true;
  return false;
}

const key = (x: number[]): string => x.join(",");
const sums = (inner: number[]): number[] => SIDES.map(([x, y]) => inner[x] + inner[y]);
const dist = (x: number[], y: number[]): number => x.reduce((s, v, i) => s + Math.abs(v - y[i]), 0);
const lexLess = (x: number[], y: number[]): boolean => {
  for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return x[i] < y[i];
  return false;
};

// The inner numbers nearest to `gen` that hold the typed numbers `typed` (field to value) and are not `taken`. The
// typed inner fields fix their numbers. The others come from the typed sums, enumerating one free inner number from
// 0 up to 9999 (or up to a typed sum it sits in). An outer typed with both ends free takes the generated end as near as
// it may. Undecided inner numbers keep their generated value. Undefined when no inner triple holds the typed numbers.
function fill(typed: Map<number, number>, gen: number[], taken: Set<string>): number[] | undefined {
  const fixed = [0, 1, 2].map((i) => typed.get(i));
  const free = [0, 1, 2].find((i) => fixed[i] === undefined);
  const hi = (e: number): number => {
    let b = 9999;
    for (const [f, v] of typed) if (f >= 3 && SIDES[f - 3].includes(e)) b = Math.min(b, v);
    return b;
  };
  const holds = (x: number[]): boolean =>
    x.every((v) => v >= 0 && v <= 9999) && [...typed].every(([f, v]) => (f < 3 ? x[f] : x[SIDES[f - 3][0]] + x[SIDES[f - 3][1]]) === v);
  const propagate = (k: (number | undefined)[]): void => {
    let changed = true;
    while (changed) {
      changed = false;
      for (const [f, v] of typed) {
        if (f < 3) continue;
        const [a, b] = SIDES[f - 3];
        if (k[a] !== undefined && k[b] === undefined) [k[b], changed] = [v - k[a], true];
        else if (k[b] !== undefined && k[a] === undefined) [k[a], changed] = [v - k[b], true];
        else if (k[a] === undefined && k[b] === undefined) {
          k[a] = Math.min(Math.max(gen[a], 0), v);
          k[b] = v - k[a];
          changed = true;
        }
      }
    }
  };
  let best: number[] | undefined;
  const starts: (number | undefined)[][] = [];
  if (free === undefined) starts.push([...fixed]);
  else for (let x = 0; x <= hi(free); x++) starts.push(fixed.map((v, i) => (i === free ? x : v)));
  for (const s of starts) {
    const k = [...s];
    propagate(k);
    const x = k.map((v, i) => v ?? gen[i]);
    if (!holds(x) || taken.has(key(x))) continue;
    if (!best || dist(x, gen) < dist(best, gen) || (dist(x, gen) === dist(best, gen) && lexLess(x, best))) best = x;
  }
  return best;
}

// The triangles of the block. The same settings give the same triangles on every call.
export function made(props: RechendreieckProps): Made {
  const p = sane(props);
  const next = rng(p.seed);
  const half = Math.floor(p.max / 2);
  const gen: number[][] = [];
  const givens: boolean[][] = [];
  const seen = new Set<string>();
  for (let t = 0; t < p.count; t++) {
    let inner: number[];
    do inner = [0, 1, 2].map(() => 1 + Math.floor(next() * half));
    while (seen.has(key(inner)));
    seen.add(key(inner));
    gen.push(inner);
    if (p.given === "inner") givens.push([true, true, true, false, false, false]);
    else if (p.given === "outer") givens.push([false, false, false, true, true, true]);
    else if (p.given === "free") givens.push([...(p.free as boolean[])]);
    else {
      // Mix: the inner left out, and one of the two outer fields beside it, both from the seed.
      const k = Math.floor(next() * 3);
      const beside = SIDES.flatMap((side, s) => (side.includes(k) ? [s] : []));
      const s = beside[next() < 0.5 ? 0 : 1];
      const g = [false, false, false, false, false, false];
      for (let i = 0; i < 3; i++) g[i] = i !== k;
      g[3 + s] = true;
      givens.push(g);
    }
  }
  const typedOf = (t: number): Map<number, number> => new Map((p.typed ?? []).filter(([w]) => w === t).map(([, f, v]) => [f, v]));
  const finals = gen.map((g) => [...g]);
  const wrong = gen.map(() => false);
  for (let t = 0; t < p.count; t++) {
    const T = typedOf(t);
    if (T.size === 0) continue;
    const taken = new Set(finals.filter((_, u) => u !== t).map(key));
    const best = fill(T, gen[t], taken);
    if (best) finals[t] = best;
    else wrong[t] = true;
  }
  const triangles = finals.map((inner, t): Triangle => {
    const numbers = [...inner, ...sums(inner)];
    for (const [f, v] of typedOf(t)) numbers[f] = v;
    return { numbers, given: givens[t], wrong: wrong[t] };
  });
  return { triangles };
}
