// The blocks a Selbstkontrolle can link, and the wrong answers mixed into the list. The expected
// texts are what each block's own key writes, worked out here from its generator, not from tasksOf.
import { describe, expect, it } from "vitest";
import type { Block, Doc } from "../sheet";
import { checked, labelOf, tasksOf, type SelbstkontrolleProps } from "../selbstkontrolle";
import { made as housesOf, sane as saneHaus } from "../zahlenhaus";
import { made as chainsOf, sane as saneKette, stepLabel } from "../zahlenkette";
import { made as tablesOf, sane as saneTab } from "../rechentabelle";

const block = (type: string, props: object, id = "m"): Block =>
  ({ id, type, x: 0, y: 0, w: 180, h: 80, z: 0, locked: false, props }) as unknown as Block;

const sheet = (blocks: Block[]): Doc => ({ pages: [{ blocks }], guides: { x: [], y: [] }, grid: 0 });

const texts = (b: Block): string[] | undefined => {
  const tasks = tasksOf(b);
  return tasks?.flat().map((r) => r.text).sort();
};

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

describe("tasks of the blocks the issue names", () => {
  it("a Zahlenhaus gives each number the key writes, and none of a wrong floor", () => {
    const props = { count: 2, floors: 2, given: "roof", seed: 4 };
    const want: string[] = [];
    for (const h of housesOf(saneHaus(props as never)).houses) {
      h.numbers.forEach((n, j) => {
        if (h.given[j]) return;
        if (j > 0 && h.wrong[Math.floor((j - 1) / 2)]) return;
        want.push(String(n));
      });
    }
    expect(want.length).toBeGreaterThan(0);
    expect(texts(block("zahlenhaus", props))).toEqual(want.sort());
  });

  it("a Zahlenkette gives the hidden rings and the step the key writes on the arc", () => {
    const props = { count: 2, rings: 4, showStep: false, seed: 4 };
    const p = saneKette(props as never);
    const want: string[] = [];
    for (const c of chainsOf(p).chains) {
      if (c.over || c.wrong) continue;
      c.numbers.forEach((n, j) => {
        if (!c.given[j]) want.push(String(n));
      });
      if (!p.showStep) for (let j = 1; j < c.numbers.length; j++) want.push(stepLabel(p.op, c.step));
    }
    expect(want.length).toBeGreaterThan(0);
    expect(texts(block("zahlenkette", props))).toEqual(want.sort());
  });

  it("a Rechentabelle gives each hidden number the key writes", () => {
    const props = { count: 1, rows: 2, cols: 2, hideRows: 1, seed: 4 };
    const want: string[] = [];
    for (const t of tablesOf(saneTab(props as never)).tables) {
      if (t.wrong) continue;
      t.cols.forEach((n, j) => {
        if (!t.colShown[j]) want.push(String(n));
      });
      t.rows.forEach((n, r) => {
        if (!t.rowShown[r]) want.push(String(n));
      });
      t.cells.forEach((row, r) =>
        row.forEach((n, c) => {
          if (!t.struck[r][c] && !t.madeUp[r][c] && !t.given[r][c]) want.push(String(n));
        }),
      );
    }
    expect(want.length).toBeGreaterThan(0);
    expect(texts(block("rechentabelle", props))).toEqual(want.sort());
  });
});

describe("every other task block with written answers", () => {
  const kinds = ["pfeilbild", "operatorfeld", "rechenrad", "magischesquadrat", "malquadrat", "zerlegungsfeld", "halbschriftlich", "zehnerfeld", "stellenwertbild", "textaufgabe"];

  it.each(kinds)("links a %s and takes at least one result", (type) => {
    const found = texts(block(type, { seed: 7 }));
    expect(found).toBeDefined();
    expect(found?.length).toBeGreaterThan(0);
  });

  it("links a Diagramm whose bar the pupil draws", () => {
    const props = { points: [{ value: "", label: "A", color: "#c0392b", answer: "4" }] };
    expect(texts(block("diagramm", props))).toEqual(["4"]);
  });

  it("names a Zahlenhaus Zahlenhaus", () => {
    const b = block("zahlenhaus", { seed: 1 });
    expect(labelOf(b, sheet([b]))).toBe("Zahlenhaus");
  });

  it("does not link a text", () => {
    expect(tasksOf(block("text", { text: "Hallo" }))).toBeUndefined();
  });
});

describe("falsche Lösungen", () => {
  const maths = (id: string, result: number, y: number): Block =>
    ({
      id,
      type: "maths",
      x: 10,
      y,
      w: 180,
      h: 20,
      z: 0,
      locked: false,
      props: { ops: ["+"], decimals: 0, exercises: [{ op: "+", a: 1, b: result - 1, result, rest: 0 }], columns: 1, size: 14 },
    }) as unknown as Block;

  it("mixes in the asked count of answers that are not results, and the same seed keeps them", () => {
    const doc = sheet([maths("a", 7, 0), maths("b", 9, 40)]);
    const props = { ...P({ links: ["a", "b"], seed: 4 }), wrongs: 3 } as SelbstkontrolleProps;
    const mixed = checked(props, doc).mixed;
    expect(mixed).toHaveLength(5);
    expect(mixed.filter((t) => t !== "7" && t !== "9")).toHaveLength(3);
    expect(checked(props, doc).mixed).toEqual(mixed);
  });
});
