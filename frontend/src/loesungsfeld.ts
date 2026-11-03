// A Lösungsfeld: one blank on the pupil's sheet, filled only in the Lösungen.
// For a Zuordnen or an Ankreuzen task whose answer is the teacher's own text or picture.
//
// Stored shape: `{ type: "loesungsfeld", props: LoesungsfeldProps }`.
// - `kind`: "text" a one-line Lösungstext, "image" a Lösungsbild (default "text").
// - `text`: the Lösungstext. A line break becomes a space.
// - `blank`: "line" Unterstrich, "box" Rahmen, "none" nothing (default "line").
// - `code`: an OpenMoji symbol from the library. `upload` and `ratio`: a picture the teacher uploaded.
//   An upload wins over a symbol. The pupil's sheet shows neither.
// - `wrongs`: falsche Lösungen, for a Selbstkontrolle and later for digital sheets. At most 20.
//   One that repeats the right answer is dropped. `answers` is what a Selbstkontrolle can read.
// - `size`: the Lösungstext in pt, 8 to 48 (default 14).
// - `even`: with the other even fields on the page, the blank is as wide as the longest answer,
//   so the line length gives nothing away (default false).
// `sane` never throws. `shown` is what is drawn: the blank, and the answer only when `solved`.

import { PT } from "./height";
import { SYMBOLS } from "./symbols";

const CODES = new Set(SYMBOLS.map(([code]) => code));
const KINDS = ["text", "image"] as const;
const BLANKS = ["line", "box", "none"] as const;
const MIN_MM = 18;
const MAX_WRONGS = 20;

export type FieldKind = (typeof KINDS)[number];
export type Blank = (typeof BLANKS)[number];

export type Wrong =
  | {
      /** A wrong Lösungstext. */
      kind: "text";
      /** The wrong text, one line. */
      text: string;
    }
  | {
      /** A wrong Lösungsbild. */
      kind: "image";
      /** The OpenMoji code of the wrong picture, from the symbol library. Absent when it is an upload. */
      code?: string;
      /** The id of an uploaded wrong picture. Absent when the picture is a symbol. */
      upload?: number;
    };

export type LoesungsfeldProps = {
  /** What the Lösungen print: "text" a one-line Lösungstext, "image" a Lösungsbild. Default "text". */
  kind: FieldKind;
  /** The Lösungstext, one line. The pupil's sheet leaves it blank. Default "". */
  text: string;
  /** How the blank looks on the pupil's sheet: "line" an underline (Unterstrich), "box" a frame (Rahmen), "none" nothing. Default "line". */
  blank: Blank;
  /** The OpenMoji code of the Lösungsbild, from the symbol library. Absent for a Lösungstext, or when the picture is an upload. */
  code?: string;
  /** The id of an uploaded picture used as the Lösungsbild. Absent when the picture is a symbol. */
  upload?: number;
  /** The uploaded picture's width over its height. 1 for a square. Absent means 1. */
  ratio?: number;
  /** Wrong answers (falsche Lösungen) for a Selbstkontrolle and later for digital sheets. Absent means none. */
  wrongs?: Wrong[];
  /** Font size of the Lösungstext in pt. Default 14.
   * @minimum 8
   * @maximum 48
   */
  size: number;
  /** True makes this field as wide as the widest even Lösungsfeld on the page, so the line length gives nothing away. Default false. */
  even: boolean;
};

export const DEFAULTS: LoesungsfeldProps = { kind: "text", text: "", blank: "line", size: 14, even: false, wrongs: [] };

export type Answer =
  | { kind: "text"; text: string }
  | { kind: "image"; code?: string; upload?: number; ratio?: number };

export type Shown = { blank: Blank; text?: string; code?: string; upload?: number; ratio?: number };

const pick = <T extends string>(v: unknown, options: readonly T[], fallback: T): T =>
  (options as readonly unknown[]).includes(v) ? (v as T) : fallback;

const line = (v: unknown) => (typeof v === "string" ? v.replace(/[\r\n]+/g, " ").replace(/ +/g, " ").trim() : "");

const codeOf = (v: unknown) => (typeof v === "string" && CODES.has(v) ? v : undefined);

const uploadOf = (v: unknown) => (typeof v === "number" && Number.isInteger(v) && v > 0 ? v : undefined);

const ratioOf = (v: unknown) => (typeof v === "number" && Number.isFinite(v) && v > 0 ? v : undefined);

function wrongOf(v: unknown): Wrong | undefined {
  if (!v || typeof v !== "object") return undefined;
  const r = v as Record<string, unknown>;
  if (r.kind === "image") {
    const code = codeOf(r.code);
    const upload = uploadOf(r.upload);
    if (!code && upload === undefined) return undefined;
    return { kind: "image", ...(code ? { code } : {}), ...(upload !== undefined ? { upload } : {}) };
  }
  const text = line(r.text);
  return r.kind === "text" && text ? { kind: "text", text } : undefined;
}

export function sane(p: unknown): LoesungsfeldProps {
  const r = (p ?? {}) as Record<string, unknown>;
  const kind = pick(r.kind, KINDS, DEFAULTS.kind);
  const text = line(r.text);
  const code = codeOf(r.code);
  const upload = uploadOf(r.upload);
  const seen = new Set<string>();
  const wrongs: Wrong[] = [];
  for (const item of Array.isArray(r.wrongs) ? r.wrongs : []) {
    const wrong = wrongOf(item);
    if (!wrong || wrongs.length >= MAX_WRONGS) continue;
    const key = wrong.kind === "text" ? `t:${wrong.text}` : `i:${wrong.code ?? ""}:${wrong.upload ?? ""}`;
    const same =
      wrong.kind === "text"
        ? kind === "text" && wrong.text === text
        : kind === "image" && ((code !== undefined && wrong.code === code) || (upload !== undefined && wrong.upload === upload));
    if (same || seen.has(key)) continue;
    seen.add(key);
    wrongs.push(wrong);
  }
  return {
    kind,
    text,
    blank: pick(r.blank, BLANKS, DEFAULTS.blank),
    ...(code ? { code } : {}),
    ...(upload !== undefined ? { upload, ratio: ratioOf(r.ratio) ?? 1 } : {}),
    wrongs,
    size: typeof r.size === "number" && r.size >= 8 && r.size <= 48 ? r.size : DEFAULTS.size,
    even: r.even === true,
  };
}

// The blank, and the answer only in the Lösungen. The editor's panel holds the answer while this is blank.
export function shown(p: LoesungsfeldProps, solved: boolean): Shown {
  const s = sane(p);
  if (!solved) return { blank: s.blank };
  if (s.kind === "image") {
    if (s.upload !== undefined) return { blank: s.blank, upload: s.upload, ratio: s.ratio ?? 1 };
    if (s.code) return { blank: s.blank, code: s.code };
    return { blank: s.blank };
  }
  return s.text ? { blank: s.blank, text: s.text } : { blank: s.blank };
}

// The right answer, then the falsche Lösungen. A Selbstkontrolle can read this without storing a copy.
export function answers(p: LoesungsfeldProps): { right: Answer; wrongs: Wrong[] } {
  const s = sane(p);
  const right: Answer =
    s.kind === "image"
      ? { kind: "image", ...(s.code ? { code: s.code } : {}), ...(s.upload !== undefined ? { upload: s.upload, ratio: s.ratio } : {}) }
      : { kind: "text", text: s.text };
  return { right, wrongs: s.wrongs ?? [] };
}

const round = (n: number) => Math.round(n * 10) / 10;

// The width in mm the answer needs on one line. A picture is a square of the font's size, at least MIN_MM.
export function contentMm(p: LoesungsfeldProps): number {
  const s = sane(p);
  const em = s.size * PT;
  if (s.kind === "image") return round(Math.max(MIN_MM, em * 1.6));
  return round(Math.max(MIN_MM, [...s.text].length * em * 0.55 + em * 0.4));
}

// The blank's width. Even fields on the page share the widest answer's width.
export function blankMm(p: LoesungsfeldProps, peers: LoesungsfeldProps[]): number {
  const s = sane(p);
  const own = contentMm(s);
  if (!s.even) return own;
  const group = (peers.length ? peers : [s]).map((item) => sane(item)).filter((item) => item.even);
  return Math.max(own, ...group.map(contentMm));
}
