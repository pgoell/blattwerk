// Dragging blocks, across the desk and onto another page.
import { flushSync } from "react-dom";
import type { OnResize, OnResizeEnd, OnRotate, OnRotateEnd, OnRotateGroup } from "react-moveable";
import { K, MARGIN, dir, isLine, type Axis, type Block } from "../../sheet";
import { hull, mirrored, swung, unfit as unfitted } from "../Format";
import { KEEP, CENTRE, round, idOf, cloned, span } from "./palette";
import { useArrange } from "./useArrange";

export function useMove(session: ReturnType<typeof useArrange>) {
  const live = session.live;
  const own = session.own;
  const at = session.at;
  const setAt = session.setAt;
  const ids = session.ids;
  const setIds = session.setIds;
  const part = session.part;
  const sheet = session.sheet;
  const right = session.right;
  const mod = session.mod;
  const desk = session.desk;
  const moveable = session.moveable;
  const tight = session.tight;
  const away = session.away;
  const owed = session.owed;
  const spot = session.spot;
  const start = session.start;
  const pivots = session.pivots;
  const dragFrom = session.dragFrom;
  const dragAt = session.dragAt;
  const pages = session.pages;
  const page = session.page;
  const blocks = session.blocks;
  const sizes = session.sizes;
  const W = session.W;
  const H = session.H;
  const fit = session.fit;
  const k = session.k;
  const from = session.from;
  const free = session.free;
  const thing = session.thing;
  const things = session.things;
  const keep = session.keep;
  const top = session.top;
  const xs = session.xs;
  const ys = session.ys;
  const update = session.update;
  const change = session.change;
  const place = session.place;
  const all = session.all;
  const unit = session.unit;
  const edge = session.edge;
  const deskShift = session.deskShift;
  const deskAuto = session.deskAuto;
  const stopDeskScroll = session.stopDeskScroll;
  const pick = (...a: any[]) => (session as Record<string, any>).pick(...a);
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
  // A fitted box sized by hand keeps that size (`unfitted`).
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
            return [b.id, { ...unfitted(b), x: round(b.x + b.w / 2 + lx * c - ly * s - w / 2), y: round(b.y + b.h / 2 + lx * s + ly * c - h / 2), w, h }];
          }
          // In a selection Moveable says where a turned block goes, on both axes whichever handle moved.
          const box = {
            ...unfitted(b),
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
  // A tap on a resize handle is no drag. Its finger area reaches into the block beside the selection,
  // so the tap is that block's (#206). Over empty paper it changes nothing. A drag still sizes.
  const resizeEnded = (e: OnResizeEnd) => {
    if (e.isDrag) {
      if (e.lastEvent) settle(e.lastEvent.direction);
      return;
    }
    const under = document.elementsFromPoint(e.clientX, e.clientY).find((el) => el.matches(".block:not(.sel)"));
    if (under) pick(under, !!e.inputEvent?.shiftKey);
  };
    return Object.assign(session, { deskStep, leave, toPageUnder, resize, keyOf, keptOf, turnThing, twist, rotate, rotated, each, spin, mirror, settle, resizeEnded });
}
