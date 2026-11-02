// The Geobrett: a board of nails and the rubber bands stretched from nail to nail.
//
// Stored shape: a block `{ type: "geobrett", props: GeobrettProps }`. A nail is [column, row], both from 0 at the
// top left. `cols` and `rows` are how many nails across and down. A band is the nails it visits, in order, a
// colour, and whether it is filled: a filled band closes from the last nail back to the first. `task` is what the
// pupil does. "leer" draws no band, so the sheet is an empty board. The other tasks draw the bands and, in the
// answer key, what `solution` derives: the mirror image, the axes, the turn, the right angles, the parallel
// sides, the area, the perimeter or the coordinates. Coordinates on the sheet count from the bottom left.
// `sane` never throws. A move, turn or scale that would leave the board gives the band back unchanged.

export const COLORS = ["#c0392b", "#1f6feb", "#1a7f37", "#d97706", "#6f42c1", "#222222"] as const;
export const TASKS = ["leer", "spiegel", "achsen", "drehung", "winkel", "parallelen", "flaeche", "umfang", "koordinaten"] as const;
export type Aufgabe = (typeof TASKS)[number];
export type Nail = [number, number];

export type Band = {
  /** Nails the band visits, in order. Each pair is [column, row], from 0 at the top left. A filled band closes back to its first nail. */
  nails: Nail[];
  /** Colour of the band, `#` and six hex digits. */
  color: string;
  /** Whether the polygon the nails enclose is filled. False draws a line from nail to nail. */
  fill: boolean;
};

export type Axis = {
  /** The line: "v" a column, "h" a row, "d" the diagonal where row - column = `at`, "a" the diagonal where row + column = `at`. */
  dir: "v" | "h" | "d" | "a";
  /** Where the axis sits: the column or row from 0, or the diagonal's constant. With `mid`, the gap after that nail. */
  at: number;
  /** True when a "v" or "h" axis lies in the gap after nail `at` instead of on the nail. */
  mid?: boolean;
};

export type GeobrettProps = {
  /** Nails across the board.
   * @minimum 2
   * @maximum 12
   */
  cols: number;
  /** Nails down the board.
   * @minimum 2
   * @maximum 12
   */
  rows: number;
  /** The rubber bands, in the order they are drawn. */
  bands: Band[];
  /** The task. "leer" is an empty board the pupil draws on. The others ask for the mirror image, the axes, a quarter turn, the right angles, the parallel sides, the area, the perimeter or the coordinates. */
  task: Aufgabe;
  /** Which starting figure of `task` the bands came from, from 0. Absent when the teacher drew the bands. */
  figure?: number;
  /** The mirror line of task "spiegel". */
  axis?: Axis;
  /** The nail a task "drehung" turns about, [column, row]. */
  centre?: Nail;
  /** Kept so a sheet made with the other maths blocks still carries a seed. The board does not roll from it. */
  seed: number;
};

export type Figure = { bands: Band[]; axis?: Axis; centre?: Nail };
export type Solution =
  | { kind: "leer" }
  | { kind: "spiegel"; bands: Band[] }
  | { kind: "achsen"; axes: Axis[] }
  | { kind: "drehung"; bands: Band[] }
  | { kind: "winkel"; nails: Nail[] }
  | { kind: "parallelen"; groups: number[][] }
  | { kind: "flaeche"; area: number; text: string }
  | { kind: "umfang"; text: string }
  | { kind: "koordinaten"; nails: Nail[] };

export const ASK: Record<Aufgabe, string> = {
  leer: "",
  spiegel: "Ergänze das Spiegelbild.",
  achsen: "Zeichne alle Spiegelachsen.",
  drehung: "Drehe die Figur um 90° im Uhrzeigersinn.",
  winkel: "Markiere die rechten Winkel.",
  parallelen: "Welche Seiten sind parallel?",
  flaeche: "Wie groß ist der Flächeninhalt?",
  umfang: "Wie lang ist der Umfang?",
  koordinaten: "Schreibe die Koordinaten der Nägel.",
};

export const DEFAULTS: GeobrettProps = { cols: 5, rows: 5, bands: [], task: "leer", seed: 0 };
const MIN = 2;
const MAX = 12;
const HEX = /^#[0-9a-f]{6}$/i;

const whole = (v: unknown, lo: number, hi: number, fallback: number) =>
  typeof v === "number" && Number.isInteger(v) && v >= lo && v <= hi ? v : fallback;

function nailOf(v: unknown, cols: number, rows: number): Nail | undefined {
  if (!Array.isArray(v) || v.length < 2) return;
  const [c, r] = [v[0], v[1]];
  if (typeof c !== "number" || typeof r !== "number" || !Number.isInteger(c) || !Number.isInteger(r)) return;
  if (c < 0 || r < 0 || c >= cols || r >= rows) return;
  return [c, r];
}

function axisOf(v: unknown, cols: number, rows: number): Axis | undefined {
  if (!v || typeof v !== "object") return;
  const a = v as Record<string, unknown>;
  if (typeof a.at !== "number" || !Number.isInteger(a.at)) return;
  const mid = a.mid === true;
  if (a.dir === "v" || a.dir === "h") {
    const span = (a.dir === "v" ? cols : rows) - (mid ? 1 : 0);
    if (a.at < 0 || a.at >= span) return;
    return { dir: a.dir, at: a.at, ...(mid && { mid: true }) };
  }
  if (a.dir !== "d" && a.dir !== "a") return;
  const lo = a.dir === "d" ? 1 - cols : 0;
  const hi = a.dir === "d" ? rows - 1 : cols + rows - 2;
  if (a.at < lo || a.at > hi) return;
  return { dir: a.dir, at: a.at };
}

function bandsOf(v: unknown, cols: number, rows: number): Band[] {
  if (!Array.isArray(v)) return [];
  const bands: Band[] = [];
  for (const item of v.slice(0, 8)) {
    if (!item || typeof item !== "object") continue;
    const raw = item as Record<string, unknown>;
    const nails: Nail[] = [];
    if (Array.isArray(raw.nails)) {
      for (const one of raw.nails.slice(0, 12)) {
        const nail = nailOf(one, cols, rows);
        const last = nails[nails.length - 1];
        if (nail && (!last || last[0] !== nail[0] || last[1] !== nail[1])) nails.push(nail);
      }
    }
    if (nails.length < 2) continue;
    const color = typeof raw.color === "string" && HEX.test(raw.color) ? raw.color.toLowerCase() : COLORS[0];
    bands.push({ nails, color, fill: raw.fill === true });
  }
  return bands;
}

export function sane(props: unknown): GeobrettProps {
  const p = props && typeof props === "object" ? (props as Record<string, unknown>) : {};
  const cols = whole(p.cols, MIN, MAX, DEFAULTS.cols);
  const rows = whole(p.rows, MIN, MAX, DEFAULTS.rows);
  const task = TASKS.includes(p.task as Aufgabe) ? (p.task as Aufgabe) : "leer";
  const seed = typeof p.seed === "number" && Number.isInteger(p.seed) ? p.seed : 0;
  const figure = typeof p.figure === "number" && Number.isInteger(p.figure) && p.figure >= 0 ? p.figure : undefined;
  const axis = axisOf(p.axis, cols, rows);
  const centre = nailOf(p.centre, cols, rows);
  return {
    cols,
    rows,
    bands: bandsOf(p.bands, cols, rows),
    task,
    seed,
    ...(figure !== undefined && { figure }),
    ...(axis && { axis }),
    ...(centre && { centre }),
  };
}

const outside = (nails: Nail[], cols: number, rows: number) => nails.some(([c, r]) => c < 0 || r < 0 || c >= cols || r >= rows);

export function moved(band: Band, dc: number, dr: number, cols: number, rows: number): Band {
  const nails = band.nails.map(([c, r]) => [c + dc, r + dr] as Nail);
  return outside(nails, cols, rows) ? band : { ...band, nails };
}

// 90 degrees clockwise on the page, where row grows downward: (dx, dy) goes to (-dy, dx).
export function turned(band: Band, cols: number, rows: number): Band {
  if (!band.nails.length) return band;
  const cs = band.nails.map((n) => n[0]);
  const rs = band.nails.map((n) => n[1]);
  const [minC, maxC, minR, maxR] = [Math.min(...cs), Math.max(...cs), Math.min(...rs), Math.max(...rs)];
  const same = (minC + maxC) % 2 === (minR + maxR) % 2;
  const [cx, cy] = same ? [(minC + maxC) / 2, (minR + maxR) / 2] : [minC, minR];
  const nails = band.nails.map(([c, r]) => [cx - (r - cy), cy + (c - cx)] as Nail);
  return outside(nails, cols, rows) ? band : { ...band, nails };
}

export function mirrored(band: Band, way: "x" | "y"): Band {
  const cs = band.nails.map((n) => n[0]);
  const rs = band.nails.map((n) => n[1]);
  const [minC, maxC, minR, maxR] = [Math.min(...cs), Math.max(...cs), Math.min(...rs), Math.max(...rs)];
  const nails = band.nails.map(([c, r]) => (way === "x" ? [minC + maxC - c, r] : [c, minR + maxR - r]) as Nail);
  return { ...band, nails };
}

export function scaled(band: Band, by: 2 | 0.5, cols: number, rows: number): Band {
  if (!band.nails.length) return band;
  const [ox, oy] = [Math.min(...band.nails.map((n) => n[0])), Math.min(...band.nails.map((n) => n[1]))];
  const nails: Nail[] = [];
  for (const [c, r] of band.nails) {
    const [dx, dy] = [c - ox, r - oy];
    if (by === 0.5 && (dx % 2 !== 0 || dy % 2 !== 0)) return band;
    nails.push(by === 2 ? [ox + 2 * dx, oy + 2 * dy] : [ox + dx / 2, oy + dy / 2]);
  }
  return outside(nails, cols, rows) ? band : { ...band, nails };
}

export function areaOf(band: Band): number {
  const n = ring(band);
  if (n.length < 3) return 0;
  let sum = 0;
  for (let i = 0; i < n.length; i++) {
    const [x, y] = n[i];
    const [u, v] = n[(i + 1) % n.length];
    sum += x * v - u * y;
  }
  return Math.abs(sum) / 2;
}

export function areaText(n: number): string {
  if (Number.isInteger(n)) return String(n);
  const tenths = Math.round(Math.abs(n) * 10);
  return `${n < 0 ? "-" : ""}${Math.floor(tenths / 10)},${tenths % 10}`;
}

function ring(band: Band): Nail[] {
  const n = band.nails;
  if (n.length > 1 && n[0][0] === n[n.length - 1][0] && n[0][1] === n[n.length - 1][1]) return n.slice(0, -1);
  return n;
}

function closed(band: Band): boolean {
  return band.fill || ring(band).length !== band.nails.length;
}

function squareFree(n: number): [number, number] {
  let s = 1;
  let k = n;
  for (let p = 2; p * p <= k; p++) {
    while (k % (p * p) === 0) {
      k = k / (p * p);
      s *= p;
    }
  }
  return [s, k];
}

function textOf(lengths: number[]): string {
  const coeff = new Map<number, number>();
  for (const d of lengths) {
    if (d <= 0) continue;
    const [s, k] = squareFree(d);
    coeff.set(k, (coeff.get(k) ?? 0) + s);
  }
  const keys = [...coeff.keys()].sort((a, b) => a - b);
  if (!keys.length) return "0";
  return keys
    .map((k) => {
      const c = coeff.get(k)!;
      if (k === 1) return String(c);
      const root = `√${k}`;
      return c === 1 ? root : `${c}${root}`;
    })
    .join(" + ");
}

function edges(band: Band): number[] {
  const n = ring(band);
  const m = closed(band) ? n.length : n.length - 1;
  const out: number[] = [];
  for (let i = 0; i < m; i++) {
    const [x, y] = n[i];
    const [u, v] = n[(i + 1) % n.length];
    out.push((x - u) ** 2 + (y - v) ** 2);
  }
  return out;
}

export function lengthText(band: Band): string {
  return textOf(edges(band));
}

export function rightAngles(band: Band): Nail[] {
  const n = ring(band);
  const from = closed(band) ? 0 : 1;
  const to = closed(band) ? n.length : n.length - 1;
  const found: Nail[] = [];
  for (let i = from; i < to; i++) {
    const prev = n[(i - 1 + n.length) % n.length];
    const at = n[i];
    const next = n[(i + 1) % n.length];
    const dot = (prev[0] - at[0]) * (next[0] - at[0]) + (prev[1] - at[1]) * (next[1] - at[1]);
    if (dot === 0 && (prev[0] !== at[0] || prev[1] !== at[1]) && (next[0] !== at[0] || next[1] !== at[1])) found.push(at);
  }
  return found;
}

export function parallelGroups(band: Band): number[][] {
  const n = ring(band);
  const m = closed(band) ? n.length : n.length - 1;
  const dir = (i: number): [number, number] | undefined => {
    const [x, y] = n[i];
    const [u, v] = n[(i + 1) % n.length];
    return u === x && v === y ? undefined : [u - x, v - y];
  };
  const parent = Array.from({ length: m }, (_, i) => i);
  const find = (i: number): number => (parent[i] === i ? i : (parent[i] = find(parent[i])));
  for (let i = 0; i < m; i++) {
    const a = dir(i);
    if (!a) continue;
    for (let j = i + 1; j < m; j++) {
      const b = dir(j);
      if (b && a[0] * b[1] - a[1] * b[0] === 0) parent[find(j)] = find(i);
    }
  }
  const groups = new Map<number, number[]>();
  for (let i = 0; i < m; i++) {
    if (!dir(i)) continue;
    const root = find(i);
    groups.set(root, [...(groups.get(root) ?? []), i]);
  }
  return [...groups.values()].filter((g) => g.length > 1).sort((a, b) => a[0] - b[0]);
}

function mirrorNail([c, r]: Nail, axis: Axis): Nail {
  if (axis.dir === "v") return [(axis.mid ? 2 * axis.at + 1 : 2 * axis.at) - c, r];
  if (axis.dir === "h") return [c, (axis.mid ? 2 * axis.at + 1 : 2 * axis.at) - r];
  if (axis.dir === "d") return [r - axis.at, c + axis.at];
  return [axis.at - r, axis.at - c];
}

function onBoard(band: Band, nails: Nail[], cols: number, rows: number): Band[] {
  return outside(nails, cols, rows) ? [] : [{ ...band, nails }];
}

function axesOf(bands: Band[], cols: number, rows: number): Axis[] {
  const nails = bands.flatMap((b) => b.nails);
  const seen = new Set<string>();
  const uniq = nails.filter(([c, r]) => {
    const key = `${c},${r}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  if (uniq.length < 2) return [];
  const has = (c: number, r: number) => seen.has(`${c},${r}`);
  const ok = (map: (n: Nail) => Nail) => uniq.every((n) => {
    const [c, r] = map(n);
    return Number.isInteger(c) && Number.isInteger(r) && has(c, r);
  });
  const found: Axis[] = [];
  for (let at = 0; at < cols; at++) if (ok(([c, r]) => [2 * at - c, r])) found.push({ dir: "v", at });
  for (let at = 0; at < cols - 1; at++) if (ok(([c, r]) => [2 * at + 1 - c, r])) found.push({ dir: "v", at, mid: true });
  for (let at = 0; at < rows; at++) if (ok(([c, r]) => [c, 2 * at - r])) found.push({ dir: "h", at });
  for (let at = 0; at < rows - 1; at++) if (ok(([c, r]) => [c, 2 * at + 1 - r])) found.push({ dir: "h", at, mid: true });
  for (let at = 1 - cols; at <= rows - 1; at++) if (ok(([c, r]) => [r - at, c + at])) found.push({ dir: "d", at });
  for (let at = 0; at <= cols + rows - 2; at++) if (ok(([c, r]) => [at - r, at - c])) found.push({ dir: "a", at });
  return found;
}

export function solution(raw: GeobrettProps): Solution {
  const p = sane(raw);
  if (p.task === "leer") return { kind: "leer" };
  if (p.task === "spiegel") {
    const bands = p.axis ? p.bands.flatMap((b) => onBoard(b, b.nails.map((n) => mirrorNail(n, p.axis!)), p.cols, p.rows)) : [];
    return { kind: "spiegel", bands };
  }
  if (p.task === "achsen") return { kind: "achsen", axes: axesOf(p.bands, p.cols, p.rows) };
  if (p.task === "drehung") {
    const centre = centreOf(p);
    const bands = p.bands.flatMap((b) => onBoard(b, b.nails.map(([c, r]) => [centre[0] - (r - centre[1]), centre[1] + (c - centre[0])]), p.cols, p.rows));
    return { kind: "drehung", bands };
  }
  if (p.task === "winkel") {
    const nails: Nail[] = [];
    for (const b of p.bands) for (const n of rightAngles(b)) if (!nails.some(([c, r]) => c === n[0] && r === n[1])) nails.push(n);
    return { kind: "winkel", nails };
  }
  if (p.task === "parallelen") return { kind: "parallelen", groups: p.bands[0] ? parallelGroups(p.bands[0]) : [] };
  if (p.task === "flaeche") {
    const filled = p.bands.filter((b) => b.fill);
    const area = (filled.length ? filled : p.bands.slice(0, 1)).reduce((sum, b) => sum + areaOf(b), 0);
    return { kind: "flaeche", area, text: areaText(area) };
  }
  if (p.task === "umfang") return { kind: "umfang", text: textOf(p.bands.flatMap(edges)) };
  const nails: Nail[] = [];
  for (const b of p.bands) {
    for (const [c, r] of b.nails) {
      const shown: Nail = [c, p.rows - 1 - r];
      if (!nails.some(([x, y]) => x === shown[0] && y === shown[1])) nails.push(shown);
    }
  }
  return { kind: "koordinaten", nails };
}

const poly = (nails: Nail[], color: string, fill = true): Band => ({ nails, color, fill });

export function figures(task: Aufgabe): Figure[] {
  const [red, blue, green, orange, purple, black] = COLORS;
  if (task === "spiegel") {
    return [
      { bands: [poly([[0, 1], [2, 2], [0, 3]], red)], axis: { dir: "v", at: 2 } },
      { bands: [poly([[1, 0], [3, 0], [2, 2]], blue)], axis: { dir: "h", at: 2 } },
    ];
  }
  if (task === "achsen") {
    return [{ bands: [poly([[1, 1], [3, 1], [3, 3], [1, 3]], green)] }, { bands: [poly([[1, 1], [3, 1], [2, 3]], red)] }];
  }
  if (task === "drehung") {
    return [
      { bands: [poly([[1, 1], [1, 3], [2, 3]], blue)], centre: [2, 2] },
      { bands: [poly([[2, 0], [2, 1], [3, 1]], orange)], centre: [2, 2] },
    ];
  }
  if (task === "winkel") {
    return [{ bands: [poly([[1, 1], [3, 1], [3, 3], [1, 3]], red)] }, { bands: [poly([[0, 4], [4, 4], [0, 0]], purple)] }];
  }
  if (task === "parallelen") {
    return [{ bands: [poly([[0, 0], [2, 0], [2, 2], [0, 2]], blue)] }, { bands: [poly([[1, 3], [3, 3], [4, 1], [2, 1]], green)] }];
  }
  if (task === "flaeche") {
    return [{ bands: [poly([[1, 1], [2, 1], [2, 2], [1, 2]], orange)] }, { bands: [poly([[0, 0], [4, 0], [0, 4]], red)] }];
  }
  if (task === "umfang") {
    return [{ bands: [poly([[1, 1], [2, 1], [2, 2], [1, 2]], black)] }, { bands: [poly([[0, 0], [3, 0], [0, 3]], blue)] }];
  }
  if (task === "koordinaten") {
    return [{ bands: [poly([[0, 4], [2, 4], [2, 2]], red, false)] }, { bands: [poly([[0, 0], [4, 0], [4, 4], [0, 4]], green, false)] }];
  }
  return [];
}

export const STEP = 10;
export const PAD = 8;

export function centreOf(p: GeobrettProps): Nail {
  return p.centre ?? [Math.floor((p.cols - 1) / 2), Math.floor((p.rows - 1) / 2)];
}

export function segments(band: Band): [Nail, Nail][] {
  const n = ring(band);
  const m = closed(band) ? n.length : n.length - 1;
  return Array.from({ length: Math.max(0, m) }, (_, i) => [n[i], n[(i + 1) % n.length]]);
}

export function dotAt(c: number, r: number): [number, number] {
  return [PAD + c * STEP, PAD + r * STEP];
}

export function boardBox(cols: number, rows: number, caption: boolean): [number, number] {
  return [PAD * 2 + (cols - 1) * STEP, PAD * 2 + (rows - 1) * STEP + (caption ? 12 : 0)];
}
