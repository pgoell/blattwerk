// A Diagramm: bars, columns and a pie from a few values, and the bar a pupil draws.
import { describe, expect, it } from "vitest";
import { COLORS, DEFAULTS, chart, read, sane, type DiagrammProps, type Point } from "./diagramm";

const point = (value: string, label = "A", color: string = COLORS[0], answer?: string): Point => ({
  value,
  label,
  color,
  ...(answer ? { answer } : {}),
});

const props = (over: Partial<DiagrammProps> = {}): DiagrammProps => sane({ ...DEFAULTS, ...over });

describe("read", () => {
  it("reads a number and a unit, with a comma or a dot", () => {
    expect(read("3,5 kg")).toEqual({ n: 3.5, text: "3,5 kg" });
    expect(read("3.5")).toEqual({ n: 3.5, text: "3.5" });
    expect(read("12")).toEqual({ n: 12, text: "12" });
    expect(read("  3,5kg ")).toEqual({ n: 3.5, text: "3,5kg" });
  });

  it("reads nothing from an empty value, a word or a negative", () => {
    expect(read("")).toBeUndefined();
    expect(read("kg")).toBeUndefined();
    expect(read("-2")).toBeUndefined();
  });
});

describe("sane", () => {
  it("gives the sample columns", () => {
    expect(sane(undefined)).toEqual(DEFAULTS);
    expect(DEFAULTS.kind).toBe("saeulen");
    expect(DEFAULTS.points).toHaveLength(3);
  });

  it("drops a kind it does not know, a point that is not an object, and a blank answer", () => {
    const got = sane({
      kind: "nope",
      values: "nope",
      axes: "nope",
      grid: "nope",
      legend: "yes",
      seed: 1.5,
      xTitle: 4,
      points: [{ value: "3,5 kg", label: " Äpfel ", color: "#C0392B", answer: "  " }, { value: 4 }, "no"],
    });
    expect(got.kind).toBe("saeulen");
    expect(got.values).toBe("aussen");
    expect(got.axes).toBe("beide");
    expect(got.grid).toBe("haupt");
    expect(got.legend).toBe(true);
    expect(got.seed).toBe(0);
    expect(got.xTitle).toBe("");
    expect(got.points).toEqual([{ value: "3,5 kg", label: " Äpfel ", color: "#c0392b" }]);
  });

  it("keeps eight points and no more", () => {
    const points = Array.from({ length: 10 }, (_, i) => point(String(i), String(i)));
    expect(sane({ points }).points).toHaveLength(8);
  });
});

describe("chart", () => {
  const columns = props({
    kind: "saeulen",
    points: [point("2", "A"), point("4", "B", COLORS[1]), point("6", "C", COLORS[2])],
    legend: true,
    values: "aussen",
    axes: "beide",
    xTitle: "Obst",
    yTitle: "kg",
    grid: "haupt",
  });

  it("draws columns whose heights follow the values and whose slots stay put", () => {
    const drawn = chart(columns, false);
    expect(drawn.bars.map((b) => b.h)).toHaveLength(3);
    expect(drawn.bars[1].h).toBeCloseTo(drawn.bars[0].h * 2);
    expect(drawn.bars[2].h).toBeCloseTo(drawn.bars[0].h * 3);
    expect(drawn.bars[2].y).toBeCloseTo(drawn.plot.y);
    expect(drawn.bars[0].w).toBeCloseTo(drawn.bars[2].w);
    expect(drawn.bars[2].x).toBeGreaterThan(drawn.bars[1].x);
    expect(drawn.bars.every((b) => b.answer === false)).toBe(true);
  });

  it("scales 3,5 kg to three and a half of four and writes the value", () => {
    const drawn = chart(props({ points: [point("3,5 kg", "Äpfel")], legend: false, grid: "keine" }), false);
    expect(drawn.bars[0].h / drawn.plot.h).toBeCloseTo(3.5 / 4);
    expect(drawn.values.map((v) => v.text)).toEqual(["3,5 kg"]);
    expect(drawn.ticks.map((t) => t.text)).toEqual(["0", "1", "2", "3", "4"]);
  });

  it("leaves an empty value undrawn until the key, in its own slot", () => {
    const gapped = props({
      points: [point("2", "A"), point("", "B", COLORS[1], "6"), point("4", "C", COLORS[2])],
      values: "aussen",
    });
    const pupil = chart(gapped, false);
    expect(pupil.bars.map((b) => b.i)).toEqual([0, 2]);
    expect(pupil.bars[1].x).toBeGreaterThan(pupil.bars[0].x + pupil.bars[0].w);
    const key = chart(gapped, true);
    expect(key.bars.map((b) => b.i)).toEqual([0, 1, 2]);
    expect(key.bars[1].answer).toBe(true);
    expect(key.bars[1].h).toBeCloseTo(key.bars[0].h * 3);
    expect(key.values.filter((v) => v.answer).map((v) => v.text)).toEqual(["6"]);
  });

  it("puts a value outside above a column and inside the column", () => {
    const outside = chart(columns, false);
    expect(outside.values[0].y).toBeLessThan(outside.bars[0].y);
    const inside = chart({ ...columns, values: "innen" }, false);
    expect(inside.values[0].y).toBeGreaterThan(inside.bars[0].y);
    expect(inside.values[0].y).toBeLessThan(inside.bars[0].y + inside.bars[0].h);
    expect(chart({ ...columns, values: "keine" }, false).values).toEqual([]);
  });

  it("draws the axes, the titles, the legend and only the main grid", () => {
    const drawn = chart(columns, false);
    expect(drawn.axes.map((a) => a.dir).sort()).toEqual(["x", "y"]);
    expect(drawn.axes.every((a) => (a.dir === "x" ? a.y1 === a.y2 : a.x1 === a.x2))).toBe(true);
    expect(drawn.titles.map((t) => t.text).sort()).toEqual(["Obst", "kg"]);
    expect(drawn.legend.map((item) => item.text)).toEqual(["A", "B", "C"]);
    expect(drawn.grid.length).toBeGreaterThan(0);
    expect(drawn.grid.every((g) => g.step === "haupt" && g.y1 === g.y2)).toBe(true);
    expect(chart({ ...columns, grid: "zwischen" }, false).grid.some((g) => g.step === "zwischen")).toBe(true);
    const none = chart({ ...columns, axes: "keine", legend: false, xTitle: "Obst", yTitle: "kg" }, false);
    expect(none.axes).toEqual([]);
    expect(none.ticks).toEqual([]);
    expect(none.titles).toEqual([]);
    expect(none.legend).toEqual([]);
    expect(none.grid.length).toBeGreaterThan(0);
  });

  it("draws bars sideways and a pie from the shares, with no axes", () => {
    const bars = chart({ ...columns, kind: "balken", grid: "zwischen" }, false);
    expect(bars.bars[1].w).toBeCloseTo(bars.bars[0].w * 2);
    expect(bars.bars[0].h).toBeCloseTo(bars.bars[2].h);
    expect(bars.grid.every((g) => g.x1 === g.x2)).toBe(true);
    expect(bars.values[0].x).toBeGreaterThan(bars.bars[0].x + bars.bars[0].w);
    const pie = chart({ ...columns, kind: "kreis", axes: "beide", grid: "haupt" }, false);
    expect(pie.axes).toEqual([]);
    expect(pie.grid).toEqual([]);
    expect(pie.bars).toEqual([]);
    expect(pie.slices.map((s) => s.sweep)).toHaveLength(3);
    expect(pie.slices[0].sweep).toBeCloseTo(Math.PI / 3);
    expect(pie.slices[1].sweep).toBeCloseTo((Math.PI * 2) / 3);
    expect(pie.slices[2].sweep).toBeCloseTo(Math.PI);
    const whole = chart(props({ kind: "kreis", points: [point("5")], legend: false, grid: "keine", axes: "keine" }), false);
    expect(whole.slices[0].sweep).toBeCloseTo(Math.PI * 2);
  });
});
