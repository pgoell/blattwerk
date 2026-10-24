// Picking a block, with the mouse or a finger.
import type { PointerEvent, TouchEvent } from "react";
import { flushSync } from "react-dom";
import { FIELDS, boxed, dir, isLine, tied, type Block, type ImageBlock } from "../../sheet";
import { made } from "../../zahlenmauer";
import { next } from "../../cells";
import { SLOP, round, grouped, spread, centre } from "./palette";
import { useTemplates } from "./useTemplates";

export function usePick(session: ReturnType<typeof useTemplates>) {
  const over = session.over;
  const at = session.at;
  const setAt = session.setAt;
  const ids = session.ids;
  const setIds = session.setIds;
  const brush = session.brush;
  const setBrush = session.setBrush;
  const editing = session.editing;
  const setEditing = session.setEditing;
  const setStone = session.setStone;
  const setSlot = session.setSlot;
  const setReach = session.setReach;
  const clicked = session.clicked;
  const entire = session.entire;
  const setWords = session.setWords;
  const wordsKept = session.wordsKept;
  const nameWriting = session.nameWriting;
  const sheet = session.sheet;
  const multi = session.multi;
  const setMulti = session.setMulti;
  const left = session.left;
  const draft = session.draft;
  const setDraft = session.setDraft;
  const zoom = session.zoom;
  const desk = session.desk;
  const moveable = session.moveable;
  const touch = session.touch;
  const hold = session.hold;
  const held = session.held;
  const came = session.came;
  const away = session.away;
  const downOn = session.downOn;
  const owed = session.owed;
  const press = session.press;
  const spot = session.spot;
  const pinch = session.pinch;
  const pages = session.pages;
  const page = session.page;
  const blocks = session.blocks;
  const fit = session.fit;
  const cell = session.cell;
  const k = session.k;
  const zoomTo = session.zoomTo;
  const sel = session.sel;
  const free = session.free;
  const cropping = session.cropping;
  const top = session.top;
  const full = session.full;
  const change = session.change;
  const style = session.style;
  const brushDrag = session.brushDrag;
  const daub = session.daub;
  const pageOf = session.pageOf;
  const steer = session.steer;
  const cut = session.cut;
  const typed = session.typed;
  const all = session.all;
  const unit = session.unit;
  const drag = session.drag;
  const point = session.point;
  const scale = session.scale;
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

    return Object.assign(session, { pick, writable, openStone, typeStone, edit, whole, trim, done, onTouchStart, onTouchMove });
}
