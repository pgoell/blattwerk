// Text and tables growing to the words they hold.
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { MARGIN, boxed, lowest, sizeOf, tall, fitWidth, type Block, type Box, type Page } from "../../sheet";
import { heightsOf } from "../../cells";
import { grown } from "../../insert";
import { useSelection } from "./useSelection";

export function useTextFit(session: ReturnType<typeof useSelection>) {
  const hist = session.hist;
  const setHist = session.setHist;
  const own = session.own;
  const at = session.at;
  const ids = session.ids;
  const setTargets = session.setTargets;
  const setRest = session.setRest;
  const editing = session.editing;
  const sheet = session.sheet;
  const leaf = session.leaf;
  const left = session.left;
  const right = session.right;
  const room = session.room;
  const setRoom = session.setRoom;
  const high = session.high;
  const setHigh = session.setHigh;
  const fitted = session.fitted;
  const stage = session.stage;
  const desk = session.desk;
  const moveable = session.moveable;
  const tight = session.tight;
  const sink = session.sink;
  const pages = session.pages;
  const page = session.page;
  const blocks = session.blocks;
  const W = session.W;
  const H = session.H;
  const fit = session.fit;
  const k = session.k;
  const sel = session.sel;
  const kept = session.kept;
  const frame = session.frame;
  const across = session.across;
  const down = session.down;
  const top = session.top;
  const look = (...a: any[]) => (session as Record<string, any>).look(...a);
  const fitPage = (...a: any[]) => (session as Record<string, any>).fitPage(...a);
  const snug = (...a: any[]) => (session as Record<string, any>).snug(...a);
  const cut = (...a: any[]) => (session as Record<string, any>).cut(...a);
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
    const fit = () =>
      stage.current!.parentElement!.style.setProperty("--dock", `${Math.max(...docks.map((el) => el.offsetHeight))}px`);
    // The observer reports the height a frame later. Until that report the sheet keeps the room of one row, and a
    // dock that has already wrapped lies over the sheet scrolled to its end (#408).
    if (docks.length) fit();
    const observer = new ResizeObserver(fit);
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
  // A fitted box's width and height, in mm: as wide as its longest line, up to `cap`, where its text breaks. The width
  // is rounded up with a little slack, so that the print does not break the last word.
  const fitSize = (b: Block, cap: number) => {
    const frame = sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] > :is(.frame, .table)`);
    if (!frame) return undefined;
    const block = frame.parentElement!;
    const was = block.style.transform;
    block.style.transform = "none";
    const [ownW, ownH] = [frame.style.width, frame.style.height];
    frame.style.width = "max-content";
    let w = Math.round((Math.ceil((frame.getBoundingClientRect().width / k) * 10) / 10 + 0.2) * 100) / 100;
    if (w > cap) {
      frame.style.width = `${cap * k}px`;
      w = cap;
    }
    frame.style.height = "auto";
    const h = Math.ceil((frame.getBoundingClientRect().height / k) * 100) / 100;
    [frame.style.width, frame.style.height] = [ownW, ownH];
    block.style.transform = was;
    // An empty text keeps 10 mm, as a new box does.
    return { w: frame.textContent?.trim() ? w : 10, h };
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
      // A fitted box takes its text's width and height, shrinking too, and keeps the edge its words are aligned to.
      // A locked box keeps its place and size, and a linked text grows on with its list: neither fits.
      if (shape?.fit === true && !b.locked && shape.list !== true) {
        const at = b.angle || shape.align === "center" ? 0.5 : shape.align === "right" ? 1 : 0;
        // The room to the margins from the edge that stays: a box that keeps its middle widens to both sides.
        const W = sizeOf(hist.doc, page)[0];
        const [left, right] = [b.x + b.w * at - MARGIN, W - MARGIN - b.x - b.w * at];
        const cap = Math.max(10, at === 0 ? right : at === 1 ? left : 2 * Math.min(left, right));
        const m = fitSize(b, cap);
        if (!m) continue;
        const widened = { ...b, ...fitWidth(b, m.w, at) };
        // It stops at the page's foot, as a text that grows does.
        const h = Math.min(m.h, Math.max(widened.h, footTop(widened, H)));
        if (Math.abs(m.w - b.w) <= 0.005 && Math.abs(h - b.h) <= 0.005) continue;
        grown.set(b.id, { ...fitWidth(b, m.w, at), ...tall(widened, h) });
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
    return Object.assign(session, { full, setFull, cramped, setCramped, panelSized, heldIds, setHeldIds, pickedKey, stopped, footTop, atFoot, shrinks, natural, fitSize, overfit, wrote });
}
