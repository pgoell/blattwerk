// The Diagramm: bars (Balken), columns (Säulen) or a pie (Kreis) from a few values.
//
// Stored shape: a block `{ type: "diagramm", props: DiagrammProps }`. A point's `value` is what the pupil
// sees, a number and an optional unit such as "3,5 kg". Empty means the pupil draws the bar. `answer` is what
// the Lösungen draw then. `sane` never throws. `chart` is the drawing, in a box of VIEW units, origin top left.

export const COLORS = ["#c0392b", "#1f6feb", "#1a7f37", "#d97706", "#6f42c1", "#222222"] as const;
export const VIEW = { w: 200, h: 120 };

export type ChartKind = "balken" | "saeulen" | "kreis";
export type ValuePlace = "keine" | "innen" | "aussen";
export type ChartAxes = "keine" | "x" | "y" | "beide";
export type ChartGrid = "keine" | "haupt" | "zwischen";

export type Point = {
  /** The value the pupil sees: a number and an optional unit, such as "3,5 kg". Empty when the pupil draws the bar. */
  value: string;
  /** The label of the point, on the category axis and in the legend. */
  label: string;
  /** Colour of the bar or slice, `#` and six hex digits. */
  color: string;
  /** The value the Lösungen draw when `value` is empty, in the same shape. Absent when the pupil's sheet already shows the bar. */
  answer?: string;
};

export type DiagrammProps = {
  /** Balken are horizontal bars, Säulen are vertical columns, Kreis is a pie. */
  kind: ChartKind;
  /** The data points, in order, at most 8. */
  points: Point[];
  /** Whether a legend is drawn. */
  legend: boolean;
  /** Where a value is written: nowhere, inside the bar or slice, or outside it. */
  values: ValuePlace;
  /** Which axes are drawn. A pie draws none. */
  axes: ChartAxes;
  /** Title of the horizontal axis. Empty draws none. */
  xTitle: string;
  /** Title of the vertical axis. Empty draws none. */
  yTitle: string;
  /** Gridlines: none, the main steps, or the main steps and the steps between them. A pie draws none. */
  grid: ChartGrid;
  /** Kept so a sheet made with the other maths blocks still carries a seed. The chart does not roll from it. */
  seed: number;
};

type Plot = { x: number; y: number; w: number; h: number };
type Bar = Plot & { i: number; color: string; answer: boolean };
type Slice = { i: number; d: string; color: string; answer: boolean; sweep: number; lx: number; ly: number; ox: number; oy: number };
type Mark = { i: number; x: number; y: number; text: string; anchor: "start" | "middle" | "end"; answer: boolean };
type Segment = { x1: number; y1: number; x2: number; y2: number };
type Drawn = {
  plot: Plot;
  bars: Bar[];
  slices: Slice[];
  values: Mark[];
  cats: Mark[];
  axes: (Segment & { dir: "x" | "y" })[];
  titles: { axis: "x" | "y"; x: number; y: number; text: string }[];
  grid: (Segment & { step: "haupt" | "zwischen" })[];
  legend: { i: number; x: number; y: number; color: string; text: string }[];
  ticks: { x: number; y: number; text: string; anchor: "start" | "middle" | "end" }[];
};

export const DEFAULTS: DiagrammProps = {
  kind: "saeulen",
  points: [
    { value: "4", label: "A", color: COLORS[0] },
    { value: "6", label: "B", color: COLORS[1] },
    { value: "2", label: "C", color: COLORS[2] },
  ],
  legend: true,
  values: "aussen",
  axes: "beide",
  xTitle: "",
  yTitle: "",
  grid: "haupt",
  seed: 0,
};

const HEX = /^#[0-9a-f]{6}$/i;
const TEXT = 40;
const KINDS = ["balken", "saeulen", "kreis"] as const satisfies readonly ChartKind[];
const PLACES = ["keine", "innen", "aussen"] as const satisfies readonly ValuePlace[];
const AXES = ["keine", "x", "y", "beide"] as const satisfies readonly ChartAxes[];
const GRIDS = ["keine", "haupt", "zwischen"] as const satisfies readonly ChartGrid[];

const one = <T extends string>(v: unknown, allowed: readonly T[], fallback: T): T =>
  typeof v === "string" && (allowed as readonly string[]).includes(v) ? (v as T) : fallback;

const copy = (points: Point[]) => points.map((p) => ({ ...p }));

export function read(text: string): { n: number; text: string } | undefined {
  const trimmed = text.trim();
  const m = /^([+-]?\d+(?:[.,]\d+)?)(.*)$/.exec(trimmed);
  if (!m) return;
  if (m[2].trim() && /\d/.test(m[2])) return;
  const n = Number(m[1].replace(",", "."));
  if (!Number.isFinite(n) || n < 0) return;
  return { n, text: trimmed };
}

function pointOf(v: unknown, i: number): Point | undefined {
  if (!v || typeof v !== "object" || Array.isArray(v)) return;
  const raw = v as Record<string, unknown>;
  if ("value" in raw && raw.value !== undefined && typeof raw.value !== "string") return;
  if ("label" in raw && raw.label !== undefined && typeof raw.label !== "string") return;
  if ("answer" in raw && raw.answer !== undefined && typeof raw.answer !== "string") return;
  const value = typeof raw.value === "string" ? raw.value.slice(0, TEXT) : "";
  const label = typeof raw.label === "string" ? raw.label.slice(0, TEXT) : "";
  const color = typeof raw.color === "string" && HEX.test(raw.color) ? raw.color.toLowerCase() : COLORS[i % COLORS.length];
  const answer = typeof raw.answer === "string" ? raw.answer.slice(0, TEXT) : "";
  const point: Point = { value, label, color };
  if (answer.trim()) point.answer = answer;
  return point;
}

export function sane(v: unknown): DiagrammProps {
  if (v == null || typeof v !== "object" || Array.isArray(v)) return { ...DEFAULTS, points: copy(DEFAULTS.points) };
  const raw = v as Record<string, unknown>;
  const points = Array.isArray(raw.points)
    ? raw.points.slice(0, 8).map(pointOf).filter((p): p is Point => !!p)
    : copy(DEFAULTS.points);
  return {
    kind: one(raw.kind, KINDS, DEFAULTS.kind),
    points,
    legend: typeof raw.legend === "boolean" ? raw.legend : DEFAULTS.legend,
    values: one(raw.values, PLACES, DEFAULTS.values),
    axes: one(raw.axes, AXES, DEFAULTS.axes),
    xTitle: typeof raw.xTitle === "string" ? raw.xTitle.slice(0, TEXT) : "",
    yTitle: typeof raw.yTitle === "string" ? raw.yTitle.slice(0, TEXT) : "",
    grid: one(raw.grid, GRIDS, DEFAULTS.grid),
    seed: typeof raw.seed === "number" && Number.isInteger(raw.seed) ? raw.seed : 0,
  };
}

const num = (n: number) => String(Math.round(n * 100) / 100).replace(".", ",");

function scale(max: number) {
  if (!(max > 0)) return { top: 1, major: 1, minor: 0.5 };
  const rough = max / 4;
  const pow = 10 ** Math.floor(Math.log10(rough));
  const n = rough / pow;
  const major = (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;
  const top = Math.ceil((max - 1e-9) / major) * major;
  return { top, major, minor: major / 2 };
}

type Shown = { i: number; n: number; text: string; answer: boolean; point: Point };

function shown(points: Point[], solved: boolean): Shown[] {
  const out: Shown[] = [];
  points.forEach((point, i) => {
    const own = read(point.value);
    if (own) out.push({ i, n: own.n, text: own.text, answer: false, point });
    else if (solved && point.answer) {
      const key = read(point.answer);
      if (key) out.push({ i, n: key.n, text: key.text, answer: true, point });
    }
  });
  return out;
}

function frame(p: DiagrammProps) {
  const pie = p.kind === "kreis";
  const showX = !pie && (p.axes === "x" || p.axes === "beide");
  const showY = !pie && (p.axes === "y" || p.axes === "beide");
  const legend = p.legend && p.points.length > 0;
  const bottom = 4 + (pie ? 0 : p.kind === "saeulen" ? 14 : showX ? 10 : 2) + (showX && p.xTitle.trim() ? 8 : 0) + (legend ? 16 : 0);
  const left = 4 + (pie ? 0 : p.kind === "balken" ? 36 : showY ? 18 : 2) + (showY && p.yTitle.trim() ? 10 : 0);
  const plot = { x: left, y: 8, w: VIEW.w - left - 6, h: VIEW.h - 8 - bottom };
  return { plot, showX, showY, legend, legendY: VIEW.h - 8 };
}

function wedge(cx: number, cy: number, r: number, a0: number, sweep: number): string {
  if (sweep >= Math.PI * 2 - 1e-4) {
    return `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy} A ${r} ${r} 0 1 1 ${cx - r} ${cy} Z`;
  }
  const at = (a: number) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const [x0, y0] = at(a0);
  const [x1, y1] = at(a0 + sweep);
  const large = sweep > Math.PI ? 1 : 0;
  return `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`;
}

export function chart(props: unknown, solved = false): Drawn {
  const p = sane(props);
  const { plot, showX, showY, legend, legendY } = frame(p);
  const marks = shown(p.points, solved);
  const { top, major, minor } = scale(Math.max(0, ...marks.map((m) => m.n)));
  const bars: Bar[] = [];
  const slices: Slice[] = [];
  const values: Mark[] = [];
  const cats: Mark[] = [];
  const n = Math.max(p.points.length, 1);
  const place = (m: Shown, x: number, y: number, anchor: Mark["anchor"]) => {
    if (p.values === "keine") return;
    values.push({ i: m.i, x, y, text: m.text, anchor, answer: m.answer });
  };

  if (p.kind === "kreis") {
    const total = marks.reduce((sum, m) => sum + m.n, 0);
    const r = Math.min(plot.w, plot.h) * 0.36;
    const [cx, cy] = [plot.x + plot.w / 2, plot.y + plot.h / 2];
    let angle = -Math.PI / 2;
    for (const m of marks) {
      if (!(m.n > 0) || !(total > 0)) continue;
      const sweep = (m.n / total) * Math.PI * 2;
      const mid = angle + sweep / 2;
      const at = (dist: number) => [cx + dist * Math.cos(mid), cy + dist * Math.sin(mid)];
      const [lx, ly] = at(r * 0.6);
      const [ox, oy] = at(r * 1.2);
      slices.push({ i: m.i, d: wedge(cx, cy, r, angle, sweep), color: m.point.color, answer: m.answer, sweep, lx, ly, ox, oy });
      place(m, p.values === "innen" ? lx : ox, p.values === "innen" ? ly : oy, "middle");
      if (!legend && m.point.label) cats.push({ i: m.i, x: ox, y: oy + (p.values === "keine" ? 0 : 5), text: m.point.label, anchor: "middle", answer: false });
      angle += sweep;
    }
  } else if (p.kind === "balken") {
    const slot = plot.h / n;
    const bh = slot * 0.62;
    for (const m of marks) {
      const bar = { i: m.i, x: plot.x, y: plot.y + slot * m.i + (slot - bh) / 2, w: (m.n / top) * plot.w, h: bh, color: m.point.color, answer: m.answer };
      bars.push(bar);
      place(m, p.values === "innen" ? bar.x + bar.w / 2 : bar.x + bar.w + 2, bar.y + bar.h / 2, p.values === "innen" ? "middle" : "start");
    }
    p.points.forEach((point, i) => {
      if (point.label) cats.push({ i, x: plot.x - 2, y: plot.y + slot * i + slot / 2, text: point.label, anchor: "end", answer: false });
    });
  } else {
    const slot = plot.w / n;
    const bw = slot * 0.62;
    for (const m of marks) {
      const bh = (m.n / top) * plot.h;
      const bar = { i: m.i, x: plot.x + slot * m.i + (slot - bw) / 2, y: plot.y + plot.h - bh, w: bw, h: bh, color: m.point.color, answer: m.answer };
      bars.push(bar);
      place(m, bar.x + bar.w / 2, p.values === "innen" ? bar.y + bar.h / 2 : bar.y - 3, "middle");
    }
    p.points.forEach((point, i) => {
      if (point.label) cats.push({ i, x: plot.x + slot * i + slot / 2, y: plot.y + plot.h + 5, text: point.label, anchor: "middle", answer: false });
    });
  }

  const axes: Drawn["axes"] = [];
  if (showX) axes.push({ dir: "x", x1: plot.x, y1: plot.y + plot.h, x2: plot.x + plot.w, y2: plot.y + plot.h });
  if (showY) axes.push({ dir: "y", x1: plot.x, y1: plot.y, x2: plot.x, y2: plot.y + plot.h });
  const titles: Drawn["titles"] = [];
  if (showX && p.xTitle.trim()) titles.push({ axis: "x", x: plot.x + plot.w / 2, y: plot.y + plot.h + (p.kind === "saeulen" ? 12 : 8), text: p.xTitle.trim() });
  if (showY && p.yTitle.trim()) titles.push({ axis: "y", x: 8, y: plot.y + plot.h / 2, text: p.yTitle.trim() });

  const grid: Drawn["grid"] = [];
  const ticks: Drawn["ticks"] = [];
  const valueAxis = p.kind === "saeulen" ? showY : p.kind === "balken" ? showX : false;
  if (p.kind !== "kreis" && (p.grid !== "keine" || valueAxis)) {
    const step = p.grid === "zwischen" ? minor : major;
    const count = Math.round(top / (p.grid === "keine" ? major : step));
    for (let i = 0; i <= count; i++) {
      const v = Math.round(i * (p.grid === "keine" ? major : step) * 1000) / 1000;
      if (v > top + 1e-6) continue;
      const along = p.kind === "balken" ? plot.x + (v / top) * plot.w : plot.y + plot.h - (v / top) * plot.h;
      const main = Math.abs(v / major - Math.round(v / major)) < 1e-6;
      if (p.grid !== "keine" && v > 0) {
        grid.push(
          p.kind === "balken"
            ? { step: main ? "haupt" : "zwischen", x1: along, y1: plot.y, x2: along, y2: plot.y + plot.h }
            : { step: main ? "haupt" : "zwischen", x1: plot.x, y1: along, x2: plot.x + plot.w, y2: along },
        );
      }
      if (valueAxis && (p.grid === "keine" || main)) {
        ticks.push(
          p.kind === "balken"
            ? { x: along, y: plot.y + plot.h + 5, text: num(v), anchor: "middle" }
            : { x: plot.x - 2, y: along, text: num(v), anchor: "end" },
        );
      }
    }
  }

  const legendItems = legend
    ? p.points.map((point, i) => ({ i, x: 8 + (i % 4) * 48, y: legendY - Math.floor(i / 4) * 8, color: point.color, text: point.label }))
    : [];
  return { plot, bars, slices, values, cats, axes, titles, grid, legend: legendItems, ticks };
}
