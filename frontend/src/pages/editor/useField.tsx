// The open field, a picture's crop, and where the caret goes.
import { useEffect, useLayoutEffect, useRef, type PointerEvent } from "react";
import { innerOf, boxed, dir, fitOf, lowest, sizeOf, tall, type Block, type Page } from "../../sheet";
import { anchorOf, rectOf } from "../../cells";
import { drawn, outline } from "../Format";
import { round, idOf } from "./palette";
import { useTextFit } from "./useTextFit";

export function useField(session: ReturnType<typeof useTextFit>) {
  const over = session.over;
  const hist = session.hist;
  const live = session.live;
  const setHist = session.setHist;
  const at = session.at;
  const editing = session.editing;
  const setEditing = session.setEditing;
  const finger = session.finger;
  const setGrips = session.setGrips;
  const slot = session.slot;
  const setSlot = session.setSlot;
  const reach = session.reach;
  const setReach = session.setReach;
  const cellDrag = session.cellDrag;
  const laid = session.laid;
  const setLaid = session.setLaid;
  const caret = session.caret;
  const clicked = session.clicked;
  const entire = session.entire;
  const words = session.words;
  const wordsKept = session.wordsKept;
  const nameWriting = session.nameWriting;
  const sheet = session.sheet;
  const side = session.side;
  const fits = session.fits;
  const desk = session.desk;
  const tight = session.tight;
  const pages = session.pages;
  const grid = session.grid;
  const page = session.page;
  const blocks = session.blocks;
  const H = session.H;
  const last = session.last;
  const cell = session.cell;
  const sel = session.sel;
  const kept = session.kept;
  const line = session.line;
  const table = session.table;
  const across = session.across;
  const down = session.down;
  const top = session.top;
  const setCramped = session.setCramped;
  const panelSized = session.panelSized;
  const setHeldIds = session.setHeldIds;
  const stopped = session.stopped;
  const footTop = session.footTop;
  const atFoot = session.atFoot;
  const overfit = session.overfit;
  const wrote = session.wrote;
  const cut = (...a: any[]) => (session as Record<string, any>).cut(...a);
  const scale = (...a: any[]) => (session as Record<string, any>).scale(...a);
  const turn = (...a: any[]) => (session as Record<string, any>).turn(...a);
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
  // Chrome counts a drag on `touch-action: none` as a scroll it did not run, and the next tap then
  // ends in a touchend with no click (#723). The first move can still be cancelled, and cancelling
  // it says the drag was the page's, so that tap clicks. React's listener is passive and could not.
  useLayoutEffect(() => {
    const root = sheet.current;
    if (!root) return;
    const stop = (e: globalThis.TouchEvent) => {
      if (e.cancelable) e.preventDefault();
    };
    const handles = [...root.querySelectorAll<HTMLElement>(".cell-handle")];
    for (const el of handles) el.addEventListener("touchmove", stop, { passive: false });
    return () => {
      for (const el of handles) el.removeEventListener("touchmove", stop);
    };
  });
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
    const kept = words.map((w, i) => ({ word: w.trim(), i })).filter((f) => f.word);
    const fields = kept.map((f) => f.word);
    if (!fields.length || fields.join("\n") === wordsKept.current) return;
    const block = live.current.doc.pages[line.n]?.blocks.find((b) => b.id === line.id);
    if (block?.type !== "name") return;
    // A hidden field keeps its word, but its index moves when a word before it drops out with its field.
    const hidden = (block.props.hidden ?? []).flatMap((h) => {
      const at = kept.findIndex((f) => f.i === h);
      return at < 0 ? [] : [at];
    });
    // With every shown word emptied only hidden fields are left: they show again, as no line shows nothing.
    const props = { ...block.props, fields, hidden: hidden.length && hidden.length < fields.length ? hidden : undefined };
    turn((p: Page) => ({ ...p, blocks: p.blocks.map((b) => (b.id === line.id ? ({ ...b, props } as Block) : b)) }), "", line.n);
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

    return Object.assign(session, { gripFixed, gripDown, gripMove, gripUp });
}
