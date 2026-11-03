// The tasks a Textaufgabe draws. A pure function of the settings and the seed.

import { rng } from "../zahlenmauer";
import { STORIES, type Story } from "./pool";
import { sane, type Carry, type TextOp, type TextaufgabeProps, type TextaufgabeWritten } from "./props";

export type Step = { op: TextOp; left: number; right: number; result: number };
export type Kind = "number" | "cent" | "punkt" | "dauer";
export type Task = {
  id: string;
  theme: Story["theme"];
  kind: Kind;
  steps: Step[];
  text: string;
  frage: string;
  rechnung: string;
  antwort: string;
  manual: boolean;
  /** False when no numbers keep the Übertrag inside the Zahlenraum. The story still adds up. */
  fit: boolean;
};
export type Made = { tasks: Task[] };

const SIGN: Record<TextOp, string> = { "+": "+", "-": "\u2212", "*": "\u00B7", ":": ":" };
const DAY = 24 * 60;

function apply(op: TextOp, a: number, b: number): number | undefined {
  if (op === "+") return a + b;
  if (op === "-") return a - b;
  if (op === "*") return a * b;
  if (b !== 0 && a % b === 0) return a / b;
  return undefined;
}

export function crossed(op: "+" | "-", a: number, b: number, base: number): boolean {
  let carry = 0;
  let x = a;
  let y = b;
  while (x > 0 || y > 0) {
    const da = x % base;
    const db = y % base;
    carry = op === "+" ? (da + db + carry >= base ? 1 : 0) : da < db + carry ? 1 : 0;
    if (carry) return true;
    x = Math.floor(x / base);
    y = Math.floor(y / base);
  }
  return false;
}

function carryOk(op: TextOp, a: number, b: number, base: number, carry: Carry): boolean {
  if (carry === "any" || (op !== "+" && op !== "-")) return true;
  return crossed(op, a, b, base) === (carry === "yes");
}

function kindOf(story: Story, p: TextaufgabeProps): Kind {
  if (story.clock === "punkt") return "punkt";
  if (story.clock === "dauer" && story.ops[0] === "-") return "dauer";
  if (story.theme === "geld" || (p.numbers === "decimal" && story.clock === undefined)) return "cent";
  return "number";
}

function euro(cents: number): string {
  return `${Math.floor(cents / 100)},${String(cents % 100).padStart(2, "0")}`;
}

function clock(mins: number): string {
  return `${Math.floor(mins / 60)}:${String(mins % 60).padStart(2, "0")}`;
}

function fill(story: Story, steps: Step[], kind: Kind): Pick<Task, "text" | "frage" | "rechnung" | "antwort"> {
  const s0 = steps[0];
  const s1 = steps[1];
  const last = steps[steps.length - 1];
  const money = kind === "cent";
  const show = (n: number, op: TextOp, side: "left" | "right" | "result") => {
    if (kind === "punkt" && side !== "right") return clock(n);
    if (kind === "dauer" && side !== "result") return clock(n);
    if (money && !(side === "right" && (op === "*" || op === ":"))) return euro(n);
    return String(n);
  };
  const bag: Record<string, string> =
    kind === "dauer"
      ? { a: clock(s0.right), b: clock(s0.left), c: "", m: "", r: String(s0.result) }
      : {
          a: show(s0.left, s0.op, "left"),
          b: show(s0.right, s0.op, "right"),
          m: show(s0.result, s0.op, "result"),
          c: s1 ? show(s1.right, s1.op, "right") : "",
          r: show(last.result, last.op, "result"),
        };
  const put = (s: string) => s.replace(/\{(a|b|c|m|r)\}/g, (_, key: string) => bag[key] ?? "");
  return { text: put(story.text), frage: put(story.frage), rechnung: put(story.rechnung), antwort: put(story.antwort) };
}

function tryStep(op: TextOp, cap: number, next: () => number, left: number | undefined): Step | null {
  if (op === "+") {
    const a = left ?? Math.floor(next() * (cap + 1));
    if (a > cap) return null;
    const b = Math.floor(next() * (cap - a + 1));
    if (a === 0 && b === 0) return null;
    return { op, left: a, right: b, result: a + b };
  }
  if (op === "-") {
    const a = left ?? Math.floor(next() * (cap + 1));
    if (a < 1) return null;
    const b = Math.floor(next() * (a + 1));
    return { op, left: a, right: b, result: a - b };
  }
  if (op === "*") {
    const b = 2 + Math.floor(next() * 9);
    const room = Math.floor(cap / b);
    if (room < 1) return null;
    const a = left ?? 1 + Math.floor(next() * room);
    if (a < 1 || a > room || a * b > cap) return null;
    return { op, left: a, right: b, result: a * b };
  }
  const b = 2 + Math.floor(next() * 9);
  const room = Math.floor(cap / b);
  if (room < 1) return null;
  if (left !== undefined) {
    if (left < b || left % b !== 0 || left / b > cap) return null;
    return { op, left, right: b, result: left / b };
  }
  const result = 1 + Math.floor(next() * room);
  return { op, left: result * b, right: b, result };
}

function tryNumbers(ops: TextOp[], cap: number, base: number, carry: Carry, next: () => number): Step[] | null {
  for (let t = 0; t < 400; t++) {
    const steps: Step[] = [];
    let left: number | undefined;
    let ok = true;
    for (const op of ops) {
      const step = tryStep(op, cap, next, left);
      if (!step || !carryOk(op, step.left, step.right, base, carry)) {
        ok = false;
        break;
      }
      steps.push(step);
      left = step.result;
    }
    if (ok) return steps;
  }
  return null;
}

function options(op: TextOp, cap: number, left: number | undefined): Step[] {
  const out: Step[] = [];
  const lefts = left !== undefined ? [left] : [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 50, 60, 100, 120, 150, 200, 250, 300].filter((n) => n <= cap);
  const rights = op === "*" || op === ":" ? [2, 3, 4, 5, 6, 8, 10] : undefined;
  for (const a of lefts) {
    const bs = rights ?? Array.from({ length: Math.min(op === "+" ? cap - a : a, 40) + 1 }, (_, b) => b);
    for (const b of bs) {
      const result = apply(op, a, b);
      if (result === undefined || result < 0 || result > cap || a > cap) continue;
      if ((op === "*" || op === ":") && result < 1) continue;
      out.push({ op, left: a, right: b, result });
    }
  }
  return out;
}

function forcedNumbers(ops: TextOp[], cap: number, base: number, carry: Carry): Step[] | null {
  function walk(i: number, left: number | undefined): Step[] | null {
    if (i === ops.length) return [];
    for (const step of options(ops[i], cap, left)) {
      if (!carryOk(step.op, step.left, step.right, base, carry)) continue;
      const rest = walk(i + 1, step.result);
      if (rest) return [step, ...rest];
    }
    return null;
  }
  return walk(0, undefined);
}

function numberSteps(ops: TextOp[], cap: number, base: number, carry: Carry, next: () => number): { steps: Step[]; fit: boolean } {
  const strict = tryNumbers(ops, cap, base, carry, next);
  if (strict) return { steps: strict, fit: true };
  const loose = tryNumbers(ops, cap, base, "any", next) ?? forcedNumbers(ops, cap, base, "any");
  const steps = loose ?? ops.map((op) => ({ op, left: 1, right: op === ":" || op === "*" ? 2 : 1, result: op === "*" ? 2 : op === ":" ? 0 : op === "+" ? 2 : 0 }));
  return { steps, fit: false };
}

function tryClock(ops: TextOp[], max: number, carry: Carry, next: () => number): Step[] | null {
  for (let t = 0; t < 400; t++) {
    const steps: Step[] = [];
    let left: number | undefined;
    let ok = true;
    for (const op of ops) {
      if (op !== "+" && op !== "-") return null;
      const dur = 1 + Math.floor(next() * max);
      const start = left ?? 7 * 60 + Math.floor(next() * (11 * 60));
      const result = op === "+" ? start + dur : start - dur;
      if (dur > max || result < 0 || result >= DAY || (op === "-" && dur > start) || !carryOk(op, start, dur, 10, carry)) {
        ok = false;
        break;
      }
      steps.push({ op, left: start, right: dur, result });
      left = result;
    }
    if (ok && steps.length === ops.length) return steps;
  }
  return null;
}

function forcedClock(ops: TextOp[], max: number, carry: Carry): Step[] | null {
  function walk(i: number, left: number | undefined): Step[] | null {
    if (i === ops.length) return [];
    const op = ops[i];
    if (op !== "+" && op !== "-") return null;
    const starts = left !== undefined ? [left] : Array.from({ length: 11 * 12 }, (_, n) => 7 * 60 + n * 5);
    for (const start of starts) {
      for (let dur = 1; dur <= max; dur++) {
        const result = op === "+" ? start + dur : start - dur;
        if (result < 0 || result >= DAY || !carryOk(op, start, dur, 10, carry)) continue;
        const rest = walk(i + 1, result);
        if (rest) return [{ op, left: start, right: dur, result }, ...rest];
      }
    }
    return null;
  }
  return walk(0, undefined);
}

function clockSteps(ops: TextOp[], max: number, carry: Carry, next: () => number): { steps: Step[]; fit: boolean } {
  const strict = tryClock(ops, max, carry, next) ?? forcedClock(ops, max, carry);
  if (strict) return { steps: strict, fit: true };
  const loose = tryClock(ops, max, "any", next) ?? forcedClock(ops, max, "any");
  return { steps: loose ?? [{ op: "+", left: 8 * 60, right: 1, result: 8 * 60 + 1 }], fit: false };
}

function dauerSteps(max: number, carry: Carry, next: () => number): { steps: Step[]; fit: boolean } {
  const accept = (start: number, duration: number, rule: Carry) => {
    const end = start + duration;
    return end < DAY && carryOk("-", end, start, 10, rule);
  };
  for (let t = 0; t < 400; t++) {
    const duration = 1 + Math.floor(next() * max);
    const start = 7 * 60 + Math.floor(next() * (12 * 60));
    if (accept(start, duration, carry)) return { steps: [{ op: "-", left: start + duration, right: start, result: duration }], fit: true };
  }
  for (let start = 7 * 60; start < 18 * 60; start++) {
    for (let duration = 1; duration <= max; duration++) {
      if (accept(start, duration, carry)) return { steps: [{ op: "-", left: start + duration, right: start, result: duration }], fit: true };
    }
  }
  return { steps: [{ op: "-", left: 8 * 60 + 10, right: 8 * 60, result: 10 }], fit: false };
}

function matching(p: TextaufgabeProps): Story[] {
  return STORIES.filter((s) => p.themes.includes(s.theme) && s.ops.length === p.steps && s.ops.every((op) => p.ops.includes(op)) && !(s.clock === "punkt" && p.zeit === "dauer") && !(s.clock === "dauer" && p.zeit === "punkt"));
}

function plain(ops: TextOp[], steps: 1 | 2): Story {
  const used: TextOp[] = steps === 1 ? [ops[0]] : ops.length > 1 ? [ops[0], ops[1]] : [ops[0], ops[0]];
  const text = used.length === 1 ? `Rechne {a} ${SIGN[used[0]]} {b}.` : `Rechne {a} ${SIGN[used[0]]} {b} und dann ${SIGN[used[1]]} {c}.`;
  const rechnung = used.length === 1 ? `{a} ${SIGN[used[0]]} {b} = {r}` : `{a} ${SIGN[used[0]]} {b} = {m}\n{m} ${SIGN[used[1]]} {c} = {r}`;
  return { id: "plain", theme: "kurz", ops: used, text, frage: "Was kommt heraus?", rechnung, antwort: "{r}." };
}

function build(story: Story, p: TextaufgabeProps, next: () => number): Task {
  const kind = kindOf(story, p);
  const drawn =
    kind === "punkt" ? clockSteps(story.ops, p.max, p.carry, next)
    : kind === "dauer" ? dauerSteps(p.max, p.carry, next)
    : numberSteps(story.ops, kind === "cent" ? p.max * 100 : p.max, kind === "cent" ? 100 : 10, p.carry, next);
  return { id: story.id, theme: story.theme, kind, ...drawn, ...fill(story, drawn.steps, kind), manual: false };
}

function withWritten(task: Task, row: TextaufgabeWritten | undefined): Task {
  if (!row) return task;
  return { ...task, text: row.text, frage: row.frage, rechnung: row.rechnung, antwort: row.antwort, manual: true, fit: true };
}

function tasksOf(p: TextaufgabeProps): Task[] {
  const next = rng(p.seed);
  const stories = matching(p);
  const seen = new Set<string>();
  const tasks: Task[] = [];
  for (let i = 0; i < p.count; i++) {
    let task: Task | undefined;
    for (let t = 0; t < 8; t++) {
      const story = stories.length ? stories[Math.floor(next() * stories.length)] : plain(p.ops, p.steps);
      task = build(story, p, next);
      const key = `${task.id}:${task.steps.map((s) => `${s.left},${s.right}`).join(";")}`;
      if (!seen.has(key)) {
        seen.add(key);
        break;
      }
    }
    tasks.push(withWritten(task!, p.manual ? p.written?.[i] : undefined));
  }
  return tasks;
}

const memo = new Map<string, Made>();

export function made(props: TextaufgabeProps): Made {
  const p = sane(props);
  const key = JSON.stringify(p);
  const hit = memo.get(key);
  if (hit) return hit;
  const madeTasks = { tasks: tasksOf(p) };
  memo.set(key, madeTasks);
  if (memo.size > 50) memo.delete(memo.keys().next().value!);
  return madeTasks;
}
