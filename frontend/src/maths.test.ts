import { describe, expect, it } from "vitest";
import { kept } from "./pages/Maths";

// A family of a plus and its minus task.
const fam = (a: number, b: number, family: number) => [
  { op: "+", a, b, family },
  { op: "-", a: a + b, b, family },
];
const limits = { ops: ["+", "-"], max: 20, format: "row", family: "reverse", seed: 1 };

describe("kept", () => {
  it("adds a family the block does not have yet, numbered after its own (#906)", () => {
    const was = { ...limits, count: 2, exercises: [...fam(3, 4, 0), ...fam(5, 2, 1)] } as any;
    // The server's new set for three families holds both of the block's, the new one in the middle.
    const made = { exercises: [...fam(5, 2, 0), ...fam(1, 1, 1), ...fam(3, 4, 2)], loosen: null } as any;
    expect(kept(was, { ...limits, count: 3 } as any, made).exercises).toEqual([...fam(3, 4, 0), ...fam(5, 2, 1), ...fam(1, 1, 2)]);
  });

  it("adds a task the block does not have yet and keeps the server's word on what is in the way (#906)", () => {
    const ex = (a: number) => ({ op: "+", a, b: 1 });
    const was = { ...limits, family: "none", count: 2, exercises: [ex(1), ex(2)] } as any;
    const made = { exercises: [ex(2), ex(7), ex(1)], loosen: ["max"] } as any;
    expect(kept(was, { ...limits, family: "none", count: 3 } as any, made)).toEqual({ exercises: [ex(1), ex(2), ex(7)], loosen: ["max"] });
  });
});
