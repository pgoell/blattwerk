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
  ImagePlus,
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
import { api, post, type User } from "../api";
import { DRAWERS, opening } from "../components/Blank";
import Failed from "../components/Failed";
import Feedback from "../components/Feedback";
import Logo from "../components/Logo";
import Menu, { type Item } from "../components/Menu";
import ZoomList from "../components/ZoomList";
import Tour from "../components/Tour";
import Variants from "../components/Variants";
import { changed, fresh, redone, returned, undone, type Hist, type Step } from "../history";
import type { EditorView } from "prosemirror-view";
import { attempt, status } from "../fault";
import { ask, attach, discard, flush, get, isGone, keepAsNew, open, overwrite, refused, reset, set, signed, useSaves } from "../saves";
import { Draw, FIELDS, K, MARGIN, Mark, Numbers, PageNumber, PT, Paper, RULINGS, ScoreInput, Whole, Words, bandOf, pageNumbersOf, wordsIn, boxed, cleared, colsOf, dir, fadeOf, far, isLine, kindOf, listOf, listed, mathsHeight, numbers, overFoot, parasOf, read, rowsOf, sizeOf, spliced, squares, stored, stepOf, sum, tall, tied, traceOf, turned, writtenStyle, type Axis, type Block, type Box, type Corner, type Doc, type Fade, type Guides, type ImageBlock, type Kind, type List, type ListMode, type Page, type PageNumbers, type Range, type RulingBlock, type Sheet, type ShapeBlock, type TableBlock, type TextProps } from "../sheet";
import { blatt, follow as growRulings, landed as carried, linked, loose as cutLoose, looseText, pasted, unshown } from "../words";
import Field, { hole, list, tint, type Marks, type Picked } from "./Field";
import { allCells, allGaps, everyNth, everyNthCell } from "../gaps";
import { totals } from "../totals";
import { EDGE, anchorOf, beside, emptied, evened, heightsOf, merged, next, putTsv, rectOf, sized, slotsIn, spanAt, spansOf, tsvOf, unmerged, widthsOf, type Rect } from "../cells";
import { bordered, cutLines, lined, type Border } from "../borders";
import type { LineStyle, Pen } from "../edges";
import Format, { bounds, drawn, has, hull, mirrored, norm, outline, swung } from "./Format";
import { generate, newSeed } from "./Maths";
import { DEFAULTS as DREIECK, heightFor, sane as saneDreieck } from "../rechendreieck";
import { DEFAULTS as STRAHL, below, sane as saneStrahl } from "../zahlenstrahl";
import { DEFAULTS as FELD } from "../hunderterfeld";
import { DEFAULTS as UHR, heightFor as heightForUhr, sane as saneUhr } from "../uhr";
import { DEFAULTS as SELBST, heightFor as heightForSelbst, sane as saneSelbst } from "../selbstkontrolle";
import { heightFor as heightForMauer, sane as saneMauer } from "../zahlenmauer";

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
const LOOK = ["font", "size", "bold", "italic", "underline", "color", "spacing", "align", "valign", "syllables", "tints", "tintsAcross", "trace", "fade", "fill", "opacity", "stroke", "strokeWidth", "dash"] as const;
// The part of it that belongs to the words, with the breaks set by hand, the gaps and the solution words, and the
// Schüttelwörter with their settings: a line takes none of these.
const WORDS: string[] = ["font", "size", "bold", "italic", "underline", "color", "spacing", "align", "valign", "syllables", "tints", "tintsAcross", "breaks", "gapWidth", "bank", "mix", "mixFirst", "mixCaps", "mixLine", "list", "listCols", "holes", "holeSeed"];
type Coat = Partial<TextProps> & { mark?: string; rule?: string; trace?: boolean | "outline" | "dotted"; fade?: Fade; numbering?: string; house?: boolean; houseTint?: "room" | "all"; band?: boolean; bandColor?: string };
// Karo is always in print, and a written exercise is as large as its squares: they have no script and no size.
const takes = (b: Block): readonly (keyof Coat)[] => {
  const school: (keyof Coat)[] = b.type === "ruling" ? (RULINGS[kindOf(b.props.kind)].zones ? ["font", "rule", "trace", "fade", "house", "houseTint", "band", "bandColor"] : RULINGS[kindOf(b.props.kind)].at ? ["font", "rule", "trace", "fade"] : ["rule", "trace", "fade"]) : b.type === "maths" ? (b.props.format === "written" ? ["numbering"] : ["size", "numbering"]) : [];
  return [...(isLine(b) ? (["stroke", "strokeWidth", "dash"] as const) : b.type === "table" ? (["font", "size", "color", "align", "syllables", "tints", "tintsAcross", "rule", "trace", "fade"] as const) : (boxed(b) && LOOK) || school), "mark"];
};
// What a shape gets where the brush brings none: its fill, stroke and width must be set, and a text with no
// `valign` stands at the top, where a shape's would stand in the middle.
const BARE: Record<string, string | number> = { fill: "none", stroke: "none", strokeWidth: 0.5, valign: "top" };
// The frames a text or a shape can have.
const FRAMES: [Kind, string][] = [["rect", "Eckig"], ["rounded", "Abgerundet"], ["circle", "Rund"], ["triangle", "Dreieck"], ["star", "Stern"], ["bubble", "Sprechblase"]];
// A new shape's width in mm, where it is not 60.
const WIDTHS: Partial<Record<Kind, number>> = { circle: 40, triangle: 40, star: 40 };
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
const TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];
// The grid's lines along one side of the page.
const lines = (cell: number, max: number) => (cell ? Array.from({ length: Math.floor(max / cell) + 1 }, (_, i) => i * cell) : []);
const idOf = (el: Element) => (el as HTMLElement).dataset.id!;
// Groups work as in PowerPoint. A block lists the groups it is in, the outermost first, so a group can hold groups.
// These are the ids with those of every block that shares an outermost group with one of them.
const grouped = (ids: string[], bs: Block[]) => {
  const tops = new Set(bs.filter((b) => b.group && ids.includes(b.id)).map((b) => b.group![0]));
  return bs.filter((b) => ids.includes(b.id) || (b.group && tops.has(b.group[0]))).map((b) => b.id);
};
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
  const [file, setFile] = useState<{ sheet: Sheet | null | "failed"; n: number }>();
  const show = (sheet: Sheet | null | "failed") => setFile((was) => ({ sheet, n: (was?.n ?? 0) + 1 }));
  // The tries after a load that failed. Each asks anew, with the loading page up meanwhile.
  const [tries, setTries] = useState(0);
  const retry = () => {
    setFile(undefined);
    setTries((n) => n + 1);
  };
  const here = useRef(true);
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
  const keep = () => void keepAsNew(Number(id)).then((sheet) => sheet && sheet !== "failed" && navigate(`/blatt/${sheet.id}`));
  // Only from the dead sheet's own address: the teacher may have gone on while the server was asked.
  const drop = () => void discard(Number(id)).then((gone) => gone && location.pathname === `/blatt/${id}` && navigate("/"));
  function load() {
    setChoice("busy");
    ask<Sheet>(`/sheets/${id}`).then(
      (sheet) => {
        ended();
        const other = here.current && reset(sheet);
        if (other) show(other);
      },
      (e: Error) => ended(refused(Number(id), e)),
    );
  }
  function over() {
    setChoice("busy");
    overwrite(Number(id)).then(ended);
  }
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
  return <Canvas key={file.n} file={file.sheet} user={user} reload={load} over={over} choice={choice} asNew={keep} discard={drop} />;
}

function Canvas({ file, user, reload, over, choice, asNew, discard }: { file: Sheet; user: User; reload: () => void; over: () => void; choice?: "busy" | "failed"; asNew: () => void; discard: () => void }) {
  // The saver has brought an old document up to date.
  const [hist, draw] = useState<Hist>(() => ({ past: [], doc: file.doc, future: [] }));
  // The same as it stands after every change so far, drawn or not: a change knows at once what the one before left.
  const live = useRef(hist);
  const setHist = (step: (h: typeof hist) => typeof hist) => draw((live.current = step(live.current)));
  const [title, setTitle] = useState(file.title);
  // The sheet's saver: what the server holds, whether a save failed, and whether the server holds a newer document
  // than the one this editor is based on.
  const saver = useSaves().list.find((s) => s.id === file.id);
  const named = useRef(title);
  named.current = title;
  // Whether a new guide line or grid is for the page in use alone.
  const [own, setOwn] = useState(false);
  const [at, setAt] = useState(0);
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
  const [editing, setEditing] = useState("");
  // The cell of the table being edited, counted row by row.
  const [slot, setSlot] = useState(0);
  // The far corner of a selection of cells in the table being edited, and whether a drag picks cells.
  const [reach, setReach] = useState<number | undefined>(undefined);
  const cellDrag = useRef(false);
  // The heights of the rows of the picked table as its grid laid them out, in px.
  const [laid, setLaid] = useState("");
  // Where the caret stood in a cell that a new row or column moves to another place.
  const caret = useRef<number>(undefined);
  // Where the click that opened a text's field landed, on the screen: its caret goes there.
  const clicked = useRef<[number, number]>(undefined);
  // Whether the field that opens next has all its text picked.
  const entire = useRef(false);
  // A name line's words while it is written in, the words it was opened with, and whether Escape ended it.
  const [words, setWords] = useState<string[]>([]);
  const wordsKept = useRef("");
  // The name line being written in, and the page it stands on.
  const nameWriting = useRef<{ id: string; n: number } | undefined>(undefined);
  const escaped = useRef(false);
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
  const [menu, setMenu] = useState<{ x: number; y: number; thumb?: number; more?: boolean; cells?: boolean; rule?: { axis: Axis; i: number; n?: number } }>();
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
  // The panel's lock: a new width sets the height to match, in its fields and on the handles.
  const [lock, setLock] = useState(false);
  const [pane, setPane] = useState(true);
  // Blattform lays the editor out anew on a wide window: the left panel holds what can be inserted, and Start,
  // Ansicht and Vorlagen in the bar pick what the panels show. `side` then means that Vorlagen is open. `opening`
  // tells when the layout is that one and how the panel of pages and templates starts.
  const { leafy } = opening();
  const [side, setSide] = useState(() => opening().side);
  // Upright, at most one panel is open and both start shut. `side` and `pane` keep what the window on its side shows.
  const drawers = useSyncExternalStore(whenTurned, () => DRAWERS.matches);
  const [drawer, setDrawer] = useState<"left" | "right">();
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
  // A thumbnail's width in px.
  const [thumb, setThumb] = useState(97);
  // Space held makes the pointer a hand, and a drag with it moves the desk. The drag may outlast the key.
  const [pan, setPan] = useState(false);
  const [panning, setPanning] = useState(false);
  // Where the hand's drag began: the pointer, and the desk's scroll.
  const hand = useRef([0, 0, 0, 0]);
  // Space pressed on a picked text, shape, table or Lineatur: opens it at the keyup, unless the hand dragged meanwhile.
  const spaced = useRef<(() => void) | null>(null);
  const stage = useRef<HTMLDivElement>(null);
  const desk = useRef<HTMLDivElement>(null);
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
  // What Moveable said of a drag while the finger had not yet left there.
  const owed = useRef<OnDrag[]>(undefined);
  // The thumbnails, and the press on one of them: where it began, and its gap once it is a drag.
  const strip = useRef<HTMLDivElement>(null);
  const tug = useRef<{ from: number; x: number; y: number; slot?: number }>(undefined);
  const press = useRef(0);
  // The panel scrolls while a drag rests near its edge: the frame that does it, its speed and the pointer.
  const auto = useRef({ frame: 0, speed: 0, x: 0, y: 0, last: 0, rest: 0 });
  // Set by a drag, for the click that follows it.
  const dragged = useRef(false);
  const grab = useRef([0, 0]);
  const spot = useRef<number[]>(undefined);
  const start = useRef<Block[]>([]);
  const pinch = useRef({ spread: 1, zoom: 1, x: 0, y: 0 });

  const { pages, guides, grid } = hist.doc;
  // The sheet's Lernwörter, the same list until the sheet's own changes.
  const learnt = useMemo(() => wordsIn(hist.doc), [hist.doc.words]);
  // How many of them the most crowded Lineatur of the sheet cannot show.
  const lineaturen = useMemo(() => pages.flatMap((p) => p.blocks).filter((b): b is RulingBlock => b.type === "ruling"), [pages]);
  const crowded = unshown(lineaturen, learnt);
  // One page is in use: it holds the selection, and new and pasted blocks land on it. Undo can take it away.
  const page = Math.min(at, pages.length - 1);
  const { blocks } = pages[page];
  // Each page's width and height in mm.
  const sizes = pages.map((_, n) => sizeOf(hist.doc, n));
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
  // Moveable collapses a group that holds a flat line, so a group with a line gets its own corner handles.
  const group = free.length > 1 && free.length === sel.length && sel.some(isLine) ? bounds(sel) : undefined;
  // Picked as one group, they show one frame, as in PowerPoint: their own outlines go, and the frame lies outside them.
  const oneGroup = sel.length > 1 && (sel[0].group ?? []).some((g) => sel.every((b) => b.group?.includes(g)));
  // A picture, a symbol and a Hunderterfeld always keep their shape, so only their corners have handles.
  const shaped = sel.some((b) => b.type === "image" || b.type === "symbol" || b.type === "hunderterfeld");
  const keep = (mod & KEEP) > 0 || shaped || lock;
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
  // A box grows with its text, as a PowerPoint text box does, and never shrinks by itself. Only a change the teacher
  // makes is measured, so a sheet that opens stays as saved. The frame says how high it would be with no height
  // set; the top edge stays. The new height adds no step to undo: it belongs to the change that asked for it.
  useLayoutEffect(() => {
    if (!tight.current) return;
    tight.current = false;
    const snug = sink.current;
    sink.current = false;
    const grown = new Map<string, Partial<Block>>();
    // The linked texts on the page in view grow with the list too, picked or not.
    const measured = [...sel, ...blocks.filter((b) => !ids.includes(b.id) && !b.locked && boxed(b)?.list === true)];
    for (const b of measured) {
      // A table's rows are each as high as their highest cell when its height is not set.
      const frame = sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] > :is(.frame, .table)`);
      if (!frame) continue;
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
      const kept = b.type === "table" ? heightsOf(b.props) : undefined;
      // A table with its rows set goes back to what they need when a text in it changed, down as well. A text box
      // never shrinks by itself. No other change brings a table down: a height the teacher set holds.
      const down = snug && kept;
      if (down ? Math.abs(h - b.h) <= 0.05 : h <= b.h) continue;
      // The edge the words start at stays in its place on the page, turned or not.
      grown.set(b.id, tall(b, h));
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
    if (escaped.current || !fields.length || fields.join("\n") === wordsKept.current) return;
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
      if ((e.key === "Escape" || e.key === "Enter") && el.matches(".panel select")) back(el);
    };
    window.addEventListener("change", chosen);
    window.addEventListener("keyup", shut);
    window.addEventListener("keydown", press);
    window.addEventListener("paste", pasted, true);
    window.addEventListener("dragover", dragged, true);
    window.addEventListener("drop", dragged, true);
    return () => {
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
  onDrag.current = (e) => {
    if (!e.dataTransfer?.types.includes("Files")) return;
    if (document.querySelector("dialog:modal .pick")?.contains(e.target as Node)) return;
    e.preventDefault();
    e.stopPropagation();
    const on = desk.current!.contains(e.target as Node) && !document.querySelector("dialog:modal");
    if (e.type === "dragover") e.dataTransfer.dropEffect = on ? "copy" : "none";
    else if (on) dropped([...e.dataTransfer.files], e.clientX, e.clientY);
  };
  // Ctrl+V comes as the browser's paste, which alone brings a picture copied in another app. A field keeps a paste
  // of words as its own. A picture has no place in a text's, a cell's or a Lineatur's field, so it lands on the
  // sheet as from anywhere else; one that comes with words, as cells copied in Excel do, stays the field's.
  // Outside a field, words copied in another app make a text block; the editor's own bring the copied blocks.
  onPaste.current = (e) => {
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
    if (!picture || writing.current) {
      if (writing.current || !typed(e.clipboardData?.getData("text/plain") ?? "")) paste();
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
      list = select && target.matches(":open");
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
      if (moveable.current?.isDragging()) moveable.current.stopDrag();
      else {
        grasp.current!.el.releasePointerCapture(grasp.current!.id);
        setDraft(grasp.current!.draft);
      }
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
    const ours = (e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key) && target.closest(".ProseMirror, .table, input.mm, input.score, input[type=range], input[type=checkbox], input[type=number]:not(.own), select, textarea.wordlist");
    if (!ours && !shut && target.closest(".ProseMirror, textarea, input, select")) return;
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
      press.current = window.setTimeout(() => aim(x, y), 500);
    }
    function onMove(e: globalThis.TouchEvent) {
      if (!tug.current) return;
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
    sheet.current!.scrollIntoView({ behavior: "smooth" });
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
  function style(type: Block["type"], props: object, key?: string) {
    if (type === "table" || key === "words") tight.current = true;
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || b.type !== type) return b;
          const next = { ...b, props: { ...b.props, ...fresh(b, props) } } as Block;
          return { ...next, ...grown(b, next) } as Block;
        }),
      key,
    );
  }
  // A maths block grows downward when a change in its panel needs more room, to the page's foot at most, in the same
  // undo step; it never shrinks by itself. A Zahlenstrahl grows by what its line rises, so the line keeps its place.
  // The blocks that grow so that their drawing keeps the size of the default block's: the height their props need at
  // width w, and the props that change it (#588, #598).
  const GROWS: Partial<Record<Block["type"], [(props: any, w: number) => number, string[]]>> = {
    rechendreieck: [(p, w) => heightFor(saneDreieck(p), w), ["count", "columns"]],
    zahlenmauer: [(p, w) => heightForMauer(saneMauer(p), w), ["count", "columns", "base"]],
    uhr: [(p, w) => heightForUhr(saneUhr(p), w), ["count", "cols"]],
  };
  function grown(b: Block, next: Block): Partial<Box> {
    const foot = Math.max(b.h, H - MARGIN - b.y);
    if (b.type === "zahlenstrahl" && next.type === "zahlenstrahl") {
      const more = below(saneStrahl(next.props), b.w) - below(saneStrahl(b.props), b.w);
      if (more > 0) return tall(b, round(Math.min(b.h + more, foot)));
    }
    // A Selbstkontrolle grows with its form, its links or its word, as its content needs, and needs the sheet to count its tasks.
    if (b.type === "selbstkontrolle" && next.type === "selbstkontrolle" && (["form", "links", "word", "size", "title", "turn"] as const).some((key) => next.props[key] !== b.props[key])) {
      const need = round(Math.min(heightForSelbst(saneSelbst(next.props), hist.doc, b.w), foot));
      if (need > b.h) return tall(b, need);
    }
    const grow = GROWS[b.type];
    if (grow && b.type === next.type && grow[1].some((key) => (next.props as any)[key] !== (b.props as any)[key])) {
      const need = round(Math.min(grow[0](next.props, b.w), foot));
      if (need > b.h) return tall(b, need);
    }
    return {};
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
      if (n === page) return;
      setIds([]);
      setDraft(undefined);
    });
    // A page in use that lies partly in view stays put: the desk does not jump to its top.
    const [on, view] = [sheet.current!.getBoundingClientRect(), desk.current!.getBoundingClientRect()];
    if (n !== page || on.bottom <= view.top || on.top >= view.bottom) sheet.current!.scrollIntoView({ behavior: "smooth" });
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
      setIds([]);
    });
    sheet.current!.scrollIntoView({ behavior: "smooth" });
  }
  function visit(n: number) {
    done();
    [steered.current, scrollHeld.current, lagged.current] = [0, false, false];
    flushSync(() => {
      setAt(n);
      setIds([]);
    });
    sheet.current!.scrollIntoView({ behavior: "smooth" });
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
  function removePage(n = page) {
    // The page in use stays, one place back when a page before it goes; a page gone itself hands it to the one in its place.
    // It stays on the desk where it was too: the zoom may change with the widest page, so its top is measured before and after.
    const was = sheet.current!.getBoundingClientRect().top;
    flushSync(() => {
      update((doc) => ({ ...doc, pages: doc.pages.filter((_, i) => i !== n) }), "", n < page ? page - 1 : Math.min(page, pages.length - 2));
      setIds([]);
    });
    desk.current!.scrollBy(0, sheet.current!.getBoundingClientRect().top - was);
  }
  // Puts a page at another place among the pages. It is the page in use from then on.
  function movePage(from: number, to: number) {
    if (from === to) return;
    done();
    flushSync(() => {
      update((doc) => {
        const rest = doc.pages.filter((_, i) => i !== from);
        return { ...doc, pages: [...rest.slice(0, to), doc.pages[from], ...rest.slice(to)] };
      }, "", to);
      setAt(to);
      setIds([]);
    });
    sheet.current!.scrollIntoView({ behavior: "smooth" });
  }
  // The copy comes after its page and takes its place. It has the page's guide lines, grid and format, and blocks
  // of its own.
  function copyPage(n = page) {
    done();
    flushSync(() => {
      update((doc) => ({ ...doc, pages: doc.pages.flatMap((p, i) => (i === n ? [p, { ...p, blocks: cloned(p.blocks, p.blocks) }] : [p])) }), "", n + 1);
      setAt(n + 1);
      setIds([]);
    });
    sheet.current!.scrollIntoView({ behavior: "smooth" });
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
    const { from, slot } = tug.current ?? {};
    quit();
    if (slot === undefined) return;
    const to = landing(from!, slot);
    movePage(from!, to);
    strip.current!.querySelector(`[data-thumb="${to}"]`)?.scrollIntoView({ block: "nearest" });
  }
  // On a thumbnail Ctrl with an arrow moves its page by one place, with Shift to the start or the end, and Ctrl+D
  // copies it. The focus follows the page.
  function pageKey(e: Key, n: number) {
    // Delete and Backspace take the thumbnail's page away, never the picked blocks, and the last page stays.
    if (/^(Delete|Backspace)$/.test(e.key) && !(e.ctrlKey || e.metaKey || e.altKey || e.shiftKey)) {
      e.preventDefault();
      e.stopPropagation();
      // A page being dragged stays: the drop would look for it.
      if (pages.length < 2 || tug.current) return;
      removePage(n);
      strip.current!.querySelector<HTMLElement>(`[data-thumb="${Math.min(n, pages.length - 2)}"]`)!.focus();
      return;
    }
    if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
    const last = pages.length - 1;
    const copy = /^d$/i.test(e.key) && !e.shiftKey;
    const to = copy ? n + 1 : e.key === "ArrowUp" ? (e.shiftKey ? 0 : Math.max(0, n - 1)) : e.key === "ArrowDown" ? (e.shiftKey ? last : Math.min(last, n + 1)) : -1;
    if (to < 0) return;
    // The window's own Ctrl+D copies blocks, and Chrome's sets a bookmark.
    e.preventDefault();
    e.stopPropagation();
    if (copy) copyPage(n);
    else movePage(n, to);
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
  function follow() {
    if (performance.now() > steered.current && !scrollHeld.current) return;
    if (editing) lagged.current = true;
    else inView();
  }
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
  }

  // Notes page `was` for what the server sends later, and gives a way to look it up then. The pages may have changed
  // by that time: the page is found where it is now; one changed since is known by a block it still holds, or keeps
  // its number while the pages are as many as before. For a page that is gone, the page in use stands in.
  function mark(was = page) {
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
  function add(w: number, h: number, rest: Fresh, n = page, pasted = false) {
    const { doc } = latest.current;
    const [held, size] = [doc.pages[n].blocks, sizeOf(doc, n)];
    const id = crypto.randomUUID();
    // A turned block counts with the box it fills on the page, turned about its middle.
    const outer = held.map((b) => {
      const [c, s] = dir(b).map(Math.abs);
      const [w, h] = [b.w * c + b.h * s, b.w * s + b.h * c];
      return { x: b.x + (b.w - w) / 2, y: b.y + (b.h - h) / 2, w, h };
    });
    const low = pasted || !outer.length ? undefined : outer.reduce((a, b) => (b.y + b.h > a.y + a.h ? b : a));
    const under = !!low && low.y + low.h + 5 + h <= size[1] - MARGIN;
    const [x, y] =
      low && under
        ? [Math.max(0, Math.min(low.x, size[0] - MARGIN - w)), round(low.y + low.h + 5)]
        : [(size[0] - w) / 2, round(Math.max(0, seen(0, n))) + MARGIN];
    const z = Math.max(0, ...held.map((b) => b.z)) + 1;
    const [block] = land([{ id, x, y, w, h, z, locked: false, ...rest }], held, size);
    turn((p) => ({ ...p, blocks: [...p.blocks, block] }), undefined, n);
    setAt(n);
    setIds([id]);
    // A block under the view is brought into it, once it is drawn.
    requestAnimationFrame(() => document.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" }));
    // An empty text opens for typing; a pasted one comes with its words.
    if (rest.type === "text" && !rest.props.text) setEditing(id);
  }
  // A picture goes to the server first; the block holds its number and its shape, and starts within 100 mm.
  async function sent(file: File) {
    const body = new FormData();
    body.append("file", file);
    // What the server says counts before what the browser makes of the file: WebKit reads no file while it has no
    // connection, and the file is not the one to blame then.
    const drawn = createImageBitmap(file);
    drawn.catch(() => {});
    const { id } = await signed(api<{ id: number }>("/uploads", { method: "POST", body }));
    const { width, height } = await drawn;
    const w = round(Math.min(100, (100 * width) / height));
    return { w, h: round((w * height) / width), type: "image" as const, props: { upload: id, ratio: width / height, cut: [0, 0, 0, 0] } };
  }
  // With no connection or a fault of the server the picture can be sent again. Any other refusal is the file's own:
  // one the server does not take, or one the browser cannot read.
  const NO_PICTURE = "Das Bild konnte nicht hochgeladen werden.";
  const unfit = (s: string) => (s === "offline" || s.startsWith("5") ? undefined : "Das Bild ließ sich nicht hochladen. Es gehen JPEG, PNG, WebP und GIF bis 15 MB.");
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
  // A maths block starts with plus exercises up to 20; the server makes them.
  async function addMaths() {
    const limits = { ops: ["+" as const], max: 20, a: [[0, 9], [0, 9]] as Range[], b: [[0, 9], [0, 9]] as Range[], carry: "either" as const, rest: false, format: "row" as const, count: 12, seed: newSeed() };
    await attempt("Die Aufgaben konnten nicht erzeugt werden.", async () => {
      const where = mark();
      const props = { ...limits, ...(await generate(limits)), columns: 3, size: 14 };
      calm(() => add(180, mathsHeight(props), { type: "maths", props }, where()));
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
  // A mark of the copied words, apart from the blocks: a logout takes the blocks away, and the words still lie on
  // the system's clipboard, where the next account must not get them as a text. The mark gives no word away.
  const hash = (words: string) => String([...words].reduce((h, c) => (h * 33) ^ c.codePointAt(0)!, 5381) >>> 0);
  function copy(held = sel) {
    if (!held.length) return;
    // A linked Lineatur is drawn from the sheet's list, so the list goes along with it.
    const linkedAny = held.some(tied);
    localStorage.setItem("clip", JSON.stringify({ owner: user.id, blocks: held, ...(linkedAny && { words: live.current.doc.words }) }));
    const words = wordsOf(held);
    localStorage.setItem("copied", hash(words));
    pending.current = words;
    document.execCommand("copy");
    if (pending.current === null) return;
    pending.current = null;
    const landed = navigator.clipboard?.writeText(words);
    if (!landed) return;
    writing.current++;
    landed.catch(() => {}).finally(() => writing.current--);
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
    // A type this script does not know (a newer Blattomat's) is kept whole, as the sheet keeps it.
    const whole = (b?: Block) => b?.id && typeof b.type === "string" && b.props && [b.x, b.y, b.w, b.h, b.z].every(Number.isFinite);
    return held?.owner === user.id && Array.isArray(held.blocks) && held.blocks.every(whole) ? { blocks: held.blocks, words: held.words } : { blocks: [] };
  }
  function clip(): Block[] {
    return clipped().blocks;
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
  function typed(got: string) {
    const words = got.replace(/\r\n/g, "\n");
    const [copied, held] = [localStorage.getItem("copied"), clip()];
    // A copy of the build before left no mark: its words are those of the stored blocks.
    const own = copied === null ? held.length && words === wordsOf(held) : copied === hash(words);
    if (!words.trim() || own) return false;
    tight.current = true;
    // Word ends a whole line with a break, which would make an empty last paragraph.
    add(80, 12, { type: "text", props: { text: words.replace(/\n+$/, ""), size: 14, align: "left" } }, page, true);
    return true;
  }
  // A second press while the system's clipboard is still being read would paste onto the same spot.
  const reading = useRef(false);
  // The button has no paste of the browser's to go by, so it asks the system's clipboard itself: for a picture
  // first, then for words.
  async function pasteAny() {
    if (reading.current) return;
    if (writing.current) return paste();
    reading.current = true;
    let words = "";
    try {
      for (const item of await navigator.clipboard.read()) {
        const type = item.types.find((t) => t.startsWith("image/"));
        if (type) return upload(new File([await item.getType(type)], "bild", { type }), true);
        if (item.types.includes("text/plain")) words = await (await item.getType("text/plain")).text();
      }
    } catch {
      // No leave to read, or a browser that cannot: the copied blocks are still there.
    } finally {
      reading.current = false;
    }
    if (!typed(words)) paste();
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
    const boxes = things.map((t) => bounds(t.map(outline)));
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
    const row = things.map((t) => ({ t, box: bounds(t.map(outline)) })).sort((a, b) => a.box[axis] - b.box[axis]);
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
    // A finger that holds never rests still: nothing moves until it has left where it came down. Once a block has
    // moved, the blocks are new ones, and they follow the finger back there too. Of a group only the event of the
    // whole says where the finger is: those of its blocks say where a snap would put them.
    // Moveable says nothing more while a snap holds the blocks, so what is dropped here is kept for the finger's
    // own move to bring back once it has left.
    const still = touch.current && blocks.includes(start.current[0]) && Math.hypot(finger.clientX - came.current[0], finger.clientY - came.current[1]) <= SLOP;
    owed.current = still ? events : undefined;
    if (still) return;
    const from = events.map((e) => blocks.find((b) => b.id === idOf(e.target))!);
    const to = events.map((e, i) => ({ ...from[i], x: e.left / K, y: e.top / K }));
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
  };
  // With Ctrl held when a move ends, copies stay where the blocks began.
  const leave = (moved: boolean) => {
    owed.current = undefined;
    if (moved && mod & CENTRE) change((bs) => [...bs, ...cloned(start.current, bs)], "drag");
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
  // A turn follows the handle from the angles the blocks began with: `by` is how far it has gone. With Shift one
  // block stops at every 15 degrees. Several blocks turn as one about the middle of the box around them, in steps
  // of 15 degrees with Shift.
  const twist = (by: number, shift: boolean) => {
    const from = start.current;
    const stop = (a: number) => (shift || mod & KEEP ? Math.round(a / 15) * 15 : a);
    const first = from[0].angle ?? 0;
    const a = from.length > 1 ? stop(by) : stop(first + by) - first;
    flushSync(() => place(swung(from, a).map(({ id, x, y, angle }) => [id, { x, y, angle }]), "drag"));
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
  const spin = (by: number) => each((t) => swung(t, by));
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
    if (after !== undefined) setSlot(after);
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
    e.currentTarget.setPointerCapture(e.pointerId);
    ahead.current = hist.future;
    grasp.current = { el: e.currentTarget, id: e.pointerId, draft };
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
  // Resizes a group from the boxes it began with. The corner opposite the dragged one stays, or with Ctrl the middle,
  // and the group keeps its shape, as Moveable's groups do, so every line keeps its angle. A group can shrink to a
  // tenth, not flip.
  function scale(e: PointerEvent, right: boolean, low: boolean) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const { x, y, w, h } = bounds(start.current);
    const [px, py] = point(e);
    const half = mod & CENTRE ? 2 : 1;
    const [fx, fy] = half > 1 ? [x + w / 2, y + h / 2] : [right ? x : x + w, low ? y : y + h];
    const [sw, sh] = [(right ? w : -w) / half, (low ? h : -h) / half];
    let s = Math.max(0.1, w && (px - fx) / sw, h && (py - fy) / sh);
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
  // Let go off the page, a guide line is gone.
  function drop(axis: Axis, i: number, n?: number) {
    const at = (n === undefined ? guides : pages[n].guides!)[axis][i];
    if (at >= 0 && at <= (axis === "x" ? W : H)) return;
    rules(n, (g) => ({ ...g, [axis]: g[axis].filter((_, j) => j !== i) }), "drag");
  }

  // The PDF is made of what the server holds, so a change still waiting is saved first: after a save under way,
  // which may hold an older document. A save that fails or never answers holds the PDF up for 20 s at most.
  // The session is asked for first: where it is gone the login shows, and nothing goes to the PDF's address. The
  // PDF is fetched, so a failure leaves the sheet where it is, and goes to the browser as a download under the name
  // the server gives it. With no limit of time: a long sheet takes long to print.
  async function pdf(key: boolean) {
    // A sheet deleted elsewhere: another try ends the same, so the line names the choice and has no button.
    const deleted = "Das PDF konnte nicht erstellt werden. Dieses Blatt wurde auf einem anderen Gerät gelöscht. Wähle „Als neues Blatt behalten“, dann gibt es wieder ein PDF.";
    await attempt("Das PDF konnte nicht erstellt werden.", async () => {
      await flush(file.id);
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
    }, (s) => (s === "404" && isGone(file.id) ? deleted : undefined));
  }

  // The print variants: the dialog's choice lives here, so it stays while the editor is open.
  const [variants, setVariants] = useState(false);
  const [count, setCount] = useState(2);
  const [letters, setLetters] = useState(true);
  // The button that opened the dialog gets the focus back when it shuts.
  const variantsDoor = useRef<HTMLElement | null>(null);
  const openVariants = (door: HTMLElement) => {
    variantsDoor.current = door;
    setVariants(true);
  };

  // A template stored or deleted with the session run out brings the login. A second press while one is on its way
  // stores no second template. The name stays until the template is stored.
  const storing = useRef(false);
  async function store() {
    const made = { name: name.trim() };
    await attempt("Die Vorlage konnte nicht gespeichert werden.", async () => {
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
    });
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
    if (el.closest(".end, .rule, .crop, .bar")) return;
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
        setEditing("");
        daub(on, to);
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
        edit(id, el);
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
  function edit(id?: string, el?: Element, all = false) {
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
        escaped.current = false;
      }
      setEditing(id);
    }
    setSlot(+(el?.closest<HTMLElement>("[data-cell]")?.dataset.cell ?? 0));
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
    if (!(id || over) || id === editing) return;
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
    if (e.touches.length === 1) steer(1500);
    // A second finger ends the hold at once, and so does one finger that has moved away.
    const { clientX: x0, clientY: y0 } = e.touches[0];
    if (e.touches.length > 1 || Math.hypot(x0 - came.current[0], y0 - came.current[1]) > SLOP) clearTimeout(hold.current);
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
    const over = moveable.current!.isMoveableElement(el) || !!el.closest(".end, .bar, .crop");
    const id = (over ? document.elementsFromPoint(x, y).find((o) => o.matches(".block")) : el.closest(".block"))?.getAttribute("data-id");
    const to = pageOf(el);
    // A block of the selection keeps it whole. Another one is picked with its group, and the empty page picks nothing.
    if (to !== page || (id ? !ids.includes(id) : !over)) {
      done();
      setAt(to);
      setIds(id ? grouped([id], pages[to].blocks) : []);
    }
    setMenu({ x, y });
    return true;
  }
  function thumbMenu(n: number, x: number, y: number) {
    // The menu hands the focus back when it closes: to a field, that would keep the sheet's keys.
    (document.activeElement as HTMLElement | null)?.blur();
    visit(n);
    setMenu({ x, y, thumb: n });
  }
  const none = !sel.length;
  const ctrl = APPLE ? "⌘" : "Strg+";
  const shift = APPLE ? "⇧" : "Umschalt+";
  const thumbed = menu?.thumb;
  const ruled = menu?.rule;
  type Command = Exclude<Item, "sep">;
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
  const items: Item[] =
    ruled
      ? // Only the one line goes, as one undo step: no merge key, so no other change joins it.
        [{ label: "Hilfslinie entfernen", icon: Eraser, run: () => rules(ruled.n, (g) => ({ ...g, [ruled.axis]: g[ruled.axis].filter((_, j) => j !== ruled.i) })) }]
      : thumbed !== undefined
      ? [
          { label: "Neue Seite", icon: FilePlus, run: () => addPage(thumbed) },
          { label: "Seite duplizieren", icon: CopyPlus, run: () => copyPage(thumbed) },
          { label: "Seite löschen", icon: FileX, disabled: pages.length < 2, run: () => removePage(thumbed) },
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
    const el = desk.current!;
    fitted.current = true;
    // 120 is the desk's padding above and below. The whole box, not clientHeight: that leaves out the bar along the
    // bottom, which goes once the page fits, and the desk has no border to take off.
    flushSync(() => setZoom(Math.min(4, Math.max(0.25, Math.min(room / W, (el.offsetHeight - 120) / H) / fit))));
    const [page, box] = [sheet.current!.getBoundingClientRect(), el.getBoundingClientRect()];
    // The page lies in the middle, across, also beside a wider one, and its top under the desk's padding.
    el.scrollBy(page.left + page.width / 2 - box.left - el.clientWidth / 2, page.top - box.top - 32);
  }
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
    { label: "Zahlenmauer", icon: BrickWall, run: () => add(180, 60, { type: "zahlenmauer", props: { base: 3, count: 4, columns: 2, max: 20, op: "+", given: "base", empty: false, seed: newSeed() } }) },
    { label: "Rechendreieck", icon: TriangleDashed, run: () => add(180, 50, { type: "rechendreieck", props: { ...DREIECK, seed: newSeed() } }) },
    { label: "Zahlenstrahl", icon: MoveRight, run: () => add(180, 30, { type: "zahlenstrahl", props: { ...STRAHL, seed: newSeed() } }) },
    { label: "Hunderterfeld", icon: Grid3x3, run: () => add(100, 100, { type: "hunderterfeld", props: { ...FELD, seed: newSeed() } }) },
    { label: "Uhr", icon: Clock3, run: () => add(180, 58.5, { type: "uhr", props: { ...UHR, seed: newSeed() } }) },
    { label: "Selbstkontrolle", icon: ListChecks, run: () => add(180, 30, { type: "selbstkontrolle", props: { ...SELBST, seed: newSeed() } }) },
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
      <Tool icon={Type} label="Text" data-tour="text" onClick={() => add(80, 12, { type: "text", props: { text: "", size: 14, align: "left" } })} />
      <Tool icon={Heading} label="Überschrift" onClick={() => add(180, 14, { type: "text", props: { text: "", size: 24, align: "center", bold: true } })} />
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
      <Tool icon={Smile} label="Symbol" onClick={() => add(20, 20, { type: "symbol", props: { code: "270F" } })} />
      <Tool icon={Table} label="Tabelle" onClick={() => add(180, 30, { type: "table", props: { cells: Array.from({ length: 3 }, () => ["", "", ""]), cols: [1, 1, 1], size: 14, align: "center", line: "#222222" } })} />
      <i className="sep" data-name="Schule" />
      <Tool icon={Rows3} label="Lineatur" onClick={() => add(180, 60, { type: "ruling", props: { kind: "l1", color: "#555555" } })} />
      <Tool icon={UserPen} label="Namenszeile" onClick={() => add(180, 10, { type: "name", props: {} })} />
      <Tool icon={SquareSlash} label="Punkte" onClick={() => add(40, 12, { type: "points", props: { max: 10 } })} />
      <Tool icon={Grid3x3} label="Suchsel" onClick={() => add(120, 140, { type: "suchsel", props: { words: [], cols: 10, rows: 10, ways: "down", caps: true, umlauts: true, show: "words", seed: newSeed() } })} />
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
      <Tool icon={Ruler} label="Strecke" onClick={() => add(50, 0, { type: "shape", props: { kind: "line", fill: "none", stroke: "#222222", strokeWidth: 0.5, ticks: true } })} />
      <i className="sep" data-name="Formen" />
      <span className="shapes">
        {SHAPES.map(([kind, label, icon]) => (
          <Tool
            key={kind}
            icon={icon}
            label={label}
            onClick={() =>
              add(WIDTHS[kind] ?? 60, FRAMES.some(([frame]) => frame === kind) ? 40 : 0, {
                type: "shape",
                props: { kind, fill: "none", stroke: "#222222", strokeWidth: 0.5 },
              })
            }
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
      className={`editor${leaf ? " leaf" : ""}${brush ? " brush" : ""}${pan ? " pan" : ""}${panning ? " panning" : ""}`}
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
            <Variants id={file.id} doc={hist.doc} count={count} setCount={setCount} letters={letters} setLetters={setLetters} opener={variantsDoor} onClose={() => setVariants(false)} />
          )}
        </div>
        {saver?.clash && (
          <div className="clash" role="alert">
            Dieses Blatt wurde auf einem anderen Gerät geändert.
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
            {saver.choice && <span>{saver.choice === "busy" ? "Lädt …" : "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."}</span>}
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
            <Tool icon={CopyPlus} label="Seite duplizieren" onClick={() => copyPage()} />
            <Tool icon={FileX} label="Seite löschen" disabled={pages.length < 2} onClick={() => removePage()} />
          </div>
        </aside>
      )}
      {left && (
        <aside className="left">
          {leaf && brand}
          <div className="head">
            Seiten
            <span>
              <Tool icon={CopyPlus} label="Seite duplizieren" title="Seite duplizieren" onClick={() => copyPage()} />
              <Tool icon={FileX} label="Seite löschen" title="Seite löschen" disabled={pages.length < 2} onClick={() => removePage()} />
            </span>
          </div>
          {/* As many thumbnails in a row as fit, 12 px apart, in the 206 px that two take at first. */}
          <div className="pages" ref={strip} style={{ "--thumb": `${thumb}px`, "--across": Math.floor(218 / (Math.round(thumb) + 12)) } as CSSProperties}>
            {pages.map((_, n) => (
              <button
                key={n}
                data-thumb={n}
                title="Ziehen verschiebt die Seite"
                className={[n === page && "on", n === haul?.from && "drag"].filter(Boolean).join(" ")}
                aria-pressed={n === page}
                // The click after a drag is the drag's end, not a visit. The next one, also by Enter, visits again.
                onClick={(e) => {
                  if (!dragged.current) {
                    visit(n);
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

      <div className="stage" ref={stage}>
        <div
          className="desk"
          ref={desk}
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
            cover.current = moveable.current!.isMoveableElement(e.target as Element);
            // The hold before is over with the next press, not with its own lift: Moveable hears of that lift later.
            held.current = false;
            // A press of the mouse on a cell of the table being edited picks cells. Moveable takes the focus from the
            // field before the mouse's own event: the field stays open through that.
            cellDrag.current = !touch.current && !!table && editing === table.id && !!(e.target as Element).closest(`[data-id="${table.id}"] [data-cell]`);
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
          onDoubleClick={(e) => brush || edit((e.target as Element).closest<HTMLElement>(".block")?.dataset.id, e.target as Element)}
          // A held finger gets no menu, and a mouse the editor's own, unless a field keeps the browser's.
          onContextMenu={(e) => (touch.current || menuAt(e.target as Element, e.clientX, e.clientY)) && e.preventDefault()}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={(e) => {
            clearTimeout(hold.current);
            // Lifting the finger after a hold is not a tap.
            if (held.current) e.preventDefault();
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
              <div className="scaled" style={{ width: sizes[n][0] * K, height: sizes[n][1] * K, transform: `scale(${k / K})`, "--px": `${K / k}px` } as CSSProperties}>
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
                              if (e.key === "Escape") {
                                escaped.current = true;
                                setEditing("");
                              }
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
                    {b.type === "text" && stepOf(b.props.lines) > 0 && <Numbers block={b} />}
                    <Mark block={b} k={K} n={ns.get(b.id)} />
                  </div>
                ))}
              </div>
              {/* The sheet's guide lines lie on every page; a page's own are drawn dotted. */}
              {[undefined, n].flatMap((at) =>
                (["x", "y"] as const).flatMap((axis) =>
                  (at === undefined ? guides : (p.guides ?? NONE))[axis].map((mm, i) => (at === undefined && mm > sizes[n][axis === "x" ? 0 : 1]) || (
                    <i key={`${at}${axis}${i}`} className={`rule ${axis}${at === undefined ? "" : " own"}`} style={axis === "x" ? { left: mm * k } : { top: mm * k }}>
                      <b
                        data-axis={axis}
                        data-i={i}
                        data-page={at}
                        // The right button drags nothing: its menu removes this one line, and picks no block.
                        onPointerDown={(e) => e.button === 0 && grip(e)}
                        onPointerMove={(e) => slide(e, axis, i, at)}
                        onLostPointerCapture={() => drop(axis, i, at)}
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
                  {group &&
                    [0, 1, 2, 3].map((i) => (
                      <i
                        key={i}
                        className="end"
                        // On the frame's corners, which stand outside the group's.
                        style={{ left: (group.x + (i % 2) * group.w) * k + (i % 2 ? FRAME.right : -FRAME.left), top: (group.y + (i >> 1) * group.h) * k + (i >> 1 ? FRAME.bottom : -FRAME.top) }}
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
                    ))}
                  <Moveable
                    ref={moveable}
                    // In crop mode the frame's handles stand in for Moveable's.
                    target={cropping ? [] : targets}
                    draggable={free.length === sel.length}
                    resizable={free.length === sel.length && !sel.some(isLine)}
                    renderDirections={handles}
                    // A lone line keeps its own handles at its ends, and has no frame.
                    padding={sel.length === 1 && isLine(sel[0]) ? undefined : FRAME}
                    // Each loose block has its own outline from Moveable, which the padding does not reach. Blocks of one
                    // group keep only the frame about them all, so the outlines do not cut their letters.
                    hideChildMoveableDefaultLines={oneGroup}
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
                    onClickGroup={(e) => cover.current && !held.current && pick(e.inputTarget, e.inputEvent.shiftKey)}
                    // A press on a cell of the table being edited picks cells: it moves no block.
                    onDragStart={(e) => (cellDrag.current ? e.stopDrag() : begin([e.target]))}
                    onDragGroupStart={(e) => begin(e.targets)}
                    onDrag={(e) => drag([e])}
                    onDragGroup={(e) => drag(e.events, e)}
                    onDragEnd={(e) => leave(e.isDrag)}
                    onDragGroupEnd={(e) => leave(e.isDrag)}
                    // Ctrl resizes about the centre.
                    onBeforeResize={(e) => mod & CENTRE && e.setFixedDirection([0, 0])}
                    onBeforeResizeGroup={(e) => mod & CENTRE && e.setFixedDirection([0, 0])}
                    onResizeStart={(e) => begin([e.target])}
                    onResizeGroupStart={(e) => begin(e.targets)}
                    // A table stays level, and a line turns by its ends.
                    rotatable={!cropping && free.length === sel.length && !sel.some((b) => b.type === "table") && !sel.some(isLine)}
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
                    // Moveable measures the box around the blocks anew: turned with them where they share an angle, else level.
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
              desk.current!.scrollLeft = hand.current[2] - (e.clientX - hand.current[0]);
              desk.current!.scrollTop = hand.current[3] - (e.clientY - hand.current[1]);
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
          if (e.inputEvent.type === "touchstart" || el.closest(".block, .end, .rule, .bar, .crop") || moveable.current!.isMoveableElement(el)) e.stop();
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
                {sel.length > 1 ? `${sel.length} Felder` : (NAMES[sel[0].type] ?? "Unbekannter Block")}
              </p>
              <Format
                // A block of a group with a locked one is as fixed there as the locked one.
                sel={sel.map((b) => (free.includes(b) ? b : { ...b, locked: true }))}
                style={style}
                bump={bump}
                look={look}
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
              {boxes.length > 0 && (
                <>
                  <h2>Füllung und Rand</h2>
                  {/* A line stays a line. */}
                  {!rulers.length && (
                    <div className="seg">
                      {FRAMES.map(([kind, label]) => (
                        <button key={kind} className={(boxes[0].props.kind ?? "rect") === kind ? "on" : ""} onClick={() => look({ kind })}>
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
                  <label>
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
                  </label>
                  {/* The next fill is solid again, as in PowerPoint. */}
                  <button className="wide" disabled={fill === "none"} onClick={() => look({ fill: "none", opacity: undefined })}>Keine Füllung</button>
                  <label>
                    Rand
                    <input type="color" value={stroke === "none" ? "#222222" : stroke} onChange={(e) => look({ stroke: e.target.value }, "stroke")} />
                  </label>
                  {!rulers.length && <button className="wide" disabled={stroke === "none"} onClick={() => look({ stroke: "none" })}>Kein Rand</button>}
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
                onClick={() => add(W - 2 * MARGIN, Math.max(1, Math.min(learnt.length, Math.floor((H - 2 * MARGIN) / RULINGS.l3.row))) * RULINGS.l3.row, { type: "ruling", props: { kind: "l3", color: "#222222", list: "fold", folds: 2 } })}
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
