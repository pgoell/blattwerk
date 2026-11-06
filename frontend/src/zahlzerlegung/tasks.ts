// The candidates that keep a Zahlzerlegung's rule, the drawn tasks, and each task's line of items.
import { rng } from "../zahlenmauer";
import { layout, placesOf, sane } from "./props";
import type { Item, Made, Task, ZahlzerlegungProps } from "./props";

const digitsOf = (n: number, vs: number[]): number[] => vs.map((v) => Math.floor(n / v) % 10);
const valueOf = (counts: number[], vs: number[]): number => counts.reduce((s, c, j) => s + c * vs[j], 0);

// The candidates: numbers n for every type but "bundle", count tuples for "bundle", by plain loops in rising order.
const candMemo = new Map<string, number[] | number[][]>();

function candidates(p: ZahlzerlegungProps): number[] | number[][] {
  const key = JSON.stringify([p.max, p.task]);
  const old = candMemo.get(key);
  if (old) return old;
  const vs = placesOf(p).map((pl) => pl.v);
  let out: number[] | number[][];
  if (p.task === "bundle") {
    const tuples: number[][] = [];
    const counts: number[] = [];
    const walk = (j: number, tens: number) => {
      if (j === vs.length) {
        if (tens === 1 && valueOf(counts, vs) < p.max) tuples.push([...counts]);
        return;
      }
      for (let c = j === 0 ? 1 : 0; c <= (j === 0 ? 9 : 19); c++) {
        const t = tens + (c >= 10 ? 1 : 0);
        if (t > 1) break;
        counts[j] = c;
        walk(j + 1, t);
      }
    };
    walk(0, 0);
    out = tuples;
  } else {
    const nums: number[] = [];
    for (let n = 10 ** (vs.length - 1); n < p.max; n++) {
      const d = digitsOf(n, vs);
      const ok = p.task === "places" || (p.task === "zero" ? d.slice(1).includes(0) : d.every((x) => x > 0));
      if (ok) nums.push(n);
    }
    out = nums;
  }
  candMemo.set(key, out);
  return out;
}

// Every order of m places, in lexicographic order of their indices (index 0 the place order).
function perms(m: number): number[][] {
  const out: number[][] = [];
  const cur: number[] = [];
  const used = new Array<boolean>(m).fill(false);
  const walk = () => {
    if (cur.length === m) {
      out.push([...cur]);
      return;
    }
    for (let j = 0; j < m; j++) {
      if (used[j]) continue;
      used[j] = true;
      cur.push(j);
      walk();
      cur.pop();
      used[j] = false;
    }
  };
  walk();
  return out;
}

// One drawn or typed task: its digits, counts, shown places in their order, and the gap of "gap".
function build(p: ZahlzerlegungProps, vs: number[], n: number, counts: number[], i: number, r: number, g: number): Task {
  const digits = digitsOf(n, vs);
  const shown: number[] = [];
  for (let j = 0; j < vs.length; j++) if (p.task !== "places" || digits[j] > 0) shown.push(j);
  let order = shown;
  if ((p.task === "shuffled" || (p.task === "places" && i % 2 === 1)) && shown.length >= 2) {
    const all = perms(shown.length);
    order = all[1 + Math.floor(r * (all.length - 1))].map((j) => shown[j]);
  }
  return {
    n,
    digits,
    counts: p.task === "bundle" ? counts : digits,
    order,
    gap: p.task === "gap" ? Math.floor(g * vs.length) : -1,
    wrong: false,
  };
}

function wrongTask(k: number): Task {
  const zeros = new Array<number>(k).fill(0);
  return { n: 0, digits: zeros, counts: zeros, order: zeros.map((_, j) => j), gap: -1, wrong: true };
}

const madeMemo = new Map<string, Made>();

export function made(props: ZahlzerlegungProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = madeMemo.get(key);
  if (old) return old;
  const vs = placesOf(p).map((pl) => pl.v);
  const bundle = p.task === "bundle";
  const P = candidates(p);
  const next = rng(p.seed);
  const seen = new Set<number>();
  const tasks: Task[] = [];
  for (let i = 0; i < p.count; i++) {
    let n = 0;
    let counts: number[] = [];
    for (let t = 0; t < 20; t++) {
      if (bundle) {
        counts = (P as number[][])[Math.floor(next() * P.length)];
        n = valueOf(counts, vs);
      } else {
        n = (P as number[])[Math.floor(next() * P.length)];
      }
      if (!seen.has(n)) break;
    }
    seen.add(n);
    const r = next();
    const g = next();
    const mine = p.typed?.find(([j]) => j === i);
    if (!mine) {
      tasks.push(build(p, vs, n, counts, i, r, g));
      continue;
    }
    const v = mine[1];
    let fits = false;
    if (bundle) {
      const hit = v === n ? counts : (P as number[][]).find((c) => valueOf(c, vs) === v);
      if (hit) {
        fits = true;
        counts = hit;
        n = v;
      }
    } else if (p.task === "split" ? v >= 10 ** (vs.length - 1) && v < p.max : (P as number[]).includes(v)) {
      // A typed "split" number may have a 0 place (306): its gap stays and the key writes 0 in it.
      fits = true;
      n = v;
    }
    tasks.push(fits ? build(p, vs, n, counts, i, r, g) : wrongTask(vs.length));
  }
  const out: Made = { tasks, none: false };
  madeMemo.set(key, out);
  if (madeMemo.size > 50) madeMemo.delete(madeMemo.keys().next().value as string);
  return out;
}

export function items(props: ZahlzerlegungProps, t: Task): Item[] {
  const p = sane(props);
  const pl = placesOf(p);
  const { k, NW, DW, LT, SW } = layout(p);
  const out: Item[] = [];
  let x = 0;
  const put = (kind: Item["kind"], w: number, text: string) => {
    out.push({ kind, x, w, text });
    x += w;
  };
  const shownNum = (text: string) => {
    if (t.wrong) put("gap", NW, "");
    else put("given", NW, text);
  };
  const shownCount = (text: string) => {
    if (t.wrong) put("gap", DW, "");
    else put("given", DW, text);
  };
  const answer = (w: number, text: string) => put("gap", w, t.wrong ? "" : text);
  const sign = (s: string) => put("sign", SW, s);
  const letter = (j: number) => put("letter", LT, pl[j].letter);
  const part = (j: number) => String(t.digits[j] * pl[j].v);
  const gapAt = t.gap >= 0 ? t.order[t.gap] : -1;

  switch (p.task) {
    case "split":
      shownNum(String(t.n));
      sign("=");
      pl.forEach((_, j) => {
        answer(NW, part(j));
        if (j < k - 1) sign("+");
      });
      break;
    case "join":
      pl.forEach((_, j) => {
        shownNum(part(j));
        if (j < k - 1) sign("+");
      });
      sign("=");
      answer(NW, String(t.n));
      break;
    case "shuffled":
      t.order.forEach((j, idx) => {
        shownNum(part(j));
        if (idx < k - 1) sign("+");
      });
      sign("=");
      answer(NW, String(t.n));
      break;
    case "gap":
      pl.forEach((_, j) => {
        if (j === gapAt) answer(NW, part(j));
        else shownNum(part(j));
        if (j < k - 1) sign("+");
      });
      sign("=");
      shownNum(String(t.n));
      break;
    case "places":
      t.order.forEach((j) => {
        shownCount(String(t.digits[j]));
        letter(j);
      });
      sign("=");
      answer(NW, String(t.n));
      break;
    case "zero":
      shownNum(String(t.n));
      sign("=");
      pl.forEach((_, j) => {
        answer(DW, String(t.digits[j]));
        letter(j);
      });
      break;
    case "bundle":
      pl.forEach((_, j) => {
        shownCount(String(t.counts[j]));
        letter(j);
      });
      sign("=");
      answer(NW, String(t.n));
      break;
  }
  return out;
}
