// The numbers of her own that a teacher types into a maths block, on the sheet: a double click on a box of the block
// opens a field there. A block's view marks each such box with `data-own`, its place in the block: the copy (wall,
// house, table ...) first, then the box in it. What is typed is stored in the block's `typed`, as the block's own
// file says.
import type { Block } from "../../sheet";
import { made as madeMagic, sane as saneMagic } from "../../magischesquadrat";
import { made as madeMal, sane as saneMal } from "../../malquadrat";
import { made as madeOperator, sane as saneOperator } from "../../operatorfeld";
import { made as madePfeil, opLabel, sane as sanePfeil } from "../../pfeilbild";
import { made as madeDreieck, sane as saneDreieck } from "../../rechendreieck";
import { made as madeRad, sane as saneRad } from "../../rechenrad";
import { made as madeTabelle, sane as saneTabelle } from "../../rechentabelle";
import { made as madeHaus, sane as saneHaus } from "../../zahlenhaus";
import { made as madeKette, sane as saneKette } from "../../zahlenkette";
import { made as madeMauer, sane as saneMauer } from "../../zahlenmauer";
import { made as madeZerlegung, sane as saneZerlegung } from "../../zerlegungsfeld";

type Of<T extends Block["type"]> = Extract<Block, { type: T }>;
// What a field stores: the props that change, and the key under which the typing of one box is one undo step.
type Change = { props: object; key: string };
type Own<B extends Block> = {
  // What the field shows as it opens: the number in the box, typed or made, or nothing for a box left empty.
  read: (block: B, cell: string[]) => string;
  // What the text in the field stores. Null stores nothing: the text is not whole yet.
  write: (block: B, cell: string[], text: string) => Change | null;
  // The texts the field takes, as they are typed. Up to four digits unless said otherwise.
  takes?: RegExp;
};

const DIGITS = /^\d{0,4}$/;
const list = (raw: unknown): unknown[][] => (Array.isArray(raw) ? raw.filter((t): t is unknown[] => Array.isArray(t)) : []);
const at = (cell: number[]) => (t: unknown[]) => cell.every((v, i) => t[i] === v);

// The entries with the one for this box set to the number, or without it for an empty field. `drawn` are entries the
// block's copy gets first: the numbers it shows now, where typing one number makes the whole copy the teacher's.
function typed(block: Block, cell: number[], text: string, drawn: unknown[][] = []): Change {
  const others = [...list((block.props as { typed?: unknown }).typed), ...drawn].filter((t) => !at(cell)(t));
  const next = text === "" ? others : [...others, [...cell, Number(text)]];
  return { props: { typed: next.length ? next : undefined }, key: `typed:${cell.join(":")}` };
}
const nums = (cell: string[]) => cell.map(Number);

// The Pfeilbild's operator at an arrow, as typed: a sign, or none for plus, and a number from 1.
const OP_TEXT = /^([+\-−*x×·:/÷]?)(\d{0,4})$/;
const TYPED_OP: Record<string, string> = { "": "+", "+": "+", "-": "-", "−": "-", "*": "*", x: "*", "×": "*", "·": "*", ":": ":", "/": ":", "÷": ":" };

const OWN: { [T in Block["type"]]?: Own<Of<T>> } = {
  zahlenmauer: {
    read: (b, cell) => String(madeMauer(saneMauer(b.props)).walls[+cell[0]]?.numbers[+cell[1]] ?? ""),
    write: (b, cell, text) => typed(b, nums(cell), text),
  },
  operatorfeld: {
    read: (b, cell) => String(madeOperator(saneOperator(b.props)).fields[+cell[0]]?.numbers[+cell[1]] ?? ""),
    write: (b, cell, text) => typed(b, nums(cell), text),
  },
  zahlenkette: {
    read: (b, cell) => String(madeKette(saneKette(b.props)).chains[+cell[0]]?.numbers[+cell[1]] ?? ""),
    write: (b, cell, text) => typed(b, nums(cell), text),
  },
  rechendreieck: {
    read: (b, cell) => String(madeDreieck(saneDreieck(b.props)).triangles[+cell[0]]?.numbers[+cell[1]] ?? ""),
    write: (b, cell, text) => typed(b, nums(cell), text),
  },
  zahlenhaus: {
    read: (b, cell) => String(madeHaus(saneHaus(b.props)).houses[+cell[0]]?.numbers[+cell[1]] ?? ""),
    write: (b, cell, text) => typed(b, nums(cell), text),
  },
  rechenrad: {
    // Ring 0 is the centre, the rings count from 1.
    read: (b, [c, ring, segment]) => {
      const wheel = madeRad(saneRad(b.props)).wheels[+c];
      return String((+ring ? wheel?.rings[+ring - 1]?.[+segment] : wheel?.centre) ?? "");
    },
    write: (b, cell, text) => typed(b, nums(cell), text),
  },
  pfeilbild: {
    read: (b, cell) => {
      const pictures = madePfeil(sanePfeil(b.props)).pictures;
      if (cell[0] !== "op") return String(pictures[+cell[0]]?.numbers[+cell[1]] ?? "");
      const step = pictures[+cell[1]]?.steps[+cell[2]];
      return step ? opLabel(step) : "";
    },
    write: (b, cell, text) => {
      if (cell[0] !== "op") return typed(b, nums(cell), text);
      const [c, arrow] = [+cell[1], +cell[2]];
      const hit = OP_TEXT.exec(text)!;
      const n = Number(hit[2]);
      // A sign alone, or a 0, is no operator yet.
      if (text !== "" && n < 1) return null;
      const others = list(b.props.typedOps).filter((t) => !at([c, arrow])(t));
      const next = text === "" ? others : [...others, [c, arrow, TYPED_OP[hit[1]], n]];
      return { props: { typedOps: next.length ? next : undefined }, key: `typedOps:${c}:${arrow}` };
    },
    takes: OP_TEXT,
  },
  rechentabelle: {
    // Row 0 holds the column values and column 0 the row values. A struck or made-up cell shows nothing.
    read: (b, [c, row, col]) => {
      const p = saneTabelle(b.props);
      const [r, s] = [+row, +col];
      const own = p.typed?.find((e) => e[0] === +c && e[1] === r && e[2] === s)?.[3];
      if (own !== undefined) return String(own);
      const table = madeTabelle(p).tables?.[+c];
      if (!table) return "";
      if (r === 0) return String(table.cols[s - 1] ?? "");
      if (s === 0) return String(table.rows[r - 1] ?? "");
      if (table.struck[r - 1]?.[s - 1] || table.madeUp[r - 1]?.[s - 1]) return "";
      return String(table.cells[r - 1]?.[s - 1] ?? "");
    },
    write: (b, cell, text) => typed(b, nums(cell), text),
  },
  malquadrat: {
    read: (b, [c, i, j]) => {
      const square = madeMal(saneMal(b.props)).squares[+c];
      return square?.given[+i]?.[+j] ? String(square.cells[+i][+j]) : "";
    },
    // The first number typed into a square makes the square the teacher's: the numbers it shows are stored with it.
    write: (b, cell, text) => {
      const p = saneMal(b.props);
      const c = +cell[0];
      const n = p.size;
      const inside = (i: number, j: number) => i >= 0 && j >= 0 && i <= n + 1 && j <= n + 1 && !((i === 0 && j === 0) || (i === 0 && j === n + 1) || (i === n + 1 && j === 0));
      const square = madeMal(p).squares[c];
      const mine = (p.typed ?? []).some((e) => e[0] === c && inside(e[1], e[2]));
      const drawn: unknown[][] = [];
      if (!mine && square) square.given.forEach((row, r) => row.forEach((given, s) => given && inside(r, s) && drawn.push([c, r, s, square.cells[r][s]])));
      return typed(b, nums(cell), text, drawn);
    },
  },
  magischesquadrat: {
    // Rows and columns count from 1.
    read: (b, [c, r, s]) => {
      const square = madeMagic(saneMagic(b.props)).squares[+c];
      return square?.given[+r - 1]?.[+s - 1] ? String(square.cells[+r - 1][+s - 1]) : "";
    },
    write: (b, cell, text) => {
      const p = saneMagic(b.props);
      const c = +cell[0];
      const square = madeMagic(p).squares[c];
      const mine = (p.typed ?? []).some((e) => e[0] === c && e[1] <= p.size && e[2] <= p.size);
      const drawn: unknown[][] = [];
      if (!mine && square) square.given.forEach((row, i) => row.forEach((given, j) => given && drawn.push([c, i + 1, j + 1, square.cells[i][j]])));
      return typed(b, nums(cell), text, drawn);
    },
  },
  zerlegungsfeld: {
    read: (b, [c, pos]) => {
      const task = madeZerlegung(saneZerlegung(b.props)).tasks[+c];
      return task?.given[+pos] ? String(task.values[+pos]) : "";
    },
    write: (b, cell, text) => {
      const p = saneZerlegung(b.props);
      const c = +cell[0];
      const task = madeZerlegung(p).tasks[c];
      const mine = (p.typed ?? []).some((e) => e[0] === c);
      const drawn: unknown[][] = [];
      if (!mine && task) task.given.forEach((given, q) => given && drawn.push([c, q, task.values[q]]));
      return typed(b, nums(cell), text, drawn);
    },
  },
};

// The block's way with its own numbers, if it takes any on the sheet.
export function ownOf(block: Block) {
  const own = OWN[block.type] as Own<Block> | undefined;
  return own && { read: (cell: string[]) => own.read(block, cell), write: (cell: string[], text: string) => own.write(block, cell, text), takes: own.takes ?? DIGITS };
}
