// The Textaufgaben generator (#832): a story, a question, a Rechnung and an Antwort, from our own
// texts. The numbers follow the operation, the Zahlenraum, the Übertrag and the theme. The same
// seed gives the same tasks. A part left blank for the pupil is filled in the Lösungen.

import { describe, expect, it } from "vitest";
import { DEFAULTS, heightFor, layout, made, sane, visible, STORIES, type TextaufgabeProps, type Task } from "./textaufgabe";

const MINUS = "\u2212";

function props(over: Partial<TextaufgabeProps> = {}): TextaufgabeProps {
  return sane({ ...DEFAULTS, seed: 1, ...over });
}

function apply(op: Task["steps"][number]["op"], a: number, b: number): number | undefined {
  if (op === "+") return a + b;
  if (op === "-") return a - b;
  if (op === "*") return a * b;
  if (b !== 0 && a % b === 0) return a / b;
  return undefined;
}

// Übertrag, written apart from the generator: a ten for whole numbers and clocks, a euro for cents.
function crossed(op: "+" | "-", a: number, b: number, base: number): boolean {
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

function euro(cents: number): string {
  return `${Math.floor(cents / 100)},${String(cents % 100).padStart(2, "0")}`;
}

function clock(mins: number): string {
  return `${Math.floor(mins / 60)}:${String(mins % 60).padStart(2, "0")}`;
}

function holds(task: Task, max: number, carry: TextaufgabeProps["carry"]) {
  expect(task.manual).toBe(false);
  expect(task.text.length).toBeGreaterThan(0);
  expect(task.frage.length).toBeGreaterThan(0);
  expect(task.rechnung.length).toBeGreaterThan(0);
  expect(task.antwort.length).toBeGreaterThan(0);
  const base = task.kind === "cent" ? 100 : 10;
  const cap = task.kind === "cent" ? max * 100 : max;
  task.steps.forEach((s, i) => {
    expect(apply(s.op, s.left, s.right)).toBe(s.result);
    if (i > 0 && task.kind !== "dauer") expect(s.left).toBe(task.steps[i - 1].result);
    if (task.kind === "punkt") {
      expect(s.right).toBeGreaterThanOrEqual(1);
      expect(s.right).toBeLessThanOrEqual(max);
      expect(s.left).toBeGreaterThanOrEqual(0);
      expect(s.result).toBeGreaterThanOrEqual(0);
      expect(s.left).toBeLessThan(24 * 60);
      expect(s.result).toBeLessThan(24 * 60);
    } else if (task.kind === "dauer") {
      expect(s.result).toBeGreaterThanOrEqual(1);
      expect(s.result).toBeLessThanOrEqual(max);
      expect(s.left - s.right).toBe(s.result);
    } else if (s.op === "*" || s.op === ":") {
      expect(s.right).toBeGreaterThanOrEqual(2);
      expect(s.right).toBeLessThanOrEqual(10);
      expect(s.left).toBeGreaterThanOrEqual(0);
      expect(s.left).toBeLessThanOrEqual(cap);
      expect(s.result).toBeGreaterThanOrEqual(0);
      expect(s.result).toBeLessThanOrEqual(cap);
    } else {
      for (const n of [s.left, s.right, s.result]) {
        expect(Number.isInteger(n)).toBe(true);
        expect(n).toBeGreaterThanOrEqual(0);
        expect(n).toBeLessThanOrEqual(cap);
      }
    }
    if (task.fit && carry !== "any" && (s.op === "+" || s.op === "-")) expect(crossed(s.op, s.left, s.right, base)).toBe(carry === "yes");
  });
  if (task.id !== "plain") {
    const story = STORIES.find((s) => s.id === task.id);
    expect(story?.theme).toBe(task.theme);
  }
}

describe("sane", () => {
  it("fills an empty block with the Sachaufgabe defaults", () => {
    expect(sane({} as TextaufgabeProps)).toEqual({ ...DEFAULTS, seed: 0 });
  });

  it("drops a value the block cannot store", () => {
    const p = sane({
      count: 9,
      themes: ["geld", "nope", "kurz"] as TextaufgabeProps["themes"],
      ops: ["*", "+", "*"] as TextaufgabeProps["ops"],
      steps: 3 as 1,
      max: 15,
      numbers: "cents" as "whole",
      carry: "required" as "any",
      frage: "yes" as unknown as boolean,
      rechnung: false,
      antwort: true,
      sketch: true,
      rows: 0 as unknown as "auto",
      manual: false,
      zeit: "noon" as "both",
      seed: Number.NaN,
      written: [{ text: "T", frage: 4, rechnung: "R", antwort: "A" }],
    } as unknown as TextaufgabeProps);
    expect(p.count).toBe(DEFAULTS.count);
    expect(p.themes).toEqual(["kurz", "geld"]);
    expect(p.ops).toEqual(["+", "*"]);
    expect(p.steps).toBe(1);
    expect(p.max).toBe(20);
    expect(p.numbers).toBe("whole");
    expect(p.carry).toBe("any");
    expect(p.frage).toBe(true);
    expect(p.rows).toBe("auto");
    expect(p.zeit).toBe("both");
    expect(p.seed).toBe(0);
    expect(p.written).toBeUndefined();
    expect(p.sketch).toBe(true);
    expect(p.antwort).toBe(true);
  });
});

describe("made", () => {
  it("keeps the same tasks for one seed and draws others for another", () => {
    const one = made(props({ seed: 4, count: 3, themes: ["kurz", "sach", "raetsel", "zeit", "geld"] }));
    expect(JSON.stringify(made(props({ seed: 4, count: 3, themes: ["kurz", "sach", "raetsel", "zeit", "geld"] })))).toBe(JSON.stringify(one));
    expect(JSON.stringify(made(props({ seed: 5, count: 3, themes: ["kurz", "sach", "raetsel", "zeit", "geld"] })))).not.toBe(JSON.stringify(one));
    expect(one.tasks).toHaveLength(3);
  });

  it("holds the operation, the Zahlenraum and the Übertrag for one step and for two", () => {
    const ops = ["+", "-", "*", ":"] as const;
    for (const op of ops) {
      for (const carry of ["any", "yes", "no"] as const) {
        for (const seed of [1, 2, 3, 4]) {
          for (const task of made(props({ seed, ops: [op], carry, themes: ["sach"], max: 20, count: 2 })).tasks) {
            expect(task.fit).toBe(true);
            holds(task, 20, carry);
            expect(task.theme).toBe("sach");
          }
        }
      }
    }
    for (const seed of [1, 2, 3]) {
      const tasks = made(props({ seed, steps: 2, ops: ["+", "-"], carry: "yes", themes: ["sach"], max: 20, count: 2 })).tasks;
      for (const task of tasks) {
        expect(task.fit).toBe(true);
        expect(task.steps).toHaveLength(2);
        expect(task.rechnung).toContain("\n");
        holds(task, 20, "yes");
      }
    }
  });

  it("cannot keep a double Übertrag inside Zahlenraum 10, and still gives a story that adds up", () => {
    const [task] = made(props({ max: 10, steps: 2, ops: ["+"], carry: "yes", themes: ["kurz"], count: 1, seed: 2 })).tasks;
    expect(task.fit).toBe(false);
    expect(task.steps).toHaveLength(2);
    holds(task, 10, "any");
    expect(task.text.length).toBeGreaterThan(0);
  });

  it("draws Geld in cents, with a comma and a euro sign, including when the Zahlen are ganze Zahlen", () => {
    for (const task of made(props({ themes: ["geld"], ops: ["+", "-"], numbers: "whole", max: 20, count: 4, seed: 6, carry: "yes" })).tasks) {
      expect(task.kind).toBe("cent");
      expect(task.fit).toBe(true);
      holds(task, 20, "yes");
      expect(task.text).toContain("€");
      expect(task.rechnung).toContain(`${euro(task.steps[0].left)} €`);
      expect(task.antwort).toContain(`${euro(task.steps.at(-1)!.result)} €`);
    }
  });

  it("writes Kommazahlen with a comma outside Geld too", () => {
    const [task] = made(props({ themes: ["sach"], numbers: "decimal", ops: ["+"], max: 20, count: 1, seed: 3 })).tasks;
    expect(task.kind).toBe("cent");
    holds(task, 20, "any");
    expect(task.rechnung).toContain(euro(task.steps[0].result));
    expect(task.rechnung).not.toContain("€");
  });

  it("draws a Zeitpunkt as clocks and a Dauer as the minutes between them", () => {
    for (const task of made(props({ themes: ["zeit"], zeit: "punkt", ops: ["+"], max: 20, count: 3, seed: 8, carry: "yes" })).tasks) {
      expect(task.kind).toBe("punkt");
      expect(task.fit).toBe(true);
      holds(task, 20, "yes");
      expect(task.text).toContain("Uhr");
      expect(task.text).toContain(clock(task.steps[0].left));
      expect(task.antwort).toContain(clock(task.steps.at(-1)!.result));
    }
    const [dauer] = made(props({ themes: ["zeit"], zeit: "dauer", ops: ["-"], max: 30, count: 1, seed: 9, carry: "no" })).tasks;
    expect(dauer.kind).toBe("dauer");
    expect(dauer.fit).toBe(true);
    holds(dauer, 30, "no");
    expect(dauer.text).toContain("Minuten");
    expect(dauer.rechnung).toContain(MINUS);
    expect(dauer.text).toContain(clock(dauer.steps[0].right));
    expect(dauer.text).toContain(clock(dauer.steps[0].left));
  });

  it("keeps clocks when Kommazahlen are on, and a Rätsel asks for a Zahl", () => {
    const [zeit] = made(props({ themes: ["zeit"], zeit: "punkt", numbers: "decimal", ops: ["-"], count: 1, seed: 4 })).tasks;
    expect(zeit.kind).toBe("punkt");
    holds(zeit, 20, "any");
    const [raetsel] = made(props({ themes: ["raetsel"], ops: ["+"], count: 1, seed: 2 })).tasks;
    expect(raetsel.theme).toBe("raetsel");
    expect(`${raetsel.text} ${raetsel.frage}`).toContain("Zahl");
    holds(raetsel, 20, "any");
  });

  it("uses the teacher's four parts in the manual mode and ignores the pool", () => {
    const written = [{ text: "Eigener Text", frage: "Eigene Frage", rechnung: "1 + 1 = 2", antwort: "2" }];
    const [task] = made(props({ manual: true, written, count: 1, seed: 1, themes: ["geld"] })).tasks;
    expect(task).toMatchObject({ text: "Eigener Text", frage: "Eigene Frage", rechnung: "1 + 1 = 2", antwort: "2", manual: true });
    expect(task.text).not.toContain("€");
  });
});

describe("parts and the Rechnung", () => {
  it("shows the story always, and fills a blank Frage, Rechnung or Antwort only in the Lösungen", () => {
    const p = props({ frage: true, rechnung: false, antwort: false });
    expect(visible("text", p, false)).toBe(true);
    expect(visible("frage", p, false)).toBe(true);
    expect(visible("rechnung", p, false)).toBe(false);
    expect(visible("rechnung", p, true)).toBe(true);
    expect(visible("antwort", p, false)).toBe(false);
    expect(visible("antwort", p, true)).toBe(true);
    expect(visible("frage", props({ frage: false }), true)).toBe(true);
  });

  it("gives the Rechnung one row per step plus one, or the rows asked for, and the Zeichenfeld makes the block taller", () => {
    const base = props({ count: 2, steps: 1, sketch: false, rows: "auto" });
    expect(layout(base).rows).toBe(2);
    expect(layout(props({ steps: 2 })).rows).toBe(3);
    expect(layout(props({ rows: 6, steps: 2 })).rows).toBe(6);
    expect(heightFor(props({ count: 3 }), 180)).toBeGreaterThan(heightFor(base, 180));
    expect(heightFor(props({ sketch: true }), 180)).toBeGreaterThan(heightFor(base, 180));
    expect(heightFor(props({ rows: 8 }), 180)).toBeGreaterThan(heightFor(base, 180));
  });
});
