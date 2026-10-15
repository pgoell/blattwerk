// The total score box of a Klassenarbeit follows its task boxes, and nothing else moves.
import { describe, expect, it } from "vitest";
import { totals } from "./totals";
import type { Block, Doc } from "./sheet";

const points = (id: string, max: number, total = false): Block => ({ id, type: "points", x: 0, y: 0, w: 10, h: 10, z: 0, locked: false, props: total ? { max, total } : { max } }) as Block;
const page = (...maxes: [string, number, boolean?][]) => ({ blocks: maxes.map(([id, max, total]) => points(id, max, total)) });
const doc = (...pages: { blocks: Block[] }[]): Doc => ({ pages, guides: { x: [], y: [] }, grid: 0 });
// The Klassenarbeit: three pages, each with a marked total 60 and two tasks of 10. Unmarked, it is an ordinary sheet.
const klassenarbeit = (marked = true) =>
  doc(
    page(["t1", 60, marked], ["a1", 10], ["b1", 10]),
    page(["t2", 60, marked], ["a2", 10], ["b2", 10]),
    page(["t3", 60, marked], ["a3", 10], ["b3", 10]),
  );
const maxes = (d: Doc) => d.pages.map((p) => p.blocks.filter((b) => b.type === "points").map((b) => (b as Block & { props: { max: number } }).props.max));
// Sets the max of the boxes named by `ids`.
const set = (d: Doc, changes: Record<string, number>): Doc => ({
  ...d,
  pages: d.pages.map((p) => ({ ...p, blocks: p.blocks.map((b) => (b.id in changes ? ({ ...b, props: { ...(b as Block & { props: object }).props, max: changes[b.id] } }) as Block : b)) })),
});

describe("totals", () => {
  it("moves the total on every page when one task changes", () => {
    const before = klassenarbeit();
    expect(maxes(totals(before, set(before, { a1: 15 })))).toStrictEqual([
      [65, 15, 10],
      [65, 10, 10],
      [65, 10, 10],
    ]);
  });

  it("moves the total by the sum of two tasks changed at once", () => {
    const before = klassenarbeit();
    const out = totals(before, set(before, { a1: 12, b2: 9 }));
    expect(maxes(out)[0]).toStrictEqual([61, 12, 10]);
    expect(maxes(out)[1]).toStrictEqual([61, 10, 9]);
  });

  it("does nothing when the total itself is changed", () => {
    const before = klassenarbeit();
    const after = set(before, { t1: 70 });
    expect(totals(before, after)).toBe(after);
  });

  it("does nothing on a sheet with no marked total, however it adds up", () => {
    const before = klassenarbeit(false);
    const after = set(before, { a1: 15 });
    expect(totals(before, after)).toBe(after);
  });

  it("counts a new task box in the total", () => {
    const before = klassenarbeit();
    const added = { ...before, pages: [{ blocks: [...before.pages[0].blocks, points("new", 5)] }, ...before.pages.slice(1)] };
    expect(maxes(totals(before, added))).toStrictEqual([
      [65, 10, 10, 5],
      [65, 10, 10],
      [65, 10, 10],
    ]);
  });

  it("takes a deleted task box out of the total", () => {
    const before = klassenarbeit();
    const deleted = { ...before, pages: [{ blocks: before.pages[0].blocks.filter((b) => b.id !== "a1") }, ...before.pages.slice(1)] };
    expect(maxes(totals(before, deleted))).toStrictEqual([
      [50, 10],
      [50, 10, 10],
      [50, 10, 10],
    ]);
  });

  it("sums a pasted marked total with the changed task", () => {
    const before = doc(page(["a1", 10], ["b1", 10]));
    const after = set(before, { a1: 15 });
    const pasted = { ...after, pages: [{ blocks: [...after.pages[0].blocks, points("tp", 5, true)] }] };
    expect(maxes(totals(before, pasted))).toStrictEqual([[15, 10, 25]]);
  });

  it("leaves the totals as they are when no task changed", () => {
    const before = klassenarbeit();
    const after = set(before, { t1: 70, t2: 70 });
    expect(totals(before, after)).toBe(after);
  });

  it("keeps a total typed by hand in the same step as a task, as the panel does with a total and a task picked", () => {
    const before = klassenarbeit();
    const after = set(before, { t1: 7, a1: 7 });
    expect(totals(before, after)).toBe(after);
  });

  it("leaves a sheet with no tasks left as it is", () => {
    const before = klassenarbeit();
    const noTasks = { ...before, pages: before.pages.map((p) => ({ blocks: p.blocks.filter((b) => (b as Block & { props: { total?: boolean } }).props.total === true) })) };
    expect(totals(before, noTasks)).toBe(noTasks);
  });

  it("clamps the total to 999", () => {
    const before = klassenarbeit();
    const big = set(before, { a1: 999 });
    expect(maxes(totals(before, big))[0][0]).toBe(999);
    const huge = set(before, { a1: 999, b1: 999 });
    expect(maxes(totals(before, huge))[0][0]).toBe(999);
  });

  it("returns the same object when nothing changed", () => {
    const before = klassenarbeit();
    const after = { ...before, pages: before.pages.map((p) => ({ ...p, blocks: [...p.blocks] })) };
    expect(totals(before, after)).toBe(after);
  });

  it("keeps the blocks it does not change", () => {
    const before = klassenarbeit();
    const after = set(before, { a1: 15 });
    const out = totals(before, after);
    expect(out.pages[0].blocks[2]).toBe(after.pages[0].blocks[2]);
    expect(out.pages[0].blocks[1]).toBe(after.pages[0].blocks[1]);
  });
});
