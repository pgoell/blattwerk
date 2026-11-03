// A Lösungsfeld is blank on the pupil's sheet. The Lösungen print its text or its picture.
// Falsche Lösungen stay stored for a Selbstkontrolle. Even fields share the widest answer's width.
import { describe, expect, it } from "vitest";
import { answers, blankMm, contentMm, sane, shown, type LoesungsfeldProps } from "./loesungsfeld";

const field = (over: Partial<LoesungsfeldProps> = {}) => sane({ text: "Hund", ...over });

describe("Lösungstext", () => {
  it("is blank on the pupil's sheet and printed in the Lösungen", () => {
    const p = field();
    expect(shown(p, false)).toEqual({ blank: "line" });
    expect(shown(p, true)).toEqual({ blank: "line", text: "Hund" });
  });

  it("leaves an Unterstrich, a Rahmen or nothing", () => {
    expect(shown(field({ blank: "box" }), false).blank).toBe("box");
    expect(shown(field({ blank: "none" }), true)).toEqual({ blank: "none", text: "Hund" });
  });

  it("keeps the answer on one line", () => {
    expect(sane({ text: "Hund\nKatze" }).text).toBe("Hund Katze");
  });
});

describe("Lösungsbild", () => {
  it("shows a symbol only in the Lösungen", () => {
    const p = field({ kind: "image", code: "1F333" });
    expect(shown(p, false).code).toBeUndefined();
    expect(shown(p, true).code).toBe("1F333");
  });

  it("shows an uploaded picture only in the Lösungen", () => {
    const p = field({ kind: "image", upload: 4, ratio: 1.5 });
    expect(shown(p, false).upload).toBeUndefined();
    expect(shown(p, true)).toMatchObject({ upload: 4, ratio: 1.5 });
  });

  it("drops a picture that is not in the symbol library", () => {
    expect(sane({ kind: "image", code: "nope" }).code).toBeUndefined();
  });
});

describe("falsche Lösungen", () => {
  it("keeps wrong answers and drops one that repeats the right one", () => {
    const p = field({
      wrongs: [
        { kind: "text", text: "Katze" },
        { kind: "text", text: "Hund" },
        { kind: "image", code: "1F33B" },
      ],
    });
    expect(answers(p)).toEqual({
      right: { kind: "text", text: "Hund" },
      wrongs: [
        { kind: "text", text: "Katze" },
        { kind: "image", code: "1F33B" },
      ],
    });
  });
});

describe("Alle Lösungsfelder gleich breit", () => {
  it("gives every even field the width of the longest answer", () => {
    const short = field({ text: "Ja", even: true });
    const long = field({ text: "Elefant", even: true });
    const own = field({ text: "Ja", even: false });
    const other = field({ text: "Elefant", even: false });
    expect(contentMm(long)).toBeGreaterThan(contentMm(short));
    expect(blankMm(short, [short, long])).toBe(contentMm(long));
    expect(blankMm(long, [short, long])).toBe(contentMm(long));
    expect(blankMm(own, [own, other])).toBe(contentMm(own));
    expect(blankMm(own, [own, other])).toBeLessThan(contentMm(other));
  });
});

describe("sane", () => {
  it("fills defaults and never throws on a wrong stored value", () => {
    expect(sane({ size: "x", blank: "nope", kind: 1 })).toEqual({
      kind: "text",
      text: "",
      blank: "line",
      size: 14,
      even: false,
      wrongs: [],
    });
  });
});
