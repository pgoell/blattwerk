// The decimal text of a maths number: it reads back to the number, and money always has its places.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { decimal } from "./decimal";

describe("decimal", () => {
  it("cuts the zeros after the comma, and keeps them as money", () => {
    expect([decimal(350, 2), decimal(300, 2), decimal(5, 2), decimal(350, 2, true), decimal(300, 2, true)]).toEqual(["3,5", "3", "0,05", "3,50", "3,00"]);
  });

  it("reads back to the number, with a comma and no point", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 10 ** 8 }), fc.integer({ min: 0, max: 2 }), fc.boolean(), (n, places, money) => {
        const text = decimal(n, places, money);
        expect(text).not.toContain(".");
        const [whole, fraction = ""] = text.split(",");
        expect(Number(whole) * 10 ** places + Number(fraction.padEnd(places, "0"))).toBe(n);
        if (money) expect(fraction.length).toBe(places);
      }),
    );
  });
});
