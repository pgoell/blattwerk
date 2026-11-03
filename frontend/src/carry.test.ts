import { describe, expect, it } from "vitest";
import { crossesAt } from "./carry";

describe("crossesAt", () => {
  it("landing on 10 is no crossing, and a carry does not run on (#838)", () => {
    expect(crossesAt("+", 7, 3, 0)).toBe(false);
    expect(crossesAt("+", 17, 23, 0)).toBe(false);
    expect(crossesAt("+", 17, 23, 1)).toBe(false);
    expect(crossesAt("+", 8, 5, 0)).toBe(true);
    expect(crossesAt("+", 6, 3, 0)).toBe(false);
    expect(crossesAt("+", 20, 80, 1)).toBe(false);
    expect(crossesAt("+", 395, 7, 1)).toBe(false);
  });
});
