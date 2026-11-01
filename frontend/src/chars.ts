// The characters the text bar inserts, and the small rules behind the Unicode field and the recent list.
import { parasOf, stored, type TextProps } from "./sheet";

// In the order the menu shows them. The name is what a button says.
export const CHARS: readonly [string, string][] = [
  ["·", "Malpunkt"],
  ["×", "Mal"],
  ["÷", "Geteilt"],
  ["≈", "Ungefähr"],
  ["≠", "Ungleich"],
  ["≤", "Kleiner oder gleich"],
  ["≥", "Größer oder gleich"],
  ["²", "Hoch zwei"],
  ["α", "Alpha"],
  ["β", "Beta"],
  ["γ", "Gamma"],
  ["€", "Euro"],
  ["©", "Copyright"],
  ["∥", "Parallel"],
  ["⊥", "Senkrecht"],
];

// How many symbols the recent list keeps.
export const RECENT = 8;

// `U+00B7` or `00B7`: one scalar the sheet can show. A control, a surrogate or a code past U+10FFFF is none.
export function fromCode(raw: string): string | undefined {
  const found = /^(?:U\+)?([0-9A-Fa-f]{1,6})$/i.exec(raw.trim());
  if (!found) return;
  const n = Number.parseInt(found[1], 16);
  if (n < 0x20 || n > 0x10ffff || (n >= 0x7f && n <= 0x9f) || (n >= 0xd800 && n <= 0xdfff)) return;
  return String.fromCodePoint(n);
}

// Newest first. The same symbol again moves to the front, and the list stays at `RECENT`.
export function remembered(list: readonly string[], ch: string): string[] {
  return [ch, ...list.filter((c) => c !== ch)].slice(0, RECENT);
}

// The character at the end of the text, on the last run so a bold word stays bold.
export function added(text: Pick<TextProps, "text" | "rich">, ch: string) {
  const paras = parasOf({ size: 14, align: "left", ...text });
  const last = paras.at(-1);
  if (!last) return stored([{ runs: [{ text: ch }] }]);
  const runs = last.runs.length
    ? last.runs.map((run, i) => (i === last.runs.length - 1 ? { ...run, text: run.text + ch } : run))
    : [{ text: ch }];
  return stored([...paras.slice(0, -1), { ...last, runs }]);
}
