// What a Selbstkontrolle stores.
import type { Block } from "../sheet";

export type Form = "mixed" | "word" | "sum";
export type Turn = "none" | "upside" | "fold";
export type MixLook = "ticks" | "snake" | "caterpillar" | "train" | "box";
export type SelbstkontrolleProps = {
  /** How the child checks her results. "mixed": the results in a shuffled list, each with a box to tick. "word": a Lösungswort with a letter box under each task. "sum": one control sum per linked block. Default "mixed". */
  form: Form;
  /** Ids of the linked task blocks of the sheet, in the order the teacher ticked them. Default none. */
  links: string[];
  /** The Lösungswort the child builds from the letters, as the teacher typed it. Used with form "word" only. Default "". */
  word: string;
  /** The heading of the block. An empty heading prints none. Default "Selbstkontrolle". */
  title: string;
  /** Font size of the text in pt, except the heading, which is 1.2 times it. Default 14.
   * @minimum 8
   * @maximum 24
   */
  size: number;
  /** Turns the block for the child to read it later. "none": not turned. "upside": the whole content turned by 180 degrees. "fold": a dashed fold line along the top, with "Hier umknicken" over it, and the content turned by 180 degrees under it, so the child folds it back. Default "none". */
  turn: Turn;
  /** Seed for the shuffle of form "mixed" and of the table of form "word". The same seed always gives the same order. */
  seed: number;
  /** How many wrong answers to mix into the shuffled list of form "mixed". They are numbers that are not among the results, written the same way (decimals, euro). Default 0. A sheet from before this field counts as 0.
   * @minimum 0
   * @maximum 20
   */
  wrongs?: number;
  /** How form "mixed" draws the shuffled answers. "ticks": a list, each result with a box to tick. "snake": a winding snake of circles. "caterpillar": a caterpillar of circles, the first one its head. "train": a train, the first wagon its engine. "box": the results in a plain box, no ticks. Default "ticks". A sheet from before this field counts as "ticks". */
  look?: MixLook;
};

export const DEFAULTS: Omit<SelbstkontrolleProps, "seed"> = { form: "mixed", links: [], word: "", title: "Selbstkontrolle", size: 14, turn: "none", wrongs: 0, look: "ticks" };

export type Result = { text: string; value?: number };
export type Check = {
  empty: boolean;
  /** No block of the sheet gives tasks yet, so the hint asks for them first. */
  bare: boolean;
  lost: string[];
  sources: Block[];
  mixed: string[];
  sums: [string, string][];
  letters: Map<string, string[]>;
  table: [string, string][];
  fault?: string;
};

const pick = <T extends string>(v: unknown, options: readonly T[], fallback: T): T => (options as readonly unknown[]).includes(v) ? (v as T) : fallback;

export function sane(p: SelbstkontrolleProps): SelbstkontrolleProps & { wrongs: number; look: MixLook } {
  const r = (p ?? {}) as unknown as Record<string, unknown>;
  const wrongs = r.wrongs;
  return {
    form: pick(r.form, ["mixed", "word", "sum"] as const, DEFAULTS.form),
    links: Array.isArray(r.links) ? r.links.filter((id): id is string => typeof id === "string") : [],
    word: typeof r.word === "string" ? r.word : DEFAULTS.word,
    title: typeof r.title === "string" ? r.title : DEFAULTS.title,
    size: typeof r.size === "number" && r.size >= 8 && r.size <= 24 ? r.size : DEFAULTS.size,
    turn: pick(r.turn, ["none", "upside", "fold"] as const, DEFAULTS.turn),
    seed: Number.isSafeInteger(r.seed) ? (r.seed as number) : 0,
    wrongs: typeof wrongs === "number" && Number.isInteger(wrongs) && wrongs >= 0 && wrongs <= 20 ? wrongs : 0,
    look: pick(r.look, ["ticks", "snake", "caterpillar", "train", "box"] as const, "ticks"),
  };
}

