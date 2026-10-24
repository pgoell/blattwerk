// What a Zehnerfeld stores, and the box one task takes on the page.
/** A number the teacher typed: the task's index (from 0), the position (0 to 2), the value (0 to 999; above the field's size it never fits). */
export type ZehnerfeldTyped = [number, number, number];
/** A dot the teacher set: the task's index (from 0), the dot (0 to 99), the mark (1, 2 or 3). */
export type ZehnerfeldMark = [number, number, number];
export type Field = "zehn" | "zehn2" | "zwanzig" | "hundert";
export type Cross = "any" | "yes" | "no";
export type ZehnerfeldProps = {
  /** Number of tasks (fields) on the sheet, side by side in rows of `columns`. Default 4.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of tasks per row. Default 2.
   * @minimum 1
   * @maximum 4
   */
  columns: number;
  /** The Typ of field: "zehn" Zehnerfeld 1 × 10, "zehn2" Zehnerfeld 2 × 5, "zwanzig" Zwanzigerfeld 2 × 10, "hundert" Hunderterfeld 10 × 10. The dots count row by row from the top left. Default "zwanzig". */
  field: Field;
  /** The Rechenart: "+" (Plus: the first number's dots in colour 1, the second number's in colour 2) or "-" (Minus: the first number's dots in colour 1, the second number's of them struck through). Default "+". */
  op: "+" | "-";
  /** The Aufgabentyp: "dots" the field shows the dots and the pupil writes the task; "write" the task's two numbers show and the pupil paints the dots and writes the result; "mixed" the two by turns, starting with "dots". Default "dots". */
  task: "dots" | "write" | "mixed";
  /** The Zahlenraum: 5, 10, 20, 50 or 100, at most the field's size (10, 20 or 100). Plus results and Minus first numbers stay within it. Default 20. */
  max: number;
  /** The Zehnerübergang: "yes" every task crosses a ten (Plus: the Einer of both numbers add up to more than 10, as 8 + 5; Minus: the Einer of the result and the second number do, as 13 − 5), "no" none does (6 + 4 = 10 and 20 − 4 do not cross), "any" either. Counts only with the Zwanziger- and Hunderterfeld. Default "any". */
  cross: Cross;
  /** Trennlinien: true draws a strong line after each five dots, across and down. Default true. */
  lines: boolean;
  /** Farben: "color" red and blue, "grey" Graustufen (black and grey, for black and white copies), "own" the colours `color1` and `color2`. Default "color". */
  colors: "color" | "grey" | "own";
  /** The first colour with `colors` "own", as "#rrggbb". Default "#e3463b". */
  color1?: string;
  /** The second colour with `colors` "own", as "#rrggbb". Default "#1d4ea6". */
  color2?: string;
  /** Punkte selbst setzen: true shows in each field exactly the dots in `marks` and no task; the number boxes stay empty for the pupil. Default false. */
  manual: boolean;
  /** The dots the teacher set with `manual`. Each entry is [task index from 0, dot 0 to 99 counted row by row, mark 1 colour 1, 2 colour 2 or 3 colour 1 struck through]. */
  marks?: ZehnerfeldMark[];
  /** Seed for the random tasks. The same seed always gives the same tasks. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [task index from 0, position 0 to 2, value 0 to 999]. Positions: 0 the first number, 1 the second number, 2 the result. The other positions are worked out from them; a task whose typed numbers do not fit the field is marked wrong and shows no dots and no numbers. */
  typed?: ZehnerfeldTyped[];
};

// A task: [a, b, r] (0 where unknown), its kind as it shows ("dots" or "write"), its dots (C marks, 0 to 3, the task's
// own picture, also for a "write" task), whether its typed numbers do not fit, and whether it is an empty drawn task.
export type Task = { values: number[]; kind: "dots" | "write"; dots: number[]; wrong: boolean; none: boolean };
export type Made = { tasks: Task[]; none: boolean };

export const DEFAULTS: Omit<ZehnerfeldProps, "seed"> = {
  count: 4,
  columns: 2,
  field: "zwanzig",
  op: "+",
  task: "dots",
  max: 20,
  cross: "any",
  lines: true,
  colors: "color",
  manual: false,
};
export const MAXES = [5, 10, 20, 50, 100];
export const COLOR = ["#e3463b", "#1d4ea6"] as const;
export const GREY = ["#222222", "#9a9a9a"] as const;
// The field's rows and columns by Typ.
export const SHAPE: Record<Field, { rows: number; cols: number }> = {
  zehn: { rows: 1, cols: 10 },
  zehn2: { rows: 2, cols: 5 },
  zwanzig: { rows: 2, cols: 10 },
  hundert: { rows: 10, cols: 10 },
};

// The exports the drawing, the panel and the insert use; the generator fills them in:
// - `sane(p: ZehnerfeldProps): ZehnerfeldProps`: the sane settings (a wrong value gives its default, as the contract
//   says; `typed` and `marks` only when they have entries; `max`, `cross`, `color1`, `color2` stay as stored when valid).
// - `acts(p): { C: number; M: number; cross: Cross; rows: number; cols: number }`: the field and the rules as they act.
// - `colorsOf(p): [string, string]`: the two colours as they draw.
// - `crosses(op, a, b): boolean`: the Zehnerübergang of the contract.
// - `picture(op, a, b, C): number[]`: the C marks of the task's field.
// - `solve(op, known: (number | null)[], drawn: number[] | null, C): number[] | null`: a teacher's own task [a, b, r]
//   from its typed positions, or null when none fits; exact, by a plain walk.
// - `layout(p)`: { U, B, LH, G, FW, FH, LW, TW, TH, CG, RG, rows, across, vbW, vbH } as the contract says.
// - `heightFor(p, w: number): number` and `widthFor(p): number` (vbW).
// - `opLabel(op): string`: "+" or "−".
// - `made(p): Made`.
const pick = <T>(v: unknown, ok: readonly T[], dflt: T): T => (ok.includes(v as T) ? (v as T) : dflt);
const isColor = (v: unknown): v is string => typeof v === "string" && /^#[0-9a-f]{6}$/.test(v);

export function sane(p: ZehnerfeldProps): ZehnerfeldProps {
  const field = pick<Field>(p.field, ["zehn", "zehn2", "zwanzig", "hundert"], DEFAULTS.field);
  const C = SHAPE[field].rows * SHAPE[field].cols;
  const marks = new Map<string, ZehnerfeldMark>();
  if (Array.isArray(p.marks)) {
    for (const m of p.marks) {
      if (!Array.isArray(m) || m.length !== 3 || !m.every((x) => Number.isInteger(x))) continue;
      const [t, d, mk] = m;
      if (t < 0 || t > 11 || d < 0 || d > 99 || mk < 1 || mk > 3) continue;
      marks.delete(`${t}:${d}`);
      marks.set(`${t}:${d}`, [t, d, mk]);
    }
  }
  const typed = new Map<string, ZehnerfeldTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [i, pos, v] = t;
      if (i < 0 || i > 11 || pos < 0 || pos > 2 || v < 0 || v > 999) continue;
      typed.delete(`${i}:${pos}`);
      typed.set(`${i}:${pos}`, [i, pos, v]);
    }
  }
  return {
    count: Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : DEFAULTS.count,
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 4 ? p.columns : DEFAULTS.columns,
    field,
    op: pick<"+" | "-">(p.op, ["+", "-"], DEFAULTS.op),
    task: pick(p.task, ["dots", "write", "mixed"] as const, DEFAULTS.task),
    max: MAXES.includes(p.max) ? p.max : C,
    cross: pick<Cross>(p.cross, ["any", "yes", "no"], DEFAULTS.cross),
    lines: typeof p.lines === "boolean" ? p.lines : DEFAULTS.lines,
    colors: pick(p.colors, ["color", "grey", "own"] as const, DEFAULTS.colors),
    color1: isColor(p.color1) ? p.color1 : COLOR[0],
    color2: isColor(p.color2) ? p.color2 : COLOR[1],
    manual: typeof p.manual === "boolean" ? p.manual : DEFAULTS.manual,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(marks.size ? { marks: [...marks.values()] } : {}),
    ...(typed.size ? { typed: [...typed.values()] } : {}),
  };
}

export function acts(p: ZehnerfeldProps): { C: number; M: number; cross: Cross; rows: number; cols: number } {
  const s = sane(p);
  const { rows, cols } = SHAPE[s.field];
  const C = rows * cols;
  return { C, M: Math.min(s.max, C), cross: C >= 20 ? s.cross : "any", rows, cols };
}

export function colorsOf(p: ZehnerfeldProps): [string, string] {
  const s = sane(p);
  if (s.colors === "own") return [s.color1 ?? COLOR[0], s.color2 ?? COLOR[1]];
  return s.colors === "grey" ? [GREY[0], GREY[1]] : [COLOR[0], COLOR[1]];
}

export function layout(p: ZehnerfeldProps) {
  const s = sane(p);
  const { rows: fieldRows, cols: fieldCols } = SHAPE[s.field];
  const U = 6;
  const B = 10;
  const LH = 8;
  const G = 3;
  const SIGN = 5;
  const CG = 6;
  const RG = 6;
  const FW = fieldCols * U;
  const FH = fieldRows * U;
  const LW = 3 * B + 2 * SIGN;
  const TW = Math.max(FW, LW);
  const TH = FH + G + LH;
  const across = Math.min(s.columns, s.count);
  const rows = Math.ceil(s.count / s.columns);
  const vbW = across * TW + (across - 1) * CG + 1;
  const vbH = rows * TH + (rows - 1) * RG + 1;
  return { U, B, LH, G, FW, FH, LW, TW, TH, CG, RG, rows, across, vbW, vbH };
}

export function heightFor(p: ZehnerfeldProps, w: number): number {
  const l = layout(p);
  return l.vbH * Math.min(w / l.vbW, 1);
}

export function widthFor(p: ZehnerfeldProps): number {
  return layout(p).vbW;
}

export function opLabel(op: "+" | "-"): string {
  return op === "-" ? "−" : "+";
}
