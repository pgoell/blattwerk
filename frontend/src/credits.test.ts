import { describe, expect, it } from "vitest";
import { EMPTY, creditLine, creditsOf, creditsOn, read, type Credit, type Doc } from "./sheet";

const note = (id: number, licence = "Pixabay-Lizenz"): Credit => ({
  id,
  source: "Pixabay",
  author: id === 1 ? "Ada" : "Josch13",
  licence,
  page: `https://pixabay.com/photos/${id}/`,
});

describe("credits", () => {
  it("stays off for a Pixabay picture until the sheet says on", () => {
    expect(creditsOn({}, ["Pixabay-Lizenz"])).toBe(false);
    expect(creditsOn({ credits: true }, ["Pixabay-Lizenz"])).toBe(true);
    expect(creditsOn({}, ["CC BY 4.0"])).toBe(true);
    expect(creditsOn({ credits: false }, ["CC BY 4.0"])).toBe(false);
    expect(creditsOn({}, [])).toBe(false);
  });

  it("keeps a stored choice and drops anything else", () => {
    expect(read({ ...EMPTY, credits: true }).credits).toBe(true);
    expect(read({ ...EMPTY, credits: false }).credits).toBe(false);
    expect(read({ ...EMPTY, credits: "yes" } as unknown as Doc).credits).toBeUndefined();
  });

  it("lists each found picture once, in the order of the sheet", () => {
    const doc = {
      ...EMPTY,
      pages: [{
        blocks: [
          { type: "image", props: { upload: 2 } },
          { type: "image", props: { upload: 2 } },
          { type: "text", props: {} },
          { type: "image", props: { upload: 1 } },
        ],
      }],
    } as unknown as Doc;
    expect(creditsOf(doc, [note(1), note(2)]).map((item) => item.id)).toEqual([2, 1]);
    expect(creditLine(note(2))).toBe("Pixabay, Josch13, Pixabay-Lizenz, https://pixabay.com/photos/2/");
  });
});
