// The limits a maths block sends, and which of the server's exercises it keeps.
import { post, signed } from "../../api";
import type { Exercise, Limits, Made, MathsProps, Range } from "../../sheet";

export const ROOMS = [10, 20, 100, 1000, 1000000];
// Einer, Zehner, Hunderter, Tausender and so on up to the million.
export const PLACES = ["E", "Z", "H", "T", "ZT", "HT", "M"];
// The places after the comma, Zehntel first, with their labels in the rows and their names for the pupil's ear.
export const FRACTIONS = [["z", "Zehntel"], ["h", "Hundertstel"]] as const;
// A number's digit ranges: its whole places by its name, or the places after the comma by AFTER.
export type Key = "a" | "b" | "c" | "af" | "bf" | "cf";
export const AFTER = { a: "af", b: "bf", c: "cf" } as const;
export const NACH = ["0 Nachkommastellen", "1 Nachkommastelle", "2 Nachkommastellen"];
export const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
export const CARRIES = [["none", "Ohne"], ["required", "Mit"], ["either", "Egal"]] as const;
export const FORMATS = [["row", "Zeile"], ["gap", "Lücke"], ["written", "Schriftlich"], ["compare", "Vergleichen"]] as const;
export const SIDES = [["nn", "Zahl ○ Zahl"], ["tn", "Aufgabe ○ Zahl"], ["tt", "Aufgabe ○ Aufgabe"]] as const;
export const LOOSEN: Record<string, string> = { carry: "Übertrag", rest: "Rest", a: "Ziffern der 1. Zahl", b: "Ziffern der 2. Zahl", c: "Ziffern der 3. Zahl", max: "Zahlenraum", close: "Knapp", equal: "Aufgaben mit =", brackets: "Klammern", family: "Aufgabenfamilien", zero: "Aufgaben mit 0", one: "Aufgaben mit 1 beim Malnehmen und Teilen", distinct: "keine gleichen Zahlen", small: "Kleines Einmaleins" };
export const GAPS = ["a", "b", "c", "result"] as const;
export const FAMILIES = [["none", "Keine"], ["swap", "Tauschaufgaben"], ["reverse", "Umkehraufgaben"], ["neighbour", "Nachbaraufgaben"]] as const;
export const NTH = { a: "1. Zahl", b: "2. Zahl", c: "3. Zahl" } as const;

export const newSeed = () => Math.floor(Math.random() * 1e9);
// The limits the server reads from a request, and nothing else.
export const ask = ({ ops, max, a, b, c, carry, rest, format, count, seed, sides, close, equal, numbers, pvs, brackets, decimals, money, af, bf, cf, family, moves, gaps, zero, one, distinct, small }: Limits) => ({ ops, max, a, b, c, carry, rest, format, count, seed, sides, close, equal, numbers, pvs, brackets, decimals, money, af, bf, cf, family, moves, gaps, zero, one, distinct, small });
// Asked with the session run out, it brings the login.
export const generate = (l: Limits) => signed(post<Made>("/maths", ask(l)));
// A smaller count and nothing else changed: the block keeps its own exercises, less the last ones, and the server's word on what is in the way.
// With families the count is that of the families, so the last families go whole.
// A bigger count: the block keeps its exercises and takes the new ones from the server's answer, at the end.
// The server draws a new set for every count, so only the tail that is new to the block is taken.
export const kept = (was: MathsProps, next: Limits, made: Made): Made => {
  if (JSON.stringify(ask({ ...was, count: next.count })) !== JSON.stringify(ask(next))) return made;
  if (next.count < was.count)
    return { ...made, exercises: was.exercises.filter((e, i) => (("sign" in e ? undefined : e.family) ?? i) < next.count) };
  if (next.count === was.count) return made;
  const families = was.exercises.some((e) => ("sign" in e ? undefined : e.family) !== undefined);
  if (families) {
    // The families of a list by number, each told by its tasks, so that one the block has already is not added again.
    const groups = (list: Exercise[]) => {
      const out = new Map<number, Exercise[]>();
      for (const e of list) {
        const f = "sign" in e ? 0 : (e.family ?? 0);
        out.set(f, [...(out.get(f) ?? []), e]);
      }
      return [...out.values()];
    };
    const told = (g: Exercise[]) => JSON.stringify(g.map((e) => JSON.stringify({ ...e, family: undefined })).sort());
    const old = groups(was.exercises);
    const all = groups(made.exercises);
    const known = new Set(old.map(told));
    const fresh = all.filter((g) => !known.has(told(g)) && known.add(told(g)));
    const more = [...fresh, ...all.slice(old.length)].filter((g, i, list) => list.indexOf(g) === i).slice(0, Math.max(0, all.length - old.length));
    return { ...made, exercises: [...was.exercises, ...more.flatMap((g, k) => g.map((e) => ({ ...e, family: old.length + k })))] };
  }
  const seen = new Set(was.exercises.map((e) => JSON.stringify(e)));
  const fresh = made.exercises.filter((e) => !seen.has(JSON.stringify(e)) && seen.add(JSON.stringify(e)));
  const more = [...fresh, ...made.exercises.slice(was.exercises.length)].slice(0, Math.max(0, made.exercises.length - was.exercises.length));
  return { ...made, exercises: [...was.exercises, ...more] };
};
// Any digit in each place of a Zahlenraum.
export const anyDigits = (max: number): Range[] => Array.from(String(max), (): Range => [0, 9]);
