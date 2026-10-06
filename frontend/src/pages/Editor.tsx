import {
  memo,
  useDeferredValue,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type CSSProperties,
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
  FileCheck,
  FileDown,
  FileX,
  Heading,
  ImagePlus,
  LayoutTemplate,
  Lock,
  LockOpen,
  Minus,
  PanelLeft,
  PanelRight,
  Plus,
  Redo2,
  Rows3,
  SeparatorHorizontal,
  SeparatorVertical,
  Smile,
  Square,
  SquareDashedMousePointer,
  SquareSlash,
  Squircle,
  Trash2,
  Type,
  Undo2,
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
import Logo from "../components/Logo";
import Tour from "../components/Tour";
import { Draw, H, Mark, Paper, W, far, isLine, last, mathsHeight, numbers, read, textStyle, type Axis, type Block, type Box, type Corner, type Doc, type Guides, type ImageBlock, type Kind, type Page, type Range, type Sheet, type ShapeBlock } from "../sheet";
import Format from "./Format";
import { generate, newSeed } from "./Maths";

type Template = { id: number; name: string; doc: Doc };
// A new block's type and settings; `add` gives it its place.
type Fresh<B = Block> = B extends Block ? Pick<B, "type" | "props"> : never;

const MARGIN = 15;
const SIDES = { top: true, left: true, bottom: true, right: true, center: true, middle: true };
const CORNERS = ["nw", "ne", "sw", "se"];
// Snap lines on the page: the margins and the centre.
const XS = [MARGIN, W / 2, W - MARGIN];
const YS = [MARGIN, H / 2, H - MARGIN];
const SHAPES: [Kind, string, LucideIcon][] = [
  ["rect", "Rechteck", Square],
  ["rounded", "Abgerundet", Squircle],
  ["circle", "Kreis", Circle],
  ["line", "Linie", Minus],
  ["arrow", "Pfeil", ArrowRight],
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
const spread = (e: TouchEvent) => Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
const centre = (e: TouchEvent) => [(e.touches[0].clientX + e.touches[1].clientX) / 2, (e.touches[0].clientY + e.touches[1].clientY) / 2];
// The box around several blocks.
const bounds = (bs: Box[]) => {
  const [x, y] = [Math.min(...bs.map((b) => b.x)), Math.min(...bs.map((b) => b.y))];
  return { x, y, w: Math.max(...bs.map((b) => b.x + b.w)) - x, h: Math.max(...bs.map((b) => b.y + b.h)) - y };
};
// Where the box around some blocks starts and ends.
const span = (boxes: Box[], axis: Axis) => {
  const size = axis === "x" ? "w" : "h";
  return [Math.min(...boxes.map((b) => b[axis])), Math.max(...boxes.map((b) => b[axis] + b[size]))];
};
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
  const [editing, setEditing] = useState("");
  const [multi, setMulti] = useState(false);
  const [tab, setTab] = useState(TABS[0]);
  const [pane, setPane] = useState(true);
  // The panel of pages and templates starts shut where it would lie over the desk.
  const [side, setSide] = useState(() => innerWidth > 700);
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
  // Pixels per mm when the page fills the desk's width; zoom multiplies it.
  const [fit, setFit] = useState(1);
  const [zoom, setZoom] = useState(1);
  const desk = useRef<HTMLDivElement>(null);
  const sheet = useRef<HTMLDivElement>(null);
  const moveable = useRef<Moveable>(null);
  const picker = useRef<HTMLInputElement>(null);
  const mergeKey = useRef("");
  const touch = useRef(false);
  const hold = useRef(0);
  const held = useRef(false);
  const grab = useRef([0, 0]);
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
  const ns = numbers(hist.doc);
  // The built-in templates have ids below zero; the teacher's own can be deleted.
  const kept = templates.filter((t) => t.id > 0);
  const shapes = sel.filter((b) => b.type === "shape");
  // A line on its own gets a handle at each end. Moveable cannot resize a box with no height, so lines get no corner handles.
  const line = sel.length === 1 ? free.find(isLine) : undefined;
  // The picture in crop mode. The draft is dropped when the selection moves on by any way but `done`.
  const cropping = sel.length === 1 && sel[0].type === "image" && sel[0].id === draft?.id ? sel[0] : undefined;
  // Moveable collapses a group that holds a flat line, so a group with a line gets its own corner handles.
  const group = free.length > 1 && free.length === sel.length && sel.some(isLine) ? bounds(sel) : undefined;
  const top = Math.max(0, ...blocks.map((b) => b.z));
  // Snap lines: the page's, the teacher's own and the grid's, then the edges and centres of the blocks that stay put.
  const still = blocks.filter((b) => !ids.includes(b.id));
  const pageXs = [...XS, ...guides.x, ...mine.x, ...lines(cell, W)];
  const pageYs = [...YS, ...guides.y, ...mine.y, ...lines(cell, H)];
  const xs = loose ? [] : [...pageXs, ...still.flatMap((b) => [b.x, b.x + b.w / 2, b.x + b.w])];
  const ys = loose ? [] : [...pageYs, ...still.flatMap((b) => [b.y, b.y + b.h / 2, b.y + b.h])];

  useLayoutEffect(() => {
    const observer = new ResizeObserver(([entry]) => setFit(entry.contentRect.width / W));
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

  useLayoutEffect(() => {
    const area = editing ? sheet.current!.querySelector<HTMLTextAreaElement>(`[data-id="${editing}"] textarea`) : null;
    area?.focus();
    // A copy, or a text put back by undo, would start with the caret before the text.
    area?.setSelectionRange(area.value.length, area.value.length);
  }, [editing]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.target as Element).matches("textarea, input, select")) return;
      const keys: Record<string, () => void> =
        e.ctrlKey || e.metaKey
          ? { z: e.shiftKey ? redo : undo, y: redo, c: () => setClip(sel), v: paste, d: () => put(sel) }
          : { delete: remove, backspace: remove, escape: done };
      const run = keys[e.key.toLowerCase()];
      if (!run) return;
      e.preventDefault();
      run();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

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
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === type ? ({ ...b, props: { ...b.props, ...props } } as Block) : b)), key);
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
      [...from].sort((a, b) => a.z - b.z).map((b, i) => ({ ...b, id: crypto.randomUUID(), x: b.x + 5, y: b.y + 5, z: top + 1 + i })),
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

  function align(axis: Axis, at: number) {
    const size = axis === "x" ? "w" : "h";
    // One block lines up with the page, several with each other.
    const lo = free.length > 1 ? Math.min(...free.map((b) => b[axis])) : 0;
    const hi = free.length > 1 ? Math.max(...free.map((b) => b[axis] + b[size])) : axis === "x" ? W : H;
    place(free.map((b) => [b.id, { [axis]: round(lo + (hi - lo - b[size]) * at) }]));
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

  // Moveable works in whole pixels and leaves what it snaps up to two off the guide.
  // This is how far to move so that the nearest of `parts` that close lies exactly on it.
  const pull = (at: number, parts: number[], guides: number[]) =>
    parts
      .flatMap((part) => guides.map((g) => g - at - part))
      .filter((d) => Math.abs(d) < 2 / k)
      .sort((a, b) => Math.abs(a) - Math.abs(b))[0] ?? 0;
  const edge = (at: number, guides: number[]) => at + pull(at, [0], guides);

  // Moveable reports px, the document keeps mm. It reads the new size back at once, so render before returning.
  // A group snaps as one box, by its edges or its centre, and all its blocks move by the same amount.
  const drag = (events: OnDrag[]) => {
    const from = events.map((e) => blocks.find((b) => b.id === idOf(e.target))!);
    const to = events.map((e, i) => ({ ...from[i], x: e.left / k, y: e.top / k }));
    let [dx, dy] = (["x", "y"] as const).map((axis) => {
      const [lo, hi] = span(to, axis);
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
    moved && mod & CENTRE && change((bs) => [...bs, ...start.current.map((b) => ({ ...b, id: crypto.randomUUID() }))], "drag");
  const resize = (events: OnResize[]) =>
    flushSync(() =>
      place(
        events.map((e) => {
          const box = { x: round(e.drag.left / k), y: round(e.drag.top / k), w: round(e.width / k), h: round(e.height / k) };
          return [idOf(e.target), box];
        }),
        "drag",
      ),
    );
  // Moveable measures a block again after each step of a resize, so a pull would throw it off: the edges settle when it ends.
  // `dx` and `dy` say which handle moved: -1 the left or top edges, 1 the right or bottom ones.
  const settle = ([dx, dy]: number[]) =>
    place(
      free.map((b) => {
        const [x, y] = [dx < 0 ? round(edge(b.x, xs)) : b.x, dy < 0 ? round(edge(b.y, ys)) : b.y];
        const [right, bottom] = [dx > 0 ? edge(b.x + b.w, xs) : b.x + b.w, dy > 0 ? edge(b.y + b.h, ys) : b.y + b.h];
        return [b.id, { x, y, w: round(right - x), h: round(bottom - y) }];
      }),
      "drag",
    );
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
    if (el.closest(".end, .rule, .crop")) return;
    // A press beside the picture ends its crop.
    done();
    const id = el.closest<HTMLElement>(".block")?.dataset.id;
    const more = shift || multi;
    const to = pageOf(el);
    if (to !== page) {
      // A press on another page puts it in use, and the selection starts over. That page's Moveable is a new one.
      flushSync(() => {
        setAt(to);
        setIds(id ? [id] : []);
      });
      if (id && press) moveable.current!.dragStart(press);
    } else if (!id) {
      if (shift) return;
      setIds([]);
      setMulti(false);
    } else if (ids.includes(id)) {
      if (more) setIds(ids.filter((i) => i !== id));
      // On touch a second tap on a text block edits it and on a picture crops it; a mouse double-clicks.
      else if (touch.current) edit(id);
      // Level lines in a row leave Moveable's group area no height, so a press on one lands here.
      else if (press && ids.length > 1) moveable.current!.dragStart(press);
    } else {
      setIds(more ? [...ids, id] : [id]);
      if (press) moveable.current!.waitToChangeTarget().then(() => moveable.current!.dragStart(press));
    }
  }
  function edit(id?: string) {
    if (!id || free.length !== 1 || free[0].id !== id) return;
    if (free[0].type === "text") setEditing(id);
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
    const at = point(e);
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
    const box = { x: round(full.x + l * full.w), y: round(full.y + t * full.h), w: round(full.w * (1 - l - r)), h: round(full.h * (1 - t - b)) };
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
    const id = (e.target as Element).closest<HTMLElement>(".block")?.dataset.id;
    if (!id) return;
    const to = pageOf(e.target as Element);
    hold.current = window.setTimeout(() => {
      held.current = true;
      setMulti(true);
      setAt(to);
      setIds((now) => (to !== page ? [id] : now.includes(id) ? now : [...now, id]));
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
  return (
    <main className="editor" onPointerDown={() => (mergeKey.current = "")}>
      <header>
        <div className="top">
          <Link to="/" className="brand" aria-label="Meine Blätter" title="Meine Blätter">
            <Logo />
            <ChevronLeft size={16} aria-hidden />
          </Link>
          <Tool icon={PanelLeft} label="Seiten und Vorlagen" className={side ? "on" : ""} aria-pressed={side} onClick={() => setSide(!side)} />
          <input type="text" aria-label="Titel" placeholder="Unbenanntes Blatt" maxLength={80} value={title} onChange={(e) => setTitle(e.target.value)} />
          <span className="hint" role="status">
            {!dirty ? "Gespeichert" : tries || clash ? "Nicht gespeichert" : "Speichert …"}
          </span>
          <Tool icon={Undo2} label="Rückgängig" data-tour="undo" disabled={!hist.past.length} onClick={undo} />
          <Tool icon={Redo2} label="Wiederholen" disabled={!hist.future.length} onClick={redo} />
          <i className="sep" />
          <Tool icon={Copy} label="Kopieren" disabled={!sel.length} onClick={() => setClip(sel)} />
          <Tool icon={ClipboardPaste} label="Einfügen" disabled={!clip.length} onClick={paste} />
          <Tool icon={CopyPlus} label="Duplizieren" disabled={!sel.length} onClick={() => put(sel)} />
          <Tool icon={Trash2} label="Löschen" disabled={!sel.length} onClick={remove} />
          <Tool
            icon={locked ? LockOpen : Lock}
            label={locked ? "Entsperren" : "Sperren"}
            disabled={!sel.length}
            className={locked ? "on" : ""}
            onClick={() => place(sel.map((b) => [b.id, { locked: !locked }]))}
          />
          <i className="sep" />
          <Tool icon={Eye} label="Lösungen zeigen" className={solved ? "on" : ""} aria-pressed={solved} onClick={() => setSolved(!solved)} />
          <Tool icon={ZoomOut} label="Kleiner" onClick={() => setZoom(Math.max(0.25, zoom / 1.25))} />
          {/* The page's size on the screen against its size on paper. */}
          <button className="zoom" title="Seitenbreite" onClick={() => setZoom(1)}>
            {Math.round((k * 2540) / 96)} %
          </button>
          <Tool icon={ZoomIn} label="Größer" onClick={() => setZoom(Math.min(4, zoom * 1.25))} />
          <Tool icon={PanelRight} label="Format und Ansicht" className={pane ? "on" : ""} aria-pressed={pane} onClick={() => setPane(!pane)} />
          <Tool icon={CircleHelp} label="Rundgang" data-tour="help" onClick={() => setTour(true)} />
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

      {side && (
        <aside className="left">
          <div className="head">
            Seiten
            <Tool icon={FileX} label="Seite löschen" title="Seite löschen" disabled={pages.length < 2} onClick={removePage} />
          </div>
          <div className="pages">
            {small.pages.map((_, n) => (
              <button key={n} className={n === page ? "on" : ""} aria-pressed={n === page} onClick={() => visit(n)}>
                <Thumb doc={small} k={97 / W} page={n} />
                Seite {n + 1}
              </button>
            ))}
            <button onClick={addPage}>
              <i>
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
          onMouseDown={(e) => touch.current || moveable.current!.isMoveableElement(e.target as Element) || pick(e.target as Element, e.shiftKey, e.nativeEvent)}
          onClick={(e) => touch.current && !moveable.current!.isMoveableElement(e.target as Element) && pick(e.target as Element, false)}
          onDoubleClick={(e) => edit((e.target as Element).closest<HTMLElement>(".block")?.dataset.id)}
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
              style={{ width: W * k, height: H * k, "--cell": `${cellOf(p) * k}px` } as CSSProperties}
            >
              {p.blocks.map((b) => (

                <div
                  key={b.id}
                  data-id={b.id}
                  className={ids.includes(b.id) ? "block sel" : "block"}
                  style={{ left: b.x * k, top: b.y * k, width: b.w * k, height: b.h * k, zIndex: b === cropping ? 2998 : b.z }}
                >
                  {b.type === "text" ? (
                    <textarea
                      value={b.props.text}
                      placeholder="Text"
                      readOnly={editing !== b.id}
                      style={textStyle(b.props, k)}
                      onChange={(e) => style("text", { text: e.target.value }, "text")}
                      onKeyDown={(e) => e.key === "Escape" && e.currentTarget.blur()}
                      onBlur={() => setEditing("")}
                    />
                  ) : (
                    <Draw block={b} k={k} solved={solved} />
                  )}
                  <Mark block={b} k={k} n={ns.get(b.id)} />
                  {b === cropping && <Crop block={cropping} box={whole(cropping)} cut={draft!.cut} k={k} grip={grip} trim={trim} />}
                  {b === line &&
                    [false, true].map((end) => (
                      <i
                        key={+end}
                        className={end && line.props.kind === "arrow" ? "end tip" : "end"}
                        style={{ left: far(line, 1, end) ? b.w * k : 0, top: far(line, 0, end) ? b.h * k : 0 }}
                        onPointerDown={grip}
                        onPointerMove={(e) => stretch(e, line, end)}
                        onLostPointerCapture={() => setGuide([])}
                      />
                    ))}
                </div>
              ))}
              {/* The sheet's guide lines lie on every page; a page's own are drawn dotted. */}
              {[undefined, n].flatMap((at) =>
                (["x", "y"] as const).flatMap((axis) =>
                  (at === undefined ? guides : (p.guides ?? NONE))[axis].map((mm, i) => (
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
                        onLostPointerCapture={() => setGuide([])}
                      />
                    ))}
                  <Moveable
                    ref={moveable}
                    // In crop mode the frame's handles stand in for Moveable's.
                    target={cropping ? [] : targets}
                    draggable={free.length === sel.length}
                    resizable={free.length === sel.length && !sel.some(isLine)}
                    renderDirections={CORNERS}
                    origin={false}
                    checkInput
                    snappable={!loose}
                    // A picture and a symbol always keep their shape.
                    keepRatio={(mod & KEEP) > 0 || sel.some((b) => b.type === "image" || b.type === "symbol")}
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
                    onDragStart={(e) => ((e.inputEvent.target as Element).closest(".end") ? e.stopDrag() : begin([e.target]))}
                    onDragGroupStart={(e) => begin(e.targets)}
                    onDrag={(e) => drag([e])}
                    onDragGroup={(e) => drag(e.events)}
                    onDragEnd={(e) => leave(e.isDrag)}
                    onDragGroupEnd={(e) => leave(e.isDrag)}
                    // Ctrl resizes about the centre.
                    onBeforeResize={(e) => mod & CENTRE && e.setFixedDirection([0, 0])}
                    onBeforeResizeGroup={(e) => mod & CENTRE && e.setFixedDirection([0, 0])}
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
        <div className="dock" role="toolbar" aria-label="Einfügen">
          <Tool
            icon={SquareDashedMousePointer}
            label="Mehrere"
            data-tour="multi"
            className={multi ? "on" : ""}
            aria-pressed={multi}
            onClick={() => setMulti(!multi)}
          />
          <i className="sep" />
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
          <i className="sep" />
          <Tool icon={Rows3} label="Lineatur" onClick={() => add(180, 60, { type: "ruling", props: { kind: "l1", color: "#555555" } })} />
          <Tool icon={UserPen} label="Namenszeile" onClick={() => add(180, 10, { type: "name", props: {} })} />
          <Tool icon={SquareSlash} label="Punkte" onClick={() => add(40, 12, { type: "points", props: { max: 10 } })} />
          <Tool icon={Calculator} label="Rechnen" data-tour="maths" onClick={addMaths} />
          <i className="sep" />
          {SHAPES.map(([kind, label, icon]) => (
            <Tool
              key={kind}
              icon={icon}
              label={label}
              onClick={() =>
                add(kind === "circle" ? 40 : 60, kind === "line" || kind === "arrow" ? 0 : 40, {
                  type: "shape",
                  props: { kind, fill: "none", stroke: "#222222", strokeWidth: 0.5 },
                })
              }
            />
          ))}
        </div>
      </div>
      {/* The drag box is for a mouse on empty desk; a finger there scrolls. */}
      <Selecto
        dragContainer=".desk"
        selectableTargets={[".block"]}
        hitRate={0}
        selectByClick={false}
        onDragStart={(e) => {
          const el = e.inputEvent.target as Element;
          if (e.inputEvent.type === "touchstart" || el.closest(".block, .end, .rule") || moveable.current!.isMoveableElement(el)) e.stop();
        }}
        // The box selects on the page in use, which the press that began it has set.
        onSelectEnd={(e) => setIds((now) => [...new Set([...now, ...e.selected.filter((el) => sheet.current!.contains(el)).map(idOf)])])}
      />

      {pane && (
        <aside className="panel">
          <div className="tabs" role="tablist">
            {TABS.map((t) => (
              <button key={t} role="tab" data-tour={t} aria-selected={tab === t} onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
          </div>
          {tab === "Format" && !sel.length && <p className="hint">Wähle etwas auf dem Blatt aus, um es zu formatieren.</p>}
          {tab === "Format" && sel.length > 0 && (
            <>
              <p className="what">
                {sel.length > 1 ? `${sel.length} Felder` : NAMES[sel[0].type]}
                <small>
                  {round(bounds(sel).w).toLocaleString("de")} × {round(bounds(sel).h).toLocaleString("de")} mm
                </small>
              </p>
              <Format
                sel={sel}
                style={style}
                place={place}
                cropping={!!cropping}
                crop={sel.length === 1 && free[0]?.type === "image" ? () => (cropping ? done() : edit(free[0].id)) : undefined}
              />
              {shapes.length > 0 && (
                <>
                  <h2>Form</h2>
                  <label>
                    Füllung
                    <input
                      type="color"
                      value={shapes[0].props.fill === "none" ? "#ffffff" : shapes[0].props.fill}
                      onChange={(e) => style("shape", { fill: e.target.value }, "fill")}
                    />
                  </label>
                  <button className="wide" disabled={shapes[0].props.fill === "none"} onClick={() => style("shape", { fill: "none" })}>Keine Füllung</button>
                  <label>
                    Rand
                    <input type="color" value={shapes[0].props.stroke} onChange={(e) => style("shape", { stroke: e.target.value }, "stroke")} />
                  </label>
                  <label>
                    Randstärke
                    <input
                      type="range"
                      min={0.25}
                      max={3}
                      step={0.25}
                      value={shapes[0].props.strokeWidth}
                      onChange={(e) => style("shape", { strokeWidth: +e.target.value }, "strokeWidth")}
                    />
                  </label>
                </>
              )}
              <h2>Ausrichten</h2>
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
              <h2>Ebene</h2>
              <div className="acts">
                <button onClick={() => place(sel.map((b) => [b.id, { z: top + 1 }]))}>Nach vorn</button>
                <button onClick={() => place(sel.map((b) => [b.id, { z: Math.min(0, ...blocks.map((o) => o.z)) - 1 }]))}>Nach hinten</button>
              </div>
            </>
          )}
          {tab === "Ansicht" && (
            <>
              <h2>Raster und Hilfslinien für</h2>
              <div className="seg">
                <button className={own ? "" : "on"} aria-pressed={!own} onClick={() => setOwn(false)}>Alle Seiten</button>
                <button className={own ? "on" : ""} aria-pressed={own} onClick={() => setOwn(true)}>Nur diese Seite</button>
              </div>
              {/* A page's own grid stands in for the sheet's; "Wie Blatt" gives the page the sheet's again. */}
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
  return (
    <div className="crop" style={{ left: (box.x - block.x) * k, top: (box.y - block.y) * k, width: box.w * k, height: box.h * k }}>
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
