// Which numbers a Rechentabelle draws: the rows and columns that keep the carry rule, then the cells.
import type { Made, Op, RechentabelleProps, Table } from "../rechentabelle";

export const FAMILY = [1, 2, 4, 8, 3, 6, 9, 5, 10, 7];
export const FIRST: Record<RechentabelleProps["first"], number[]> = {
  all: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  kings: [1, 2, 5, 10],
  near: [3, 4, 6, 9],
};

// What each place of a + b (op "+") or a − b (op "-") carries to the next, units first, as maths.py `carries`. A place
// beyond the list carries 0.
export function carryList(op: "+" | "-", a: number, b: number): number[] {
  const out: number[] = [];
  let carry = 0;
  while (a > 0 || b > 0) {
    carry =
      op === "+"
        ? Number((a % 10) + (b % 10) + carry > 9)
        : Number((a % 10) - carry < b % 10);
    out.push(carry);
    a = Math.floor(a / 10);
    b = Math.floor(b / 10);
  }
  return out;
}


const range = (n: number) => Array.from({ length: n }, (_, i) => i);

// A Fisher-Yates shuffle with the draws of next.
function shuffle<T>(xs: T[], next: () => number): T[] {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// A value from lo to hi that passes ok, up to 50 draws; null when none does.
function draw(
  lo: number,
  hi: number,
  next: () => number,
  ok: (v: number) => boolean,
): number | null {
  for (let k = 0; k < 50; k++) {
    const v = lo + Math.floor(next() * (hi - lo + 1));
    if (ok(v)) return v;
  }
  return null;
}

// Whether row value r and column value c fit a Plus or Minus cell under the carry rule.
function fits(
  p: RechentabelleProps,
  op: "+" | "-",
  r: number,
  c: number,
): boolean {
  if (op === "+" ? r + c > p.max : r < c) return false;
  const list = carryList(op, r, c);
  // The places the panel shows: the Zehnerübergang, and from max 1000 the Hunderterübergang. "none" at the top one
  // holds for every place above it too (so that 20 + 80 = 100 is no cell of a table without Übertrag).
  const top = p.max >= 1000 ? 2 : 1;
  const above = p.carry[top - 1] === "none" ? "none" : "either";
  // Every place the numbers reach, and the places the list does not reach carry 0 (#962).
  return range(Math.max(top, list.length)).every((k) => {
    const v = list[k] ?? 0;
    const rule = k < top ? p.carry[k] : above;
    return rule === "none" ? v === 0 : rule === "required" ? v === 1 : true;
  });
}

// One try of Plus or Minus values: the column values, then the row values that fit them all.
function additiveTry(
  p: RechentabelleProps,
  op: "+" | "-",
  next: () => number,
  distinct: boolean,
) {
  const colHi = op === "+" ? p.max - 1 : Math.floor(p.max / 2);
  const rowHi = op === "+" ? p.max - 1 : p.max;
  // The row values that still fit every column value so far: a column value is taken only when enough of them stay.
  let room = range(rowHi).map((i) => i + 1);
  const cols: number[] = [];
  for (let j = 0; j < p.cols; j++) {
    const v = draw(1, colHi, next, (x) => {
      if (distinct && cols.includes(x)) return false;
      const left = room.filter((r) => fits(p, op, r, x)).length;
      return distinct ? left >= p.rows : left > 0;
    });
    if (v === null) return null;
    cols.push(v);
    room = room.filter((r) => fits(p, op, r, v));
  }
  const rows: number[] = [];
  for (let i = 0; i < p.rows; i++) {
    const free = distinct ? room.filter((r) => !rows.includes(r)) : room;
    if (!free.length) return null;
    rows.push(free[Math.floor(next() * free.length)]);
  }
  return { cols, rows };
}

// Plus and Minus values with distinct columns and rows, every cell under the carry rule, found by a depth-first search
// over the columns in a drawn order. Null when no such set exists.
function exactValues(
  p: RechentabelleProps,
  op: "+" | "-",
  next: () => number,
): { cols: number[]; rows: number[] } | null {
  const colHi = op === "+" ? p.max - 1 : Math.floor(p.max / 2);
  const rowHi = op === "+" ? p.max - 1 : p.max;
  const fitting = new Map<number, Set<number>>();
  for (let c = 1; c <= colHi; c++) {
    const rs = new Set(
      range(rowHi)
        .map((i) => i + 1)
        .filter((r) => fits(p, op, r, c)),
    );
    if (rs.size >= p.rows) fitting.set(c, rs);
  }
  const cands = shuffle([...fitting.keys()], next);
  const cols: number[] = [];
  const search = (from: number, room: number[]): number[] | null => {
    if (cols.length === p.cols) {
      const rows: number[] = [];
      let free = room;
      for (let i = 0; i < p.rows; i++) {
        const k = Math.floor(next() * free.length);
        rows.push(free[k]);
        free = free.filter((_, j) => j !== k);
      }
      return rows;
    }
    for (let k = from; k <= cands.length - (p.cols - cols.length); k++) {
      const set = fitting.get(cands[k])!;
      const left = room.filter((r) => set.has(r));
      if (left.length < p.rows) continue;
      cols.push(cands[k]);
      const rows = search(k + 1, left);
      if (rows) return rows;
      cols.pop();
    }
    return null;
  };
  const rows = search(
    0,
    range(rowHi).map((i) => i + 1),
  );
  if (!rows) return null;
  return { cols: [...cols], rows };
}

// Plus and Minus values, the carry rule kept at every level: 200 random tries without repeats, then the exact search
// without repeats, then 200 random tries where values may repeat, then the first pair that fits, repeated. `loose`
// "distinct" when both carry rules are "either" (only the Zahlenraum is too small), else "carry".
function additiveValues(
  p: RechentabelleProps,
  op: "+" | "-",
  next: () => number,
): { cols: number[]; rows: number[]; loose: Made["loose"] } {
  for (let t = 0; t < 200; t++) {
    const got = additiveTry(p, op, next, true);
    if (got) return { ...got, loose: null };
  }
  const exact = exactValues(p, op, next);
  if (exact) return { ...exact, loose: null };
  const loose: Made["loose"] =
    p.carry[0] === "either" && p.carry[1] === "either" ? "distinct" : "carry";
  for (let t = 0; t < 200; t++) {
    const got = additiveTry(p, op, next, false);
    if (got) return { ...got, loose };
  }
  const colHi = op === "+" ? p.max - 1 : Math.floor(p.max / 2);
  const rowHi = op === "+" ? p.max - 1 : p.max;
  for (let c = 1; c <= colHi; c++)
    for (let r = 1; r <= rowHi; r++)
      if (fits(p, op, r, c))
        return {
          cols: Array(p.cols).fill(c),
          rows: Array(p.rows).fill(r),
          loose,
        };
  // Not reached: the tests show that every panel setting has a pair that fits.
  return { cols: Array(p.cols).fill(1), rows: Array(p.rows).fill(1), loose };
}

// Mal and Geteilt values: the column values from the Reihen, the row values from the Erstfaktoren; Geteilt's rows are dividends.
function multValues(
  p: RechentabelleProps,
  next: () => number,
): { cols: number[]; rows: number[] } {
  const shuffled = shuffle(p.reihen, next);
  const list =
    p.order === "related"
      ? FAMILY.filter((n) => p.reihen.includes(n))
      : shuffled;
  const cols = range(p.cols).map((j) => list[j % list.length]);
  const erst: number[] = [];
  while (erst.length < p.rows) erst.push(...shuffle(FIRST[p.first], next));
  if (p.op === "*") return { cols, rows: erst.slice(0, p.rows) };
  const rows: number[] = [];
  for (let i = 0; i < p.rows; i++) {
    let v = 0;
    for (let k = 0; k < 10; k++) {
      v = erst[i] * cols[Math.floor(next() * cols.length)];
      if (!rows.includes(v)) break;
    }
    rows.push(v);
  }
  return { cols, rows };
}

type Cell = { v: number; struck: boolean; madeUp: boolean };

// The result of one cell from its row and column values, before any typed number.
function cellOf(op: Op, r: number, c: number): Cell {
  if (op === "+") return { v: r + c, struck: false, madeUp: false };
  if (op === "-")
    return r < c
      ? { v: 0, struck: false, madeUp: true }
      : { v: r - c, struck: false, madeUp: false };
  if (op === "*") return { v: r * c, struck: false, madeUp: false };
  if (c === 0) return { v: 0, struck: false, madeUp: true };
  return r % c === 0
    ? { v: r / c, struck: false, madeUp: false }
    : { v: 0, struck: true, madeUp: false };
}

// The tables of the settings. Every draw happens before the typed numbers overlay the values.
export function tablesOf(p: RechentabelleProps, next: () => number): Made {
  const tables: Table[] = [];
  let loose: Made["loose"] = null;
  for (let t = 0; t < p.count; t++) {
    const v =
      p.op === "+" || p.op === "-"
        ? additiveValues(p, p.op, next)
        : { ...multValues(p, next), loose: null };
    if (v.loose === "distinct" || (v.loose === "carry" && loose === null))
      loose = v.loose;

    // The hidden values: a drawn order of the rows and of the columns, then one draw per row and per column.
    const rowOrder = shuffle(range(p.rows), next);
    const colOrder = shuffle(range(p.cols), next);
    const hiddenRows = rowOrder.slice(0, p.hideRows);
    const hiddenCols = colOrder.slice(0, p.hideCols);
    const rowPick = range(p.rows).map(() => next());
    const colPick = range(p.cols).map(() => next());

    // Candidates use the drawn values, so that the typed numbers cannot move a draw.
    const drawn = v.rows.map((r) => v.cols.map((c) => cellOf(p.op, r, c)));
    const can = (i: number, j: number) => p.op !== ":" || !drawn[i][j].struck;
    const rowShown = v.rows.map((_, i) => !hiddenRows.includes(i));
    const colShown = v.cols.map((_, j) => !hiddenCols.includes(j));
    const given: boolean[][] = v.rows.map(() => v.cols.map(() => false));
    for (const i of hiddenRows) {
      const cands = range(p.cols).filter((j) => colShown[j] && can(i, j));
      if (cands.length)
        given[i][cands[Math.floor(rowPick[i] * cands.length)]] = true;
      else rowShown[i] = true;
    }
    for (const j of hiddenCols) {
      const cands = range(p.rows).filter((i) => rowShown[i] && can(i, j));
      if (cands.length)
        given[cands[Math.floor(colPick[j] * cands.length)]][j] = true;
      else colShown[j] = true;
    }

    // The typed numbers overlay the values, then the cells follow them.
    const rows = [...v.rows];
    const cols = [...v.cols];
    const typed = (p.typed ?? []).filter(
      ([tt, r, c]) => tt === t && r <= p.rows && c <= p.cols,
    );
    for (const [, r, c, val] of typed) {
      if (r === 0 && c > 0) cols[c - 1] = val;
      else if (c === 0 && r > 0) rows[r - 1] = val;
    }
    const cells = rows.map((r) => cols.map((c) => cellOf(p.op, r, c)));
    const out: Table = {
      rows,
      cols,
      cells: cells.map((row) => row.map((x) => x.v)),
      struck: cells.map((row) => row.map((x) => x.struck)),
      madeUp: cells.map((row) => row.map((x) => x.madeUp)),
      given,
      rowShown,
      colShown,
      wrong:
        (p.op === "*" || p.op === ":") &&
        (rows.includes(0) || cols.includes(0)),
    };
    if (out.madeUp.some((row) => row.some(Boolean))) out.wrong = true;
    for (const [, r, c, val] of typed) {
      if (r === 0 || c === 0) continue;
      const i = r - 1;
      const j = c - 1;
      if (out.madeUp[i][j]) {
        out.wrong = true;
        continue;
      }
      if (cells[i][j].struck || val !== cells[i][j].v) out.wrong = true;
      out.cells[i][j] = val;
      out.struck[i][j] = false;
      out.given[i][j] = true;
    }
    // A given cell that typed values struck through or made up leaves its hidden value with no clue.
    if (
      out.given.some((row, i) =>
        row.some((g, j) => g && (out.struck[i][j] || out.madeUp[i][j])),
      )
    )
      out.wrong = true;
    tables.push(out);
  }
  return { tables, loose };
}
