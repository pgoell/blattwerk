// Properties of the gaps of a Lückentext: what each change makes of a text's words and a table's cells.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { allCellGap, allCells, allGap, allGaps, everyNth, everyNthCell } from "./gaps";
import type { Para, Run } from "./sheet";

// Runs with some settings of their own, as a text keeps them.
const run = fc.record({ text: fc.array(fc.constantFrom("a", "b", " ", "-", "é", "1", ".", "’"), { maxLength: 12 }).map((cs) => cs.join("")), bold: fc.option(fc.boolean(), { nil: undefined }), gap: fc.option(fc.constant(true), { nil: undefined }) }) as fc.Arbitrary<Run>;
const paras = fc.array(fc.record({ runs: fc.array(run, { maxLength: 4 }) }), { maxLength: 3 }) as fc.Arbitrary<Para[]>;
const plain = (ps: Para[]) => ps.map((p) => p.runs.map((r) => r.text).join("")).join("\n");
// The settings of each character, in order.
const chars = (ps: Para[]) => ps.flatMap((p) => p.runs.flatMap((r) => [...r.text].map((c) => [c, r.bold ?? null, !!r.gap])));
// Each word of the text, and whether it is a gap all through.
const spans = (ps: Para[]) =>
  ps.flatMap((p) => {
    const text = p.runs.map((r) => r.text).join("");
    const marks = p.runs.map((r) => (r.gap ? r.text : r.text.replace(/./gsu, "_"))).join("");
    return [...text.matchAll(/[\p{L}\p{M}\p{N}]+(?:['’-][\p{L}\p{M}\p{N}]+)*/gu)].map(({ 0: word, index = 0 }) => ({ word, gap: marks.slice(index, index + word.length) === word }));
  });

describe("allGaps", () => {
  it("makes every run with text a gap, or none", () => {
    fc.assert(
      fc.property(paras, (ps) => {
        expect(allGap(allGaps(ps, true))).toBe(ps.some((p) => p.runs.some((r) => r.text)));
        expect(chars(allGaps(ps, false)).every(([, , gap]) => !gap)).toBe(true);
        expect(plain(allGaps(ps, true))).toBe(plain(ps));
      }),
    );
  });
});

describe("everyNth", () => {
  it("keeps the text, the order and the other settings of each character", () => {
    fc.assert(
      fc.property(paras, fc.integer({ min: 2, max: 6 }), (ps, n) => {
        const out = everyNth(ps, n);
        expect(plain(out)).toBe(plain(ps));
        expect(chars(out).map(([c, bold]) => [c, bold])).toStrictEqual(chars(ps).map(([c, bold]) => [c, bold]));
      }),
    );
  });

  it("gaps every n-th word, counted through the paragraphs", () => {
    fc.assert(
      fc.property(paras, fc.integer({ min: 2, max: 6 }), (ps, n) => {
        const out = spans(everyNth(ps, n));
        expect(out.map((s) => s.word)).toStrictEqual(spans(ps).map((s) => s.word));
        expect(out.map((s) => s.gap)).toStrictEqual(spans(ps).map((_, i) => (i + 1) % n === 0));
      }),
    );
  });

  it("takes gaps made before away", () => {
    const ps: Para[] = [{ runs: [{ text: "eins zwei", gap: true }] }];
    expect(everyNth(ps, 2)).toStrictEqual([{ runs: [{ text: "eins " }, { text: "zwei", gap: true }] }]);
  });
});

describe("cells", () => {
  const cells = [
    ["a", ""],
    ["b", "c"],
  ];
  it("makes every cell with text a gap, or none, and none when none is", () => {
    expect(allCells(cells, true)).toStrictEqual([
      [true, false],
      [true, true],
    ]);
    expect(allCells(cells, false)).toBeUndefined();
    expect(allCellGap(cells, allCells(cells, true))).toBe(true);
    expect(allCellGap(cells, undefined)).toBe(false);
  });

  it("gaps every n-th cell with text, row by row", () => {
    expect(everyNthCell(cells, 2)).toStrictEqual([
      [false, false],
      [true, false],
    ]);
    expect(everyNthCell(cells, 4)).toBeUndefined();
  });
});
