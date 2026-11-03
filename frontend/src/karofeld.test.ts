// The Karofeld (#831): one digit or sign to a square, and the moves that keep it that way.
import { describe, expect, it } from "vitest";
import { SIGNS } from "./sheet/maths";
import {
  DEFAULTS,
  boxOf,
  deletedRow,
  deletedSign,
  entered,
  figure,
  fontOf,
  gridPoints,
  insertedRow,
  insertedSign,
  painted,
  sane,
  snapped,
  typeKaro,
  type KarofeldProps,
} from "./karofeld";

const base = (): KarofeldProps => sane({ ...DEFAULTS, cols: 4, rows: 3, size: 8, seed: 1 });

const signs = (props: KarofeldProps, row: number) => (props.cells?.[row] ?? []).map((sq) => sq.sign);

describe("Karofeld", () => {
  it("puts one digit or sign in the square and moves to the next", () => {
    const once = typeKaro(base(), "7");
    expect(once?.cells?.[0][0].sign).toBe("7");
    expect(once?.cells?.[0][0].sign).toHaveLength(1);
    expect(once?.caret).toEqual([1, 0]);
    const twice = typeKaro(once!, "4");
    expect(signs(twice!, 0)).toEqual(["7", "4", undefined, undefined]);
    expect(twice?.caret).toEqual([2, 0]);
  });

  it("replaces the square instead of holding a second sign", () => {
    const once = typeKaro(base(), "7")!;
    const again = typeKaro({ ...once, caret: [0, 0] }, "8")!;
    expect(again.cells?.[0][0].sign).toBe("8");
    expect(typeKaro(base(), "12")).toBeUndefined();
    expect(typeKaro(base(), "a")).toBeUndefined();
  });

  it("stores a minus, a times and a division as the sheet's signs", () => {
    expect(typeKaro(base(), "-")?.cells?.[0][0].sign).toBe(SIGNS["-"]);
    expect(typeKaro(base(), "*")?.cells?.[0][0].sign).toBe(SIGNS["*"]);
    expect(typeKaro(base(), "/")?.cells?.[0][0].sign).toBe(SIGNS["/"]);
  });

  it("attaches a comma or a point to the digit and does not spend a square on it", () => {
    const digit = typeKaro(base(), "3")!;
    const comma = typeKaro(digit, ",")!;
    expect(comma.cells?.[0][0]).toMatchObject({ sign: "3", mark: "," });
    expect(comma.caret).toEqual([1, 0]);
    expect(signs(comma, 0).filter(Boolean)).toEqual(["3"]);
    const point = typeKaro(digit, ".")!;
    expect(point.cells?.[0][0].mark).toBe(".");
    const plus = typeKaro(base(), "+")!;
    expect(typeKaro(plus, ",")?.cells?.[0][0].mark).toBeUndefined();
  });

  it("Enter goes to the first square of the next row", () => {
    const row = typeKaro(typeKaro(base(), "1")!, "2")!;
    expect(entered(row).caret).toEqual([0, 1]);
    const last = entered({ ...base(), caret: [2, 2] });
    expect(last.caret).toEqual([2, 2]);
  });

  it("inserts a sign and shifts the rest of the row right", () => {
    let p = base();
    for (const ch of ["1", "2", "3"]) p = typeKaro(p, ch)!;
    p = insertedSign({ ...p, caret: [1, 0] });
    expect(signs(p, 0)).toEqual(["1", undefined, "2", "3", undefined]);
    expect(p.cols).toBe(5);
    expect(p.caret).toEqual([1, 0]);
    expect(p.cells?.[1]).toHaveLength(5);
  });

  it("deletes a sign and shifts the rest of the row left", () => {
    let p = base();
    for (const ch of ["1", "2", "3"]) p = typeKaro(p, ch)!;
    p = deletedSign({ ...p, caret: [1, 0] });
    expect(signs(p, 0).slice(0, 3)).toEqual(["1", "3", undefined]);
    expect(p.caret).toEqual([1, 0]);
  });

  it("inserts a row and shifts the rows below it down", () => {
    const first = typeKaro(base(), "1")!;
    const second = typeKaro(entered(first), "2")!;
    const added = insertedRow({ ...second, caret: [0, 1] });
    expect(added.rows).toBe(4);
    expect(added.cells?.[0][0].sign).toBe("1");
    expect(added.cells?.[1][0].sign).toBeUndefined();
    expect(added.cells?.[2][0].sign).toBe("2");
    expect(added.caret).toEqual([0, 1]);
  });

  it("deletes a row and shifts the rows below it up", () => {
    const first = typeKaro(base(), "1")!;
    const second = typeKaro(entered(first), "2")!;
    const gone = deletedRow({ ...second, caret: [0, 0] });
    expect(gone.rows).toBe(2);
    expect(gone.cells?.[0][0].sign).toBe("2");
    expect(deletedRow({ ...base(), rows: 1 }).rows).toBe(1);
  });

  it("keeps a Lösungsstrich, thick edges and a fill on that square", () => {
    const digit = typeKaro(base(), "5")!;
    const p = painted({ ...digit, caret: [0, 0] }, { line: true, thick: [true, false, true, false], fill: "#ffe066" });
    expect(p.cells?.[0][0]).toMatchObject({ sign: "5", line: true, thick: [true, false, true, false], fill: "#ffe066" });
    expect(painted(p, { fill: null }).cells?.[0][0].fill).toBeUndefined();
  });

  it("lets the square's size in mm set the font size", () => {
    expect(fontOf(16) / 16).toBe(fontOf(5) / 5);
    expect(fontOf(10)).toBeGreaterThan(fontOf(5));
    expect(boxOf(sane({ ...DEFAULTS, cols: 4, rows: 3, size: 8, seed: 1 }))).toEqual({ w: 32, h: 24 });
    expect(boxOf(sane({ ...DEFAULTS, cols: 4, rows: 3, size: 10, seed: 1 })).w).toBe(40);
  });

  it("draws Karos, Kreise, a Punktefeld and an isometric grid as different figures", () => {
    const props = base();
    const karos = figure({ ...props, look: "karos" });
    const kreise = figure({ ...props, look: "kreise" });
    const punkte = figure({ ...props, look: "punkte" });
    const iso = figure({ ...props, look: "iso" });
    expect(karos).toEqual({ look: "karos", lines: 9, circles: 0, dots: 0 });
    expect(kreise).toEqual({ look: "kreise", lines: 9, circles: 12, dots: 0 });
    expect(punkte).toEqual({ look: "punkte", lines: 0, circles: 0, dots: 12 });
    expect(iso.look).toBe("iso");
    expect(iso.circles).toBe(0);
    expect(iso.dots).toBe(0);
    expect(iso.lines).toBeGreaterThan(0);
    expect(iso.lines).not.toBe(karos.lines);
  });

  it("snaps a point to the nearest grid point of the field", () => {
    const props = base();
    const points = gridPoints([10, 20], props);
    expect(points).toContainEqual([10, 20]);
    expect(points).toContainEqual([10 + 4 * 8, 20 + 3 * 8]);
    expect(snapped(points, [10.4, 20.2], 1)).toEqual([10, 20]);
    expect(snapped(points, [80, 80], 1)).toBeUndefined();
    expect(gridPoints([10, 20], { ...props, look: "iso" })).not.toEqual(points);
  });
});
