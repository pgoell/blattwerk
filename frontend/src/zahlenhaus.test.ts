// The Zahlenhaus generator: the floors add up to the roof, the given boxes follow the settings, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { boxes, made, sane, sideFlags, type ZahlenhausProps } from "./zahlenhaus";

const P = (over: Partial<ZahlenhausProps> = {}): ZahlenhausProps => ({ count: 4, columns: 4, floors: 4, max: 10, given: "side", seed: 1, ...over });

// The smallest roof a generated house takes: at least floors - 1, at most max.
const lowest = (floors: number, max: number) => Math.min(max, Math.max(2, floors - 1));

describe("the houses of a block", () => {
  it("the same seed gives the same houses", () => {
    expect(made(P({ seed: 42 }))).toEqual(made(P({ seed: 42 })));
    expect(made(P({ seed: 42, max: 100, floors: 6 }))).toEqual(made(P({ seed: 42, max: 100, floors: 6 })));
  });

  it("another seed gives other houses", () => {
    expect(made(P({ seed: 1, max: 1000 }))).not.toEqual(made(P({ seed: 2, max: 1000 })));
  });

  it("every floor of a generated house adds up to its roof, and the roof lies within lo to max", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.integer({ min: 2, max: 1000 }),
        fc.integer({ min: 2, max: 10 }),
        fc.integer({ min: 1, max: 12 }),
        (seed, max, floors, count) => {
          const { houses } = made(P({ seed, max, floors, count }));
          expect(houses).toHaveLength(count);
          for (const h of houses) {
            expect(h.numbers).toHaveLength(boxes(floors));
            expect(h.wrong).toEqual(Array.from({ length: floors }, () => false));
            const roof = h.numbers[0];
            expect(roof).toBeGreaterThanOrEqual(lowest(floors, max));
            expect(roof).toBeLessThanOrEqual(max);
            for (let f = 0; f < floors; f++) {
              expect(h.numbers[1 + 2 * f]).toBeGreaterThanOrEqual(0);
              expect(h.numbers[2 + 2 * f]).toBeGreaterThanOrEqual(0);
              expect(h.numbers[1 + 2 * f] + h.numbers[2 + 2 * f]).toBe(roof);
            }
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("the floors of one house are distinct when the roof has enough splits", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.integer({ min: 2, max: 1000 }),
        fc.integer({ min: 2, max: 10 }),
        (seed, max, floors) => {
          for (const h of made(P({ seed, max, floors, count: 3 })).houses) {
            if (h.numbers[0] + 1 < floors) continue;
            const lefts = Array.from({ length: floors }, (_, f) => h.numbers[1 + 2 * f]);
            expect(new Set(lefts).size).toBe(floors);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("\"side\" shows the roof and each floor's left box", () => {
    for (const h of made(P({ given: "side", floors: 3 })).houses) expect(h.given).toEqual([true, true, false, true, false, true, false]);
  });

  it("\"roof\" shows the roof only", () => {
    for (const h of made(P({ given: "roof", floors: 3 })).houses) expect(h.given).toEqual([true, false, false, false, false, false, false]);
  });

  it("\"free\" shows the boxes its flags name, the same for every house", () => {
    const free = [false, true, false, true, true, false, false];
    const { houses } = made(P({ given: "free", floors: 3, free }));
    for (const h of houses) expect(h.given).toEqual(free);
  });

  it("\"mix\" shows the roof and one box of each floor", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1_000_000 }), fc.integer({ min: 2, max: 10 }), (seed, floors) => {
        for (const h of made(P({ seed, given: "mix", floors, count: 3 })).houses) {
          expect(h.given[0]).toBe(true);
          for (let f = 0; f < floors; f++) expect(h.given[1 + 2 * f] !== h.given[2 + 2 * f]).toBe(true);
        }
      }),
      { numRuns: 100 },
    );
  });
});

describe("the settings as a block takes them", () => {
  it("a wrong value gives its default", () => {
    const s = sane({ count: 13, columns: 0, floors: 1, max: 1001, given: "bogus" as ZahlenhausProps["given"], seed: NaN });
    expect(s).toMatchObject({ count: 4, columns: 4, floors: 4, max: 10, given: "side", seed: 0 });
  });

  it("non-integers are wrong too", () => {
    expect(sane(P({ count: 2.5, floors: 4.5, max: 10.5, columns: 1.5 }))).toMatchObject({ count: 4, floors: 4, max: 10, columns: 4 });
  });

  it("the largest and smallest allowed values stay", () => {
    expect(sane(P({ count: 12, columns: 6, floors: 10, max: 1000 }))).toMatchObject({ count: 12, columns: 6, floors: 10, max: 1000 });
    expect(sane(P({ count: 1, columns: 1, floors: 2, max: 2 }))).toMatchObject({ count: 1, columns: 1, floors: 2, max: 2 });
  });

  it("a free of another length gives the side boxes of the floors", () => {
    expect(sane(P({ floors: 3, given: "free", free: [true, true] })).free).toEqual(sideFlags(3));
    expect(sane(P({ floors: 3, given: "free", free: [true, "x" as unknown as boolean, true, true, true, true, true] })).free).toEqual(sideFlags(3));
  });

  it("a typed entry that is not three whole numbers in range is dropped, and the last of two for one box stays", () => {
    const s = sane(
      P({
        count: 2,
        floors: 2,
        typed: [
          [0, 1, 5],
          [0, 1, 7],
          [2, 1, 5],
          [1, 5, 5],
          [1, 1, 10000],
          [1, 1, -1],
          [1, 1.5, 3],
          [1, 2] as unknown as [number, number, number],
          [-1, 1, 3],
          [1, 5, 3],
        ],
      }),
    );
    expect(s.typed).toEqual([[0, 1, 7]]);
  });

  it("no typed key when none is kept", () => {
    expect(sane(P({ typed: [[9, 9, 9]] })).typed).toBeUndefined();
    expect("typed" in sane(P())).toBe(false);
  });
});

describe("the typed numbers", () => {
  it("a typed roof is the roof of its house, and its floors are split again", () => {
    const { houses } = made(P({ count: 2, max: 20, typed: [[1, 0, 9]] }));
    expect(houses[1].numbers[0]).toBe(9);
    for (let f = 0; f < 4; f++) expect(houses[1].numbers[1 + 2 * f] + houses[1].numbers[2 + 2 * f]).toBe(9);
    expect(houses[1].wrong).toEqual([false, false, false, false]);
  });

  it("a typed roof of a house does not change the roof of another", () => {
    const plain = made(P({ count: 2, max: 20 })).houses;
    const typed = made(P({ count: 2, max: 20, typed: [[1, 0, 9]] })).houses;
    expect(typed[0]).toEqual(plain[0]);
  });

  it("a floor with both boxes typed keeps both, and is wrong when they do not add up to the roof", () => {
    const right = made(P({ count: 1, floors: 2, max: 10, typed: [[0, 0, 10], [0, 1, 3], [0, 2, 7]] })).houses[0];
    expect(right.numbers.slice(0, 3)).toEqual([10, 3, 7]);
    expect(right.wrong).toEqual([false, false]);

    const wrong = made(P({ count: 1, floors: 2, max: 10, typed: [[0, 0, 10], [0, 1, 3], [0, 2, 4]] })).houses[0];
    expect(wrong.numbers.slice(0, 3)).toEqual([10, 3, 4]);
    expect(wrong.wrong).toEqual([true, false]);
  });

  it("a floor with one box typed gets the roof minus it in the other", () => {
    const { houses } = made(P({ count: 1, floors: 2, max: 10, typed: [[0, 0, 10], [0, 3, 4]] }));
    expect(houses[0].numbers[3]).toBe(4);
    expect(houses[0].numbers[4]).toBe(6);
    expect(houses[0].wrong).toEqual([false, false]);
  });

  it("a floor with one box typed above the roof is wrong, and its other box is 0", () => {
    const { houses } = made(P({ count: 1, floors: 2, max: 10, typed: [[0, 0, 10], [0, 1, 12]] }));
    expect(houses[0].numbers[1]).toBe(12);
    expect(houses[0].numbers[2]).toBe(0);
    expect(houses[0].wrong).toEqual([true, false]);
  });

  it("a floor with none typed keeps its generated left box, at most the roof", () => {
    const plain = made(P({ count: 1, floors: 3, max: 10, seed: 5 })).houses[0];
    const { houses } = made(P({ count: 1, floors: 3, max: 10, seed: 5, typed: [[0, 0, plain.numbers[0]], [0, 5, 0]] }));
    expect(houses[0].numbers[1]).toBe(plain.numbers[1]);
    expect(houses[0].numbers[2]).toBe(plain.numbers[2]);
    expect(houses[0].numbers[3]).toBe(plain.numbers[3]);
    expect(houses[0].numbers[4]).toBe(plain.numbers[4]);
  });
});
