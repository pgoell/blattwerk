// Adding, removing, copying and reordering pages.
import { flushSync } from "react-dom";
import { redone, undone } from "../../history";
import { MARGIN, sizeOf, type Block } from "../../sheet";
import { next } from "../../cells";
import { hull } from "../Format";
import { round, cloned } from "./palette";
import { useBrush } from "./useBrush";

export function usePages(session: ReturnType<typeof useBrush>) {
  const hist = session.hist;
  const at = session.at;
  const setAt = session.setAt;
  const setChosen = session.setChosen;
  const setHaul = session.setHaul;
  const setIds = session.setIds;
  const rest = session.rest;
  const slot = session.slot;
  const setReach = session.setReach;
  const sheet = session.sheet;
  const back = session.back;
  const desk = session.desk;
  const strip = session.strip;
  const tug = session.tug;
  const press = session.press;
  const auto = session.auto;
  const dragged = session.dragged;
  const start = session.start;
  const pages = session.pages;
  const page = session.page;
  const chosenNow = session.chosenNow;
  const choiceOf = session.choiceOf;
  const blocks = session.blocks;
  const last = session.last;
  const from = session.from;
  const ns = session.ns;
  const across = session.across;
  const down = session.down;
  const update = session.update;
  const steered = session.steered;
  const scrollHeld = session.scrollHeld;
  const lagged = session.lagged;
  const show = session.show;
  const seek = (...a: any[]) => (session as Record<string, any>).seek(...a);
  const done = (...a: any[]) => (session as Record<string, any>).done(...a);
  const unit = (...a: any[]) => (session as Record<string, any>).unit(...a);
  const stretch = (...a: any[]) => (session as Record<string, any>).stretch(...a);
  const all = (...a: any[]) => (session as Record<string, any>).all(...a);
  const thumbMenu = (...a: any[]) => (session as Record<string, any>).thumbMenu(...a);
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
    return Object.assign(session, { undo, redo, addPage, visit, lay, removePages, movePages, copyPages, aim, landing, scrollEdge, scrollStep, quit, release });
}
