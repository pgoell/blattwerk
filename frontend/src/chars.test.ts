import { expect, it } from "vitest";
import { CHARS, added, fromCode, remembered } from "./chars";

it("lists the symbols the text bar offers", () => {
  expect(CHARS.map(([ch]) => ch).join(" ")).toBe("· × ÷ ≈ ≠ ≤ ≥ ² α β γ € © ∥ ⊥");
});

it("reads a Unicode code and refuses what cannot be shown", () => {
  expect(fromCode("U+00B7")).toBe("·");
  expect(fromCode("u+00b7")).toBe("·");
  expect(fromCode("00B7")).toBe("·");
  expect(fromCode("U+20AC")).toBe("€");
  expect(fromCode("U+1F4A1")).toBe("💡");
  expect(fromCode("U+")).toBeUndefined();
  expect(fromCode("U+0000")).toBeUndefined();
  expect(fromCode("U+007F")).toBeUndefined();
  expect(fromCode("U+D800")).toBeUndefined();
  expect(fromCode("U+110000")).toBeUndefined();
  expect(fromCode("Wort")).toBeUndefined();
});

it("keeps the last symbols, newest first, and no more than eight", () => {
  expect(remembered([], "×")).toEqual(["×"]);
  expect(remembered(["×", "·"], "×")).toEqual(["×", "·"]);
  expect(remembered(["1", "2", "3", "4", "5", "6", "7", "8"], "9")).toEqual(["9", "1", "2", "3", "4", "5", "6", "7"]);
});

it("adds a character at the end, and a bold word stays bold", () => {
  expect(added({ text: "Hallo" }, "×").text).toBe("Hallo×");
  expect(added({ text: "" }, "€").text).toBe("€");
  expect(added({ text: "Hallo\nWelt" }, "×").text).toBe("Hallo\nWelt×");
  const rich = added({ text: "ab", rich: [{ runs: [{ text: "ab", bold: true }] }] }, "×");
  expect(rich.text).toBe("ab×");
  expect(rich.rich?.[0].runs[0]).toEqual({ text: "ab×", bold: true });
});
