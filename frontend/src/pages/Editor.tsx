import {
  memo,
  useDeferredValue,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type KeyboardEvent as Key,
  type MouseEvent as Click,
  type PointerEvent,
  type ReactNode,
  type RefObject,
  type TouchEvent,
} from "react";
import { flushSync } from "react-dom";
import {
  AlignCenterHorizontal,
  AlignCenterVertical,
  AlignEndHorizontal,
  AlignEndVertical,
  AlignStartHorizontal,
  AlignStartVertical,
  ArrowRight,
  BrickWall,
  Calculator,
  ChevronLeft,
  Sigma,
  Circle,
  CircleHelp,
  ClipboardPaste,
  Copy,
  CopyPlus,
  Ellipsis,
  Eraser,
  Eye,
  Group,
  Grid3x3,
  Clock3,
  ListChecks,
  FileCheck,
  FileDown,
  FilePlus,
  FileX,
  Fullscreen,
  Layers,
  Heading,
  House,
  ImagePlus,
  Link2,
  LayoutTemplate,
  Lock,
  MessageSquare,
  LockOpen,
  Minus,
  MoveHorizontal,
  Paintbrush,
  PanelLeft,
  PanelRight,
  Plus,
  Redo2,
  RotateCcw,
  RotateCw,
  Rows3,
  Ruler,
  Scissors,
  SeparatorHorizontal,
  SeparatorVertical,
  Smile,
  Square,
  SquareDashedMousePointer,
  SquareSlash,
  Squircle,
  Star,
  Table,
  Trash2,
  Triangle,
  TriangleDashed,
  MoveRight,
  Type,
  Undo2,
  Ungroup,
  UserPen,
  X,
  ZoomIn,
  ZoomOut,
  type LucideIcon,
} from "lucide-react";
import Moveable, { type OnDrag, type OnResize, type OnRotate, type OnRotateEnd, type OnRotateGroup } from "react-moveable";
import Selecto from "react-selecto";
import { Link, useNavigate, useParams } from "react-router";
import { api, post, type Refusal, type User } from "../api";
import { DRAWERS, opening } from "../components/Blank";
import Failed from "../components/Failed";
import Feedback from "../components/Feedback";
import Logo from "../components/Logo";
import Menu, { type Item } from "../components/Menu";
import ZoomList from "../components/ZoomList";
import Tour from "../components/Tour";
import Variants, { NEWER } from "../components/Variants";
import { changed, fresh, redone, returned, undone, type Hist, type Step } from "../history";
import { TextSelection } from "prosemirror-state";
import type { EditorView } from "prosemirror-view";
import { attempt, drop as dropFault, note, status } from "../fault";
import { ask, attach, discard, flush, get, inClash, isGone, keepAsNew, newer, onNewer, open, overwrite, owe, refused, reset, set, signed, takeOwed, useSaves } from "../saves";
import { Draw, FIELDS, K, MARGIN, lengthened, keepsFractions, Mark, Numbers, PageNumber, PT, Paper, RULINGS, ScoreInput, Whole, Words, adjusted, bandOf, innerOf, pageNumbersOf, wordsIn, boxed, cleared, colsOf, dir, fadeOf, far, fitOf, handleOf, isLine, kindOf, listOf, listed, lowest, mathsHeight, numbers, overFoot, parasOf, reachOf, read, rowsOf, sizeOf, spliced, squares, stored, stepOf, sum, tailReach, tall, tied, traceOf, turned, writtenStyle, type Axis, type Block, type Box, type Corner, type Doc, type Fade, type Guides, type ImageBlock, type Kind, type List, type MathsProps, type ListMode, type Page, type PageNumbers, type Range, type RulingBlock, type Sheet, type ShapeBlock, type TableBlock, type TextProps } from "../sheet";
import { blatt, follow as growRulings, landed as carried, linked, loose as cutLoose, looseText, pasted, unshown } from "../words";
import Field, { hole, list, tint, type Marks, type Picked } from "./Field";
import { allCells, allGaps, everyNth, everyNthCell } from "../gaps";
import { made } from "../zahlenmauer";
import { pictureOf } from "../picture";
import { copied, hash, mark as markCopy, onTheWay, refused as refusedWords } from "../clip";
import { totals } from "../totals";
import { EDGE, anchorOf, beside, emptied, evened, heightsOf, merged, next, putTsv, rectOf, sized, slotsIn, spanAt, spansOf, tsvOf, unmerged, widthsOf, type Rect } from "../cells";
import { bordered, cutLines, lined, type Border } from "../borders";
import type { LineStyle, Pen } from "../edges";
import Format, { bounds, drawn, frameOf, has, hull, inked, mirrored, norm, outline, scaledGroup, sized as resized, swung } from "./Format";
import { generate, kept as keptMaths, newSeed } from "./Maths";
import { FRAMES as FRAME_KINDS, INSERTS, MATHS, filled, grown, type Fresh as Insert } from "../insert";
import { parasFromHtml } from "../pasted";
import type { Breaks } from "../syllables";

// The line a PDF gives when it fails, and the line it keeps while the sheet's change is not saved.
const pdfFault = "Das PDF konnte nicht erstellt werden.";

// A point turned by `by` degrees about `about`, in the same sense as a block turns (Format's swung).
const turnedAt = ([x, y]: [number, number], by: number, [cx, cy]: [number, number]): [number, number] => {
  const [c, s] = [Math.cos((by * Math.PI) / 180), Math.sin((by * Math.PI) / 180)];
  const [dx, dy] = [x - cx, y - cy];
  return [cx + dx * c - dy * s, cy + dx * s + dy * c];
};

type Template = { id: number; name: string; doc: Doc; group?: string };
// A new block's type and settings; `add` gives it its place.
type Fresh<B = Block> = B extends Block ? Pick<B, "type" | "props"> : never;

const SIDES = { top: true, left: true, bottom: true, right: true, center: true, middle: true };
const CORNERS = ["nw", "ne", "sw", "se"];
// The look the brush carries from a text or a shape to the next. A line gives and takes its stroke alone, a table
// what its cells have and the colour of its lines, `rule`, a Lineatur its script, the colour of its lines, `rule`
// too, and its Nachspuren, `trace`, and a maths block its size and the numbering of its exercises. A Lineatur 1, 2 or 3 also
// gives and takes its houses, `house` and `houseTint`, and its middle band, `band` and `bandColor`. Every block
// gives and takes the numbering before it, `mark`. The Silbenbögen and the Silbenfarbe go along, `syllables`, `tints`
// and `tintsAcross`, but not the words split by hand, `breaks`: they belong to the words.
const LOOK = ["font", "size", "bold", "italic", "underline", "color", "spacing", "align", "valign", "syllables", "tints", "tintsAcross", "trace", "fade", "fill", "opacity", "stroke", "strokeOpacity", "strokeWidth", "dash"] as const;
// The part of it that belongs to the words, with the breaks set by hand, the gaps and the solution words, and the
// Schüttelwörter with their settings: a line takes none of these.
const WORDS: string[] = ["font", "size", "bold", "italic", "underline", "color", "spacing", "align", "valign", "syllables", "tints", "tintsAcross", "breaks", "gapWidth", "bank", "mix", "mixFirst", "mixCaps", "mixLine", "list", "listCols", "holes", "holeSeed"];
type Coat = Partial<TextProps> & { mark?: string; rule?: string; trace?: boolean | "outline" | "dotted"; fade?: Fade; numbering?: string; house?: boolean; houseTint?: "room" | "all"; band?: boolean; bandColor?: string };
// Karo is always in print, and a written exercise is as large as its squares: they have no script and no size.
const takes = (b: Block): readonly (keyof Coat)[] => {
  const school: (keyof Coat)[] = b.type === "ruling" ? (RULINGS[kindOf(b.props.kind)].zones ? ["font", "rule", "trace", "fade", "house", "houseTint", "band", "bandColor"] : RULINGS[kindOf(b.props.kind)].at ? ["font", "rule", "trace", "fade"] : ["rule", "trace", "fade"]) : b.type === "maths" ? (b.props.format === "written" ? ["numbering"] : ["size", "numbering"]) : [];
  return [...(isLine(b) ? (["stroke", "strokeOpacity", "strokeWidth", "dash"] as const) : b.type === "table" ? (["font", "size", "color", "align", "syllables", "tints", "tintsAcross", "rule", "trace", "fade"] as const) : (boxed(b) && LOOK) || school), "mark"];
};
// What a shape gets where the brush brings none: its fill, stroke and width must be set, and a text with no
// `valign` stands at the top, where a shape's would stand in the middle.
const BARE: Record<string, string | number> = { fill: "none", stroke: "none", strokeWidth: 0.5, valign: "top" };
// The frames a text or a shape can have: the kinds from insert.ts, with their labels.
const FRAME_LABELS: Record<string, string> = { rect: "Eckig", rounded: "Abgerundet", circle: "Rund", triangle: "Dreieck", star: "Stern", bubble: "Sprechblase" };
const FRAMES: [Kind, string][] = FRAME_KINDS.map((kind) => [kind, FRAME_LABELS[kind]]);
const DASHES = [[undefined, "Durchgezogen", "───"], ["dashed", "Gestrichelt", "╌╌╌"], ["dotted", "Gepunktet", "┈┈┈"]] as const;
const LABELS = [[undefined, "Keine"], ["show", "Blatt"], ["key", "Lösungen"]] as const;
const SHAPES: [Kind, string, LucideIcon][] = [
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
const ALIGNS: [Axis, number, string, LucideIcon][] = [
  ["x", 0, "Links", AlignStartVertical],
  ["x", 0.5, "Mitte waagerecht", AlignCenterVertical],
  ["x", 1, "Rechts", AlignEndVertical],
  ["y", 0, "Oben", AlignStartHorizontal],
  ["y", 0.5, "Mitte senkrecht", AlignCenterHorizontal],
  ["y", 1, "Unten", AlignEndHorizontal],
];
const NAMES: Record<Block["type"], string> = {
  text: "Text",
  image: "Bild",
  symbol: "Symbol",
  ruling: "Lineatur",
  suchsel: "Suchsel",
  zahlenmauer: "Zahlenmauer",
  zahlenhaus: "Zahlenhaus",
  zahlenkette: "Zahlenkette",
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
const PLURALS: Record<Block["type"], string> = {
  text: "Texte",
  image: "Bilder",
  symbol: "Symbole",
  ruling: "Lineaturen",
  suchsel: "Suchsel",
  zahlenmauer: "Zahlenmauern",
  zahlenhaus: "Zahlenhäuser",
  zahlenkette: "Zahlenketten",
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
function pickName(sel: Block[], blocks: Block[]): string {
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
const TABS = ["Format", "Ansicht", "Lernwörter"];
const whenTurned = (heard: () => void) => {
  DRAWERS.addEventListener("change", heard);
  return () => DRAWERS.removeEventListener("change", heard);
};
const GRIDS = [0, 5, 10, 20];
// A thumbnail's smallest and largest width in px: three in a row of the panel Seiten, or one nearly as wide as it.
const THUMBS = [60, 200];
const NONE: Guides = { x: [], y: [] };
// A finger that holds never rests still: within this many px of where it came down it has not moved.
const SLOP = 10;
// The keys held during a drag, as PowerPoint reads them. Shift keeps the shape or the direction. Ctrl (Option on
// Apple) resizes about the centre and leaves a copy behind a move. Alt (Command on Apple) switches snapping off.
const KEEP = 1;
const CENTRE = 2;
const LOOSE = 4;
// The frame and handles stand this far (px) outside a picked block, so they lie clear of its letters.
const FRAME = { left: 8, top: 8, right: 8, bottom: 8 };
const APPLE = /Mac|iPhone|iPad/.test(navigator.platform);

const round = (n: number) => Math.round(n * 100) / 100;
// The pictures the server takes.
const TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"];
// The grid's lines along one side of the page.
const lines = (cell: number, max: number) => (cell ? Array.from({ length: Math.floor(max / cell) + 1 }, (_, i) => i * cell) : []);
const idOf = (el: Element) => (el as HTMLElement).dataset.id!;
// Groups work as in PowerPoint. A block lists the groups it is in, the outermost first, so a group can hold groups.
// These are the ids with those of every block that shares an outermost group with one of them.
const grouped = (ids: string[], bs: Block[]) => {
  const tops = new Set(bs.filter((b) => b.group && ids.includes(b.id)).map((b) => b.group![0]));
  return bs.filter((b) => ids.includes(b.id) || (b.group && tops.has(b.group[0]))).map((b) => b.id);
};
// A block the clipboards read as whole. A type this script does not know (a newer Blattomat's) is kept whole, as the sheet keeps it.
const wholeBlock = (b?: Block) => b?.id && typeof b.type === "string" && b.props && [b.x, b.y, b.w, b.h, b.z].every(Number.isFinite);
// Copies with ids of their own. A group copied whole stays one, as a group of its own; part of a group leaves it.
// A Selbstkontrolle copied with a block it links links the copy; alone it keeps its links.
const cloned = (from: Block[], all: Block[]) => {
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
const spread = (e: TouchEvent) => Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
const centre = (e: TouchEvent) => [(e.touches[0].clientX + e.touches[1].clientX) / 2, (e.touches[0].clientY + e.touches[1].clientY) / 2];
// Where the box around some blocks starts and ends.
const span = (boxes: Box[], axis: Axis) => {
  const size = axis === "x" ? "w" : "h";
  return [Math.min(...boxes.map((b) => b[axis])), Math.max(...boxes.map((b) => b[axis] + b[size]))];
};
// A new block's next step along one axis: 5 mm on, or back at the margin where the page ends.
const step = (at: number, max: number) => (at + 5 <= max ? at + 5 : Math.min(MARGIN, max));
// A page drawn small in the left panel.
const Thumb = memo(Paper);

// `wait` is the loading page, which the app draws while this script loads too. `first` is the sheet as the app
// asked for it meanwhile, null where it is not there, or "failed" where the load failed.
export default function Editor({ user, wait, first }: { user: User; wait: ReactNode; first: ReturnType<typeof get> }) {
  const { id } = useParams();
  // undefined while the sheet is loading, null when it is not there. `n` counts the loads.
  // `variants` opens the print variants in a sheet loaded anew for them.
  const [file, setFile] = useState<{ sheet: Sheet | null | "failed"; n: number; variants?: Opened }>();
  const show = (sheet: Sheet | null | "failed") => setFile((was) => ({ sheet, n: (was?.n ?? 0) + 1 }));
  // The tries after a load that failed. Each asks anew, with the loading page up meanwhile.
  const [tries, setTries] = useState(0);
  const retry = () => {
    setFile(undefined);
    setTries((n) => n + 1);
  };
  const here = useRef(true);
  // A PDF pressed in a clash, Lösungen where true: it comes once the teacher has chosen, also in the editor a load starts anew.
  const waiting = useRef<boolean | undefined>(undefined);
  useEffect(() => {
    here.current = true;
    return () => void (here.current = false);
  }, []);

  // The other version of a clash: the saver starts over from it. An answer that comes when the teacher has gone on,
  // or has chosen this version meanwhile, changes nothing. Either choice may find the sheet deleted elsewhere, which
  // ends the clash in the choice of a deleted sheet, or the session gone or another account's, which brings the
  // login and keeps the change for its owner. Any other failure, and no answer after 20 s, says so and leaves the
  // choice: the kept change is dropped only once the other version has come. While a choice is under way the banner
  // says so and takes no second press, and it stops saying so with whatever the choice ends in.
  const [choice, setChoice] = useState<"busy" | "failed">();
  const ended = (end: "failed" | void) => void (here.current && setChoice(end || undefined));
  // The two answers to a sheet deleted elsewhere: what shows becomes a new sheet, which opens, or it is dropped.
  const navigate = useNavigate();
  const keep = () => void keepAsNew(Number(id)).then((sheet) => {
    if (!sheet || sheet === "failed") return;
    dropFault(pdfFault);
    navigate(`/blatt/${sheet.id}`);
  });
  // Only from the dead sheet's own address: the teacher may have gone on while the server was asked.
  const drop = () => void discard(Number(id)).then((gone) => gone && location.pathname === `/blatt/${id}` && navigate("/"));
  function load() {
    setChoice("busy");
    ask<Sheet>(`/sheets/${id}`).then(
      (sheet) => {
        ended();
        dropFault(pdfFault);
        const other = here.current && reset(sheet);
        if (other) show(other);
      },
      (e: Error) => ended(refused(Number(id), e)),
    );
  }
  function over() {
    setChoice("busy");
    overwrite(Number(id)).then((end) => {
      // Where this version took the other's place: what shows is what the next PDF prints.
      if (!inClash(Number(id)) && !isGone(Number(id))) dropFault(pdfFault);
      ended(end);
    });
  }
  // The newer sheet of another window is shown where this window has no change of its own (#720).
  // At once: the saver is the new sheet's already, and a key typed into the old editor meanwhile would be lost.
  const renew = (sheet: Sheet, variants?: Opened) => void (here.current && flushSync(() => setFile((was) => ({ sheet, n: (was?.n ?? 0) + 1, variants }))));
  // The sheet's saver says what shows: the answer, or a change that is still unsaved. An answer that comes when the
  // teacher has gone on is not for the saver either, nor is the late answer of a try before this one. A change the
  // browser kept waits through a load that failed, and shows with the try that brings the sheet.
  useEffect(() => {
    let on = true;
    (tries ? get(id!) : first).then((sheet) => on && show(sheet && sheet !== "failed" ? open(sheet) : sheet));
    return () => void (on = false);
  }, [first, tries]);

  if (file === undefined) return wait;
  if (file.sheet === "failed") return <main><Failed retry={retry}><h1>Das Blatt konnte nicht geladen werden</h1></Failed></main>;
  if (!file.sheet) return <main><h1>Blatt nicht gefunden</h1></main>;
  // A sheet loaded anew starts the editor over.
  return <Canvas key={file.n} file={file.sheet} user={user} reload={load} over={over} choice={choice} asNew={keep} discard={drop} renew={renew} opened={file.variants} waiting={waiting} />;
}

// The print variants opened in an editor loaded anew: the dialog's choice as it was, and the press that loaded it.
// `print` prints at once, Lösungen where true; `newer` says that a newer version was loaded for it.
type Opened = { count: number; letters: boolean; print?: boolean; newer?: boolean };

// The clash bar. A PDF pressed in the clash adds its own sentence to it.
const CLASH_BAR = "Dieses Blatt wurde in einem anderen Fenster oder auf einem anderen Gerät geändert. Wähle, welche Version gilt.";

function Canvas({ file, user, reload, over, choice, asNew, discard, renew, opened, waiting }: { file: Sheet; user: User; reload: () => void; over: () => void; choice?: "busy" | "failed"; asNew: () => void; discard: () => void; renew: (sheet: Sheet, variants?: Opened) => void; opened?: Opened; waiting: RefObject<boolean | undefined> }) {
  // The saver has brought an old document up to date.
  const [hist, draw] = useState<Hist>(() => ({ past: [], doc: file.doc, future: [] }));
  // The same as it stands after every change so far, drawn or not: a change knows at once what the one before left.
  const live = useRef(hist);
  const setHist = (step: (h: typeof hist) => typeof hist) => draw((live.current = step(live.current)));
  // A Lineatur on lines stored too short for its text grows to its rows once the fonts are in, as a Karo does on
  // load. No step to undo: the sheet opens so.
  useEffect(() => {
    document.fonts.ready.then(() =>
      setHist((h) => {
        const doc = lengthened(h.doc);
        return doc === h.doc ? h : { ...h, doc };
      }),
    );
  }, []);
  // Maths changes the session ran out on (saves.ts `owe`) are redone once the sheet opens after the login. The
  // clicks of one block go together, the later over the earlier, laid over the block as it is when the answer
  // comes: one request and one undo step a block. What cannot land says so.
  useEffect(() => {
    const changes = new Map<string, Partial<MathsProps>>();
    for (const { block, change } of takeOwed(file.id, user.id)) changes.set(block, { ...changes.get(block), ...change });
    const lost = "Eine Änderung an den Rechenaufgaben von vor der Anmeldung";
    const find = (block: string) => {
      const n = live.current.doc.pages.findIndex((p) => p.blocks.some((b) => b.id === block));
      const b = live.current.doc.pages[n]?.blocks.find((x) => x.id === block);
      return b?.type === "maths" ? { n, b } : undefined;
    };
    changes.forEach(async (change, block) => {
      const was = find(block);
      if (!was) return note("owed", `${lost} fand ihren Block nicht mehr und wurde nicht übernommen.`);
      const made = await generate({ ...was.b.props, ...change }).catch((e: Error) => e);
      // The session gone again keeps it owed with the red bar; another failure keeps it owed for the next opening.
      if (made instanceof Error) {
        owe(file.id, { block, change }, made.message === "401");
        if (made.message !== "401") note("owed", `${lost} konnte noch nicht übernommen werden. Öffne das Blatt später noch einmal.`);
        return;
      }
      const now = find(block);
      if (!now) return note("owed", `${lost} fand ihren Block nicht mehr und wurde nicht übernommen.`);
      const props = { ...now.b.props, ...change, ...keptMaths(now.b.props, { ...now.b.props, ...change }, made) };
      if (overFoot(now.b, props, sizeOf(live.current.doc, now.n)[1])) return note("owed", `${lost} passt nicht mehr auf die Seite und wurde nicht übernommen.`);
      turn((p) => ({ ...p, blocks: p.blocks.map((x) => (x.id === block && x.type === "maths" ? ({ ...x, props, ...tall(x, mathsHeight(props)) } as Block) : x)) }), `owed ${block}`, now.n);
    });
  }, []);
  const [title, setTitle] = useState(file.title);
  // The sheet's saver: what the server holds, whether a save failed, and whether the server holds a newer document
  // than the one this editor is based on.
  const saver = useSaves().list.find((s) => s.id === file.id);
  const named = useRef(title);
  named.current = title;
  // Loads the newer sheet of another window, where this one has no change: it says so, and shows the sheet (#720).
  // With `variants` the new editor opens the print variants. A press asks anew, so the line of a load before goes.
  async function newerSheet(variants?: Opened) {
    const sheet = await newer(file.id, () => ({ doc: live.current.doc, title: named.current }));
    if (sheet) {
      note(NEWER, NEWER);
      renew(sheet, variants);
    }
    return !!sheet;
  }
  // The clash bar says it all then: no second red line.
  useEffect(() => void (saver?.clash && dropFault(NEWER)), [saver?.clash]);
  // A PDF pressed in the clash waits for the choice. It prints once the choice has ended, unless the sheet is gone.
  const [pdfWaits, setPdfWaits] = useState(waiting.current !== undefined);
  useEffect(() => {
    if (saver?.clash || waiting.current === undefined) return;
    const key = waiting.current;
    waiting.current = undefined;
    setPdfWaits(false);
    if (!saver?.gone) void pdf(key);
  }, [saver?.clash, saver?.gone]);
  useEffect(() => onNewer(file.id, () => void newerSheet(dialogState.current)), []);
  useEffect(() => {
    const focus = () => void newerSheet(dialogState.current);
    addEventListener("focus", focus);
    return () => removeEventListener("focus", focus);
  }, []);
  // Whether a new guide line or grid is for the page in use alone.
  const [own, setOwn] = useState(false);
  const [at, setAt] = useState(0);
  // The pages chosen in the panel Seiten, with the page in use among them.
  const [chosen, setChosen] = useState<number[]>([]);
  // A thumbnail being dragged: the page it shows, the gap between the thumbnails it would drop into, and whether
  // the line stands after the thumbnail before that gap.
  const [haul, setHaul] = useState<{ from: number; slot: number; after: boolean }>();
  const [ids, setIds] = useState<string[]>([]);
  const [targets, setTargets] = useState<HTMLElement[]>([]);
  // The blocks that stay put. Moveable reads a selector as its first match only, so it gets the elements.
  const [rest, setRest] = useState<HTMLElement[]>([]);
  // The format painter: the look it picked up, as it was then, and whether it is on: 1 for one block, 2 until ended.
  const [coat, setCoat] = useState<Coat>();
  const [brush, setBrush] = useState(0);
  // What the words picked in a field have of their own, read before the press on the brush ends the field.
  const wet = useRef<Marks>(undefined);
  // Opens a text's field for a drag of the brush, from the latest render: the drag's listeners outlive the press.
  const openNow = useRef((_id: string, _el: Element) => {});
  const [editing, setEditing] = useState("");
  // The stone of a Zahlenmauer opened by a double click: its block, wall and stone, the number as typed, and its box in the block.
  const [stone, setStone] = useState<{ id: string; wall: number; at: number; text: string; box: number[] } | null>(null);
  // Whether the last press was a finger's, and where the handles of the picked table's range stand.
  const [finger, setFinger] = useState(false);
  const [grips, setGrips] = useState<{ corner: string; x: number; y: number }[]>([]);
  // The cell of the table being edited, counted row by row.
  const [slot, setSlot] = useState(0);
  // The far corner of a selection of cells in the table being edited, and whether a drag picks cells.
  const [reach, setReach] = useState<number | undefined>(undefined);
  const cellDrag = useRef(false);
  // A press with the brush in the open text picks its words: Moveable must not drag the block by it.
  const brushing = useRef(false);
  // The element a brush press lands on: the text under Moveable's frame, not the frame.
  const brushed = useRef<Element | undefined>(undefined);
  // The heights of the rows of the picked table as its grid laid them out, in px.
  const [laid, setLaid] = useState("");
  // Where the caret stood in a cell that a new row or column moves to another place.
  const caret = useRef<number>(undefined);
  // Where the click that opened a text's field landed, on the screen: its caret goes there.
  const clicked = useRef<[number, number]>(undefined);
  // Whether the field that opens next has all its text picked.
  const entire = useRef(false);
  // A name line's words while it is written in, and the words it was opened with.
  const [words, setWords] = useState<string[]>([]);
  const wordsKept = useRef("");
  // The name line being written in, and the page it stands on.
  const nameWriting = useRef<{ id: string; n: number } | undefined>(undefined);
  // The field of the text being edited, and what is picked in it.
  const field = useRef<EditorView>(null);
  const [part, setPart] = useState<Picked>();
  // Whether the last press was in the format panel, with no key since: the field then stays open though it loses
  // the focus, and a select or a colour picked there hands the keys back.
  const inPanel = useRef(false);
  // What is written in stays open when it loses the focus to the panel: by the keys, or by a press, which on the
  // word beside a colour names nothing that takes the focus. So does it under the bar's menu "Mehr", which hands
  // the focus back when it shuts.
  const stays = (e: { relatedTarget: EventTarget | null }) => cellDrag.current || inPanel.current || !!(e.relatedTarget as Element | null)?.closest(menu?.more || menu?.cells ? ".panel, .menu" : ".panel");
  // The text, the Lineatur or the cell being written in.
  const written = () => field.current ?? sheet.current?.querySelector<HTMLElement>("textarea:not([readonly])");
  // Gives the keys back from a control of the panel, as PowerPoint does: to what is written in, whose caret is
  // where it was, or else to the sheet.
  const back = (from: HTMLElement) => {
    const open = written();
    if (open) open.focus();
    else from.blur();
  };
  // Where an arrow, Home and End take the caret.
  const MOVES: Record<string, string[]> = {
    ArrowLeft: ["left", "character"],
    ArrowRight: ["right", "character"],
    ArrowUp: ["backward", "line"],
    ArrowDown: ["forward", "line"],
    Home: ["backward", "lineboundary"],
    End: ["forward", "lineboundary"],
  };
  // Does in what is written in what a key does there that types no letter, and says whether it did. The browser
  // still counts the key that gave the focus back as the control's: only a letter follows the focus by itself. A
  // text's field takes its own keys first, as Ctrl+B. Deleting and the caret's moves are the browser's, done by hand.
  // Any other key with Ctrl is the browser's too and follows the focus by itself, as Ctrl+X or Ctrl+Backspace.
  const act = (e: KeyboardEvent) => {
    const view = field.current;
    const mod = e.ctrlKey || e.metaKey;
    const erase = e.key === "Backspace" || e.key === "Delete";
    if (e.altKey || !(mod || erase || MOVES[e.key])) return false;
    if (view?.someProp("handleKeyDown", (f) => f(view, e))) return true;
    const key = e.key.toLowerCase();
    // Undo and redo of a text and a cell are the sheet's, as with the second key: the browser's own would run in
    // their place. A Lineatur's are the browser's.
    if (mod && (key === "z" || key === "y") && document.activeElement!.closest(".ProseMirror, .table")) {
      (key === "y" || e.shiftKey ? redo : undo)();
      return true;
    }
    // Ctrl and an arrow step by a word. A select would walk by it.
    const word = e.ctrlKey && (e.key === "ArrowLeft" || e.key === "ArrowRight");
    if (mod && !word) return false;
    if (erase) document.execCommand(e.key === "Delete" ? "forwardDelete" : "delete");
    else getSelection()!.modify(e.shiftKey ? "extend" : "move", MOVES[e.key][0], word ? "word" : MOVES[e.key][1]);
    return true;
  };
  const [multi, setMulti] = useState(false);
  // The right click's menu and where it stands: a thumbnail's with `thumb`, its page, else the one for blocks. With
  // `more` it is the bar's menu instead, of the commands the bar has no room for.
  const [menu, setMenu] = useState<{ x: number; y: number; thumb?: number; more?: boolean; cells?: boolean; cell?: number; rule?: { axis: Axis; i: number; n?: number } }>();
  const [mathMenu, setMathMenu] = useState<{ x: number; y: number }>();
  const [lens, setLens] = useState<{ x: number; y: number; up: boolean }>();
  const [tab, setTab] = useState(TABS[0]);
  // A block picked on the list's tab shows its settings, as in PowerPoint (#429).
  const idKey = ids.join();
  useEffect(() => {
    if (idKey) setTab((now) => (now === "Lernwörter" ? "Format" : now));
  }, [idKey]);
  // So does a click on a block that is picked already: the pick does not change then.
  useEffect(() => {
    if (tab !== "Lernwörter") return;
    const down = (e: Event) => {
      if (e.target instanceof Element && e.target.closest(".block") && sheet.current?.contains(e.target)) setTab("Format");
    };
    document.addEventListener("pointerdown", down, true);
    return () => document.removeEventListener("pointerdown", down, true);
  }, [tab]);
  // Whether several blocks line up with the page, not with each other.
  const [onPage, setOnPage] = useState(false);
  const [pane, setPane] = useState(true);
  // Blattform lays the editor out anew on a wide window: the left panel holds what can be inserted, and Start,
  // Ansicht and Vorlagen in the bar pick what the panels show. `side` then means that Vorlagen is open. `opening`
  // tells when the layout is that one and how the panel of pages and templates starts.
  const { leafy } = opening();
  const [side, setSide] = useState(() => opening().side);
  // Upright, at most one panel is open and both start shut. `side` and `pane` keep what the window on its side shows.
  const drawers = useSyncExternalStore(whenTurned, () => DRAWERS.matches);
  const [drawer, setDrawer] = useState<"left" | "right">();
  // The finger on a drawer's swipe: where it came down, which drawer it may open or shut, and whether it has.
  const swipe = useRef<{ x: number; y: number; open?: "left" | "right"; shut?: "left" | "right"; decided?: boolean } | undefined>(undefined);
  // Each turn upright starts with both shut.
  useEffect(() => setDrawer(undefined), [drawers]);
  const leaf = leafy && !drawers;
  const left = drawers ? drawer === "left" : side;
  const right = drawers ? drawer === "right" : pane;
  const showLeft = (on: boolean) => (drawers ? setDrawer(on ? "left" : undefined) : setSide(on));
  const showRight = (on: boolean) => (drawers ? setDrawer(on ? "right" : undefined) : setPane(on));
  // The bar is one row, and what has no room in it lies behind "Mehr": `fits` is how many of the commands that may
  // fold stay in the bar, counted from its left. While it is not known all of them are drawn in the bar, where they
  // are measured and the count is set before the browser paints.
  const bar = useRef<HTMLDivElement>(null);
  const [fits, setFits] = useState<number>();
  const feedback = useRef<() => void>(null);
  // "Mehr" leaves the bar while it is measured, and the focus with it: where the button comes back, so does the focus.
  const focused = useRef(false);
  // Under an open menu the bar waits to be measured until the menu shuts: the menu hands the focus back to the
  // button that had it, and a "Mehr" that left the bar meanwhile is no longer that button.
  const late = useRef(false);
  // A measure is asked for and not yet taken: until it is, the focus "Mehr" had is not given back and not forgotten.
  const awaited = useRef(false);
  const refit = () => {
    late.current = !!document.querySelector("dialog.menu[open]");
    if (late.current) return;
    focused.current ||= !!document.activeElement?.matches(".more");
    awaited.current = true;
    setFits(undefined);
  };
  // The bar is measured anew when its width changes, as the window's does or the iPad turns, when its type has
  // loaded, and when Blattform's layout, which has the zoom elsewhere, comes or goes. A turn has shut an open "Mehr"
  // by then, as the window's new size shuts any menu; a type that loads under an open menu has not. So it is when
  // the title changes, and when its field gains or loses the focus: the bar's width stays, and tells of none.
  // This runs before the measure below: a render that is measured and whose layout changes at once would else have
  // its count wiped after it was taken, and the bar would stay unmeasured.
  useLayoutEffect(refit, [leaf, title]);
  useLayoutEffect(() => {
    if (fits !== undefined) {
      if (awaited.current) return;
      if (focused.current) bar.current!.querySelector<HTMLElement>(".more")?.focus();
      focused.current = false;
      return;
    }
    awaited.current = false;
    const row = bar.current!;
    const look = getComputedStyle(row);
    const may = [...row.querySelectorAll(".sep ~ :is(.ib, .zoom):not(.pin)")];
    const widths = may.map((el) => el.getBoundingClientRect().width + parseFloat(look.columnGap));
    // How far the row runs past the bar's end, and how much of the hint it has squeezed away before that.
    const hint = row.querySelector(".hint")!;
    let over = row.querySelector(".pdf")!.getBoundingClientRect().right + parseFloat(look.paddingRight) - row.getBoundingClientRect().right + hint.scrollWidth - hint.clientWidth;
    // The title gives way first, so the row may end in the bar with the title cut: what it lacks counts too, up to
    // the most a title may take. While it is edited that is all of it, and `none` is no number. Safari counts a
    // whole title a pixel wider than its field: that is no lack.
    const name = row.querySelector("input")!;
    const lack = name.scrollWidth - name.clientWidth;
    if (lack > 1) over += Math.min(lack, (parseFloat(getComputedStyle(name).maxWidth) || Infinity) - name.offsetWidth);
    let n = may.length;
    // A phone's bar wraps and keeps them all.
    if (look.flexWrap === "nowrap" && over > 0.5) {
      // "Mehr" needs the room of one of them.
      over += widths[0];
      while (n && over > 0.5) over -= widths[--n];
      // The zoom's four stay or go together.
      const lens = may.findIndex((el) => el.matches(".zoom"));
      if (lens > 0 && n >= lens && n < lens + 3) n = lens - 1;
    }
    setFits(n);
  });
  useLayoutEffect(() => {
    // Before the browser paints the bar at its new width.
    const again = () => flushSync(refit);
    const watch = new ResizeObserver(again);
    watch.observe(bar.current!);
    document.fonts.ready.then(again);
    return () => watch.disconnect();
  }, []);
  // The tour opens by itself the first time the editor does on this device.
  const [tour, setTour] = useState(() => !localStorage.getItem("tour"));
  // Whether the maths exercises show their answers.
  const [solved, setSolved] = useState(false);
  const [mod, setMod] = useState(0);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [name, setName] = useState("");
  // The x and y, in mm, that a line's end or a group's corner has snapped to.
  const [guide, setGuide] = useState<(number | undefined)[]>([]);
  // Crop mode: the picture being cropped and the cut its frame shows, stored only when the mode ends.
  const [draft, setDraft] = useState<{ id: string; cut: number[] }>();
  // The desk's width in pixels. The widest page fills it; zoom multiplies that.
  const [room, setRoom] = useState(210);
  // The desk's height in pixels, which a fit follows too.
  const [high, setHigh] = useState(0);
  const [zoom, setZoom] = useState(1);
  // Set by Ganze Seite, cleared by a zoom by hand: while it is set, a new size of the desk fits the page again.
  const fitted = useRef(false);
  // The page in use when Ganze Seite was pressed, and a count that makes each press a change to draw.
  const fitOn = useRef(0);
  const [fitTick, setFitTick] = useState(0);
  // A thumbnail's width in px.
  const [thumb, setThumb] = useState(97);
  // Space held makes the pointer a hand, and a drag with it moves the desk. The drag may outlast the key.
  const [pan, setPan] = useState(false);
  const [panning, setPanning] = useState(false);
  // Where the hand's drag began: the pointer, and the desk's scroll.
  const hand = useRef([0, 0, 0, 0]);
  // Space pressed on a picked text, shape, table or Lineatur: opens it at the keyup, unless the hand dragged meanwhile.
  const spaced = useRef<(() => void) | null>(null);
  // The block, and the cell, that Text bearbeiten opens a moment later. A key typed before opens it at once (#640).
  const asked = useRef<{ id: string; cell?: number }>(undefined);
  useEffect(() => {
    if (editing) asked.current = undefined;
  }, [editing]);
  const stage = useRef<HTMLDivElement>(null);
  const desk = useRef<HTMLDivElement>(null);
  // Moves the desk by a drag from where hand.current says: the hand and the middle button share it.
  const dragDesk = (e: { clientX: number; clientY: number }) => {
    desk.current!.scrollLeft = hand.current[2] - (e.clientX - hand.current[0]);
    desk.current!.scrollTop = hand.current[3] - (e.clientY - hand.current[1]);
  };
  // The middle button pans the desk while it is held, over a block too. The window hears the moves and the lift.
  const middlePan = (x: number, y: number) => {
    hand.current = [x, y, desk.current!.scrollLeft, desk.current!.scrollTop];
    setPanning(true);
    const move = (e: { clientX: number; clientY: number; buttons: number }) => {
      if (!(e.buttons & 4)) return stop();
      steer();
      dragDesk(e);
    };
    const stop = () => {
      setPanning(false);
      removeEventListener("pointermove", move);
      removeEventListener("pointerup", stop);
      removeEventListener("pointercancel", stop);
    };
    addEventListener("pointermove", move);
    addEventListener("pointerup", stop);
    addEventListener("pointercancel", stop);
  };
  // An open Format drawer lies over the sheet's right end. The desk scrolls so the picked block, or the caret in the
  // open text, stays in view beside it: the drawer shows the room on the desk's right, see `.drawn` in styles.css.
  const drawnRight = drawers && drawer === "right";
  // The desk's scroll before the drawer moved it: shutting the drawer puts it back.
  const scrolledFrom = useRef<number | undefined>(undefined);
  useLayoutEffect(() => {
    const el = desk.current;
    if (!drawnRight) {
      if (el && scrolledFrom.current !== undefined) el.scrollLeft = scrolledFrom.current;
      scrolledFrom.current = undefined;
      return;
    }
    const panel = document.querySelector("aside.panel");
    if (!el || !panel || !ids.length) return;
    // The part to keep in view, as its left and right edges on the window.
    let rect: { left: number; right: number } | undefined;
    if (editing) {
      const caret = getSelection()?.rangeCount ? getSelection()!.getRangeAt(0).getBoundingClientRect() : undefined;
      // A caret at the end of a line may have no size: then the text's box stands in for it.
      rect = caret && (caret.width || caret.height) ? caret : document.querySelector(`.block[data-id="${editing}"]`)?.getBoundingClientRect();
    } else {
      const boxes = ids.map((id) => document.querySelector(`.block[data-id="${id}"]`)?.getBoundingClientRect()).filter((b): b is DOMRect => !!b);
      if (boxes.length) rect = { left: Math.min(...boxes.map((b) => b.left)), right: Math.max(...boxes.map((b) => b.right)) };
    }
    if (!rect) return;
    // Scroll until the part clears the panel's left edge with a gap, but no further than the desk's own left edge allows.
    const gap = 16;
    const dx = rect.right - (panel.getBoundingClientRect().left - gap);
    const by = dx > 0 ? Math.max(0, Math.min(dx, rect.left - (el.getBoundingClientRect().left + gap))) : 0;
    if (by > 0) {
      scrolledFrom.current = el.scrollLeft;
      el.scrollLeft += by;
    }
  }, [drawnRight]);
  const sheet = useRef<HTMLDivElement>(null);
  const moveable = useRef<Moveable>(null);
  const picker = useRef<HTMLInputElement>(null);
  const mergeKey = useRef("");
  // For Escape to call a drag off: what redo held when the drag began, and the handle the pointer holds, with the
  // crop's frame as it was then, which is in no undo step.
  const ahead = useRef<Step[]>([]);
  const grasp = useRef<{ el: Element; id: number; draft: typeof draft }>(undefined);
  // Set by a change that can leave a text higher than its box.
  const tight = useRef(false);
  // Whether that measure may also bring a table down: only after a text change in a table that had no spare room.
  const sink = useRef(false);
  const touch = useRef(false);
  // Set by a press on Moveable's box over the selection, not on a block.
  const cover = useRef(false);
  const hold = useRef(0);
  const held = useRef(false);
  // Where the finger of a hold or a drag came down.
  const came = useRef([0, 0]);
  // Whether that finger has left its SLOP since it came down, and what it came down on.
  const away = useRef(false);
  const downOn = useRef<Element>(null);
  // What Moveable said of a drag while the finger had not yet left there.
  const owed = useRef<OnDrag[]>(undefined);
  // The thumbnails, and the press on one of them: where it began, and its gap once it is a drag.
  const strip = useRef<HTMLDivElement>(null);
  const tug = useRef<{ from: number; x: number; y: number; slot?: number; held?: boolean; left?: boolean }>(undefined);
  const press = useRef(0);
  // The panel scrolls while a drag rests near its edge: the frame that does it, its speed and the pointer.
  const auto = useRef({ frame: 0, speed: 0, x: 0, y: 0, last: 0, rest: 0 });
  // Set by a drag, for the click that follows it.
  const dragged = useRef(false);
  const grab = useRef([0, 0]);
  // The pointer that holds an adjust handle, for a browser that would not capture it.
  const adjusting = useRef<number>(undefined);
  const spot = useRef<number[]>(undefined);
  const start = useRef<Block[]>([]);
  // The middle a turn went about, by the blocks of the thing as each turn left them; and the middles of the drag now.
  const pivots = useRef(new Map<string, [number, number]>());
  const dragFrom = useRef<Block[]>(undefined);
  const dragAt = useRef(new Map<string, [number, number] | undefined>());
  const pinch = useRef({ spread: 1, zoom: 1, x: 0, y: 0 });

  const { pages, guides, grid } = hist.doc;
  // The sheet's Lernwörter, the same list until the sheet's own changes.
  const learnt = useMemo(() => wordsIn(hist.doc), [hist.doc.words]);
  // How many of them the most crowded Lineatur of the sheet cannot show.
  const lineaturen = useMemo(() => pages.flatMap((p) => p.blocks).filter((b): b is RulingBlock => b.type === "ruling"), [pages]);
  const crowded = unshown(lineaturen, learnt);
  // One page is in use: it holds the selection, and new and pasted blocks land on it. Undo can take it away.
  const page = Math.min(at, pages.length - 1);
  // The choice: the pages chosen when the page in use is among them, else that page alone.
  const chosenNow = chosen.includes(page) ? chosen : [page];
  const choiceOf = (n: number) => (chosenNow.includes(n) ? chosenNow : [n]);
  const { blocks } = pages[page];
  // Each page's width and height in mm.
  const sizes = pages.map((_, n) => sizeOf(hist.doc, n));
  // A mend holds for the word in every block of the sheet, in one step: it stands in the sheet, and in the block it was
  // made in, which takes it along when copied; the other blocks' own entries for it go. Counts undefined takes the word
  // back to the module's own split everywhere.
  // `keys` are the word's key and its old key: the panel has the splitter that makes them, the editor loads none.
  function mendWord(keys: string[], counts: number[] | undefined, id: string) {
    const rest = (own?: Breaks) => Object.fromEntries(Object.entries(own ?? {}).filter(([key]) => !keys.includes(key)));
    update((doc) => {
      const base = { ...doc };
      delete base.breaks;
      const mended = counts ? { ...rest(doc.breaks), [keys[0]]: counts } : rest(doc.breaks);
      if (Object.keys(mended).length) base.breaks = mended;
      const pages = doc.pages.map((p) => ({
        ...p,
        blocks: p.blocks.map((b) => {
          const own = (b.props as { breaks?: Breaks }).breaks;
          const here = b.id === id && counts;
          if (!own && !here) return b;
          const props = { ...b.props } as Record<string, unknown>;
          delete props.breaks;
          const kept = here ? { ...rest(own), [keys[0]]: counts } : rest(own);
          if (Object.keys(kept).length) props.breaks = kept;
          return { ...b, props } as Block;
        }),
      }));
      return { ...base, pages };
    });
  }
  // Page numbers are sheet-wide. A change turns them on and keeps the rest; "Aus" turns them off and keeps the rest too.
  const folio = pageNumbersOf(hist.doc);
  // A click on what is already set makes no step to undo.
  const numbering = (change: Partial<PageNumbers>, on = true) => {
    const next = { ...folio, ...change, on };
    if (Object.entries(next).every(([key, value]) => folio[key as keyof typeof folio] === value)) return;
    update((doc) => ({ ...doc, pageNumbers: next }));
  };
  const [W, H] = sizes[page];
  // Pixels per mm when the widest page fills the desk's width.
  const widest = Math.max(...sizes.map(([w]) => w));
  const fit = room / widest;
  // The page count and the widest width as they were last. A page that goes or comes along with a new widest width
  // scales the zoom by the ratio, so the shown size stays. A page turned Quer keeps the zoom.
  const last = useRef({ count: pages.length, widest });
  useLayoutEffect(() => {
    const before = last.current;
    last.current = { count: pages.length, widest };
    if (before.count !== pages.length && before.widest !== widest) setZoom((z) => Math.min(4, Math.max(0.25, z * (widest / before.widest))));
  }, [pages.length, widest]);
  // The thumbnails draw after the desk, so a drag stays quick.
  const small = useDeferredValue(hist.doc);
  const cellOf = (p: Page) => p.grid ?? grid;
  const cell = cellOf(pages[page]);
  const mine = pages[page].guides ?? NONE;
  // Read here and not from the saver alone, which hears of a change only after it is drawn.
  const dirty = !saver || saver.unsaved || hist.doc !== saver.saved.doc || title !== saver.saved.title;
  const loose = (mod & LOOSE) > 0;
  const k = fit * zoom;
  // A zoom by hand: the buttons, the wheel, a pinch. It stays between a quarter and four times the page's width.
  const zoomTo = (z: number) => {
    fitted.current = false;
    setZoom(Math.min(4, Math.max(0.25, z)));
  };
  const sel = blocks.filter((b) => ids.includes(b.id));
  // The panel's lock, kept by each block: on when every picked block keeps its ratio. A new width then sets the height
  // to match, in the fields and on the handles. Switching it is one step.
  const lock = sel.length > 0 && sel.every((b) => b.keep);
  function setLock(on: boolean) {
    place(sel.map((b): [string, Partial<Box>] => [b.id, { keep: on || undefined }]));
  }
  // Where the panel's X and Y count from. Not in the sheet, and kept while the picks change.
  const [from, setFrom] = useState<"corner" | "centre">("corner");
  // What may be deleted, cut, moved, sized, turned and written in, as in PowerPoint: no locked block, and no block of
  // a group with a locked one, picked whole or in part. Such a group stays as a whole, so it keeps its shape.
  // A format still goes to a locked block, and its box follows where the content needs it: the edge it starts at stays.
  // A sheet laid on its side brings it back onto the page as any other block.
  const free = sel.filter((b) => !blocks.some((o) => o.locked && (o === b || (b.group && o.group?.[0] === b.group[0]))));
  // What lines up as one thing, as in PowerPoint: a group picked whole, the outermost such, or else a block by itself.
  const thing = (b: Block) => b.group?.find((g) => blocks.every((o) => !o.group?.includes(g) || ids.includes(o.id))) ?? b.id;
  const things = [...new Set(free.map(thing))].map((t) => free.filter((b) => thing(b) === t));
  // Whether they line up among themselves.
  const among = !onPage && things.length > 1;
  // What can take another's size: a line has only its length.
  const sizable = free.filter((b) => !isLine(b));
  const ns = numbers(hist.doc);
  // The built-in templates have ids below zero; the teacher's own can be deleted.
  const kept = templates.filter((t) => t.id > 0);
  // The built-in templates' documents for their thumbnails, read once, so a thumbnail draws again only with the list.
  const builtIn = useMemo(() => templates.filter((t) => t.id < 0).map((t) => ({ ...t, shown: read(t.doc) })), [templates]);
  // What has a fill and a border. The first shows its settings; a change goes to all of them.
  const boxes = sel.filter((b) => b.type === "shape" || b.type === "text");
  const fill = boxes[0]?.props.fill ?? "none";
  const stroke = boxes[0]?.props.stroke ?? "none";
  // The block the brush picks its look up from: the first with more of a look than a numbering, or else the first.
  const source = sel.find((b) => takes(b).length > 1) ?? (sel[0] as Block | undefined);
  const rulers = sel.filter(isLine);
  // A line on its own gets a handle at each end. Moveable cannot resize a box with no height, so lines get no corner handles.
  const line = sel.length === 1 ? free.find(isLine) : undefined;
  // A table on its own can have its columns' lines moved.
  const table = sel.length === 1 && free[0]?.type === "table" ? free[0] : undefined;
  // The picture in crop mode. The draft is dropped when the selection moves on by any way but `done`.
  const cropping = sel.length === 1 && sel[0].type === "image" && sel[0].id === draft?.id ? sel[0] : undefined;
  // Picked as one group, they show one frame, as in PowerPoint: their own outlines go, and the frame lies outside them.
  const oneGroup = sel.length > 1 && (sel[0].group ?? []).some((g) => sel.every((b) => b.group?.includes(g)));
  // Moveable collapses a selection that holds a flat line, so one with a line gets its own corner handles. A turned
  // one shows them on its turned frame: they size it in its own frame, where its blocks lie level.
  // Loose blocks keep a level frame, however they are turned. A group whose blocks are turned each their own way has
  // no frame of its own to size it in, so it has none: the handles would stand off Moveable's frame round them.
  const ownFrame = oneGroup && sel.some(isLine) ? frameOf(sel) : undefined;
  const mixed = !!ownFrame && !ownFrame.turn && sel.some((b) => !isLine(b) && b.angle);
  const frame = free.length > 1 && free.length === sel.length && sel.some(isLine) && !mixed ? (ownFrame ?? { turn: 0, about: [0, 0] as [number, number], level: sel }) : undefined;
  const turnedLine = !!frame?.turn;
  // Loose blocks show the box round their turned outlines, as PowerPoint does, where their handles stand.
  const group = frame && (turnedLine ? bounds(frame.level) : hull(sel));
  // A picture, a symbol and a Hunderterfeld always keep their shape, so only their corners have handles.
  const shaped = sel.some((b) => b.type === "image" || b.type === "symbol" || b.type === "hunderterfeld");
  const keep = (mod & KEEP) > 0 || shaped || sel.some((b) => b.keep);
  // The selection's size in px. An edge has a handle too, as in PowerPoint, once the 14 px handles of its corners
  // leave room for a third. The edges come last, so they lie on top where the areas a finger can hit overlap.
  const [across, down] = [bounds(sel).w * k, bounds(sel).h * k];
  const handles = shaped ? CORNERS : [...CORNERS, ...(across < 28 ? [] : ["n", "s"]), ...(down < 28 ? [] : ["e", "w"])];
  const top = Math.max(0, ...blocks.map((b) => b.z));
  // Snap lines: the page's, the teacher's own and the grid's, then the edges and centres of the blocks that stay put.
  const still = blocks.filter((b) => !ids.includes(b.id));
  // The page's own are its margins and its centre.
  const pageXs = [MARGIN, W / 2, W - MARGIN, ...guides.x, ...mine.x, ...lines(cell, W)];
  const pageYs = [MARGIN, H / 2, H - MARGIN, ...guides.y, ...mine.y, ...lines(cell, H)];
  const xs = loose ? [] : [...pageXs, ...still.map(outline).flatMap((b) => [b.x, b.x + b.w / 2, b.x + b.w])];
  const ys = loose ? [] : [...pageYs, ...still.map(outline).flatMap((b) => [b.y, b.y + b.h / 2, b.y + b.h])];

  useLayoutEffect(() => {
    // The page that stood while the sheet loaded fills the desk, and so does this one from its first frame: the
    // observer tells the width only after that frame. A desk with no width yet leaves the page as it is.
    const look = getComputedStyle(desk.current!);
    const width = desk.current!.clientWidth - parseFloat(look.paddingLeft) - parseFloat(look.paddingRight);
    if (width > 0) setRoom(width);
    const observer = new ResizeObserver(([entry]) => {
      setRoom(entry.contentRect.width);
      setHigh(entry.target.clientHeight);
    });
    observer.observe(desk.current!);
    return () => observer.disconnect();
  }, []);
  // A fit lasts until a zoom by hand: a new size of the desk fits the page again, as Ganze Seite would. A passive
  // effect, not a layout one, so that the zoom it sets may flush.
  useEffect(() => {
    if (fitted.current) fitPage();
  }, [room, high]);
  // For a mouse the dock wraps to more rows in a narrow window: the styles keep as much room free as it is high.
  useLayoutEffect(() => {
    // Blattform has two side by side, the second once the sheet has more pages than one: the higher counts.
    const docks = [...stage.current!.querySelectorAll<HTMLElement>(".dock")];
    const observer = new ResizeObserver(() =>
      stage.current!.parentElement!.style.setProperty("--dock", `${Math.max(...docks.map((el) => el.offsetHeight))}px`),
    );
    for (const el of docks) observer.observe(el);
    return () => observer.disconnect();
  }, [leaf, pages.length > 1]);

  // Moveable needs the elements, and they exist only after the blocks render.
  useLayoutEffect(() => {
    setTargets([...sheet.current!.querySelectorAll<HTMLElement>(".block.sel")]);
    setRest([...sheet.current!.querySelectorAll<HTMLElement>(".block:not(.sel)")]);
  }, [ids, blocks.length, page]);

  useLayoutEffect(() => {
    if (!moveable.current!.isDragging()) moveable.current!.updateRect();
  }, [blocks, k]);
  // The ids whose text the page's foot cuts short: the panel warns about them.
  const [full, setFull] = useState<string[]>([]);
  // The ids whose text does not fit their shape, wherever it stands: the panel warns about them.
  const [cramped, setCramped] = useState<string[]>([]);
  // The blocks the panel resized last, and the picked shapes whose text grew them back: the panel says why they stay.
  const panelSized = useRef<string[]>([]);
  const [heldIds, setHeldIds] = useState<string[]>([]);
  const pickedKey = ids.join(" ");
  useEffect(() => {
    panelSized.current = [];
    setHeldIds([]);
  }, [pickedKey]);
  const stopped = (id: string, on: boolean) =>
    setFull((f) => (f.includes(id) === on ? f : on ? [...f, id] : f.filter((x) => x !== id)));
  // The height at which a block's lowest point meets the page's foot `H`, or Infinity when it never does. Lowest is
  // linear in the height, so one more mm gives the slope.
  const footTop = (b: Block, H: number) => {
    const at = (h: number) => lowest({ ...b, ...tall(b, h) } as Box);
    const slope = at(b.h + 1) - at(b.h);
    return slope > 0.001 ? b.h + (H - at(b.h)) / slope : Infinity;
  };
  // Whether the block ends at the page's foot. A turned block's place is rounded to 0.01 mm: it may reach a hair past.
  // One that hangs further down has a warning of its own.
  const atFoot = (b: Block) => Math.abs(footTop(b, sizeOf(hist.doc, page)[1]) - b.h) <= 0.05;
  // A circle, triangle or star with `inside` shrinks its text to its outline in place of growing.
  const shrinks = (b: Block) => {
    const shape = boxed(b);
    return shape?.inside === true && (shape.kind === "circle" || shape.kind === "triangle" || shape.kind === "star");
  };
  // How high the block's frame would be with no height set, in mm. A table's rows are each as high as their highest
  // cell when its height is not set.
  const natural = (b: Block) => {
    const frame = sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] > :is(.frame, .table)`);
    if (!frame) return undefined;
    // A turned frame would measure as high as its outline, so the block lies level for the moment.
    const block = frame.parentElement!;
    const was = block.style.transform;
    block.style.transform = "none";
    // A linked text's frame has a height of its own, which it keeps after the measure.
    const own = frame.style.height;
    frame.style.height = "auto";
    const h = Math.ceil((frame.getBoundingClientRect().height / k) * 100) / 100;
    frame.style.height = own;
    block.style.transform = was;
    return h;
  };
  // A picked text at the page's foot whose words need more room than it has: the panel warns. Told from the sheet as
  // it is, so it holds after an undo, a reload or a paste too. A shape that shrinks its text tells by `overfit`.
  useLayoutEffect(() => {
    for (const b of sel) {
      const p = boxed(b);
      if (!p || p.list === true || shrinks(b)) continue;
      const h = atFoot(b) ? natural(b) : undefined;
      stopped(b.id, h !== undefined && h > b.h + 0.05);
    }
  });
  // A box grows with its text, as a PowerPoint text box does, and never shrinks by itself. Only a change the teacher
  // makes is measured, so a sheet that opens stays as saved. The frame says how high it would be with no height
  // set; the top edge stays. The new height adds no step to undo: it belongs to the change that asked for it.
  useLayoutEffect(() => {
    if (!tight.current) return;
    tight.current = false;
    const snug = sink.current;
    sink.current = false;
    const grown = new Map<string, Partial<Block>>();
    const H = sizeOf(hist.doc, page)[1];
    // The linked texts on the page in view grow with the list too, picked or not.
    const measured = [...sel, ...blocks.filter((b) => !ids.includes(b.id) && !b.locked && boxed(b)?.list === true)];
    for (const b of measured) {
      // A circle, triangle or star with `inside` shrinks its text to its outline: it grows only by `overfit` (below).
      const shape = boxed(b);
      if (shrinks(b)) {
        // A saved shape prints as it did. The teacher's change gives a picked one the floor: its type stays at 10 pt,
        // and the grow that follows is told by `overfit` on the next draw, so the flag is set again for it.
        // A locked one cannot grow, so it keeps its old type.
        if (shape && shape.floor !== true && !b.locked && sel.some((s) => s.id === b.id)) {
          grown.set(b.id, { props: { ...b.props, floor: true } } as Partial<Block>);
          tight.current = true;
        }
        continue;
      }
      const h = natural(b);
      if (h === undefined) continue;
      const kept = b.type === "table" ? heightsOf(b.props) : undefined;
      // A table with its rows set goes back to what they need when a text in it changed, down as well. A text box
      // never shrinks by itself. No other change brings a table down: a height the teacher set holds.
      const down = snug && kept;
      // A text or a shape stops at the page's foot; a linked text and a table grow on.
      const stops = shape !== undefined && shape.list !== true;
      const top = stops ? footTop(b, H) : Infinity;
      const fit = stops ? Math.max(b.h, Math.min(h, top)) : h;
      if (down ? Math.abs(h - b.h) <= 0.05 : fit <= b.h) continue;
      // The edge the words start at stays in its place on the page, turned or not.
      grown.set(b.id, tall(b, fit));
    }
    // A font used for the first time is still on its way: the text is measured again once it is there.
    if (document.fonts.status === "loading")
      document.fonts.ready.then(() => {
        tight.current = true;
        setHist((h) => ({ ...h }));
      });
    if (!grown.size) return;
    const grow = (p: Page) => ({ ...p, blocks: p.blocks.map((b) => (grown.has(b.id) ? ({ ...b, ...grown.get(b.id) } as Block) : b)) });
    setHist((h) => ({ ...h, doc: { ...h.doc, pages: h.doc.pages.map((p, i) => (i === page ? grow(p) : p)) } }));
  });

  // A circle, triangle or star whose text is too long even at the smallest type grows downward, as a rectangle grows,
  // by the mm its inner box lacks. Only a picked one: a sheet that opens stays as saved. No step to undo of its own.
  const overfit = useRef((_id: string, _lack: { down: number; across: number; cut: boolean }) => {});
  // The block last written in.
  const wrote = useRef("");
  if (editing) wrote.current = editing;
  overfit.current = (id, { down: mm, across, cut }) => {
    const b = sel.find((x) => x.id === id);
    // The frame tells on every draw, with 0 when it fits: one that does not fit at the foot warns. Elsewhere a shape
    // warns only for a word that does not print whole.
    if (b) {
      stopped(id, (mm > 0 || across > 1) && atFoot(b));
      setCramped((c) => (c.includes(id) === cut ? c : cut ? [...c, id] : c.filter((x) => x !== id)));
    }
    // Only after a change the teacher made: the frame tells before the grow effect above takes the flag back, or once
    // the text written in it is drawn.
    const shape = b && boxed(b);
    if (!b || !shape || !(tight.current || wrote.current === id) || b.locked || (mm <= 0 && across <= 1)) return;
    // A star whose points were deepened keeps its size: its word shrinks, and the warning tells when it still does not fit (#789).
    if (shape.kind === "star" && (innerOf(shape) ?? 0.38) < 0.38) return;
    if (panelSized.current.includes(id)) setHeldIds((h) => (h.includes(id) ? h : [...h, id]));
    const H = sizeOf(hist.doc, page);
    if (across > 1) {
      // A word too wide for the inner box: the shape grows as wide as high, by the share its words and lines lack,
      // its top left corner stays, up to the foot and the page's right edge, by its outline when it is turned.
      const grownBy = (s: number) => ({ ...b, ...tall(b, Math.ceil(b.h * s * 100) / 100), w: Math.ceil(b.w * s * 100) / 100 }) as Block;
      const fits = (s: number) => lowest(grownBy(s)) <= H[1] + 0.01 && outline(grownBy(s)).x + outline(grownBy(s)).w <= H[0] + 0.01;
      // The share it lacks, or the largest that fits, found by halving: the outline's reach grows with the share.
      let [lo, s] = [1, Math.max(across, 1 + mm / b.h)];
      for (let i = 0; i < 12 && !fits(s); i++) {
        const mid = (lo + s) / 2;
        if (fits(mid)) lo = mid;
        else s = mid;
      }
      if (!fits(s)) s = lo;
      if (!(s > 1)) return;
      setHist((st) => ({ ...st, doc: { ...st.doc, pages: st.doc.pages.map((p, i) => (i === page ? { ...p, blocks: p.blocks.map((x) => (x.id === id ? ({ ...x, ...tall(x, Math.ceil(x.h * s * 100) / 100), w: Math.ceil(x.w * s * 100) / 100 } as Block) : x)) } : p)) } }));
      return;
    }
    const [up, , low] = fitOf(shape.kind, b.w, b.h, undefined, shape);
    const want = Math.ceil((b.h + mm / (1 - (up + low) / b.h)) * 100) / 100;
    const top = footTop(b, H[1]);
    const h = Math.max(b.h, Math.min(want, top));
    // At the foot there is nothing to grow: no new state, or the frame would tell again at once.
    if (h <= b.h) return;
    // A round circle stays round (#661): it grows as wide as high.
    const round = shape.kind === "circle" && b.w === b.h ? { w: h } : {};
    setHist((s) => ({ ...s, doc: { ...s.doc, pages: s.doc.pages.map((p, i) => (i === page ? { ...p, blocks: p.blocks.map((x) => (x.id === id ? ({ ...x, ...tall(x, h), ...round } as Block) : x)) } : p)) } }));
  };
  // With a finger, round handles stand at the top left and the bottom right of the picked cells, as on PowerPoint's
  // iPad. They stand on the sheet as the lines' handles do, at the cells' corners as the block's turn puts them.
  useLayoutEffect(() => {
    const page = sheet.current;
    const block = table && finger && editing === table.id ? page?.querySelector<HTMLElement>(`[data-id="${table.id}"]`) : null;
    // Measured after each draw, as the open cell's field may move the cells; set only where a place changed.
    const none = () => setGrips((was) => (was.length ? [] : was));
    if (!table || !page || !block) return none();
    const [r0, c0, r1, c1] = rectOf(table.props, slot, reach ?? slot);
    const cellAt = (r: number, c: number) => block.querySelector<HTMLElement>(`.table > div[data-cell="${anchorOf(table.props, r * table.props.cols.length + c)}"]`);
    const [first, last] = [cellAt(r0, c0), cellAt(r1, c1)];
    if (!first || !last) return none();
    // A turned cell's box on the screen has the cell's centre still: the corner lies half the cell from there, turned
    // as the block is. The sheet may be drawn larger or smaller than its own size.
    const on = page.getBoundingClientRect();
    const scale = on.width / page.offsetWidth;
    const [c, s] = dir(table);
    // The table draws its cells smaller or larger than their own size: the turned box's width tells by how much.
    const corner = (cell: HTMLElement, side: number) => {
      const box = cell.getBoundingClientRect();
      const [w, h] = [cell.offsetWidth, cell.offsetHeight];
      const drawn = box.width / (w * Math.abs(c) + h * Math.abs(s)) / scale;
      const [vx, vy] = [(side * w * drawn) / 2, (side * h * drawn) / 2];
      return { x: (box.left + box.width / 2 - on.left) / scale + vx * c - vy * s, y: (box.top + box.height / 2 - on.top) / scale + vx * s + vy * c };
    };
    const now = [
      { corner: "nw", ...corner(first, -1) },
      { corner: "se", ...corner(last, 1) },
    ];
    setGrips((was) => (JSON.stringify(was) === JSON.stringify(now) ? was : now));
  });
  // The cell that stays while a handle is dragged: the corner across from it.
  const gripFixed = useRef(0);
  // A finger on a handle picks the cells from the corner across to the cell it lies over, as a mouse drag does. The
  // open cell is that far corner's: the range is the open cell and `reach`.
  const gripDown = (e: PointerEvent<HTMLElement>, corner: string) => {
    if (!table) return;
    e.preventDefault();
    e.stopPropagation();
    cellDrag.current = true;
    const [r0, c0, r1, c1] = rectOf(table.props, slot, reach ?? slot);
    gripFixed.current = anchorOf(table.props, corner === "nw" ? r1 * table.props.cols.length + c1 : r0 * table.props.cols.length + c0);
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const gripMove = (e: PointerEvent<HTMLElement>) => {
    if (!cellDrag.current || !table) return;
    const over = document.elementsFromPoint(e.clientX, e.clientY).map((el) => el.closest<HTMLElement>("[data-cell]")).find((el) => el && el.closest(`[data-id="${table.id}"]`));
    if (!over) return;
    const at = anchorOf(table.props, +over.dataset.cell!);
    if (gripFixed.current !== slot) setSlot(gripFixed.current);
    setReach(at === gripFixed.current ? undefined : at);
  };
  const gripUp = () => {
    cellDrag.current = false;
  };
  useEffect(() => {
    const on = (e: Event) => overfit.current(idOf((e.target as HTMLElement).closest(".block")!), (e as CustomEvent<{ down: number; across: number; cut: boolean }>).detail);
    const desk = sheet.current!;
    desk.addEventListener("overfit", on);
    return () => desk.removeEventListener("overfit", on);
  }, []);

  // A ruling's field, or that of a table's cell, a score's or a name line's first word; a text's own field takes the
  // focus by itself.
  useLayoutEffect(() => {
    const area = editing ? sheet.current!.querySelector<HTMLTextAreaElement | HTMLInputElement>(`[data-id="${editing}"] :is(textarea, input)`) : null;
    area?.focus();
    // A copy, or a text put back by undo, would start with the caret before the text.
    const end = caret.current ?? area?.value.length ?? 0;
    area?.setSelectionRange(entire.current ? 0 : end, end);
    caret.current = undefined;
    // A text's field has read its click by now: its effect runs before this one.
    clicked.current = undefined;
    entire.current = false;
  }, [editing, slot]);
  // A name line's words are kept once its field ends, however it ends: a press on the sheet can end it with no blur.
  // They go to the page the line stands on. An emptied word drops its field, and with none left nothing changes.
  useEffect(() => {
    const line = nameWriting.current;
    if (editing || !line) return;
    nameWriting.current = undefined;
    const fields = words.map((w) => w.trim()).filter(Boolean);
    if (!fields.length || fields.join("\n") === wordsKept.current) return;
    if (!live.current.doc.pages[line.n]?.blocks.some((b) => b.id === line.id && b.type === "name")) return;
    turn((p) => ({ ...p, blocks: p.blocks.map((b) => (b.id === line.id ? ({ ...b, props: { ...b.props, fields } } as Block) : b)) }), "", line.n);
  });
  // A field the panel took the focus from has no blur left to end it: it ends once its block is no longer picked.
  // So does the field of a cell that undo took away with its row.
  useEffect(() => {
    if (editing && (!sel.some((b) => b.id === editing) || (table && slot >= table.props.cells.flat().length))) setEditing("");
    // A covered cell is no cell of its own: the field goes to the merged cell that covers it.
    else if (table && editing === table.id && anchorOf(table.props, slot) !== slot) setSlot(anchorOf(table.props, slot));
    // Cells picked stay picked only while their table is being edited.
    if (reach !== undefined && (!table || editing !== table.id || reach >= table.props.cells.flat().length)) setReach(undefined);
    // The handles of a table's column lines need its rows' heights where a merged cell lies over a line.
    const grid = table ? sheet.current!.querySelector(`[data-id="${table.id}"] .table`) : null;
    const rows = grid ? getComputedStyle(grid).gridTemplateRows : "";
    if (rows !== laid) setLaid(rows);
  });

  // The keys do what the latest drawing says, from the moment the editor is drawn. The listener itself stays for
  // good: one that a new drawing swaps while a key is on its way would miss that key.
  const onKey = useRef((_e: KeyboardEvent) => {});
  const onPaste = useRef((_e: ClipboardEvent) => {});
  const onDrag = useRef((_e: DragEvent) => {});
  // A drag that starts in the page, as words dragged in a field do, is the page's own: only one that comes in is taken.
  const fromPage = useRef(false);
  // The sheet and the page in use as last drawn, for what comes back from the server after them.
  const latest = useRef({ doc: hist.doc, page });
  latest.current = { doc: hist.doc, page };
  useLayoutEffect(() => {
    const press = (e: KeyboardEvent) => onKey.current(e);
    const pasted = (e: ClipboardEvent) => onPaste.current(e);
    // A dragged file, like a pasted picture, is caught on the way down, before a text's field or the browser can take it.
    const dragged = (e: DragEvent) => onDrag.current(e);
    // A font or a colour picked with the mouse in the panel gives the keys back, as in PowerPoint: to the text being
    // edited, or else to the sheet. A colour's `change` comes when its picker closes, and after the pick is set.
    // A colour reached by the keys gives them back too: only so is it for what is typed next. Who walks a select
    // with the keys keeps the focus there, and so does who sets a colour with nothing written in.
    const chosen = (e: Event) => {
      const el = e.target as HTMLElement;
      if (!el.matches(".panel select, .panel input[type=color]")) return;
      if (inPanel.current || (el.matches("input") && written())) back(el);
    };
    // Escape and Enter shut the list of a select and give the keys back. Chromium keeps the keydown of a key that
    // shuts an open list to itself, so the keyup tells. Escape goes no further: the selection stays.
    const shut = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      // A font menu's own list is open: its keys are its own.
      if ((e.key === "Escape" || e.key === "Enter") && el.matches(".panel select") && !el.hasAttribute("data-open")) back(el);
    };
    window.addEventListener("change", chosen);
    window.addEventListener("keyup", shut);
    window.addEventListener("keydown", press);
    window.addEventListener("paste", pasted, true);
    window.addEventListener("dragover", dragged, true);
    window.addEventListener("drop", dragged, true);
    const began = () => (fromPage.current = true);
    const ended = () => (fromPage.current = false);
    window.addEventListener("dragstart", began);
    window.addEventListener("dragend", ended);
    return () => {
      window.removeEventListener("dragstart", began);
      window.removeEventListener("dragend", ended);
      window.removeEventListener("change", chosen);
      window.removeEventListener("keyup", shut);
      window.removeEventListener("keydown", press);
      window.removeEventListener("paste", pasted, true);
      window.removeEventListener("dragover", dragged, true);
      window.removeEventListener("drop", dragged, true);
    };
  }, []);
  // The browser would open a dropped file in place of the editor, so a drag with files is the editor's everywhere.
  // Only the desk takes them, and not while a dialog is open. Text dragged in a field and Moveable's own drags bring
  // no files and stay as they are. The photo field of the feedback dialog takes its own.
  // A picture dragged from another web page brings no file, only its address: the same rule, for the desk alone.
  // Only an address counts (selected words bring text/html too), and never over a field, which takes it as text.
  onDrag.current = (e) => {
    const types = e.dataTransfer?.types ?? [];
    if (e.type === "drop") fromPage.current = false;
    const files = types.includes("Files");
    const inField = e.target instanceof Element && !!e.target.closest(".ProseMirror, textarea, input");
    const link = !files && !fromPage.current && !inField && types.includes("text/uri-list");
    if (!files && !link) return;
    if (files && document.querySelector("dialog:modal .pick")?.contains(e.target as Node)) return;
    e.preventDefault();
    e.stopPropagation();
    const on = desk.current!.contains(e.target as Node) && !document.querySelector("dialog:modal");
    if (e.type === "dragover") e.dataTransfer!.dropEffect = on ? "copy" : "none";
    else if (on && files) dropped([...e.dataTransfer!.files], e.clientX, e.clientY);
    else if (on) dropLink(e.dataTransfer!, e.clientX, e.clientY);
  };
  // Ctrl+V comes as the browser's paste, which alone brings a picture copied in another app. A field keeps a paste
  // of words as its own. A picture has no place in a text's, a cell's or a Lineatur's field, so it lands on the
  // sheet as from anywhere else; one that comes with words, as cells copied in Excel do, stays the field's.
  // Outside a field, words copied in another app make a text block; the editor's own bring the copied blocks.
  onPaste.current = (e) => {
    // Another account's copy: its words stay on the system's clipboard after its logout. No field or text of this account takes them.
    if (localStorage.getItem("copied") === hash((e.clipboardData?.getData("text/plain") ?? "").replace(/\r\n/g, "\n")) && !clip().length) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    if (document.querySelector("dialog:modal")) return;
    // Words with tabs, or the cells copied, spread over the table's cells from the open one on: one step of undo.
    const text = e.clipboardData?.getData("text/plain") ?? "";
    if ((e.target as HTMLElement).closest(".sheet .table textarea") && table && (text.includes("\t") || (text.includes("\n") && text.replace(/\r\n/g, "\n") === cellsCopied.current))) {
      e.preventDefault();
      e.stopPropagation();
      mergeKey.current = "";
      tight.current = true;
      sink.current = snug(table);
      change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: putTsv(table.props,[Math.floor(slot / table.props.cols.length), slot % table.props.cols.length], text) } : o)));
      return;
    }
    const field = (e.target as HTMLElement).closest(".ProseMirror, textarea, input, select");
    const picture = [...(e.clipboardData?.files ?? [])].find((f) => f.type.startsWith("image/"));
    const words = !field?.matches(".sheet .ProseMirror, .sheet textarea") || e.clipboardData!.types.includes("text/plain");
    if (field && (words || !picture || writing.current)) return;
    // The editor's own copy comes with its picture: the blocks come first.
    if (ownCopy(text.replace(/\r\n/g, "\n")) && !writing.current) {
      e.preventDefault();
      e.stopPropagation();
      paste();
      return;
    }
    if (!picture || writing.current) {
      if (writing.current || !typed(e.clipboardData?.getData("text/plain") ?? "", e.clipboardData?.getData("text/html"))) paste();
      return;
    }
    e.preventDefault();
    // The field does not take it too.
    e.stopPropagation();
    upload(picture, true);
  };
  onKey.current = (e) => {
    const target = e.target as HTMLElement;
    const select = target.matches(".panel select");
    // Shift alone is no key yet, and a key that only switches something or opens the menu is none either.
    const real = !["Shift", "Control", "Alt", "AltGraph", "Meta", "CapsLock", "NumLock", "ScrollLock", "ContextMenu"].includes(e.key);
    // A list still open keeps its keys. Chromium sends none of them here, Firefox does. A browser that does not
    // know `:open` throws.
    let list = false;
    try {
      list = select && (target.matches(":open") || target.hasAttribute("data-open"));
    } catch {
      // The list counts as shut.
    }
    // Enter in a select of the panel gives the keys back, as in PowerPoint's box of fonts. A list or a colour picker
    // opened with the mouse and shut with no pick tells nobody, and its control keeps the focus: the first key since
    // the press is then not the control's either. A colour has no key of its own while its picker is shut. A select
    // keeps the arrows, which walk it, a letter while its list is open, and Escape, whose keyup gives the keys back.
    // An arrow with Ctrl walks no select.
    const walks = e.key.startsWith("Arrow") && !e.ctrlKey && !e.metaKey;
    const first = real && inPanel.current && (select ? e.key === "Tab" || !(list || e.key === "Escape" || walks) : target.matches(".panel input[type=color]"));
    const shut = first || (select && e.key === "Enter");
    // Who walks a select of the panel with the keys keeps the focus there.
    if (real) inPanel.current = false;
    // Ctrl and + or - never zoom the browser's window, which would take the bar and the panels with it: in a field
    // or a dialog, where they zoom nothing, they type nothing either. With AltGr they type a character.
    if ((e.ctrlKey || e.metaKey) && !e.getModifierState("AltGraph") && ["+", "=", "-"].includes(e.key)) e.preventDefault();
    // Alt+Left and Alt+Right never take the browser back or forward out of the sheet, also in a text or a dialog. A
    // Mac's Option with an arrow goes by words in a text, and is no way back, so it stays.
    const turnKey = e.altKey && !e.ctrlKey && !e.metaKey && (e.key === "ArrowLeft" || e.key === "ArrowRight");
    if (turnKey && !APPLE) e.preventDefault();
    // The keys are a dialog's own while it is open.
    if (document.querySelector("dialog:modal")) return;
    if (shut) {
      const open = written();
      back(target);
      // Tab and Enter do no more. A letter goes on to what is written in, with the keypress that types it there;
      // a key of the field's that types none, as Backspace or Ctrl+Z, is done there by hand, and any other only brings
      // the caret back. With nothing written in the key goes on to the sheet.
      if (e.key === "Enter" || (open && (e.key === "Tab" || act(e)))) e.preventDefault();
      if (open || e.key === "Enter" || e.key === "Escape") return;
    }
    // Escape calls a thumbnail's drag off.
    if (e.key === "Escape" && haul) return quit();
    // Escape puts the brush down from anywhere, also from a field that keeps the key to itself, and does no more.
    if (e.key === "Escape" && brush) return setBrush(0);
    // Escape during a press makes its release no click: the block stays picked and closed.
    if (e.key === "Escape") spot.current = undefined;
    // Escape calls a move, a resize or a turn off while the pointer is still down, as in PowerPoint: the blocks are
    // back where they began, with no undo step, and what redo held stays. Moveable ends its drag with no event.
    // So it is with a handle the pointer holds: a line's end, a table's column line, a guide line, a crop's frame.
    if (e.key === "Escape" && (moveable.current?.isDragging() || grasp.current?.el.hasPointerCapture(grasp.current.id))) {
      if (moveable.current?.isDragging()) {
        // Moveable sends no end of the drag: the desk's scroll at its edge stops here.
        stopDeskScroll();
        moveable.current.stopDrag();
      } else {
        grasp.current!.el.releasePointerCapture(grasp.current!.id);
        setDraft(grasp.current!.draft);
      }
      adjusting.current = undefined;
      // A drag that has changed nothing yet has no step to take back.
      if (mergeKey.current === "drag") setHist((h) => returned(h, ahead.current));
      mergeKey.current = "";
      return;
    }
    // A text being written in keeps F6, and its own Escape, which ends the writing.
    const away = !target.closest(".ProseMirror, .sheet textarea:not([readonly])");
    // F6 walks the focus as in PowerPoint: from the sheet to the bar Einfügen, the header, the panel and back to
    // the sheet, and with Shift the other way round. Tab cannot: on the sheet it picks blocks. The browser's own
    // F6 would go to its address bar. A part that is shut, or holds nothing to press, is no stop.
    if (e.key === "F6" && away && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      const lead = (el: Element | null) => [...(el?.querySelectorAll<HTMLElement>("button:enabled, select:enabled, input:enabled") ?? [])].find((c) => c.getClientRects().length);
      const parts = ['[role=toolbar][aria-label="Einfügen"]', "header", ".panel"].map((s) => document.querySelector(s)).filter(lead);
      if (e.shiftKey) parts.reverse();
      const to = lead(parts[parts.findIndex((el) => el!.contains(target)) + 1] ?? null);
      if (to) to.focus();
      // Back on the sheet a text still open gets its caret back.
      else back(target);
      return;
    }
    // Escape on a button or a field gives the keys back, as in PowerPoint's ribbon, and the selection stays. Not on
    // a button of a menu that has just shut: it holds the focus until the menu is gone, and the key is the sheet's.
    if (e.key === "Escape" && away && target.closest("button, a, input, select") && !target.closest("dialog")) return back(target);
    // Ctrl+B, I and U alone never reach the browser while a block is selected: Chrome has shortcuts of its own on
    // them. With Shift or Alt they stay the browser's.
    const mark = (e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey;
    if (mark && /^[biu]$/i.test(e.key) && sel.length && !target.closest("input, select")) e.preventDefault();
    // In a text's field, in a table's cell, in the panel's fields for place and size, on its sliders, its checkboxes
    // and its number fields, and on its lists only undo and redo are the sheet's. A number field that holds a number
    // for the panel alone keeps them.
    const ours = (e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key) && target.closest(".ProseMirror, .table, input.mm, input.score, input[type=range], input[type=checkbox], input[type=number]:not(.own), input.typed, select, textarea.wordlist");
    // Ctrl+Shift+C copies the look of the caret's word, Ctrl+Shift+V lays it on the picked words of the text being
    // written, as in PowerPoint. The field's own copy and paste are not wanted for them. With no look picked up,
    // Ctrl+Shift+V stays the browser's paste of plain words.
    const lookKey = (e.ctrlKey || e.metaKey) && e.shiftKey && !e.altKey && e.key.toLowerCase();
    if ((lookKey === "c" || (lookKey === "v" && coat)) && target.closest(".sheet .ProseMirror")) {
      e.preventDefault();
      if (e.key.toLowerCase() === "c") dip(part?.marks);
      else wordPaint(sel.find((b) => b.id === editing)!);
      return;
    }
    if (!ours && !shut && target.closest(".ProseMirror, textarea, input, select")) return;
    // Alt+Left and Alt+Right turn the picked blocks 15° counter-clockwise and clockwise, as in PowerPoint. A locked
    // block, a table and a line on its own do not turn, as the buttons of the panel do not.
    if (turnKey) {
      e.preventDefault();
      if (sel.length && free.length === sel.length && !cropping && !sel.some((b) => b.type === "table" || (isLine(b) && thing(b) === b.id))) spin(e.key === "ArrowRight" ? 15 : -15);
      return;
    }
    // Shift+F10 and the Menu key open the menu of the selection, as in PowerPoint: at the middle of the picked blocks, or
    // with nothing picked near the corner of the page in use. A focused button keeps the key for itself.
    if (((e.key === "F10" && e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) || e.key === "ContextMenu") && !target.closest("button, a, summary, .panel, header, .dock")) {
      e.preventDefault();
      const rects = sel.map((b) => sheet.current!.querySelector(`[data-id="${b.id}"]`)?.getBoundingClientRect()).filter((r): r is DOMRect => !!r);
      const paper = document.querySelector(".sheet.on")?.getBoundingClientRect();
      const x = rects.length ? (Math.min(...rects.map((r) => r.left)) + Math.max(...rects.map((r) => r.right))) / 2 : (paper?.left ?? 0) + 20;
      const y = rects.length ? (Math.min(...rects.map((r) => r.top)) + Math.max(...rects.map((r) => r.bottom))) / 2 : (paper?.top ?? 0) + 20;
      setMenu({ x: Math.max(0, Math.min(x, innerWidth)), y: Math.max(0, Math.min(y, innerHeight)) });
      return;
    }
    // With the focus on a button or on nothing, as after Ganze Seite, a page key scrolls the desk: the browser would
    // scroll the window instead. The left strip keeps them for its own long list of pages.
    if (!target.closest(".desk, .left, .ProseMirror, input, textarea, select, .panel, .menu, dialog, [role=menu]") && /^(PageUp|PageDown|Home|End)$/.test(e.key) && !(e.ctrlKey || e.metaKey || e.altKey)) {
      e.preventDefault();
      const d = desk.current!;
      if (!sel.length) steer();
      d.scrollTop = e.key === "End" ? d.scrollHeight : e.key === "Home" ? 0 : d.scrollTop + d.clientHeight * (e.key === "PageDown" ? 0.9 : -0.9);
      // The view has moved now: the page in view is in use at once, the scroll events that follow keep it.
      if (!sel.length) inView();
      return;
    }
    // The page keys scroll the desk; with nothing picked the page that then fills the view becomes the page in use.
    if (!sel.length && /^(PageUp|PageDown|Home|End|Arrow(Up|Down|Left|Right))$/.test(e.key) && !(e.ctrlKey || e.metaKey || e.altKey)) steer();
    // A number field drops a number it refused, as on leaving it, so it shows what the undo gives back.
    if (ours && target.matches("input[type=number]")) {
      target.blur();
      target.focus();
    }
    // A letter typed with one picked text, shape, table or Lineatur opens it for writing, and the caret goes to the end
    // of its text. The focus moves in the same flush, so the browser types the key into the textarea: no preventDefault.
    // Keys that are commands, and a field, a button or the panel that keep their own, stay as they are. Space is also
    // the hand's key: on a picked block it opens it at the keyup and types the space, unless the hand dragged first.
    // A dead key, as ^ on a German keyboard, opens it too: the letter that follows makes ê there. An IME or an on-screen
    // keyboard sends 229 or "Process" for a letter, and the text comes after it as input: it opens too.
    const typed = (e.key.length === 1 || e.key === "Dead" || e.keyCode === 229 || e.key === "Process") && (e.getModifierState("AltGraph") || !(e.ctrlKey || e.metaKey || e.altKey));
    const space = e.code === "Space" && !e.ctrlKey && !e.metaKey && !e.altKey;
    // A key that comes before Text bearbeiten has opened its block opens it now, in its cell and all picked, so the
    // key replaces the text there. It went to the first cell before, after the text (#640).
    const ask = asked.current;
    if (typed && ask) {
      asked.current = undefined;
      if (!editing && free.length === 1 && free[0].id === ask.id) {
        flushSync(() => edit(ask.id, undefined, true, ask.cell));
        return;
      }
    }
    if (typed && !editing && sel.length === 1 && free.length === 1 && writable(free[0]) && !tied(free[0]) && !target.closest("button, a, summary, .panel")) {
      const id = free[0].id;
      if (space) {
        e.preventDefault();
        if (!e.repeat) {
          setPan(true);
          spaced.current = () => edit(id);
        }
        return;
      }
      flushSync(() => edit(id));
      // A key that comes while Space is still down: the space first, then the key.
      if (spaced.current) {
        spaced.current = null;
        document.execCommand("insertText", false, " ");
      }
      return;
    }
    // Space is the hand's key and does not scroll the desk, also while it repeats. A focused button keeps it as its own.
    if (space) {
      if (!target.closest("button, a, summary")) e.preventDefault();
      if (!e.repeat) setPan(true);
      return;
    }
    // An arrow moves by 1 mm, or by a grid cell, and with Shift by 10 mm. A run of them makes one undo step.
    const step = e.shiftKey ? 10 : cell || 1;
    const nudge = (dx: number, dy: number) => place(free.map((b) => [b.id, { x: round(b.x + dx * step), y: round(b.y + dy * step) }]), "nudge");
    // Ctrl+B, I and U do what the panel's buttons do.
    const flip = (name: "bold" | "italic" | "underline") => mark && sel.some(boxed) && (() => paint({ [name]: !has(sel, part, name) }));
    // Enter and F2 open the one selected block to write in it, with all its text picked, as in PowerPoint. A
    // picture is not cropped, and a locked block stays shut as it does for a double click.
    const write = sel.length === 1 && free[0] && free[0].type !== "image" && (() => edit(free[0].id, undefined, true));
    // Tab picks the next block from back to front and Shift+Tab the one before, as in PowerPoint. A group is one stop.
    const next = () => {
      const order = [...blocks].sort((a, b) => a.z - b.z);
      if (e.shiftKey) order.reverse();
      const from = order.map((b) => ids.includes(b.id)).lastIndexOf(true);
      const to = [...order.slice(from + 1), ...order].find((b) => !ids.includes(b.id));
      if (!to) return;
      done();
      const picked = grouped([to.id], blocks);
      // Drawn at once: under a narrow window's desk the panel grows with the first block picked, and the desk
      // scrolls at the height that leaves it.
      flushSync(() => setIds(picked));
      // The desk scrolls to what is picked, as in PowerPoint: a group as far as it fits, and the block itself last.
      for (const id of [...picked, to.id]) sheet.current!.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
    };
    // A button that has the focus keeps Enter and Tab. With nothing selected Tab picks the block at the back and
    // Shift+Tab the one in front.
    const plain = !target.closest("button, a");
    // Ctrl+] and Ctrl+[ step the picked blocks in the stack, with Shift to the front or the back, as in PowerPoint.
    // With Alt or AltGr the key types a character, so it is no order key.
    const order = (front: boolean) => sel.length > 0 && !e.altKey && !e.getModifierState("AltGraph") && (() => raise(front, !e.shiftKey));
    // Ctrl and + or - zoom the sheet a step, as the buttons do, and Ctrl+Alt+O fits the page, not the browser's zoom.
    // With AltGr the keys type characters, so they are no zoom keys.
    const zoomStep = (by: number) => !e.getModifierState("AltGraph") && (() => zoomBy(by));
    const fitKey = e.altKey && !e.getModifierState("AltGraph") && (() => fitPage());
    // Ctrl+V alone is not here: a key stopped on its way down brings no paste.
    const keys: Record<string, (() => void) | false | undefined> =
      e.ctrlKey || e.metaKey
        ? { z: e.shiftKey ? redo : undo, y: redo, x: cut, c: e.shiftKey ? () => dip() : copy, v: e.shiftKey && (() => daub(ids)), d: () => put(sel), a: all, g: e.shiftKey ? split : join, b: flip("bold"), i: flip("italic"), u: flip("underline"), "]": order(true), "}": order(true), "[": order(false), "{": order(false), "+": zoomStep(1), "=": zoomStep(1), "-": zoomStep(-1), o: fitKey }
        : {
            delete: remove,
            backspace: remove,
            // Escape ends a crop, or else selects nothing, as in PowerPoint. A part of one group goes back to the
            // whole group first.
            escape: cropping
              ? done
              : () => {
                  const mates = grouped(ids, blocks);
                  setIds(new Set(sel.map((b) => b.group?.[0])).size === 1 && mates.length > ids.length ? mates : []);
                  setMulti(false);
                },
            arrowleft: () => nudge(-1, 0),
            arrowright: () => nudge(1, 0),
            arrowup: () => nudge(0, -1),
            arrowdown: () => nudge(0, 1),
            enter: plain && write,
            f2: write,
            tab: plain && blocks.length > 0 && next,
          };
    // A Mac's Option+O types ø, so the key is read by its place on the keyboard.
    const run = keys[e.code === "KeyO" && e.altKey ? "o" : e.key.toLowerCase()];
    // With nothing to move the arrows scroll the desk, and Alt with an arrow stays the browser's way back.
    if (!run || (e.key.startsWith("Arrow") && (!free.length || cropping || e.altKey))) return;
    e.preventDefault();
    run();
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      setMod((e.shiftKey ? KEEP : 0) | ((APPLE ? e.altKey : e.ctrlKey) ? CENTRE : 0) | ((APPLE ? e.metaKey : e.altKey) ? LOOSE : 0));
      // Any key but a letter, which types the space before it, takes the waiting space back: Enter or F2 would open
      // the text with all of it picked, and the space would take its place.
      const letter = e.key.length === 1 && (e.getModifierState("AltGraph") || !(e.ctrlKey || e.metaKey || e.altKey));
      if (e.type === "keydown" && e.code !== "Space" && !letter) spaced.current = null;
      // Letting Space go puts the hand down. A drag that is on goes on until the pointer lifts.
      if (e.type === "keyup" && e.code === "Space") {
        setPan(false);
        const open = spaced.current;
        spaced.current = null;
        if (open) {
          flushSync(open);
          document.execCommand("insertText", false, " ");
        }
      }
    };
    const onBlur = () => {
      setMod(0);
      setPan(false);
      spaced.current = null;
      setPanning(false);
    };
    // A press anywhere, on the hand or in the panel, takes the waiting space back too.
    const onPress = () => (spaced.current = null);
    window.addEventListener("keydown", onKey);
    window.addEventListener("keyup", onKey);
    window.addEventListener("blur", onBlur);
    window.addEventListener("pointerdown", onPress, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("keyup", onKey);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("pointerdown", onPress, true);
    };
  }, []);

  useEffect(() => {
    attempt("Die Vorlagen konnten nicht geladen werden.", () => signed(api<Template[]>("/templates")).then(setTemplates));
  }, []);

  // The sheet's saver (saves.ts) saves a change two seconds after the last one, tries a failed save again, and goes
  // on when this editor has gone. It hears of each change here, and of the last one as the editor goes.
  useEffect(() => set(file.id, { doc: hist.doc, title }), [hist.doc, title]);
  useEffect(() => attach(file.id, () => ({ doc: live.current.doc, title: named.current })), []);

  // A finger on a block of a flat group starts the group's drag, as a mouse press does in `pick`. Moveable cancels
  // the touch it drags from, and React's own touch listeners are passive, so this one is set by hand.
  useEffect(() => {
    const el = desk.current!;
    function onTouch(e: globalThis.TouchEvent) {
      const id = (e.target as Element).closest<HTMLElement>(".block")?.dataset.id;
      if (e.touches.length === 1 && ids.length > 1 && ids.includes(id!)) moveable.current!.dragStart(e);
    }
    el.addEventListener("touchstart", onTouch, { passive: false });
    return () => el.removeEventListener("touchstart", onTouch);
  });
  // On the iPad held upright a swipe in from a window's edge opens that side's drawer, and a swipe of an open drawer
  // back to its edge shuts it. Only one finger counts, and only a swipe across more than a vertical one: a scroll
  // of the drawer or a drag of a block keeps its own. Set by hand, as the desk must not pan once a swipe is taken.
  useEffect(() => {
    if (!drawers) return;
    function onStart(e: globalThis.TouchEvent) {
      swipe.current = undefined;
      if (e.touches.length !== 1) return;
      const { clientX: x, clientY: y } = e.touches[0];
      const on = e.target as Element;
      const free = !on.closest(".sheet, header, aside, .dock, .moveable-control-box");
      const panel = drawer && on.closest(drawer === "left" ? "aside.left" : "aside.panel");
      const shut = panel && !on.closest("input, select, textarea, [draggable=true]") && !tug.current?.held ? drawer : undefined;
      const open = free && x <= 24 ? "left" : free && x >= innerWidth - 24 ? "right" : undefined;
      if (open || shut) swipe.current = { x, y, open, shut };
    }
    function onMove(e: globalThis.TouchEvent) {
      const s = swipe.current;
      if (!s) return;
      // A thumbnail held for the long press is dragged, not swiped: the drawer stays as it is.
      if (e.touches.length !== 1 || tug.current?.held) {
        swipe.current = undefined;
        return;
      }
      const dx = e.touches[0].clientX - s.x;
      const dy = e.touches[0].clientY - s.y;
      if (s.decided) return e.preventDefault();
      if (Math.abs(dx) <= 40 || Math.abs(dx) <= 2 * Math.abs(dy)) {
        // A scroll that runs up or down first is not a swipe.
        if (Math.abs(dy) > 40 && Math.abs(dy) > 2 * Math.abs(dx)) swipe.current = undefined;
        return;
      }
      if (s.open === "left" && dx > 0) showLeft(true);
      else if (s.open === "right" && dx < 0) showRight(true);
      else if (s.shut === "left" && dx < 0) showLeft(false);
      else if (s.shut === "right" && dx > 0) showRight(false);
      else {
        swipe.current = undefined;
        return;
      }
      s.decided = true;
      e.preventDefault();
    }
    function onEnd() {
      swipe.current = undefined;
    }
    window.addEventListener("touchstart", onStart, { passive: true });
    window.addEventListener("touchmove", onMove, { passive: false });
    window.addEventListener("touchend", onEnd);
    window.addEventListener("touchcancel", onEnd);
    return () => {
      window.removeEventListener("touchstart", onStart);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onEnd);
      window.removeEventListener("touchcancel", onEnd);
    };
  });
  // Ctrl and the wheel zoom the page about the pointer, and never the window: over the bar and the panels they do
  // nothing, and over the thumbnails they make those larger and smaller, as in PowerPoint. A trackpad's pinch comes
  // the same way. React's own wheel listener is passive, so this one is set by hand.
  useEffect(() => {
    function onWheel(e: globalThis.WheelEvent) {
      const on = e.target as Element;
      if (!e.ctrlKey && !e.metaKey) {
        // The hand lies over the desk, so a wheel on it scrolls the desk from here.
        if (on.closest(".hand")) {
          steer();
          desk.current!.scrollBy(e.deltaX, e.deltaY);
        }
        return;
      }
      e.preventDefault();
      // One notch of a mouse wheel is one step of the buttons.
      const by = 1.25 ** (-e.deltaY / 100);
      if (on.closest(".pages")) return setThumb((w) => Math.min(THUMBS[1], Math.max(THUMBS[0], w * by)));
      if (!stage.current!.contains(on)) return;
      const next = Math.min(4, Math.max(0.25, zoom * by));
      // The page under the pointer, not the one in use: the gaps between the pages do not grow with them.
      const under = document.elementsFromPoint(e.clientX, e.clientY).find((el) => el.matches(".sheet")) ?? sheet.current!;
      let page = under.getBoundingClientRect();
      const [x, y] = [(e.clientX - page.left) / k, (e.clientY - page.top) / k];
      flushSync(() => zoomTo(next));
      // Scroll the page point that was under the pointer back under it.
      page = under.getBoundingClientRect();
      // Whole px: Safari cuts a fraction off, always the same way, and the page creeps with each step.
      desk.current!.scrollBy(Math.round(page.left + x * fit * next - e.clientX), Math.round(page.top + y * fit * next - e.clientY));
    }
    window.addEventListener("wheel", onWheel, { passive: false });
    return () => window.removeEventListener("wheel", onWheel);
  });
  useEffect(() => () => cancelAnimationFrame(auto.current.frame), []);
  // A finger held on a thumbnail for half a second drags it. One that moves away before then scrolls the panel, and
  // only a listener set by hand can keep the panel still once the drag is on.
  useEffect(() => {
    const el = strip.current;
    if (!el) return;
    function onStart(e: globalThis.TouchEvent) {
      quit();
      const thumb = (e.target as Element).closest<HTMLElement>("[data-thumb]");
      if (!thumb || e.touches.length !== 1) return;
      const { clientX: x, clientY: y } = e.touches[0];
      tug.current = { from: +thumb.dataset.thumb!, x, y };
      press.current = window.setTimeout(() => {
        tug.current!.held = true;
        aim(x, y);
      }, 500);
    }
    function onMove(e: globalThis.TouchEvent) {
      if (!tug.current) return;
      if (Math.hypot(e.touches[0].clientX - tug.current.x, e.touches[0].clientY - tug.current.y) > SLOP) tug.current.left = true;
      if (tug.current.slot === undefined) {
        // No preventDefault during the hold: it would keep the panel still for the whole swipe.
        // A second finger may have come down beside the panel, where the start of a touch is not heard.
        if (e.touches.length > 1 || Math.hypot(e.touches[0].clientX - tug.current.x, e.touches[0].clientY - tug.current.y) > SLOP) quit();
        return;
      }
      e.preventDefault();
      aim(e.touches[0].clientX, e.touches[0].clientY);
      scrollEdge(e.touches[0].clientX, e.touches[0].clientY);
    }
    el.addEventListener("touchstart", onStart);
    el.addEventListener("touchmove", onMove, { passive: false });
    el.addEventListener("touchend", release);
    el.addEventListener("touchcancel", quit);
    return () => {
      el.removeEventListener("touchstart", onStart);
      el.removeEventListener("touchmove", onMove);
      el.removeEventListener("touchend", release);
      el.removeEventListener("touchcancel", quit);
    };
  });

  // Changes that share a key within one gesture (a drag, typing, a colour picker) make one undo step.
  // `to` is the page in use after the change, and `from` the one before: read as last drawn, for a block from the
  // server comes after the drawing that asked for it.
  // A change that leaves the sheet as it is, as a second press on "Seitenbreite", is none, as in PowerPoint: no undo
  // step, redo stays, and the sheet stays saved. So it is with a gesture that ends where it began.
  function update(fn: (doc: Doc) => Doc, key = "", to = page, from = latest.current.page) {
    const next = changed(live.current, { key: mergeKey.current, ahead: ahead.current }, totals(live.current.doc, fn(live.current.doc)), key, from, to);
    if (!next) {
      // A gesture under way goes on, and what it has changed is measured where its end asks for that, as a resize's.
      if (key !== "" && key === mergeKey.current) return void (tight.current && setHist((h) => ({ ...h })));
      // Any other gesture is over: the next change is a step of its own. No text has grown, so nothing is measured,
      // unless a change still waits to be drawn.
      mergeKey.current = "";
      if (live.current.doc === latest.current.doc) tight.current = sink.current = false;
      return;
    }
    ahead.current = next.gesture.ahead;
    mergeKey.current = next.gesture.key;
    // `setHist` hands its step the history as it stands, and that is what `changed` was given.
    setHist(() => next.h);
  }
  // Changes one page, the one in use unless `n` names another. Undo and redo of it show that page.
  function turn(fn: (p: Page) => Page, key?: string, n = page) {
    update((doc) => ({ ...doc, pages: doc.pages.map((p, i) => (i === n ? fn(p) : p)) }), key, n, n);
  }
  function change(fn: (blocks: Block[]) => Block[], key?: string) {
    turn((p) => ({ ...p, blocks: fn(p.blocks) }), key);
  }
  // Sets the number of a score box on page n, the page it stands on: the page in use may have changed since it was
  // opened. Nothing is changed, and no step made, when the box is not there.
  function scoreOn(id: string, max: number, n: number) {
    if (!live.current.doc.pages[n]?.blocks.some((b) => b.id === id && b.type === "points")) return;
    turn((p) => ({ ...p, blocks: p.blocks.map((b) => (b.id === id && b.type === "points" ? ({ ...b, props: { ...b.props, max } } as Block) : b)) }), "", n);
  }
  // Adds `by` to the score of each picked score box, from its own number: the panel's field shows only the first one's.
  function bump(by: number) {
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === "points" ? ({ ...b, props: { ...b.props, max: Math.min(999, Math.max(1, b.props.max + by)) } } as Block) : b)));
  }
  // The Lineatur's text: a mode links each picked Lineatur to the sheet's list, none cuts each loose with its words.
  // One step for all of them.
  function takeList(mode?: ListMode) {
    // A Lineatur being written in ends its writing: linked, it has no field left to write in.
    if (mode) setEditing("");
    // A block of a group with a locked one is as fixed as the locked one: it takes the list and does not grow.
    const fixed = sel.filter((b) => !free.includes(b)).map((b) => b.id);
    change((bs) =>
      bs.map((b) => {
        if (!ids.includes(b.id) || b.type !== "ruling") return b;
        if (!mode) return cutLoose(b, learnt);
        return fixed.includes(b.id) ? { ...b, props: { ...b.props, list: mode } } : linked(b, mode, learnt, W, H);
      }),
    );
  }
  // A text or shape takes the sheet's list, or is cut loose with the words as its own text. One step for all of them.
  function takeText(on: boolean) {
    // A text being written in ends its writing: linked, it has no field left to write in.
    if (on) setEditing("");
    tight.current = true;
    change((bs) =>
      bs.map((b) => {
        const text = boxed(b);
        if (!ids.includes(b.id) || !text || (!on && text.list !== true)) return b;
        return { ...b, props: on ? { ...b.props, list: true } : looseText(b.props as Partial<TextProps>, learnt) } as Block;
      }),
    );
  }
  // Sets the columns, the Lückenwörter and their seed of a linked text or shape. Other blocks stay as they are.
  function feed(props: object, key?: string) {
    tight.current = true;
    change(
      (bs) => bs.map((b) => (ids.includes(b.id) && boxed(b)?.list === true ? ({ ...b, props: { ...b.props, ...fresh(b, props) } } as Block) : b)),
      key,
    );
  }
  // The list field of the Lernwörter tab shows the sheet's list, one word to a line. An empty field removes the list.
  // A changed list changes every linked text on the page, which the grow effect measures. A linked ruling grows by a
  // row for each new word, in the same step.
  function listWords(value: string) {
    tight.current = true;
    update((doc) => {
      const next = { ...doc, words: value === "" ? undefined : value.split("\n") };
      const words = wordsIn(next);
      const all = doc.pages.flatMap((p) => p.blocks);
      return { ...next, pages: doc.pages.map((p, n) => ({ ...p, blocks: growRulings(p.blocks, words, sizeOf(doc, n)[0], sizeOf(doc, n)[1], all) })) };
    }, "words");
  }
  // The caret of the list field goes behind a paste once the paste is drawn, as React sets the value only then.
  const listField = useRef<HTMLTextAreaElement>(null);
  const caretAt = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (caretAt.current === undefined) return;
    listField.current?.setSelectionRange(caretAt.current, caretAt.current);
    caretAt.current = undefined;
  });
  // The Lernwörter-Blatt comes behind the page in use, and is the page in use from then on. On an empty page it fills
  // that page instead. Its size is the sheet's, or the empty page's own.
  function addBlatt() {
    const n = page;
    const empty = live.current.doc.pages[n].blocks.length === 0;
    const [w, h] = empty ? sizeOf(live.current.doc, n) : live.current.doc.landscape ? [297, 210] : [210, 297];
    // One undo step for every page of the Blatt: the first fills the empty page or comes after the page in use, the rest follow it.
    const [first, ...rest] = blatt(learnt, w, h).map((page) => page.map((b, i) => ({ ...b, id: crypto.randomUUID(), z: i + 1, locked: false }) as Block));
    if (empty) {
      // The empty page keeps what is its own, and the run-on pages lie as it does.
      const { landscape } = live.current.doc.pages[n];
      const lie = landscape === undefined ? {} : { landscape };
      update((doc) => ({ ...doc, pages: [...doc.pages.slice(0, n), { ...doc.pages[n], blocks: first }, ...rest.map((blocks) => ({ ...lie, blocks })), ...doc.pages.slice(n + 1)] }), "", n);
      setIds([]);
      return;
    }
    flushSync(() => {
      update((doc) => ({ ...doc, pages: [...doc.pages.slice(0, n + 1), { blocks: first }, ...rest.map((blocks) => ({ blocks })), ...doc.pages.slice(n + 1)] }), "", n + 1);
      setAt(n + 1);
      setIds([]);
    });
    seek();
  }
  // Changes the sheet's guide lines, or with `n` those of that page alone.
  function rules(n: number | undefined, fn: (g: Guides) => Guides, key?: string) {
    if (n === undefined) update((doc) => ({ ...doc, guides: fn(doc.guides) }), key);
    else turn((p) => ({ ...p, guides: fn(p.guides ?? NONE) }), key, n);
  }
  // The heights of a table's own rows as the screen lays them out now, in mm. The grid's rows after them are the box of
  // solution words. Undefined when the grid is not there or its rows do not parse.
  function screenRows(b: Block): number[] | undefined {
    const grid = sheet.current?.querySelector<HTMLElement>(`[data-id="${b.id}"] .table`);
    if (!grid || b.type !== "table") return undefined;
    const px = getComputedStyle(grid).gridTemplateRows.split(" ").slice(0, b.props.cells.length).map((p) => parseFloat(p) / K);
    return px.length === b.props.cells.length && !px.some(Number.isNaN) ? px : undefined;
  }
  // Whether a table has no spare room now: then it may come down with the texts that go from its cells. A table made
  // taller than its rows need keeps that height.
  function snug(b: TableBlock): boolean {
    const grid = sheet.current?.querySelector<HTMLElement>(`[data-id="${b.id}"] .table`);
    if (!grid) return false;
    const own = grid.style.height;
    grid.style.height = "auto";
    const full = parseFloat(getComputedStyle(grid).height) / K >= b.h - 0.05;
    grid.style.height = own;
    return full;
  }
  // The height in mm that a table's box of solution words needs: the grid's rows after the table's own, read with the
  // grid's height free. In a table with spare room the box is stretched as the rows are, and that share is the rows'.
  function boxOf(grid: HTMLElement, rows: number): number {
    const own = grid.style.height;
    grid.style.height = "auto";
    const box = getComputedStyle(grid).gridTemplateRows.split(" ").slice(rows).reduce((all, p) => all + (parseFloat(p) || 0) / K, 0);
    grid.style.height = own;
    return box;
  }
  function place(boxes: [string, Partial<Box>][], key?: string) {
    const byId = new Map(boxes);
    change(
      (bs) =>
        bs.map((b) => {
          const patch = byId.get(b.id);
          // A table with row heights keeps them in proportion to its height. The rows are those on screen: a row the text
          // holds up is taller than its saved height.
          const rows = b.type === "table" && patch?.h !== undefined && b.h > EDGE && patch.h !== b.h ? heightsOf(b.props) : undefined;
          if (!rows) return { ...b, ...patch };
          // A row as high as it is saved is taken as saved: the screen lays rows out on parts of a pixel.
          const screen = screenRows(b)?.map((h, i) => (Math.abs(h - rows[i]) <= 0.05 ? rows[i] : h));
          if (screen && sum(screen) > 0) {
            // The rows fill the height without the table's line and the box of solution words.
            const to = patch!.h! - EDGE - boxOf(sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] .table`)!, screen.length);
            if (to <= 0) return { ...b, ...patch };
            return { ...b, ...patch, props: { ...b.props, rows: screen.map((h) => (h * to) / sum(screen)) } } as Block;
          }
          const f = (patch!.h! - EDGE) / (b.h - EDGE);
          return { ...b, ...patch, props: { ...b.props, rows: rows.map((h) => h * f) } } as Block;
        }),
      key,
    );
  }
  // `only` names the picked blocks of the type that take the props, where not all of them do.
  function style(type: Block["type"], props: object, key?: string, only?: string[]) {
    if (type === "table" || key === "words") tight.current = true;
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || b.type !== type || (only && !only.includes(b.id))) return b;
          const next = { ...b, props: { ...b.props, ...fresh(b, props) } } as Block;
          return { ...next, ...grown(b, next, hist.doc, H) } as Block;
        }),
      key,
    );
  }
  // The text typed into a ruling is set, and in the same change the block grows by whole rows when the text needs more
  // rows than it has. A Karo needs the rows of its squares. A Lineatur's field scrolls past its last row, so its
  // scroll height is taller than its box: the lines are that height in rows. Growth stops at the foot of the page, and
  // a block never shrinks by itself. Text and height share the typing's key, so one undo step takes both back.
  function typeRuling(b: Extract<Block, { type: "ruling" }>, text: string, area: HTMLTextAreaElement) {
    const { row, at } = RULINGS[kindOf(b.props.kind)];
    const have = rowsOf(b);
    const need = at
      ? area.scrollHeight > area.clientHeight + 1 ? Math.round(area.scrollHeight / (row * K)) : 0
      : Math.max(0, ...squares(text, colsOf(b)).map(([, y]) => y + 1));
    // Near the foot it takes the rows that still fit the page, not none.
    const rows = Math.max(have, Math.min(need, Math.floor((H - b.y) / row + 0.05)));
    const h = round(rows * row);
    const grows = rows > have;
    change(
      (bs) =>
        bs.map((x) =>
          ids.includes(x.id) && x.type === "ruling"
            ? ({ ...x, ...(grows && x.id === b.id ? tall(x, h) : {}), props: { ...x.props, ...fresh(x, { text }) } } as Block)
            : x,
        ),
      "text",
    );
  }
  // Sets what a shape and a text share: the frame, and the text in it.
  function look(props: object, key?: string) {
    tight.current = true;
    // A line style or a width turns on the border of each box that has none, as in PowerPoint.
    const edge = "dash" in props || "strokeWidth" in props;
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || (b.type !== "shape" && b.type !== "text")) return b;
          // A line holds no words: what belongs to them passes it by, and the frame's look lands as on any shape.
          const own = isLine(b) ? Object.fromEntries(Object.entries(props).filter(([name]) => !WORDS.includes(name))) : props;
          if (!Object.keys(own).length) return b;
          const on = edge && (b.props.stroke ?? "none") === "none" && { stroke: "#222222" };
          return { ...b, props: { ...b.props, ...fresh(b, own), ...on } } as Block;
        }),
      key,
    );
  }
  // A picture's see-through, on every picked picture, in one step.
  function fadePicture(opacity: number) {
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === "image" ? { ...b, props: { ...b.props, opacity } } : b)), "opacity");
  }
  // Sets the trace text's look on every picked block that carries text, in one step: a text, a shape, a table and a
  // Lineatur each have it. A Lineatur that shows the Lernwörter has a look of its own and takes none.
  function traced(props: object) {
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && (b.type === "table" || (b.type === "ruling" && !listOf(b)) ||((b.type === "text" || b.type === "shape") && !isLine(b))) ? ({ ...b, props: { ...b.props, ...fresh(b, props) } } as Block) : b)));
  }
  // The panel's bold, italic, underline and colour go to the field while a text is written, as in PowerPoint.
  // Else they go to the whole of every selected block, and there take the place of what its words had of their own.
  function paint(props: Marks, key?: string) {
    if (field.current && tint(field.current, props, boxed(sel.find((b) => b.id === editing)!)!, key)) return;
    tight.current = true;
    change(
      (bs) =>
        bs.map((b) => {
          const text = ids.includes(b.id) && boxed(b);
          return text ? ({ ...b, props: { ...b.props, ...(text.rich && cleared(text.rich, props)), ...fresh(b, props) } } as Block) : b;
        }),
      key,
    );
  }
  // The brush picks up the look of the source. Every key is in it, also where the block has nothing
  // there: the block painted then loses its own, as in PowerPoint.
  function dip(marks?: Marks) {
    if (!source) return;
    const from = { ...(boxed(source) ?? source.props), ...marks, mark: source.mark } as Coat;
    // A table's `color` is the colour of its text: its lines have `line`.
    from.rule = source.type === "table" ? source.props.line : from.color;
    // The band a Lineatur shows, set by hand or its kind's own: a Lineatur 3 with none takes the band off a Lineatur 1.
    if (source.type === "ruling") from.band = bandOf(source);
    // A field says "not bold" where a block says nothing: both are the same look. A band switched off is a look too:
    // it stays false, or the target would fall back to its kind's default, which is on for Lineatur 1 and 2.
    setCoat(Object.fromEntries(takes(source).map((name) => [name, from[name] === false && name !== "band" ? undefined : from[name]])));
  }
  // Lays the brush's look on the picked words of a text being written, in one undo step. A look that says "not bold"
  // says it as false, so the words lose their own bold and colour where the look has none.
  function wordPaint(b: Block) {
    const text = b && boxed(b);
    // Only what the look has of words: one from a line or a picture has none, and leaves the words as they are.
    const has = (name: keyof Coat) => !!coat && name in coat;
    if (!field.current || !text || !coat || !(["bold", "italic", "underline", "color"] as const).some(has)) return false;
    const marks: Marks = {};
    for (const name of ["bold", "italic", "underline"] as const) if (has(name)) marks[name] = coat[name] ?? false;
    if (has("color")) marks.color = coat.color ?? text.color ?? "#222222";
    return tint(field.current, marks, text, "");
  }
  openNow.current = (id, el) => {
    clicked.current = undefined;
    edit(id, el);
  };
  // A drag with the brush over a text or a shape with words: the field opens at the press, and the words the pointer
  // crosses take the look. A press that does not move paints the whole block, as a click does.
  function brushDrag(id: string, el: Element, press: globalThis.MouseEvent, on: string[]) {
    const start: [number, number] = [press.clientX, press.clientY];
    let opened = false;
    const move = (e: globalThis.PointerEvent) => {
      if (!opened) {
        if (Math.hypot(e.clientX - start[0], e.clientY - start[1]) <= 3) return;
        opened = true;
        if (editing !== id) {
          // A text of a picked group is picked alone, as the field's words go to every picked block. A locked or a
          // linked text opens no field: its group stays picked, and it is painted whole.
          if (on.length > 1) flushSync(() => setIds([id]));
          flushSync(() => openNow.current(id, el));
          if (on.length > 1 && !field.current) flushSync(() => setIds(on));
        }
      }
      const view = field.current;
      const from = view?.posAtCoords({ left: start[0], top: start[1] });
      const to = view?.posAtCoords({ left: e.clientX, top: e.clientY });
      if (view && from && to) view.dispatch(view.state.tr.setSelection(TextSelection.between(view.state.doc.resolve(from.pos), view.state.doc.resolve(to.pos))));
    };
    // The words are picked, not moved: the browser's drag of a selected text would move them.
    const stop = (e: Event) => e.preventDefault();
    // A drag the browser calls off, or that the window loses, paints nothing.
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", end);
      window.removeEventListener("blur", end);
      window.removeEventListener("dragstart", stop);
    };
    const up = () => {
      end();
      const view = field.current;
      if (!(opened && view && !view.state.selection.empty && wordPaint(blocks.find((b) => b.id === id)!))) daub(on, page);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", end);
    window.addEventListener("blur", end);
    window.addEventListener("dragstart", stop);
  }
  // Lays the look on blocks of page `n`. Each takes what it has, and its words lose what they had of their own
  // there. All of it is one undo step, and none where nothing changes.
  function daub(on: string[], n = page) {
    if (!coat) return;
    const dab = (b: Block) => {
      if (!on.includes(b.id)) return b;
      // A line never vanishes: it takes a border only from a block that has one.
      // Nor do a table's or a Lineatur's lines: a table made outside the editor may name no colour for its own.
      // A Lineatur that shows its band as the brush does keeps what it stores of it: the band of its kind stays unset.
      const own = takes(b).filter((name) => name in coat && name !== "mark" && !(isLine(b) && (coat.stroke ?? "none") === "none") && !(name === "rule" && !coat.rule) && !(name === "band" && b.type === "ruling" && bandOf(b) === coat.band));
      // The colour of a Lineatur's lines is its `color`, that of a table's lines its `line`.
      const props = Object.fromEntries(own.map((name) => [name === "rule" ? (b.type === "table" ? "line" : "color") : name, coat[name] ?? (b.type === "shape" ? BARE[name] : undefined)]));
      const rich = own.length ? boxed(b)?.rich : undefined;
      // What is left unset goes, so a saved sheet opens as it looks here.
      const all = Object.entries({ ...b.props, ...(rich && cleared(rich, props)), ...props }).filter(([, value]) => value !== undefined);
      const next = { ...b, mark: coat.mark, props: Object.fromEntries(all) } as Block;
      if (!next.mark) delete next.mark;
      // A maths block is as high as its exercises need, as from the panel.
      if (next.type === "maths" && b.type === "maths" && overFoot(b, next.props, sizeOf(live.current.doc, n)[1])) {
        // A painted type size that would push the block past the page's foot is not painted: the size stays.
        return { ...next, props: { ...next.props, size: b.props.size } };
      }
      return next.type === "maths" && b.type === "maths" && mathsHeight(next.props) !== mathsHeight(b.props) ? { ...next, ...tall(b, mathsHeight(next.props)) } : next;
    };
    if (pages[n].blocks.every((b) => JSON.stringify(dab(b)) === JSON.stringify(b))) return;
    tight.current = true;
    turn((p) => ({ ...p, blocks: p.blocks.map(dab) }), undefined, n);
  }
  // A list is for the paragraphs the caret stands in, or with no field for every paragraph of the selected blocks.
  // Asked for again, it goes.
  function itemize(kind: List) {
    if (field.current) return list(field.current, kind);
    const on = sel.map(boxed).find((p) => p)!;
    const to = parasOf(on)[0].list === kind ? undefined : kind;
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && boxed(b) ? ({ ...b, props: { ...b.props, ...listed(boxed(b)!, to) } } as Block) : b)));
  }
  // The gaps of a Lückentext. In a text being written in, the picked words become a gap or stop being one; in a table
  // cell being written in, that cell does. Else every selected block that holds words is a gap as a whole.
  // A block with no words takes no gap: its props stay as they are.
  const wordy = (b: Block) => {
    const text = boxed(b);
    // A linked text draws the sheet's list, which takes no gap.
    if (text?.list === true) return false;
    return b.type === "table" ? b.props.cells.flat().some(Boolean) : !!text && parasOf(text).some((p) => p.runs.some((r) => r.text));
  };
  function gapping(on: boolean) {
    if (field.current) return hole(field.current, on);
    if (!sel.some(wordy)) return;
    tight.current = true;
    if (table && editing === table.id) {
      const { cols, cells, gaps } = table.props;
      const [r, c] = [Math.floor(slot / cols.length), slot % cols.length];
      const next = cells.map((row, i) => row.map((_, j) => (i === r && j === c ? on : !!gaps?.[i]?.[j])));
      return style("table", { gaps: next.some((row) => row.some(Boolean)) ? next : undefined }, "");
    }
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || !wordy(b)) return b;
          if (b.type === "table") return { ...b, props: { ...b.props, gaps: allCells(b.props.cells, on) } } as Block;
          const text = boxed(b);
          return text ? ({ ...b, props: { ...b.props, ...stored(allGaps(parasOf(text), on)) } } as Block) : b;
        }),
      "",
    );
  }
  // Every n-th word of each selected block that holds words is a gap, counted through its text, in one undo step.
  function gapEvery(n: number) {
    if (!sel.some(wordy)) return;
    tight.current = true;
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || !wordy(b)) return b;
          if (b.type === "table") return { ...b, props: { ...b.props, gaps: everyNthCell(b.props.cells, n) } } as Block;
          const text = boxed(b);
          return text ? ({ ...b, props: { ...b.props, ...stored(everyNth(parasOf(text), n)) } } as Block) : b;
        }),
      "",
    );
  }
  // Gives the selected lines a length in mm. Each keeps its angle and the top left corner of its box.
  function extend(to: number) {
    place(
      rulers.map((b) => {
        const now = Math.hypot(b.w, b.h);
        return [b.id, now ? { w: round((b.w * to) / now), h: round((b.h * to) / now) } : { w: to }];
      }),
      "length",
    );
  }
  // Undo and redo show the page of their step, as PowerPoint does: page `n` is in use, and the desk scrolls to it.
  // On another page than before nothing is selected, and a crop ends with the picture as it was.
  function show(n: number, step: (h: typeof hist) => typeof hist) {
    mergeKey.current = "";
    [steered.current, scrollHeld.current, lagged.current] = [0, false, false];
    flushSync(() => {
      setHist(step);
      setAt(n);
      // The step may have added or taken pages before the choice: the page of the step alone is chosen.
      setChosen([]);
      if (n === page) return;
      setIds([]);
      setDraft(undefined);
    });
    // A page in use that lies partly in view stays put: the desk does not jump to its top.
    const [on, view] = [sheet.current!.getBoundingClientRect(), desk.current!.getBoundingClientRect()];
    if (n !== page || on.bottom <= view.top || on.top >= view.bottom) seek();
  }
  function undo() {
    const last = hist.past.at(-1);
    // The cells picked may be other cells in the sheet of the step before, or none.
    setReach(undefined);
    if (last) show(last.from, (h) => undone(h, last));
  }
  function redo() {
    const next = hist.future[0];
    setReach(undefined);
    if (next) show(next.to, (h) => redone(h, next));
  }

  // The new page comes after the one in use and takes its place.
  function addPage(n = page) {
    flushSync(() => {
      update((doc) => ({ ...doc, pages: [...doc.pages.slice(0, n + 1), { blocks: [] }, ...doc.pages.slice(n + 1)] }), "", n + 1);
      setAt(n + 1);
      setChosen([n + 1]);
      setIds([]);
    });
    seek();
  }
  function visit(n: number) {
    done();
    [steered.current, scrollHeld.current, lagged.current] = [0, false, false];
    flushSync(() => {
      setAt(n);
      setChosen([n]);
      setIds([]);
    });
    seek();
  }
  // Lays the sheet on its side or upright, or with `n` that page alone (`undefined` gives the sheet's format again).
  // A block spanning the page stretches with it, one centred across stays centred, the rest keep their place.
  // Blocks the page no longer holds move back onto it.
  function lay(landscape: boolean | undefined, n?: number) {
    update((doc) => {
      // A sheet that says nothing stands upright: "Hoch" leaves it so.
      const next = { ...doc, ...(n === undefined && landscape !== !!doc.landscape && { landscape }), pages: doc.pages.map((p, i) => (n === undefined || i === n ? { ...p, landscape: n === undefined ? undefined : landscape } : p)) };
      const pages = next.pages.map((p, i) => {
        const [w, h] = sizeOf(next, i);
        if (w === sizeOf(doc, i)[0]) return p;
        // As PowerPoint: a group comes back as one, by its outermost, so its blocks keep their places in it, and a
        // turned block counts by its outline. Left and top win where it is larger than the page. What lies on the
        // page stays as it is: `hull` knows the half hundredth by which a block on its side may lie off.
        const unit = (b: Block) => b.group?.[0] ?? b.id;
        const round = (v: number) => Math.round(v * 100) / 100;
        const back = (at: number, size: number, max: number) => round(Math.max(0, Math.min(at, max - size)) - at);
        // One axis of a unit, in plain words: a block that starts at the margin, or up to 15 mm right of it, and
        // reaches the right margin spans the page. It keeps its start and grows with the page if it may stretch, else
        // it moves by half the growth. A block whose middle is 0, 5, 10 or 15 mm right of the page's middle is centred
        // and moves by half the growth too, so it keeps its distance from the middle. Down the page no slack, no
        // centring: a block that lands in the middle of the turned page by chance would move on the way back.
        const along = (at: number, size: number, old: number, now: number, stretch: boolean, middle: boolean, slack: number): [number, number] => {
          const spans = at <= MARGIN + 1 + slack && at + size >= old - MARGIN - 1;
          if (spans && stretch) return [0, now - old];
          const off = at + size / 2 - old / 2;
          const centred = [0, 5, 10, 15].some((s) => Math.abs(off - s) <= 0.5);
          if (middle && (spans || centred)) return [(now - old) / 2, 0];
          return [0, 0];
        };
        const across = new Set(["text", "shape", "ruling", "table", "name", "maths"]);
        const down = new Set(["text", "shape", "ruling"]);
        const [ow, oh] = sizeOf(doc, i);
        const blocks = p.blocks.map((b) => {
          const all = hull(p.blocks.filter((o) => unit(o) === unit(b)));
          // Only a single block that is not turned stretches.
          // A circle, a triangle and a star keep their shape.
          const single = !b.group && (b.angle ?? 0) % 180 === 0 && !(b.type === "shape" && ["circle", "triangle", "star"].includes(b.props.kind));
          const [mx, sw] = along(all.x, all.w, ow, w, single && across.has(b.type), true, 15);
          const [my, sh] = along(all.y, all.h, oh, h, single && down.has(b.type), false, 0);
          const [dx, dy] = [back(all.x + mx, all.w + sw, w), back(all.y + my, all.h + sh, h)];
          if (!mx && !my && !sw && !sh && !dx && !dy) return b;
          return { ...b, x: round(b.x + mx + dx), y: round(b.y + my + dy), w: round(b.w + sw), h: round(b.h + sh) };
        });
        return { ...p, blocks };
      });
      return { ...next, pages };
    });
  }
  // Takes the chosen pages away, all in one step. The last page stays. The page in use stays, one place back when a
  // page before it goes; a page gone itself hands it to the one in its place.
  // It stays on the desk where it was too: the zoom may change with the widest page, so its top is measured before and after.
  function removePages(ns: number[] = chosenNow) {
    if (ns.length >= pages.length) return;
    const was = sheet.current!.getBoundingClientRect().top;
    const at = ns.includes(page) ? Math.min(Math.min(...ns), pages.length - ns.length - 1) : page - ns.filter((i) => i < page).length;
    flushSync(() => {
      update((doc) => ({ ...doc, pages: doc.pages.filter((_, i) => !ns.includes(i)) }), "", at);
      setAt(at);
      setChosen([at]);
      setIds([]);
    });
    desk.current!.scrollBy(0, sheet.current!.getBoundingClientRect().top - was);
  }
  // Puts the pages at another place among the pages, from `start` on, in their order. The first of them is the page in use.
  function movePages(ns: number[], start: number) {
    const moved = [...ns].sort((a, b) => a - b);
    if (moved.every((i, j) => i === start + j)) return;
    done();
    flushSync(() => {
      update((doc) => {
        const rest = doc.pages.filter((_, i) => !moved.includes(i));
        return { ...doc, pages: [...rest.slice(0, start), ...moved.map((i) => doc.pages[i]), ...rest.slice(start)] };
      }, "", start);
      setAt(start);
      setChosen(moved.map((_, j) => start + j));
      setIds([]);
    });
    seek();
  }
  // The copies come after the last of their pages and take its place, in order. Each has its page's guide lines, grid
  // and format, and blocks of its own.
  function copyPages(ns: number[] = chosenNow) {
    const sorted = [...ns].sort((a, b) => a - b);
    const last = sorted[sorted.length - 1];
    done();
    flushSync(() => {
      update((doc) => ({
        ...doc,
        pages: doc.pages.flatMap((p, i) => (i === last ? [p, ...sorted.map((j) => ({ ...doc.pages[j], blocks: cloned(doc.pages[j].blocks, doc.pages[j].blocks) }))] : [p])),
      }), "", last + 1);
      setAt(last + 1);
      setChosen(sorted.map((_, j) => last + 1 + j));
      setIds([]);
    });
    seek();
  }
  // A drag of a thumbnail goes on at this point of the window. The pointer on the left half of a thumbnail means
  // the gap before it, on the right half the one after it, and past the last thumbnail the end.
  function aim(x: number, y: number) {
    const { from } = tug.current!;
    // A pen on an iPad is a finger too: its drag is on before the hold is up.
    clearTimeout(press.current);
    const rects = [...strip.current!.querySelectorAll("[data-thumb]")].map((el) => el.getBoundingClientRect());
    const slot = rects.filter((r) => y > r.bottom || (y >= r.top && x > r.left + r.width / 2)).length;
    // The line stays in the pointer's row: at the end of a row it stands after the thumbnail before the gap.
    const after = slot > 0 && (slot === rects.length || y < rects[slot].top);
    tug.current!.slot = slot;
    dragged.current = true;
    setHaul((now) => (now?.slot === slot && now.after === after ? now : { from, slot, after }));
  }
  // The place a dragged page would have after the drop.
  const landing = (from: number, slot: number) => (slot > from ? slot - 1 : slot);
  // Near the top or the bottom of the panel a drag scrolls it, faster the nearer the pointer is to the edge, so a
  // page can be dropped on a thumbnail out of view. The scroll goes on while the pointer rests there.
  function scrollEdge(x: number, y: number) {
    const panel = strip.current!.closest<HTMLElement>(".left")!.getBoundingClientRect();
    const zone = 40;
    const down = (y - (panel.bottom - zone)) / zone;
    const up = (panel.top + zone - y) / zone;
    const a = auto.current;
    a.x = x;
    a.y = y;
    a.speed = (down > 0 ? Math.min(1, down) : up > 0 ? -Math.min(1, up) : 0) * 12;
    if (!a.speed) {
      cancelAnimationFrame(a.frame);
      a.frame = 0;
      a.last = 0;
      a.rest = 0;
    } else if (!a.frame) a.frame = requestAnimationFrame(scrollStep);
  }
  // The speed is px per 1/60 s, so the scroll keeps its pace in time on a slow machine: a busy CI runner gave 10 to
  // 20 frames a second, and the panel took up to six times as long (#597). A longer hitch counts as 100 ms.
  function scrollStep(now: number) {
    const a = auto.current;
    a.frame = 0;
    if (!tug.current || !a.speed) return;
    const dt = a.last ? Math.min(now - a.last, 100) : 1000 / 60;
    a.last = now;
    // Whole pixels only, the rest kept for the next frame: the browser rounds a part of a pixel away, and at the outer
    // edge of the zone or on a 120 Hz screen each frame's step is less than one.
    a.rest += (a.speed * dt) / (1000 / 60);
    const px = Math.trunc(a.rest);
    a.rest -= px;
    strip.current!.closest<HTMLElement>(".left")!.scrollTop += px;
    aim(a.x, a.y);
    a.frame = requestAnimationFrame(scrollStep);
  }
  function quit() {
    clearTimeout(press.current);
    cancelAnimationFrame(auto.current.frame);
    auto.current.frame = 0;
    auto.current.speed = 0;
    auto.current.last = 0;
    auto.current.rest = 0;
    tug.current = undefined;
    setHaul(undefined);
  }
  function release() {
    const t = tug.current;
    quit();
    // A finger held still on a thumbnail opens its page's menu on the lift.
    if (t?.held && !t.left) return thumbMenu(t.from, t.x, t.y);
    const { from, slot } = t ?? {};
    if (slot === undefined) return;
    // The chosen pages go together; the dragged one alone when it is not chosen.
    const ns = choiceOf(from!);
    const start = slot - ns.filter((i) => i < slot).length;
    movePages(ns, start);
    strip.current!.querySelector(`[data-thumb="${start}"]`)?.scrollIntoView({ block: "nearest" });
  }
  // On a thumbnail Ctrl with an arrow moves its page by one place, with Shift to the start or the end, and Ctrl+D
  // copies it. The focus follows the page.
  function pageKey(e: Key, n: number) {
    // Delete and Backspace take the thumbnail's page away, never the picked blocks, and the last page stays.
    if (/^(Delete|Backspace)$/.test(e.key) && !(e.ctrlKey || e.metaKey || e.altKey || e.shiftKey)) {
      e.preventDefault();
      e.stopPropagation();
      // A page being dragged stays: the drop would look for it.
      const ns = choiceOf(n);
      if (ns.length >= pages.length || tug.current) return;
      removePages(ns);
      // The thumbnail in the place of the first page gone, or the last one left.
      strip.current!.querySelector<HTMLElement>(`[data-thumb="${Math.min(Math.min(...ns), pages.length - ns.length - 1)}"]`)!.focus();
      return;
    }
    if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
    // Copy, cut and paste of pages: the block ones of the sheet must not also run.
    // Ctrl+V pastes pages only when they are the newest copy; else the sheet's paste takes it, as before.
    if (/^[cxv]$/i.test(e.key) && !e.shiftKey && !(/^v$/i.test(e.key) && !clippedPages().pages.length)) {
      e.preventDefault();
      e.stopPropagation();
      const ns = choiceOf(n);
      if (/^c$/i.test(e.key)) storePages(ns);
      else if (/^x$/i.test(e.key)) {
        if (ns.length >= pages.length) return;
        cutPages(ns);
        // As after Delete: the thumbnail in the place of the first page gone keeps the keys.
        strip.current!.querySelector<HTMLElement>(`[data-thumb="${Math.min(Math.min(...ns), pages.length - ns.length - 1)}"]`)!.focus();
      } else {
        pastePages(n);
        strip.current!.querySelector<HTMLElement>(`[data-thumb="${n + 1}"]`)?.focus();
      }
      return;
    }
    const ns = choiceOf(n);
    const first = ns[0];
    const count = ns.length;
    const copy = /^d$/i.test(e.key) && !e.shiftKey;
    const to = copy
      ? Math.max(...ns) + 1
      : e.key === "ArrowUp"
        ? (e.shiftKey ? 0 : Math.max(0, first - 1))
        : e.key === "ArrowDown"
          ? (e.shiftKey ? pages.length - count : Math.min(pages.length - count, first + 1))
          : -1;
    if (to < 0) return;
    // The window's own Ctrl+D copies blocks, and Chrome's sets a bookmark.
    e.preventDefault();
    e.stopPropagation();
    if (copy) copyPages(ns);
    else movePages(ns, to);
    strip.current!.querySelector<HTMLElement>(`[data-thumb="${to}"]`)!.focus();
  }

  // The page an element lies on; beside the pages, the one in use.
  const pageOf = (el: Element) => +(el.closest<HTMLElement>(".sheet")?.dataset.page ?? page);
  // How far down the page in use, or page `n`, in mm, a point of the desk's view lies.
  const seen = (down: number, n?: number) => {
    const on = n === undefined ? sheet.current! : desk.current!.querySelector(`[data-page="${n}"]`)!;
    return (desk.current!.getBoundingClientRect().top + down - on.getBoundingClientRect().top) / k;
  };
  // The page that fills most of the desk's view becomes the page in use when the teacher scrolls the desk (the wheel,
  // a finger, its scroll bar), so a new block lands where the teacher looks. A scroll the editor makes itself, to
  // show a page or a block, or a zoom with Ctrl and the wheel, leaves the page in use as it is.
  // `steered` is the time until which a scroll counts as the teacher's; `scrollHeld` holds while the scroll bar is held.
  // A text being typed keeps its page; `lagged` says the view moved meanwhile, and the page in view is in use once the
  // text closes.
  const steered = useRef(0);
  const scrollHeld = useRef(false);
  const lagged = useRef(false);
  const steer = (ms = 500) => (steered.current = performance.now() + ms);
  // Any other scroll (a zoom about the pointer, a page key with a block picked, a script) that leaves the page in use
  // out of view hands it on to the page in view once the desk rests, so a new block never lands out of sight (#805).
  // A scroll of the editor's own ends on the page in use, so it keeps it.
  const resting = useRef(0);
  useEffect(() => () => clearTimeout(resting.current), []);
  function follow() {
    clearTimeout(resting.current);
    // The editor's own scroll has brought the page in use into view: from here on it counts as any other.
    if (heading.current && !lost()) heading.current = 0;
    // A drag that scrolls the desk at its edge keeps its page until the pointer is up.
    if (performance.now() > steered.current && !scrollHeld.current) return void (resting.current = window.setTimeout(() => calm(() => strayNow.current()), 150));
    if (editing) lagged.current = true;
    else inView();
  }
  // Whether no part of the page in use lies in the desk's view.
  function lost() {
    const [on, view] = [sheet.current?.getBoundingClientRect(), desk.current!.getBoundingClientRect()];
    return !on || on.bottom <= view.top || on.top >= view.bottom || on.right <= view.left || on.left >= view.right;
  }
  // A picked block keeps its page, so the arrow keys still nudge it; a new block finds the page in view by `looked`.
  // The editor's own smooth scroll to the page in use: until it is there, the page in use lies out of view on purpose.
  const heading = useRef(0);
  function seek() {
    heading.current = performance.now() + 1500;
    sheet.current!.scrollIntoView({ behavior: "smooth" });
  }
  const strayed = () => lost() && performance.now() > heading.current;
  // A picked block keeps its page, so the arrow keys still nudge it; a new block finds the page in view by `looked`.
  // A text being typed is picked too, so it keeps its page here as well. The timer runs the stray of the latest
  // render: a pick dropped meanwhile counts.
  function stray() {
    if (!strayed() || ids.length) return;
    inView();
  }
  const strayNow = useRef(stray);
  strayNow.current = stray;
  // The page a new block goes to: the page in use, or the page in view when the page in use is out of sight.
  const looked = () => (strayed() ? inView() : page);
  useEffect(() => {
    if (editing || !lagged.current) return;
    lagged.current = false;
    inView();
  }, [editing]);
  function inView() {
    const view = desk.current!.getBoundingClientRect();
    let [best, most] = [page, 0];
    for (const el of desk.current!.querySelectorAll<HTMLElement>("[data-page]")) {
      const r = el.getBoundingClientRect();
      const shown = (Math.min(r.right, view.right) - Math.max(r.left, view.left)) * (Math.min(r.bottom, view.bottom) - Math.max(r.top, view.top));
      if (shown > most) [best, most] = [+el.dataset.page!, shown];
    }
    setAt(best);
    return best;
  }

  // Notes page `was` for what the server sends later, and gives a way to look it up then. The pages may have changed
  // by that time: the page is found where it is now; one changed since is known by a block it still holds, or keeps
  // its number while the pages are as many as before. For a page that is gone, the page in use stands in.
  function mark(was = looked()) {
    const [on, count] = [pages[was], pages.length];
    return () => {
      const { doc, page } = latest.current;
      const same = doc.pages.indexOf(on);
      const found = same >= 0 ? same : doc.pages.findIndex((p) => p.blocks.some((b) => on.blocks.some((o) => o.id === b.id)));
      return found >= 0 ? found : doc.pages.length === count ? was : page;
    };
  }
  // Moves new blocks as one onto the page, then in steps clear of a block already at that spot.
  function land<T extends Box>(boxes: T[], blocks = pages[page].blocks, [W, H] = sizes[page]) {
    const [x, right] = span(boxes, "x");
    const [y, bottom] = span(boxes, "y");
    const [maxX, maxY] = [Math.max(0, W - right + x), Math.max(0, H - bottom + y)];
    let [dx, dy] = [Math.max(0, Math.min(x, maxX)) - x, Math.max(0, Math.min(y, maxY)) - y];
    const taken = () => blocks.some((b) => b.x === round(boxes[0].x + dx) && b.y === round(boxes[0].y + dy));
    // A step for each block is enough to find a free spot, unless the page has none.
    for (let n = 0; n < blocks.length && taken(); n++) {
      dx = step(x + dx, maxX) - x;
      dy = step(y + dy, maxY) - y;
    }
    return boxes.map((b) => ({ ...b, x: round(b.x + dx), y: round(b.y + dy) }));
  }
  // What the server sends waits while a pointer is down: a new block takes the selection, and with it Moveable's
  // target in the middle of a drag. It lands once the pointer is up, as an undo step after the drag's.
  const pressed = useRef(false);
  const due = useRef<(() => void)[]>([]);
  const calm = (run: () => void) => (pressed.current ? due.current.push(run) : run());
  useEffect(() => {
    // The right button drags nothing, and its menu may keep the release to itself.
    const press = (e: globalThis.PointerEvent) => void (pressed.current ||= !e.button);
    const lift = () => {
      pressed.current = false;
      cellDrag.current = false;
      // Moveable ends its drag with the mouse's or the finger's own event, which comes after the pointer's.
      setTimeout(() => pressed.current || due.current.splice(0).forEach((run) => run()));
    };
    window.addEventListener("pointerdown", press, true);
    window.addEventListener("pointerup", lift, true);
    window.addEventListener("pointercancel", lift, true);
    return () => {
      window.removeEventListener("pointerdown", press, true);
      window.removeEventListener("pointerup", lift, true);
      window.removeEventListener("pointercancel", lift, true);
    };
  }, []);
  // The block lands on page `n` of the sheet as last drawn, and that page is in use from then on.
  // A block the teacher inserts goes under the lowest block of the page, at its left edge, when it fits above the
  // margin there. Words and pictures pasted from another app keep the place at the top of the view.
  // The first spot of page `p` where a w x h box keeps 5 mm from every block, scanned in rows from the top, in steps of 5 mm.
  function freeSpot(doc: Doc, p: number, w: number, h: number) {
    const [W, H] = sizeOf(doc, p);
    const boxes = filled(doc.pages[p].blocks);
    for (let y = MARGIN; y <= H - MARGIN - h; y += 5)
      for (let x = MARGIN; x <= W - MARGIN - w; x += 5)
        if (boxes.every((b) => x + w + 5 <= b.x || x >= b.x + b.w + 5 || y + h + 5 <= b.y || y >= b.y + b.h + 5)) return { p, x, y };
    return undefined;
  }
  function add(w: number, h: number, rest: Fresh, n = looked(), pasted = false) {
    const { doc } = latest.current;
    const [held, size] = [doc.pages[n].blocks, sizeOf(doc, n)];
    const id = crypto.randomUUID();
    // Under the lowest block of page p, at its left edge, when it fits above the margin there.
    const below = (p: number) => {
      const outer = filled(doc.pages[p].blocks);
      if (!outer.length) return undefined;
      const [W, H] = sizeOf(doc, p);
      const low = outer.reduce((a, b) => (b.y + b.h > a.y + a.h ? b : a));
      return low.y + low.h + 5 + h <= H - MARGIN ? { p, x: Math.max(0, Math.min(low.x, W - MARGIN - w)), y: round(low.y + low.h + 5) } : undefined;
    };
    // Under the lowest block, else the first free spot, on page n and then on each later page; else a new page after the last.
    const free = () => {
      for (let p = n; p < doc.pages.length; p++) {
        const spot = below(p) ?? freeSpot(doc, p, w, h);
        if (spot) return spot;
      }
      return { p: doc.pages.length, x: MARGIN, y: MARGIN };
    };
    const spot = pasted || !held.length ? { p: n, x: (size[0] - w) / 2, y: round(Math.max(0, seen(0, n))) + MARGIN } : free();
    const { p } = spot;
    const onPage = p < doc.pages.length;
    const z = Math.max(0, ...(onPage ? doc.pages[p].blocks : []).map((b) => b.z)) + 1;
    const [block] = land([{ id, x: spot.x, y: spot.y, w, h, z, locked: false, ...rest }], onPage ? doc.pages[p].blocks : [], onPage ? sizeOf(doc, p) : size);
    // A new page is one step with the block, and takes the format of page n.
    if (onPage) turn((q) => ({ ...q, blocks: [...q.blocks, block] }), undefined, p);
    else update((d) => ({ ...d, pages: [...d.pages, { blocks: [block], landscape: d.pages[n].landscape }] }), "", p);
    setAt(p);
    setIds([id]);
    // A block under the view is brought into it, once it is drawn.
    requestAnimationFrame(() => document.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" }));
    // An empty text opens for typing; a pasted one comes with its words.
    if (rest.type === "text" && !rest.props.text) setEditing(id);
  }
  // The picture as the server holds it, measured once it decodes.
  async function served(id: number) {
    const img = new Image();
    img.src = `/api/uploads/${id}`;
    await img.decode();
    return { width: img.naturalWidth, height: img.naturalHeight };
  }
  // A picture goes to the server first; the block holds its number and its shape, and starts within 100 mm.
  async function sent(file: File) {
    const body = new FormData();
    body.append("file", file);
    // What the server says counts before what the browser makes of the file: WebKit reads no file while it has no
    // connection, and the file is not the one to blame then.
    // Chromium cannot decode an SVG here: the server's cleaned copy is measured instead.
    const svg = file.type === "image/svg+xml";
    const drawn = svg ? null : createImageBitmap(file);
    drawn?.catch(() => {});
    const { id } = await signed(api<{ id: number }>("/uploads", { method: "POST", body }));
    const { width, height } = drawn ? await drawn : await served(id);
    const w = round(Math.min(100, (100 * width) / height));
    return { w, h: round((w * height) / width), type: "image" as const, props: { upload: id, ratio: width / height, cut: [0, 0, 0, 0] } };
  }
  // With no connection or a fault of the server the picture can be sent again. Any other refusal is the file's own:
  // one the server does not take, or one the browser cannot read.
  const NO_PICTURE = "Das Bild konnte nicht hochgeladen werden.";
  const unfit = (s: string) => (s === "offline" || s.startsWith("5") ? undefined : "Das Bild ließ sich nicht hochladen. Es gehen JPEG, PNG, WebP und GIF bis 15 MB, SVG bis 2 MB.");
  async function upload(file?: File, pasted = false) {
    if (!file) return;
    await attempt(
      NO_PICTURE,
      async () => {
        const where = mark();
        const { w, h, ...rest } = await sent(file);
        calm(() => add(w, h, rest, where(), pasted));
      },
      unfit,
    );
  }
  // Dropped files land with the first one's middle under the pointer, on the page that lies there, and each next one
  // 5 mm right and down. They stay where they were dropped, also on a block, so they only move as far as the page
  // needs to hold them. The page and the spot are read at once: the desk may scroll while the pictures are on their way.
  // The ones that did not arrive are sent again by the line's button, and land on the same spot.
  function dropped(files: File[], left: number, top: number) {
    // Beside the pages, the nearest one takes the drop.
    const rects = [...desk.current!.querySelectorAll<HTMLElement>("[data-page]")].map((el) => el.getBoundingClientRect());
    const away = rects.map((r) => Math.hypot(Math.max(r.left - left, 0, left - r.right), Math.max(r.top - top, 0, top - r.bottom)));
    const was = away.indexOf(Math.min(...away));
    const [x, y] = [(left - rects[was].left) / k, (top - rects[was].top) / k];
    let rest = files;
    return attempt(NO_PICTURE, () => landed(rest, was, x, y, (still) => void (rest = still)), unfit);
  }
  // A picture from a web page comes as its address: a data: address is read here, as a file, and a web address is not
  // fetched (a browser refuses it across sites, and the server must not ask it). A dragged link with no picture adds nothing.
  const WEB_PICTURE = "Ein Bild von einer Webseite lässt sich nicht hereinziehen. Kopiere es dort und füge es hier mit Strg+V ein, oder speichere es und ziehe die Datei herein.";
  function dropLink(data: DataTransfer, left: number, top: number) {
    const html = data.getData("text/html");
    const pic = html ? new DOMParser().parseFromString(html, "text/html").querySelector("img") : null;
    const img = pic?.getAttribute("src");
    const uri = data.getData("text/uri-list").split(/\r?\n/).find((line) => line && !line.startsWith("#"));
    // The address the browser hands over is the picture shown: a lazy picture's `src` may be a blank placeholder. A
    // picture in a link hands over the link's address instead: then its <img> tells.
    const address = uri?.startsWith("data:image/") || (uri && pic && !pic.closest("a[href]")) ? uri : (img ?? undefined);
    if (!address) return;
    const read = /^data:image\/(png|jpeg|gif|webp);base64,([A-Za-z0-9+/=]+)$/.exec(address);
    if (!read) return attempt(WEB_PICTURE, () => Promise.reject(), () => WEB_PICTURE);
    const [, kind, b64] = read;
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    return dropped([new File([bytes], `bild.${kind}`, { type: `image/${kind}` })], left, top);
  }
  // Sends the files and lands those that arrived. Tells which did not, and throws why.
  async function landed(files: File[], was: number, x: number, y: number, keep: (still: File[]) => void) {
    const where = mark(was);
    const got = await Promise.allSettled(files.map((f) => (TYPES.includes(f.type) ? sent(f) : Promise.reject())));
    const made = got.flatMap((r) => (r.status === "fulfilled" ? [{ ...r.value, id: crypto.randomUUID() }] : []));
    if (made.length)
      calm(() => {
        // The pages may have changed while the pictures were on their way.
        const n = where();
        // The stack as a whole stays on the page, so its pictures keep their steps at an edge too.
        const [w, h] = sizeOf(latest.current.doc, n);
        const most = [w, h].map((side, axis) => side - Math.max(...made.map((b) => (axis ? b.h : b.w))) - 5 * (made.length - 1));
        const [cx, cy] = [x - made[0].w / 2, y - made[0].h / 2].map((c, axis) => Math.max(0, Math.min(c, most[axis])));
        // All of them are one undo step, on top of what the page holds by then.
        turn(
          (p) => {
            const z = Math.max(0, ...p.blocks.map((b) => b.z));
            const fresh = made.map((b, i) => ({
              ...b,
              x: round(Math.max(0, Math.min(cx + 5 * i, w - b.w))),
              y: round(Math.max(0, Math.min(cy + 5 * i, h - b.h))),
              z: z + 1 + i,
              locked: false,
            }));
            return { ...p, blocks: [...p.blocks, ...fresh] };
          },
          undefined,
          n,
        );
        setAt(n);
        setIds(made.map((b) => b.id));
      });
    keep(files.filter((_, i) => got[i].status === "rejected"));
    const why = got.flatMap((r) => (r.status === "rejected" ? [r.reason as Error | undefined] : []));
    // The session run out says nothing, and a picture that can be sent again counts before a file's own fault.
    if (why.length) throw why.find((e) => e?.message === "401") ?? why.find((e) => !unfit(status(e))) ?? why[0];
  }
  // What an insert button makes, from insert.ts.
  const addInsert = (f: Insert) => add(f.w, f.h, f);
  // A maths block starts with plus exercises up to 20; the server makes them.
  async function addMaths() {
    const limits = MATHS.limits(newSeed());
    await attempt("Die Aufgaben konnten nicht erzeugt werden.", async () => {
      const where = mark();
      const props = { ...limits, ...(await generate(limits)), ...MATHS.look };
      calm(() => add(MATHS.w, mathsHeight(props), { type: "maths", props }, where()));
    });
  }
  // `got` is the sheet's Lernwörter when the blocks bring a list the sheet lacks: it comes in the same step.
  function put(from: Block[], got?: string[]) {
    const copies = land(
      cloned([...from].sort((a, b) => a.z - b.z), blocks).map((b, i) => ({ ...b, z: top + 1 + i })),
    );
    update((doc) => ({ ...doc, ...(got && { words: got }), pages: doc.pages.map((p, i) => (i === page ? { ...p, blocks: [...p.blocks, ...copies] } : p)) }), "", page, page);
    setIds(copies.map((b) => b.id));
  }
  // The copied blocks lie in the browser's store: they last over a reload and reach another sheet and another tab.
  // They carry the account's id, for the browser may serve another account next.
  // Their words go to the system's clipboard, which pushes out a picture copied before: the newest copy wins.
  // They go out in a copy of the browser's own, which needs no leave and is done before the next paste. A copy with
  // no words waiting, as a field's, stays the browser's.
  const pending = useRef<string | null>(null);
  // The text of the last cells copied: a paste of exactly that, with line breaks, spreads over the cells.
  const cellsCopied = useRef("");
  useEffect(() => {
    const copied = (e: ClipboardEvent) => {
      if (pending.current === null) return;
      e.clipboardData!.setData("text/plain", pending.current);
      pending.current = null;
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener("copy", copied, true);
    return () => window.removeEventListener("copy", copied, true);
  }, []);
  // In a browser that makes no such copy the words land a moment later: until then a paste still finds the older
  // picture there, which is stale.
  const writing = useRef(0);
  // A copy with no words still stamps the system's clipboard, with a blank.
  const wordsOf = (held: Block[]) => held.map((b) => ("text" in b.props && b.props.text) || "").filter(Boolean).join("\n") || " ";
  // The sheet's mends go along with the copied texts and tables, so a paste into another sheet keeps them. A block's own entry wins.
  const carrying = (bs: Block[]): Block[] => {
    const mends = live.current.doc.breaks;
    if (!mends) return bs;
    return bs.map((b) => ("text" in b.props || "cells" in b.props ? ({ ...b, props: { ...b.props, breaks: { ...mends, ...(b.props as { breaks?: Breaks }).breaks } } } as Block) : b));
  };
  function copy(held = sel) {
    if (!held.length) return;
    // A linked Lineatur is drawn from the sheet's list, so the list goes along with it.
    const linkedAny = held.some(tied);
    localStorage.setItem("clip", JSON.stringify({ owner: user.id, blocks: carrying(held), ...(linkedAny && { words: live.current.doc.words }) }));
    // The newest copy wins: pages copied before are no longer what a paste on a thumbnail brings.
    localStorage.removeItem("pages");
    const words = wordsOf(held);
    localStorage.setItem("copied", hash(words));
    pending.current = words;
    document.execCommand("copy");
    pending.current = null;
    copied();
    writing.current++;
    onTheWay(toClipboard(held, words).catch(() => {}).finally(() => writing.current--));
  }
  // The words and a picture of the blocks go out together. The write starts in the key press, as Safari wants; the
  // picture is drawn after it, and a refused picture still leaves the words.
  // A copy made while an earlier one's picture is still drawn wins: the earlier write is called off.
  const lastCopy = useRef(0);
  function toClipboard(held: Block[], words: string): Promise<void> {
    const n = ++lastCopy.current;
    const write = () => (n === lastCopy.current && navigator.clipboard?.writeText(words)) || Promise.resolve();
    try {
      const png = pictureOf(held, live.current.doc, page).then((blob) => (n === lastCopy.current ? blob : Promise.reject(new Error("newer copy"))));
      return navigator.clipboard.write([new ClipboardItem({ "image/png": png, "text/plain": new Blob([words], { type: "text/plain" }) })]).catch(write);
    } catch {
      return write();
    }
  }
  // Only what is free goes. With nothing free the clipboard keeps what it held.
  function cut() {
    copy(free);
    remove();
  }
  // The store is open to an older build and to anyone: only this account's whole blocks reach the sheet.
  // With the words the copy carried, if any: they are not checked here, as `landed` reads them.
  function clipped(): { blocks: Block[]; words?: unknown } {
    let held: { owner?: number; blocks?: Block[]; words?: unknown } | null = null;
    try {
      held = JSON.parse(localStorage.getItem("clip") ?? "null");
    } catch {
      return { blocks: [] };
    }
    return held?.owner === user.id && Array.isArray(held.blocks) && held.blocks.every(wholeBlock) ? { blocks: held.blocks, words: held.words } : { blocks: [] };
  }
  function clip(): Block[] {
    return clipped().blocks;
  }
  // The pages copied in the panel Seiten, read the same way: this account's, each page with whole blocks.
  function clippedPages(): { pages: Page[]; words?: unknown } {
    let held: { owner?: number; pages?: Page[]; words?: unknown } | null = null;
    try {
      held = JSON.parse(localStorage.getItem("pages") ?? "null");
    } catch {
      return { pages: [] };
    }
    const fits = (p: Page) => !!p && typeof p === "object" && Array.isArray(p.blocks) && p.blocks.every(wholeBlock);
    return held?.owner === user.id && Array.isArray(held.pages) && held.pages.every(fits) ? { pages: held.pages, words: held.words } : { pages: [] };
  }
  // Stores the pages chosen, in their order, with the words of a linked Lineatur as the block copy does.
  function storePages(ns: number[]) {
    const held = [...ns].sort((a, b) => a - b).map((i) => live.current.doc.pages[i]);
    const linkedAny = held.some((p) => p.blocks.some(tied));
    localStorage.setItem("pages", JSON.stringify({ owner: user.id, pages: held.map((p) => ({ ...p, blocks: carrying(p.blocks) })), ...(linkedAny && { words: live.current.doc.words }) }));
  }
  // The pasted pages come after page `after`, with blocks of their own, and are the choice from then on. One step of undo.
  function pastePages(after: number) {
    const { pages: held, words } = clippedPages();
    if (!held.length) return;
    const copies = held.map((p) => ({ ...p, blocks: cloned(p.blocks, p.blocks) }));
    const got = carried(copies.flatMap((p) => p.blocks), words, live.current.doc);
    let taken = 0;
    const fresh = copies.map((p) => {
      const blocks = got.blocks.slice(taken, (taken += p.blocks.length));
      return { ...p, blocks };
    });
    done();
    flushSync(() => {
      update((doc) => ({ ...doc, ...(got.words && { words: got.words }), pages: [...doc.pages.slice(0, after + 1), ...fresh, ...doc.pages.slice(after + 1)] }), "", after + 1);
      setAt(after + 1);
      setChosen(fresh.map((_, j) => after + 1 + j));
      setIds([]);
    });
    seek();
  }
  // Cut: the pages are stored, then taken away. Not when they are every page.
  function cutPages(ns: number[]) {
    if (ns.length >= live.current.doc.pages.length) return;
    storePages(ns);
    removePages(ns);
  }
  function paste() {
    const { blocks: held, words } = clipped();
    if (!held.length) return;
    const got = carried(held, words, live.current.doc);
    put(got.blocks, got.words);
  }
  // The system's clipboard holds the words of the newest copy. Words that are not the copied blocks' own were copied
  // in another app, or in a field: they make a text block that grows to hold them, as in PowerPoint. Says whether
  // they did. The editor's own words never do, for this account or the next: there the blocks' owner decides.
  // Whether words are the editor's own copy. A copy of the build before left no mark: its words are those of the stored blocks.
  function ownCopy(words: string) {
    const [copied, held] = [localStorage.getItem("copied"), clip()];
    return copied === null ? held.length > 0 && words === wordsOf(held) : copied === hash(words);
  }
  function typed(got: string, html = "") {
    const words = got.replace(/\r\n/g, "\n");
    if (!words.trim() || ownCopy(words)) return false;
    tight.current = true;
    // Words with their bold, italic, underline and colour keep them. Word ends a whole line with a break, which would make an empty last paragraph.
    const paras = parasFromHtml(html);
    const props = paras.length ? stored(paras) : { text: words.replace(/\n+$/, "") };
    add(80, 12, { type: "text", props: { ...props, size: 14, align: "left" } }, looked(), true);
    return true;
  }
  // A second press while the system's clipboard is still being read would paste onto the same spot.
  const reading = useRef(false);
  // The button has no paste of the browser's to go by, so it asks the system's clipboard itself: for a picture
  // first, then for words.
  async function pasteAny() {
    if (reading.current) return;
    if (writing.current) {
      // The blocks are here while the picture is drawn; a second press in the same moment pastes nothing more.
      reading.current = true;
      queueMicrotask(() => (reading.current = false));
      return paste();
    }
    reading.current = true;
    let words = "";
    let html = "";
    try {
      for (const item of await navigator.clipboard.read()) {
        // The editor's own copy brings its blocks, though it comes with a picture of them too.
        if (item.types.includes("text/plain")) {
          words = await (await item.getType("text/plain")).text();
          if (refusedWords(words)) return;
          if (ownCopy(words.replace(/\r\n/g, "\n"))) return paste();
        }
        const type = item.types.find((t) => t.startsWith("image/"));
        if (type) return upload(new File([await item.getType(type)], "bild", { type }), true);
        if (item.types.includes("text/html")) html = await (await item.getType("text/html")).text();
      }
    } catch {
      // No leave to read, or a browser that cannot: the copied blocks are still there.
    } finally {
      reading.current = false;
    }
    if (!typed(words, html)) paste();
  }
  // What is locked stays, and stays picked: "Entsperren" is one click away. With nothing free there is no undo step.
  function remove() {
    const gone = free.map((b) => b.id);
    if (!gone.length) return;
    change((bs) => bs.filter((b) => !gone.includes(b.id)));
    setIds(ids.filter((id) => !gone.includes(id)));
  }
  const all = () => setIds(blocks.map((b) => b.id));
  // The selection with its groups made whole: grouping and ungrouping work on whole groups.
  const wide = blocks.filter((b) => grouped(ids, blocks).includes(b.id));
  // Grouping needs two things to join: blocks or groups.
  const joinable = new Set(sel.map((b) => b.group?.[0] ?? b.id)).size > 1;
  const splittable = sel.some((b) => b.group);
  // What a click on a block picks: its whole group, or the block alone once a part of its group is picked.
  const unit = (id: string) => {
    const mates = grouped([id], blocks);
    const picked = mates.filter((i) => ids.includes(i)).length;
    return picked && picked < mates.length ? [id] : mates;
  };
  function join() {
    if (!joinable) return;
    const id = crypto.randomUUID();
    const inside = new Set(wide.map((b) => b.id));
    // The group lies where its topmost block lay: its blocks keep their order, and nothing lies between them.
    const order = [...blocks].sort((a, b) => a.z - b.z);
    const members = order.filter((b) => inside.has(b.id));
    const last = order.indexOf(members.at(-1)!);
    const stack = [...order.slice(0, last).filter((b) => !inside.has(b.id)), ...members, ...order.slice(last + 1)];
    const z = new Map(stack.map((b, i) => [b.id, i + 1]));
    change((bs) => bs.map((b) => ({ ...b, z: z.get(b.id)!, ...(inside.has(b.id) && { group: [id, ...(b.group ?? [])] }) })));
    setIds(wide.map((b) => b.id));
  }
  // Ungrouping takes the outermost group away; the groups in it stay.
  function split() {
    if (!splittable) return;
    place(wide.map((b) => [b.id, { group: b.group && b.group.length > 1 ? b.group.slice(1) : undefined }]));
    setIds(wide.map((b) => b.id));
  }
  // To the front or the back, as in PowerPoint: a part of a group moves within that group, a whole group as one thing.
  // With `one` a single step instead: over the next thing that does not move, a block or a whole group.
  // The new stack from back to front, or nothing where all already lies there.
  function stacked(front: boolean, one = false) {
    const whole = (g: string) => blocks.every((b) => !b.group?.includes(g) || ids.includes(b.id));
    // What a block moves in: its innermost group that is not picked whole, or the page.
    const level = (b: Block) => b.group?.filter((g) => !whole(g)).at(-1);
    const order = [...blocks].sort((a, b) => a.z - b.z);
    let stack = order;
    for (const g of new Set(sel.map(level))) {
      // The blocks of this level swap places among themselves, so the stack around them stays as it is.
      const part = stack.filter((b) => !g || b.group?.includes(g));
      const moved = part.filter((b) => sel.includes(b) && level(b) === g);
      const rest = part.filter((b) => !moved.includes(b));
      let next = front ? [...rest, ...moved] : [...moved, ...rest];
      if (one) {
        // What steps as one thing in this level: a block, or a group right inside it.
        const top = (b: Block) => b.group?.[g ? b.group.indexOf(g) + 1 : 0] ?? b.id;
        const units: Block[][] = [];
        for (const b of part) {
          if (units.length && top(units.at(-1)![0]) === top(b)) units.at(-1)!.push(b);
          else units.push([b]);
        }
        // From the end they step towards, so several keep their order. Backward is forward on the stack turned over.
        if (!front) units.reverse();
        for (let i = units.length - 2; i >= 0; i--) {
          if (moved.includes(units[i][0]) && !moved.includes(units[i + 1][0])) [units[i], units[i + 1]] = [units[i + 1], units[i]];
        }
        next = (front ? units : units.reverse()).flat();
      }
      stack = stack.map((b) => (part.includes(b) ? next.shift()! : b));
    }
    if (!stack.every((b, i) => b === order[i])) return stack;
  }
  // What already lies there leaves nothing to undo.
  function raise(front: boolean, one = false) {
    const stack = stacked(front, one);
    if (!stack) return;
    const z = new Map(stack.map((b, i) => [b.id, i + 1]));
    place(blocks.map((b) => [b.id, { z: z.get(b.id)! }]));
  }
  // A button of the order that greys with its press gives the focus to its pair, which the press made live, so who
  // works the panel with the keys stays where they were.
  function layer(e: Click<HTMLButtonElement>, front: boolean, one = false) {
    const el = e.currentTarget;
    const had = document.activeElement === el;
    flushSync(() => raise(front, one));
    if (had && el.disabled) ((el.nextElementSibling ?? el.previousElementSibling) as HTMLElement | null)?.focus();
  }

  // Puts the blocks where they belong, rounded. What already lies there leaves nothing to undo.
  function bring(to: [Block, Partial<Record<"x" | "y" | "w" | "h", number>>][]) {
    const boxes = to.map(([b, box]) => [b, Object.entries(box).map(([side, n]) => [side as "x" | "y" | "w" | "h", round(n)] as const)] as const);
    if (boxes.every(([b, box]) => box.every(([side, n]) => round(b[side]) === n))) return;
    place(boxes.map(([b, box]) => [b.id, Object.fromEntries(box)]));
  }
  // A thing lines up by the box around its outlines, a turned block's too, and moves whole.
  function align(axis: Axis, at: number) {
    const size = axis === "x" ? "w" : "h";
    const boxes = things.map((t) => bounds(t.map(inked)));
    // One thing lines up with the page. Several do so with each other, or with the page when the switch says so.
    const lo = among ? Math.min(...boxes.map((b) => b[axis])) : 0;
    const hi = among ? Math.max(...boxes.map((b) => b[axis] + b[size])) : axis === "x" ? W : H;
    bring(things.flatMap((t, i) => t.map((b) => [b, { [axis]: b[axis] + lo + (hi - lo - boxes[i][size]) * at - boxes[i][axis] }])));
  }
  // As wide as the widest, or as high as the highest, by the outlines. Each outline keeps its corner; a picture and a
  // symbol keep their shape.
  function same(side: "w" | "h") {
    const other = side === "w" ? "h" : "w";
    const to = Math.max(...sizable.map((b) => outline(b)[side]));
    bring(
      sizable.map((b) => {
        const [c, s] = dir(b).map(Math.abs);
        // Of a turned block the side that lies more along this one grows, until the outline is that large.
        const along = c >= s ? side : other;
        const across = along === "w" ? "h" : "w";
        const k = to / outline(b)[side];
        const sized = b.type === "image" || b.type === "symbol" || b.type === "hunderterfeld" ? { ...b, w: b.w * k, h: b.h * k } : { ...b, [along]: (to - b[across] * Math.min(c, s)) / Math.max(c, s) };
        const [was, now] = [outline(b), outline(sized)];
        return [b, { x: sized.x + was.x - now.x, y: sized.y + was.y - now.y, w: sized.w, h: sized.h }];
      }),
    );
  }
  function distribute(axis: Axis) {
    const size = axis === "x" ? "w" : "h";
    const row = things.map((t) => ({ t, box: bounds(t.map(inked)) })).sort((a, b) => a.box[axis] - b.box[axis]);
    // Between the outer things, or between the page's edges. One thing goes to the middle of the frame.
    const lo = among ? Math.min(...row.map((r) => r.box[axis])) : 0;
    const hi = among ? Math.max(...row.map((r) => r.box[axis] + r.box[size])) : axis === "x" ? W : H;
    const sum = row.reduce((total, r) => total + r.box[size], 0);
    const gap = row.length > 1 ? (hi - lo - sum) / (row.length - 1) : 0;
    let next = row.length > 1 ? lo : (lo + hi - sum) / 2;
    bring(
      row.flatMap(({ t, box }) => {
        const by = next - box[axis];
        next += box[size] + gap;
        return t.map((b) => [b, { [axis]: b[axis] + by }]);
      }),
    );
  }

  // Moveable works in whole pixels of the layout and leaves what it snaps up to two off the guide.
  // This is how far to move so that the nearest of `parts` that close lies exactly on it.
  const pull = (at: number, parts: number[], guides: number[]) =>
    parts
      .flatMap((part) => guides.map((g) => g - at - part))
      .filter((d) => Math.abs(d) < 2 / K)
      .sort((a, b) => Math.abs(a) - Math.abs(b))[0] ?? 0;
  const edge = (at: number, guides: number[]) => at + pull(at, [0], guides);

  // Moveable reports px of the layout, the document keeps mm. It reads the new size back at once, so render before returning.
  // A group snaps as one box, by its edges or its centre, and all its blocks move by the same amount.
  const drag = (events: OnDrag[], finger: { clientX: number; clientY: number } = events[0]) => {
    edgeScroll(finger.clientX, finger.clientY);
    // A finger that holds never rests still: nothing moves until it has left where it came down. Once a block has
    // moved, the blocks are new ones, and they follow the finger back there too. Of a group only the event of the
    // whole says where the finger is: those of its blocks say where a snap would put them.
    // Moveable says nothing more while a snap holds the blocks, so what is dropped here is kept for the finger's
    // own move to bring back once it has left.
    const still = touch.current && blocks.includes(start.current[0]) && Math.hypot(finger.clientX - came.current[0], finger.clientY - came.current[1]) <= SLOP;
    owed.current = still ? events : undefined;
    if (still) return;
    const from = events.map((e) => blocks.find((b) => b.id === idOf(e.target))!);
    // The desk's scroll has moved the blocks by `deskShift` since Moveable last measured them.
    const to = events.map((e, i) => ({ ...from[i], x: e.left / K, y: e.top / K + deskShift.current }));
    let [dx, dy] = (["x", "y"] as const).map((axis) => {
      // A turned block snaps by its outline.
      const [lo, hi] = span(to.map(outline), axis);
      return round(to[0][axis] + pull(lo, [0, (hi - lo) / 2, hi - lo], axis === "x" ? xs : ys) - from[0][axis]);
    });
    // Shift keeps the move level or upright: the shorter way from where the drag began does not count.
    if (mod & KEEP) {
      const began = start.current.find((b) => b.id === from[0].id)!;
      if (Math.abs(from[0].x + dx - began.x) >= Math.abs(from[0].y + dy - began.y)) dy = began.y - from[0].y;
      else dx = began.x - from[0].x;
    }
    flushSync(() => place(from.map((b) => [b.id, { x: round(b.x + dx), y: round(b.y + dy) }]), "drag"));
  };
  const begin = (els: Element[]) => {
    owed.current = undefined;
    ahead.current = hist.future;
    start.current = els.map((el) => blocks.find((b) => b.id === idOf(el))!);
    deskShift.current = 0;
  };
  // Near the top or the bottom of the desk a block drag scrolls it, faster the nearer the pointer is to the edge, and the
  // blocks go with it so they stay under the pointer. The scroll goes on while the pointer rests there.
  const deskShift = useRef(0);
  const deskAuto = useRef({ frame: 0, speed: 0, x: 0, y: 0, last: 0, rest: 0 });
  function edgeScroll(x: number, y: number) {
    const view = desk.current!.getBoundingClientRect();
    const zone = 40;
    const down = (y - (view.bottom - zone)) / zone;
    const up = (view.top + zone - y) / zone;
    const a = deskAuto.current;
    a.x = x;
    a.y = y;
    a.speed = (down > 0 ? Math.min(1, down) : up > 0 ? -Math.min(1, up) : 0) * 12;
    if (!a.speed) stopDeskScroll();
    else if (!a.frame) a.frame = requestAnimationFrame(deskStep);
  }
  function stopDeskScroll() {
    const a = deskAuto.current;
    cancelAnimationFrame(a.frame);
    a.frame = 0;
    a.speed = 0;
    a.last = 0;
    a.rest = 0;
  }
  // Px per 1/60 s, as the panel's scroll: the desk keeps its pace on a slow machine too.
  function deskStep(now: number) {
    const a = deskAuto.current;
    a.frame = 0;
    if (!a.speed || !moveable.current?.isDragging()) return;
    const dt = a.last ? Math.min(now - a.last, 100) : 1000 / 60;
    a.last = now;
    a.rest += (a.speed * dt) / (1000 / 60);
    const px = Math.trunc(a.rest);
    a.rest -= px;
    if (px) {
      desk.current!.scrollTop += px;
      const mm = px / k;
      deskShift.current += mm;
      const ids = start.current.map((b) => b.id);
      change((bs) => bs.map((b) => (ids.includes(b.id) ? { ...b, y: b.y + mm } : b)), "drag");
    }
    a.frame = requestAnimationFrame(deskStep);
  }
  // With Ctrl held when a move ends, copies stay where the blocks began.
  const leave = (moved: boolean) => {
    owed.current = undefined;
    stopDeskScroll();
    if (!moved) return;
    // With Ctrl the copies stay where the blocks began, on their page; the blocks themselves may go to another.
    const copies = mod & CENTRE ? cloned(start.current, live.current.doc.pages[page].blocks) : [];
    if (!toPageUnder(copies) && copies.length) change((bs) => [...bs, ...copies], "drag");
  };
  // A drop over another page moves the blocks to it, each group or block to the page under its own middle, or the
  // nearest page when that lies in a gap or past the last page. There it lies whole on the page, in front of the
  // blocks it finds, and where it was on the screen. One step with the drag. Says whether a block changed pages.
  const toPageUnder = (copies: Block[]) => {
    const own = live.current.doc.pages[page].blocks;
    const ids = start.current.map((b) => b.id);
    // The pages alone: a page's own guide has a tab with its page's number too, out in the gap above it.
    const sheets = [...desk.current!.querySelectorAll<HTMLElement>(".sheet[data-page]")].map((el) => [+el.dataset.page!, el.getBoundingClientRect()] as const);
    const was = sheet.current!.getBoundingClientRect();
    const away = new Map<number, Block[]>();
    for (const t of new Set(own.filter((b) => ids.includes(b.id)).map(thing))) {
      const unit = own.filter((b) => ids.includes(b.id) && thing(b) === t);
      const rects = unit.flatMap((b) => [...sheet.current!.querySelectorAll(`.block[data-id="${b.id}"]`)].map((el) => el.getBoundingClientRect()));
      if (!rects.length) continue;
      const mid = (Math.min(...rects.map((r) => r.top)) + Math.max(...rects.map((r) => r.bottom))) / 2;
      const gap = (r: DOMRect) => Math.max(0, r.top - mid, mid - r.bottom);
      const [n, now] = sheets.reduce((a, b) => (gap(b[1]) < gap(a[1]) ? b : a));
      // The own page takes the unit back only when the middle lies off it, in the gap: then it is clamped onto it.
      if (n === page && gap(was) === 0) continue;
      const [W, H] = sizes[n];
      const [x, right] = span(unit, "x");
      const [y, bottom] = span(unit, "y");
      // The unit keeps the page margin on every side. A unit too big for the text area stands in the middle of
      // the paper, so that neither end lies on its edge.
      const fit = (from: number, to: number, size: number, by: number) =>
        to - from > size - 2 * MARGIN ? (size - to - from) / 2 : Math.max(MARGIN - from, Math.min(size - MARGIN - to, by));
      const dx = fit(x, right, W, (was.left - now.left) / k);
      const dy = fit(y, bottom, H, (was.top - now.top) / k);
      away.set(n, [...(away.get(n) ?? []), ...unit.map((b) => ({ ...b, x: round(b.x + dx), y: round(b.y + dy) }))]);
    }
    if (!away.size) return false;
    const gone = new Set([...away.values()].flat().map((b) => b.id));
    const to = [...away.keys()][0];
    update(
      (doc) => ({
        ...doc,
        pages: doc.pages.map((p, i) => {
          if (i === page) return { ...p, blocks: [...p.blocks.filter((b) => !gone.has(b.id)), ...(away.get(page) ?? []), ...copies] };
          const come = away.get(i);
          if (!come) return p;
          const top = Math.max(0, ...p.blocks.map((b) => b.z)) - Math.min(...come.map((b) => b.z)) + 1;
          return { ...p, blocks: [...p.blocks, ...come.map((b) => ({ ...b, z: b.z + top }))] };
        }),
      }),
      "drag",
      to,
      page,
    );
    setAt(to);
    setIds((away.get(to) ?? []).map((b) => b.id));
    return true;
  };
  // A handle on an edge leaves the other axis as it is, to the hundredth of a mm, unless the block keeps its shape.
  const resize = (events: OnResize[]) =>
    flushSync(() =>
      place(
        events.map((e) => {
          const [dx, dy] = e.direction;
          const b = start.current.find((b) => b.id === idOf(e.target))!;
          let [w, h] = [round(e.width / K), round(e.height / K)];
          // A turned block turns about its centre, and a new size moves that: the centre goes where the point
          // across from the handle, or with Ctrl the middle, stays in its place on the page.
          if (b.angle && events.length === 1) {
            // A handle on an edge leaves the other axis as it began.
            [w, h] = [dx || keep ? w : b.w, dy || keep ? h : b.h];
            const [c, s] = dir(b);
            const [lx, ly] = mod & CENTRE ? [0, 0] : [(dx * (w - b.w)) / 2, (dy * (h - b.h)) / 2];
            return [b.id, { x: round(b.x + b.w / 2 + lx * c - ly * s - w / 2), y: round(b.y + b.h / 2 + lx * s + ly * c - h / 2), w, h }];
          }
          // In a selection Moveable says where a turned block goes, on both axes whichever handle moved.
          const box = {
            ...((dx || keep || b.angle) && { x: round(e.drag.left / K), w }),
            ...((dy || keep || b.angle) && { y: round(e.drag.top / K), h }),
          };
          return [b.id, box];
        }),
        "drag",
      ),
    );
  // The middle a thing turns about is the one a turn used that left its blocks as they lie now, also one undone
  // since or called off by Escape: so a turn and its back come to the same place. Else it is the middle of the
  // level box around the thing (undefined here), and a quarter turn of it stays on the hundredths, so none is kept.
  const keyOf = (part: Block[]) => part.map((b) => b.id).join();
  const keptOf = (part: Block[]) => pivots.current.get(JSON.stringify(part));
  const turnThing = (part: Block[], by: number, at = keptOf(part)) => {
    const to = swung(part, by, at);
    if (at || by % 90) {
      const all = hull(part);
      if (pivots.current.size > 1000) pivots.current.clear();
      pivots.current.set(JSON.stringify(to), at ?? [all.x + all.w / 2, all.y + all.h / 2]);
    }
    return to;
  };
  // A turn follows the handle from the angles the blocks began with: `by` is how far it has gone. With Shift one
  // block stops at every 15 degrees. A group picked whole turns as one about the middle of the box around it, in
  // steps of 15 degrees with Shift; each loose block turns about its own centre.
  const twist = (by: number, shift: boolean) => {
    const from = start.current;
    const stop = (a: number) => (shift || mod & KEEP ? Math.round(a / 15) * 15 : a);
    const parts = [...new Set(from.map(thing))].map((t) => from.filter((b) => thing(b) === t));
    // The middle of each thing is looked up once, when the drag begins, and then kept for the whole drag.
    if (dragFrom.current !== from) {
      dragFrom.current = from;
      dragAt.current = new Map(parts.map((part) => [keyOf(part), keptOf(part)]));
    }
    const to = new Map(
      parts
        .flatMap((part) => {
          const first = part[0].angle ?? 0;
          return turnThing(part, part.length > 1 ? stop(by) : stop(first + by) - first, dragAt.current.get(keyOf(part)));
        })
        .map((b) => [b.id, b]),
    );
    flushSync(() =>
      change(
        (bs) =>
          bs.map((b) => {
            const t = to.get(b.id);
            if (!t) return b;
            return (isLine(t) ? { ...b, x: t.x, y: t.y, w: t.w, h: t.h, props: { ...b.props, from: t.props.from } } : { ...b, x: t.x, y: t.y, angle: t.angle }) as Block;
          }),
        "drag",
      ),
    );
  };
  // A press on the handle that turns is a click until the pointer has left its spot, by as much as a click on a
  // block may: a hand moves the mouse a pixel or two, and that turns nothing.
  const rotate = (e: OnRotate | OnRotateGroup) => {
    if (spot.current && Math.hypot(e.clientX - spot.current[0], e.clientY - spot.current[1]) < 3) return;
    spot.current = undefined;
    twist(e.dist, e.inputEvent.shiftKey);
  };
  // The handle lies over the block above the selection, so a click on it is that block's. Over empty paper it is none.
  const rotated = (e: OnRotateEnd) => {
    const under = spot.current && document.elementsFromPoint(e.clientX, e.clientY).find((el) => el.matches(".block:not(.sel)"));
    if (under) pick(under, e.inputEvent.shiftKey);
  };
  // The panel's buttons turn and mirror each thing by itself, in one step: a group picked whole goes as one about
  // the middle of the box around it, as the handle turns it and as in PowerPoint, and a loose block about its own.
  const each = (go: (thing: Block[]) => Block[]) => {
    const to = new Map(things.flatMap(go).map((b) => [b.id, b]));
    change((bs) => bs.map((b) => to.get(b.id) ?? b));
  };
  const spin = (by: number) => each((t) => turnThing(t, by));
  const mirror = (axis: Axis) => each((t) => mirrored(t, axis));
  // Moveable measures a block again after each step of a resize, so a pull would throw it off: the edges settle when it ends.
  // So does a text the resize left higher than its box.
  // `dx` and `dy` say which handle moved: -1 the left or top edges, 1 the right or bottom ones.
  const settle = ([dx, dy]: number[]) => {
    tight.current = true;
    place(
      // A turned block's edges are not level, so no guide pulls them.
      free.filter((b) => !b.angle).map((b) => {
        const [x, y] = [dx < 0 ? round(edge(b.x, xs)) : b.x, dy < 0 ? round(edge(b.y, ys)) : b.y];
        const [right, bottom] = [dx > 0 ? edge(b.x + b.w, xs) : b.x + b.w, dy > 0 ? edge(b.y + b.h, ys) : b.y + b.h];
        return [b.id, { x, y, w: round(right - x), h: round(bottom - y) }];
      }),
      "drag",
    );
  };
  // Tab goes to the next cell of a table and Shift+Tab to the one before, as in PowerPoint. Past the last cell a
  // new row begins.
  // The text of cells on the system's clipboard, as copy() does for blocks: the browser's copy first, then the fallback.
  function copyCells(tsv: string) {
    cellsCopied.current = tsv;
    pending.current = tsv;
    document.execCommand("copy");
    markCopy(tsv);
    if (pending.current === null) return;
    pending.current = null;
    navigator.clipboard?.writeText(tsv).catch(() => {});
  }
  function hop(e: Key<HTMLTextAreaElement>, b: TableBlock) {
    // Escape and F2 end the writing themselves: after a press in the panel a blur would not.
    if (e.key === "Escape" || e.key === "F2") {
      setEditing("");
      setReach(undefined);
    }
    // With two or more cells picked, the keys work on all of them: Entf and Backspace empty them, Ctrl+C copies them as
    // text, Ctrl+X copies and empties them. The cells stay picked. Ctrl+V is the paste, see onPaste.
    if (reach !== undefined && slotsIn(b.props, rectOf(b.props, slot, reach)).length > 1) {
      const rect = rectOf(b.props, slot, reach);
      const ctrl = e.ctrlKey || e.metaKey;
      const key = e.key.toLowerCase();
      if (ctrl && (key === "c" || key === "x")) {
        e.preventDefault();
        copyCells(tsvOf(b.props, rect));
        if (key === "x") {
          mergeKey.current = "";
          tight.current = true;
          sink.current = snug(b);
          change((bs) => bs.map((o) => (o.id === b.id ? { ...b, props: emptied(b.props, rect) } : o)));
        }
        return;
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        // Not through the field's change, which would drop the pick.
        mergeKey.current = "";
        tight.current = true;
        sink.current = snug(b);
        change((bs) => bs.map((o) => (o.id === b.id ? { ...b, props: emptied(b.props, rect) } : o)));
        return;
      }
    }
    // An arrow at the edge of the text goes on to the next cell, when there is one in that way.
    const plain = !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey;
    const field = e.currentTarget;
    const at = field.selectionStart;
    const line = sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] [data-cell="${slot}"] p.open`);
    let to: number | undefined;
    if (e.key.startsWith("Arrow")) setReach(undefined);
    if (plain && line && at === field.selectionEnd) {
      if (e.key === "ArrowLeft" && at === 0) to = next(b.props, slot, -1);
      if (e.key === "ArrowRight" && at === field.value.length) to = next(b.props, slot, 1);
      if (e.key === "ArrowUp" && sameLine(line, at, 0)) to = beside(b.props, slot, "up");
      if (e.key === "ArrowDown" && sameLine(line, at, field.value.length)) to = beside(b.props, slot, "down");
    }
    if (to !== undefined) {
      e.preventDefault();
      mergeKey.current = "";
      setReach(undefined);
      setSlot(to);
      return;
    }
    if (e.key !== "Tab") return;
    e.preventDefault();
    // What is typed in the next cell is an undo step of its own.
    mergeKey.current = "";
    setReach(undefined);
    const after = next(b.props, slot, e.shiftKey ? -1 : 1);
    if (after !== undefined) {
      // The next cell's text is picked, so that typing replaces it.
      entire.current = true;
      setSlot(after);
    }
    else if (!e.shiftKey) {
      const rows = b.props.cells.length;
      rank(b, "row", rows, true);
      setSlot(rows * b.props.cols.length);
    }
  }
  // Whether the caret at `at` of a cell's text stands on its first (0) or last line: the same top as the text's edge.
  function sameLine(line: HTMLElement, at: number, edge: number) {
    const top = (n: number) => {
      let left = n;
      const walk = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
      for (let t = walk.nextNode() as Text | null; t; t = walk.nextNode() as Text | null) {
        if (left <= t.length) {
          const range = document.createRange();
          range.setStart(t, left);
          range.collapse(true);
          return range.getBoundingClientRect().top;
        }
        left -= t.length;
      }
      return line.getBoundingClientRect().top;
    };
    return Math.abs(top(at) - top(edge)) < 2;
  }
  // Makes the picked cells of the table being edited one cell. It is one step of undo.
  function merge() {
    if (!table || reach === undefined) return;
    const rect = rectOf(table.props, slot, reach);
    mergeKey.current = "";
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: merged(table.props, rect) } : o)));
    setSlot(rect[0] * table.props.cols.length + rect[1]);
    setReach(undefined);
  }
  // Brings back the single cells of the merged cell at the open cell. The freed cells stay picked.
  function unmerge() {
    if (!table) return;
    const [r, c, h, w] = spanAt(table.props, slot);
    if (h * w < 2) return;
    mergeKey.current = "";
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: unmerged(table.props, slot) } : o)));
    setReach((r + h - 1) * table.props.cols.length + c + w - 1);
  }
  // The heights of the rows as the grid lays them out now, in mm.
  // The grid's rows after the table's own hold no cells: the box of solution words is one. No heights are known
  // while the grid has not laid its rows out.
  const mmOf = (px: string) => {
    const all = px.split(" ").slice(0, table?.props.cells.length).map((p) => parseFloat(p) / K);
    return all.length === table?.props.cells.length && !all.some(Number.isNaN) ? all : [];
  };
  const laidMm = mmOf(laid);
  // The heights in mm that the rows' texts need, read from the grid with its rows free.
  function needs(grid: HTMLElement): number[] {
    const [rows, height] = [grid.style.gridTemplateRows, grid.style.height];
    grid.style.gridTemplateRows = "none";
    grid.style.height = "auto";
    const px = getComputedStyle(grid).gridTemplateRows;
    grid.style.gridTemplateRows = rows;
    grid.style.height = height;
    return mmOf(px);
  }
  // Sets the width of the picked columns, or the open cell's, or the height of the rows. With cells picked each
  // one becomes `mm`; else the open cell's lines keep their share and sum to `mm`. It is one step of undo.
  function sizeCells(axis: "col" | "row", mm: number) {
    if (!table || !(mm > 0)) return;
    const [r, c, h, w] = spanAt(table.props, slot);
    const [r0, c0, r1, c1]: Rect = reach === undefined ? [r, c, r + h - 1, c + w - 1] : rectOf(table.props, slot, reach);
    const each = reach !== undefined;
    const [from, to] = axis === "col" ? [c0, c1] : [r0, r1];
    const least = axis === "col" ? 5 : 0;
    const value = each ? Math.max(least, mm) : Math.max(least * (to - from + 1), mm);
    const base = axis === "col" ? widthsOf(table.props.cols, table.w) : laidMm;
    if (!base.length) return;
    // A share rounded to nothing would be no height at all.
    const sizes = sized(base.map(round), from, to, value, each).map((s) => Math.max(0.01, round(s)));
    tight.current = true;
    change((bs) =>
      bs.map((o) =>
        o.id !== table.id ? o : axis === "col" ? { ...table, w: round(sum(sizes) + EDGE), props: { ...table.props, cols: sizes } } : { ...table, h: round(sum(sizes) + EDGE), props: { ...table.props, rows: sizes } },
      ),
    );
  }
  // Makes the picked columns or rows equal within the room they hold: all of them with no cell picked. The rows
  // take the higher of their share and the height their texts need. It is one step of undo.
  function evenCells(axis: "col" | "row") {
    if (!table) return;
    const all: Rect = [0, 0, table.props.cells.length - 1, table.props.cols.length - 1];
    const [r0, c0, r1, c1] = reach === undefined ? all : rectOf(table.props, slot, reach);
    const [from, to] = axis === "col" ? [c0, c1] : [r0, r1];
    tight.current = true;
    if (axis === "col") {
      const cols = evened(widthsOf(table.props.cols, table.w), from, to).map(round);
      change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: { ...table.props, cols } } : o)));
      return;
    }
    const grid = sheet.current!.querySelector<HTMLElement>(`[data-id="${table.id}"] .table`);
    if (!grid || !laidMm.length) return;
    const top = needs(grid).slice(from, to + 1);
    const picked = laidMm.slice(from, to + 1);
    const share = round(Math.max(sum(picked) / picked.length, ...top));
    const rows = sized(laidMm.map(round), from, to, share, true).map(round);
    change((bs) => bs.map((o) => (o.id === table.id ? { ...table, h: round(sum(rows) + EDGE), props: { ...table.props, rows } } : o)));
  }
  // Sets the line style or width of every picked table, each line of it. A drag of the slider passes its `key`, so that
  // the whole drag is one step of undo.
  function drawLines(patch: { style?: LineStyle; width?: number }, key?: string) {
    if (!key) tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === "table" ? ({ ...b, props: lined(b.props, patch) } as Block) : b)), key);
  }
  // Draws the pen on the chosen borders: of the cells picked with the open one, or of the open cell alone, or with no
  // cell open, of the whole table. It is one step of undo, and the cells stay picked.
  function border(which: Border, pen: Pen) {
    if (!table) return;
    const open = editing === table.id;
    const [r, c, h, w] = spanAt(table.props, slot);
    const rect: Rect = !open ? [0, 0, table.props.cells.length - 1, table.props.cols.length - 1] : reach === undefined ? [r, c, r + h - 1, c + w - 1] : rectOf(table.props, slot, reach);
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: bordered(table.props, rect, which, pen) } : o)));
  }
  // Turns Schneidelinien on or off for every picked table.
  function cutting(on: boolean) {
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === "table" ? ({ ...b, props: cutLines(b.props, on) } as Block) : b)));
  }
  // Adds an empty row or column to a table before the one at `i`, or takes the one at `i` away; the last one
  // stays. A new row adds its height to the block, a line of text with the cell's padding and line, and
  // a row that goes takes with it the height it has now. The field stays with its cell, and goes to a neighbour
  // when its cell goes.
  function rank(b: TableBlock, axis: "row" | "col", i: number, add: boolean, after = false) {
    const [rows, cols] = [b.props.cells.length, b.props.cols.length];
    const n = axis === "row" ? rows : cols;
    if (!add && n < 2) return;
    // A row's height is read from its first cell, or from the grid when that cell is covered or spans rows.
    const table = sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] .table`)!;
    const first = table.querySelector<HTMLElement>(`[data-cell="${i * cols}"]`);
    const gone = first && !first.dataset.span ? first.getBoundingClientRect().height / k : parseFloat(getComputedStyle(table).gridTemplateRows.split(" ")[i]) / K;
    const dh = axis === "col" ? 0 : add ? b.props.size * PT * 1.6 + 0.25 : -gone;
    // A column that comes or goes takes its average width or its own width from the block, so the others keep theirs.
    const widths = widthsOf(b.props.cols, b.w);
    // A new column widens the table only to the right margin; there the columns narrow (#602).
    const dw = axis === "row" ? 0 : add ? Math.min(sum(widths) / widths.length, Math.max(0, W - MARGIN - b.x - b.w)) : -widths[i];
    const to = (at: number) => (add ? at + +(i <= at) : Math.min(at - +(i < at), n - 2));
    const [r, c] = [Math.floor(slot / cols), slot % cols];
    const target = axis === "row" ? to(r) * cols + c : r * (cols + (add ? 1 : -1)) + to(c);
    const props = spliced(b.props, axis, i, add, after);
    if (add && target !== slot) caret.current = sheet.current!.querySelector<HTMLTextAreaElement>(".table textarea")?.selectionStart;
    setSlot(anchorOf(props, target));
    setReach(undefined);
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === b.id ? { ...b, w: round(b.w + dw), h: round(b.h + dh), props } : o)));
  }
  // Moves the line right of column `i` with the pointer. The columns on its two sides share the width they had,
  // and each keeps 5 mm, or half of it where they have less.
  function widen(e: PointerEvent, b: TableBlock, i: number) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const cols = [...b.props.cols];
    const mm = b.w / sum(cols);
    const left = sum(cols.slice(0, i));
    const pair = cols[i] + cols[i + 1];
    const least = Math.min(5 / mm, pair / 2);
    cols[i] = Math.max(least, Math.min(pair - least, (point(e)[0] - b.x) / mm - left));
    cols[i + 1] = pair - cols[i];
    style("table", { cols }, "drag");
  }
  // Where the line right of column `i` shows, as [top, height] in mm of the page: all of the table's height, or
  // the rows between the merged cells that lie over it. The rows' heights are the grid's own (`laid`).
  function shown(b: TableBlock, i: number): [number, number][] {
    const over = spansOf(b.props).filter(([, c, , w]) => c <= i && i + 1 < c + w);
    if (!over.length) return [[b.y, b.h]];
    const heights = laid.split(" ").map((px) => parseFloat(px) / K);
    if (heights.length < b.props.cells.length || heights.some(Number.isNaN)) return [];
    const free = b.props.cells.map((_, r) => !over.some(([at, , h]) => r >= at && r < at + h));
    return free.flatMap((is, r) => (is && !free[r - 1] ? [[b.y + sum(heights.slice(0, r)), sum(heights.slice(r, free.indexOf(false, r) < 0 ? free.length : free.indexOf(false, r)))] as [number, number]] : []));
  }
  // An end handle remembers where the pointer took hold of it, so the end does not jump under the finger.
  function grip(e: PointerEvent) {
    const at = e.currentTarget.getBoundingClientRect();
    grab.current = [e.clientX - at.left - at.width / 2, e.clientY - at.top - at.height / 2];
    ahead.current = hist.future;
    grasp.current = { el: e.currentTarget, id: e.pointerId, draft };
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  // Where on the page, in mm, the pointer puts the handle it holds.
  function point(e: PointerEvent) {
    const page = e.currentTarget.closest(".sheet")!.getBoundingClientRect();
    return [(e.clientX - grab.current[0] - page.left) / k, (e.clientY - grab.current[1] - page.top) / k];
  }
  // The guide closest to a point, if one lies within the snap distance.
  const near = (at: number, guides: number[]) => guides.filter((g) => Math.abs(g - at) < 6 / k).sort((a, b) => Math.abs(a - at) - Math.abs(b - at))[0];
  // Moves one end of a line with the pointer; the other end stays, or with Ctrl the middle does. It snaps to the
  // guides a block drag snaps to, and to the point that stays, which makes the line level or upright.
  function stretch(e: PointerEvent, b: ShapeBlock, end: boolean) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const mid = (mod & CENTRE) > 0;
    let fx = mid ? b.x + b.w / 2 : b.x + (far(b, 1, !end) ? b.w : 0);
    let fy = mid ? b.y + b.h / 2 : b.y + (far(b, 0, !end) ? b.h : 0);
    const at = point(e);
    // Shift turns the line in steps of 45 degrees and leaves the guides alone.
    const turn = (Math.round(Math.atan2(at[1] - fy, at[0] - fx) / (Math.PI / 4)) * Math.PI) / 4;
    const reach = Math.hypot(at[0] - fx, at[1] - fy);
    const gx = mod & KEEP ? fx + Math.cos(turn) * reach : near(at[0], loose ? [] : [fx, ...xs]);
    const gy = mod & KEEP ? fy + Math.sin(turn) * reach : near(at[1], loose ? [] : [fy, ...ys]);
    setGuide(mod & KEEP ? [] : [gx, gy]);
    const [px, py] = [gx ?? at[0], gy ?? at[1]];
    if (mid) [fx, fy] = [2 * fx - px, 2 * fy - py];
    const from = ((py > fy !== end ? "s" : "n") + (px > fx !== end ? "e" : "w")) as Corner;
    const box = { x: round(Math.min(px, fx)), y: round(Math.min(py, fy)), w: round(Math.abs(px - fx)), h: round(Math.abs(py - fy)) };
    change((bs) => bs.map((o) => (o.id === b.id ? { ...b, ...box, props: { ...b.props, from } } : o)), "drag");
  }
  // How far down the adjust handle of a triangle or a bubble stands from its point, in mm: 12 px inside the box, clear
  // of Moveable's handles on its edge.
  const pullOf = (kind?: string) => (kind === "triangle" ? 12 / k : kind === "bubble" ? -12 / k : 0);
  // A bubble's handle is pulled into the box only while its tip lies in the box: outside, the handle stands on the tip.
  const pullAt = (b: Block, [x, y]: [number, number]) => {
    const kind = (b.props as TextProps).kind;
    return kind === "bubble" && (x < 0 || y < 0 || x > b.w || y > b.h) ? 0 : pullOf(kind);
  };
  // Where the adjust handle of a block stands on the page, in mm: its point in the block's own frame, flipped and turned.
  function adjustAt(b: Block): [number, number] {
    const p = b.props as TextProps;
    const [lx, ly] = handleOf(p.kind, b.w, b.h, p)!;
    const [cx, cy] = [b.x + b.w / 2, b.y + b.h / 2];
    const [dx, dy] = [lx - b.w / 2, ly + pullAt(b, [lx, ly]) - b.h / 2];
    return turnedAt([cx + dx * (b.flipX ? -1 : 1), cy + dy * (b.flipY ? -1 : 1)], b.angle ?? 0, [cx, cy]);
  }
  // Moves the point of a picked speech bubble, star or triangle with the pointer, and sets its props on each picked block of the same kind.
  function adjust(e: PointerEvent, b: Block) {
    // A pointer with no button down holds nothing, whatever it held before.
    if (!e.buttons || (!e.currentTarget.hasPointerCapture(e.pointerId) && adjusting.current !== e.pointerId)) return;
    const p = b.props as TextProps;
    const [cx, cy] = [b.x + b.w / 2, b.y + b.h / 2];
    const [px, py] = turnedAt(point(e) as [number, number], -(b.angle ?? 0), [cx, cy]);
    const [fx, fy] = [cx + (px - cx) * (b.flipX ? -1 : 1), cy + (py - cy) * (b.flipY ? -1 : 1)];
    const raw: [number, number] = [fx - b.x, fy - b.y];
    const local: [number, number] = [raw[0], raw[1] - pullAt(b, raw)];
    const props = adjusted(p.kind, b.w, b.h, local);
    const same = new Set(sel.filter((o) => drawn(o) && !o.locked && (o.props as TextProps).kind === p.kind).map((o) => o.id));
    change((bs) => bs.map((o) => (same.has(o.id) ? ({ ...o, props: { ...o.props, ...props } } as Block) : o)), "drag");
  }
  // Resizes a group from the boxes it began with. The corner opposite the dragged one stays, or with Ctrl the middle,
  // and the group keeps its shape, as Moveable's groups do, so every line keeps its angle. A group can shrink to a
  // tenth, not flip.
  function scale(e: PointerEvent, right: boolean, low: boolean) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    // A turned group scales in its own frame: the pointer turns back to it, and the factor is taken there.
    const { turn, about, level } = turnedLine ? frameOf(start.current) : { turn: 0, about: [0, 0] as [number, number], level: start.current };
    const { x, y, w, h } = turnedLine ? bounds(level) : hull(level);
    const [px, py] = turn ? turnedAt(point(e) as [number, number], -turn, about) : point(e);
    const half = mod & CENTRE ? 2 : 1;
    const [fx, fy] = half > 1 ? [x + w / 2, y + h / 2] : [right ? x : x + w, low ? y : y + h];
    const [sw, sh] = [(right ? w : -w) / half, (low ? h : -h) / half];
    let s = Math.max(0.1, w && (px - fx) / sw, h && (py - fy) / sh);
    if (turn) {
      setGuide([]);
      place(scaledGroup(start.current, s, s, [fx, fy]).map(resized), "drag");
      return;
    }
    // The dragged corner snaps to the guides a block drag snaps to. The group keeps its shape, so only the nearer
    // of the two guides holds it.
    const [mx, my] = [fx + sw * s, fy + sh * s];
    const gx = w ? near(mx, xs.filter((g) => (g - fx) / sw >= 0.1)) : undefined;
    const gy = h ? near(my, ys.filter((g) => (g - fy) / sh >= 0.1)) : undefined;
    const onX = gx !== undefined && (gy === undefined || Math.abs(gx - mx) <= Math.abs(gy - my));
    if (onX) s = (gx - fx) / sw;
    else if (gy !== undefined) s = (gy - fy) / sh;
    setGuide(onX ? [gx] : [undefined, gy]);
    // Each size comes from its block's two edges, so the edge on the guide lands exactly on it.
    place(
      start.current.map((b) => {
        const [bx, by] = [round(fx + (b.x - fx) * s), round(fy + (b.y - fy) * s)];
        return [b.id, { x: bx, y: by, w: round(fx + (b.x + b.w - fx) * s - bx), h: round(fy + (b.y + b.h - fy) * s - by) }];
      }),
      "drag",
    );
  }

  // A new guide line starts in the middle of what the desk shows, clear of a guide already there.
  function rule(axis: Axis) {
    let at = axis === "x" ? W / 2 : Math.max(0, Math.min(H, Math.round(seen(desk.current!.clientHeight / 2))));
    while ([...guides[axis], ...mine[axis]].includes(at)) at += 10;
    rules(own ? page : undefined, (g) => ({ ...g, [axis]: [...g[axis], at] }));
  }
  // A guide line moves with its tab, in steps of the grid or of a millimetre. `n` is the page of a page's own line.
  function slide(e: PointerEvent, axis: Axis, i: number, n?: number) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const at = point(e)[axis === "x" ? 0 : 1];
    const by = loose ? 0.01 : cell || 1;
    const to = round(Math.round(at / by) * by);
    rules(n, (g) => ({ ...g, [axis]: g[axis].map((o, j) => (j === i ? to : o)) }), "drag");
  }
  // The tab of a guide line held now: its page, axis and number.
  const sliding = useRef("");
  // Let go off the page, a guide line is gone. Its place is read from the document as it stands, not from the last
  // render: the pointer may be let go before the page has drawn its last move (#525).
  function drop(axis: Axis, i: number, n?: number) {
    const on = (at: number) => at >= 0 && at <= (axis === "x" ? W : H);
    rules(n, (g) => (on(g[axis][i]) ? g : { ...g, [axis]: g[axis].filter((_, j) => j !== i) }), "drag");
  }

  // The PDF is made of what the server holds, so a change still waiting is saved first: after a save under way,
  // which may hold an older document. A save that fails or never answers holds the PDF up for 20 s at most.
  // The session is asked for first: where it is gone the login shows, and nothing goes to the PDF's address. The
  // PDF is fetched, so a failure leaves the sheet where it is, and goes to the browser as a download under the name
  // the server gives it. With no limit of time: a long sheet takes long to print.
  // The PDF waits for the clash's choice, and the bar says so.
  const holdPdf = (key: boolean) => void (waiting.current = key, setPdfWaits(true));
  async function pdf(key: boolean) {
    // A sheet deleted elsewhere: another try ends the same, so the line names the choice and has no button.
    const deleted = "Das PDF konnte nicht erstellt werden. Dieses Blatt wurde auf einem anderen Gerät gelöscht. Wähle „Als neues Blatt behalten“, dann gibt es wieder ein PDF.";
    const what = pdfFault;
    await attempt(what, async () => {
      // In a clash the server holds the other device's sheet: the PDF waits until the teacher has chosen. Also where
      // the save it waits for is the one turned down.
      if (inClash(file.id)) return holdPdf(key);
      // A newer version saved in another window is what prints: the editor shows it first (#720).
      dropFault(NEWER);
      await newerSheet();
      // Deleted elsewhere: the PDF has no sheet to print, and the line names the choice.
      if (isGone(file.id)) throw new Error("404");
      const current = await flush(file.id);
      if (inClash(file.id)) return holdPdf(key);
      await ask("/me");
      const res = await signed(
        fetch(`/api/sheets/${file.id}/pdf${key ? "?solved=true" : ""}`).then((res) => {
          if (!res.ok) throw new Error(String(res.status));
          return res;
        }),
      );
      const link = document.createElement("a");
      link.href = URL.createObjectURL(await res.blob());
      link.download = decodeURIComponent(/filename\*=UTF-8''(.+)/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "Blatt.pdf");
      link.click();
      // After the browser has taken the file.
      setTimeout(() => URL.revokeObjectURL(link.href), 60000);
      if (!current) note(what, "Das PDF zeigt den zuletzt gespeicherten Stand, nicht deine letzte Änderung: sie ist noch nicht gespeichert.");
    }, (s) => (s === "404" && isGone(file.id) ? deleted : undefined));
  }

  // The print variants: the dialog's choice lives here, so it stays while the editor is open.
  const [variants, setVariants] = useState(!!opened);
  // What opened the dialog: a press that came with a newer sheet prints once, and the line stays while the dialog is open.
  const [fromPress, setFromPress] = useState(opened);
  const [count, setCount] = useState(opened?.count ?? 2);
  const [letters, setLetters] = useState(opened?.letters ?? true);
  // The button that opened the dialog gets the focus back when it shuts.
  const variantsDoor = useRef<HTMLElement | null>(null);
  // The dialog's state while it is open, so a newer sheet from another tab or a focus reopens it as it stands.
  const dialogState = useRef<Opened | undefined>(undefined);
  dialogState.current = variants ? { count, letters, newer: true } : undefined;
  // A press that re-mounted the editor has the dialog open: Schließen gives the focus back to the bar's button.
  useEffect(() => {
    if (!opened) return;
    variantsDoor.current = bar.current?.querySelector<HTMLElement>('[aria-label="Varianten drucken"]') ?? bar.current?.querySelector<HTMLElement>(".more") ?? null;
  }, []);
  // A newer version saved in another window: the dialog opens on it, in the editor that shows it (#720).
  const openVariants = async (door: HTMLElement) => {
    dropFault(NEWER);
    if (await newerSheet({ count, letters, newer: true })) return;
    variantsDoor.current = door;
    setVariants(true);
  };

  // A template stored or deleted with the session run out brings the login. A second press while one is on its way
  // stores no second template. The name stays until the template is stored.
  const storing = useRef(false);
  async function store() {
    const made = { name: name.trim() };
    await attempt(
      "Die Vorlage konnte nicht gespeichert werden.",
      async () => {
        if (storing.current) return;
        storing.current = true;
        try {
          // The page as it stands at the try: a later one stores what the teacher sees then.
          const saved = await signed(post<Template>("/templates", { ...made, doc: live.current.doc }));
          setTemplates((ts) => [...ts, saved]);
          setName((now) => (now.trim() === made.name ? "" : now));
        } finally {
          storing.current = false;
        }
      },
      // A template the server refuses names what is wrong in it, and a try again would end the same.
      (_, e) => {
        const problems = (e as Refusal).problems;
        return problems ? `Die Vorlage konnte nicht gespeichert werden: das Blatt passt nicht zum Format. ${problems.join("; ")}` : undefined;
      },
    );
  }
  // A template takes the place of the sheet; undo brings the sheet back. A built-in one gets fresh seeds, and its
  // maths blocks fresh exercises from the server; a block whose request fails keeps its own. The sheet keeps its
  // Lernwörter unless the template brings some.
  // The last click wins: an apply still waiting for its exercises gives way to one started after it.
  const applied = useRef(0);
  async function apply(t: Template) {
    const turn = ++applied.current;
    const doc = read(t.doc);
    const pages = t.id > 0 ? doc.pages : await Promise.all(doc.pages.map(async (p) => ({
      ...p,
      blocks: await Promise.all(p.blocks.map(async (b): Promise<Block> => {
        const props = b.props as Record<string, unknown>;
        if (typeof props.seed !== "number") return b;
        const limits = { ...props, seed: newSeed() };
        if (b.type !== "maths") return { ...b, props: limits } as Block;
        const made = await generate(limits as Parameters<typeof generate>[0]).catch(() => undefined);
        if (!made) return b;
        // New exercises may need more room than the template's block: it grows, to the page's foot at most.
        const fresh = { ...limits, ...made };
        const h = Math.min(Math.max(b.h, mathsHeight(fresh as Parameters<typeof mathsHeight>[0])), 297 - b.y);
        return { ...b, h, props: fresh } as Block;
      })),
    })));
    if (turn !== applied.current) return;
    update((cur) => {
      const next = { ...doc, words: doc.words ?? cur.words };
      const words = wordsIn(next);
      const all = pages.flatMap((p) => p.blocks);
      return { ...next, pages: pages.map((p, n) => ({ ...p, blocks: growRulings(p.blocks, words, sizeOf(next, n)[0], sizeOf(next, n)[1], all) })) };
    });
    setIds([]);
  }
  async function forget(t: Template) {
    if (!confirm(`Vorlage „${t.name}“ löschen?`)) return;
    await attempt("Die Vorlage konnte nicht gelöscht werden.", async () => {
      // One deleted on another device is gone as asked: a 404 is no failure here.
      await signed(api(`/templates/${t.id}`, { method: "DELETE" })).catch((e: Error) => (e.message === "404" ? undefined : Promise.reject(e)));
      setTemplates((ts) => ts.filter((o) => o.id !== t.id));
    });
  }

  // `press` is the mouse press that selects, so the same press can drag.
  // `point` is where a click landed, if it was one: a text's caret opens there.
  function pick(el: Element, shift: boolean, press?: globalThis.MouseEvent, point?: [number, number]) {
    if (el.closest(".end, .adjust, .rule, .crop, .bar")) return;
    // A press beside the picture ends its crop.
    done();
    const id = el.closest<HTMLElement>(".block")?.dataset.id;
    const more = shift || multi;
    const to = pageOf(el);
    if (brush) {
      // The brush ends with the block it paints, unless a double click keeps it, and with a press on the empty page.
      if (brush === 1 || !id) setBrush(0);
      if (id) {
        // The block's whole group is painted and picked, on any page. A field ends, and the click this press may
        // grow into picks nothing out of the group.
        const on = to === page ? unit(id) : grouped([id], pages[to].blocks);
        setAt(to);
        setIds(on);
        // The open text stays open for its words: a drag selects in it.
        if (id !== editing) setEditing("");
        const target = blocks.find((b) => b.id === id);
        if (to === page && press && target && boxed(target)) brushDrag(id, el, press, on);
        else daub(on, to);
        spot.current = undefined;
        return;
      }
    }
    if (to !== page) {
      // A press on another page puts it in use, and the selection starts over. That page's Moveable is a new one.
      flushSync(() => {
        setAt(to);
        setIds(id ? grouped([id], pages[to].blocks) : []);
      });
      if (id && press) moveable.current!.dragStart(press);
    } else if (!id) {
      if (shift) return;
      setIds([]);
      setMulti(false);
    } else if (ids.includes(id)) {
      if (more) setIds(ids.filter((i) => !unit(id).includes(i)));
      // A click on a block of a picked group picks the block alone. A press drags the group instead.
      else if (!press && ids.length > 1 && unit(id).length > 1) setIds([id]);
      // On touch a second tap on a text block edits it and on a picture crops it; a mouse double-clicks. A second
      // click on a picked text, shape with words, table or Lineatur writes in it too, as in PowerPoint: a press that
      // drags the block is no click, and Shift took the branch above. A text's caret goes where the click landed;
      // a cell's and a Lineatur's to the end, as a textarea tells no letter for a point.
      else if (touch.current || (!press && sel.length === 1 && free.length === 1 && writable(free[0]) && !tied(free[0]))) {
        clicked.current = point;
        openStone(el) || edit(id, el);
      }
      // Level lines in a row leave Moveable's group area no height, so a press on one lands here.
      else if (press && ids.length > 1) moveable.current!.dragStart(press);
    } else {
      setIds(more ? [...ids, ...unit(id)] : unit(id));
      if (press) moveable.current!.waitToChangeTarget().then(() => moveable.current!.dragStart(press));
    }
  }
  // The blocks that open for writing at once on a key or a second click: those with words of their own.
  const writable = (b: Block) => b.type === "ruling" || b.type === "table" || b.type === "text" || (b.type === "shape" && !isLine(b));
  // `el` is what was pressed: in a table, the cell that gets the caret. `all` picks all the text there.
  // A double click on a stone of the selected Zahlenmauer opens its number field on the stone, as a table cell opens.
  // Gives whether it did.
  function openStone(target: Element): boolean {
    const el = target.closest<SVGGElement>(".stone");
    const block = target.closest<HTMLElement>(".block");
    const only = free.length === 1 ? free[0] : undefined;
    if (!el || !block || only?.type !== "zahlenmauer" || only.id !== block.dataset.id) return false;
    const wall = Number(el.closest<SVGGElement>(".wall")?.dataset.wall);
    const at = Number(el.dataset.stone);
    // The stone's box in the block's own layout, from the svg's units: a turned block's screen box is not its own.
    const svg = el.closest<SVGSVGElement>("svg")!;
    const view = svg.viewBox.baseVal;
    const cell = el.querySelector("rect")!;
    const scale = Math.min(svg.clientWidth / view.width, svg.clientHeight / view.height);
    // The svg has no offsets of its own: its box is that of the block's Zahlenmauer, which has.
    const host = el.closest<HTMLElement>(".zahlenmauer")!;
    const left = host.offsetLeft + (svg.clientWidth - view.width * scale) / 2 + (cell.x.baseVal.value - view.x) * scale;
    const top = host.offsetTop + (cell.y.baseVal.value - view.y) * scale;
    const box = [left, top, cell.width.baseVal.value * scale, cell.height.baseVal.value * scale];
    setStone({ id: only.id, wall, at, text: String(made(only.props).walls[wall].numbers[at]), box });
    return true;
  }
  // A number typed into a stone, stored as the format panel stores it: one undo step for each stone.
  function typeStone(b: Block, wall: number, at: number, text: string) {
    if (b.type !== "zahlenmauer") return;
    // The stored entries as they are, so that the walls beyond `count` keep their numbers.
    const others = (b.props.typed ?? []).filter((t) => t[0] !== wall || t[1] !== at);
    const typed = text === "" ? (others.length ? others : undefined) : [...others, [wall, at, Number(text)]];
    style("zahlenmauer", { typed }, `typed:${wall}:${at}`);
  }
  function edit(id?: string, el?: Element, all = false, cell?: number) {
    if (!id || free.length !== 1 || free[0].id !== id || el?.closest(".bar")) return;
    // A linked Lineatur, text or shape has no text of its own: the list is what it shows.
    if (tied(free[0])) return;
    if (boxed(free[0]) || free[0].type === "ruling" || free[0].type === "table" || free[0].type === "points" || free[0].type === "name") {
      // A score's number is all picked when its field opens, a double click too: a new one replaces it.
      entire.current = all || free[0].type === "points";
      if (free[0].type === "name") {
        setWords(free[0].props.fields ?? FIELDS);
        wordsKept.current = (free[0].props.fields ?? FIELDS).join("\n");
        nameWriting.current = { id, n: page };
      }
      setEditing(id);
    }
    setSlot(cell ?? +(el?.closest<HTMLElement>("[data-cell]")?.dataset.cell ?? 0));
    // A tap in a cell opens that cell alone, as a press of the mouse does: the cells picked before are let go.
    setReach(undefined);
    if (free[0].type === "image") setDraft({ id, cut: free[0].props.cut });
  }
  // The whole picture's box on the page, in mm, from the block's box and its stored cut.
  function whole(b: ImageBlock) {
    const w = b.w / (1 - b.props.cut[0] - b.props.cut[2]);
    const h = w / b.props.ratio;
    return { x: b.x - b.props.cut[0] * w, y: b.y - b.props.cut[1] * h, w, h };
  }
  // A crop handle moves the edges of the frame it stands on: `dx` and `dy` are -1 for the left or top edge, 1 for the
  // right or bottom one. The frame itself (0, 0) moves as a whole over the picture. A tenth of the picture always stays.
  function trim(e: PointerEvent, b: ImageBlock, dx: number, dy: number) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const full = whole(b);
    // The pointer as the picture lies with no turn and no flip: both are about the block's centre.
    const [c, s] = dir(b);
    const [cx, cy] = [b.x + b.w / 2, b.y + b.h / 2];
    const [px, py] = point(e).map((p, i) => p - [cx, cy][i]);
    const at = [cx + (px * c + py * s) * (b.flipX ? -1 : 1), cy + (py * c - px * s) * (b.flipY ? -1 : 1)];
    const share = [(at[0] - full.x) / full.w, (at[1] - full.y) / full.h];
    const cut = [...draft!.cut];
    [dx, dy].forEach((d, axis) => {
      const [lo, hi] = [axis, axis + 2];
      const size = 1 - cut[lo] - cut[hi];
      if (d < 0) cut[lo] = Math.max(0, Math.min(share[axis], 1 - cut[hi] - 0.1));
      if (d > 0) cut[hi] = Math.max(0, Math.min(1 - share[axis], 1 - cut[lo] - 0.1));
      if (!dx && !dy) {
        cut[lo] = Math.max(0, Math.min(share[axis] - size / 2, 1 - size));
        cut[hi] = 1 - size - cut[lo];
      }
    });
    setDraft({ id: b.id, cut });
  }
  // Leaving crop mode cuts the picture in one undo step. The block's box becomes the frame, so what stays of the
  // picture keeps its place and its size on the page.
  function done() {
    setDraft(undefined);
    if (!cropping || draft!.cut.join() === cropping.props.cut.join()) return;
    const full = whole(cropping);
    const [l, t, r, b] = draft!.cut;
    const [w, h] = [full.w * (1 - l - r), full.h * (1 - t - b)];
    // The frame's middle is the new centre the block turns and flips about, so it goes where the page shows it now.
    const [c, s] = dir(cropping);
    const [cx, cy] = [cropping.x + cropping.w / 2, cropping.y + cropping.h / 2];
    const [mx, my] = [(full.x + l * full.w + w / 2 - cx) * (cropping.flipX ? -1 : 1), (full.y + t * full.h + h / 2 - cy) * (cropping.flipY ? -1 : 1)];
    const box = { x: round(cx + mx * c - my * s - w / 2), y: round(cy + mx * s + my * c - h / 2), w: round(w), h: round(h) };
    change((bs) => bs.map((o) => (o.id === cropping.id ? { ...cropping, ...box, props: { ...cropping.props, cut: draft!.cut } } : o)));
  }

  function onTouchStart(e: TouchEvent) {
    clearTimeout(hold.current);
    if (e.touches.length === 2) {
      // A second finger means a pinch, which opens no menu on the lift.
      away.current = true;
      moveable.current!.stopDrag();
      owed.current = undefined;
      const page = sheet.current!.getBoundingClientRect();
      const [x, y] = centre(e);
      pinch.current = { spread: spread(e), zoom, x: (x - page.left) / k, y: (y - page.top) / k };
      return;
    }
    // Tap and hold on a block starts selecting several.
    // A finger held on the text being edited picks a word of it.
    const el = e.target as Element;
    const { clientX: x, clientY: y } = e.touches[0];
    // Moveable's box lies over a selection of several, so the block is looked up under it. Beside a block there the
    // hold selects no more.
    const over = el.matches(".moveable-area");
    const on = over ? document.elementsFromPoint(x, y).find((o) => o.matches(".block")) : el.closest(".block");
    const id = on?.getAttribute("data-id");
    // A drag asks for it too, and that may begin on Moveable's box over the selection.
    came.current = [x, y];
    away.current = false;
    downOn.current = el;
    // The empty page holds no block, but a still hold there opens its menu on the lift.
    if (!(id || over)) {
      hold.current = window.setTimeout(() => (held.current = true), 500);
      return;
    }
    if (id === editing) return;
    const to = pageOf(on ?? el);
    hold.current = window.setTimeout(() => {
      held.current = true;
      setMulti(true);
      setAt(to);
      if (id) setIds((now) => (to !== page ? grouped([id], pages[to].blocks) : [...new Set([...now, ...unit(id)])]));
    }, 500);
  }
  function onTouchMove(e: TouchEvent) {
    // One finger scrolls the desk, and its fling goes on after the lift; two pinch, which keeps the page in use.
    // A finger that drags a block scrolls the desk only at its edge, and that keeps the page of the drag.
    if (e.touches.length === 1 && !moveable.current?.isDragging()) steer(1500);
    // A second finger ends the hold at once, and so does one finger that has moved away.
    const { clientX: x0, clientY: y0 } = e.touches[0];
    if (e.touches.length > 1 || Math.hypot(x0 - came.current[0], y0 - came.current[1]) > SLOP) away.current = true;
    if (e.touches.length > 1 || away.current) clearTimeout(hold.current);
    // A snap the blocks reached before the finger had left where it came down takes them now, if it has.
    if (e.touches.length === 1 && owed.current) drag(owed.current, e.touches[0]);
    if (e.touches.length !== 2) return;
    const next = Math.min(4, Math.max(0.25, (pinch.current.zoom * spread(e)) / pinch.current.spread));
    flushSync(() => zoomTo(next));
    // Scroll the page point the pinch began on back under the fingers.
    const page = sheet.current!.getBoundingClientRect();
    const [x, y] = centre(e);
    desk.current!.scrollBy(page.left + pinch.current.x * fit * next - x, page.top + pinch.current.y * fit * next - y);
  }

  // With nothing free in it the selection is held, be it by a locked block of its group that is not picked.
  const locked = sel.length > 0 && !free.length;
  // A right click on the desk picks as in PowerPoint and opens the menu. In a field the browser's own stays: false.
  function menuAt(el: Element, x: number, y: number) {
    // In the table being edited the menu holds the merge commands, once cells are picked or a merged cell is open.
    const onCell = table && editing === table.id && el.closest(`[data-id="${table.id}"] :is([data-cell], textarea)`);
    if (onCell && (reach !== undefined || spanAt(table.props, slot)[2] * spanAt(table.props, slot)[3] > 1)) {
      setMenu({ x, y, cells: true });
      return true;
    }
    if (el.closest(".ProseMirror, textarea, input, select")) return false;
    // Moveable's area and a line's handles lie over a selection, so the block is looked up under them. Beside a block
    // there the selection stays.
    const over = moveable.current!.isMoveableElement(el) || !!el.closest(".end, .adjust, .bar, .crop");
    const id = (over ? document.elementsFromPoint(x, y).find((o) => o.matches(".block")) : el.closest(".block"))?.getAttribute("data-id");
    const to = pageOf(el);
    // A block of the selection keeps it whole. Another one is picked with its group, and the empty page picks nothing.
    if (to !== page || (id ? !ids.includes(id) : !over)) {
      done();
      setAt(to);
      setIds(id ? grouped([id], pages[to].blocks) : []);
    }
    // The cell under the click, for Text bearbeiten: the menu runs after the click has closed it, so it is kept here.
    const cell = el.closest<HTMLElement>("[data-cell]")?.dataset.cell;
    setMenu({ x, y, cell: cell === undefined ? undefined : +cell });
    return true;
  }
  function thumbMenu(n: number, x: number, y: number) {
    // The menu hands the focus back when it closes: to a field, that would keep the sheet's keys.
    (document.activeElement as HTMLElement | null)?.blur();
    // A page in the choice keeps it; any other is chosen alone.
    if (!chosenNow.includes(n)) visit(n);
    setMenu({ x, y, thumb: n });
  }
  const none = !sel.length;
  const ctrl = APPLE ? "⌘" : "Strg+";
  const shift = APPLE ? "⇧" : "Umschalt+";
  const thumbed = menu?.thumb;
  const ruled = menu?.rule;
  const menuCell = menu?.cell;
  type Command = Exclude<Item, "sep">;
  // One block with words of its own, or a score or a name, opens for writing from its menu, as F2 does. Not a linked one.
  // It opens a moment later: the menu's dialog gives the focus back as it shuts, and in WebKit after the text took it.
  const [only] = sel;
  const writeIn: Item[] =
    sel.length === 1 && (writable(only) || only.type === "points" || only.type === "name") && !tied(only) && editing !== only.id
      ? ["sep", { label: "Text bearbeiten", keys: "F2", disabled: !free.length, run: () => {
            asked.current = { id: only.id, cell: menuCell };
            setTimeout(() => {
              // A key typed in the meantime has opened it already. The request stays until the sheet's keys know the
              // block is open: a key in between opens it again in its cell, not the first cell after its text.
              if (asked.current?.id !== only.id) return;
              flushSync(() => edit(only.id, undefined, true, menuCell));
            });
          } }, "sep"]
      : [];
  const clips: Command[] = [
    { label: "Ausschneiden", icon: Scissors, keys: `${ctrl}X`, disabled: !free.length, run: cut },
    { label: "Kopieren", icon: Copy, keys: `${ctrl}C`, disabled: none, run: copy },
    { label: "Einfügen", icon: ClipboardPaste, keys: `${ctrl}V`, run: pasteAny },
  ];
  const copies: Command[] = [
    { label: "Duplizieren", icon: CopyPlus, keys: `${ctrl}D`, disabled: none, run: () => put(sel) },
    { label: "Löschen", icon: Trash2, keys: "Entf", disabled: !free.length, run: remove },
  ];
  const lockIt: Command = { label: locked ? "Entsperren" : "Sperren", icon: locked ? LockOpen : Lock, disabled: none, run: () => place((locked ? wide : sel).map((b) => [b.id, { locked: !locked }])) };
  const groups: Command[] = [
    { label: "Gruppieren", icon: Group, keys: `${ctrl}G`, disabled: !joinable, run: join },
    { label: "Gruppierung aufheben", icon: Ungroup, keys: `${ctrl}${shift}G`, disabled: !splittable, run: split },
  ];
  // The block menu's row of icon buttons: turn, align and the brush, as the panel and the bar have them.
  // A selection held by a locked block, though that one is not picked, turns no more than in the panel.
  const turnless = free.length !== sel.length || sel.some((b) => b.type === "table" || (isLine(b) && thing(b) === b.id));
  const mini: Command[] = [
    { label: "Linksdrehung 90°", icon: RotateCcw, disabled: turnless, run: () => spin(-90) },
    { label: "Rechtsdrehung 90°", icon: RotateCw, disabled: turnless, run: () => spin(90) },
    ...ALIGNS.map(([axis, at, label, icon]): Command => ({ label, icon, disabled: !things.length, run: () => align(axis, at) })),
    { label: "Format übertragen", icon: Paintbrush, disabled: !brush && !source, run: () => (dip(part?.marks), setBrush(1)) },
  ];
  // The block menu, which has the row. Not the Mehr list, the thumbs, a guide line or a table's cells.
  const blockMenu = !menu?.more && menu?.thumb === undefined && !menu?.rule && !menu?.cells && sel.length > 0;
  // The box around the picked blocks, which the row keeps clear of.
  const pickedBox = () => {
    // On the whole desk: a right click on a block of another page picks it in the same render that brings its page.
    const rs = sel.map((b) => desk.current?.querySelector(`[data-id="${b.id}"]`)?.getBoundingClientRect()).filter((r): r is DOMRect => !!r);
    if (!rs.length) return undefined;
    return { left: Math.min(...rs.map((r) => r.left)), top: Math.min(...rs.map((r) => r.top)), right: Math.max(...rs.map((r) => r.right)), bottom: Math.max(...rs.map((r) => r.bottom)) };
  };
  const items: Item[] =
    ruled
      ? // Only the one line goes, as one undo step: no merge key, so no other change joins it.
        [{ label: "Hilfslinie entfernen", icon: Eraser, run: () => rules(ruled.n, (g) => ({ ...g, [ruled.axis]: g[ruled.axis].filter((_, j) => j !== ruled.i) })) }]
      : thumbed !== undefined
      ? [
          { label: "Neue Seite", icon: FilePlus, run: () => addPage(thumbed) },
          { label: "Seite duplizieren", icon: CopyPlus, run: () => copyPages(choiceOf(thumbed)) },
          { label: "Seite löschen", icon: FileX, disabled: choiceOf(thumbed).length >= pages.length, run: () => removePages(choiceOf(thumbed)) },
          { label: "Ausschneiden", icon: Scissors, keys: `${ctrl}X`, disabled: choiceOf(thumbed).length >= pages.length, run: () => cutPages(choiceOf(thumbed)) },
          { label: "Kopieren", icon: Copy, keys: `${ctrl}C`, run: () => storePages(choiceOf(thumbed)) },
          { label: "Einfügen", icon: ClipboardPaste, keys: `${ctrl}V`, disabled: !clippedPages().pages.length, run: () => pastePages(thumbed) },
        ]
      : [
          ...(table && editing === table.id
            ? ([
                { label: "Zellen verbinden", disabled: reach === undefined, run: merge },
                { label: "Zellen teilen", disabled: !(spanAt(table.props, slot)[2] * spanAt(table.props, slot)[3] > 1), run: unmerge },
                "sep",
              ] as Item[])
            : []),
          ...clips,
          ...writeIn,
          ...copies,
          "sep",
          lockIt,
          "sep",
          ...groups,
          "sep",
          { label: "In den Vordergrund", disabled: none || !stacked(true), run: () => raise(true) },
          { label: "Eine Ebene nach vorn", disabled: none || !stacked(true, true), run: () => raise(true, true) },
          { label: "Eine Ebene nach hinten", disabled: none || !stacked(false, true), run: () => raise(false, true) },
          { label: "In den Hintergrund", disabled: none || !stacked(false), run: () => raise(false) },
        ];
  const mode = side ? "Vorlagen" : tab === "Ansicht" ? "Ansicht" : "Start";
  const brand = (
    <Link to="/" className="brand" aria-label="Meine Blätter" title="Meine Blätter">
      <Logo />
      <ChevronLeft size={16} aria-hidden />
    </Link>
  );
  // The buttons walk fixed steps of a quarter around the page's width, so the way back passes the same sizes, also
  // from either end and after a pinch.
  function zoomBy(by: number) {
    const n = Math.log(zoom) / Math.log(1.25);
    const to = by > 0 ? Math.floor(n + 1e-6) + 1 : Math.ceil(n - 1e-6) - 1;
    zoomTo(1.25 ** to);
  }
  // The whole page in use, width and height, until a zoom by hand: it follows the desk when the window changes.
  function fitPage() {
    fitted.current = true;
    fitOn.current = page;
    // 120 is the desk's padding above and below. The whole box, not clientHeight: that leaves out the bar along the
    // bottom, which goes once the page fits, and the desk has no border to take off.
    setZoom(Math.min(4, Math.max(0.25, Math.min(room / W, (desk.current!.offsetHeight - 120) / H) / fit)));
    setFitTick((n) => n + 1);
  }
  // The scroll follows the zoom once it is drawn: the rects read before that are the old size's. The page is the one
  // in use when the fit was made.
  useLayoutEffect(() => {
    if (!fitted.current) return;
    const el = desk.current!;
    const [sheetRect, box] = [el.querySelector(`.sheet[data-page="${fitOn.current}"]`)!.getBoundingClientRect(), el.getBoundingClientRect()];
    // The page lies in the middle, across, also beside a wider one, and its top under the desk's padding.
    el.scrollBy(sheetRect.left + sheetRect.width / 2 - box.left - el.clientWidth / 2, sheetRect.top - box.top - 32);
  }, [fitTick]);
  const zoomer = (
    <>
      <Tool icon={ZoomOut} label="Kleiner" onClick={() => zoomBy(-1)} />
      {/* The page's size on the screen against its size on paper. */}
      {/* The list opens over the button: upward from the dock, downward from the bar. */}
      <button
        className="zoom"
        title="Zoom"
        aria-haspopup="dialog"
        onClick={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          const up = !!e.currentTarget.closest(".dock");
          setLens({ x: box.left, y: up ? box.top : box.bottom, up });
        }}
      >
        {Math.round((k * 2540) / 96)} %
      </button>
      <Tool icon={Fullscreen} label="Ganze Seite" onClick={fitPage} />
      <Tool icon={ZoomIn} label="Größer" onClick={() => zoomBy(1)} />
    </>
  );
  // The bar's commands that may fold, in the bar's order, and those of them that "Mehr" holds now. A menu has no
  // double click, so the brush picked there stays on, as after one on its button, until its ticked item is picked
  // again or Escape puts it down.
  const folding: Command[] = [
    ...clips,
    { label: "Format übertragen", icon: Paintbrush, disabled: !brush && !source, on: brush > 0, run: () => (brush ? setBrush(0) : (dip(part?.marks), setBrush(2))) },
    ...copies,
    lockIt,
    ...groups,
    { label: "Lösungen zeigen", icon: Eye, on: solved, run: () => setSolved(!solved) },
    ...(leaf
      ? []
      : [
          { label: "Kleiner", icon: ZoomOut, run: () => zoomBy(-1) },
          // The bar's zoom button, which opens the list below "Mehr" as the button does in the bar.
          {
            label: "Zoom",
            run: () => {
              // The list gives the focus back to what has it when it opens: that is "Mehr", not the item just picked.
              const more = bar.current!.querySelector<HTMLElement>(".more")!;
              more.focus();
              const box = more.getBoundingClientRect();
              setLens({ x: box.left, y: box.bottom, up: false });
            },
          },
          { label: "Ganze Seite", icon: Fullscreen, run: fitPage },
          { label: "Größer", icon: ZoomIn, run: () => zoomBy(1) },
        ]),
    { label: "Rundgang", icon: CircleHelp, run: () => setTour(true) },
    { label: "Feedback", icon: MessageSquare, run: () => feedback.current!() },
    { label: "Varianten drucken", icon: Layers, run: () => openVariants(bar.current!.querySelector<HTMLElement>(".more")!) },
  ];
  const more = folding.slice(fits ?? folding.length);
  const inBar = (label: string) => !more.some((item) => item.label === label);
  // The maths blocks, picked from the "Mathe-Blöcke" menu.
  const mathBlocks: Item[] = [
    { label: "Zahlenmauer", icon: BrickWall, run: () => addInsert(INSERTS.zahlenmauer(newSeed())) },
    { label: "Zahlenhaus", icon: House, run: () => addInsert(INSERTS.zahlenhaus(newSeed())) },
    { label: "Zahlenkette", icon: Link2, run: () => addInsert(INSERTS.zahlenkette(newSeed())) },
    { label: "Rechendreieck", icon: TriangleDashed, run: () => addInsert(INSERTS.rechendreieck(newSeed())) },
    { label: "Zahlenstrahl", icon: MoveRight, run: () => addInsert(INSERTS.zahlenstrahl(newSeed())) },
    { label: "Hunderterfeld", icon: Grid3x3, run: () => addInsert(INSERTS.hunderterfeld(newSeed())) },
    { label: "Uhr", icon: Clock3, run: () => addInsert(INSERTS.uhr(newSeed())) },
    { label: "Selbstkontrolle", icon: ListChecks, run: () => addInsert(INSERTS.selbstkontrolle(newSeed())) },
  ];
  // What can go on the page. A divider's name is its group's heading in Blattform's left panel.
  const tools = (
    <>
      <Tool
        icon={SquareDashedMousePointer}
        label="Mehrere"
        data-tour="multi"
        className={multi ? "on" : ""}
        aria-pressed={multi}
        onClick={() => setMulti(!multi)}
      />
      <i className="sep" data-name="Einfügen" />
      <Tool icon={Type} label="Text" data-tour="text" onClick={() => addInsert(INSERTS.text())} />
      <Tool icon={Heading} label="Überschrift" onClick={() => addInsert(INSERTS.heading())} />
      <Tool icon={ImagePlus} label="Bild" onClick={() => picker.current!.click()} />
      <input
        ref={picker}
        type="file"
        accept={TYPES.join()}
        hidden
        onChange={(e) => {
          upload(e.target.files?.[0]);
          // The same picture can be picked again.
          e.target.value = "";
        }}
      />
      <Tool icon={Smile} label="Symbol" onClick={() => addInsert(INSERTS.symbol())} />
      <Tool icon={Table} label="Tabelle" onClick={() => addInsert(INSERTS.table())} />
      <i className="sep" data-name="Schule" />
      <Tool icon={Rows3} label="Lineatur" onClick={() => addInsert(INSERTS.ruling())} />
      <Tool icon={UserPen} label="Namenszeile" onClick={() => addInsert(INSERTS.name())} />
      <Tool icon={SquareSlash} label="Punkte" onClick={() => addInsert(INSERTS.points())} />
      <Tool icon={Grid3x3} label="Suchsel" onClick={() => addInsert(INSERTS.suchsel(newSeed()))} />
      {/* What makes exercises, a group to a subject. */}
      <i className="sep" data-name="Mathe" />
      <Tool icon={Calculator} label="Rechnen" data-tour="maths" onClick={addMaths} />
      <Tool
        icon={Sigma}
        label="Mathe-Blöcke"
        aria-haspopup="menu"
        aria-expanded={!!mathMenu}
        onClick={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          setMathMenu({ x: box.left, y: box.top - 4 });
        }}
      />
      <Tool icon={Ruler} label="Strecke" onClick={() => addInsert(INSERTS.strecke())} />
      <i className="sep" data-name="Formen" />
      <span className="shapes">
        {SHAPES.map(([kind, label, icon]) => (
          <Tool
            key={kind}
            icon={icon}
            label={label}
            onClick={() => addInsert(INSERTS.shape(kind))}
          />
        ))}
      </span>
    </>
  );
  return (
    // The Lernwörter reach every Lineatur that draws them, on the pages and on their thumbnails.
    <Words.Provider value={learnt}>
    <Whole.Provider value={hist.doc}>
    <main
      className={`editor${leaf ? " leaf" : ""}${brush ? " brush" : ""}${pan ? " pan" : ""}${panning ? " panning" : ""}${drawnRight ? " drawn" : ""}`}
      data-ready="1"
      // The keys end a run of changes as a press of the mouse does: when they take the focus elsewhere, and when
      // they press a button, also one that finds nothing to change. The next change is a step of its own.
      onFocusCapture={() => (mergeKey.current = "")}
      onClickCapture={() => (mergeKey.current = "")}
      // So does each value picked in a list, also when the arrows walk the list with no press between.
      onChangeCapture={(e) => (e.target as Element).matches("select") && (mergeKey.current = "")}
      onPointerDown={(e) => {
        mergeKey.current = "";
        inPanel.current = !!(e.target as Element).closest(".panel");
        // The browser tells the field only later where the caret went, and the field hears nothing once the panel
        // has the focus: a look picked there would go to the word the caret has left. So the field reads it now.
        if (inPanel.current && field.current) document.dispatchEvent(new Event("selectionchange"));
        // What is written in lost the focus to the panel and has no blur left to end it: a press beside the panel
        // and the blocks, as on the title, ends it.
        if (!inPanel.current && document.activeElement?.closest(".panel") && !(e.target as Element).closest(".block")) setEditing("");
      }}
      // A button pressed with the mouse does not take the focus, as PowerPoint's ribbon does not: Enter and Tab stay
      // the sheet's. A dialog's buttons are its own. What had the focus loses it to the main mouse button as before,
      // but a button of the format panel leaves it where it is: a text, a Lineatur or a cell being written in keeps
      // the caret, and a number of the panel its draft. So does the panel's bare ground, where a press on a disabled
      // button lands: a press there may also be the one that shuts a list or a colour picker with no pick, and its
      // control must keep the focus for the next key to give it back.
      onMouseDown={(e) => {
        const target = e.target as Element;
        const button = target.closest("button");
        const panel = target.closest(".panel");
        // A text being written in stays open while a drawer's button in the bar opens the drawer with its format.
        // A number of the panel does lose the focus to it, and so lands before the drawer shuts. The text stays open
        // under "Mehr" as well, until a command is picked there.
        const pin = target.closest(drawers ? ".pin, .more" : ".more") && document.activeElement?.closest(".block");
        if (panel && !button && !target.closest("input, select, textarea, label") && document.activeElement?.closest(".block, .panel select, .panel input[type=color]")) return e.preventDefault();
        if (e.defaultPrevented || !button || button.closest("dialog")) return;
        e.preventDefault();
        if (!e.button && !pin && !(panel && document.activeElement?.closest(".block, .panel"))) (document.activeElement as HTMLElement | null)?.blur();
      }}
    >
      <header>
        {/* Blank.tsx draws this bar's boxes, and the panel's below, for a phone that loads: a change here goes there too. */}
        <div className="top" ref={bar} onPointerOver={holdName}>
          {leaf ? (
            <span className="modes" role="tablist">
              {["Start", "Ansicht", "Vorlagen"].map((m) => (
                <button
                  key={m}
                  role="tab"
                  data-tour={m}
                  aria-selected={mode === m}
                  onClick={() => {
                    setSide(m === "Vorlagen");
                    setTab(m === "Ansicht" ? "Ansicht" : "Format");
                    if (m === "Ansicht") setPane(true);
                  }}
                >
                  {m}
                </button>
              ))}
            </span>
          ) : (
            <>
              {brand}
              <Tool icon={PanelLeft} label="Seiten und Vorlagen" className={`pin${left ? " on" : ""}`} aria-pressed={left} onClick={() => showLeft(!left)} />
            </>
          )}
          <input
            type="text"
            aria-label="Titel"
            placeholder="Unbenanntes Blatt"
            maxLength={80}
            value={title}
            // A title the bar cuts shows whole under the pointer, and while it is edited: see `refit`.
            title={title}
            onChange={(e) => setTitle(e.target.value)}
            onFocus={refit}
            // A press that takes the focus from the stand-in title picks it whole, as PowerPoint does, so that typing replaces it.
            // The press then does not place the caret, and a second press, with the focus already here, does.
            onMouseDown={(e) => {
              if (document.activeElement === e.currentTarget || e.currentTarget.value.trim() !== "Unbenanntes Blatt") return;
              e.preventDefault();
              e.currentTarget.focus();
              e.currentTarget.select();
            }}
            // A press that took the focus has its click still to come: the bar waits until the mouse button is up and
            // the click is through, or the button pressed would move from under the pointer. A key ends it at once.
            onBlur={() => (document.querySelector(":active") ? addEventListener("mouseup", () => setTimeout(refit), { once: true, capture: true }) : refit())}
            // Enter ends the edit, as in PowerPoint, and gives the keys back; Escape does so for any field.
            onKeyDown={(e) => e.key === "Enter" && back(e.currentTarget)}
          />
          <span className="hint" role="status">
            {!dirty ? "Gespeichert" : !saver || saver.failed || saver.clash ? "Nicht gespeichert" : "Speichert …"}
          </span>
          <Tool icon={Undo2} label="Rückgängig" data-tour="undo" disabled={!hist.past.length} onClick={undo} />
          <Tool icon={Redo2} label="Wiederholen" disabled={!hist.future.length} onClick={redo} />
          <i className="sep" />
          {inBar("Ausschneiden") && <Tool icon={Scissors} label="Ausschneiden" disabled={!free.length} onClick={cut} />}
          {inBar("Kopieren") && <Tool icon={Copy} label="Kopieren" disabled={!sel.length} onClick={() => copy()} />}
          {inBar("Einfügen") && <Tool icon={ClipboardPaste} label="Einfügen" onClick={pasteAny} />}
          {inBar("Format übertragen") && (
            <Tool
              icon={Paintbrush}
              label="Format übertragen"
              disabled={!brush && !source}
              className={brush ? "on" : ""}
              aria-pressed={brush > 0}
              onPointerDown={() => (wet.current = part?.marks)}
              // One click picks the look up for one block, or puts the brush down. The second click of a double click
              // keeps the brush on with the look the first one picked up.
              onClick={(e) => {
                // A press by the keys has no pointer before it, and must not find an earlier one's words.
                const marks = wet.current;
                wet.current = undefined;
                if (brush && e.detail < 2) return setBrush(0);
                if (!brush) dip(marks);
                setBrush(e.detail < 2 ? 1 : 2);
              }}
            />
          )}
          {inBar("Duplizieren") && <Tool icon={CopyPlus} label="Duplizieren" disabled={!sel.length} onClick={() => put(sel)} />}
          {inBar("Löschen") && <Tool icon={Trash2} label="Löschen" disabled={!free.length} onClick={remove} />}
          {inBar(lockIt.label) && <Tool icon={lockIt.icon!} label={lockIt.label} disabled={!sel.length} className={locked ? "on" : ""} onClick={lockIt.run} />}
          {inBar("Gruppieren") && <Tool icon={Group} label="Gruppieren" disabled={!joinable} onClick={join} />}
          {inBar("Gruppierung aufheben") && <Tool icon={Ungroup} label="Gruppierung aufheben" disabled={!splittable} onClick={split} />}
          {/* With none of them left in the bar, the divider before them is enough. */}
          {fits !== 0 && <i className="sep" />}
          {inBar("Lösungen zeigen") && <Tool icon={Eye} label="Lösungen zeigen" className={solved ? "on" : ""} aria-pressed={solved} onClick={() => setSolved(!solved)} />}
          {!leaf && inBar("Kleiner") && zoomer}
          <Tool icon={PanelRight} label="Format und Ansicht" className={`pin${right ? " on" : ""}`} aria-pressed={right} onClick={() => showRight(!right)} />
          {inBar("Rundgang") && <Tool icon={CircleHelp} label="Rundgang" data-tour="help" onClick={() => setTour(true)} />}
          <Feedback className="ib" aria-label="Feedback" opener={inBar("Feedback") ? undefined : feedback}>
            <MessageSquare size={16} aria-hidden />
          </Feedback>
          {inBar("Varianten drucken") && <Tool icon={Layers} label="Varianten drucken" onClick={(e) => openVariants(e.currentTarget)} />}
          {more.length > 0 && (
            <Tool
              icon={Ellipsis}
              label="Mehr"
              className="more"
              aria-haspopup="menu"
              aria-expanded={!!menu?.more}
              // The tour's last step is about its own button, which lies in here when the bar has folded it.
              data-tour={inBar("Rundgang") ? undefined : "help"}
              onClick={(e) => {
                const box = e.currentTarget.getBoundingClientRect();
                setMenu({ x: box.left, y: box.bottom + 4, more: true });
              }}
            />
          )}
          <span className="pdf" data-tour="pdf">
            <button onClick={() => pdf(true)}>
              <FileCheck size={14} aria-hidden />
              Lösungen
            </button>
            <button className="primary" onClick={() => pdf(false)}>
              <FileDown size={14} aria-hidden />
              PDF
            </button>
          </span>
          {variants && (
            <Variants
              id={file.id}
              doc={hist.doc}
              count={count}
              setCount={setCount}
              letters={letters}
              setLetters={setLetters}
              opener={variantsDoor}
              onClose={() => { setVariants(false); setFromPress(undefined); }}
              clash={!!saver?.clash}
              newer={(key) => newerSheet({ count, letters, print: key, newer: true })}
              print={fromPress?.print}
              fresh={fromPress?.newer}
            />
          )}
        </div>
        {saver?.refused && (
          <div className="clash" role="alert">
            Nicht gespeichert: Das Blatt passt nicht zum Format.
            <ul>
              {saver.refused.map((problem, i) => (
                <li key={i}>{problem}</li>
              ))}
            </ul>
          </div>
        )}
        {saver?.clash && (
          <div className="clash" role="alert">
            {CLASH_BAR}
            {pdfWaits && " Danach kommt dein PDF."}
            <button disabled={choice === "busy"} onClick={reload}>Andere Version laden</button>
            {/* Based on the version the server has now, this document takes its place; a change that lands in between clashes again. */}
            <button disabled={choice === "busy"} onClick={over}>Mit dieser überschreiben</button>
            {choice && <span>{choice === "busy" ? "Lädt …" : "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."}</span>}
          </div>
        )}
        {/* The editor works on under it: what shows at the press is what is kept. */}
        {saver?.gone && (
          <div className="clash" role="alert">
            Dieses Blatt wurde auf einem anderen Gerät gelöscht. Was du hier siehst, ist noch da.
            <button disabled={saver.choice === "busy"} onClick={asNew}>Als neues Blatt behalten</button>
            <button disabled={saver.choice === "busy"} onClick={discard}>Verwerfen</button>
            {saver.choice && (
              <span>
                {saver.choice === "busy" ? "Lädt …" : saver.choiceProblems ? `Das hat nicht geklappt: das Blatt passt nicht zum Format. ${saver.choiceProblems.join("; ")}` : "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."}
              </span>
            )}
          </div>
        )}
      </header>

      {leaf && !side && (
        <aside className="left">
          {brand}
          <div className="insert" role="toolbar" aria-label="Einfügen" onPointerOver={(e) => holdName(e, e.currentTarget.parentElement!)}>
            {tools}
            <i className="sep" data-name="Seite" />
            <Tool icon={FilePlus} label="Neue Seite" onClick={() => addPage()} />
            <Tool icon={CopyPlus} label="Seite duplizieren" onClick={() => copyPages()} />
            <Tool icon={FileX} label="Seite löschen" disabled={chosenNow.length >= pages.length} onClick={() => removePages()} />
          </div>
        </aside>
      )}
      {left && (
        <aside className="left">
          {leaf && brand}
          <div className="head">
            Seiten
            <span>
              <Tool icon={CopyPlus} label="Seite duplizieren" title="Seite duplizieren" onClick={() => copyPages()} />
              <Tool icon={FileX} label="Seite löschen" title="Seite löschen" disabled={chosenNow.length >= pages.length} onClick={() => removePages()} />
            </span>
          </div>
          {/* As many thumbnails in a row as fit, 12 px apart, in the 206 px that two take at first. */}
          <div className="pages" ref={strip} style={{ "--thumb": `${thumb}px` } as CSSProperties}>
            {pages.map((_, n) => (
              <button
                key={n}
                data-thumb={n}
                title="Ziehen verschiebt die Seite"
                className={[chosenNow.includes(n) && "on", n === haul?.from && "drag"].filter(Boolean).join(" ")}
                aria-pressed={chosenNow.includes(n)}
                // The click after a drag is the drag's end, not a visit. The next one, also by Enter, visits again.
                onClick={(e) => {
                  if (!dragged.current) {
                    if (e.shiftKey) {
                      // From the page in use to this one; the page in use stays.
                      setChosen(Array.from({ length: Math.abs(n - page) + 1 }, (_, j) => Math.min(n, page) + j));
                    } else if (e.ctrlKey || e.metaKey) {
                      // Adds this page to the choice, or drops it; the last one stays.
                      const next = chosenNow.includes(n) ? (chosenNow.length > 1 ? chosenNow.filter((i) => i !== n) : chosenNow) : [...chosenNow, n].sort((a, b) => a - b);
                      if (next.includes(page)) setChosen(next);
                      else {
                        visit(next[0]);
                        setChosen(next);
                      }
                    } else {
                      visit(n);
                    }
                    // The keys of a thumbnail need its focus, and a click leaves it with the page.
                    e.currentTarget.focus({ preventScroll: true });
                  }
                  dragged.current = false;
                }}
                onKeyDown={(e) => pageKey(e, n)}
                // The mouse and the pen drag once they have moved 4 px. A finger holds first: see the listeners on the thumbnails.
                onPointerDown={(e) => {
                  dragged.current = false;
                  touch.current = e.pointerType === "touch";
                  if (e.pointerType === "touch" || e.button) return;
                  tug.current = { from: n, x: e.clientX, y: e.clientY };
                  e.currentTarget.setPointerCapture(e.pointerId);
                }}
                onPointerMove={(e) => {
                  const t = tug.current;
                  if (e.pointerType === "touch" || !t) return;
                  if (t.slot !== undefined || Math.hypot(e.clientX - t.x, e.clientY - t.y) >= 4) {
                    aim(e.clientX, e.clientY);
                    scrollEdge(e.clientX, e.clientY);
                  }
                }}
                onPointerUp={(e) => e.pointerType !== "touch" && release()}
                onPointerCancel={(e) => e.pointerType !== "touch" && quit()}
                // A held finger would open the browser's menu and end the touch. The mouse gets the page's menu.
                onContextMenu={(e) => {
                  if (tug.current || !touch.current) e.preventDefault();
                  if (!tug.current && !touch.current) thumbMenu(n, e.clientX, e.clientY);
                }}
              >
                {/* The thumbnails draw late: a new page has its button before its picture. */}
                {n < small.pages.length && <Thumb doc={small} k={thumb / sizeOf(small, n)[0]} page={n} />}
                Seite {n + 1}
                {/* The line where the dragged page will land: before this thumbnail, or after it. */}
                {haul && haul.slot - +haul.after === n && (
                  <span className={haul.after ? "mark end" : "mark"} data-to={landing(haul.from, haul.slot)} />
                )}
              </button>
            ))}
            <button onClick={() => addPage()}>
              <i style={{ aspectRatio: small.landscape ? "297 / 210" : "210 / 297" }}>
                <Plus size={16} aria-hidden />
              </i>
              Neue Seite
            </button>
          </div>
          <label className="tick numbers">
            <input type="checkbox" checked={folio.on} onChange={(e) => numbering({}, e.target.checked)} /> Seitenzahlen
          </label>
          <h2>Vorlagen</h2>
          {["Allgemein", "Mathe", "Deutsch", "Organisation"].map((g) => {
            const group = builtIn.filter((t) => t.group === g);
            return group.length ? (
              <div role="group" aria-label={g} className="tpl-group" key={g}>
                <h3>{g}</h3>
                {group.map((t) => (
                  <div key={t.id} className="tpl">
                    <button onClick={() => apply(t)}>
                      <span className="tpl-thumb" aria-hidden>
                        <Thumb doc={t.shown} k={48 / 210} page={0} />
                      </span>
                      <span className="tpl-name">{t.name}</span>
                    </button>
                    <small>eingebaut</small>
                  </div>
                ))}
              </div>
            ) : null;
          })}
          <h2>Meine Vorlagen</h2>
          {kept.map((t) => (
            <div key={t.id} className="tpl">
              <button onClick={() => apply(t)}>
                <LayoutTemplate size={14} aria-hidden />
                <span className="tpl-name">{t.name}</span>
              </button>
              <Tool icon={X} label={`Vorlage ${t.name} löschen`} title="Löschen" onClick={() => forget(t)} />
            </div>
          ))}
          {!kept.length && <p className="hint">Noch keine</p>}
          <div className="foot">
            <input type="text" aria-label="Name der Vorlage" placeholder="Name der Vorlage" maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
            <button disabled={!name.trim()} onClick={store}>
              <Plus size={14} aria-hidden />
              Dieses Blatt als Vorlage
            </button>
          </div>
        </aside>
      )}

      {/* The release may land on the hand, beside the desk: the click is the stage's, not the desk's. */}
      <div
        className="stage"
        ref={stage}
        onMouseUp={(e) => e.button === 1 && e.preventDefault()}
        onAuxClick={(e) => e.button === 1 && e.preventDefault()}
        // Capture: Moveable's frame over a picked block would hear the press first otherwise. The hand lies beside the desk, so the stage takes its press too.
        onPointerDownCapture={(e) => {
          if (e.button !== 1 || e.pointerType !== "mouse") return;
          e.stopPropagation();
          middlePan(e.clientX, e.clientY);
        }}
        // The press is not cancelled as a pointer: Chrome then sends no mouseup, and a middle paste would follow it.
        onMouseDownCapture={(e) => {
          if (e.button !== 1) return;
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        <div
          className="desk"
          ref={desk}
          // How wide the widest page lies on the desk: the room an open Format drawer adds starts past it.
          style={{ "--reach": `${widest * k}px` } as CSSProperties}
          onScroll={follow}
          onWheel={(e) => !(e.ctrlKey || e.metaKey) && steer()}
          onPointerDown={(e) => {
            if (e.target === e.currentTarget) {
              scrollHeld.current = true;
              const let_go = () => {
                scrollHeld.current = false;
                window.removeEventListener("pointerup", let_go);
                window.removeEventListener("pointercancel", let_go);
              };
              window.addEventListener("pointerup", let_go);
              window.addEventListener("pointercancel", let_go);
            }
            touch.current = e.pointerType === "touch";
            setFinger(touch.current);
            cover.current =moveable.current!.isMoveableElement(e.target as Element);
            // The hold before is over with the next press, not with its own lift: Moveable hears of that lift later.
            held.current = false;
            // A press of the mouse on a cell of the table being edited picks cells. Moveable takes the focus from the
            // field before the mouse's own event: the field stays open through that.
            cellDrag.current = !touch.current && !!table && editing === table.id && !!(e.target as Element).closest(`[data-id="${table.id}"] [data-cell]`);
            // A press with the brush on a picked text is the brush's: Moveable, which hears of it before the mouse's
            // own event, would drag the block (#756). The click after it picks nothing more.
            // Under Moveable's frame the block is the one the point finds, as onClickCapture finds it.
            // A handle of the frame resizes or turns: only its area lies over the text.
            const hit = cover.current && (e.target as Element).matches(".moveable-area") ? document.elementsFromPoint(e.clientX, e.clientY).find((el) => el.closest(".block")) : undefined;
            brushed.current = hit ?? (e.target as Element);
            const id = brushed.current.closest<HTMLElement>(".block")?.dataset.id;
            const text = blocks.find((b) => b.id === id);
            brushing.current = !touch.current && e.button === 0 && !!brush && !!text && !!boxed(text) && ids.includes(text.id);
            if (brushing.current) {
              const off = () => setTimeout(() => (brushing.current = false));
              addEventListener("pointerup", off, { once: true });
              addEventListener("pointercancel", off, { once: true });
            }
          }}
          onMouseDown={(e) => {
            // Moveable keeps the press from moving the focus, so an input, or a button reached by the keys, would keep
            // Enter and Tab.
            if (!document.activeElement?.closest(".block")) (document.activeElement as HTMLElement | null)?.blur();
            // In the table being edited a press on a cell picks cells: Shift picks up to that cell, a drag picks across.
            const hit = table && editing === table.id && (e.target as Element).closest(`[data-id="${table.id}"]`) ? (e.target as Element).closest<HTMLElement>("[data-cell]") : null;
            if (hit && e.button === 0) {
              const at = anchorOf(table!.props, +hit.dataset.cell!);
              // Shift on another cell keeps the letters of the cells unpicked; in the open field it picks text, and a
              // plain press there sets the caret.
              if (e.shiftKey && at !== slot) e.preventDefault();
              else if (!e.shiftKey) setSlot(at);
              setReach(e.shiftKey && at !== slot ? at : undefined);
              spot.current = undefined;
              return;
            }
            // With the brush a press in the open text picks its words, and a drag paints them.
            // The brush's press on a picked text (see onPointerDown) paints, and its drag picks words.
            if (brushing.current) return void pick(brushed.current!, e.shiftKey, e.nativeEvent);
            // The right button drags nothing: its menu picks the block.
            if (touch.current || e.button === 2 || moveable.current!.isMoveableElement(e.target as Element)) return;
            // A press on a picked block may drag it. Only a click that stays on its spot picks a block out of its group.
            spot.current = !e.shiftKey && !e.ctrlKey && !e.metaKey && ids.includes((e.target as Element).closest<HTMLElement>(".block")?.dataset.id ?? "") ? [e.clientX, e.clientY] : undefined;
            pick(e.target as Element, e.shiftKey, e.nativeEvent);
          }}
          // Moveable keeps a click on a selection it cannot drag to itself, so the block under its area is looked up on the way down.
          onClickCapture={(e) => {
            if (free.length === sel.length || !moveable.current!.isMoveableElement(e.target as Element)) return;
            const under = document.elementsFromPoint(e.clientX, e.clientY).find((el) => el.closest(".block"));
            if (under) pick(under, e.shiftKey);
          }}
          onClick={(e) => {
            if (moveable.current!.isMoveableElement(e.target as Element)) return;
            // Moveable took the focus from the field with a press on a cell: it goes back to the cell that is open now.
            if (table && editing === table.id && (e.target as Element).closest(`[data-id="${table.id}"]`)) return void written()?.focus();
            const still = spot.current && Math.hypot(e.clientX - spot.current[0], e.clientY - spot.current[1]) < 3;
            // The second click of a double click does not open the field: the double click does, with no word picked.
            if (touch.current || (still && e.detail < 2)) pick(e.target as Element, false, undefined, [e.clientX, e.clientY]);
          }}
          // A drag over the cells of the table being edited picks the cells between its start and the pointer.
          onMouseMove={(e) => {
            if (!cellDrag.current || e.buttons !== 1 || !table) return;
            const over = document.elementsFromPoint(e.clientX, e.clientY).map((el) => el.closest<HTMLElement>("[data-cell]")).find((el) => el && el.closest(`[data-id="${table.id}"]`));
            if (!over) return;
            const at = anchorOf(table.props, +over.dataset.cell!);
            setReach(at === slot ? undefined : at);
          }}
          onDoubleClick={(e) => brush || openStone(e.target as Element) || edit((e.target as Element).closest<HTMLElement>(".block")?.dataset.id, e.target as Element)}
          // A held finger gets no menu, and a mouse the editor's own, unless a field keeps the browser's.
          // In a field the browser's own menu stays, a finger's and a mouse's alike.
          onContextMenu={(e) => {
            const el = e.target as Element;
            if (touch.current ? !el.closest(".ProseMirror, textarea, input, select") : menuAt(el, e.clientX, e.clientY)) e.preventDefault();
          }}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={(e) => {
            clearTimeout(hold.current);
            // Lifting the finger after a hold is not a tap.
            if (held.current) e.preventDefault();
            // A finger held still opens the menu on the lift, where it lies.
            if (held.current && !away.current && !e.touches.length) menuAt(downOn.current!, e.changedTouches[0].clientX, e.changedTouches[0].clientY);
          }}
          // The browser took the touch for its own, a scroll: no finger holds, and the next lift is a tap again.
          onTouchCancel={() => {
            clearTimeout(hold.current);
            held.current = false;
          }}
        >
          {pages.map((p, n) => (
            <div
              key={n}
              data-page={n}
              className={`sheet${cellOf(p) ? " grid" : ""}${n === page ? " on" : ""}`}
              ref={n === page ? sheet : undefined}
              style={{ width: sizes[n][0] * k, height: sizes[n][1] * k, "--cell": `${cellOf(p) * k}px`, "--across": `${across}px`, "--down": `${down}px` } as CSSProperties}
            >
              {/* The blocks are laid out as the PDF's are and scaled to the zoom as one. What marks or moves them lies
                  beside them, in px of the screen. */}
              <div className={keepsFractions() ? "scaled fractions" : "scaled"} style={{ width: sizes[n][0] * K, height: sizes[n][1] * K, transform: `scale(${k / K})`, "--px": `${K / k}px` } as CSSProperties}>
                <PageNumber doc={hist.doc} page={n} />
                {p.blocks.map((b) => (

                  <div
                    key={b.id}
                    data-id={b.id}
                    className={ids.includes(b.id) ? "block sel" : "block"}
                    style={{ left: b.x * K, top: b.y * K, width: b.w * K, height: b.h * K, zIndex: b.z, ...turned(b) }}
                  >
                    <Draw block={b} k={K} solved={solved} at={editing === b.id ? slot : undefined} reach={editing === b.id ? reach : undefined}>
                      {/* Only the text being edited needs a field; the others draw as they do in the PDF. */}
                      {boxed(b) && editing === b.id ? (
                        <Field
                          view={field}
                          props={boxed(b)!}
                          hint={b.type === "text"}
                          all={entire.current}
                          at={clicked.current}
                          change={look}
                          pick={(next) => setPart((now) => (JSON.stringify(now) === JSON.stringify(next) ? now : next))}
                          blur={(e) => stays(e) || setEditing("")}
                          end={() => setEditing("")}
                        />
                      ) : b.type === "text" && !b.props.text && !b.props.rich && b.props.list !== true ? (
                        <div className="rich" data-hint="">
                          <p>
                            <br />
                          </p>
                        </div>
                      ) : b.type === "ruling" && !listOf(b) ? (
                        <textarea
                          className="written"
                          data-trace={traceOf(b.props)}
                          data-fade={fadeOf(b.props)}
                          value={b.props.text ?? ""}
                          readOnly={editing !== b.id}
                          // Tab from a field of the panel does not stop at a Lineatur that is not written in.
                          tabIndex={editing === b.id ? undefined : -1}
                          style={writtenStyle(b, K)}
                          onChange={(e) => typeRuling(b, e.target.value, e.currentTarget)}
                          // Tab types nothing and stays here: the browser's would end the writing. Escape and F2 end
                          // it themselves: after a press in the panel the blur would not.
                          onKeyDown={(e) => {
                            if (e.key === "Tab") e.preventDefault();
                            if (e.key !== "Escape" && e.key !== "F2") return;
                            e.currentTarget.blur();
                            setEditing("");
                          }}
                          onBlur={(e) => stays(e) || setEditing("")}
                          // A line typed past the last row would scroll the others off their rows.
                          onScroll={(e) => (e.currentTarget.scrollTop = 0)}
                        />
                      ) : b.type === "table" && editing === b.id ? (
                        <textarea
                          value={b.props.cells.flat()[slot]}
                          onChange={(e) => {
                            setReach(undefined);
                            // A table without row heights gets, with the first text typed in it, the heights its rows have
                            // now: from then on a row grows alone, as in PowerPoint, and comes back when its text goes. A
                            // table saved lower than its texts need has no such heights.
                            const grid = e.currentTarget.closest<HTMLElement>(".table")!;
                            // The box of solution words is the grid's rows after the table's own, so the rows fill b.h less that.
                            // What the box is stretched by goes to the rows, so they and the box as it needs to be fill b.h.
                            const boxMm = getComputedStyle(grid).gridTemplateRows.split(" ").slice(b.props.cells.length).reduce((all, p) => all + parseFloat(p) / K, 0);
                            const fill = boxMm > 0 ? b.h - EDGE - boxOf(grid, b.props.cells.length) : sum(laidMm);
                            const rows = !heightsOf(b.props) && laidMm.length && Math.abs(sum(laidMm) - (b.h - EDGE - boxMm)) <= 0.05 ? { rows: laidMm.map((h) => round((h * fill) / sum(laidMm))) } : {};
                            // The table may come down with its text when it has no spare room now: a table made taller
                            // than its rows need keeps that height.
                            const own = grid.style.height;
                            grid.style.height = "auto";
                            sink.current = "rows" in rows || parseFloat(getComputedStyle(grid).height) / K >= b.h - 0.05;
                            grid.style.height = own;
                            style("table", { cells: b.props.cells.map((row, r) => row.map((text, c) => (r * row.length + c === slot ? e.target.value : text))), ...rows }, "text");
                          }}
                          onKeyDown={(e) => hop(e, b)}
                          onBlur={(e) => stays(e) || setEditing("")}
                        />
                      ) : b.type === "points" && editing === b.id ? (
                        <ScoreInput max={b.props.max} change={(max) => scoreOn(b.id, max, n)} end={() => setEditing("")} blur={(e) => stays(e) || setEditing("")} />
                      ) : b.type === "name" && editing === b.id ? (
                        // Each word is a field of its own, in its place on the line. Enter and leaving the line keep them.
                        words.map((word, i) => (
                          <input
                            key={i}
                            aria-label={`Feld ${i + 1}`}
                            value={word}
                            onChange={(e) => setWords((ws) => ws.map((w, j) => (j === i ? e.target.value : w)))}
                            onKeyDown={(e) => {
                              if (e.key === "Escape") setEditing("");
                              if (e.key === "Enter" || e.key === "F2") e.currentTarget.blur();
                            }}
                            onBlur={(e) => {
                              if ((e.relatedTarget as Element | null)?.closest(`[data-id="${b.id}"]`)) return;
                              stays(e) || setEditing("");
                            }}
                          />
                        ))
                      ) : undefined}
                    </Draw>
                    {stone?.id === b.id && (
                      <input
                        className="stone-field"
                        inputMode="numeric"
                        aria-label="Zahl im Stein"
                        autoFocus
                        value={stone.text}
                        style={{ left: stone.box[0], top: stone.box[1], width: stone.box[2], height: stone.box[3], fontSize: stone.box[3] * 0.6 }}
                        onFocus={(e) => e.currentTarget.select()}
                        onKeyDown={(e) => {
                          // The keys are the field's: the sheet's own keys do not take the digits or the Enter.
                          e.stopPropagation();
                          if (e.key === "Enter" || e.key === "Escape") setStone(null);
                        }}
                        onBlur={() => setStone(null)}
                        onChange={(e) => {
                          if (!/^\d{0,4}$/.test(e.target.value)) return;
                          setStone({ ...stone, text: e.target.value });
                          typeStone(b, stone.wall, stone.at, e.target.value);
                        }}
                      />
                    )}
                    {b.type === "text" && stepOf(b.props.lines) > 0 && <Numbers block={b} />}
                    <Mark block={b} k={K} n={ns.get(b.id)} />
                  </div>
                ))}
              </div>
              {/* The sheet's guide lines lie on every page; a page's own are drawn dotted. */}
              {[undefined, n].flatMap((at) =>
                (["x", "y"] as const).flatMap((axis) =>
                  // A sheet's line past a smaller page is not drawn there, unless its tab is held on that page: the
                  // tab must stay to hear its letting go (#525).
                  (at === undefined ? guides : (p.guides ?? NONE))[axis].map((mm, i) => (at === undefined && mm > sizes[n][axis === "x" ? 0 : 1] && sliding.current !== `${n}${axis}${i}`) || (
                    <i key={`${at}${axis}${i}`} className={`rule ${axis}${at === undefined ? "" : " own"}`} style={axis === "x" ? { left: mm * k } : { top: mm * k }}>
                      <b
                        data-axis={axis}
                        data-i={i}
                        data-page={at}
                        // The right button drags nothing: its menu removes this one line, and picks no block.
                        onPointerDown={(e) => e.button === 0 && ((sliding.current = `${n}${axis}${i}`), grip(e))}
                        onPointerMove={(e) => slide(e, axis, i, at)}
                        onLostPointerCapture={() => ((sliding.current = ""), drop(axis, i, at))}
                        onContextMenu={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setMenu({ x: e.clientX, y: e.clientY, rule: { axis, i, n: at } });
                        }}
                      >
                        {mm}
                      </b>
                    </i>
                  )),
                ),
              )}
              {n === page && (
                <>
                  {guide[0] !== undefined && <i className="guide" style={{ left: guide[0] * k, height: "100%" }} />}
                  {guide[1] !== undefined && <i className="guide" style={{ top: guide[1] * k, width: "100%" }} />}
                  {table?.props.cols.slice(1).flatMap((_, i) =>
                    // A line that runs through a merged cell does not show there: its handle keeps to the rows where it does.
                    shown(table, i).map(([top, height]) => (
                      <i
                        key={`${i} ${top}`}
                        className="bar"
                        style={{ left: (table.x + (sum(table.props.cols.slice(0, i + 1)) / sum(table.props.cols)) * table.w) * k, top: top * k, height: height * k }}
                        onPointerDown={grip}
                        onPointerMove={(e) => widen(e, table, i)}
                      />
                    )),
                  )}
                  {/* Over the lines' handles, which run along the cells' edges where these stand. The sheet's touch, a
                      hold that opens a menu, is not theirs: it took the click of the next tap. */}
                  {table && grips.map((g) => (
                    <i key={g.corner} className={`cell-handle cell-handle-${g.corner}`} style={{ left: g.x, top: g.y }} onPointerDown={(e) => gripDown(e, g.corner)} onTouchStart={(e) => e.stopPropagation()} onPointerMove={gripMove} onPointerUp={gripUp} onPointerCancel={gripUp} />
                  ))}
                  {cropping && <Crop block={cropping} box={whole(cropping)} cut={draft!.cut} k={k} grip={grip} trim={trim} />}
                  {line &&
                    [false, true].map((end) => (
                      <i
                        key={+end}
                        className={line.props.kind === "double" || (end && line.props.kind === "arrow") ? "end tip" : "end"}
                        style={{ left: (line.x + (far(line, 1, end) ? line.w : 0)) * k, top: (line.y + (far(line, 0, end) ? line.h : 0)) * k }}
                        onPointerDown={grip}
                        onPointerMove={(e) => stretch(e, line, end)}
                        onLostPointerCapture={() => setGuide([])}
                      />
                    ))}
                  {/* A picked bubble whose tail reaches out of its box: a frame round both, the handles stay on the box. */}
                  {sel.filter((b) => drawn(b) && tailReach({ ...b, props: b.props as TextProps }).some((mm) => mm > 0)).map((b) => {
                    const r = reachOf(b);
                    return <i key={`reach-${b.id}`} className="reach" data-id={b.id} style={{ left: (r.x - r.hw) * k, top: (r.y - r.hh) * k, width: 2 * r.hw * k, height: 2 * r.hh * k, transform: b.angle ? `rotate(${b.angle}deg)` : undefined }} />;
                  })}
                  {/* One handle per picked bubble, star or triangle, which moves the point its shape takes. */}
                  {free.length === sel.length && !cropping && sel.filter((b) => drawn(b) && !b.locked).map((b) => (
                    <i
                      key={b.id}
                      className="adjust"
                      data-id={b.id}
                      style={{ left: adjustAt(b)[0] * k, top: adjustAt(b)[1] * k }}
                      onPointerDown={(e) => {
                        adjusting.current = e.pointerId;
                        // A drag of the handle does not grow the shape: the grow would move the handle from the pointer.
                        wrote.current = "";
                        // WebKit captures no pointer it no longer knows, such as a touch a script made: its moves
                        // still come here, by `adjusting`.
                        try {
                          grip(e);
                        } catch {
                          /* not captured */
                        }
                      }}
                      onPointerUp={() => (adjusting.current = undefined)}
                      onPointerCancel={() => (adjusting.current = undefined)}
                      onLostPointerCapture={() => (adjusting.current = undefined)}
                      onTouchStart={(e) => e.stopPropagation()}
                      onPointerMove={(e) => adjust(e, b)}
                    />
                  ))}
                  {/* Moveable's frame round a turned group with a line takes in the line's level box, so the group's own
                      frame is drawn here, where its handles stand. */}
                  {turnedLine &&
                    ((nw, off) => (
                      <div
                        className="turned-frame"
                        style={{ left: nw[0] * k + off[0], top: nw[1] * k + off[1], width: group!.w * k + FRAME.left + FRAME.right, height: group!.h * k + FRAME.top + FRAME.bottom, transform: `rotate(${frame!.turn}deg)` }}
                      />
                    ))(turnedAt([group!.x, group!.y], frame!.turn, frame!.about), turnedAt([-FRAME.left, -FRAME.top], frame!.turn, [0, 0]))}
                  {group &&
                    [0, 1, 2, 3].map((i) => {
                      // On the frame's corners, which stand outside the group's. A turned frame turns them about its middle.
                      const at = turnedAt([group.x + (i % 2) * group.w, group.y + (i >> 1) * group.h], frame!.turn, frame!.about);
                      const off = turnedAt([i % 2 ? FRAME.right : -FRAME.left, i >> 1 ? FRAME.bottom : -FRAME.top], frame!.turn, [0, 0]);
                      return (
                      <i
                        key={i}
                        className="end"
                        style={{ left: at[0] * k + off[0], top: at[1] * k + off[1] }}
                        onPointerDown={(e) => {
                          grip(e);
                          start.current = free;
                        }}
                        onPointerMove={(e) => scale(e, i % 2 > 0, i > 1)}
                        // The render this asks for also measures a text the group made too small.
                        onLostPointerCapture={() => {
                          tight.current = true;
                          setGuide([]);
                        }}
                      />
                      );
                    })}
                  <Moveable
                    ref={moveable}
                    // In crop mode the frame's handles stand in for Moveable's.
                    target={cropping ? [] : targets}
                    draggable={free.length === sel.length}
                    resizable={free.length === sel.length && !sel.some(isLine)}
                    renderDirections={turnedLine ? [] : handles}
                    hideDefaultLines={turnedLine}
                    // A lone line keeps its own handles at its ends, and has no frame.
                    padding={sel.length === 1 && isLine(sel[0]) ? undefined : FRAME}
                    // Each loose block has its own outline from Moveable, which the padding does not reach. Blocks of one
                    // group keep only the frame about them all, so the outlines do not cut their letters.
                    hideChildMoveableDefaultLines={oneGroup}
                    // Loose blocks turned alike would get a frame turned about their middle. Their frame stays level.
                    // A turned group with a line has blocks of two angles: its frame takes the group's own.
                    useDefaultGroupRotate={!oneGroup || !!turnedLine}
                    defaultGroupRotate={turnedLine ? frame!.turn : 0}
                    origin={false}
                    checkInput
                    // Two fingers zoom the desk and are none of Moveable's. Waiting for a second one outside the block,
                    // it would take the next tap anywhere for that finger when the first lifted before its timer ran.
                    pinchOutside={false}
                    snappable={!loose}
                    keepRatio={keep}
                    snapThreshold={6}
                    isDisplaySnapDigit={false}
                    snapDirections={SIDES}
                    elementSnapDirections={SIDES}
                    elementGuidelines={rest}
                    verticalGuidelines={pageXs.map((mm) => mm * k)}
                    horizontalGuidelines={pageYs.map((mm) => mm * k)}
                    // Moveable swallows a tap on what is selected, and a group's box covers its blocks. To Moveable the
                    // lift of a finger that held still is a tap too, on one block and on several: it is none.
                    onClick={(e) => touch.current && !held.current && pick(e.inputTarget, false)}
                    // A press on a block is the desk's to pick by. Moveable drags by it too, and would take it for a click
                    // on the group where the point the mouse reports lies beside what was pressed.
                    onClickGroup={(e) => cover.current && !held.current && !brushing.current && pick(e.inputTarget, e.inputEvent.shiftKey)}
                    // A press on a cell of the table being edited picks cells: it moves no block.
                    onDragStart={(e) => (cellDrag.current || brushing.current ? e.stopDrag() : begin([e.target]))}
                    onDragGroupStart={(e) => (brushing.current ? e.stopDrag() : begin(e.targets))}
                    onDrag={(e) => !brushing.current && drag([e])}
                    onDragGroup={(e) => !brushing.current && drag(e.events, e)}
                    onDragEnd={(e) => leave(e.isDrag)}
                    onDragGroupEnd={(e) => leave(e.isDrag)}
                    // Ctrl resizes about the centre.
                    onBeforeResize={(e) => mod & CENTRE && e.setFixedDirection([0, 0])}
                    onBeforeResizeGroup={(e) => mod & CENTRE && e.setFixedDirection([0, 0])}
                    onResizeStart={(e) => begin([e.target])}
                    onResizeGroupStart={(e) => begin(e.targets)}
                    // A table stays level, and a line turns by its ends.
                    rotatable={!cropping && free.length === sel.length && !sel.some((b) => b.type === "table") && !sel.some((b) => isLine(b) && thing(b) === b.id)}
                    rotationPosition="top"
                    onRotateStart={(e) => {
                      spot.current = [e.clientX, e.clientY];
                      begin([e.target]);
                    }}
                    onRotateGroupStart={(e) => {
                      spot.current = [e.clientX, e.clientY];
                      begin(e.targets);
                    }}
                    onRotate={rotate}
                    onRotateGroup={rotate}
                    onRotateEnd={rotated}
                    // Moveable measures the box around the blocks anew: turned with one group's blocks, else level.
                    onRotateGroupEnd={(e) => {
                      moveable.current!.updateRect();
                      rotated(e);
                    }}
                    onResize={(e) => resize([e])}
                    onResizeGroup={(e) => resize(e.events)}
                    onResizeEnd={(e) => e.lastEvent && settle(e.lastEvent.direction)}
                    onResizeGroupEnd={(e) => e.lastEvent && settle(e.lastEvent.direction)}
                  />
                </>
              )}
            </div>
          ))}
        </div>
        {/* The hand lies over the desk and takes the press, so no block under it is picked or moved. */}
        {(pan || panning) && (
          <div
            className="hand"
            onPointerDown={(e) => {
              // The left button only: the right one opens the menu.
              if (e.button) return;
              e.currentTarget.setPointerCapture(e.pointerId);
              hand.current = [e.clientX, e.clientY, desk.current!.scrollLeft, desk.current!.scrollTop];
              // A drag: the Space was the hand's, not a space to type.
              spaced.current = null;
              setPanning(true);
              // A button that has the focus would take Space's keyup as its click.
              if (document.activeElement instanceof HTMLButtonElement) document.activeElement.blur();
            }}
            onPointerMove={(e) => {
              if (!panning) return;
              // The button came up where the hand could not see it.
              if (!e.buttons) return setPanning(false);
              steer();
              dragDesk(e);
            }}
            onPointerUp={() => setPanning(false)}
            onPointerCancel={() => setPanning(false)}
          />
        )}
        {/* What can go on the page floats over the desk's lower edge. */}
        {leaf ? (
          <>
            <div className="dock">{zoomer}</div>
            {pages.length > 1 && (
              <div className="dock at">
                Seite {page + 1} von {pages.length}
              </div>
            )}
          </>
        ) : (
          <div className="dock" role="toolbar" aria-label="Einfügen" onPointerOver={holdName}>
            {tools}
          </div>
        )}
      </div>
      {/* The drag box is for a mouse on empty desk; a finger there scrolls. */}
      <Selecto
        dragContainer=".desk"
        selectableTargets={[".block"]}
        hitRate={0}
        selectByClick={false}
        onDragStart={(e) => {
          const el = e.inputEvent.target as Element;
          if (e.inputEvent.type === "touchstart" || el.closest(".block, .end, .adjust, .rule, .bar, .crop") || moveable.current!.isMoveableElement(el)) e.stop();
        }}
        // The box selects on the page in use, which the press that began it has set.
        onSelectEnd={(e) => setIds((now) => grouped([...now, ...e.selected.filter((el) => sheet.current!.contains(el)).map(idOf)], blocks))}
      />

      {right && (
        <aside className="panel">
          {!leaf && (
            <div className="tabs" role="tablist">
              {TABS.map((t) => (
                <button key={t} role="tab" data-tour={t} aria-selected={tab === t} onClick={() => setTab(t)}>
                  {t}
                </button>
              ))}
            </div>
          )}
          {tab === "Format" && !sel.length && <p className="hint">Wähle etwas auf dem Blatt aus, um es zu formatieren.</p>}
          {/* Blattform's panel has no tabs, and its bar no room for one more mode: there this button leads to the
              list, and "Start" in the bar leads back. */}
          {tab === "Format" && !sel.length && leaf && <button onClick={() => setTab("Lernwörter")}>Lernwörter</button>}
          {tab === "Format" && sel.length > 0 && (
            <>
              <p className="what">
                {pickName(sel, blocks)}
              </p>
              <Format
                owe={(entry) => owe(file.id, entry)}
                // A block of a group with a locked one is as fixed there as the locked one.
                sel={sel.map((b) => (free.includes(b) ? b : { ...b, locked: true }))}
                style={style}
                bump={bump}
                look={look}
                mendWord={mendWord}
                traced={traced}
                paint={paint}
                itemize={itemize}
                gap={gapping}
                every={gapEvery}
                part={part}
                // A text that a typed size left higher than its box grows back, as after a resize by handle.
                place={(boxes, key) => {
                  tight.current = true;
                  place(boxes, key);
                }}
                rank={rank}
                cell={editing && editing === table?.id ? slot : undefined}
                reach={editing && editing === table?.id ? reach : undefined}
                merge={merge}
                unmerge={unmerge}
                laid={laidMm}
                full={full}
                cramped={cramped}
                held={heldIds}
                onSize={(ids) => (panelSized.current = ids)}
                sizeCells={sizeCells}
                evenCells={evenCells}
                lines={drawLines}
                border={table && border}
                cutting={cutting}
                cropping={!!cropping}
                spin={spin}
                mirror={mirror}
                alone={(b) => thing(b) === b.id}
                lock={lock}
                setLock={setLock}
                from={from}
                setFrom={setFrom}
                size={[W, H]}
                doc={hist.doc}
                crop={sel.length === 1 && free[0]?.type === "image" ? () => (cropping ? done() : edit(free[0].id)) : undefined}
                words={learnt}
                lineaturen={lineaturen}
                list={takeList}
                link={takeText}
                feed={feed}
                toList={() => setTab("Lernwörter")}
              />
              {free.length > 0 && free.every((b) => b.type === "image") && (
                <>
                  <h2>Bild</h2>
                  <label>
                    Transparenz
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={Math.round((1 - ((free[0] as ImageBlock).props.opacity ?? 1)) * 100)}
                      onChange={(e) => fadePicture(Math.round(100 - +e.target.value) / 100)}
                    />
                  </label>
                </>
              )}
              {boxes.length > 0 && (
                <>
                  <h2>Füllung und Rand</h2>
                  {/* A line stays a line. */}
                  {!rulers.length && (
                    <div className="seg">
                      {FRAMES.map(([kind, label]) => (
                        <button key={kind} className={(boxes[0].props.kind ?? "rect") === kind ? "on" : ""} onClick={() => look((boxes[0].props.kind ?? "rect") === kind ? { kind } : { kind, inside: true })}>
                          {label}
                        </button>
                      ))}
                    </div>
                  )}
                  <label>
                    Füllung
                    <input type="color" value={fill === "none" ? "#ffffff" : fill} onChange={(e) => look({ fill: e.target.value }, "fill")} />
                  </label>
                  {/* How far the fill lets through what lies behind it: the text and the border stay solid. */}
                  {!isLine(boxes[0]) && <label>
                    Transparenz
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={Math.round((1 - (boxes[0].props.opacity ?? 1)) * 100)}
                      disabled={fill === "none"}
                      onChange={(e) => look({ opacity: Math.round(100 - +e.target.value) / 100 }, "opacity")}
                    />
                  </label>}
                  {/* The next fill is solid again, as in PowerPoint. */}
                  <button className="wide" disabled={fill === "none"} onClick={() => look({ fill: "none", opacity: undefined })}>Keine Füllung</button>
                  <label>
                    Rand
                    <input type="color" value={stroke === "none" ? "#222222" : stroke} onChange={(e) => look({ stroke: e.target.value }, "stroke")} />
                  </label>
                  {!rulers.length && <button className="wide" disabled={stroke === "none"} onClick={() => look({ stroke: "none", strokeOpacity: undefined })}>Kein Rand</button>}
                  <label>
                    Randstärke
                    <input
                      type="range"
                      min={0.25}
                      max={3}
                      step={0.25}
                      value={boxes[0].props.strokeWidth ?? 0.5}
                      onChange={(e) => look({ strokeWidth: +e.target.value }, "strokeWidth")}
                    />
                  </label>
                  {/* How far the border lets through what lies behind it. A line has only this slider. */}
                  <label>
                    {isLine(boxes[0]) ? "Transparenz" : "Transparenz Linie"}
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={Math.round((1 - (boxes[0].props.strokeOpacity ?? 1)) * 100)}
                      disabled={stroke === "none"}
                      onChange={(e) => look({ strokeOpacity: Math.round(100 - +e.target.value) / 100 }, "strokeOpacity")}
                    />
                  </label>
                  {/* No style is lit while there is no border to show it. */}
                  <div className="seg">
                    {DASHES.map(([dash, label, sign]) => (
                      <button key={label} className={stroke !== "none" && boxes[0].props.dash === dash ? "on" : ""} aria-label={label} title={label} onClick={() => look({ dash })}>
                        {sign}
                      </button>
                    ))}
                  </div>
                </>
              )}
              {rulers.length > 0 && rulers.length === sel.length && (
                <>
                  <h2>Strecke</h2>
                  <label>
                    Länge in cm
                    <input
                      type="number"
                      min={0.1}
                      step={0.1}
                      value={Math.round(Math.hypot(rulers[0].w, rulers[0].h) * 10) / 100}
                      disabled={free.length < sel.length}
                      onChange={(e) => +e.target.value > 0 && extend(+e.target.value * 10)}
                    />
                  </label>
                  <button className={rulers[0].props.ticks ? "wide on" : "wide"} aria-pressed={!!rulers[0].props.ticks} onClick={() => style("shape", { ticks: !rulers[0].props.ticks })}>
                    Striche an den Enden
                  </button>
                  <h2>Länge anschreiben</h2>
                  <div className="seg">
                    {LABELS.map(([label, name]) => (
                      <button key={name} className={rulers[0].props.label === label ? "on" : ""} onClick={() => style("shape", { label })}>
                        {name}
                      </button>
                    ))}
                  </div>
                </>
              )}
              <h2>Ausrichten</h2>
              {/* What the blocks line up with. One block has only the page. */}
              <div className="seg">
                <button className={among ? "on" : ""} aria-pressed={among} disabled={things.length < 2} onClick={() => setOnPage(false)}>Auswahl</button>
                <button className={among ? "" : "on"} aria-pressed={!among} disabled={things.length < 2} onClick={() => setOnPage(true)}>Seite</button>
              </div>
              <div className="acts">
                {ALIGNS.map(([axis, at, label, icon]) => (
                  <Tool key={label} icon={icon} label={label} title={label} disabled={!things.length} onClick={() => align(axis, at)} />
                ))}
              </div>
              <h2>Verteilen</h2>
              <div className="acts">
                <button disabled={among ? things.length < 3 : !things.length} onClick={() => distribute("x")}>Waagerecht</button>
                <button disabled={among ? things.length < 3 : !things.length} onClick={() => distribute("y")}>Senkrecht</button>
              </div>
              <h2>Größe angleichen</h2>
              <div className="acts">
                <button disabled={sizable.length < 2} onClick={() => same("w")}>Gleiche Breite</button>
                <button disabled={sizable.length < 2} onClick={() => same("h")}>Gleiche Höhe</button>
              </div>
              <h2>Ebene</h2>
              <div className="acts">
                <button disabled={!stacked(true)} onClick={(e) => layer(e, true)}>Nach vorn</button>
                <button disabled={!stacked(false)} onClick={(e) => layer(e, false)}>Nach hinten</button>
              </div>
              <div className="acts">
                <button disabled={!stacked(true, true)} onClick={(e) => layer(e, true, true)}>Eine nach vorn</button>
                <button disabled={!stacked(false, true)} onClick={(e) => layer(e, false, true)}>Eine nach hinten</button>
              </div>
            </>
          )}
          {tab === "Lernwörter" && (
            <>
              <h2>Lernwörter</h2>
              <textarea
                aria-label="Lernwörter"
                className="wordlist"
                rows={10}
                // The browser's check knows no German on most machines and marks every word (#580).
                spellCheck={false}
                placeholder="Ein Wort pro Zeile"
                ref={listField}
                value={Array.isArray(hist.doc.words) ? hist.doc.words.filter((w) => typeof w === "string").join("\n") : ""}
                onChange={(e) => listWords(e.target.value)}
                // A paste brings its words one to a line, in place of what is picked in the field.
                onPaste={(e) => {
                  e.preventDefault();
                  const field = e.currentTarget;
                  const [from, to] = [field.selectionStart, field.selectionEnd];
                  // A paste that holds no word changes nothing.
                  if (!pasted(e.clipboardData.getData("text/plain")).length) return;
                  const [before, after] = [field.value.slice(0, from), field.value.slice(to)];
                  // The pasted words keep to lines of their own: a word before or behind them is not joined to one.
                  const words = (/[^\n]$/.test(before) ? "\n" : "") + pasted(e.clipboardData.getData("text/plain")).join("\n") + (/^[^\n]/.test(after) ? "\n" : "");
                  caretAt.current = from + words.length;
                  listWords(before + words + after);
                }}
              />
              <p className="hint">Ein Wort pro Zeile. Eine Lineatur oder ein Text nimmt die Wörter unter Format, „Text“.</p>
              {/* Said here too: the list is where a word too many comes from, and the Lernwörter-Blatt picks no block. */}
              {crowded > 0 && (
                <p className="hint" role="status">
                  {crowded === 1 ? "In einer Lineatur passt 1 Wort nicht in die Zeilen." : `In einer Lineatur passen ${crowded} Wörter nicht in die Zeilen.`}
                </p>
              )}
              <button
                disabled={!learnt.length}
                onClick={addBlatt}
                title="Ein Blatt mit Überschrift, Namenszeile und drei Lineaturen: abschreiben, nachspuren, ganze Zeile nachspuren. Viele Wörter gehen auf weiteren Seiten weiter."
              >
                Lernwörter-Blatt
              </button>
              <p className="hint">Ein Blatt mit Überschrift, Namenszeile und drei Lineaturen: abschreiben, nachspuren, ganze Zeile nachspuren. Viele Wörter gehen auf weiteren Seiten weiter.</p>
              {/* A Lineatur as wide as the page between the margins, a row for each word, at most as many as a page holds. */}
              <button
                disabled={!learnt.length}
                title="Eine Lineatur zum Falten: links die Wörter, rechts leere Spalten zum Üben aus dem Gedächtnis."
                onClick={() => addInsert(INSERTS.wordList(learnt.length, [W, H], RULINGS.l3.row))}
              >
                Knickblatt
              </button>
              <p className="hint">Eine Lineatur zum Falten: links die Wörter, rechts leere Spalten zum Üben aus dem Gedächtnis.</p>
            </>
          )}
          {tab === "Ansicht" && (
            <>
              <h2>Format, Raster und Hilfslinien für</h2>
              <div className="seg">
                <button className={own ? "" : "on"} aria-pressed={!own} onClick={() => setOwn(false)}>Alle Seiten</button>
                <button className={own ? "on" : ""} aria-pressed={own} onClick={() => setOwn(true)}>Nur diese Seite</button>
              </div>
              {/* A page's own format or grid stands in for the sheet's; "Wie Blatt" gives the page the sheet's again. */}
              <h2>Format</h2>
              <div className="seg">
                {(own ? [undefined, false, true] : [false, true]).map((c) => {
                  const on = own ? pages[page].landscape === c : !!hist.doc.landscape === c;
                  return (
                    <button key={String(c)} className={on ? "on" : ""} aria-pressed={on} onClick={() => lay(c, own ? page : undefined)}>
                      {c === undefined ? "Wie Blatt" : c ? "Quer" : "Hoch"}
                    </button>
                  );
                })}
              </div>
              <h2>Raster</h2>
              <div className="seg">
                {(own ? [undefined, ...GRIDS] : GRIDS).map((c) => {
                  const on = (own ? pages[page].grid : grid) === c;
                  return (
                    <button
                      key={c ?? "sheet"}
                      className={on ? "on" : ""}
                      aria-pressed={on}
                      onClick={() => (own ? turn((p) => ({ ...p, grid: c })) : update((doc) => ({ ...doc, grid: c! })))}
                    >
                      {c === undefined ? "Wie Blatt" : c ? `${c} mm` : "Aus"}
                    </button>
                  );
                })}
              </div>
              <h2>Hilfslinien</h2>
              <div className="acts">
                <button onClick={() => rule("x")}>
                  <SeparatorVertical size={14} aria-hidden />
                  Senkrecht
                </button>
                <button onClick={() => rule("y")}>
                  <SeparatorHorizontal size={14} aria-hidden />
                  Waagerecht
                </button>
              </div>
              <button
                className="wide"
                disabled={!(own ? mine : guides).x.length && !(own ? mine : guides).y.length}
                onClick={() => rules(own ? page : undefined, () => NONE)}
              >
                <Eraser size={14} aria-hidden />
                Alle entfernen
              </button>
              <p className="hint">Eine einzelne Hilfslinie entfernen: an ihrer Zahl vom Blatt ziehen oder mit der rechten Maustaste auf die Zahl klicken.</p>
              <h2>Seitenzahlen</h2>
              <div className="seg" role="group" aria-label="Seitenzahlen">
                <button className={folio.on ? "" : "on"} aria-pressed={!folio.on} onClick={() => numbering({}, false)}>Aus</button>
                <button className={folio.on ? "on" : ""} aria-pressed={folio.on} onClick={() => numbering({})}>An</button>
              </div>
              {folio.on && (
                <>
                  <h2>Ort</h2>
                  <div className="seg">
                    {[
                      ["bottom", "Unten Mitte"],
                      ["right", "Unten rechts"],
                      ["outer", "Unten außen"],
                      ["top", "Oben rechts"],
                    ].map(([at, label]) => (
                      <button key={at} className={folio.at === at ? "on" : ""} aria-pressed={folio.at === at} onClick={() => numbering({ at: at as PageNumbers["at"] })}>
                        {label}
                      </button>
                    ))}
                  </div>
                  <h2>Form</h2>
                  <div className="seg">
                    {[
                      ["n", "2"],
                      ["seite", "Seite 2"],
                      ["of", "2 / 5"],
                      ["seiteVon", "Seite 2 von 5"],
                    ].map(([form, label]) => (
                      <button key={form} className={folio.form === form ? "on" : ""} aria-pressed={folio.form === form} onClick={() => numbering({ form: form as PageNumbers["form"] })}>
                        {label}
                      </button>
                    ))}
                  </div>
                  <label className="tick">
                    <input type="checkbox" checked={folio.notFirst} onChange={(e) => numbering({ notFirst: e.target.checked })} /> Nicht auf der ersten Seite
                  </label>
                  <h2>Farbe</h2>
                  <div className="seg">
                    <button className={folio.black ? "" : "on"} aria-pressed={!folio.black} onClick={() => numbering({ black: false })}>Grau</button>
                    <button className={folio.black ? "on" : ""} aria-pressed={folio.black} onClick={() => numbering({ black: true })}>Schwarz</button>
                  </div>
                </>
              )}
              {/* Here too, not only in the bar: an iPad's bar has no room for it and folds it under "Mehr". */}
              <h2>Drucken</h2>
              <button className="wide" onClick={(e) => openVariants(e.currentTarget)}>
                <Layers size={14} aria-hidden />
                Varianten drucken
              </button>
            </>
          )}
        </aside>
      )}
      {tour && (
        <Tour
          seen={{ doc: hist.doc, blocks: blocks.length, sel: sel.length, editing: !!editing, tab }}
          show={(t) => {
            if (t === "Vorlagen") return showLeft(true);
            setTab(t);
            showRight(true);
          }}
          close={() => {
            localStorage.setItem("tour", "1");
            setTour(false);
          }}
        />
      )}
      {lens && (
        <ZoomList
          x={lens.x}
          y={lens.y}
          up={lens.up}
          current={Math.round((k * 2540) / 96)}
          onPercent={(p) => zoomTo((p * 96) / 2540 / fit)}
          onWidth={() => zoomTo(1)}
          onFit={fitPage}
          onClose={() => setLens(undefined)}
        />
      )}
      {mathMenu && (
        <Menu
          x={mathMenu.x}
          y={mathMenu.y}
          up
          items={mathBlocks}
          onClose={() => setMathMenu(undefined)}
          onElsewhere={() => setMathMenu(undefined)}
        />
      )}
      {menu && (
        <Menu
          x={menu.x}
          y={menu.y}
          // A command picked in "Mehr" first ends what is written in, as the press of its button in the bar does:
          // the menu has just handed the focus back to it.
          items={
            menu.more
              ? more.map((item) => ({
                  ...item,
                  run: () => {
                    if (document.activeElement?.closest(".block")) (document.activeElement as HTMLElement).blur();
                    item.run();
                  },
                }))
              : items
          }
          // The row of the block menu only, over the picked blocks: not on the page, thumb, rule or cells menus.
          tools={blockMenu ? mini : undefined}
          avoid={blockMenu ? pickedBox() : undefined}
          onClose={() => {
            setMenu(undefined);
            if (late.current) refit();
          }}
          // A right click beside the menu opens it anew on what lies there.
          onElsewhere={(x, y) => {
            flushSync(() => setMenu(undefined));
            // This way no `onClose` comes: the bar that waited under the menu is measured now.
            if (late.current) refit();
            const el = document.elementFromPoint(x, y);
            const n = el?.closest<HTMLElement>("[data-thumb]")?.dataset.thumb;
            const guide = el?.closest<HTMLElement>("[data-axis]");
            if (n) thumbMenu(+n, x, y);
            else if (guide) setMenu({ x, y, rule: { axis: guide.dataset.axis as Axis, i: +guide.dataset.i!, n: guide.dataset.page === undefined ? undefined : +guide.dataset.page } });
            else if (el?.closest(".desk")) menuAt(el, x, y);
          }}
        />
      )}
    </main>
    </Whole.Provider>
    </Words.Provider>
  );
}

// Crop mode, drawn over the picture's block: the whole picture, pale outside the frame, and the frame with a handle
// on each corner and edge. `box` is the whole picture on the page; the block lies inside it.
function Crop({ block, box, cut: [l, t, r, b], k, grip, trim }: {
  block: ImageBlock;
  box: { x: number; y: number; w: number; h: number };
  cut: number[];
  k: number;
  grip: (e: PointerEvent) => void;
  trim: (e: PointerEvent, b: ImageBlock, dx: number, dy: number) => void;
}) {
  const src = `/api/uploads/${block.props.upload}`;
  const inset = [t, r, b, l].map((share) => `${share * 100}%`).join(" ");
  // Along one axis: the frame's near edge, its middle and its far edge.
  const at = (d: number, lo: number, hi: number) => `${(d < 0 ? lo : d > 0 ? 1 - hi : (lo + 1 - hi) / 2) * 100}%`;
  // The picture turns and flips about its block's centre, as the block does.
  const turn = {
    transform: `rotate(${block.angle ?? 0}deg) scale(${block.flipX ? -1 : 1}, ${block.flipY ? -1 : 1})`,
    transformOrigin: `${(block.x + block.w / 2 - box.x) * k}px ${(block.y + block.h / 2 - box.y) * k}px`,
  };
  return (
    <div className="crop" style={{ left: box.x * k, top: box.y * k, width: box.w * k, height: box.h * k, ...turn }}>
      <img className="dim" src={src} alt="" draggable={false} />
      <img src={src} alt="" draggable={false} style={{ clipPath: `inset(${inset})` }} />
      <div style={{ inset }} onPointerDown={grip} onPointerMove={(e) => trim(e, block, 0, 0)} />
      {[-1, 0, 1].flatMap((dy) =>
        [-1, 0, 1].map(
          (dx) =>
            (dx || dy) !== 0 && (
              <i key={`${dx}${dy}`} className="end" style={{ left: at(dx, l, r), top: at(dy, t, b) }} onPointerDown={grip} onPointerMove={(e) => trim(e, block, dx, dy)} />
            ),
        ),
      )}
    </div>
  );
}

// The name of a button at a row's end would poke out of the window, or of the panel that cuts it off:
// it shifts to stay 4 px inside.
function holdName(e: PointerEvent<HTMLElement>, within?: Element) {
  const on = (e.target as Element).closest(".ib");
  if (!on) return;
  const name = getComputedStyle(on, "::after");
  // No name hangs there where the pointer is no mouse, and none on a button with its name beside it.
  if (name.position !== "absolute") return;
  const half = (parseFloat(name.width) + parseFloat(name.paddingLeft) + parseFloat(name.paddingRight)) / 2;
  const { left, width } = on.getBoundingClientRect();
  const middle = left + width / 2;
  // A panel shows what lies inside its border and its scrollbar.
  const from = within ? within.getBoundingClientRect().left + within.clientLeft : 0;
  const to = within ? from + within.clientWidth : innerWidth;
  const shift = Math.max(from + 4 + half - middle, 0) + Math.min(to - 4 - half - middle, 0);
  e.currentTarget.style.setProperty("--shift", `${shift}px`);
}

// A button that is its icon; the name shows when the pointer rests on it.
function Tool({ icon: Icon, label, className = "", ...rest }: { icon: LucideIcon; label: string } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button aria-label={label} {...rest} className={`ib ${className}`}>
      <Icon size={16} aria-hidden />
    </button>
  );
}
