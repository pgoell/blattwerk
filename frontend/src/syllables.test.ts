import { expect, it } from "vitest";
import { cuts, pieces, split, words } from "./syllables";

it("splits a word, and a text into its pieces", () => {
  expect(split("Fenster")).toEqual([4]);
  expect(split("Maus")).toEqual([]);
  expect(cuts("Abend", { abend: [1] })).toEqual([1]);
  expect(words("Die Maus, die 3 Mäuse")).toEqual(["Die", "Maus", "die", "Mäuse"]);
  expect(pieces("Fenster 3!").map((p) => p.text)).toEqual(["Fens", "ter", " 3!"]);
});
