import {
  memo,
  useDeferredValue,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type KeyboardEvent as Key,
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
  Calculator,
  ChevronLeft,
  Circle,
  CircleHelp,
  ClipboardPaste,
  Copy,
  CopyPlus,
  Ellipsis,
  Eraser,
  Eye,
  Group,
  FileCheck,
  FileDown,
  FilePlus,
  FileX,
  Fullscreen,
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
import { Link, useParams } from "react-router";
import { api, post, type User } from "../api";
import { DRAWERS, opening } from "../components/Blank";
import Feedback from "../components/Feedback";
import Logo from "../components/Logo";
import Menu, { type Item } from "../components/Menu";
import Tour from "../components/Tour";
import { changed, fresh, redone, returned, undone, type Hist, type Step } from "../history";
import type { EditorView } from "prosemirror-view";
import { Draw, K, MARGIN, Mark, PT, Paper, RULINGS, boxed, cleared, dir, far, isLine, last, listed, mathsHeight, numbers, parasOf, read, sizeOf, spliced, sum, tall, turned, writtenStyle, type Axis, type Block, type Box, type Corner, type Doc, type Guides, type ImageBlock, type Kind, type List, type Page, type Range, type Sheet, type ShapeBlock, type TableBlock, type TextProps } from "../sheet";
import Field, { list, tint, type Marks, type Picked } from "./Field";
import Format, { bounds, drawn, has, mirrored, norm, outline, swung } from "./Format";
import { generate, newSeed } from "./Maths";

type Template = { id: number; name: string; doc: Doc };
// A new block's type and settings; `add` gives it its place.
type Fresh<B = Block> = B extends Block ? Pick<B, "type" | "props"> : never;

const SIDES = { top: true, left: true, bottom: true, right: true, center: true, middle: true };
const CORNERS = ["nw", "ne", "sw", "se"];
// The look the brush carries from a text or a shape to the next. A line gives and takes its stroke alone, a table
// what its cells have and the colour of its lines, `rule`, a Lineatur its script, the colour of its lines, `rule`
// too, and its Nachspuren, `trace`, and a maths block its size and the numbering of its exercises. Every block
// gives and takes the numbering before it, `mark`.
const LOOK = ["font", "size", "bold", "italic", "underline", "color", "spacing", "align", "valign", "fill", "opacity", "stroke", "strokeWidth", "dash"] as const;
type Coat = Partial<TextProps> & { mark?: string; rule?: string; trace?: boolean; numbering?: string };
// Karo is always in print, and a written exercise is as large as its squares: they have no script and no size.
const takes = (b: Block): readonly (keyof Coat)[] => {
  const school: (keyof Coat)[] = b.type === "ruling" ? (RULINGS[b.props.kind].at ? ["font", "rule", "trace"] : ["rule", "trace"]) : b.type === "maths" ? (b.props.format === "written" ? ["numbering"] : ["size", "numbering"]) : [];
  return [...(isLine(b) ? (["stroke", "strokeWidth", "dash"] as const) : b.type === "table" ? (["font", "size", "color", "align", "rule"] as const) : (boxed(b) && LOOK) || school), "mark"];
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
  name: "Namenszeile",
  points: "Punkte",
  maths: "Rechnen",
  shape: "Form",
  table: "Tabelle",
};
// The right panel's tabs.
const TABS = ["Format", "Ansicht"];
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
const cloned = (from: Block[], all: Block[]) => {
  const fresh = new Map<string, string>();
  const whole = (g: string) => all.every((b) => !b.group?.includes(g) || from.some((f) => f.id === b.id));
  return from.map((b) => {
    const group = b.group?.filter(whole).map((g) => fresh.get(g) ?? fresh.set(g, crypto.randomUUID()).get(g)!);
    return { ...b, id: crypto.randomUUID(), group: group?.length ? group : undefined };
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
// asked for it meanwhile, or null where it is not there.
export default function Editor({ user, wait, first }: { user: User; wait: ReactNode; first: Promise<Sheet | null> }) {
  const { id } = useParams();
  // undefined while the sheet is loading, null when it is not there.
  const [file, setFile] = useState<Sheet | null>();

  function load() {
    api<Sheet>(`/sheets/${id}`).then(setFile, () => setFile(null));
  }
  useEffect(() => void first.then(setFile), [first]);

  if (file === undefined) return wait;
  if (!file) return <main><h1>Blatt nicht gefunden</h1></main>;
  // A version loaded anew starts the editor over.
  return <Canvas key={`${file.id}.${file.version}`} file={file} user={user} reload={load} />;
}

function Canvas({ file, user, reload }: { file: Sheet; user: User; reload: () => void }) {
  const [hist, draw] = useState<Hist>(() => ({ past: [], doc: read(file.doc), future: [] }));
  // The same as it stands after every change so far, drawn or not: a change knows at once what the one before left.
  const live = useRef(hist);
  const setHist = (step: (h: typeof hist) => typeof hist) => draw((live.current = step(live.current)));
  const [title, setTitle] = useState(file.title);
  // What the server holds, and how often a save has failed since.
  const [stored, setStored] = useState({ doc: hist.doc, title });
  const [tries, setTries] = useState(0);
  // Set when the server holds a newer document than the one this editor began with.
  const [clash, setClash] = useState(false);
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
  // Where the caret stood in a cell that a new row or column moves to another place.
  const caret = useRef<number>(undefined);
  // Whether the field that opens next has all its text picked.
  const entire = useRef(false);
  // The field of the text being edited, and what is picked in it.
  const field = useRef<EditorView>(null);
  const [part, setPart] = useState<Picked>();
  // Whether the last press was in the format panel, with no key since: the field then stays open though it loses
  // the focus, and a select or a colour picked there hands the keys back.
  const inPanel = useRef(false);
  // What is written in stays open when it loses the focus to the panel: by the keys, or by a press, which on the
  // word beside a colour names nothing that takes the focus. So does it under the bar's menu "Mehr", which hands
  // the focus back when it shuts.
  const stays = (e: { relatedTarget: EventTarget | null }) => inPanel.current || !!(e.relatedTarget as Element | null)?.closest(menu?.more ? ".panel, .menu" : ".panel");
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
  const [menu, setMenu] = useState<{ x: number; y: number; thumb?: number; more?: boolean }>();
  const [tab, setTab] = useState(TABS[0]);
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
  const refit = () => {
    late.current = !!document.querySelector("dialog.menu[open]");
    if (late.current) return;
    focused.current ||= !!document.activeElement?.matches(".more");
    setFits(undefined);
  };
  useLayoutEffect(() => {
    if (fits !== undefined) {
      if (focused.current) bar.current!.querySelector<HTMLElement>(".more")?.focus();
      focused.current = false;
      return;
    }
    const row = bar.current!;
    const look = getComputedStyle(row);
    const may = [...row.querySelectorAll(".sep ~ :is(.ib, .zoom):not(.pin)")];
    const widths = may.map((el) => el.getBoundingClientRect().width + parseFloat(look.columnGap));
    // How far the row runs past the bar's end, and how much of the hint it has squeezed away before that.
    const hint = row.querySelector(".hint")!;
    let over = row.querySelector(".pdf")!.getBoundingClientRect().right + parseFloat(look.paddingRight) - row.getBoundingClientRect().right + hint.scrollWidth - hint.clientWidth;
    // The title gives way first, so the row may end in the bar with the title cut: what it lacks counts too, up to
    // the most a title may take. While it is edited that is all of it, and `none` is no number.
    const name = row.querySelector("input")!;
    over += Math.min(name.scrollWidth - name.clientWidth, (parseFloat(getComputedStyle(name).maxWidth) || Infinity) - name.offsetWidth);
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
  // The bar is measured anew when its width changes, as the window's does or the iPad turns, when its type has
  // loaded, and when Blattform's layout, which has the zoom elsewhere, comes or goes. A turn has shut an open "Mehr"
  // by then, as the window's new size shuts any menu; a type that loads under an open menu has not. So it is when
  // the title changes, and when its field gains or loses the focus: the bar's width stays, and tells of none.
  useLayoutEffect(refit, [leaf, title]);
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
  const [zoom, setZoom] = useState(1);
  // A thumbnail's width in px.
  const [thumb, setThumb] = useState(97);
  // Space held makes the pointer a hand, and a drag with it moves the desk. The drag may outlast the key.
  const [pan, setPan] = useState(false);
  const [panning, setPanning] = useState(false);
  // Where the hand's drag began: the pointer, and the desk's scroll.
  const hand = useRef([0, 0, 0, 0]);
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
  // Set by a drag, for the click that follows it.
  const dragged = useRef(false);
  const grab = useRef([0, 0]);
  const spot = useRef<number[]>(undefined);
  const start = useRef<Block[]>([]);
  const pinch = useRef({ spread: 1, zoom: 1, x: 0, y: 0 });
  const save = useRef((_keepalive: boolean) => {});
  // The version the document here is based on.
  const version = useRef(file.version);
  const busy = useRef(false);

  const { pages, guides, grid } = hist.doc;
  // One page is in use: it holds the selection, and new and pasted blocks land on it. Undo can take it away.
  const page = Math.min(at, pages.length - 1);
  const { blocks } = pages[page];
  // Each page's width and height in mm.
  const sizes = pages.map((_, n) => sizeOf(hist.doc, n));
  const [W, H] = sizes[page];
  // Pixels per mm when the widest page fills the desk's width.
  const fit = room / Math.max(...sizes.map(([w]) => w));
  // The thumbnails draw after the desk, so a drag stays quick.
  const small = useDeferredValue(hist.doc);
  const cellOf = (p: Page) => p.grid ?? grid;
  const cell = cellOf(pages[page]);
  const mine = pages[page].guides ?? NONE;
  const dirty = hist.doc !== stored.doc || title !== stored.title;
  const loose = (mod & LOOSE) > 0;
  const k = fit * zoom;
  const sel = blocks.filter((b) => ids.includes(b.id));
  // What may be deleted, cut, moved, sized, turned and written in, as in PowerPoint: no locked block, and no block of
  // a group with a locked one, picked whole or in part. Such a group stays as a whole, so it keeps its shape.
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
  // A picture and a symbol always keep their shape, so only their corners have handles.
  const shaped = sel.some((b) => b.type === "image" || b.type === "symbol");
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
    const observer = new ResizeObserver(([entry]) => setRoom(entry.contentRect.width));
    observer.observe(desk.current!);
    return () => observer.disconnect();
  }, []);
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
    const grown = new Map<string, Partial<Box>>();
    for (const b of sel) {
      // A table's rows are each as high as their highest cell when its height is not set.
      const frame = sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] > :is(.frame, .table)`);
      if (!frame) continue;
      // A turned frame would measure as high as its outline, so the block lies level for the moment.
      const block = frame.parentElement!;
      const was = block.style.transform;
      block.style.transform = "none";
      frame.style.height = "auto";
      const h = Math.ceil((frame.getBoundingClientRect().height / k) * 100) / 100;
      frame.style.height = "";
      block.style.transform = was;
      if (h <= b.h) continue;
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
    const grow = (p: Page) => ({ ...p, blocks: p.blocks.map((b) => (grown.has(b.id) ? { ...b, ...grown.get(b.id) } : b)) });
    setHist((h) => ({ ...h, doc: { ...h.doc, pages: h.doc.pages.map((p, i) => (i === page ? grow(p) : p)) } }));
  });

  // A ruling's field, or that of a table's cell; a text's own field takes the focus by itself.
  useLayoutEffect(() => {
    const area = editing ? sheet.current!.querySelector<HTMLTextAreaElement>(`[data-id="${editing}"] textarea`) : null;
    area?.focus();
    // A copy, or a text put back by undo, would start with the caret before the text.
    const end = caret.current ?? area?.value.length ?? 0;
    area?.setSelectionRange(entire.current ? 0 : end, end);
    caret.current = undefined;
    entire.current = false;
  }, [editing, slot]);
  // A field the panel took the focus from has no blur left to end it: it ends once its block is no longer picked.
  // So does the field of a cell that undo took away with its row.
  useEffect(() => {
    if (editing && (!sel.some((b) => b.id === editing) || (table && slot >= table.props.cells.flat().length))) setEditing("");
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
    upload(picture);
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
    // In a text's field, in a table's cell, in the panel's fields for place and size, on its sliders and on its lists
    // only undo and redo are the sheet's.
    const ours = (e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key) && target.closest(".ProseMirror, .table, input.mm, input[type=range], select");
    if (!ours && !shut && target.closest(".ProseMirror, textarea, input, select")) return;
    // Space is the hand's key and does not scroll the desk, also while it repeats. A focused button keeps it as its own.
    if (e.code === "Space" && !e.ctrlKey && !e.metaKey && !e.altKey) {
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
    // Ctrl+V alone is not here: a key stopped on its way down brings no paste.
    const keys: Record<string, (() => void) | false | undefined> =
      e.ctrlKey || e.metaKey
        ? { z: e.shiftKey ? redo : undo, y: redo, x: cut, c: e.shiftKey ? () => dip() : copy, v: e.shiftKey && (() => daub(ids)), d: () => put(sel), a: all, g: e.shiftKey ? split : join, b: flip("bold"), i: flip("italic"), u: flip("underline") }
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
    const run = keys[e.key.toLowerCase()];
    // With nothing to move the arrows scroll the desk, and Alt with an arrow stays the browser's way back.
    if (!run || (e.key.startsWith("Arrow") && (!free.length || cropping || e.altKey))) return;
    e.preventDefault();
    run();
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      setMod((e.shiftKey ? KEEP : 0) | ((APPLE ? e.altKey : e.ctrlKey) ? CENTRE : 0) | ((APPLE ? e.metaKey : e.altKey) ? LOOSE : 0));
      // Letting Space go puts the hand down. A drag that is on goes on until the pointer lifts.
      if (e.type === "keyup" && e.code === "Space") setPan(false);
    };
    const onBlur = () => {
      setMod(0);
      setPan(false);
      setPanning(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("keyup", onKey);
    window.addEventListener("blur", onBlur);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("keyup", onKey);
      window.removeEventListener("blur", onBlur);
    };
  }, []);

  useEffect(() => {
    api<Template[]>("/templates").then(setTemplates, () => {});
  }, []);

  // A change is saved two seconds after the last one, one save at a time, and a save that failed is tried again.
  // The server turns down a document based on an older version than it holds: then saving stops until the teacher
  // has chosen. The title goes along only when it changed here, so a rename from the list stays.
  save.current = (keepalive) => {
    if (!dirty || clash || busy.current) return;
    busy.current = true;
    const now = { doc: hist.doc, title };
    const named = title === stored.title ? {} : { title: title.trim() || "Unbenanntes Blatt" };
    last.save = post<Sheet>(`/sheets/${file.id}`, { doc: now.doc, version: version.current, ...named }, { method: "PATCH", keepalive })
      .then(
        (saved) => {
          version.current = saved.version;
          setStored(now);
          setTries(0);
        },
        (e: Error) => (e.message === "409" ? setClash(true) : setTries((n) => n + 1)),
      )
      .finally(() => (busy.current = false));
  };
  useEffect(() => {
    const timer = setTimeout(() => save.current(false), 2000);
    return () => clearTimeout(timer);
  }, [hist.doc, title, tries, stored, clash]);
  // Leaving the editor or the app saves at once; `keepalive` lets the request outlive the window.
  useEffect(() => {
    const leave = () => save.current(true);
    window.addEventListener("pagehide", leave);
    return () => {
      window.removeEventListener("pagehide", leave);
      leave();
    };
  }, []);

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
        if (on.closest(".hand")) desk.current!.scrollBy(e.deltaX, e.deltaY);
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
      flushSync(() => setZoom(next));
      // Scroll the page point that was under the pointer back under it.
      page = under.getBoundingClientRect();
      // Whole px: Safari cuts a fraction off, always the same way, and the page creeps with each step.
      desk.current!.scrollBy(Math.round(page.left + x * fit * next - e.clientX), Math.round(page.top + y * fit * next - e.clientY));
    }
    window.addEventListener("wheel", onWheel, { passive: false });
    return () => window.removeEventListener("wheel", onWheel);
  });
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
    const next = changed(live.current, { key: mergeKey.current, ahead: ahead.current }, fn(live.current.doc), key, from, to);
    if (!next) {
      // A gesture under way goes on, and what it has changed is measured where its end asks for that, as a resize's.
      if (key !== "" && key === mergeKey.current) return void (tight.current && setHist((h) => ({ ...h })));
      // Any other gesture is over: the next change is a step of its own. No text has grown, so nothing is measured,
      // unless a change still waits to be drawn.
      mergeKey.current = "";
      if (live.current.doc === latest.current.doc) tight.current = false;
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
  // Changes the sheet's guide lines, or with `n` those of that page alone.
  function rules(n: number | undefined, fn: (g: Guides) => Guides, key?: string) {
    if (n === undefined) update((doc) => ({ ...doc, guides: fn(doc.guides) }), key);
    else turn((p) => ({ ...p, guides: fn(p.guides ?? NONE) }), key, n);
  }
  function place(boxes: [string, Partial<Box>][], key?: string) {
    const byId = new Map(boxes);
    change((bs) => bs.map((b) => ({ ...b, ...byId.get(b.id) })), key);
  }
  function style(type: Block["type"], props: object, key?: string) {
    if (type === "table") tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === type ? ({ ...b, props: { ...b.props, ...fresh(b, props) } } as Block) : b)), key);
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
          const on = edge && (b.props.stroke ?? "none") === "none" && { stroke: "#222222" };
          return { ...b, props: { ...b.props, ...fresh(b, props), ...on } } as Block;
        }),
      key,
    );
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
    // A field says "not bold" where a block says nothing: both are the same look.
    setCoat(Object.fromEntries(takes(source).map((name) => [name, from[name] === false ? undefined : from[name]])));
  }
  // Lays the look on blocks of page `n`. Each takes what it has, and its words lose what they had of their own
  // there. All of it is one undo step, and none where nothing changes.
  function daub(on: string[], n = page) {
    if (!coat) return;
    const dab = (b: Block) => {
      if (!on.includes(b.id)) return b;
      // A line never vanishes: it takes a border only from a block that has one.
      // Nor do a table's or a Lineatur's lines: a table made outside the editor may name no colour for its own.
      const own = takes(b).filter((name) => name in coat && name !== "mark" && !(isLine(b) && (coat.stroke ?? "none") === "none") && !(name === "rule" && !coat.rule));
      // The colour of a Lineatur's lines is its `color`, that of a table's lines its `line`.
      const props = Object.fromEntries(own.map((name) => [name === "rule" ? (b.type === "table" ? "line" : "color") : name, coat[name] ?? (b.type === "shape" ? BARE[name] : undefined)]));
      const rich = own.length ? boxed(b)?.rich : undefined;
      // What is left unset goes, so a saved sheet opens as it looks here.
      const all = Object.entries({ ...b.props, ...(rich && cleared(rich, props)), ...props }).filter(([, value]) => value !== undefined);
      const next = { ...b, mark: coat.mark, props: Object.fromEntries(all) } as Block;
      if (!next.mark) delete next.mark;
      // A maths block is as high as its exercises need, as from the panel.
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
    if (last) show(last.from, (h) => undone(h, last));
  }
  function redo() {
    const next = hist.future[0];
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
    flushSync(() => {
      setAt(n);
      setIds([]);
    });
    sheet.current!.scrollIntoView({ behavior: "smooth" });
  }
  // Lays the sheet on its side or upright, or with `n` that page alone: `undefined` gives it the sheet's format
  // again. Set for the sheet, every page follows. Blocks the page no longer holds move back onto it.
  function lay(landscape: boolean | undefined, n?: number) {
    update((doc) => {
      // A sheet that says nothing stands upright: "Hoch" leaves it so.
      const next = { ...doc, ...(n === undefined && landscape !== !!doc.landscape && { landscape }), pages: doc.pages.map((p, i) => (n === undefined || i === n ? { ...p, landscape: n === undefined ? undefined : landscape } : p)) };
      const pages = next.pages.map((p, i) => {
        const [w, h] = sizeOf(next, i);
        if (w === sizeOf(doc, i)[0]) return p;
        return { ...p, blocks: p.blocks.map((b) => ({ ...b, x: Math.max(0, Math.min(b.x, w - b.w)), y: Math.max(0, Math.min(b.y, h - b.h)) })) };
      });
      return { ...next, pages };
    });
  }
  function removePage(n = page) {
    update((doc) => ({ ...doc, pages: doc.pages.filter((_, i) => i !== n) }), "", Math.min(page, pages.length - 2));
    setIds([]);
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
  function quit() {
    clearTimeout(press.current);
    tug.current = undefined;
    setHaul(undefined);
  }
  function release() {
    const { from, slot } = tug.current ?? {};
    quit();
    if (slot !== undefined) movePage(from!, landing(from!, slot));
  }
  // On a thumbnail Ctrl with an arrow moves its page by one place, with Shift to the start or the end, and Ctrl+D
  // copies it. The focus follows the page.
  function pageKey(e: Key, n: number) {
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
  function add(w: number, h: number, rest: Fresh, n = page) {
    const { doc } = latest.current;
    const [held, size] = [doc.pages[n].blocks, sizeOf(doc, n)];
    const id = crypto.randomUUID();
    const y = round(Math.max(0, seen(0, n))) + MARGIN;
    const z = Math.max(0, ...held.map((b) => b.z)) + 1;
    const [block] = land([{ id, x: (size[0] - w) / 2, y, w, h, z, locked: false, ...rest }], held, size);
    turn((p) => ({ ...p, blocks: [...p.blocks, block] }), undefined, n);
    setAt(n);
    setIds([id]);
    // An empty text opens for typing; a pasted one comes with its words.
    if (rest.type === "text" && !rest.props.text) setEditing(id);
  }
  // A picture goes to the server first; the block holds its number and its shape, and starts within 100 mm.
  async function sent(file: File) {
    const body = new FormData();
    body.append("file", file);
    const [{ id }, { width, height }] = await Promise.all([api<{ id: number }>("/uploads", { method: "POST", body }), createImageBitmap(file)]);
    const w = round(Math.min(100, (100 * width) / height));
    return { w, h: round((w * height) / width), type: "image" as const, props: { upload: id, ratio: width / height, cut: [0, 0, 0, 0] } };
  }
  const refuse = () => alert("Das Bild ließ sich nicht hochladen. Es gehen JPEG, PNG, WebP und GIF bis 15 MB.");
  async function upload(file?: File) {
    if (!file) return;
    const where = mark();
    try {
      const { w, h, ...rest } = await sent(file);
      calm(() => add(w, h, rest, where()));
    } catch {
      refuse();
    }
  }
  // Dropped files land with the first one's middle under the pointer, on the page that lies there, and each next one
  // 5 mm right and down. They stay where they were dropped, also on a block, so they only move as far as the page
  // needs to hold them. The page and the spot are read at once: the desk may scroll while the pictures are on their way.
  async function dropped(files: File[], left: number, top: number) {
    // Beside the pages, the nearest one takes the drop.
    const rects = [...desk.current!.querySelectorAll<HTMLElement>("[data-page]")].map((el) => el.getBoundingClientRect());
    const away = rects.map((r) => Math.hypot(Math.max(r.left - left, 0, left - r.right), Math.max(r.top - top, 0, top - r.bottom)));
    const was = away.indexOf(Math.min(...away));
    const [x, y] = [(left - rects[was].left) / k, (top - rects[was].top) / k];
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
    if (made.length < files.length) refuse();
  }
  // A maths block starts with plus exercises up to 20; the server makes them.
  async function addMaths() {
    const limits = { ops: ["+" as const], max: 20, a: [[0, 9], [0, 9]] as Range[], b: [[0, 9], [0, 9]] as Range[], carry: "either" as const, rest: false, format: "row" as const, count: 12, seed: newSeed() };
    const where = mark();
    try {
      const props = { ...limits, ...(await generate(limits)), columns: 3, size: 14 };
      calm(() => add(180, mathsHeight(props), { type: "maths", props }, where()));
    } catch {
      alert("Die Aufgaben ließen sich nicht erzeugen. Ist das Gerät online?");
    }
  }
  function put(from: Block[]) {
    const copies = land(
      cloned([...from].sort((a, b) => a.z - b.z), blocks).map((b, i) => ({ ...b, z: top + 1 + i })),
    );
    change((bs) => [...bs, ...copies]);
    setIds(copies.map((b) => b.id));
  }
  // The copied blocks lie in the browser's store: they last over a reload and reach another sheet and another tab.
  // They carry the account's id, for the browser may serve another account next.
  // Their words go to the system's clipboard, which pushes out a picture copied before: the newest copy wins.
  // They go out in a copy of the browser's own, which needs no leave and is done before the next paste. A copy with
  // no words waiting, as a field's, stays the browser's.
  const pending = useRef<string | null>(null);
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
    localStorage.setItem("clip", JSON.stringify({ owner: user.id, blocks: held }));
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
  function clip(): Block[] {
    let held: { owner?: number; blocks?: Block[] } | null = null;
    try {
      held = JSON.parse(localStorage.getItem("clip") ?? "null");
    } catch {
      return [];
    }
    const whole = (b?: Block) => b?.id && b.type in NAMES && b.props && [b.x, b.y, b.w, b.h, b.z].every(Number.isFinite);
    return held?.owner === user.id && Array.isArray(held.blocks) && held.blocks.every(whole) ? held.blocks : [];
  }
  function paste() {
    const held = clip();
    if (held.length) put(held);
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
    add(80, 12, { type: "text", props: { text: words.replace(/\n+$/, ""), size: 14, align: "left" } });
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
        if (type) return upload(new File([await item.getType(type)], "bild", { type }));
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
  function raise(front: boolean, one = false) {
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
    // What already lies there leaves nothing to undo.
    if (stack.every((b, i) => b === order[i])) return;
    const z = new Map(stack.map((b, i) => [b.id, i + 1]));
    place(blocks.map((b) => [b.id, { z: z.get(b.id)! }]));
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
        const sized = b.type === "image" || b.type === "symbol" ? { ...b, w: b.w * k, h: b.h * k } : { ...b, [along]: (to - b[across] * Math.min(c, s)) / Math.max(c, s) };
        const [was, now] = [outline(b), outline(sized)];
        return [b, { x: sized.x + was.x - now.x, y: sized.y + was.y - now.y, w: sized.w, h: sized.h }];
      }),
    );
  }
  function distribute(axis: Axis) {
    const size = axis === "x" ? "w" : "h";
    const row = things.map((t) => ({ t, box: bounds(t.map(outline)) })).sort((a, b) => a.box[axis] - b.box[axis]);
    const end = row.at(-1)!.box[axis] + row.at(-1)!.box[size];
    const gap = (end - row[0].box[axis] - row.reduce((sum, r) => sum + r.box[size], 0)) / (row.length - 1);
    let next = row[0].box[axis];
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
  function hop(e: Key<HTMLTextAreaElement>, b: TableBlock) {
    // Escape and F2 end the writing themselves: after a press in the panel a blur would not.
    if (e.key === "Escape" || e.key === "F2") setEditing("");
    if (e.key !== "Tab") return;
    e.preventDefault();
    // What is typed in the next cell is an undo step of its own.
    mergeKey.current = "";
    const to = Math.max(0, slot + (e.shiftKey ? -1 : 1));
    const rows = b.props.cells.length;
    if (to === rows * b.props.cols.length) rank(b, "row", rows, true);
    setSlot(to);
  }
  // Adds an empty row or column to a table before the one at `i`, or takes the one at `i` away; the last one
  // stays. A new row adds its height to the block, a line of text with the cell's padding and line, and
  // a row that goes takes with it the height it has now. The field stays with its cell, and goes to a neighbour
  // when its cell goes.
  function rank(b: TableBlock, axis: "row" | "col", i: number, add: boolean) {
    const [rows, cols] = [b.props.cells.length, b.props.cols.length];
    const n = axis === "row" ? rows : cols;
    if (!add && n < 2) return;
    const gone = sheet.current!.querySelector(`[data-id="${b.id}"] [data-cell="${i * cols}"]`);
    const dh = axis === "col" ? 0 : add ? b.props.size * PT * 1.6 + 0.25 : -gone!.getBoundingClientRect().height / k;
    const to = (at: number) => (add ? at + +(i <= at) : Math.min(at - +(i < at), n - 2));
    const [r, c] = [Math.floor(slot / cols), slot % cols];
    const next = axis === "row" ? to(r) * cols + c : r * (cols + (add ? 1 : -1)) + to(c);
    if (add && next !== slot) caret.current = sheet.current!.querySelector<HTMLTextAreaElement>(".table textarea")?.selectionStart;
    setSlot(next);
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === b.id ? { ...b, h: round(b.h + dh), props: spliced(b.props, axis, i, add) } : o)));
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
  // which may hold an older document.
  async function pdf(key: boolean) {
    await last.save;
    save.current(false);
    await last.save;
    location.href = `/api/sheets/${file.id}/pdf${key ? "?solved=true" : ""}`;
  }

  async function store() {
    const saved = await post<Template>("/templates", { name: name.trim(), doc: hist.doc });
    setTemplates((ts) => [...ts, saved]);
    setName("");
  }
  // A template takes the place of the sheet; undo brings the sheet back.
  function apply(t: Template) {
    update(() => read(t.doc));
    setIds([]);
  }
  async function forget(t: Template) {
    if (!confirm(`Vorlage „${t.name}“ löschen?`)) return;
    await api(`/templates/${t.id}`, { method: "DELETE" });
    setTemplates((ts) => ts.filter((o) => o.id !== t.id));
  }

  // `press` is the mouse press that selects, so the same press can drag.
  function pick(el: Element, shift: boolean, press?: globalThis.MouseEvent) {
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
      // On touch a second tap on a text block edits it and on a picture crops it; a mouse double-clicks.
      else if (touch.current) edit(id, el);
      // Level lines in a row leave Moveable's group area no height, so a press on one lands here.
      else if (press && ids.length > 1) moveable.current!.dragStart(press);
    } else {
      setIds(more ? [...ids, ...unit(id)] : unit(id));
      if (press) moveable.current!.waitToChangeTarget().then(() => moveable.current!.dragStart(press));
    }
  }
  // `el` is what was pressed: in a table, the cell that gets the caret. `all` picks all the text there.
  function edit(id?: string, el?: Element, all = false) {
    if (!id || free.length !== 1 || free[0].id !== id || el?.closest(".bar")) return;
    if (boxed(free[0]) || free[0].type === "ruling" || free[0].type === "table") {
      entire.current = all;
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
    // A second finger ends the hold at once, and so does one finger that has moved away.
    const { clientX: x0, clientY: y0 } = e.touches[0];
    if (e.touches.length > 1 || Math.hypot(x0 - came.current[0], y0 - came.current[1]) > SLOP) clearTimeout(hold.current);
    // A snap the blocks reached before the finger had left where it came down takes them now, if it has.
    if (e.touches.length === 1 && owed.current) drag(owed.current, e.touches[0]);
    if (e.touches.length !== 2) return;
    const next = Math.min(4, Math.max(0.25, (pinch.current.zoom * spread(e)) / pinch.current.spread));
    flushSync(() => setZoom(next));
    // Scroll the page point the pinch began on back under the fingers.
    const page = sheet.current!.getBoundingClientRect();
    const [x, y] = centre(e);
    desk.current!.scrollBy(page.left + pinch.current.x * fit * next - x, page.top + pinch.current.y * fit * next - y);
  }

  const locked = sel.length > 0 && sel.every((b) => b.locked);
  // A right click on the desk picks as in PowerPoint and opens the menu. In a field the browser's own stays: false.
  function menuAt(el: Element, x: number, y: number) {
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
  const lockIt: Command = { label: locked ? "Entsperren" : "Sperren", icon: locked ? LockOpen : Lock, disabled: none, run: () => place(sel.map((b) => [b.id, { locked: !locked }])) };
  const groups: Command[] = [
    { label: "Gruppieren", icon: Group, keys: `${ctrl}G`, disabled: !joinable, run: join },
    { label: "Gruppierung aufheben", icon: Ungroup, keys: `${ctrl}${shift}G`, disabled: !splittable, run: split },
  ];
  const items: Item[] =
    thumbed !== undefined
      ? [
          { label: "Neue Seite", icon: FilePlus, run: () => addPage(thumbed) },
          { label: "Seite duplizieren", icon: CopyPlus, run: () => copyPage(thumbed) },
          { label: "Seite löschen", icon: FileX, disabled: pages.length < 2, run: () => removePage(thumbed) },
        ]
      : [
          ...clips,
          ...copies,
          "sep",
          lockIt,
          "sep",
          ...groups,
          "sep",
          { label: "In den Vordergrund", disabled: none, run: () => raise(true) },
          { label: "Eine Ebene nach vorn", disabled: none, run: () => raise(true, true) },
          { label: "Eine Ebene nach hinten", disabled: none, run: () => raise(false, true) },
          { label: "In den Hintergrund", disabled: none, run: () => raise(false) },
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
    setZoom(Math.min(4, Math.max(0.25, 1.25 ** to)));
  }
  // The whole page in use, width and height, once: it does not follow the window.
  function fitPage() {
    const el = desk.current!;
    // 120 is the desk's padding above and below.
    flushSync(() => setZoom(Math.min(4, Math.max(0.25, Math.min(room / W, (el.clientHeight - 120) / H) / fit))));
    const [page, box] = [sheet.current!.getBoundingClientRect(), el.getBoundingClientRect()];
    // The page lies in the middle, across, also beside a wider one, and its top under the desk's padding.
    el.scrollBy(page.left + page.width / 2 - box.left - el.clientWidth / 2, page.top - box.top - 32);
  }
  const zoomer = (
    <>
      <Tool icon={ZoomOut} label="Kleiner" onClick={() => zoomBy(-1)} />
      {/* The page's size on the screen against its size on paper. */}
      <button className="zoom" title="Seitenbreite" onClick={() => setZoom(1)}>
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
          { label: "Seitenbreite", run: () => setZoom(1) },
          { label: "Ganze Seite", icon: Fullscreen, run: fitPage },
          { label: "Größer", icon: ZoomIn, run: () => zoomBy(1) },
        ]),
    { label: "Rundgang", icon: CircleHelp, run: () => setTour(true) },
    { label: "Feedback", icon: MessageSquare, run: () => feedback.current!() },
  ];
  const more = folding.slice(fits ?? folding.length);
  const inBar = (label: string) => !more.some((item) => item.label === label);
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
      {/* What makes exercises, a group to a subject. */}
      <i className="sep" data-name="Mathe" />
      <Tool icon={Calculator} label="Rechnen" data-tour="maths" onClick={addMaths} />
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
            // A press that took the focus has its click still to come: the bar waits until the mouse button is up and
            // the click is through, or the button pressed would move from under the pointer. A key ends it at once.
            onBlur={() => (document.querySelector(":active") ? addEventListener("mouseup", () => setTimeout(refit), { once: true, capture: true }) : refit())}
            // Enter ends the edit, as in PowerPoint, and gives the keys back; Escape does so for any field.
            onKeyDown={(e) => e.key === "Enter" && back(e.currentTarget)}
          />
          <span className="hint" role="status">
            {!dirty ? "Gespeichert" : tries || clash ? "Nicht gespeichert" : "Speichert …"}
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
        </div>
        {clash && (
          <div className="clash" role="alert">
            Dieses Blatt wurde auf einem anderen Gerät geändert.
            <button onClick={reload}>Andere Version laden</button>
            <button
              // Based on the version the server has now, this document takes its place; a change that lands in between clashes again.
              onClick={async () => {
                version.current = (await api<Sheet>(`/sheets/${file.id}`)).version;
                setClash(false);
              }}
            >
              Mit dieser überschreiben
            </button>
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
                className={[n === page && "on", n === haul?.from && "drag"].filter(Boolean).join(" ")}
                aria-pressed={n === page}
                // The click after a drag is the drag's end, not a visit. The next one, also by Enter, visits again.
                onClick={() => {
                  if (!dragged.current) visit(n);
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
                  if (t.slot !== undefined || Math.hypot(e.clientX - t.x, e.clientY - t.y) >= 4) aim(e.clientX, e.clientY);
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
          <h2>Vorlagen</h2>
          {templates.filter((t) => t.id < 0).map((t) => (
            <div key={t.id} className="tpl">
              <button onClick={() => apply(t)}>
                <LayoutTemplate size={14} aria-hidden />
                {t.name}
              </button>
              <small>eingebaut</small>
            </div>
          ))}
          <h2>Meine Vorlagen</h2>
          {kept.map((t) => (
            <div key={t.id} className="tpl">
              <button onClick={() => apply(t)}>
                <LayoutTemplate size={14} aria-hidden />
                {t.name}
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
          onPointerDown={(e) => {
            touch.current = e.pointerType === "touch";
            cover.current = moveable.current!.isMoveableElement(e.target as Element);
            // The hold before is over with the next press, not with its own lift: Moveable hears of that lift later.
            held.current = false;
          }}
          onMouseDown={(e) => {
            // Moveable keeps the press from moving the focus, so an input, or a button reached by the keys, would keep
            // Enter and Tab.
            if (!document.activeElement?.closest(".block")) (document.activeElement as HTMLElement | null)?.blur();
            // The right button drags nothing: its menu picks the block.
            if (touch.current || e.button === 2 || moveable.current!.isMoveableElement(e.target as Element)) return;
            // A press on a picked block may drag it. Only a click that stays on its spot picks a block out of its group.
            spot.current = !e.shiftKey && ids.includes((e.target as Element).closest<HTMLElement>(".block")?.dataset.id ?? "") ? [e.clientX, e.clientY] : undefined;
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
            const still = spot.current && Math.hypot(e.clientX - spot.current[0], e.clientY - spot.current[1]) < 3;
            if (touch.current || still) pick(e.target as Element, false);
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
              <div className="scaled" style={{ width: sizes[n][0] * K, height: sizes[n][1] * K, transform: `scale(${k / K})` }}>
                {p.blocks.map((b) => (

                  <div
                    key={b.id}
                    data-id={b.id}
                    className={ids.includes(b.id) ? "block sel" : "block"}
                    style={{ left: b.x * K, top: b.y * K, width: b.w * K, height: b.h * K, zIndex: b.z, ...turned(b) }}
                  >
                    <Draw block={b} k={K} solved={solved} at={editing === b.id ? slot : undefined}>
                      {/* Only the text being edited needs a field; the others draw as they do in the PDF. */}
                      {boxed(b) && editing === b.id ? (
                        <Field
                          view={field}
                          props={boxed(b)!}
                          hint={b.type === "text"}
                          all={entire.current}
                          change={look}
                          pick={(next) => setPart((now) => (JSON.stringify(now) === JSON.stringify(next) ? now : next))}
                          blur={(e) => stays(e) || setEditing("")}
                          end={() => setEditing("")}
                        />
                      ) : b.type === "text" && !b.props.text && !b.props.rich ? (
                        <div className="rich" data-hint="">
                          <p>
                            <br />
                          </p>
                        </div>
                      ) : b.type === "ruling" ? (
                        <textarea
                          className="written"
                          value={b.props.text ?? ""}
                          readOnly={editing !== b.id}
                          // Tab from a field of the panel does not stop at a Lineatur that is not written in.
                          tabIndex={editing === b.id ? undefined : -1}
                          style={writtenStyle(b, K)}
                          onChange={(e) => style("ruling", { text: e.target.value }, "text")}
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
                          onChange={(e) => style("table", { cells: b.props.cells.map((row, r) => row.map((text, c) => (r * row.length + c === slot ? e.target.value : text))) }, "text")}
                          onKeyDown={(e) => hop(e, b)}
                          onBlur={(e) => stays(e) || setEditing("")}
                        />
                      ) : undefined}
                    </Draw>
                    <Mark block={b} k={K} n={ns.get(b.id)} />
                  </div>
                ))}
              </div>
              {/* The sheet's guide lines lie on every page; a page's own are drawn dotted. */}
              {[undefined, n].flatMap((at) =>
                (["x", "y"] as const).flatMap((axis) =>
                  (at === undefined ? guides : (p.guides ?? NONE))[axis].map((mm, i) => (at === undefined && mm > sizes[n][axis === "x" ? 0 : 1]) || (
                    <i key={`${at}${axis}${i}`} className={`rule ${axis}${at === undefined ? "" : " own"}`} style={axis === "x" ? { left: mm * k } : { top: mm * k }}>
                      <b onPointerDown={grip} onPointerMove={(e) => slide(e, axis, i, at)} onLostPointerCapture={() => drop(axis, i, at)}>
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
                  {table?.props.cols.slice(1).map((_, i) => (
                    <i
                      key={i}
                      className="bar"
                      style={{ left: (table.x + (sum(table.props.cols.slice(0, i + 1)) / sum(table.props.cols)) * table.w) * k, top: table.y * k, height: table.h * k }}
                      onPointerDown={grip}
                      onPointerMove={(e) => widen(e, table, i)}
                    />
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
                  {group &&
                    [0, 1, 2, 3].map((i) => (
                      <i
                        key={i}
                        className="end"
                        style={{ left: (group.x + (i % 2) * group.w) * k, top: (group.y + (i >> 1) * group.h) * k }}
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
                    onDragStart={(e) => begin([e.target])}
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
              setPanning(true);
              // A button that has the focus would take Space's keyup as its click.
              if (document.activeElement instanceof HTMLButtonElement) document.activeElement.blur();
            }}
            onPointerMove={(e) => {
              if (!panning) return;
              // The button came up where the hand could not see it.
              if (!e.buttons) return setPanning(false);
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
          {tab === "Format" && sel.length > 0 && (
            <>
              <p className="what">
                {sel.length > 1 ? `${sel.length} Felder` : NAMES[sel[0].type]}
              </p>
              <Format
                // A block of a group with a locked one is as fixed there as the locked one.
                sel={sel.map((b) => (free.includes(b) ? b : { ...b, locked: true }))}
                style={style}
                look={look}
                paint={paint}
                itemize={itemize}
                part={part}
                // A text that a typed size left higher than its box grows back, as after a resize by handle.
                place={(boxes, key) => {
                  tight.current = true;
                  place(boxes, key);
                }}
                rank={rank}
                cell={editing && editing === table?.id ? slot : undefined}
                cropping={!!cropping}
                spin={spin}
                mirror={mirror}
                alone={(b) => thing(b) === b.id}
                lock={lock}
                setLock={setLock}
                size={[W, H]}
                crop={sel.length === 1 && free[0]?.type === "image" ? () => (cropping ? done() : edit(free[0].id)) : undefined}
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
                <button disabled={things.length < 3} onClick={() => distribute("x")}>Waagerecht</button>
                <button disabled={things.length < 3} onClick={() => distribute("y")}>Senkrecht</button>
              </div>
              <h2>Größe angleichen</h2>
              <div className="acts">
                <button disabled={sizable.length < 2} onClick={() => same("w")}>Gleiche Breite</button>
                <button disabled={sizable.length < 2} onClick={() => same("h")}>Gleiche Höhe</button>
              </div>
              <h2>Ebene</h2>
              <div className="acts">
                <button onClick={() => raise(true)}>Nach vorn</button>
                <button onClick={() => raise(false)}>Nach hinten</button>
              </div>
              <div className="acts">
                <button onClick={() => raise(true, true)}>Eine nach vorn</button>
                <button onClick={() => raise(false, true)}>Eine nach hinten</button>
              </div>
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
            if (n) thumbMenu(+n, x, y);
            else if (el?.closest(".desk")) menuAt(el, x, y);
          }}
        />
      )}
    </main>
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
