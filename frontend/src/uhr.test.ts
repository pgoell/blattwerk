// The Uhr model: the time words, the written times, the random and the own times, the sanitising of stored props.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { DEFAULTS, hands, inWords, parsed, sane, timesOf, written, type UhrProps } from "./uhr";

const P = (over: Partial<UhrProps> = {}): UhrProps => ({ ...DEFAULTS, seed: 1, ...over });
const NACH = "nach";
const VIERTEL = "viertel";

describe("inWords, 3 o'clock", () => {
  const rows: [number, string, string][] = [
    [0, "drei Uhr", "drei Uhr"],
    [5, "fünf nach drei", "fünf nach drei"],
    [10, "zehn nach drei", "zehn nach drei"],
    [15, "viertel nach drei", "viertel vier"],
    [20, "zwanzig nach drei", "zwanzig nach drei"],
    [25, "fünf vor halb vier", "fünf vor halb vier"],
    [30, "halb vier", "halb vier"],
    [35, "fünf nach halb vier", "fünf nach halb vier"],
    [40, "zwanzig vor vier", "zwanzig vor vier"],
    [45, "viertel vor vier", "dreiviertel vier"],
    [50, "zehn vor vier", "zehn vor vier"],
    [55, "fünf vor vier", "fünf vor vier"],
  ];
  for (const [m, nach, viertel] of rows) {
    it(`3:${String(m).padStart(2, "0")} reads "${nach}" nach and "${viertel}" viertel`, () => {
      expect(inWords(180 + m, NACH)).toBe(nach);
      expect(inWords(180 + m, VIERTEL)).toBe(viertel);
    });
  }
});

describe("inWords, other times", () => {
  it("12:45 reads viertel vor eins, dreiviertel eins", () => {
    expect(inWords(12 * 60 + 45, NACH)).toBe("viertel vor eins");
    expect(inWords(12 * 60 + 45, VIERTEL)).toBe("dreiviertel eins");
  });

  it("0:30 reads halb eins in both regions", () => {
    expect(inWords(30, NACH)).toBe("halb eins");
    expect(inWords(30, VIERTEL)).toBe("halb eins");
  });

  it("1:00 reads ein Uhr, not eins Uhr", () => {
    expect(inWords(60, NACH)).toBe("ein Uhr");
    expect(inWords(60, VIERTEL)).toBe("ein Uhr");
  });

  it("13:15 reads the same as 1:15", () => {
    expect(inWords(13 * 60 + 15, NACH)).toBe(inWords(75, NACH));
    expect(inWords(13 * 60 + 15, VIERTEL)).toBe(inWords(75, VIERTEL));
  });

  it("odd minutes: 3:23 reads 23 Minuten nach drei, 3:59 reads 1 Minute vor vier", () => {
    expect(inWords(3 * 60 + 23, NACH)).toBe("23 Minuten nach drei");
    expect(inWords(3 * 60 + 59, NACH)).toBe("1 Minute vor vier");
  });

  it("midnight and noon read zwölf Uhr in both regions", () => {
    for (const region of [NACH, VIERTEL] as const) {
      expect(inWords(0, region)).toBe("zwölf Uhr");
      expect(inWords(720, region)).toBe("zwölf Uhr");
    }
  });
});

describe("written", () => {
  it("format 12 gives hours 1 to 12", () => {
    expect(written(15 * 60 + 30, P({ format: "12" }))).toBe("3:30 Uhr");
    expect(written(5, P({ format: "12" }))).toBe("12:05 Uhr");
  });

  it("format 24 gives hours 0 to 23", () => {
    expect(written(15 * 60 + 30, P({ format: "24" }))).toBe("15:30 Uhr");
    expect(written(5, P({ format: "24" }))).toBe("0:05 Uhr");
  });

  it("format words gives the words of the region", () => {
    expect(written(180 + 15, P({ format: "words", region: "viertel" }))).toBe("viertel vier");
    expect(written(180 + 15, P({ format: "words", region: "nach" }))).toBe("viertel nach drei");
  });
});

describe("parsed", () => {
  it("reads h:mm", () => {
    expect(parsed("7:05")).toBe(425);
    expect(parsed("15:30")).toBe(930);
  });

  it("24:00 and text are undefined", () => {
    expect(parsed("24:00")).toBeUndefined();
    expect(parsed("abc")).toBeUndefined();
  });

  it("surrounding spaces are fine", () => {
    expect(parsed(" 9:00 ")).toBe(540);
  });
});

describe("sane", () => {
  it("never throws on any stored value, and gives props in range", () => {
    fc.assert(
      fc.property(fc.anything(), (x) => {
        const q = sane(x as UhrProps);
        expect(q.count).toBeGreaterThanOrEqual(1);
        expect(q.count).toBeLessThanOrEqual(12);
        expect(q.cols).toBeGreaterThanOrEqual(1);
        expect(q.cols).toBeLessThanOrEqual(6);
        expect([60, 30, 15, 5, 1]).toContain(q.step);
        expect(sane(q)).toEqual(q);
        for (const t of timesOf(q)) expect(Number.isInteger(t)).toBe(true);
        written(timesOf(q)[0], q);
      }),
      { numRuns: 300 },
    );
  });

  it("wrong values give the defaults", () => {
    expect(sane({ ...P(), count: 13, cols: 0, step: 7, format: "x" } as unknown as UhrProps)).toEqual({ ...DEFAULTS, seed: 1 });
  });

  it("a bad entry of times keeps the other clocks in their places", () => {
    expect(sane(P({ times: [100, "x" as unknown as number, 300] })).times).toEqual([100, -1, 300]);
  });
});

describe("timesOf", () => {
  it("gives count entries", () => {
    for (const count of [1, 4, 12]) expect(timesOf(P({ count }))).toHaveLength(count);
  });

  it("random times are multiples of step, distinct while there are enough", () => {
    fc.assert(
      fc.property(fc.integer(), fc.constantFrom(60, 30, 15, 5, 1), (seed, step) => {
        const ts = timesOf(P({ seed, step: step as UhrProps["step"], count: 12, format: "24" }));
        expect(ts.every((t) => t % step === 0 && t >= 0 && t <= 1439)).toBe(true);
        expect(new Set(ts).size).toBe(ts.length);
      }),
      { numRuns: 100 },
    );
  });

  it("the same seed gives the same times, another seed other times", () => {
    expect(timesOf(P({ seed: 7 }))).toEqual(timesOf(P({ seed: 7 })));
    expect(timesOf(P({ seed: 7 }))).not.toEqual(timesOf(P({ seed: 8 })));
  });

  it("format 12 and words keep the times in 60 to 779", () => {
    for (const format of ["12", "words"] as const) {
      fc.assert(
        fc.property(fc.integer(), (seed) => {
          for (const t of timesOf(P({ seed, format, step: 1, count: 12 }))) expect(t >= 60 && t <= 779).toBe(true);
        }),
        { numRuns: 50 },
      );
    }
  });

  it("free takes a valid times entry and ignores a bad one", () => {
    const ts = timesOf(P({ fill: "free", times: [600, 1500], count: 2, format: "24" }));
    expect(ts[0]).toBe(600);
    expect(ts[1]).toBeGreaterThanOrEqual(0);
    expect(ts[1]).toBeLessThanOrEqual(1439);
    expect(ts[1]).not.toBe(1500);
  });

  it("random ignores times", () => {
    expect(timesOf(P({ fill: "random", times: [600], count: 1, format: "24" }))).toEqual(timesOf(P({ fill: "random", count: 1, format: "24" })));
  });

  it("own times with a 60-minute step stay distinct from the random ones", () => {
    const ts = timesOf(P({ fill: "free", step: 60, format: "12", times: [60, 120], count: 4 }));
    expect(new Set(ts).size).toBe(4);
  });
});

describe("hands", () => {
  it("15:30 puts the hour hand at 105 and the minute hand at 180", () => {
    expect(hands(15 * 60 + 30)).toEqual([105, 180]);
  });
});

describe("own cases", () => {
  it("midnight and noon put the hour hand at the same place", () => {
    expect(hands(0)).toEqual(hands(720));
  });

  it("written in 12 keeps the same minute in 24 for every time of the day", () => {
    for (let t = 0; t < 1440; t += 7) {
      const twelve = written(t, P({ format: "12" })).replace(" Uhr", "").split(":")[1];
      const day = written(t, P({ format: "24" })).replace(" Uhr", "").split(":")[1];
      expect(twelve).toBe(day);
    }
  });
});
