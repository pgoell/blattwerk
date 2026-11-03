// The written answers of every task block but the ones tasks.ts already names.
// Each text is what that block's answer key writes in red, once per thing the child writes.
import type { Block } from "../sheet";
import { chart, sane as saneChart } from "../diagramm";
import { made as halbOf, sane as saneHalb } from "../halbschriftlich";
import { made as squaresOf, sane as saneMagic } from "../magischesquadrat";
import { made as malOf, sane as saneMal } from "../malquadrat";
import { inverse, made as arrowsOf, opLabel as arrowLabel, sane as saneArrow } from "../pfeilbild";
import { made as fieldsOf, opLabel as fieldLabel, sane as saneOp } from "../operatorfeld";
import { made as wheelsOf, sane as saneWheel } from "../rechenrad";
import { made as tablesOf, sane as saneTab } from "../rechentabelle";
import { made as storiesOf, sane as saneStory } from "../textaufgabe";
import { made as housesOf, sane as saneHaus } from "../zahlenhaus";
import { made as chainsOf, sane as saneKette, stepLabel } from "../zahlenkette";
import { made as zehnOf, sane as saneZehn } from "../zehnerfeld";
import { made as splitsOf, sane as saneSplit } from "../zerlegungsfeld";
import type { Result } from "./props";

const num = (n: number): Result => ({ text: String(n), value: n });

function haus(props: Block["props"] & object): Result[][] {
  const p = saneHaus(props as never);
  const out: Result[][] = [];
  for (const h of housesOf(p).houses) {
    const task: Result[] = [];
    h.numbers.forEach((n, j) => {
      if (h.given[j]) return;
      if (j > 0 && h.wrong[Math.floor((j - 1) / 2)]) return;
      task.push(num(n));
    });
    if (task.length) out.push(task);
  }
  return out;
}

function kette(props: Block["props"] & object): Result[][] {
  const p = saneKette(props as never);
  const out: Result[][] = [];
  for (const c of chainsOf(p).chains) {
    if (c.over || c.wrong) continue;
    const task: Result[] = [];
    c.numbers.forEach((n, j) => {
      if (!c.given[j]) task.push(num(n));
    });
    if (!p.showStep) for (let j = 1; j < c.numbers.length; j++) task.push({ text: stepLabel(p.op, c.step) });
    if (task.length) out.push(task);
  }
  return out;
}

function tabelle(props: Block["props"] & object): Result[][] {
  const out: Result[][] = [];
  for (const t of tablesOf(saneTab(props as never)).tables) {
    if (t.wrong) continue;
    const task: Result[] = [];
    t.cols.forEach((n, j) => {
      if (!t.colShown[j]) task.push(num(n));
    });
    t.rows.forEach((n, r) => {
      if (!t.rowShown[r]) task.push(num(n));
    });
    t.cells.forEach((row, r) =>
      row.forEach((n, c) => {
        if (!t.struck[r][c] && !t.madeUp[r][c] && !t.given[r][c]) task.push(num(n));
      }),
    );
    if (task.length) out.push(task);
  }
  return out;
}

function pfeil(props: Block["props"] & object): Result[][] {
  const p = saneArrow(props as never);
  const out: Result[][] = [];
  for (const pic of arrowsOf(p).pictures) {
    if (pic.over || pic.wrong) continue;
    const task: Result[] = [];
    pic.numbers.forEach((n, j) => {
      if (!pic.given[j]) task.push(num(n));
    });
    pic.steps.forEach((step, j) => {
      if (pic.opGiven[j]) return;
      task.push({ text: arrowLabel(step) });
      if (p.arrows === "both") task.push({ text: arrowLabel(inverse(step)) });
    });
    if (task.length) out.push(task);
  }
  return out;
}

function operator(props: Block["props"] & object): Result[][] {
  const out: Result[][] = [];
  for (const field of fieldsOf(saneOp(props as never)).fields) {
    if (field.over || field.wrong) continue;
    const task: Result[] = [];
    field.numbers.forEach((n, j) => {
      if (!field.given[j]) task.push(num(n));
    });
    field.links.forEach((link, j) => {
      if (!field.opGiven[j]) task.push({ text: fieldLabel(link) });
    });
    if (task.length) out.push(task);
  }
  return out;
}

function rad(props: Block["props"] & object): Result[][] {
  const out: Result[][] = [];
  for (const wheel of wheelsOf(saneWheel(props as never)).wheels) {
    if (wheel.wrong) continue;
    const task: Result[] = [];
    wheel.rings.forEach((ring, ri) =>
      ring.forEach((n, s) => {
        if (!wheel.given[ri][s]) task.push(num(n));
      }),
    );
    if (task.length) out.push(task);
  }
  return out;
}

function magic(props: Block["props"] & object): Result[][] {
  const out: Result[][] = [];
  for (const s of squaresOf(saneMagic(props as never)).squares) {
    if (s.wrong) continue;
    const task: Result[] = [];
    s.cells.forEach((row, r) =>
      row.forEach((n, c) => {
        if (!s.given[r][c]) task.push(num(n));
      }),
    );
    if (task.length) out.push(task);
  }
  return out;
}

function mal(props: Block["props"] & object): Result[][] {
  const out: Result[][] = [];
  for (const s of malOf(saneMal(props as never)).squares) {
    if (s.wrong) continue;
    const far = s.size + 1;
    const task: Result[] = [];
    s.cells.forEach((row, r) =>
      row.forEach((n, c) => {
        if (r === 0 && (c === 0 || c === far)) return;
        if (r === far && c === 0) return;
        if (!s.given[r][c]) task.push(num(n));
      }),
    );
    if (task.length) out.push(task);
  }
  return out;
}

function split(props: Block["props"] & object): Result[][] {
  const out: Result[][] = [];
  for (const t of splitsOf(saneSplit(props as never)).tasks) {
    if (t.wrong) continue;
    const task = t.values.flatMap((n, pos) => (t.given[pos] ? [] : [num(n)]));
    if (task.length) out.push(task);
  }
  return out;
}

function halb(props: Block["props"] & object): Result[][] {
  const out: Result[][] = [];
  for (const t of halbOf(saneHalb(props as never)).tasks) {
    if (t.wrong || t.none) continue;
    const task: Result[] = [];
    t.values.forEach((n, pos) => {
      if (!t.given[pos]) task.push(num(n));
    });
    for (const step of t.steps) step.forEach((n) => task.push(num(n)));
    if (task.length) out.push(task);
  }
  return out;
}

function zehn(props: Block["props"] & object): Result[][] {
  const p = saneZehn(props as never);
  if (p.manual) return [];
  const out: Result[][] = [];
  for (const t of zehnOf(p).tasks) {
    if (t.wrong || t.none) continue;
    const task: Result[] = [];
    t.values.forEach((n, pos) => {
      if (t.kind === "write" && pos < 2) return;
      task.push(num(n));
    });
    if (task.length) out.push(task);
  }
  return out;
}

function story(props: Block["props"] & object): Result[][] {
  const p = saneStory(props as never);
  const out: Result[][] = [];
  for (const t of storiesOf(p).tasks) {
    const task: Result[] = [];
    if (!p.rechnung && t.rechnung.trim()) task.push({ text: t.rechnung });
    if (!p.antwort && t.antwort.trim()) task.push({ text: t.antwort });
    if (task.length) out.push(task);
  }
  return out;
}

function bars(props: Block["props"] & object): Result[][] {
  const task: Result[] = [];
  for (const v of chart(saneChart(props), true).values) {
    if (!v.answer || !v.text.trim()) continue;
    const n = Number(v.text.replace(",", "."));
    task.push(Number.isFinite(n) && String(n) === v.text ? { text: v.text, value: n } : { text: v.text });
  }
  return task.length ? [task] : [];
}

const KINDS: Partial<Record<Block["type"], (props: Block["props"] & object) => Result[][]>> = {
  zahlenhaus: haus,
  zahlenkette: kette,
  rechentabelle: tabelle,
  pfeilbild: pfeil,
  operatorfeld: operator,
  rechenrad: rad,
  magischesquadrat: magic,
  malquadrat: mal,
  zerlegungsfeld: split,
  halbschriftlich: halb,
  zehnerfeld: zehn,
  textaufgabe: story,
  diagramm: bars,
};

export function kindTasks(b: Block): Result[][] | undefined {
  const run = KINDS[b.type];
  return run ? run(b.props) : undefined;
}
