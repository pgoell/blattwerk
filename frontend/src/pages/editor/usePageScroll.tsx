// Which page fills the desk, and keeping it in view.
import { useEffect, useRef, type KeyboardEvent as Key } from "react";
import type { Box } from "../../sheet";
import { round, span, step } from "./palette";
import { usePages } from "./usePages";

export function usePageScroll(session: ReturnType<typeof usePages>) {
  const setAt = session.setAt;
  const ids = session.ids;
  const editing = session.editing;
  const cellDrag = session.cellDrag;
  const sheet = session.sheet;
  const right = session.right;
  const desk = session.desk;
  const strip = session.strip;
  const tug = session.tug;
  const press = session.press;
  const pages = session.pages;
  const page = session.page;
  const choiceOf = session.choiceOf;
  const blocks = session.blocks;
  const sizes = session.sizes;
  const W = session.W;
  const H = session.H;
  const k = session.k;
  const ns = session.ns;
  const boxes = session.boxes;
  const down = session.down;
  const latest = session.latest;
  const steered = session.steered;
  const scrollHeld = session.scrollHeld;
  const lagged = session.lagged;
  const removePages = session.removePages;
  const movePages = session.movePages;
  const copyPages = session.copyPages;
  const clippedPages = (...a: any[]) => (session as Record<string, any>).clippedPages(...a);
  const storePages = (...a: any[]) => (session as Record<string, any>).storePages(...a);
  const cutPages = (...a: any[]) => (session as Record<string, any>).cutPages(...a);
  const pastePages = (...a: any[]) => (session as Record<string, any>).pastePages(...a);
  const copy = (...a: any[]) => (session as Record<string, any>).copy(...a);
  const shown = (...a: any[]) => (session as Record<string, any>).shown(...a);
  const same = (...a: any[]) => (session as Record<string, any>).same(...a);
// On a thumbnail Ctrl with an arrow moves its page by one place, with Shift to the start or the end, and Ctrl+D
  // copies it. The focus follows the page.
  function pageKey(e: Key, n: number) {
    // Delete and Backspace take the thumbnail's page away, never the picked blocks, and the last page stays.
    if (/^(Delete|Backspace)$/.test(e.key) && !(e.ctrlKey || e.metaKey || e.altKey || e.shiftKey)) {
      e.preventDefault();
      e.stopPropagation();
      // A page being dragged stays: the drop would look for it.
      const ns = choiceOf(n);
      if (ns.length >= pages.length || tug.current) return;
      removePages(ns);
      // The thumbnail in the place of the first page gone, or the last one left.
      strip.current!.querySelector<HTMLElement>(`[data-thumb="${Math.min(Math.min(...ns), pages.length - ns.length - 1)}"]`)!.focus();
      return;
    }
    if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
    // Copy, cut and paste of pages: the block ones of the sheet must not also run.
    // Ctrl+V pastes pages only when they are the newest copy; else the sheet's paste takes it, as before.
    if (/^[cxv]$/i.test(e.key) && !e.shiftKey && !(/^v$/i.test(e.key) && !clippedPages().pages.length)) {
      e.preventDefault();
      e.stopPropagation();
      const ns = choiceOf(n);
      if (/^c$/i.test(e.key)) storePages(ns);
      else if (/^x$/i.test(e.key)) {
        if (ns.length >= pages.length) return;
        cutPages(ns);
        // As after Delete: the thumbnail in the place of the first page gone keeps the keys.
        strip.current!.querySelector<HTMLElement>(`[data-thumb="${Math.min(Math.min(...ns), pages.length - ns.length - 1)}"]`)!.focus();
      } else {
        pastePages(n);
        strip.current!.querySelector<HTMLElement>(`[data-thumb="${n + 1}"]`)?.focus();
      }
      return;
    }
    const ns = choiceOf(n);
    const first = ns[0];
    const count = ns.length;
    const copy = /^d$/i.test(e.key) && !e.shiftKey;
    const to = copy
      ? Math.max(...ns) + 1
      : e.key === "ArrowUp"
        ? (e.shiftKey ? 0 : Math.max(0, first - 1))
        : e.key === "ArrowDown"
          ? (e.shiftKey ? pages.length - count : Math.min(pages.length - count, first + 1))
          : -1;
    if (to < 0) return;
    // The window's own Ctrl+D copies blocks, and Chrome's sets a bookmark.
    e.preventDefault();
    e.stopPropagation();
    if (copy) copyPages(ns);
    else movePages(ns, to);
    strip.current!.querySelector<HTMLElement>(`[data-thumb="${to}"]`)!.focus();
  }

  // The page an element lies on; beside the pages, the one in use.
  const pageOf = (el: Element) => +(el.closest<HTMLElement>(".sheet")?.dataset.page ?? page);
  // How far down the page in use, or page `n`, in mm, a point of the desk's view lies.
  const seen = (down: number, n?: number) => {
    const on = n === undefined ? sheet.current! : desk.current!.querySelector(`[data-page="${n}"]`)!;
    return (desk.current!.getBoundingClientRect().top + down - on.getBoundingClientRect().top) / k;
  };
  const steer = (ms = 500) => (steered.current = performance.now() + ms);
  // Any other scroll (a zoom about the pointer, a page key with a block picked, a script) that leaves the page in use
  // out of view hands it on to the page in view once the desk rests, so a new block never lands out of sight (#805).
  // A scroll of the editor's own ends on the page in use, so it keeps it.
  const resting = useRef(0);
  useEffect(() => () => clearTimeout(resting.current), []);
  function follow() {
    clearTimeout(resting.current);
    // The editor's own scroll has brought the page in use into view: from here on it counts as any other.
    if (heading.current && !lost()) heading.current = 0;
    // A drag that scrolls the desk at its edge keeps its page until the pointer is up.
    if (performance.now() > steered.current && !scrollHeld.current) return void (resting.current = window.setTimeout(() => calm(() => strayNow.current()), 150));
    if (editing) lagged.current = true;
    else inView();
  }
  // Whether no part of the page in use lies in the desk's view.
  function lost() {
    const [on, view] = [sheet.current?.getBoundingClientRect(), desk.current!.getBoundingClientRect()];
    return !on || on.bottom <= view.top || on.top >= view.bottom || on.right <= view.left || on.left >= view.right;
  }
  // A picked block keeps its page, so the arrow keys still nudge it; a new block finds the page in view by `looked`.
  // The editor's own smooth scroll to the page in use: until it is there, the page in use lies out of view on purpose.
  const heading = useRef(0);
  function seek() {
    heading.current = performance.now() + 1500;
    sheet.current!.scrollIntoView({ behavior: "smooth" });
  }
  const strayed = () => lost() && performance.now() > heading.current;
  // A picked block keeps its page, so the arrow keys still nudge it; a new block finds the page in view by `looked`.
  // A text being typed is picked too, so it keeps its page here as well. The timer runs the stray of the latest
  // render: a pick dropped meanwhile counts.
  function stray() {
    if (!strayed() || ids.length) return;
    inView();
  }
  const strayNow = useRef(stray);
  strayNow.current = stray;
  // The page a new block goes to: the page in use, or the page in view when the page in use is out of sight.
  const looked = () => (strayed() ? inView() : page);
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
    return best;
  }

  // Notes page `was` for what the server sends later, and gives a way to look it up then. The pages may have changed
  // by that time: the page is found where it is now; one changed since is known by a block it still holds, or keeps
  // its number while the pages are as many as before. For a page that is gone, the page in use stands in.
  function mark(was = looked()) {
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
    return Object.assign(session, { pageKey, pageOf, seen, steer, resting, follow, lost, heading, seek, strayed, stray, strayNow, looked, inView, mark, land, pressed, due, calm });
}
