// The Selbstkontrolle model: the stored props, the results of the linked blocks, the mixed and word checks, the sums,
// the letters and the height. The expected values are written by hand.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import type { Block, Doc } from "./sheet";
import { checked, heightFor, labelOf, lettersOf, ordered, sane, tasksOf, type SelbstkontrolleProps } from "./selbstkontrolle";

const P = (over: Partial<SelbstkontrolleProps> = {}): SelbstkontrolleProps => ({
  form: "mixed",
  links: [],
  word: "",
  title: "Selbstkontrolle",
  size: 14,
  turn: "none",
  seed: 1,
  ...over,
});

// A maths block with the given exercises; the limits are those a plain addition block has.
const maths = (id: string, exercises: unknown[], over: Record<string, unknown> = {}, y = 0): Block =>
  ({ id, type: "maths", x: 10, y, w: 180, h: 40, z: 0, locked: false, props: { ops: ["+"], decimals: 0, exercises, columns: 1, size: 14, ...over } }) as unknown as Block;

const sheet = (blocks: Block[], more: Block[] = []): Doc => ({ pages: [{ blocks }, { blocks: more }], guides: { x: [], y: [] }, grid: 0 });

const sum = (a: number, b: number, result: number) => ({ op: "+", a, b, result, rest: 0 });

const selbst = (over: Partial<SelbstkontrolleProps>): Block =>
  ({ id: "s", type: "selbstkontrolle", x: 10, y: 200, w: 180, h: 30, z: 0, locked: false, props: P(over) }) as unknown as Block;

describe("sane", () => {
  it("never throws on any JSON value", () => {
    fc.assert(
      fc.property(fc.jsonValue(), (v) => {
        const s = sane(v as unknown as SelbstkontrolleProps);
        expect(["mixed", "word", "sum"]).toContain(s.form);
        expect(["none", "upside", "fold"]).toContain(s.turn);
        expect(s.size).toBeGreaterThanOrEqual(8);
        expect(s.size).toBeLessThanOrEqual(24);
      }),
    );
  });

  it("gives the defaults for wrong kinds and values out of range", () => {
    const s = sane({ form: "nope", links: [1, "a"], word: 3, title: null, size: 99, turn: "side", seed: 1.5 } as unknown as SelbstkontrolleProps);
    expect(s).toEqual({ form: "mixed", links: ["a"], word: "", title: "Selbstkontrolle", size: 14, turn: "none", seed: 0 });
  });
});

describe("tasksOf", () => {
  it("gives the sum of a calc row as its one result", () => {
    expect(tasksOf(maths("a", [sum(3, 4, 7)]))).toEqual([[{ text: "7", value: 7 }]]);
  });

  it("gives the hidden part of a gap exercise", () => {
    expect(tasksOf(maths("a", [{ op: "+", a: 3, b: 4, result: 7, rest: 0, hide: "a" }]))).toEqual([[{ text: "3", value: 3 }]]);
  });

  it("gives the quotient and its rest as text, the quotient as value", () => {
    expect(tasksOf(maths("a", [{ op: "+", a: 17, b: 5, result: 3, rest: 2 }]))).toEqual([[{ text: "3 R 2", value: 3 }]]);
  });

  it("gives the sign of a comparison, with no value", () => {
    const cmp = { left: { value: 3 }, right: { value: 5 }, sign: "<" };
    expect(tasksOf(maths("a", [cmp]))).toEqual([[{ text: "<" }]]);
  });

  it("writes money with two places and the euro sign", () => {
    expect(tasksOf(maths("a", [sum(350, 0, 350)], { decimals: 2, money: true }))).toEqual([[{ text: "3,50 €", value: 350 }]]);
  });

  it("gives an Uhr that reads one task per clock, and a drawn Uhr none", () => {
    const uhr = (task: string) =>
      ({ id: "u", type: "uhr", x: 0, y: 0, w: 100, h: 130, z: 0, locked: false, props: { numbers: "all", minutes: true, ring: false, task, answer: "box", format: "12", region: "nach", count: 2, cols: 2, step: 60, fill: "random", seed: 1 } }) as unknown as Block;
    expect(tasksOf(uhr("read"))).toHaveLength(2);
    expect(tasksOf(uhr("draw"))).toEqual([]);
  });
});

describe("checked and the forms", () => {
  const a = maths("a", [sum(3, 4, 7), sum(4, 5, 9)], {}, 0);
  const b = maths("b", [sum(2, 5, 7)], {}, 50);

  it("mixed holds every result as often as it occurs, and the same seed gives the same order", () => {
    const doc = sheet([a, b]);
    const c = checked(P({ links: ["a", "b"], seed: 3 }), doc);
    expect([...c.mixed].sort()).toEqual(["7", "7", "9"]);
    expect(checked(P({ links: ["a", "b"], seed: 3 }), doc).mixed).toEqual(c.mixed);
  });

  it("another seed gives another order", () => {
    const doc = sheet([a, b]);
    const orders = new Set<string>();
    for (let seed = 1; seed <= 10; seed++) orders.add(checked(P({ links: ["a", "b"], seed }), doc).mixed.join(","));
    expect(orders.size).toBeGreaterThan(1);
  });

  it("sum gives one line per source with values, labelled", () => {
    const doc = sheet([a, b]);
    expect(checked(P({ form: "sum", links: ["a", "b"] }), doc).sums).toEqual([
      ["Rechnen 1", "16"],
      ["Rechnen 2", "7"],
    ]);
  });

  it("word fault: no word", () => {
    expect(checked(P({ form: "word", links: ["a", "b"], word: " " }), sheet([a, b])).fault).toBe("Gib ein Lösungswort ein.");
  });

  it("word fault: the letters count is not the task count", () => {
    expect(checked(P({ form: "word", links: ["a", "b"], word: "AB" }), sheet([a, b])).fault).toBe("Das Wort hat 2 Buchstaben, die Aufgaben sind 3.");
  });

  it("word fault: two tasks with one result and two letters", () => {
    expect(checked(P({ form: "word", links: ["a", "b"], word: "ABC" }), sheet([a, b])).fault).toBe(
      "Aufgabe 1 und 3 haben dasselbe Ergebnis 7, das Wort braucht dort A und C.",
    );
  });

  it("word without fault gives the letters per source and a table of the distinct results", () => {
    const doc = sheet([a, b]);
    const c = checked(P({ form: "word", links: ["a", "b"], word: "aba" }), doc);
    expect(c.fault).toBeUndefined();
    expect(c.letters.get("a")).toEqual(["A", "B"]);
    expect(c.letters.get("b")).toEqual(["A"]);
    expect([...c.table].sort()).toEqual([
      ["7", "A"],
      ["9", "B"],
    ]);
  });

  it("the same word and seed give the same table order, and a fault gives letters of \"\"", () => {
    const doc = sheet([a, b]);
    expect(checked(P({ form: "word", links: ["a", "b"], word: "ABC" }), doc).letters.get("a")).toEqual(["", ""]);
    expect(checked(P({ form: "word", links: ["a", "b"], word: "ABA", seed: 2 }), doc).table).toEqual(checked(P({ form: "word", links: ["a", "b"], word: "ABA", seed: 2 }), doc).table);
  });

  it("the first word Selbstkontrolle of the sheet gives the letters of lettersOf", () => {
    const doc = sheet([a, b, selbst({ form: "word", links: ["a", "b"], word: "ABA" })]);
    const letters = lettersOf(doc);
    expect(letters.get("a")).toEqual(["A", "B"]);
    expect(letters.get("b")).toEqual(["A"]);
  });
});

describe("links and labels", () => {
  it("a link to no block is lost and no source", () => {
    const c = checked(P({ links: ["a", "zz"] }), sheet([maths("a", [sum(1, 1, 2)])]));
    expect(c.lost).toEqual(["zz"]);
    expect(c.sources.map((b) => b.id)).toEqual(["a"]);
  });

  it("the sources follow the sheet order, page then y, not the link order", () => {
    const doc = sheet([maths("a", [sum(1, 1, 2)], {}, 60), maths("b", [sum(1, 1, 2)], {}, 10)], [maths("c", [sum(1, 1, 2)], {}, 0)]);
    expect(ordered(doc, ["a", "b", "c"]).map((b) => b.id)).toEqual(["b", "a", "c"]);
  });

  it("labelOf adds a number only with more than one block of the type", () => {
    const one = sheet([maths("a", [sum(1, 1, 2)])]);
    expect(labelOf(one.pages[0].blocks[0], one)).toBe("Rechnen");
    const two = sheet([maths("a", [sum(1, 1, 2)]), maths("b", [sum(1, 1, 2)], {}, 50)]);
    expect(labelOf(two.pages[0].blocks[1], two)).toBe("Rechnen 2");
  });
});

describe("heightFor", () => {
  it("is 4 mm of padding and the heading alone with no link", () => {
    // Heading 1.2 times 14 pt, plus 4 mm, with no line of content.
    const h = heightFor(P({ links: [] }), sheet([]), 180);
    expect(h).toBeCloseTo(1.2 * 14 * (25.4 / 72) + 4, 6);
  });
});
