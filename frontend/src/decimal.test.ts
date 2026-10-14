// The decimal text of a maths number: it reads back to the number, money always has its places,
// and a whole part of five digits or more is grouped in threes.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { decimal, GAP } from "./decimal";

describe("decimal", () => {
  it("two places keep their zeros, one place drops them", () => {
    expect([decimal(350, 2), decimal(300, 2), decimal(5, 2), decimal(350, 2, true), decimal(300, 2, true)]).toEqual(["3,50", "3,00", "0,05", "3,50", "3,00"]);
    expect([decimal(30, 1), decimal(35, 1)]).toEqual(["3", "3,5"]);
    expect([decimal(1730, 2), decimal(700, 2)]).toEqual(["17,30", "7,00"]);
  });

  it("reads back to the number, with a comma and no point", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 10 ** 8 }), fc.integer({ min: 0, max: 2 }), fc.boolean(), (n, places, money) => {
        const text = decimal(n, places, money).split(GAP).join("");
        expect(text).not.toContain(".");
        const [whole, fraction = ""] = text.split(",");
        expect(Number(whole) * 10 ** places + Number(fraction.padEnd(places, "0"))).toBe(n);
        if (money) expect(fraction.length).toBe(places);
      }),
    );
  });

  it("groups the whole part in threes from 10 000 on", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 10 ** 9 }), fc.integer({ min: 0, max: 2 }), fc.boolean(), (n, places, money) => {
        const text = decimal(n, places, money);
        const [whole, fraction] = text.split(",");
        const groups = whole.split(GAP);
        expect(groups.join("")).toBe(String(Math.floor(n / 10 ** places)));
        expect(groups.slice(1).every((g) => /^\d{3}$/.test(g))).toBe(true);
        // A whole part of four digits stands alone (1000,00 in #549); a grouped one leads with one to three.
        expect(groups[0]).toMatch(groups.length > 1 ? /^\d{1,3}$/ : /^\d{1,4}$/);
        expect(groups.length > 1).toBe(whole.split(GAP).join("").length >= 5);
        if (fraction !== undefined) expect(fraction).not.toContain(GAP);
      }),
      // The case fast-check drew in 2 runs of 5 (#549): 1000,00 has a whole part of four digits.
      { examples: [[100000, 2, false]] },
    );
  });

  it("sets 9 999 without a gap and 10 000 and 270 091 with one", () => {
    expect([decimal(9999, 0), decimal(10000, 0), decimal(270091, 0), decimal(1000000, 0), decimal(1234567, 2)]).toEqual(["9999", `10${GAP}000`, `270${GAP}091`, `1${GAP}000${GAP}000`, `12${GAP}345,67`]);
  });
});
