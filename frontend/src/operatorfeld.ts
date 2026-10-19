// The Operatorfeld generator: number boxes linked by operator ellipses such as "+4", "−3", "·2" or ":5". Without a
// centre (ohne Zentrum) the boxes stand in a closed ring and each pair of neighbours is one task; with a centre (mit
// Zentrum) one number in the middle is linked to every outer box. A pure function of the block's settings and its seed,
// so the editor, the thumbnail and the PDF draw the same fields.
//
// The contract of #822, which the generator, the drawing and the panel keep:
//
// Stored shape: a block `{ type: "operatorfeld", props: OperatorfeldProps }`.
// - `centre`: false (default) ohne Zentrum, true mit Zentrum.
// - `count` Operatorfelder (1 to 6, default 2) in `columns` side by side (1 to 3, default 2).
// - `boxes` Kästchen per field: 3 to 8 (default 4). Ohne Zentrum the ring's boxes, mit Zentrum the outer boxes.
// - `max`, the Zahlenraum: one of 10, 20, 100, 1000 (default 20). Any other value gives 20.
// - `ops`, the Rechenarten: a list of "+", "-", "*", ":" (default ["+", "-"]). "*" and ":" only ohne Zentrum and with
//   max 20 or more. Several checked: each link draws its own (gemischt).
// - `only`, the Einschränkung: "none" (default), "tens" (every number and every "+" or "−" operand a multiple of 10, from
//   max 100) or "hundreds" (multiples of 100, max 1000). Too small a max gives "none".
// - `given`: "start" (default: the first box, or the centre, and every operator), "ops" (every box, no operator) or
//   "mixed" (the first box, or the centre, and for each link either its operator or its other box).
// - `drawOps`: draws an ellipse around each operator place (default true).
// - `typed`: numbers the teacher typed into boxes, each entry [field from 0, box from 0, value 0 to 9999].
// - `seed` alone gives the fields.
//
// Boxes and links of one field:
// - Ohne Zentrum: boxes 0 to k-1 around the ring, clockwise from the top. Link j joins box j and box (j + 1) % k.
// - Mit Zentrum: box 0 is the centre, boxes 1 to k the outer ones, clockwise from the top. Link j joins box 0 and box j + 1.
// - Each link has a direction, `from` and `to` (box indices): numbers[from] op n = numbers[to]. The drawing puts the
//   arrow head at `to`. Mit Zentrum every generated link goes from the centre out (a typed one may turn, see below).
//
// The generator `made` (memo of 50, `rng` from zahlenmauer.ts), per field, in units u (1, 10 for "tens", 100 for
// "hundreds") up to M = max / u, the numbers and the "+" and "−" operands times u at the end ("·" and ":" operands stay):
// - Up to 50 tries. None fits: `over`, the field is not drawn.
// - Mit Zentrum: the centre C from 0 to M, then for each outer box an op among `ops` that has an operand from C ("+" n
//   from 1 to M - C, "−" n from 1 to C); outer = C op n. Up to 10 draws per box for a number no other outer box has.
// - Ohne Zentrum: box 0 from 0 to M, then box by box a move from the box before: a move is one of "+", "−", "·", ":"
//   that is in `ops` (the link goes forward, from j to j + 1) or whose inverse is in `ops` (the link goes back, from
//   j + 1 to j, with the inverse op: with Plus only a step down is "+" read from the right). Operands: "+" and "−" 1 and
//   up within 0 to M, "·" and ":" 2 to 10 and whole. The last link, box k-1 and box 0, must also be such a link: none is
//   a failed try.
// - The given flags of "start", "ops" or "mixed". "mixed" ohne Zentrum: link j < k - 1 shows its op or box j + 1, the
//   last link always its op; mit Zentrum each link its op or its outer box.
// - Typed boxes (the teacher's numbers win, also outside the Zahlenraum or the Einschränkung): their numbers replace the
//   generated ones, and each link with a typed end gets its op from its two numbers: in its own direction first, then the
//   other way, the first of "+", "−", "·", ":" in `ops` that has an operand ("+" and "−" 1 and up, "·" and ":" 2 to 10).
//   No such op: the field is `wrong`, its link keeps its generated op, and the key shows no answers for that field.
//   A typed field is never `over`.
//
// The drawing (sheet.tsx `Operatorfeld`, on screen, print and in the key alike): `div.operatorfeld` holds one svg. Each
// field `g.field[data-field=i]` (classes `wrong`, `over`), each box `g.box[data-box=j]`, each link `g.link[data-link=j]`
// with a line from box edge to box edge, an arrow head at `to`, and at its middle the ellipse (when `drawOps`) and the
// label. A shown number or label has class `given` (box) or `op` (label) in #222; in the key a missing one has class
// `answer` in #c0392b. With `noted` the key has `text.note` "Auch andere Lösungen sind richtig." in the line at the foot.
//
// Units: a box is D = 10 across; outer boxes stand at radius R from the field's middle, R = 32 ohne Zentrum and 34 mit
// Zentrum; a field is F = 2R + D square. Fields side by side are CG = 8 apart, rows RG = 6 apart.

import { rng } from "./zahlenmauer";

/** A number the teacher typed into a box: the field's index (from 0), the box's index (from 0; mit Zentrum 0 is the centre), the value (0 to 9999). */
export type OperatorfeldTyped = [number, number, number];
export type OperatorfeldProps = {
  /** Whether the field has a centre (mit Zentrum): one number in the middle, linked to every outer box. Without (ohne Zentrum) the boxes stand in a closed ring and each pair of neighbours is linked. Default false. */
  centre: boolean;
  /** Number of Operatorfelder on the sheet, side by side in rows of `columns`. Default 2.
   * @minimum 1
   * @maximum 6
   */
  count: number;
  /** Number of Operatorfelder per row. Default 2.
   * @minimum 1
   * @maximum 3
   */
  columns: number;
  /** Kästchen per Operatorfeld: ohne Zentrum the boxes of the ring, mit Zentrum the outer boxes around the centre. Default 4.
   * @minimum 3
   * @maximum 8
   */
  boxes: number;
  /** The Zahlenraum: the largest number a box may show, one of 10, 20, 100 or 1000. Any other value gives 20. Default 20. */
  max: number;
  /** The Rechenarten: "+", "-", "*" (Mal) and ":" (Geteilt), in that order, each once. Mit Zentrum only "+" and "-"; "*" and ":" need max 20 or more; the others are dropped. Several give each link its own (gemischt). Empty or not a list: ["+"]. Default ["+", "-"]. */
  ops: ("+" | "-" | "*" | ":")[];
  /** The Einschränkung: "none", "tens" (nur Zehnerzahlen: every number and every "+" or "-" operand a multiple of 10, needs max 100 or more) or "hundreds" (nur Hunderterzahlen: multiples of 100, needs max 1000). Too small a max gives "none". Default "none". */
  only: "none" | "tens" | "hundreds";
  /** Which numbers show: "start" the first box (mit Zentrum the centre) and every operator; "ops" every box and no operator; "mixed" (gemischt) the first box (mit Zentrum the centre) and for each link either its operator or its other box. Ohne Zentrum with "+" or "-" and "*" or ":" together, "ops" and "mixed" may have several right answers ("+2" or "·2"), so the answer key says under the fields that other answers count too, and the block keeps a line for that note. Default "start". */
  given: "start" | "ops" | "mixed";
  /** Whether each operator place has an ellipse around it, also an empty one. Default true. */
  drawOps: boolean;
  /** Seed for the random fields. The same seed always gives the same fields. */
  seed: number;
  /** Numbers the teacher typed into boxes. Each entry is [field index from 0, box index from 0 (mit Zentrum 0 is the centre), value 0 to 9999]. The operators of the links at a typed box follow from its numbers; a field where no allowed operator links two numbers is marked wrong. */
  typed?: OperatorfeldTyped[];
};

export type Op = "+" | "-" | "*" | ":";
// A link: numbers[from] op n = numbers[to].
export type Link = { from: number; to: number; op: Op; n: number };
// A field: its numbers (mit Zentrum the centre first), its links, which boxes and operators show, whether it is wrong
// or does not fit the Zahlenraum.
export type Field = { numbers: number[]; links: Link[]; given: boolean[]; opGiven: boolean[]; wrong: boolean; over: boolean };
export type Made = { fields: Field[] };

export const DEFAULTS: Omit<OperatorfeldProps, "seed"> = { centre: false, count: 2, columns: 2, boxes: 4, max: 20, ops: ["+", "-"], only: "none", given: "start", drawOps: true };

const OPS: Op[] = ["+", "-", "*", ":"];

// Whether x is a whole number from lo to hi.
const whole = (x: number, lo: number, hi: number) => Number.isInteger(x) && x >= lo && x <= hi;

// The settings as an operatorfeld block can take them, whatever a stored sheet holds: a wrong value gives its default,
// a typed entry that is not three whole numbers in range is dropped, and of two for the same box the last one stays.
export function sane(p: OperatorfeldProps): OperatorfeldProps {
  const centre = p.centre === true;
  const count = whole(p.count, 1, 6) ? p.count : DEFAULTS.count;
  const columns = whole(p.columns, 1, 3) ? p.columns : DEFAULTS.columns;
  const boxes = whole(p.boxes, 3, 8) ? p.boxes : DEFAULTS.boxes;
  const max = [10, 20, 100, 1000].includes(p.max) ? p.max : DEFAULTS.max;
  const listed = Array.isArray(p.ops) ? OPS.filter((o) => p.ops.includes(o)) : [];
  const ops = listed.filter((o) => o === "+" || o === "-" || (!centre && max >= 20));
  const only = p.only === "tens" && max >= 100 ? "tens" : p.only === "hundreds" && max >= 1000 ? "hundreds" : "none";
  const typed = new Map<string, OperatorfeldTyped>();
  if (Array.isArray(p.typed)) {
    for (const t of p.typed) {
      if (!Array.isArray(t) || t.length !== 3 || !t.every((x) => Number.isInteger(x))) continue;
      const [c, b, v] = t;
      if (c < 0 || c >= count || b < 0 || b > 8 || v < 0 || v > 9999) continue;
      typed.delete(`${c}:${b}`);
      typed.set(`${c}:${b}`, [c, b, v]);
    }
  }
  const kept = [...typed.values()];
  return {
    centre,
    count,
    columns,
    boxes,
    max,
    ops: ops.length ? ops : ["+"],
    only,
    given: p.given === "ops" || p.given === "mixed" ? p.given : "start",
    drawOps: typeof p.drawOps === "boolean" ? p.drawOps : true,
    seed: Number.isFinite(p.seed) ? p.seed : 0,
    ...(kept.length ? { typed: kept } : {}),
  };
}

// The label of an operator with its operand: "+4", "−4" (U+2212), "·4" (U+00B7) or ":4".
const SIGN: Record<Op, string> = { "+": "+", "-": "−", "*": "·", ":": ":" };
export function opLabel(link: Pick<Link, "op" | "n">): string {
  return `${SIGN[link.op]}${link.n}`;
}

// Whether a field of these settings can have more than one right answer, so that the key says other answers count too:
// ohne Zentrum, with a hidden operator ("ops" or "mixed"), and with "+" or "-" beside "*" or ":" ("+2" or "·2").
export function noted(p: Partial<Pick<OperatorfeldProps, "centre" | "given" | "ops">>): boolean {
  const ops = p.ops ?? [];
  return !p.centre && (p.given === "ops" || p.given === "mixed") && ops.some((o) => o === "+" || o === "-") && ops.some((o) => o === "*" || o === ":");
}

// The drawing in svg units. With a noted field (see `noted`) a line of N units at the foot holds the key's note; on
// the pupils' sheet it stays empty, so that the key and the sheet have the same size. `vbW` and `vbH` are the viewBox.
export function layout(p: Pick<OperatorfeldProps, "count" | "columns" | "centre"> & Partial<Pick<OperatorfeldProps, "given" | "ops">>) {
  const [D, CG, RG] = [10, 8, 6];
  const R = p.centre ? 34 : 32;
  const F = 2 * R + D;
  const N = noted(p) ? 6 : 0;
  const rows = Math.ceil(p.count / p.columns);
  const vbW = p.columns * F + (p.columns - 1) * CG + 1;
  const vbH = rows * F + (rows - 1) * RG + 1 + N;
  return { D, R, F, CG, RG, N, rows, vbW, vbH };
}

// The middle of box j of a field of k outer boxes whose middle is (cx, cy): mit Zentrum box 0 is the middle itself.
export function boxAt(centre: boolean, k: number, j: number, cx: number, cy: number, R: number): [number, number] {
  if (centre && j === 0) return [cx, cy];
  const i = centre ? j - 1 : j;
  const a = -Math.PI / 2 + (2 * Math.PI * i) / k;
  return [cx + R * Math.cos(a), cy + R * Math.sin(a)];
}

// The default block is drawn at the scale S0 at 180 mm wide. A block of width w draws its boxes at that scale, and its
// height grows with the rows, so that they keep that size.
const S0 = 180 / layout(DEFAULTS).vbW;

// The height in mm of a block of width w with the props p, at which its boxes draw at least at the default scale.
export function heightFor(p: OperatorfeldProps, w: number): number {
  const L = layout(sane(p));
  return L.vbH * Math.min(w / L.vbW, S0);
}

// The inverse operator: + and -, * and : swap.
const INV: Record<Op, Op> = { "+": "-", "-": "+", "*": ":", ":": "*" };

// The result of x op n.
function apply(op: Op, x: number, n: number): number {
  return op === "+" ? x + n : op === "-" ? x - n : op === "*" ? x * n : x / n;
}

// The operands that x op n takes from x within 0 to M: "+" 1 up to M - x, "−" 1 up to x, "·" 2 to 10 (x at least 1), ":" 2 to 10 that divide x.
function operands(op: Op, x: number, M: number): number[] {
  const out: number[] = [];
  if (op === "+") for (let n = 1; n <= M - x; n++) out.push(n);
  else if (op === "-") for (let n = 1; n <= x; n++) out.push(n);
  else if (op === "*") {
    if (x >= 1) for (let n = 2; n <= 10 && x * n <= M; n++) out.push(n);
  } else for (let n = 2; n <= 10; n++) if (x >= n && x % n === 0) out.push(n);
  return out;
}

// A random pick from a non-empty list.
function pick<T>(xs: T[], next: () => number): T {
  return xs[Math.floor(next() * xs.length)];
}

// One try mit Zentrum: the centre C, then each outer box an op from C. A box takes up to 10 draws for a number no other outer box has.
function centreAttempt(p: OperatorfeldProps, M: number, next: () => number): { numbers: number[]; links: Link[] } | null {
  const C = Math.floor(next() * (M + 1));
  const usable = p.ops.map((op) => ({ op, cands: operands(op, C, M) })).filter((u) => u.cands.length);
  if (!usable.length) return null;
  const outer: number[] = [];
  const links: Link[] = [];
  for (let i = 0; i < p.boxes; i++) {
    let op: Op = "+";
    let n = 0;
    for (let t = 0; t < 10; t++) {
      const use = pick(usable, next);
      op = use.op;
      n = pick(use.cands, next);
      if (!outer.includes(apply(op, C, n))) break;
    }
    outer.push(apply(op, C, n));
    links.push({ from: 0, to: i + 1, op, n });
  }
  return { numbers: [C, ...outer], links };
}

// One try ohne Zentrum: box 0, then each box from the one before by a move, the last move back to box 0. A move forward
// is an op in `ops`; a move back is the inverse of one, so it links the box after to the box before.
function ringAttempt(p: OperatorfeldProps, M: number, next: () => number): { numbers: number[]; links: Link[] } | null {
  const k = p.boxes;
  const numbers = [Math.floor(next() * (M + 1))];
  const links: Link[] = [];
  for (let j = 0; j < k; j++) {
    const x = numbers[j];
    const last = j === k - 1;
    const usable = OPS.filter((o) => p.ops.includes(o) || p.ops.includes(INV[o]))
      .map((op) => ({ op, cands: operands(op, x, M).filter((n) => !last || apply(op, x, n) === numbers[0]) }))
      .filter((u) => u.cands.length);
    if (!usable.length) return null;
    const use = pick(usable, next);
    const n = pick(use.cands, next);
    const to = (j + 1) % k;
    if (!last) numbers.push(apply(use.op, x, n));
    links.push(p.ops.includes(use.op) ? { from: j, to, op: use.op, n } : { from: to, to: j, op: INV[use.op], n });
  }
  return { numbers, links };
}

// The numbers and links of an untyped field. None in 50 tries: `over`, zeros and "+1" links in the shape, not drawn.
function generated(p: OperatorfeldProps, M: number, u: number, next: () => number): { numbers: number[]; links: Link[]; over: boolean } {
  for (let t = 0; t < 50; t++) {
    const got = p.centre ? centreAttempt(p, M, next) : ringAttempt(p, M, next);
    if (got) {
      return { numbers: got.numbers.map((x) => x * u), links: got.links.map((l) => (l.op === "+" || l.op === "-" ? { ...l, n: l.n * u } : l)), over: false };
    }
  }
  const k = p.boxes;
  return {
    numbers: Array.from({ length: p.centre ? k + 1 : k }, () => 0),
    links: Array.from({ length: k }, (_, j): Link => (p.centre ? { from: 0, to: j + 1, op: "+", n: 1 } : { from: j, to: (j + 1) % k, op: "+", n: 1 })),
    over: true,
  };
}

// The flags of the shown boxes and operators of one field with B boxes and L links.
function givenFlags(p: OperatorfeldProps, B: number, L: number, next: () => number): { given: boolean[]; opGiven: boolean[] } {
  const g = Array.from({ length: B }, () => false);
  const og = Array.from({ length: L }, () => false);
  g[0] = true;
  if (p.given === "start") og.fill(true);
  else if (p.given === "ops") g.fill(true);
  else {
    for (let j = 0; j < L; j++) {
      // Ohne Zentrum the last link always shows its operator.
      if (!p.centre && j === L - 1) og[j] = true;
      else if (next() < 0.5) og[j] = true;
      else g[j + 1] = true;
    }
  }
  return { given: g, opGiven: og };
}

// The operand n that takes x to y with op, or null.
function operandFor(op: Op, x: number, y: number): number | null {
  if (op === "+") return y - x >= 1 ? y - x : null;
  if (op === "-") return x - y >= 1 ? x - y : null;
  for (let n = 2; n <= 10; n++) if (apply(op, x, n) === y) return n;
  return null;
}

// A link with a typed end takes the first op of `ops` that fits its numbers in its own direction, else the first that fits
// the other way round (the link turns). None fits: the link keeps its op and the field is wrong.
function relink(l: Link, numbers: number[], ops: Op[]): Link {
  const x = numbers[l.from];
  const y = numbers[l.to];
  for (const op of ops) {
    const n = operandFor(op, x, y);
    if (n !== null) return { ...l, op, n };
  }
  for (const op of ops) {
    const n = operandFor(op, y, x);
    if (n !== null) return { from: l.to, to: l.from, op, n };
  }
  return l;
}

// The fields of the settings. The same settings give the same fields on every call.
const memo = new Map<string, Made>();

export function made(props: OperatorfeldProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = memo.get(key);
  if (old) return old;
  const next = rng(p.seed);
  const u = p.only === "tens" ? 10 : p.only === "hundreds" ? 100 : 1;
  const M = p.max / u;
  const fields: Field[] = [];
  for (let i = 0; i < p.count; i++) {
    // The draws of every field happen whatever its typed boxes, so that the fields after it stay as they were.
    const gen = generated(p, M, u, next);
    const flags = givenFlags(p, gen.numbers.length, gen.links.length, next);
    const typed = new Map<number, number>();
    for (const [c, b, v] of p.typed ?? []) if (c === i && b < gen.numbers.length) typed.set(b, v);
    let numbers = gen.numbers;
    let links = gen.links;
    let wrong = false;
    if (typed.size) {
      numbers = gen.numbers.map((x, b) => typed.get(b) ?? x);
      links = gen.links.map((l) => (typed.has(l.from) || typed.has(l.to) ? relink(l, numbers, p.ops) : l));
      wrong = links.some((l) => apply(l.op, numbers[l.from], l.n) !== numbers[l.to]);
    }
    fields.push({ numbers, links, given: flags.given, opGiven: flags.opGiven, wrong, over: gen.over && !typed.size });
  }
  const out: Made = { fields };
  memo.set(key, out);
  if (memo.size > 50) memo.delete(memo.keys().next().value as string);
  return out;
}
