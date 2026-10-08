import {
  memo,
  useDeferredValue,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type KeyboardEvent as Key,
  type PointerEvent,
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
  Eraser,
  Eye,
  Group,
  FileCheck,
  FileDown,
  FilePlus,
  FileX,
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
import Moveable, { type OnDrag, type OnResize } from "react-moveable";
import Selecto from "react-selecto";
import { Link, useParams } from "react-router";
import { api, post } from "../api";
import Feedback from "../components/Feedback";
import Logo from "../components/Logo";
import Tour from "../components/Tour";
import type { EditorView } from "prosemirror-view";
import { Draw, K, MARGIN, Mark, PT, Paper, boxed, cleared, far, isLine, last, listed, mathsHeight, numbers, parasOf, read, sizeOf, spliced, sum, turned, writtenStyle, type Axis, type Block, type Box, type Corner, type Doc, type Guides, type ImageBlock, type Kind, type List, type Page, type Range, type Sheet, type ShapeBlock, type TableBlock, type TextProps } from "../sheet";
import Field, { list, tint, type Marks, type Picked } from "./Field";
import Format, { bounds, drawn, has, norm } from "./Format";
import { generate, newSeed } from "./Maths";

type Template = { id: number; name: string; doc: Doc };
// A new block's type and settings; `add` gives it its place.
type Fresh<B = Block> = B extends Block ? Pick<B, "type" | "props"> : never;

const SIDES = { top: true, left: true, bottom: true, right: true, center: true, middle: true };
const CORNERS = ["nw", "ne", "sw", "se"];
// The look the brush carries from a text or a shape to the next. A line gives and takes its stroke alone, a table
// what its cells have, and any other block nothing.
const LOOK = ["font", "size", "bold", "italic", "underline", "color", "spacing", "align", "valign", "fill", "opacity", "stroke", "strokeWidth", "dash"] as const;
const takes = (b: Block): readonly (typeof LOOK)[number][] =>
  isLine(b) ? ["stroke", "strokeWidth", "dash"] : b.type === "table" ? ["font", "size", "color", "align"] : boxed(b) ? LOOK : [];
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
const GRIDS = [0, 5, 10, 20];
const NONE: Guides = { x: [], y: [] };
// The keys held during a drag, as PowerPoint reads them. Shift keeps the shape or the direction. Ctrl (Option on
// Apple) resizes about the centre and leaves a copy behind a move. Alt (Command on Apple) switches snapping off.
const KEEP = 1;
const CENTRE = 2;
const LOOSE = 4;
const APPLE = /Mac|iPhone|iPad/.test(navigator.platform);

const round = (n: number) => Math.round(n * 100) / 100;
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
// The level box around a turned block's outline. It has the block's centre.
const outline = <T extends Box>(b: T): T => {
  const [c, s] = dir(b).map(Math.abs);
  const [w, h] = [b.w * c + b.h * s, b.w * s + b.h * c];
  return { ...b, x: b.x + (b.w - w) / 2, y: b.y + (b.h - h) / 2, w, h };
};
// The cosine and sine of a block's angle.
const dir = (b: { angle?: number }) => [Math.cos(((b.angle ?? 0) * Math.PI) / 180), Math.sin(((b.angle ?? 0) * Math.PI) / 180)];
// A new block's next step along one axis: 5 mm on, or back at the margin where the page ends.
const step = (at: number, max: number) => (at + 5 <= max ? at + 5 : Math.min(MARGIN, max));
// A page drawn small in the left panel.
const Thumb = memo(Paper);

export default function Editor() {
  const { id } = useParams();
  // undefined while the sheet is loading, null when it is not there.
  const [file, setFile] = useState<Sheet | null>();

  function load() {
    api<Sheet>(`/sheets/${id}`).then(setFile, () => setFile(null));
  }
  useEffect(load, [id]);

  // The empty editor keeps the app's bar away while the sheet loads.
  if (file === undefined) return <main className="editor" />;
  if (!file) return <main><h1>Blatt nicht gefunden</h1></main>;
  // A version loaded anew starts the editor over.
  return <Canvas key={`${file.id}.${file.version}`} file={file} reload={load} />;
}

function Canvas({ file, reload }: { file: Sheet; reload: () => void }) {
  const [hist, setHist] = useState<{ past: Doc[]; doc: Doc; future: Doc[] }>(() => ({ past: [], doc: read(file.doc), future: [] }));
  const [title, setTitle] = useState(file.title);
  // What the server holds, and how often a save has failed since.
  const [stored, setStored] = useState({ doc: hist.doc, title });
  const [tries, setTries] = useState(0);
  // Set when the server holds a newer document than the one this editor began with.
  const [clash, setClash] = useState(false);
  // Whether a new guide line or grid is for the page in use alone.
  const [own, setOwn] = useState(false);
  const [at, setAt] = useState(0);
  const [ids, setIds] = useState<string[]>([]);
  const [targets, setTargets] = useState<HTMLElement[]>([]);
  // The blocks that stay put. Moveable reads a selector as its first match only, so it gets the elements.
  const [rest, setRest] = useState<HTMLElement[]>([]);
  const [clip, setClip] = useState<Block[]>([]);
  // The format painter: the look it picked up, as it was then, and whether it is on: 1 for one block, 2 until ended.
  const [coat, setCoat] = useState<Partial<TextProps>>();
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
  // Whether the last press was in the format panel: the field then stays open though it loses the focus.
  const inPanel = useRef(false);
  const [multi, setMulti] = useState(false);
  const [tab, setTab] = useState(TABS[0]);
  // Whether several blocks line up with the page, not with each other.
  const [onPage, setOnPage] = useState(false);
  // The panel's lock: a new width sets the height to match, in its fields and on the handles.
  const [lock, setLock] = useState(false);
  const [pane, setPane] = useState(true);
  // The panel of pages and templates starts shut where it would lie over the desk.
  // Blattform lays the editor out anew on a wide window: the left panel holds what can be inserted, and Start,
  // Ansicht and Vorlagen in the bar pick what the panels show. `side` then means that Vorlagen is open.
  const leaf = document.documentElement.dataset.theme === "leaf" && innerWidth > 700;
  const [side, setSide] = useState(() => innerWidth > 700 && !leaf);
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
  const desk = useRef<HTMLDivElement>(null);
  const sheet = useRef<HTMLDivElement>(null);
  const moveable = useRef<Moveable>(null);
  const picker = useRef<HTMLInputElement>(null);
  const mergeKey = useRef("");
  // Set by a change that can leave a text higher than its box.
  const tight = useRef(false);
  const touch = useRef(false);
  const hold = useRef(0);
  const held = useRef(false);
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
  const free = sel.filter((b) => !b.locked);
  // Whether the blocks line up among themselves.
  const among = !onPage && free.length > 1;
  // What can take another's size: a line has only its length.
  const sizable = free.filter((b) => !isLine(b));
  const ns = numbers(hist.doc);
  // The built-in templates have ids below zero; the teacher's own can be deleted.
  const kept = templates.filter((t) => t.id > 0);
  // What has a fill and a border. The first shows its settings; a change goes to all of them.
  const boxes = sel.filter((b) => b.type === "shape" || b.type === "text");
  const fill = boxes[0]?.props.fill ?? "none";
  const stroke = boxes[0]?.props.stroke ?? "none";
  // The block the brush picks its look up from.
  const source = sel.find((b) => takes(b).length);
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
    const observer = new ResizeObserver(([entry]) => setRoom(entry.contentRect.width));
    observer.observe(desk.current!);
    return () => observer.disconnect();
  }, []);

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
    const grown = new Map<string, number>();
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
      if (h > b.h) grown.set(b.id, h);
    }
    // A font used for the first time is still on its way: the text is measured again once it is there.
    if (document.fonts.status === "loading")
      document.fonts.ready.then(() => {
        tight.current = true;
        setHist((h) => ({ ...h }));
      });
    if (!grown.size) return;
    const grow = (p: Page) => ({ ...p, blocks: p.blocks.map((b) => (grown.has(b.id) ? { ...b, h: grown.get(b.id)! } : b)) });
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
  useLayoutEffect(() => {
    const press = (e: KeyboardEvent) => onKey.current(e);
    window.addEventListener("keydown", press);
    return () => window.removeEventListener("keydown", press);
  }, []);
  onKey.current = (e) => {
    // The keys are a dialog's own while it is open.
    if (document.querySelector("dialog:modal")) return;
    const target = e.target as HTMLElement;
    // Escape puts the brush down from anywhere, also from a field that keeps the key to itself.
    if (e.key === "Escape") setBrush(0);
    // Ctrl+B, I and U alone never reach the browser while a block is selected: Chrome has shortcuts of its own on
    // them. With Shift or Alt they stay the browser's.
    const mark = (e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey;
    if (mark && /^[biu]$/i.test(e.key) && sel.length && !target.closest("input, select")) e.preventDefault();
    // In a text's field, in a table's cell, in the panel's fields for place and size and on its sliders only undo and
    // redo are the sheet's.
    const ours = (e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key) && target.closest(".ProseMirror, .table, input.mm, input[type=range]");
    if (!ours && target.closest(".ProseMirror, textarea, input, select")) return;
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
      setIds(grouped([to.id], blocks));
    };
    // A button that has the focus keeps Enter and Tab. With nothing selected Tab picks the block at the back and
    // Shift+Tab the one in front.
    const plain = !target.closest("button, a");
    const keys: Record<string, (() => void) | false | undefined> =
      e.ctrlKey || e.metaKey
        ? { z: e.shiftKey ? redo : undo, y: redo, c: e.shiftKey ? () => dip() : () => setClip(sel), v: e.shiftKey ? () => daub(ids) : paste, d: () => put(sel), a: all, g: e.shiftKey ? split : join, b: flip("bold"), i: flip("italic"), u: flip("underline") }
        : {
            delete: remove,
            backspace: remove,
            escape: done,
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
    const onKey = (e: KeyboardEvent) =>
      setMod((e.shiftKey ? KEEP : 0) | ((APPLE ? e.altKey : e.ctrlKey) ? CENTRE : 0) | ((APPLE ? e.metaKey : e.altKey) ? LOOSE : 0));
    const onBlur = () => setMod(0);
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

  // Changes that share a key within one gesture (a drag, typing, a colour picker) make one undo step.
  function update(fn: (doc: Doc) => Doc, key = "") {
    const merge = key !== "" && key === mergeKey.current;
    mergeKey.current = key;
    setHist((h) => ({ past: merge ? h.past : [...h.past, h.doc], doc: fn(h.doc), future: [] }));
  }
  // Changes one page, the one in use unless `n` names another.
  function turn(fn: (p: Page) => Page, key?: string, n = page) {
    update((doc) => ({ ...doc, pages: doc.pages.map((p, i) => (i === n ? fn(p) : p)) }), key);
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
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === type ? ({ ...b, props: { ...b.props, ...props } } as Block) : b)), key);
  }
  // Sets what a shape and a text share: the frame, and the text in it.
  function look(props: object, key?: string) {
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && (b.type === "shape" || b.type === "text") ? ({ ...b, props: { ...b.props, ...props } } as Block) : b)), key);
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
          return text ? ({ ...b, props: { ...b.props, ...(text.rich && cleared(text.rich, props)), ...props } } as Block) : b;
        }),
      key,
    );
  }
  // The brush picks up the look of the first selected block that has one. Every key is in it, also where the block
  // has nothing there: the block painted then loses its own, as in PowerPoint.
  function dip(marks?: Marks) {
    if (!source) return;
    const from = { ...(boxed(source) ?? source.props), ...marks } as Partial<TextProps>;
    // A field says "not bold" where a block says nothing: both are the same look.
    setCoat(Object.fromEntries(takes(source).map((name) => [name, from[name] === false ? undefined : from[name]])));
  }
  // Lays the look on blocks of page `n`. Each takes what it has, and its words lose what they had of their own
  // there. All of it is one undo step, and none where nothing changes.
  function daub(on: string[], n = page) {
    if (!coat) return;
    const dab = (b: Block) => {
      const own = on.includes(b.id) ? takes(b).filter((name) => name in coat) : [];
      // A line never vanishes: it takes a border only from a block that has one.
      if (!own.length || (isLine(b) && (coat.stroke ?? "none") === "none")) return b;
      const props = Object.fromEntries(own.map((name) => [name, coat[name] ?? (b.type === "shape" ? BARE[name] : undefined)]));
      const rich = boxed(b)?.rich;
      // What is left unset goes, so a saved sheet opens as it looks here.
      const all = Object.entries({ ...b.props, ...(rich && cleared(rich, props)), ...props }).filter(([, value]) => value !== undefined);
      return { ...b, props: Object.fromEntries(all) } as Block;
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
  function undo() {
    mergeKey.current = "";
    setHist((h) => (h.past.length ? { past: h.past.slice(0, -1), doc: h.past.at(-1)!, future: [h.doc, ...h.future] } : h));
  }
  function redo() {
    mergeKey.current = "";
    setHist((h) => (h.future.length ? { past: [...h.past, h.doc], doc: h.future[0], future: h.future.slice(1) } : h));
  }

  // The new page comes after the one in use and takes its place.
  function addPage() {
    flushSync(() => {
      update((doc) => ({ ...doc, pages: [...doc.pages.slice(0, page + 1), { blocks: [] }, ...doc.pages.slice(page + 1)] }));
      setAt(page + 1);
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
      const next = { ...doc, ...(n === undefined && { landscape }), pages: doc.pages.map((p, i) => (n === undefined || i === n ? { ...p, landscape: n === undefined ? undefined : landscape } : p)) };
      const pages = next.pages.map((p, i) => {
        const [w, h] = sizeOf(next, i);
        if (w === sizeOf(doc, i)[0]) return p;
        return { ...p, blocks: p.blocks.map((b) => ({ ...b, x: Math.max(0, Math.min(b.x, w - b.w)), y: Math.max(0, Math.min(b.y, h - b.h)) })) };
      });
      return { ...next, pages };
    });
  }
  function removePage() {
    update((doc) => ({ ...doc, pages: doc.pages.filter((_, i) => i !== page) }));
    setIds([]);
  }

  // The page an element lies on; beside the pages, the one in use.
  const pageOf = (el: Element) => +(el.closest<HTMLElement>(".sheet")?.dataset.page ?? page);
  // How far down the page in use, in mm, a point of the desk's view lies.
  const seen = (down: number) => (desk.current!.getBoundingClientRect().top + down - sheet.current!.getBoundingClientRect().top) / k;

  // Moves new blocks as one onto the page, then in steps clear of a block already at that spot.
  function land<T extends Box>(boxes: T[]) {
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
  function add(w: number, h: number, rest: Fresh) {
    const id = crypto.randomUUID();
    const y = round(Math.max(0, seen(0))) + MARGIN;
    const [block] = land([{ id, x: (W - w) / 2, y, w, h, z: top + 1, locked: false, ...rest }]);
    change((bs) => [...bs, block]);
    setIds([id]);
    if (rest.type === "text") setEditing(id);
  }
  // A picture goes to the server first; the block holds its number and its shape, and starts within 100 mm.
  async function upload(file?: File) {
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const [{ id }, { width, height }] = await Promise.all([api<{ id: number }>("/uploads", { method: "POST", body }), createImageBitmap(file)]);
      const w = round(Math.min(100, (100 * width) / height));
      add(w, round((w * height) / width), { type: "image", props: { upload: id, ratio: width / height, cut: [0, 0, 0, 0] } });
    } catch {
      alert("Das Bild ließ sich nicht hochladen. Es gehen JPEG, PNG, WebP und GIF bis 15 MB.");
    }
  }
  // A maths block starts with plus exercises up to 20; the server makes them.
  async function addMaths() {
    const limits = { ops: ["+" as const], max: 20, a: [[0, 9], [0, 9]] as Range[], b: [[0, 9], [0, 9]] as Range[], carry: "either" as const, rest: false, format: "row" as const, count: 12, seed: newSeed() };
    try {
      const props = { ...limits, ...(await generate(limits)), columns: 3, size: 14 };
      add(180, mathsHeight(props), { type: "maths", props });
    } catch {
      alert("Die Aufgaben ließen sich nicht erzeugen. Ist das Gerät online?");
    }
  }
  function put(from: Block[]) {
    const copies = land(
      cloned([...from].sort((a, b) => a.z - b.z), blocks).map((b, i) => ({ ...b, x: b.x + 5, y: b.y + 5, z: top + 1 + i })),
    );
    change((bs) => [...bs, ...copies]);
    setIds(copies.map((b) => b.id));
    return copies;
  }
  // Pasting again steps on from the last paste.
  const paste = () => setClip(put(clip));
  function remove() {
    change((bs) => bs.filter((b) => !ids.includes(b.id)));
    setIds([]);
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

  function align(axis: Axis, at: number) {
    const size = axis === "x" ? "w" : "h";
    // One block lines up with the page. Several do so with each other, or with the page when the switch says so.
    const lo = among ? Math.min(...free.map((b) => b[axis])) : 0;
    const hi = among ? Math.max(...free.map((b) => b[axis] + b[size])) : axis === "x" ? W : H;
    place(free.map((b) => [b.id, { [axis]: round(lo + (hi - lo - b[size]) * at) }]));
  }
  // As wide as the widest, or as high as the highest. Each keeps its corner; a picture and a symbol keep their shape.
  function same(side: "w" | "h") {
    const other = side === "w" ? "h" : "w";
    const to = Math.max(...sizable.map((b) => b[side]));
    place(sizable.map((b) => [b.id, { [side]: to, ...((b.type === "image" || b.type === "symbol") && { [other]: round((b[other] * to) / b[side]) }) }]));
  }
  function distribute(axis: Axis) {
    const size = axis === "x" ? "w" : "h";
    const row = [...free].sort((a, b) => a[axis] - b[axis]);
    const end = row.at(-1)![axis] + row.at(-1)![size];
    const gap = (end - row[0][axis] - row.reduce((sum, b) => sum + b[size], 0)) / (row.length - 1);
    let next = row[0][axis];
    place(
      row.map((b) => {
        const at = next;
        next += b[size] + gap;
        return [b.id, { [axis]: round(at) }];
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
  const drag = (events: OnDrag[]) => {
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
  const begin = (els: Element[]) => (start.current = els.map((el) => blocks.find((b) => b.id === idOf(el))!));
  // With Ctrl held when a move ends, copies stay where the blocks began.
  const leave = (moved: boolean) =>
    moved && mod & CENTRE && change((bs) => [...bs, ...cloned(start.current, bs)], "drag");
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
    const all = bounds(from.map(outline));
    const [cx, cy] = [all.x + all.w / 2, all.y + all.h / 2];
    const [c, s] = dir({ angle: a });
    flushSync(() =>
      place(
        from.map((b) => {
          const [x, y] = [b.x + b.w / 2 - cx, b.y + b.h / 2 - cy];
          return [b.id, { x: round(cx + x * c - y * s - b.w / 2), y: round(cy + x * s + y * c - b.h / 2), angle: norm((b.angle ?? 0) + a) }];
        }),
        "drag",
      ),
    );
  };
  // The panel's buttons turn each block by a quarter about its own centre.
  const spin = (by: number) => place(sel.map((b) => [b.id, { angle: norm((b.angle ?? 0) + by) }]));
  // Mirrors each selected picture, symbol, shape and text in an outline about its own centre, as the page shows it:
  // its angle mirrors too. A line's start changes corners instead, and a shape's text stays readable.
  function mirror(axis: Axis) {
    const swap: Record<Corner, Corner> = axis === "x" ? { nw: "ne", ne: "nw", sw: "se", se: "sw" } : { nw: "sw", sw: "nw", ne: "se", se: "ne" };
    const flag = axis === "x" ? "flipX" : "flipY";
    change((bs) =>
      bs.map((b) => {
        if (!ids.includes(b.id) || (b.type !== "image" && b.type !== "symbol" && b.type !== "shape" && !drawn(b))) return b;
        // `isLine` tells the compiler that every shape it turns down is no shape, so the type is read first.
        // An outline mirrors as a picture does; a box looks the same either way.
        const flips = b.type !== "shape" || drawn(b);
        if (isLine(b)) return { ...b, props: { ...b.props, from: swap[b.props.from ?? "nw"] } };
        return { ...b, angle: norm(-(b.angle ?? 0)), ...(flips && { [flag]: !b[flag] }) };
      }),
    );
  }
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
    if (e.key === "Escape" || e.key === "F2") e.currentTarget.blur();
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
      const page = sheet.current!.getBoundingClientRect();
      const [x, y] = centre(e);
      pinch.current = { spread: spread(e), zoom, x: (x - page.left) / k, y: (y - page.top) / k };
      return;
    }
    // Tap and hold on a block starts selecting several.
    // A finger held on the text being edited picks a word of it.
    const id = (e.target as Element).closest<HTMLElement>(".block")?.dataset.id;
    if (!id || id === editing) return;
    const to = pageOf(e.target as Element);
    hold.current = window.setTimeout(() => {
      held.current = true;
      setMulti(true);
      setAt(to);
      setIds((now) => (to !== page ? grouped([id], pages[to].blocks) : [...new Set([...now, ...unit(id)])]));
    }, 500);
  }
  function onTouchMove(e: TouchEvent) {
    clearTimeout(hold.current);
    if (e.touches.length !== 2) return;
    const next = Math.min(4, Math.max(0.25, (pinch.current.zoom * spread(e)) / pinch.current.spread));
    flushSync(() => setZoom(next));
    // Scroll the page point the pinch began on back under the fingers.
    const page = sheet.current!.getBoundingClientRect();
    const [x, y] = centre(e);
    desk.current!.scrollBy(page.left + pinch.current.x * fit * next - x, page.top + pinch.current.y * fit * next - y);
  }

  const locked = sel.length > 0 && !free.length;
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
    setZoom(1.25 ** Math.min(6, Math.max(-6, to)));
  }
  const zoomer = (
    <>
      <Tool icon={ZoomOut} label="Kleiner" onClick={() => zoomBy(-1)} />
      {/* The page's size on the screen against its size on paper. */}
      <button className="zoom" title="Seitenbreite" onClick={() => setZoom(1)}>
        {Math.round((k * 2540) / 96)} %
      </button>
      <Tool icon={ZoomIn} label="Größer" onClick={() => zoomBy(1)} />
    </>
  );
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
        accept="image/jpeg,image/png,image/webp,image/gif"
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
      className={`editor${leaf ? " leaf" : ""}${brush ? " brush" : ""}`}
      data-ready="1"
      onPointerDown={(e) => {
        mergeKey.current = "";
        inPanel.current = !!(e.target as Element).closest(".panel");
      }}
      // A button pressed with the mouse does not take the focus, as PowerPoint's ribbon does not: Enter and Tab stay
      // the sheet's. A dialog's buttons are its own. What had the focus loses it to the main mouse button as before,
      // unless the button's own group has kept it there.
      onMouseDown={(e) => {
        const button = (e.target as Element).closest("button");
        if (e.defaultPrevented || !button || button.closest("dialog")) return;
        e.preventDefault();
        if (!e.button) (document.activeElement as HTMLElement | null)?.blur();
      }}
    >
      <header>
        <div className="top">
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
              <Tool icon={PanelLeft} label="Seiten und Vorlagen" className={side ? "on" : ""} aria-pressed={side} onClick={() => setSide(!side)} />
            </>
          )}
          <input type="text" aria-label="Titel" placeholder="Unbenanntes Blatt" maxLength={80} value={title} onChange={(e) => setTitle(e.target.value)} />
          <span className="hint" role="status">
            {!dirty ? "Gespeichert" : tries || clash ? "Nicht gespeichert" : "Speichert …"}
          </span>
          <Tool icon={Undo2} label="Rückgängig" data-tour="undo" disabled={!hist.past.length} onClick={undo} />
          <Tool icon={Redo2} label="Wiederholen" disabled={!hist.future.length} onClick={redo} />
          <i className="sep" />
          <Tool icon={Copy} label="Kopieren" disabled={!sel.length} onClick={() => setClip(sel)} />
          <Tool icon={ClipboardPaste} label="Einfügen" disabled={!clip.length} onClick={paste} />
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
          <Tool icon={CopyPlus} label="Duplizieren" disabled={!sel.length} onClick={() => put(sel)} />
          <Tool icon={Trash2} label="Löschen" disabled={!sel.length} onClick={remove} />
          <Tool
            icon={locked ? LockOpen : Lock}
            label={locked ? "Entsperren" : "Sperren"}
            disabled={!sel.length}
            className={locked ? "on" : ""}
            onClick={() => place(sel.map((b) => [b.id, { locked: !locked }]))}
          />
          <Tool icon={Group} label="Gruppieren" disabled={!joinable} onClick={join} />
          <Tool icon={Ungroup} label="Gruppierung aufheben" disabled={!splittable} onClick={split} />
          <i className="sep" />
          <Tool icon={Eye} label="Lösungen zeigen" className={solved ? "on" : ""} aria-pressed={solved} onClick={() => setSolved(!solved)} />
          {!leaf && zoomer}
          <Tool icon={PanelRight} label="Format und Ansicht" className={pane ? "on" : ""} aria-pressed={pane} onClick={() => setPane(!pane)} />
          <Tool icon={CircleHelp} label="Rundgang" data-tour="help" onClick={() => setTour(true)} />
          <Feedback className="ib" aria-label="Feedback">
            <MessageSquare size={16} aria-hidden />
          </Feedback>
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
          <div className="insert" role="toolbar" aria-label="Einfügen">
            {tools}
            <i className="sep" data-name="Seite" />
            <Tool icon={FilePlus} label="Neue Seite" onClick={addPage} />
            <Tool icon={FileX} label="Seite löschen" disabled={pages.length < 2} onClick={removePage} />
          </div>
        </aside>
      )}
      {side && (
        <aside className="left">
          {leaf && brand}
          <div className="head">
            Seiten
            <Tool icon={FileX} label="Seite löschen" title="Seite löschen" disabled={pages.length < 2} onClick={removePage} />
          </div>
          <div className="pages">
            {small.pages.map((_, n) => (
              <button key={n} className={n === page ? "on" : ""} aria-pressed={n === page} onClick={() => visit(n)}>
                <Thumb doc={small} k={97 / sizeOf(small, n)[0]} page={n} />
                Seite {n + 1}
              </button>
            ))}
            <button onClick={addPage}>
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

      <div className="stage">
        <div
          className="desk"
          ref={desk}
          onPointerDown={(e) => (touch.current = e.pointerType === "touch")}
          onMouseDown={(e) => {
            // Moveable keeps the press from moving the focus, so an input, or a button reached by the keys, would keep
            // Enter and Tab.
            if (!document.activeElement?.closest(".block")) (document.activeElement as HTMLElement | null)?.blur();
            if (touch.current || moveable.current!.isMoveableElement(e.target as Element)) return;
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
          onContextMenu={(e) => touch.current && e.preventDefault()}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={(e) => {
            clearTimeout(hold.current);
            // Lifting the finger after a hold is not a tap.
            if (held.current) e.preventDefault();
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
                          blur={() => inPanel.current || setEditing("")}
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
                          style={writtenStyle(b, K)}
                          onChange={(e) => style("ruling", { text: e.target.value }, "text")}
                          onKeyDown={(e) => (e.key === "Escape" || e.key === "F2") && e.currentTarget.blur()}
                          onBlur={() => setEditing("")}
                          // A line typed past the last row would scroll the others off their rows.
                          onScroll={(e) => (e.currentTarget.scrollTop = 0)}
                        />
                      ) : b.type === "table" && editing === b.id ? (
                        <textarea
                          value={b.props.cells.flat()[slot]}
                          onChange={(e) => style("table", { cells: b.props.cells.map((row, r) => row.map((text, c) => (r * row.length + c === slot ? e.target.value : text))) }, "text")}
                          onKeyDown={(e) => hop(e, b)}
                          onBlur={() => setEditing("")}
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
                    snappable={!loose}
                    keepRatio={keep}
                    snapThreshold={6}
                    isDisplaySnapDigit={false}
                    snapDirections={SIDES}
                    elementSnapDirections={SIDES}
                    elementGuidelines={rest}
                    verticalGuidelines={pageXs.map((mm) => mm * k)}
                    horizontalGuidelines={pageYs.map((mm) => mm * k)}
                    // Moveable swallows a tap on what is selected, and a group's box covers its blocks.
                    onClick={(e) => touch.current && pick(e.inputTarget, false)}
                    onClickGroup={(e) => pick(e.inputTarget, e.inputEvent.shiftKey)}
                    onDragStart={(e) => begin([e.target])}
                    onDragGroupStart={(e) => begin(e.targets)}
                    onDrag={(e) => drag([e])}
                    onDragGroup={(e) => drag(e.events)}
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
                    onRotateStart={(e) => begin([e.target])}
                    onRotateGroupStart={(e) => begin(e.targets)}
                    onRotate={(e) => twist(e.dist, e.inputEvent.shiftKey)}
                    onRotateGroup={(e) => twist(e.dist, e.inputEvent.shiftKey)}
                    // Moveable measures the box around the blocks anew: turned with them where they share an angle, else level.
                    onRotateGroupEnd={() => moveable.current!.updateRect()}
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
          <div className="dock" role="toolbar" aria-label="Einfügen">
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

      {pane && (
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
                sel={sel}
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
                  <div className="seg">
                    {DASHES.map(([dash, label, sign]) => (
                      <button key={label} className={boxes[0].props.dash === dash ? "on" : ""} aria-label={label} title={label} onClick={() => look({ dash })}>
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
                <button className={among ? "on" : ""} aria-pressed={among} disabled={free.length < 2} onClick={() => setOnPage(false)}>Auswahl</button>
                <button className={among ? "" : "on"} aria-pressed={!among} disabled={free.length < 2} onClick={() => setOnPage(true)}>Seite</button>
              </div>
              <div className="acts">
                {ALIGNS.map(([axis, at, label, icon]) => (
                  <Tool key={label} icon={icon} label={label} title={label} disabled={!free.length} onClick={() => align(axis, at)} />
                ))}
              </div>
              <h2>Verteilen</h2>
              <div className="acts">
                <button disabled={free.length < 3} onClick={() => distribute("x")}>Waagerecht</button>
                <button disabled={free.length < 3} onClick={() => distribute("y")}>Senkrecht</button>
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
            if (t === "Vorlagen") return setSide(true);
            setTab(t);
            setPane(true);
          }}
          close={() => {
            localStorage.setItem("tour", "1");
            setTour(false);
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

// A button that is its icon; the name shows when the pointer rests on it.
function Tool({ icon: Icon, label, className = "", ...rest }: { icon: LucideIcon; label: string } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button aria-label={label} {...rest} className={`ib ${className}`}>
      <Icon size={16} aria-hidden />
    </button>
  );
}
