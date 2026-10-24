// What a Halbschriftlich block stores, and the rules its steps follow.
/** A number the teacher typed: the task's index (from 0), the position (0 to 2), the value (0 to 9999). */
export type HalbschriftlichTyped = [number, number, number];
export type Rule = "any" | "yes" | "no";
export type HalbschriftlichProps = {
  /** Number of tasks on the sheet, side by side in rows of `columns`. Default 6.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of tasks per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** The Rechenart: "+" (Plus: 345 + 123 = 345 + 100 + 20 + 3) or "-" (Minus: 468 − 123 = 468 − 100 − 20 − 3). Default "+". */
  op: "+" | "-";
  /** The Zahlenraum of the first number and the result, 100 or 1000: the first number, and the result of a Plus task, are at most max. Default 1000. */
  max: number;
  /** The places of the second number: 1, 2 or 3 digits (3 only with max 1000, else it acts as 2). One step per digit that is not 0. Default 3. */
  digits: number;
  /** The Übergang at the Einer, crossing a ten: "yes" every task crosses a ten (Plus: the Einer of both numbers add up to 10 or more; Minus: the first number's Einer is smaller than the second's), "no" none does, "any" either. Default "any". */
  einer: Rule;
  /** The Übergang at the Zehner, crossing a hundred in any step, as the Übertrag of written arithmetic (Plus: the last two digits of both numbers add up to 100 or more, so 395 + 7 crosses; Minus: the first number's last two digits are smaller than the second's): "yes", "no" or "any". Counts only with max 1000. Default "any". */
  zehner: Rule;
  /** Karo: true draws 5 mm squares behind the tasks, one digit to a square; false draws plain white with a box per number. Default true. */
  grid: boolean;
  /** Stellenwerte: true draws the place letters T H Z E above each task's numbers. Default false. */
  head: boolean;
  /** true tints the second number and its parts in the steps. Default false. */
  tint: boolean;
  /** true prints the signs (+ or − and =) of the step lines on the pupils' sheet; false leaves the signs out for the pupils to write (the number boxes stay). The key always shows the full steps. Default true. */
  ops: boolean;
  /** Seed for the random tasks. The same seed always gives the same tasks. */
  seed: number;
  /** Numbers the teacher typed. Each entry is [task index from 0, position 0 to 2, value 0 to 9999]. Positions: 0 the first number, 1 the second number, 2 the result. Any two fix the task and its steps. A task with typed numbers shows exactly its typed boxes; the others are worked out from them. A task whose typed numbers do not fit is marked wrong and its key shows no answers. */
  typed?: HalbschriftlichTyped[];
};

// A task: [a, b, r] (0 where unknown), its steps as [from, part, to], which of a, b, r show on the pupils' sheet,
// whether its typed numbers do not fit or allow more than one solution, and whether it is an empty drawn task (`none`).
export type Task = {
  op: "+" | "-";
  values: number[];
  steps: [number, number, number][];
  given: boolean[];
  wrong: boolean;
  many: boolean;
  none: boolean;
};
export type Made = { tasks: Task[]; none: boolean; D: number; S: number };

export const DEFAULTS: Omit<HalbschriftlichProps, "seed"> = {
  count: 6,
  columns: 2,
  op: "+",
  max: 1000,
  digits: 3,
  einer: "any",
  zehner: "any",
  grid: true,
  head: false,
  tint: false,
  ops: true,
};
export const MAXES = [100, 1000];
// The panel's words for the three positions, in position order.
export const NAMES = ["Erste Zahl", "Zweite Zahl", "Ergebnis"];

// The exports the drawing, the panel and the insert use; the generator fills them in:
// - `sane(p: HalbschriftlichProps): HalbschriftlichProps`: the sane settings (a wrong value gives its default, as the
//   contract says; `typed` only when it has entries; `digits` and `zehner` stay as stored).
// - `acts(p: HalbschriftlichProps): { k: number; einer: Rule; zehner: Rule }`: digits and rules as they act.
// - `steps(op, a, b): [number, number, number][]`: the steps of the contract.
// - `layout(p: HalbschriftlichProps)`: { Q, D, S, CG, RG, TW, TH, rows, across, vbW, vbH, headRows } as the contract says
//   (D is 4; it calls `made` for S).
// - `heightFor(p: HalbschriftlichProps, w: number): number`: the height in mm at width w, vbH · min(w / vbW, 1).
// - `widthFor(p: HalbschriftlichProps): number`: vbW, the width the insert gives a new block.
// - `opLabel(op: "+" | "-"): string`: "+" or "−".
// - `solve(op, known: (number | null)[], drawn: number[] | null, cap = 9999): { kind: "none" } | { kind: "one" |
//   "many"; values: number[] }`: a teacher's own task from its typed positions (known[p], null where not typed), as the
//   contract says; a, b and r of a solution are 0 to cap (a ≥ 1, b ≥ 1). Exact, by algebra and counting, no search
//   budget.
// - `made(p: HalbschriftlichProps): Made`.

const pick = <T>(v: unknown, ok: readonly T[], dflt: T): T => (ok.includes(v as T) ? (v as T) : dflt);

export function sane(p: HalbschriftlichProps): HalbschriftlichProps {
  const typed = new Map<string, HalbschriftlichTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [i, pos, v] = t;
      if (i < 0 || i > 11 || pos < 0 || pos > 2 || v < 0 || v > 9999) continue;
      typed.delete(`${i}:${pos}`);
      typed.set(`${i}:${pos}`, [i, pos, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count: Number.isInteger(p.count) && p.count >= 1 && p.count <= 12 ? p.count : DEFAULTS.count,
    columns: Number.isInteger(p.columns) && p.columns >= 1 && p.columns <= 3 ? p.columns : DEFAULTS.columns,
    op: p.op === "+" || p.op === "-" ? p.op : DEFAULTS.op,
    max: MAXES.includes(p.max) ? p.max : DEFAULTS.max,
    digits: p.digits === 1 || p.digits === 2 || p.digits === 3 ? p.digits : DEFAULTS.digits,
    einer: pick<Rule>(p.einer, ["any", "yes", "no"], DEFAULTS.einer),
    zehner: pick<Rule>(p.zehner, ["any", "yes", "no"], DEFAULTS.zehner),
    grid: typeof p.grid === "boolean" ? p.grid : DEFAULTS.grid,
    head: typeof p.head === "boolean" ? p.head : DEFAULTS.head,
    tint: typeof p.tint === "boolean" ? p.tint : DEFAULTS.tint,
    ops: typeof p.ops === "boolean" ? p.ops : DEFAULTS.ops,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

export function acts(p: HalbschriftlichProps): { k: number; einer: Rule; zehner: Rule } {
  const s = sane(p);
  const k = s.max === 100 && s.digits === 3 ? 2 : s.digits;
  return { k, einer: s.einer, zehner: s.max === 1000 ? s.zehner : "any" };
}

export function opLabel(op: "+" | "-"): string {
  return op === "-" ? "−" : "+";
}
