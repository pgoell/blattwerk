// The stored settings of a Textaufgabe, and the size of its drawing. `sane` is what a block keeps of
// whatever a sheet stored: a wrong value becomes the default.

export const THEMES = ["kurz", "sach", "raetsel", "zeit", "geld"] as const;
export const OPS = ["+", "-", "*", ":"] as const;
export type Theme = (typeof THEMES)[number];
export type TextOp = (typeof OPS)[number];
export type Carry = "any" | "yes" | "no";
export type Part = "text" | "frage" | "rechnung" | "antwort";

export type TextaufgabeWritten = {
  /** The story (Text) the teacher wrote for this task. */
  text: string;
  /** The question (Frage) the teacher wrote for this task. */
  frage: string;
  /** The working (Rechnung) the teacher wrote for this task. A line break starts a new row. */
  rechnung: string;
  /** The answer (Antwort) the teacher wrote for this task. */
  antwort: string;
};

export type TextaufgabeProps = {
  /** Number of Textaufgaben, one under the other. Default 2.
   * @minimum 1
   * @maximum 4
   */
  count: number;
  /** The Themen the stories are drawn from: "kurz" (kurze Texte), "sach" (Sachaufgaben), "raetsel" (Rätsel), "zeit" (Zeit) and "geld" (Geld). Default ["sach"]. */
  themes: Theme[];
  /** The Rechenarten: "+", "-", "*" (Mal) and ":" (Geteilt), in that order, each once. Empty or not a list: ["+"]. Default ["+"]. */
  ops: TextOp[];
  /** The Komplexität: 1 for one step, 2 for two steps. Any other value gives 1. Default 1. */
  steps: 1 | 2;
  /** The Zahlenraum: the largest number a task may use, one of 10, 20, 100 or 1000. Geld counts in euros, a Dauer in minutes. Any other value gives 20. Default 20. */
  max: number;
  /** The Zahlen: "whole" for natürliche Zahlen, "decimal" for Kommazahlen (two places). Geld is always Kommazahlen, a Zeit stays a clock. Default "whole". */
  numbers: "whole" | "decimal";
  /** The Übertrag of an addition or a subtraction: "any" (egal), "yes" (mit Übergang) or "no" (ohne Übergang). It is a ten, or a euro for Kommazahlen. Mal and Geteilt ignore it. Default "any". */
  carry: Carry;
  /** Whether the Frage is printed for the pupil. The Lösungen fill it when it is not. Default true. */
  frage: boolean;
  /** Whether the Rechnung is printed for the pupil. The Lösungen fill it when it is not. Default false. */
  rechnung: boolean;
  /** Whether the Antwort is printed for the pupil. The Lösungen fill it when it is not. Default false. */
  antwort: boolean;
  /** Whether a drawing box (Zeichenfeld) stands above the Rechnung. Default false. */
  sketch: boolean;
  /** The height of the Rechnung: "auto" (one row per step, plus one row to write in) or a number of rows from 1 to 8. Default "auto".
   * @minimum 1
   * @maximum 8
   */
  rows: "auto" | number;
  /** Manual mode: the teacher writes the Text, the Frage, the Rechnung and the Antwort. Default false. */
  manual: boolean;
  /** Which Zeit stories are drawn when the theme "zeit" is on: "punkt" (Zeitpunkte), "dauer" (Dauern) or "both". Default "both". */
  zeit: "punkt" | "dauer" | "both";
  /** Seed for the stories and the numbers. The same seed always gives the same tasks. */
  seed: number;
  /** The four parts the teacher wrote, one entry per task, in order. Used when manual is on. */
  written?: TextaufgabeWritten[];
};

export const DEFAULTS: Omit<TextaufgabeProps, "seed"> = {
  count: 2,
  themes: ["sach"],
  ops: ["+"],
  steps: 1,
  max: 20,
  numbers: "whole",
  carry: "any",
  frage: true,
  rechnung: false,
  antwort: false,
  sketch: false,
  rows: "auto",
  manual: false,
  zeit: "both",
};

const whole = (x: unknown, lo: number, hi: number): x is number => typeof x === "number" && Number.isInteger(x) && x >= lo && x <= hi;

function writtenOf(raw: unknown): TextaufgabeWritten[] | undefined {
  if (!Array.isArray(raw)) return undefined;
  const out: TextaufgabeWritten[] = [];
  for (const item of raw) {
    if (out.length >= 4) break;
    if (!item || typeof item !== "object") continue;
    const row = item as Record<string, unknown>;
    if (typeof row.text !== "string" || typeof row.frage !== "string" || typeof row.rechnung !== "string" || typeof row.antwort !== "string") continue;
    out.push({ text: row.text.slice(0, 400), frage: row.frage.slice(0, 400), rechnung: row.rechnung.slice(0, 400), antwort: row.antwort.slice(0, 400) });
  }
  return out.length ? out : undefined;
}

export function sane(p: TextaufgabeProps): TextaufgabeProps {
  const themes = THEMES.filter((t) => Array.isArray(p.themes) && p.themes.includes(t));
  const ops = OPS.filter((o) => Array.isArray(p.ops) && p.ops.includes(o));
  const written = writtenOf(p.written);
  return {
    count: whole(p.count, 1, 4) ? p.count : DEFAULTS.count,
    themes: themes.length ? themes : [...DEFAULTS.themes],
    ops: ops.length ? ops : [...DEFAULTS.ops],
    steps: p.steps === 2 ? 2 : 1,
    max: p.max === 10 || p.max === 20 || p.max === 100 || p.max === 1000 ? p.max : DEFAULTS.max,
    numbers: p.numbers === "decimal" ? "decimal" : "whole",
    carry: p.carry === "yes" || p.carry === "no" ? p.carry : "any",
    frage: typeof p.frage === "boolean" ? p.frage : DEFAULTS.frage,
    rechnung: typeof p.rechnung === "boolean" ? p.rechnung : DEFAULTS.rechnung,
    antwort: typeof p.antwort === "boolean" ? p.antwort : DEFAULTS.antwort,
    sketch: typeof p.sketch === "boolean" ? p.sketch : DEFAULTS.sketch,
    rows: p.rows === "auto" || whole(p.rows, 1, 8) ? p.rows : "auto",
    manual: typeof p.manual === "boolean" ? p.manual : false,
    zeit: p.zeit === "punkt" || p.zeit === "dauer" ? p.zeit : "both",
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(written ? { written } : {}),
  };
}

// The story is always on the sheet. A Frage, a Rechnung or an Antwort that the pupil does not get is filled in the Lösungen.
export function visible(part: Part, p: Pick<TextaufgabeProps, "frage" | "rechnung" | "antwort">, solved: boolean): boolean {
  if (part === "text") return true;
  return p[part] || solved;
}

export const LINE = 4.4;
export const TEXT_LINES = 3;
export const FRAGE_LINES = 2;
export const ANTWORT = 7;
export const SKETCH = 18;
export const GAP = 3;
export const PAD = 1;
export const Q = 5;

export function rechnungRows(p: Pick<TextaufgabeProps, "rows" | "steps">): number {
  return p.rows === "auto" ? p.steps + 1 : p.rows;
}

export function layout(p: TextaufgabeProps) {
  const s = sane(p);
  const rows = rechnungRows(s);
  const taskH = PAD + TEXT_LINES * LINE + FRAGE_LINES * LINE + (s.sketch ? SKETCH : 0) + rows * Q + ANTWORT;
  const vbH = s.count * taskH + Math.max(0, s.count - 1) * GAP;
  return { rows, taskH, vbH, LINE, TEXT_LINES, FRAGE_LINES, ANTWORT, SKETCH, GAP, PAD, Q };
}

export function heightFor(p: TextaufgabeProps, w: number): number {
  void w;
  return Math.round(layout(p).vbH * 100) / 100;
}
