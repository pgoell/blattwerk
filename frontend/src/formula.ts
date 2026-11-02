// A formula a teacher types, and the tree the sheet draws.
//
// `3/4` is a fraction, `1 3/4` a mixed number, `2^3` a power, `sqrt(16)` a root, `x_2` a subscript.
// `\ ` (a backslash and a space) is a gap. `+`, the school minus, `·`, `:` and `=` stand between terms.
// A power binds tighter than a fraction, and brackets group. The same source sits inline in a text or a
// cell as `\f{3/4}`.

export type Node =
  | { k: "text"; s: string }
  | { k: "row"; xs: Node[] }
  | { k: "frac"; a: Node; b: Node }
  | { k: "mixed"; n: string; a: Node; b: Node }
  | { k: "sup"; a: Node; e: Node }
  | { k: "sub"; a: Node; e: Node }
  | { k: "both"; a: Node; sub: Node; sup: Node }
  | { k: "sqrt"; a: Node }
  | { k: "blank" };

// A script and a fraction's digits are this share of the font size they sit in. A bigger font scales both.
const SCRIPT = 0.7;

export const TEMPLATES = [
  { name: "Bruch", source: "3/4" },
  { name: "Gemischt", source: "1 3/4" },
  { name: "Potenz", source: "2^3" },
  { name: "Wurzel", source: "sqrt(16)" },
  { name: "Index", source: "x_2" },
  { name: "Lücke", source: "\\ " },
] as const;

const OPS: Record<string, string> = { "+": "+", "-": "\u2212", "\u2212": "\u2212", "=": "=", "*": "\u00B7", "\u00B7": "\u00B7", "\u00D7": "\u00B7", ":": ":" };

type Tok = { t: "num" | "id" | "op" | "sym"; s: string } | { t: "sqrt" } | { t: "blank" } | { t: "sp" };

function tokenize(src: string): Tok[] {
  const out: Tok[] = [];
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (c === "\\" && src[i + 1] === " ") {
      out.push({ t: "blank" });
      i += 2;
      continue;
    }
    if (/\s/u.test(c)) {
      out.push({ t: "sp" });
      i++;
      while (i < src.length && /\s/u.test(src[i])) i++;
      continue;
    }
    if (/[0-9]/u.test(c)) {
      let s = "";
      while (i < src.length && /[0-9]/u.test(src[i])) s += src[i++];
      if (src[i] === "," && /[0-9]/u.test(src[i + 1] ?? "")) {
        s += src[i++];
        while (i < src.length && /[0-9]/u.test(src[i])) s += src[i++];
      }
      out.push({ t: "num", s });
      continue;
    }
    if (/\p{L}/u.test(c)) {
      let s = "";
      while (i < src.length && /\p{L}/u.test(src[i])) s += src[i++];
      out.push(s === "sqrt" ? { t: "sqrt" } : { t: "id", s });
      continue;
    }
    if (c in OPS) {
      out.push({ t: "op", s: OPS[c] });
      i++;
      continue;
    }
    if ("^_/()".includes(c)) {
      out.push({ t: "sym", s: c });
      i++;
      continue;
    }
    out.push({ t: "id", s: c });
    i++;
  }
  return out;
}

class P {
  i = 0;
  ts: Tok[];
  constructor(ts: Tok[]) {
    this.ts = ts;
  }
  peek(): Tok | undefined {
    return this.ts[this.i];
  }
  eat(t: Tok["t"], s?: string): boolean {
    const n = this.peek();
    if (!n || n.t !== t) return false;
    if (s !== undefined && (!("s" in n) || n.s !== s)) return false;
    this.i++;
    return true;
  }
  skip(): void {
    while (this.eat("sp")) {}
  }
}

const rowOf = (n: Node): Node[] => (n.k === "row" ? n.xs : [n]);
const bare = (n: Node): n is { k: "text"; s: string } => n.k === "text" && /^[0-9]+(?:,[0-9]+)?$/u.test(n.s);

function atom(p: P): Node {
  p.skip();
  const n = p.peek();
  if (!n) return { k: "text", s: "" };
  if (n.t === "blank") {
    p.i++;
    return { k: "blank" };
  }
  if (n.t === "sqrt") {
    p.i++;
    p.skip();
    if (!p.eat("sym", "(")) return { k: "text", s: "sqrt" };
    const body = expr(p);
    p.skip();
    p.eat("sym", ")");
    return { k: "sqrt", a: body };
  }
  if (n.t === "sym" && n.s === "(") {
    p.i++;
    const inner = expr(p);
    p.skip();
    p.eat("sym", ")");
    return { k: "row", xs: [{ k: "text", s: "(" }, ...rowOf(inner), { k: "text", s: ")" }] };
  }
  p.i++;
  return { k: "text", s: "s" in n ? n.s : "" };
}

function factor(p: P): Node {
  const base = atom(p);
  let sup: Node | undefined;
  let sub: Node | undefined;
  for (;;) {
    const at = p.i;
    p.skip();
    const n = p.peek();
    if (n?.t === "sym" && n.s === "^" && !sup) {
      p.i++;
      sup = atom(p);
      continue;
    }
    if (n?.t === "sym" && n.s === "_" && !sub) {
      p.i++;
      sub = atom(p);
      continue;
    }
    p.i = at;
    break;
  }
  if (sup && sub) return { k: "both", a: base, sub, sup };
  if (sup) return { k: "sup", a: base, e: sup };
  if (sub) return { k: "sub", a: base, e: sub };
  return base;
}

function term(p: P): Node {
  let left = factor(p);
  for (;;) {
    const at = p.i;
    p.skip();
    if (!p.eat("sym", "/")) {
      p.i = at;
      break;
    }
    left = { k: "frac", a: left, b: factor(p) };
  }
  return left;
}

function expr(p: P): Node {
  p.skip();
  if (!p.peek()) return { k: "row", xs: [] };
  const xs: Node[] = [term(p)];
  for (;;) {
    const at = p.i;
    const sp = p.eat("sp");
    const n = p.peek();
    if (!n) break;
    if (sp && bare(xs[xs.length - 1]) && n.t === "num") {
      const ahead = p.i;
      p.i++;
      p.eat("sp");
      const next = p.peek();
      const slash = next?.t === "sym" && next.s === "/";
      p.i = ahead;
      if (slash) {
        const frac = term(p);
        if (frac.k === "frac") {
          const whole = xs.pop() as { k: "text"; s: string };
          xs.push({ k: "mixed", n: whole.s, a: frac.a, b: frac.b });
          continue;
        }
        p.i = ahead;
      }
    }
    if (n.t === "op") {
      p.i++;
      xs.push({ k: "text", s: n.s });
      xs.push(term(p));
      continue;
    }
    if (n.t === "num" || n.t === "id" || n.t === "sqrt" || n.t === "blank" || (n.t === "sym" && n.s === "(")) {
      xs.push(term(p));
      continue;
    }
    p.i = at;
    break;
  }
  return xs.length === 1 ? xs[0] : { k: "row", xs };
}

export function parse(src: string): Node {
  const p = new P(tokenize(src));
  return expr(p);
}

// The digits and signs in reading order, as the PDF's text has them. A gap has none.
export function plain(n: Node): string {
  switch (n.k) {
    case "text":
      return n.s;
    case "row":
      return n.xs.map(plain).join("");
    case "frac":
      return plain(n.a) + plain(n.b);
    case "mixed":
      return n.n + plain(n.a) + plain(n.b);
    case "sup":
    case "sub":
      return plain(n.a) + plain(n.e);
    case "both":
      return plain(n.a) + plain(n.sub) + plain(n.sup);
    case "sqrt":
      return `\u221A${plain(n.a)}`;
    case "blank":
      return "";
  }
}

// The size in pt of the first glyph `s` when the formula is set at `pt`.
export function ptOf(n: Node, glyph: string, pt: number, em = 1): number | undefined {
  switch (n.k) {
    case "text":
      return n.s === glyph ? pt * em : undefined;
    case "blank":
      return undefined;
    case "row":
      return n.xs.reduce<number | undefined>((hit, x) => hit ?? ptOf(x, glyph, pt, em), undefined);
    case "frac":
      return ptOf(n.a, glyph, pt, em * SCRIPT) ?? ptOf(n.b, glyph, pt, em * SCRIPT);
    case "mixed":
      return (n.n === glyph ? pt * em : undefined) ?? ptOf(n.a, glyph, pt, em * SCRIPT) ?? ptOf(n.b, glyph, pt, em * SCRIPT);
    case "sup":
    case "sub":
      return ptOf(n.a, glyph, pt, em) ?? ptOf(n.e, glyph, pt, em * SCRIPT);
    case "both":
      return ptOf(n.a, glyph, pt, em) ?? ptOf(n.sub, glyph, pt, em * SCRIPT) ?? ptOf(n.sup, glyph, pt, em * SCRIPT);
    case "sqrt":
      return ptOf(n.a, glyph, pt, em);
  }
}

export function embed(source: string): string {
  return `\\f{${source.replaceAll("}", "")}}`;
}

// The pieces of a text: a formula where the teacher put `\f{...}`, and the words around it.
export function splitFormula(text: string): { text?: string; formula?: string }[] {
  const out: { text?: string; formula?: string }[] = [];
  const re = /\\f\{([^{}]*)\}/gu;
  let at = 0;
  for (const m of text.matchAll(re)) {
    const i = m.index ?? 0;
    if (i > at) out.push({ text: text.slice(at, i) });
    out.push({ formula: m[1] });
    at = i + m[0].length;
  }
  if (at < text.length || !out.length) out.push({ text: text.slice(at) });
  return out;
}

function holds(n: Node): boolean {
  if (n.k === "blank") return true;
  if (n.k === "text") return false;
  if (n.k === "row") return n.xs.some(holds);
  return true;
}

// A cell whose whole text is one formula: the marker, or a source such as `3/4`. A sentence is not.
export function asFormula(text: string): string | undefined {
  const trimmed = text.trim();
  if (!trimmed) return undefined;
  const bits = splitFormula(trimmed);
  if (bits.length === 1 && bits[0].formula !== undefined) return bits[0].formula;
  if (bits.some((b) => b.formula !== undefined)) return undefined;
  return holds(parse(trimmed)) ? trimmed : undefined;
}

// What a Formel block stores. The sheet draws it at `size` pt, and the parts scale with that.
export type FormulaProps = {
  /** The formula in the simple syntax: "3/4" a fraction, "1 3/4" a mixed number, "2^3" a power, "sqrt(16)" a root, "x_2" a subscript, "\\ " a gap. */
  source: string;
  /** Font size of the formula in pt. A fraction, a power and a root scale with it. The editor steps it by 2 pt and never goes below 8.
   * @minimum 8
   */
  size: number;
  /** Colour of the formula as a hex colour, such as "#222222". Absent means #222222. */
  color?: string;
  /** Horizontal alignment in the box: "left", "center" or "right". Absent means center. */
  align?: "left" | "center" | "right";
};

export function sane(p: Partial<FormulaProps> | undefined): FormulaProps {
  const size = typeof p?.size === "number" && Number.isFinite(p.size) ? Math.max(8, p.size) : 18;
  const align = p?.align === "left" || p?.align === "right" || p?.align === "center" ? p.align : "center";
  const source = typeof p?.source === "string" ? p.source : "3/4";
  const color = typeof p?.color === "string" && /^#[0-9a-fA-F]{6}$/u.test(p.color) ? p.color : undefined;
  return { source, size, align, ...(color ? { color } : {}) };
}
