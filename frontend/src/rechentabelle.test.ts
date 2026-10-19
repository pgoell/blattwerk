// The Rechentabelle generator: the cells follow their operator, the given flags follow the hidden values, and the typed numbers come out right.
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import {
  carries,
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
      carry: "either",
      tint: "none",
      seed: 0,
    });
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

  it("Plus: every value and cell from 1 to max, every cell is row plus column, the carry rule holds", () => {
    fc.assert(
      fc.property(
        seeds,
        fc.constantFrom("none", "required", "either"),
        (seed, carry) => {
          const max = 100;
          const m = made(
            P({
              seed,
              max,
              carry: carry as RechentabelleProps["carry"],
              count: 2,
            }),
          );
          expect(m.loose).toBeNull();
          for (const t of m.tables) {
            t.rows.forEach((r, i) =>
              t.cols.forEach((c, j) => {
                expect(t.cells[i][j]).toBe(r + c);
                expect(t.cells[i][j]).toBeLessThanOrEqual(max);
                if (carry === "none") expect(carries("+", r, c)).toBe(false);
                if (carry === "required") expect(carries("+", r, c)).toBe(true);
              }),
            );
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("Minus: every value from 1 to max, every cell is row minus column and 0 or more, the carry rule holds", () => {
    fc.assert(
      fc.property(
        seeds,
        fc.constantFrom("none", "required", "either"),
        (seed, carry) => {
          for (const t of made(
            P({
              seed,
              op: "-",
              max: 100,
              carry: carry as RechentabelleProps["carry"],
              count: 2,
              rows: 6,
              cols: 6,
            }),
          ).tables) {
            t.rows.forEach((r, i) =>
              t.cols.forEach((c, j) => {
                expect(t.cells[i][j]).toBe(r - c);
                expect(t.cells[i][j]).toBeGreaterThanOrEqual(0);
                expect(t.wrong).toBe(false);
                if (carry === "none") expect(carries("-", r, c)).toBe(false);
                if (carry === "required") expect(carries("-", r, c)).toBe(true);
              }),
            );
          }
        },
      ),
      { numRuns: 100 },
    );
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
