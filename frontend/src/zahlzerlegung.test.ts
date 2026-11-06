// The Zahlzerlegung generator, checked by an oracle of plain loops that takes nothing from the generator's candidate
// list: every drawn task fits the rule, a typed number fits or gives a wrong task as the oracle says, and every line
// reads as a true equation once its gaps are filled in.
import { describe, expect, it } from "vitest";
import { items, made, placesOf, sane, type Item, type Task, type ZahlzerlegungProps } from "./zahlzerlegung";

const TYPE_NAMES = ["split", "join", "shuffled", "places", "gap", "zero", "bundle"] as const;
const MAXES = [100, 1000, 10000];
// The oracle's own table: place values and letters, highest place first.
const PV: Record<number, number[]> = { 100: [10, 1], 1000: [100, 10, 1], 10000: [1000, 100, 10, 1] };
const LETTERS: Record<number, string[]> = { 100: ["Z", "E"], 1000: ["H", "Z", "E"], 10000: ["T", "H", "Z", "E"] };
const LETTER_VALUE: Record<string, number> = { T: 1000, H: 100, Z: 10, E: 1 };

// A fixed Park-Miller generator, for the typed numbers.
function lcg(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 48271) % 2147483647;
    return s / 2147483647;
  };
}

// The numbers the oracle accepts for a Zahlenraum and a type: plain loops, nested over the counts for "bundle".
function oracleSet(max: number, type: string): Set<number> {
  const vs = PV[max];
  const k = vs.length;
  const out = new Set<number>();
  if (type === "bundle") {
    const add = (c: number[]) => {
      let n = 0;
      for (let j = 0; j < k; j++) n += c[j] * vs[j];
      if (n < max) out.add(n);
    };
    for (let a = 1; a <= 9; a++) {
      if (k === 2) {
        for (let b = 0; b <= 19; b++) if (b >= 10) add([a, b]);
      } else if (k === 3) {
        for (let b = 0; b <= 19; b++)
          for (let c = 0; c <= 19; c++) if ((b >= 10 ? 1 : 0) + (c >= 10 ? 1 : 0) === 1) add([a, b, c]);
      } else {
        for (let b = 0; b <= 19; b++)
          for (let c = 0; c <= 19; c++)
            for (let d = 0; d <= 19; d++) if ((b >= 10 ? 1 : 0) + (c >= 10 ? 1 : 0) + (d >= 10 ? 1 : 0) === 1) add([a, b, c, d]);
      }
    }
  } else {
    for (let n = 10 ** (k - 1); n < max; n++) {
      const d = vs.map((v) => Math.floor(n / v) % 10);
      let ok: boolean;
      if (type === "places") ok = true;
      else if (type === "zero") ok = d.slice(1).includes(0);
      else ok = d.every((x) => x > 0);
      if (ok) out.add(n);
    }
  }
  return out;
}

// The sum of one side of a line, read by the test's own tokenizer: a number, or a count and a letter (3 H = 300).
function sideValue(side: string): number {
  const toks = side.split(" ");
  let sum = 0;
  for (let i = 0; i < toks.length; i++) {
    const tk = toks[i];
    if (tk === "+") continue;
    if (!/^\d+$/.test(tk)) return NaN;
    const num = Number(tk);
    if (i + 1 < toks.length && LETTER_VALUE[toks[i + 1]] !== undefined) {
      sum += num * LETTER_VALUE[toks[i + 1]];
      i++;
    } else {
      sum += num;
    }
  }
  return sum;
}

const isDesc = (xs: number[]) => xs.every((x, j) => j === 0 || xs[j - 1] > x);
const isAsc = (xs: number[]) => xs.every((x, j) => j === 0 || xs[j - 1] < x);

// The problems with a drawn (non-wrong) task: its line as the key reads it, and the rule of its type.
function checkLine(max: number, type: string, i: number, t: Task, its: Item[]): string[] {
  const errs: string[] = [];
  const vs = PV[max];
  const k = vs.length;
  const letters = LETTERS[max];
  const n = t.n;
  const d = vs.map((v) => Math.floor(n / v) % 10);
  if (String(n).length !== k || n >= max) errs.push(`n ${n} is not ${k} digits under ${max}`);
  if (its.some((it) => it.kind === "gap" && it.text === "")) errs.push("an empty gap");

  const cells: string[] = [];
  for (const it of its) {
    if (it.kind === "letter") cells[cells.length - 1] += " " + it.text;
    else cells.push(it.text);
  }
  const sides = cells.join(" ").split(" = ");
  if (sides.length !== 2) errs.push(`no single "=" in ${cells.join(" ")}`);
  else {
    const lhs = sideValue(sides[0]);
    const rhs = sideValue(sides[1]);
    if (!(lhs === rhs && lhs === n)) errs.push(`line ${cells.join(" ")} does not read as ${n}`);
  }

  const gaps = its.filter((it) => it.kind === "gap");
  const givens = its.filter((it) => it.kind === "given");
  const letterTexts = its.filter((it) => it.kind === "letter").map((it) => it.text);
  const eq = its.findIndex((it) => it.kind === "sign" && it.text === "=");
  const before = its.slice(0, eq).filter((it) => it.kind === "given" || it.kind === "gap");
  // A part is a single place value d·10^j with d 1 to 9; the parts must each take their own place.
  const checkParts = (parts: string[]) => {
    const pw = parts.map((s) => (/^[1-9]0*$/.test(s) ? s.length - 1 : -1));
    if (pw.some((x) => x < 0 || x >= k) || new Set(pw).size !== parts.length || parts.length !== k)
      errs.push(`parts ${parts.join(",")} are not one per place`);
  };

  switch (type) {
    case "split": {
      // A gap per place whatever the digit: each part is its place's value, 0 for a 0 place (306 = 300 + 0 + 6).
      const parts = gaps.map((g) => g.text);
      if (gaps.length !== k || givens.length !== 1) errs.push("split: gap count");
      if (parts.join() !== d.map((x, j) => String(x * vs[j])).join()) errs.push(`split: parts ${parts.join(",")}`);
      if (parts.some((s) => !/^(0|[1-9]0*)$/.test(s))) errs.push(`split: a part ${parts.join(",")} is no place value`);
      break;
    }
    case "join": {
      const parts = givens.map((g) => g.text);
      if (givens.length !== k || gaps.length !== 1) errs.push("join: shape");
      checkParts(parts);
      if (!isDesc(parts.map(Number))) errs.push("join: parts not in place order");
      break;
    }
    case "shuffled": {
      const parts = givens.map((g) => g.text);
      if (givens.length !== k || gaps.length !== 1) errs.push("shuffled: shape");
      checkParts(parts);
      if (isDesc(parts.map(Number))) errs.push("shuffled: parts in place order");
      break;
    }
    case "gap": {
      const parts = before.map((it) => it.text);
      if (givens.length !== k || gaps.length !== 1) errs.push("gap: shape");
      checkParts(parts);
      if (!isDesc(parts.map(Number))) errs.push("gap: parts not in place order");
      break;
    }
    case "places": {
      const idx = letterTexts.map((l) => letters.indexOf(l));
      const want = d.map((x, j) => (x > 0 ? j : -1)).filter((j) => j >= 0);
      if ([...idx].sort((a, b) => a - b).join() !== want.join()) errs.push("places: shown places are not the digits above 0");
      if (givens.length !== idx.length || !idx.every((j, q) => givens[q].text === String(d[j]) && /^[1-9]$/.test(givens[q].text)))
        errs.push("places: counts");
      if (gaps.length !== 1) errs.push("places: gap count");
      if (i % 2 === 0 && !isAsc(idx)) errs.push("places: even task out of place order");
      if (i % 2 === 1 && idx.length >= 2 && isAsc(idx)) errs.push("places: odd task in place order");
      break;
    }
    case "zero": {
      if (gaps.length !== k || givens.length !== 1) errs.push("zero: gap count");
      if (gaps.map((g) => g.text).join() !== d.map(String).join()) errs.push("zero: digits");
      if (!d.slice(1).includes(0)) errs.push("zero: no 0 in a place");
      if (letterTexts.join() !== letters.join()) errs.push("zero: letters");
      break;
    }
    case "bundle": {
      const c = givens.map((g) => Number(g.text));
      if (givens.length !== k || gaps.length !== 1) errs.push("bundle: shape");
      if (!(c[0] >= 1 && c[0] <= 9)) errs.push("bundle: first count");
      if (c.slice(1).some((x) => x < 0 || x > 19) || c.slice(1).filter((x) => x >= 10).length !== 1)
        errs.push("bundle: other counts");
      if (letterTexts.join() !== letters.join()) errs.push("bundle: letters");
      break;
    }
    default:
      if (letterTexts.length !== 0 || gaps.length !== 1) errs.push("shape");
  }
  if (["split", "join", "shuffled", "gap"].includes(type) && letterTexts.length !== 0) errs.push("letters in a part type");
  return errs;
}

// The problems with a wrong task: no number shows, every gap is empty, the order is the place order.
function checkWrong(k: number, t: Task, its: Item[]): string[] {
  const errs: string[] = [];
  if (t.n !== 0 || !t.wrong || t.digits.some((x) => x !== 0) || t.counts.some((x) => x !== 0)) errs.push("wrong: values");
  if (t.gap !== -1 || t.order.join() !== [...Array(k).keys()].join()) errs.push("wrong: order or gap");
  if (its.some((it) => it.kind === "given")) errs.push("wrong: a given number");
  if (its.some((it) => it.kind === "gap" && it.text !== "")) errs.push("wrong: a gap with text");
  return errs;
}

describe("drawn tasks", () => {
  it("every Zahlenraum, type and seed: the drawn tasks are oracle numbers and read as the rule says", () => {
    const bad: string[] = [];
    let drawn = 0;
    let wrong = 0;
    for (const max of MAXES)
      for (const type of TYPE_NAMES) {
        const set = oracleSet(max, type);
        const k = PV[max].length;
        for (const seed of [1, 2, 3, 4]) {
          const p: ZahlzerlegungProps = { count: 12, columns: 3, max, task: type, seed };
          const label = `${max} ${type} seed ${seed}`;
          const widths = new Set<number>();
          made(p).tasks.forEach((t, i) => {
            const its = items(p, t);
            if (t.wrong) {
              wrong++;
              bad.push(`${label} task ${i}: wrong`);
              bad.push(...checkWrong(k, t, its).map((e) => `${label} task ${i}: ${e}`));
              return;
            }
            drawn++;
            if (!set.has(t.n)) bad.push(`${label} task ${i}: ${t.n} not in the oracle`);
            bad.push(...checkLine(max, type, i, t, its).map((e) => `${label} task ${i}: ${e}`));
            for (const it of its) if (it.kind === "gap") widths.add(it.w);
          });
          if (widths.size > 1) bad.push(`${label}: gap widths ${[...widths]}`);
        }
      }
    expect(drawn).toBeGreaterThan(0);
    expect({ wrong, falseKeys: bad.length }).toEqual({ wrong: 0, falseKeys: 0 });
    expect(bad.slice(0, 5)).toEqual([]);
  });
});

describe("typed numbers", () => {
  it("every Zahlenraum and type: a typed task fits or is wrong as the oracle says, the other tasks stay as drawn", () => {
    const rnd = lcg(4242);
    const bad: string[] = [];
    let fits = 0;
    let misses = 0;
    for (const max of MAXES)
      for (const type of TYPE_NAMES) {
        const k = PV[max].length;
        // A typed "split" number fits with any k digits, a 0 place too; the drawn ones never have a 0.
        const set = type === "split" ? new Set<number>() : oracleSet(max, type);
        if (type === "split") for (let n = 10 ** (k - 1); n < max; n++) set.add(n);
        for (let r = 0; r < 300; r++) {
          const i = Math.floor(rnd() * 12);
          // Half of them in the Zahlenraum's k digits, so that bis 100 gets its share of numbers that fit.
          const lo = 10 ** (k - 1);
          const v = rnd() < 0.5 ? Math.floor(rnd() * 10000) : lo + Math.floor(rnd() * (max - lo));
          const base: ZahlzerlegungProps = { count: 12, columns: 3, max, task: type, seed: 1 + (r % 3) };
          const typed: ZahlzerlegungProps = { ...base, typed: [[i, v]] };
          const withTyped = made(typed);
          const plain = made(base);
          const label = `${max} ${type} typed ${v} on ${i} seed ${base.seed}`;
          withTyped.tasks.forEach((t, j) => {
            if (j !== i) {
              if (JSON.stringify(t) !== JSON.stringify(plain.tasks[j])) bad.push(`${label}: task ${j} changed`);
              return;
            }
            const its = items(typed, t);
            if (!set.has(v)) {
              misses++;
              bad.push(...(t.wrong ? [] : [`${label}: should be wrong`]));
              bad.push(...checkWrong(k, t, its).map((e) => `${label}: ${e}`));
              return;
            }
            fits++;
            if (t.wrong || t.n !== v) bad.push(`${label}: n ${t.n}`);
            bad.push(...checkLine(max, type, i, t, its).map((e) => `${label}: ${e}`));
          });
        }
      }
    expect(fits).toBeGreaterThan(0);
    expect(misses).toBeGreaterThan(0);
    expect(bad.slice(0, 5)).toEqual([]);
    expect(bad.length).toBe(0);
  });
});

describe("a typed split number with a 0 place", () => {
  it("306 keeps three gaps and the key writes 300, 0, 6; 3065 bis 1000 does not fit", () => {
    const p: ZahlzerlegungProps = { count: 2, columns: 2, max: 1000, task: "split", seed: 3, typed: [[0, 306], [1, 3065]] };
    const [t, w] = made(p).tasks;
    expect(items(p, t).filter((it) => it.kind === "gap").map((it) => it.text)).toEqual(["300", "0", "6"]);
    expect(w.wrong).toBe(true);
  });
});

describe("determinism", () => {
  it("the same props give the same tasks and lines", () => {
    const p: ZahlzerlegungProps = { count: 12, columns: 3, max: 10000, task: "places", seed: 7, typed: [[2, 3065]] };
    const copy: ZahlzerlegungProps = JSON.parse(JSON.stringify(p));
    expect(made(copy)).toEqual(made(p));
    expect(made(p).tasks.map((t) => items(p, t))).toEqual(made(copy).tasks.map((t) => items(copy, t)));
    expect(placesOf(sane(p)).length).toBe(4);
  });
});
