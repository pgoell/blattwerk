// The Rechentabelle generator: the cells follow their operator, the given flags follow the hidden values, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import {
  carryList,
  DEFAULTS,
  FAMILY,
  FIRST,
  made,
  sane,
  type RechentabelleProps,
} from "./rechentabelle";

const P = (over: Partial<RechentabelleProps> = {}): RechentabelleProps => ({
  ...DEFAULTS,
  seed: 1,
  ...over,
});

const seeds = fc.integer({ min: 0, max: 1_000_000 });

describe("the Rechentabellen of a block", () => {
  it("sane of odd props gives the defaults, and drops a junk tint and too many hidden values", () => {
    const s = sane({
      count: 9,
      columns: 0,
      rows: 1,
      cols: 11,
      op: "/",
      max: 50,
      carry: "x",
      reihen: [],
      order: "x",
      first: "x",
      tint: "constructor",
      seed: NaN,
      typed: "no",
    } as unknown as RechentabelleProps);
    expect(s).toMatchObject({
      count: 2,
      columns: 2,
      rows: 4,
      cols: 4,
      op: "+",
      max: 20,
      carry: ["either", "either"],
      tint: "none",
      seed: 0,
    });
    expect(sane(P({ max: 100, carry: ["none", "required"] })).carry).toEqual([
      "none",
      "either",
    ]);
    expect(sane(P({ max: 1000, carry: ["none", "required"] })).carry).toEqual([
      "none",
      "required",
    ]);
    expect(
      sane(P({ carry: "none" as unknown as RechentabelleProps["carry"] }))
        .carry,
    ).toEqual(["either", "either"]);
    expect(s.reihen).toEqual(DEFAULTS.reihen);
    expect(s).not.toHaveProperty("typed");
    expect(sane(P({ rows: 3, hideRows: 5 })).hideRows).toBe(2);
  });

  it("the same props give the same tables, another seed other tables", () => {
    expect(made(P({ seed: 42, max: 100 }))).toEqual(
      made(P({ seed: 42, max: 100 })),
    );
    expect(made(P({ seed: 1, max: 100 })).tables).not.toEqual(
      made(P({ seed: 2, max: 100 })).tables,
    );
  });

  it("Plus: every value and cell from 1 to max, every cell is row plus column", () => {
    fc.assert(
      fc.property(seeds, fc.constantFrom(10, 20, 100, 1000), (seed, max) => {
        for (const t of made(P({ seed, max, count: 2, rows: 6, cols: 6 }))
          .tables) {
          t.rows.forEach((r, i) =>
            t.cols.forEach((c, j) => {
              expect(t.cells[i][j]).toBe(r + c);
              expect(t.cells[i][j]).toBeLessThanOrEqual(max);
            }),
          );
        }
      }),
      { numRuns: 100 },
    );
  });

  it("Minus: every value from 1 to max, every cell is row minus column and 0 or more", () => {
    fc.assert(
      fc.property(seeds, fc.constantFrom(10, 20, 100, 1000), (seed, max) => {
        for (const t of made(
          P({ seed, op: "-", max, count: 2, rows: 6, cols: 6 }),
        ).tables) {
          expect(t.wrong).toBe(false);
          t.rows.forEach((r, i) =>
            t.cols.forEach((c, j) => {
              expect(t.cells[i][j]).toBe(r - c);
              expect(t.cells[i][j]).toBeGreaterThanOrEqual(0);
            }),
          );
        }
      }),
      { numRuns: 100 },
    );
  });

  it("the Übertrag per place: every cell carries what the rule says, for Plus and Minus at max 100 and 1000", () => {
    const cases: [RechentabelleProps["carry"], number[]][] = [
      [
        ["required", "none"],
        [1, 0],
      ],
      [
        ["none", "required"],
        [0, 1],
      ],
    ];
    fc.assert(
      fc.property(
        seeds,
        fc.constantFrom(100, 1000),
        fc.constantFrom(0, 1),
        fc.constantFrom("+", "-") as fc.Arbitrary<"+" | "-">,
        (seed, max, which, op) => {
          // A carry into the Hunderter needs a Hunderter: with max 100 no table can hold that rule.
          if (max === 100 && which === 1) return;
          const [carry, [k0, k1]] = cases[which];
          const m = made(
            P({ seed, op, max, carry, count: 2, rows: 4, cols: 4 }),
          );
          expect(m.loose).toBeNull();
          for (const t of m.tables) {
            t.rows.forEach((r, i) =>
              t.cols.forEach((c, j) => {
                const list = carryList(op, r, c);
                expect(list[0] ?? 0).toBe(k0);
                // Below max 1000 the Hunderterübergang is "either".
                if (max === 1000) expect(list[1] ?? 0).toBe(k1);
              }),
            );
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("carryList matches maths.py on hand cases", () => {
    expect(carryList("+", 47, 38)).toEqual([1, 0]);
    expect(carryList("-", 52, 27)).toEqual([1, 0]);
    expect(carryList("-", 305, 127)).toEqual([1, 1, 0]);
    expect(carryList("+", 5, 4)).toEqual([0]);
  });

  it("Ohne at the top place rules out the places above: no 20 + 80 = 100 bis 100, no 100 + 900 = 1000 bis 1000 (review of #930)", () => {
    for (const [max, carry] of [
      [100, ["none", "either"]],
      [1000, ["either", "none"]],
    ] as [number, RechentabelleProps["carry"]][])
      for (const op of ["+", "-"] as const)
        for (let seed = 0; seed < 60; seed++)
          for (const t of made(P({ seed, op, max, carry, rows: 6, cols: 6 }))
            .tables)
            t.rows.forEach((r, i) =>
              t.cols.forEach((c) => {
                const list = carryList(op, r, c);
                const top = max === 1000 ? 1 : 0;
                expect(
                  list.slice(top).every((v) => v === 0),
                  `${op} ${r} ${c} seed ${seed}`,
                ).toBe(true);
                void i;
              }),
            );
  });

  it("a given clue cell that a typed value strikes through marks the table wrong (review of #930)", () => {
    const m = made(
      P({ op: ":", count: 1, hideRows: 1, seed: 1, typed: [[0, 0, 1, 7]] }),
    );
    const t = m.tables[0];
    const clueStruck = t.given.some((row, i) =>
      row.some((g, j) => g && t.struck[i][j]),
    );
    expect(clueStruck).toBe(true);
    expect(t.wrong).toBe(true);
  });

  it("Mal: every cell is row times column, the columns are the Reihen in FAMILY order with related", () => {
    const [t] = made(
      P({
        op: "*",
        reihen: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        cols: 10,
        rows: 4,
        count: 1,
      }),
    ).tables;
    expect(t.cols).toEqual(FAMILY);
    t.rows.forEach((r, i) =>
      t.cols.forEach((c, j) => expect(t.cells[i][j]).toBe(r * c)),
    );
    expect(t.wrong).toBe(false);
  });

  it("Mal with kings or near only draws the rows from those Erstfaktoren", () => {
    fc.assert(
      fc.property(
        seeds,
        fc.constantFrom("kings", "near") as fc.Arbitrary<"kings" | "near">,
        (seed, first) => {
          for (const t of made(P({ seed, op: "*", first, rows: 4, count: 2 }))
            .tables) {
            for (const r of t.rows) expect(FIRST[first]).toContain(r);
          }
        },
      ),
      { numRuns: 50 },
    );
  });

  it("Geteilt: a cell is struck exactly where row % col is not 0, and each row has a whole cell", () => {
    fc.assert(
      fc.property(
        seeds,
        fc.constantFrom("all", "kings", "near") as fc.Arbitrary<
          "all" | "kings" | "near"
        >,
        (seed, first) => {
          for (const t of made(
            P({ seed, op: ":", first, rows: 6, cols: 6, count: 2 }),
          ).tables) {
            expect(t.wrong).toBe(false);
            t.rows.forEach((r, i) => {
              t.cols.forEach((c, j) => {
                expect(t.struck[i][j]).toBe(r % c !== 0);
                if (!t.struck[i][j]) expect(t.cells[i][j]).toBe(r / c);
              });
              expect(t.struck[i].some((s) => !s)).toBe(true);
            });
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("hidden: the right counts, each hidden row a given cell in a shown column, each hidden column one in a shown row", () => {
    fc.assert(
      fc.property(
        seeds,
        fc.constantFrom("+", "-", "*", ":") as fc.Arbitrary<
          "+" | "-" | "*" | ":"
        >,
        fc.integer({ min: 0, max: 2 }),
        fc.integer({ min: 0, max: 2 }),
        (seed, op, hideRows, hideCols) => {
          for (const t of made(
            P({
              seed,
              op,
              max: 100,
              rows: 6,
              cols: 6,
              hideRows,
              hideCols,
              count: 2,
            }),
          ).tables) {
            // Geteilt: a hidden value with no whole cell in a shown line shows after all.
            const hidden = (shown: boolean[]) => shown.filter((s) => !s).length;
            if (op === ":") {
              expect(hidden(t.rowShown)).toBeLessThanOrEqual(hideRows);
              expect(hidden(t.colShown)).toBeLessThanOrEqual(hideCols);
            } else {
              expect(hidden(t.rowShown)).toBe(hideRows);
              expect(hidden(t.colShown)).toBe(hideCols);
            }
            t.rowShown.forEach((shown, i) => {
              if (!shown)
                expect(
                  t.cols.some((_, j) => t.colShown[j] && t.given[i][j]),
                ).toBe(true);
            });
            t.colShown.forEach((shown, j) => {
              if (!shown)
                expect(
                  t.rows.some((_, i) => t.rowShown[i] && t.given[i][j]),
                ).toBe(true);
            });
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("a typed column value changes that column, the other tables stay", () => {
    const base = made(P({ seed: 7, count: 2, max: 100 }));
    const typed = made(
      P({ seed: 7, count: 2, max: 100, typed: [[0, 0, 1, 77]] }),
    );
    expect(typed.tables[0].cols[0]).toBe(77);
    expect(typed.tables[0].cells.map((row) => row[0])).toEqual(
      typed.tables[0].rows.map((r) => r + 77),
    );
    expect(typed.tables[1]).toEqual(base.tables[1]);
  });

  it("a typed cell that differs from its row and column is wrong, and keeps its typed value", () => {
    const base = made(P({ seed: 8, count: 1, max: 100 })).tables[0];
    const v = base.cells[1][2];
    const t = made(
      P({ seed: 8, count: 1, max: 100, typed: [[0, 2, 3, v + 1]] }),
    ).tables[0];
    expect(t.wrong).toBe(true);
    expect(t.cells[1][2]).toBe(v + 1);
    expect(t.given[1][2]).toBe(true);
    const same = made(P({ seed: 8, count: 1, max: 100, typed: [[0, 2, 3, v]] }))
      .tables[0];
    expect(same.wrong).toBe(false);
  });

  it("a Geteilt column value 0 is wrong, and no cell is NaN or Infinity", () => {
    for (let seed = 0; seed < 20; seed++) {
      const t = made(P({ seed, count: 1, op: ":", typed: [[0, 0, 1, 0]] }))
        .tables[0];
      expect(t.wrong).toBe(true);
      t.rows.forEach((_, i) =>
        t.cols.forEach((__, j) =>
          expect(Number.isFinite(t.cells[i][j])).toBe(true),
        ),
      );
      expect(t.madeUp.every((row) => row[0])).toBe(true);
    }
  });

  it("a Minus cell below 0 is made up and the table is wrong", () => {
    const t = made(P({ seed: 3, count: 1, op: "-", typed: [[0, 1, 0, 1]] }))
      .tables[0];
    expect(t.wrong).toBe(true);
    t.rows.forEach((_, i) =>
      t.cols.forEach((__, j) =>
        expect(Number.isFinite(t.cells[i][j])).toBe(true),
      ),
    );
  });

  it("a small Zahlenraum gives the loose level distinct and still valid Plus cells", () => {
    const m = made(
      P({ seed: 5, count: 2, max: 10, rows: 10, cols: 10, op: "+" }),
    );
    expect(m.loose).toBe("distinct");
    for (const t of m.tables)
      t.rows.forEach((r, i) =>
        t.cols.forEach((c, j) => expect(t.cells[i][j]).toBe(r + c)),
      );
  });
});
