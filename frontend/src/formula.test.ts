// The formula syntax teachers type: fractions, mixed numbers, powers, roots, subscripts and a gap.
import { describe, expect, it } from "vitest";
import { TEMPLATES, asFormula, embed, parse, plain, ptOf, splitFormula } from "./formula";

const minus = "\u2212";

describe("parse", () => {
  it("reads a fraction, a power, a root and a subscript", () => {
    expect(parse("3/4")).toEqual({ k: "frac", a: { k: "text", s: "3" }, b: { k: "text", s: "4" } });
    expect(parse("2^3")).toEqual({ k: "sup", a: { k: "text", s: "2" }, e: { k: "text", s: "3" } });
    expect(parse("sqrt(16)")).toEqual({ k: "sqrt", a: { k: "text", s: "16" } });
    expect(parse("x_2")).toEqual({ k: "sub", a: { k: "text", s: "x" }, e: { k: "text", s: "2" } });
  });

  it("reads a mixed number and a sum of fractions", () => {
    expect(parse("1 3/4")).toEqual({ k: "mixed", n: "1", a: { k: "text", s: "3" }, b: { k: "text", s: "4" } });
    expect(parse("3/4+1/2")).toEqual({
      k: "row",
      xs: [
        { k: "frac", a: { k: "text", s: "3" }, b: { k: "text", s: "4" } },
        { k: "text", s: "+" },
        { k: "frac", a: { k: "text", s: "1" }, b: { k: "text", s: "2" } },
      ],
    });
  });

  it("keeps brackets and binds a power tighter than a fraction", () => {
    expect(parse("(1+2)/3")).toEqual({
      k: "frac",
      a: { k: "row", xs: [{ k: "text", s: "(" }, { k: "text", s: "1" }, { k: "text", s: "+" }, { k: "text", s: "2" }, { k: "text", s: ")" }] },
      b: { k: "text", s: "3" },
    });
    expect(parse("3/4^2")).toEqual({
      k: "frac",
      a: { k: "text", s: "3" },
      b: { k: "sup", a: { k: "text", s: "4" }, e: { k: "text", s: "2" } },
    });
    expect(parse("sqrt(2^3)")).toEqual({ k: "sqrt", a: { k: "sup", a: { k: "text", s: "2" }, e: { k: "text", s: "3" } } });
  });

  it("reads a power and a subscript on one base", () => {
    expect(parse("x_2^3")).toEqual({
      k: "both",
      a: { k: "text", s: "x" },
      sub: { k: "text", s: "2" },
      sup: { k: "text", s: "3" },
    });
  });

  it("reads a backslash space as a gap and writes the school minus", () => {
    expect(parse("\\ ")).toEqual({ k: "blank" });
    expect(parse("2+\\ ")).toEqual({ k: "row", xs: [{ k: "text", s: "2" }, { k: "text", s: "+" }, { k: "blank" }] });
    expect(parse("2-3").k === "row" && (parse("2-3") as { xs: { s?: string }[] }).xs[1].s).toBe(minus);
  });
});

describe("size follows the font size", () => {
  it("scales a fraction and a power with the font, and keeps a root's body at that size", () => {
    expect(ptOf(parse("3/4"), "3", 20)).toBeCloseTo(14);
    expect(ptOf(parse("3/4"), "4", 20)).toBeCloseTo(14);
    expect(ptOf(parse("3/4"), "3", 40)).toBeCloseTo(28);
    expect(ptOf(parse("2^3"), "3", 20)).toBeCloseTo(14);
    expect(ptOf(parse("2^3"), "2", 20)).toBeCloseTo(20);
    expect(ptOf(parse("sqrt(16)"), "16", 20)).toBeCloseTo(20);
    expect(ptOf(parse("sqrt(16)"), "16", 40)).toBeCloseTo(40);
  });
});

describe("plain reading", () => {
  it("keeps the digits in reading order", () => {
    expect(plain(parse("3/4"))).toBe("34");
    expect(plain(parse("1 3/4"))).toBe("134");
    expect(plain(parse("2^3"))).toBe("23");
    expect(plain(parse("sqrt(16)"))).toBe("\u221A16");
    expect(plain(parse("x_2"))).toBe("x2");
    expect(plain(parse("\\ "))).toBe("");
    expect(plain(parse("2*3"))).toBe("2\u00B73");
  });
});

describe("inline", () => {
  it("splits a formula out of a sentence and a cell", () => {
    expect(splitFormula("Berechne \\f{3/4} von 12.")).toEqual([{ text: "Berechne " }, { formula: "3/4" }, { text: " von 12." }]);
    expect(embed("3/4")).toBe("\\f{3/4}");
    expect(splitFormula(embed("sqrt(16)"))).toEqual([{ formula: "sqrt(16)" }]);
    expect(splitFormula("kein Bruch")).toEqual([{ text: "kein Bruch" }]);
    expect(asFormula("3/4")).toBe("3/4");
    expect(asFormula("\\f{2^3}")).toBe("2^3");
    expect(asFormula("3")).toBeUndefined();
    expect(asFormula("2+3")).toBeUndefined();
    expect(asFormula("Berechne \\f{3/4}")).toBeUndefined();
  });
});

describe("gallery", () => {
  it("offers the six templates and each one parses as a formula", () => {
    expect(TEMPLATES.map((t) => t.name)).toEqual(["Bruch", "Gemischt", "Potenz", "Wurzel", "Index", "Leerstelle"]);
    expect(TEMPLATES.map((t) => t.source)).toEqual(["3/4", "1 3/4", "2^3", "sqrt(16)", "x_2", "\\ "]);
    for (const t of TEMPLATES) expect(parse(t.source).k).not.toBe("text");
  });
});
