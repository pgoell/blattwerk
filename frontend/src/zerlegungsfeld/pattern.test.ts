// Patterns on a Zerlegungsfeld's first and second number (#839, left open by #827).
import { describe, expect, it } from "vitest";
import { DEFAULTS, made } from "../zerlegungsfeld";

describe("Zerlegungsfeld patterns", () => {
  it("keeps the first number to X3 and the second to one digit", () => {
    const tasks = made({ ...DEFAULTS, seed: 1, max: 100, count: 6, pa: "X3", pb: "X" }).tasks;
    expect(tasks.every((t) => !t.wrong)).toBe(true);
    for (const t of tasks) {
      expect(String(t.values[0])).toMatch(/^[1-9]3$/);
      expect(String(t.values[1])).toMatch(/^[0-9]$/);
    }
  });

  it("marks every task wrong when the pattern leaves no number", () => {
    const tasks = made({ ...DEFAULTS, seed: 1, max: 20, count: 4, pa: "X0" }).tasks;
    expect(tasks).toHaveLength(4);
    expect(tasks.every((t) => t.wrong)).toBe(true);
  });

  it("keeps a zero out of both numbers when the switch is off", () => {
    const tasks = made({ ...DEFAULTS, seed: 2, max: 100, count: 6, nil: false, pa: "XX", pb: "X" }).tasks;
    expect(tasks.every((t) => !t.wrong)).toBe(true);
    for (const t of tasks) {
      expect(String(t.values[0])).not.toContain("0");
      expect(String(t.values[1])).not.toContain("0");
      expect(String(t.values[0])).toMatch(/^[1-9][1-9]$/);
    }
  });
});
