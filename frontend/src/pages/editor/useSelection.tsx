// The blocks in hand, and the page they stand on.
import { useDeferredValue, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { OnDrag } from "react-moveable";
import type { Step } from "../../history";
import { FIELDS, MARGIN, pageNumbersOf, wordsIn, isLine, numbers, read, sizeOf, type Block, type Box, type Doc, type NameBlock, type Page, type PageNumbers, type RulingBlock, type TextBlock } from "../../sheet";
import { unshown } from "../../words";
import { next } from "../../cells";
import { bounds, frameOf, hull, outline } from "../Format";
import type { Breaks } from "../../syllables";
import { CORNERS, takes, NONE, KEEP, LOOSE, lines, spread } from "./palette";
import { useLayoutState } from "./useLayoutState";

export function useSelection(session: ReturnType<typeof useLayoutState>) {
  const hist = session.hist;
  const help = session.help;
  const title = session.title;
  const saver = session.saver;
  const own = session.own;
  const at = session.at;
  const chosen = session.chosen;
  const ids = session.ids;
  const rest = session.rest;
  const slot = session.slot;
  const onPage = session.onPage;
  const left = session.left;
  const mod = session.mod;
  const templates = session.templates;
  const draft = session.draft;
  const room = session.room;
  const zoom = session.zoom;
  const setZoom = session.setZoom;
  const zoomNow = session.zoomNow;
  const sizeNow = session.sizeNow;
  const fitted = session.fitted;
  const update = (...a: any[]) => (session as Record<string, any>).update(...a);
  const change = (...a: any[]) => (session as Record<string, any>).change(...a);
  const place = (...a: any[]) => (session as Record<string, any>).place(...a);
  const shown = (...a: any[]) => (session as Record<string, any>).shown(...a);
  const turn = (...a: any[]) => (session as Record<string, any>).turn(...a);
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
  const tug = useRef<{ from: number; x: number; y: number; slot?: number; held?: boolean; left?: boolean; ctrl?: boolean }>(undefined);
  const press = useRef(0);
  // The panel scrolls while a drag rests near its edge: the frame that does it, its speed and the pointer.
  const auto = useRef({ frame: 0, speed: 0, x: 0, y: 0, last: 0, rest: 0 });
  // Set by a drag, for the click that follows it.
  const dragged = useRef(false);
  // Set when Ctrl+click opened the pages' menu, so the click of that press does not also change the choice.
  const ctrlMenu = useRef(false);
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
  const helping = help ? pages[help.page]?.blocks.find((b): b is TextBlock => b.type === "text" && b.id === help.id) : undefined;
  // Each page's width and height in mm.
  const sizes = pages.map((_, n) => sizeOf(hist.doc, n));
  sizeNow.current = sizes;
  // A mend holds for the word in every block of the sheet, in one step: it stands in the sheet, and in the block it was
  // made in, which takes it along when copied; the other blocks' own entries for it go. Counts undefined takes the word
  // back to the module's own split everywhere.
  // `keys` are the word's key and its old key: the panel has the splitter that makes them, the editor loads none.
  function mendWord(keys: string[], counts: number[] | undefined, id: string) {
    const rest = (own?: Breaks) => Object.fromEntries(Object.entries(own ?? {}).filter(([key]) => !keys.includes(key)));
    update((doc: Doc) => {
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
    update((doc: Doc) => ({ ...doc, pageNumbers: next }));
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
  zoomNow.current = zoom;
  // A zoom by hand: the buttons, the wheel, a pinch. It stays between a quarter and four times the page's width.
  const zoomTo = (z: number) => {
    fitted.current = false;
    const next = Math.min(4, Math.max(0.25, z));
    // Ahead of the render, so a second notch in the same turn stacks on this one.
    zoomNow.current = next;
    setZoom(next);
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
  // The words of the picked name lines, when only name lines are picked: the panel shows a checkbox for each.
  const nameFields = free.length > 0 && free.every((b) => b.type === "name") ? ((free[0] as NameBlock).props.fields ?? FIELDS) : [];
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

    return Object.assign(session, { mergeKey, ahead, grasp, tight, sink, touch, cover, hold, held, came, away, downOn, owed, strip, tug, press, auto, dragged, ctrlMenu, grab, adjusting, spot, start, pivots, dragFrom, dragAt, pinch, pages, guides, grid, learnt, lineaturen, crowded, page, chosenNow, choiceOf, blocks, helping, sizes, mendWord, folio, numbering, W, H, widest, fit, last, small, cellOf, cell, mine, dirty, loose, k, zoomTo, sel, lock, setLock, from, setFrom, free, thing, things, among, sizable, ns, kept, builtIn, boxes, fill, nameFields, stroke, source, rulers, line, table, cropping, oneGroup, ownFrame, mixed, frame, turnedLine, group, shaped, keep, across, down, handles, top, still, pageXs, pageYs, xs, ys });
}
