// The Pfeilbild generator: rows of boxes joined by arrows, each arrow an operator such as "+4", "−3", "·2" or ":5". A pure
// function of the block's settings and its seed, so the editor, the thumbnail and the PDF draw the same pictures.
//
// The contract of #821, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "pfeilbild", props: PfeilbildProps }`.
// - `count` Pfeilbilder (1 to 12, default 4) in `columns` side by side (1 to 3, default 2).
// - `boxes` Kästchen per Pfeilbild: a whole number 3 to 8, or "random" (each picture draws its own 3 to 8). Default 4.
// - `max`, the Zahlenraum: one of 10, 20, 100, 1000 (default 20). Any other value gives 20.
// - `ops`, the Rechenarten: a list of "+", "-", "*", ":" (default ["+", "-"]). "*" and ":" only with max 20 or more.
// - `arrows`: "one" (default) or "both" (a back arrow under each forward arrow, with the inverse operator).
// - `given`: "start" (default), "ends" or "mixed".
// - `drawOps`: draws an ellipse around each operator place (default true).
// - `typed`: numbers the teacher typed into boxes, each entry [picture from 0, box from 0, value 0 to 9999].
// - `seed` alone gives the pictures.
//
// The generator `made` (memo of 50, `rng` from zahlenmauer.ts), per picture:
// - Its box count: `boxes`, or for "random" 3 + floor(next() * 6).
// - Up to 50 tries: a start number, then for each step one op among the allowed ops that have an operand, then the
//   operand. A try that fails is retried. None in 50: `over`, the picture is not drawn.
// - The given flags of "start", "ends" or "mixed".
// - The typed boxes of the picture: the lowest typed box is the anchor, and the other boxes follow from it through the
//   steps and the inverse steps. `wrong` when a typed box disagrees, or a number leaves 0 to max, or is not whole.
//
// The drawing (sheet.tsx `Pfeilbild`, on screen, print and in the key alike): `div.pfeilbild` holds one svg. Each
// picture `g.picture[data-picture=i]`, each box `g.box[data-box=j]`, each forward arrow `g.arrow[data-arrow=j]` with its
// label, and with arrows "both" each back arrow `g.back[data-arrow=j]`.
//
// Units: a box is D = 10 across, the gap between two boxes is G = 8, the arrow band A = 8 above the boxes, the back band
// B = A under them when arrows are "both". Pictures side by side are CG = 8 apart, rows RG = 4 apart.

import { rng } from "./zahlenmauer";

/** A number the teacher typed into a box: the picture's index (from 0), the box's index (from 0), the value (0 to 9999). */
export type PfeilbildTyped = [number, number, number];
export type PfeilbildProps = {
  /** Number of Pfeilbilder on the sheet, side by side in rows of `columns`. Default 4.
   * @minimum 1
   * @maximum 12
   */
  count: number;
  /** Number of Pfeilbilder per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** Kästchen per Pfeilbild: a whole number from 3 to 8, or "random" (Zufällig): each Pfeilbild draws its own number from 3 to 8 from the seed. Default 4.
   * @minimum 3
   * @maximum 8
   */
  boxes: number | "random";
  /** The Zahlenraum: the largest number a box may show, one of 10, 20, 100 or 1000. Any other value gives 20. Default 20. */
  max: number;
  /** The Rechenarten: "+", "-", "*" (Mal) and ":" (Geteilt), in that order, each once. "*" and ":" need max 20 or more, under that they are dropped. Empty or not a list: ["+"]. Default ["+", "-"]. */
  ops: ("+" | "-" | "*" | ":")[];
  /** The arrows: "one" for arrows in one direction, "both" for arrows in both directions. Under each forward arrow a back arrow shows the inverse operator: "+4" goes back as "−4", "·2" as ":2", ":2" as "·2". Default "one". */
  arrows: "one" | "both";
  /** Which numbers show: "start" the first box and every operator, "ends" the first and the last box (no operators; such a picture may have several right answers, so the answer key says under the pictures that other answers count too, and the block keeps a line for that note), "mixed" (gemischt) the first box and for each arrow either its operator or the box after it, so that the pupil can solve it from left to right; with "*" or ":" in `ops` a hidden operator may have two right answers ("+4" or "·2"), so the key carries the same note as with "ends". Default "start". */
  given: "start" | "ends" | "mixed";
  /** Whether each operator place has an ellipse around it, also an empty one. Default true. */
  drawOps: boolean;
  /** Seed for the random pictures. The same seed always gives the same pictures. */
  seed: number;
  /** Numbers the teacher typed into boxes. Each entry is [picture index from 0, box index from 0, value 0 to 9999]. The lowest typed box of a picture is its anchor. A picture whose numbers do not fit its operators is marked wrong. */
  typed?: PfeilbildTyped[];
};

// One operator and its operand: step j turns numbers[j] into numbers[j + 1].
export type Step = { op: "+" | "-" | "*" | ":"; n: number };

// A picture: its numbers, its steps, which boxes and operators show, whether it is wrong or does not fit the Zahlenraum.
export type Picture = { numbers: number[]; steps: Step[]; given: boolean[]; opGiven: boolean[]; wrong: boolean; over: boolean };
export type Made = { pictures: Picture[] };

export const DEFAULTS: Omit<PfeilbildProps, "seed"> = { count: 4, columns: 2, boxes: 4, max: 20, ops: ["+", "-"], arrows: "one", given: "start", drawOps: true };

const OPS: Step["op"][] = ["+", "-", "*", ":"];

// Whether x is a whole number from lo to hi.
const whole = (x: number, lo: number, hi: number) => Number.isInteger(x) && x >= lo && x <= hi;

// The settings as a pfeilbild block can take them, whatever a stored sheet holds: a wrong value gives its default, a
// typed entry that is not three whole numbers in range is dropped, and of two for the same box the last one stays.
export function sane(p: PfeilbildProps): PfeilbildProps {
  const count = whole(p.count, 1, 12) ? p.count : DEFAULTS.count;
  const columns = whole(p.columns, 1, 3) ? p.columns : DEFAULTS.columns;
  const boxes = p.boxes === "random" || whole(p.boxes, 3, 8) ? p.boxes : DEFAULTS.boxes;
  const max = [10, 20, 100, 1000].includes(p.max) ? p.max : DEFAULTS.max;
  const listed = Array.isArray(p.ops) ? OPS.filter((o) => p.ops.includes(o)) : [];
  const ops = listed.filter((o) => max >= 20 || (o !== "*" && o !== ":"));
  const typed = new Map<string, PfeilbildTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [c, b, v] = t;
      if (c < 0 || c >= count || b < 0 || b >= 8 || v < 0 || v > 9999) continue;
      typed.delete(`${c}:${b}`);
      typed.set(`${c}:${b}`, [c, b, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    count,
    columns,
    boxes,
    max,
    ops: ops.length ? ops : ["+"],
    arrows: p.arrows === "both" ? "both" : "one",
    given: p.given === "ends" || p.given === "mixed" ? p.given : "start",
    drawOps: typeof p.drawOps === "boolean" ? p.drawOps : true,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// The label of an operator with its operand: "+4", "−4" (U+2212), "·4" (U+00B7) or ":4".
const SIGN: Record<Step["op"], string> = { "+": "+", "-": "−", "*": "·", ":": ":" };
export function opLabel(step: Step): string {
  return `${SIGN[step.op]}${step.n}`;
}

// The step that undoes `step`: + and - swap, * and : swap, the operand stays.
export function inverse(step: Step): Step {
  const op = step.op === "+" ? "-" : step.op === "-" ? "+" : step.op === "*" ? ":" : "*";
  return { op, n: step.n };
}

// The drawing in svg units: a box is D across, boxes are G apart, the arrow band A high, the back band B low when the
// arrows go both ways. `vbW` and `vbH` are the viewBox of the whole drawing.
// Whether a picture of these settings can have more than one right answer, so that the key says other answers count
// too: "ends" always; "mixed" with Mal or Geteilt, where a hidden operator between two given boxes may be "+4" or "·2".
export function noted(p: Partial<Pick<PfeilbildProps, "given" | "ops">>): boolean {
  return p.given === "ends" || (p.given === "mixed" && !!p.ops?.some((o) => o === "*" || o === ":"));
}

// With a noted picture (see `noted`) a line of N units at the foot holds the key's note that other answers count too: on the pupils'
// sheet it stays empty, so that the key and the sheet have the same size.
export function layout(p: Pick<PfeilbildProps, "count" | "columns" | "boxes" | "arrows"> & Partial<Pick<PfeilbildProps, "given" | "ops">>) {
  const [D, G, A, CG, RG] = [10, 8, 8, 8, 4];
  const B = p.arrows === "both" ? A : 0;
  const N = noted(p) ? 6 : 0;
  const n = p.boxes === "random" ? 8 : p.boxes;
  const picW = n * D + (n - 1) * G;
  const picH = A + D + B;
  const rows = Math.ceil(p.count / p.columns);
  const vbW = p.columns * picW + (p.columns - 1) * CG + 1;
  const vbH = rows * picH + (rows - 1) * RG + 1 + N;
  return { D, G, A, B, N, picW, picH, CG, RG, rows, vbW, vbH };
}

// The default block is drawn at the scale S0 at 180 mm wide. A block of width w draws its boxes at that scale, and its
// height grows with the rows, so that they keep that size.
const S0 = 180 / layout(DEFAULTS).vbW;

// The height in mm of a block of width w with the props p, at which its boxes draw at least at the default scale.
export function heightFor(p: PfeilbildProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// The Spalten a block of width w keeps for `boxes` boxes: its own, or fewer when the pictures side by side would be too
// wide for the boxes to keep the default size (at least 1).
export function fitColumns(p: Pick<PfeilbildProps, "count" | "columns" | "arrows">, boxes: PfeilbildProps["boxes"], w: number): number {
  let columns = p.columns;
  while (columns > 1 && layout({ ...p, columns, boxes }).vbW * S0 > w + 0.01) columns--;
  return columns;
}

// The number that results from x and the operator with n.
function apply(op: Step["op"], x: number, n: number): number {
  return op === "+" ? x + n : op === "-" ? x - n : op === "*" ? x * n : x / n;
}

// The operands that the operator op takes from x: "+" up to max, "-" down to 0, "*" 2 to 10 and "/" 2 to 10 that divide x.
// With `left` steps still to come and no way back down (no "-" or ":"), a "+" keeps room for one each: n at most
// (max - x) / left; likewise a "-" with no way back up keeps x / left. So Plus only bis 10 fits 8 boxes.
function operands(op: Step["op"], x: number, max: number, ops: Step["op"][], left: number): number[] {
  const out: number[] = [];
  const up = op === "+" && !ops.includes("-") && !ops.includes(":") ? Math.floor((max - x) / left) : max - x;
  const down = op === "-" && !ops.includes("+") && !ops.includes("*") ? Math.floor(x / left) : x;
  if (op === "+") for (let n = 1; n <= up; n++) out.push(n);
  else if (op === "-") for (let n = 1; n <= down; n++) out.push(n);
  else if (op === "*") {
    if (x >= 1) for (let n = 2; n <= 10 && x * n <= max; n++) out.push(n);
  } else for (let n = 2; n <= 10; n++) if (x >= n && x % n === 0) out.push(n);
  return out;
}

// One try at a picture of `boxes` boxes: a start number, then a step each time. Null when a step has no operator.
function attempt(p: PfeilbildProps, boxes: number, next: () => number): { numbers: number[]; steps: Step[] } | null {
  const numbers = [Math.floor(next() * (p.max + 1))];
  const steps: Step[] = [];
  for (let j = 1; j < boxes; j++) {
    const x = numbers[j - 1];
    const usable = p.ops.map((op) => ({ op, cands: operands(op, x, p.max, p.ops, boxes - j) })).filter((u) => u.cands.length);
    if (!usable.length) return null;
    const { op, cands } = usable[Math.floor(next() * usable.length)];
    const n = cands[Math.floor(next() * cands.length)];
    steps.push({ op, n });
    numbers.push(apply(op, x, n));
  }
  return { numbers, steps };
}

// The numbers and steps of an untyped picture. None in 50 tries: `over`, with zeros and "+1" steps, not drawn.
function generated(p: PfeilbildProps, boxes: number, next: () => number): { numbers: number[]; steps: Step[]; over: boolean } {
  for (let t = 0; t < 50; t++) {
    const got = attempt(p, boxes, next);
    if (got) return { ...got, over: false };
  }
  return { numbers: Array.from({ length: boxes }, () => 0), steps: Array.from({ length: boxes - 1 }, () => ({ op: "+" as const, n: 1 })), over: true };
}

// The flags of the given boxes and operators of one picture.
function givenFlags(given: PfeilbildProps["given"], boxes: number, next: () => number): { given: boolean[]; opGiven: boolean[] } {
  const g = Array.from({ length: boxes }, () => false);
  const og = Array.from({ length: boxes - 1 }, () => false);
  if (given === "start") {
    g[0] = true;
    og.fill(true);
  } else if (given === "ends") {
    g[0] = true;
    g[boxes - 1] = true;
  } else {
    g[0] = true;
    for (let j = 0; j < boxes - 1; j++) {
      if (next() < 0.5) og[j] = true;
      else g[j + 1] = true;
    }
  }
  return { given: g, opGiven: og };
}

// The pictures of the settings. The same settings give the same pictures on every call.
const memo = new Map<string, Made>();

export function made(props: PfeilbildProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const next = rng(p.seed);
  const pictures: Picture[] = [];
  for (let i = 0; i < p.count; i++) {
    // The draws of every picture happen whatever its typed boxes, so that the pictures after it stay as they were.
    const boxes = p.boxes === "random" ? 3 + Math.floor(next() * 6) : p.boxes;
    const gen = generated(p, boxes, next);
    const flags = givenFlags(p.given, boxes, next);
    const typed = new Map<number, number>((p.typed ?? []).filter(([c, b]) => c === i && b < boxes).map(([, b, v]): [number, number] => [b, v]));
    let numbers = gen.numbers;
    let wrong = false;
    let over = gen.over;
    if (typed.size) {
      const k = Math.min(...typed.keys());
      const raw = Array.from({ length: boxes }, () => 0);
      raw[k] = typed.get(k) as number;
      for (let j = k + 1; j < boxes; j++) raw[j] = apply(gen.steps[j - 1].op, raw[j - 1], gen.steps[j - 1].n);
      for (let j = k - 1; j >= 0; j--) {
        const back = inverse(gen.steps[j]);
        raw[j] = apply(back.op, raw[j + 1], back.n);
      }
      numbers = raw.map((x, j) => {
        const t = typed.get(j);
        if (t !== undefined) {
          wrong ||= t !== x;
          return t;
        }
        wrong ||= x < 0 || x > p.max || !Number.isInteger(x);
        return Math.max(0, Math.trunc(x));
      });
      wrong ||= numbers.some((n) => n > p.max);
      over = false;
    }
    pictures.push({ numbers, steps: gen.steps, given: flags.given, opGiven: flags.opGiven, wrong, over });
  }
  const out: Made = { pictures };
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}
