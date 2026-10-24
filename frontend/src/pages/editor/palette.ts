// The names, the shapes and the small geometry the editor shares.
import { memo, type TouchEvent } from "react";
import { AlignCenterHorizontal, AlignCenterVertical, AlignEndHorizontal, AlignEndVertical, AlignStartHorizontal, AlignStartVertical, ArrowRight, Circle, MessageSquare, Minus, MoveHorizontal, Square, Squircle, Star, Triangle, type LucideIcon } from "lucide-react";
import { DRAWERS } from "../../components/Blank";
import { fresh } from "../../history";
import { newer } from "../../saves";
import { MARGIN, Paper, RULINGS, boxed, isLine, kindOf, type Axis, type Block, type Box, type Doc, type Fade, type Guides, type Kind, type TextProps } from "../../sheet";
import { FRAMES as FRAME_KINDS } from "../../insert";

// The line a PDF gives when it fails, and the line it keeps while the sheet's change is not saved.
export const pdfFault = "Das PDF konnte nicht erstellt werden.";

// A point turned by `by` degrees about `about`, in the same sense as a block turns (Format's swung).
export const turnedAt = ([x, y]: [number, number], by: number, [cx, cy]: [number, number]): [number, number] => {
  const [c, s] = [Math.cos((by * Math.PI) / 180), Math.sin((by * Math.PI) / 180)];
  const [dx, dy] = [x - cx, y - cy];
  return [cx + dx * c - dy * s, cy + dx * s + dy * c];
};

export type Template = { id: number; name: string; doc: Doc; group?: string };
// A new block's type and settings; `add` gives it its place.
export type Fresh<B = Block> = B extends Block ? Pick<B, "type" | "props"> : never;

export const SIDES = { top: true, left: true, bottom: true, right: true, center: true, middle: true };
export const CORNERS = ["nw", "ne", "sw", "se"];
// The look the brush carries from a text or a shape to the next. A line gives and takes its stroke alone, a table
// what its cells have and the colour of its lines, `rule`, a Lineatur its script, the colour of its lines, `rule`
// too, and its Nachspuren, `trace`, and a maths block its size and the numbering of its exercises. A Lineatur 1, 2 or 3 also
// gives and takes its houses, `house` and `houseTint`, and its middle band, `band` and `bandColor`. Every block
// gives and takes the numbering before it, `mark`. The Silbenbögen and the Silbenfarbe go along, `syllables`, `tints`
// and `tintsAcross`, but not the words split by hand, `breaks`: they belong to the words.
export const LOOK = ["font", "size", "bold", "italic", "underline", "color", "spacing", "align", "valign", "syllables", "tints", "tintsAcross", "trace", "fade", "fill", "opacity", "stroke", "strokeOpacity", "strokeWidth", "dash"] as const;
// The part of it that belongs to the words, with the breaks set by hand, the gaps and the solution words, and the
// Schüttelwörter with their settings: a line takes none of these.
export const WORDS: string[] = ["font", "size", "bold", "italic", "underline", "color", "spacing", "align", "valign", "syllables", "tints", "tintsAcross", "breaks", "gapWidth", "bank", "mix", "mixFirst", "mixCaps", "mixLine", "list", "listCols", "holes", "holeSeed"];
export type Coat = Partial<TextProps> & { mark?: string; rule?: string; trace?: boolean | "outline" | "dotted"; fade?: Fade; numbering?: string; house?: boolean; houseTint?: "room" | "all"; band?: boolean; bandColor?: string };
// Karo is always in print, and a written exercise is as large as its squares: they have no script and no size.
export const takes = (b: Block): readonly (keyof Coat)[] => {
  const school: (keyof Coat)[] = b.type === "ruling" ? (RULINGS[kindOf(b.props.kind)].zones ? ["font", "rule", "trace", "fade", "house", "houseTint", "band", "bandColor"] : RULINGS[kindOf(b.props.kind)].at ? ["font", "rule", "trace", "fade"] : ["rule", "trace", "fade"]) : b.type === "maths" ? (b.props.format === "written" ? ["numbering"] : ["size", "numbering"]) : [];
  return [...(isLine(b) ? (["stroke", "strokeOpacity", "strokeWidth", "dash"] as const) : b.type === "table" ? (["font", "size", "color", "align", "syllables", "tints", "tintsAcross", "rule", "trace", "fade"] as const) : (boxed(b) && LOOK) || school), "mark"];
};
// What a shape gets where the brush brings none: its fill, stroke and width must be set, and a text with no
// `valign` stands at the top, where a shape's would stand in the middle.
export const BARE: Record<string, string | number> = { fill: "none", stroke: "none", strokeWidth: 0.5, valign: "top" };
// The frames a text or a shape can have: the kinds from insert.ts, with their labels.
export const FRAME_LABELS: Record<string, string> = { rect: "Eckig", rounded: "Abgerundet", circle: "Rund", triangle: "Dreieck", star: "Stern", bubble: "Sprechblase" };
export const FRAMES: [Kind, string][] = FRAME_KINDS.map((kind) => [kind, FRAME_LABELS[kind]]);
export const DASHES = [[undefined, "Durchgezogen", "───"], ["dashed", "Gestrichelt", "╌╌╌"], ["dotted", "Gepunktet", "┈┈┈"]] as const;
export const LABELS = [[undefined, "Keine"], ["show", "Blatt"], ["key", "Lösungen"]] as const;
export const SHAPES: [Kind, string, LucideIcon][] = [
  ["rect", "Rechteck", Square],
  ["rounded", "Abgerundet", Squircle],
  ["circle", "Kreis", Circle],
  ["triangle", "Dreieck", Triangle],
  ["star", "Stern", Star],
  ["bubble", "Sprechblase", MessageSquare],
  ["line", "Linie", Minus],
  ["arrow", "Pfeil", ArrowRight],
  ["double", "Doppelpfeil", MoveHorizontal],
];
// The six ways to line blocks up: the axis, the share of the room a block leaves before it, and the name.
export const ALIGNS: [Axis, number, string, LucideIcon][] = [
  ["x", 0, "Links", AlignStartVertical],
  ["x", 0.5, "Mitte waagerecht", AlignCenterVertical],
  ["x", 1, "Rechts", AlignEndVertical],
  ["y", 0, "Oben", AlignStartHorizontal],
  ["y", 0.5, "Mitte senkrecht", AlignCenterHorizontal],
  ["y", 1, "Unten", AlignEndHorizontal],
];
export const NAMES: Record<Block["type"], string> = {
  text: "Text",
  image: "Bild",
  symbol: "Symbol",
  ruling: "Lineatur",
  suchsel: "Suchsel",
  zahlenmauer: "Zahlenmauer",
  zahlenhaus: "Zahlenhaus",
  zahlenkette: "Zahlenkette",
  pfeilbild: "Pfeilbild",
  operatorfeld: "Operatorfeld",
  rechenrad: "Rechenrad",
  rechentabelle: "Rechentabelle",
  magischesquadrat: "Magisches Quadrat",
  malquadrat: "Malquadrat",
  zerlegungsfeld: "Zerlegungsfeld",
  halbschriftlich: "Halbschriftlich rechnen",
  zehnerfeld: "Zehnerfeld",
  rechendreieck: "Rechendreieck",
  zahlenstrahl: "Zahlenstrahl",
  hunderterfeld: "Hunderterfeld",
  uhr: "Uhr",
  selbstkontrolle: "Selbstkontrolle",
  name: "Namenszeile",
  points: "Punkte",
  maths: "Rechnen",
  shape: "Form",
  table: "Tabelle",
};
export const PLURALS: Record<Block["type"], string> = {
  text: "Texte",
  image: "Bilder",
  symbol: "Symbole",
  ruling: "Lineaturen",
  suchsel: "Suchsel",
  zahlenmauer: "Zahlenmauern",
  zahlenhaus: "Zahlenhäuser",
  zahlenkette: "Zahlenketten",
  pfeilbild: "Pfeilbilder",
  operatorfeld: "Operatorfelder",
  rechenrad: "Rechenräder",
  rechentabelle: "Rechentabellen",
  magischesquadrat: "Magische Quadrate",
  malquadrat: "Malquadrate",
  zerlegungsfeld: "Zerlegungsfelder",
  halbschriftlich: "Halbschriftlich rechnen",
  zehnerfeld: "Zehnerfelder",
  rechendreieck: "Rechendreiecke",
  zahlenstrahl: "Zahlenstrahlen",
  hunderterfeld: "Hunderterfelder",
  uhr: "Uhren",
  selbstkontrolle: "Selbstkontrollen",
  name: "Namenszeilen",
  points: "Punkteblöcke",
  maths: "Rechenblöcke",
  shape: "Formen",
  table: "Tabellen",
};
// What a pick reads as: one block by its name, else a count of its units, as PowerPoint counts top-level objects (a group picked whole is one).
export function pickName(sel: Block[], blocks: Block[]): string {
  if (sel.length === 1) return NAMES[sel[0].type] ?? "Unbekannter Block";
  const groups = new Set<string>();
  const loose: Block[] = [];
  for (const b of sel) {
    const outer = b.group?.[0];
    if (outer && blocks.every((o) => o.group?.[0] !== outer || sel.includes(o))) groups.add(outer);
    else loose.push(b);
  }
  if (!loose.length) return groups.size === 1 ? "Gruppe" : `${groups.size} Gruppen`;
  if (groups.size) return `${groups.size + loose.length} Blöcke`;
  if (loose.every(isLine)) return `${loose.length} Linien`;
  const type = loose[0].type;
  return loose.every((b) => b.type === type) ? `${loose.length} ${PLURALS[type] ?? "Blöcke"}` : `${loose.length} Blöcke`;
}
// The right panel's tabs.
export const TABS = ["Format", "Ansicht", "Lernwörter"];
export const whenTurned = (heard: () => void) => {
  DRAWERS.addEventListener("change", heard);
  return () => DRAWERS.removeEventListener("change", heard);
};
export const GRIDS = [0, 5, 10, 20];
// A thumbnail's smallest and largest width in px: three in a row of the panel Seiten, or one nearly as wide as it.
export const THUMBS = [60, 200];
export const NONE: Guides = { x: [], y: [] };
// A finger that holds never rests still: within this many px of where it came down it has not moved.
export const SLOP = 10;
// The keys held during a drag, as PowerPoint reads them. Shift keeps the shape or the direction. Ctrl (Option on
// Apple) resizes about the centre and leaves a copy behind a move. Alt (Command on Apple) switches snapping off.
export const KEEP = 1;
export const CENTRE = 2;
export const LOOSE = 4;
// The frame and handles stand this far (px) outside a picked block, so they lie clear of its letters.
export const FRAME = { left: 8, top: 8, right: 8, bottom: 8 };
export const APPLE = /Mac|iPhone|iPad/.test(navigator.platform);

export const round = (n: number) => Math.round(n * 100) / 100;
// The pictures the server takes.
export const TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"];
// The grid's lines along one side of the page.
export const lines = (cell: number, max: number) => (cell ? Array.from({ length: Math.floor(max / cell) + 1 }, (_, i) => i * cell) : []);
export const idOf = (el: Element) => (el as HTMLElement).dataset.id!;
// Groups work as in PowerPoint. A block lists the groups it is in, the outermost first, so a group can hold groups.
// These are the ids with those of every block that shares an outermost group with one of them.
export const grouped = (ids: string[], bs: Block[]) => {
  const tops = new Set(bs.filter((b) => b.group && ids.includes(b.id)).map((b) => b.group![0]));
  return bs.filter((b) => ids.includes(b.id) || (b.group && tops.has(b.group[0]))).map((b) => b.id);
};
// A block the clipboards read as whole. A type this script does not know (a newer Blattomat's) is kept whole, as the sheet keeps it.
export const wholeBlock = (b?: Block) => b?.id && typeof b.type === "string" && b.props && [b.x, b.y, b.w, b.h, b.z].every(Number.isFinite);
// Copies with ids of their own. A group copied whole stays one, as a group of its own; part of a group leaves it.
// A Selbstkontrolle copied with a block it links links the copy; alone it keeps its links.
export const cloned = (from: Block[], all: Block[]) => {
  const fresh = new Map<string, string>();
  const ids = new Map(from.map((b) => [b.id, crypto.randomUUID()]));
  const whole = (g: string) => all.every((b) => !b.group?.includes(g) || from.some((f) => f.id === b.id));
  return from.map((b) => {
    const group = b.group?.filter(whole).map((g) => fresh.get(g) ?? fresh.set(g, crypto.randomUUID()).get(g)!);
    const copy = { ...b, id: ids.get(b.id)!, group: group?.length ? group : undefined } as Block;
    if (copy.type === "selbstkontrolle" && Array.isArray(copy.props.links)) copy.props = { ...copy.props, links: copy.props.links.map((id) => ids.get(id) ?? id) };
    return copy;
  });
};
export const spread = (e: TouchEvent) => Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
export const centre = (e: TouchEvent) => [(e.touches[0].clientX + e.touches[1].clientX) / 2, (e.touches[0].clientY + e.touches[1].clientY) / 2];
// Where the box around some blocks starts and ends.
export const span = (boxes: Box[], axis: Axis) => {
  const size = axis === "x" ? "w" : "h";
  return [Math.min(...boxes.map((b) => b[axis])), Math.max(...boxes.map((b) => b[axis] + b[size]))];
};
// A new block's next step along one axis: 5 mm on, or back at the margin where the page ends.
export const step = (at: number, max: number) => (at + 5 <= max ? at + 5 : Math.min(MARGIN, max));
// A page drawn small in the left panel.
export const Thumb = memo(Paper);
// A dead key on a German keyboard, by the physical key. The key left of backspace adds an acute
// accent, and with Shift a grave, and the key left of 1 adds a circumflex. The mark is what that
// key adds to the next letter.
export const DEAD: Record<string, string> = { Equal: "\u0301", Backquote: "\u0302" };
export const DEAD_SHIFT: Record<string, string> = { Equal: "\u0300" };
// Pressed twice, or followed by Space, the dead key types the accent on its own.
export const SPACING: Record<string, string> = { "\u0301": "\u00b4", "\u0300": "`", "\u0302": "^" };
export const deadMark = (e: KeyboardEvent) =>
  e.ctrlKey || e.metaKey || e.altKey ? "" : (e.shiftKey ? DEAD_SHIFT[e.code] : DEAD[e.code]) || "";

// The print variants opened in an editor loaded anew: the dialog's choice as it was, and the press that loaded it.
// `print` prints at once, Lösungen where true; `newer` says that a newer version was loaded for it.
export type Opened = { count: number; letters: boolean; print?: boolean; newer?: boolean };

// The clash bar. A PDF pressed in the clash adds its own sentence to it.
export const CLASH_BAR = "Dieses Blatt wurde in einem anderen Fenster oder auf einem anderen Gerät geändert. Wähle, welche Version gilt.";
