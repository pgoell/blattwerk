// Geometry for the Formen added in #835. A five-point star with no spike count uses the outline
// shape.tsx has always drawn, so a sheet saved before keeps its points.

export const THOUGHT_TAIL: [number, number] = [0.18, 1];

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

// A whole number in range, or `fallback` when the sheet holds anything else.
function whole(v: unknown, lo: number, hi: number, fallback: number) {
  return typeof v === "number" && Number.isInteger(v) ? clamp(v, lo, hi) : fallback;
}

/** Corners of a Vieleck: 5 to 15, and 6 when none is set. */
export const cornersOf = (p: { corners?: unknown }) => whole(p.corners, 5, 15, 6);
/** Points of a Stern: 3 to 35, and 5 when none is set. */
export const spikesOf = (p: { spikes?: unknown }) => whole(p.spikes, 3, 35, 5);
/** Equal parts of a Bruchkreis or Bruchrechteck: 2 to 50, and 4 when none is set. */
export const partsOf = (p: { parts?: unknown }) => whole(p.parts, 2, 50, 4);
/** How many of those parts are filled. Absent means 1, and it never passes the part count. */
export const filledOf = (p: { filled?: unknown; parts?: unknown }) => whole(p.filled, 0, partsOf(p), 1);
/** Bend of a Bogen, from -1 to 1. Absent means 0.65, up off the straight line. */
export const bulgeOf = (p: { bulge?: unknown }) => (typeof p.bulge === "number" && Number.isFinite(p.bulge) ? clamp(p.bulge, -1, 1) : 0.65);

const SKETCH = new Set(["diamond", "polygon", "arc", "bow", "thought", "pie", "bars"]);

// A line keeps its own drawing. Anything else with a square or round option, and every new Form, is drawn by Sketch.
export function replaces(p: { kind?: string; form?: unknown }) {
  if (p.kind === "line" || p.kind === "arrow" || p.kind === "double") return false;
  return SKETCH.has(p.kind ?? "") || p.form === "square" || p.form === "round";
}
export function showsSketch(p: { kind?: string; form?: unknown; hub?: unknown }) {
  return replaces(p) || (p.kind === "circle" && p.hub === true);
}

// The centred square Quadratisch and Kreisförmig share. Absent means the shape uses its whole box.
export function roomOf(w: number, h: number, form?: unknown): { x: number; y: number; s: number } | undefined {
  if (form !== "square" && form !== "round") return undefined;
  const s = Math.min(w, h);
  return { x: (w - s) / 2, y: (h - s) / 2, s };
}

// A circle of diameter `s` whose box starts at `x`, `y`, inset by the stroke.
export function circlePath(x: number, y: number, s: number, e: number) {
  const r = Math.max(0, (s - 2 * e) / 2);
  const [cx, cy] = [x + s / 2, y + s / 2];
  return `M${cx - r},${cy} A${r},${r} 0 1 1 ${cx + r},${cy} A${r},${r} 0 1 1 ${cx - r},${cy} Z`;
}

export const hubAt = (w: number, h: number): [number, number] => [w / 2, h / 2];

// The four corners of a Raute: the middle of each side of the box. In a rectangle that is a rhombus.
export function diamondPoints(w: number, h: number, e: number): number[][] {
  return [
    [w / 2, e],
    [w - e, h / 2],
    [w / 2, h - e],
    [e, h / 2],
  ];
}

// A regular Vieleck with a corner at the top, stretched to the box.
export function polygonPoints(w: number, h: number, e: number, p: { corners?: unknown } = {}): number[][] {
  const n = cornersOf(p);
  const raw = Array.from({ length: n }, (_, i) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
    return [Math.cos(a), Math.sin(a)];
  });
  const xs = raw.map(([x]) => x);
  const ys = raw.map(([, y]) => y);
  const [loX, hiX, loY, hiY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const sx = hiX === loX ? 1 : (w - 2 * e) / (hiX - loX);
  const sy = hiY === loY ? 1 : (h - 2 * e) / (hiY - loY);
  return raw.map(([x, y]) => [e + (x - loX) * sx, e + (y - loY) * sy]);
}

function innerRatio(v: unknown) {
  return typeof v === "number" && Number.isFinite(v) ? clamp(v, 0.1, 0.9) : 0.38;
}

// Five points, in the measure the editor used before `spikes`: the top point is index 0.
function fivePoint(w: number, h: number, e: number, inner: number): number[][] {
  return Array.from({ length: 10 }, (_, i) => {
    const [r, a] = [i % 2 ? inner : 1, (i * Math.PI) / 5];
    return [e + (w - 2 * e) * (0.5 + (r * Math.sin(a)) / 1.902), e + ((h - 2 * e) * (1 - r * Math.cos(a))) / 1.809];
  });
}

// A star of `spikes` points. Five, or none, is `fivePoint`. Any other count sits in the circle stretched to the box,
// so the depth handle can read the same circle back.
export function starPoints(w: number, h: number, e: number, p: { spikes?: unknown; inner?: unknown } = {}): number[][] {
  const n = spikesOf(p);
  const inner = innerRatio(p.inner);
  if (n === 5) return fivePoint(w, h, e, inner);
  return Array.from({ length: 2 * n }, (_, i) => {
    const r = i % 2 ? inner : 1;
    const a = -Math.PI / 2 + (i * Math.PI) / n;
    return [e + ((Math.cos(a) * r + 1) / 2) * (w - 2 * e), e + ((Math.sin(a) * r + 1) / 2) * (h - 2 * e)];
  });
}

// The depth that puts an inner corner on `x`, `y` in a box with no stroke inset. The inverse of `starPoints` for a count other than 5.
export function starInnerAt(w: number, h: number, x: number, y: number, spikes: number) {
  const n = whole(spikes, 3, 35, 5);
  const a = -Math.PI / 2 + ((2 * n - 1) * Math.PI) / n;
  const rx = w ? (x / w) * 2 - 1 : 0;
  const ry = h ? (y / h) * 2 - 1 : 0;
  return clamp(rx * Math.cos(a) + ry * Math.sin(a), 0.1, 0.9);
}

// A quadratic from the left middle to the right. `bulge` 1 lifts the middle to the top inset, -1 drops it to the foot.
// `head` shortens the curve and returns the arrow's three corners, the tip last along the line.
export function arcGeometry(w: number, h: number, e: number, bulge: number, head: number): { curve: string; head?: number[][] } {
  const y = h / 2;
  const x0 = e;
  const x1 = Math.max(e, w - e);
  const room = Math.max(0, y - e);
  const cx = (x0 + x1) / 2;
  const cy = y - clamp(bulge, -1, 1) * room;
  let dx = x1 - cx;
  let dy = y - cy;
  const len = Math.hypot(dx, dy) || 1;
  dx /= len;
  dy /= len;
  const trim = Math.min(Math.max(head, 0), len * 0.8);
  const endX = x1 - dx * trim;
  const endY = y - dy * trim;
  const curve = `M${x0},${y} Q${cx},${cy} ${endX},${endY}`;
  if (head <= 0) return { curve };
  const wing = head / 2;
  return { curve, head: [[x1, y], [endX - dy * wing, endY + dx * wing], [endX + dy * wing, endY - dx * wing]] };
}

// Where the bend's handle stands: the middle of the curve.
export function arcHandle(w: number, h: number, e: number, bulge: number): [number, number] {
  const y = h / 2;
  const room = Math.max(0, y - e);
  return [(e + Math.max(e, w - e)) / 2, y - 0.5 * clamp(bulge, -1, 1) * room];
}

// The bulge that puts the handle at `yAt`.
export function bulgeFrom(w: number, h: number, e: number, yAt: number) {
  const y = h / 2;
  const room = y - e;
  if (room <= 0) return 0;
  return clamp((y - yAt) / (0.5 * room), -1, 1);
}

// An ellipse and three circles stepping from its edge to `tail`. Eight arcs: two for the body, two for each bubble.
export function thoughtPath(w: number, h: number, e: number, tail: [number, number]) {
  const rx = Math.max(0, (w - 2 * e) / 2);
  const ry = Math.max(0, (0.72 * (h - 2 * e)) / 2);
  const cx = w / 2;
  const cy = e + ry;
  const [tx, ty] = [tail[0] * w, tail[1] * h];
  const [dx, dy] = [tx - cx, ty - cy];
  const norm = Math.hypot(rx ? dx / rx : 0, ry ? dy / ry : 0) || 1;
  const [ex, ey] = [cx + dx / norm, cy + dy / norm];
  const radii = [Math.min(2.4, rx / 4 || 0), Math.min(1.5, rx / 6 || 0), Math.min(0.9, rx / 8 || 0)];
  const bubbles = radii.map((r, i) => {
    const t = [0.38, 0.66, 0.9][i]!;
    const [x, y] = [ex + (tx - ex) * t, ey + (ty - ey) * t];
    return `M${x - r},${y} A${r},${r} 0 1 1 ${x + r},${y} A${r},${r} 0 1 1 ${x - r},${y}`;
  });
  const body = `M${cx - rx},${cy} A${rx},${ry} 0 1 1 ${cx + rx},${cy} A${rx},${ry} 0 1 1 ${cx - rx},${cy}`;
  return [body, ...bubbles].join(" ");
}

// Wedges of a Bruchkreis, from the top, clockwise on the page. `on` is a filled one.
export function pieWedges(w: number, h: number, e: number, p: { parts?: unknown; filled?: unknown } = {}) {
  const parts = partsOf(p);
  const filled = filledOf(p);
  const [cx, cy] = [w / 2, h / 2];
  const [rx, ry] = [Math.max(0, w / 2 - e), Math.max(0, h / 2 - e)];
  return Array.from({ length: parts }, (_, i) => {
    const a0 = -Math.PI / 2 + (i * 2 * Math.PI) / parts;
    const a1 = -Math.PI / 2 + ((i + 1) * 2 * Math.PI) / parts;
    const large = a1 - a0 > Math.PI ? 1 : 0;
    const [x0, y0, x1, y1] = [cx + rx * Math.cos(a0), cy + ry * Math.sin(a0), cx + rx * Math.cos(a1), cy + ry * Math.sin(a1)];
    return { d: `M${cx},${cy} L${x0},${y0} A${rx},${ry} 0 ${large} 1 ${x1},${y1} Z`, on: i < filled };
  });
}

// Columns of a Bruchrechteck, left to right. The first `filled` ones are `on`.
export function barStrips(w: number, h: number, e: number, p: { parts?: unknown; filled?: unknown } = {}) {
  const parts = partsOf(p);
  const filled = filledOf(p);
  const width = Math.max(0, w - 2 * e);
  const each = width / parts;
  const high = Math.max(0, h - 2 * e);
  return Array.from({ length: parts }, (_, i) => ({ x: e + i * each, y: e, w: each, h: high, on: i < filled }));
}
