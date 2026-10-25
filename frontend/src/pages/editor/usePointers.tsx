// The wheel, a swipe in from the edge, and the keys held during a drag.
import { useEffect } from "react";
import { flushSync } from "react-dom";
import { api } from "../../api";
import { attempt } from "../../fault";
import { attach, open, set, signed } from "../../saves";
import { next } from "../../cells";
import type { Template } from "./palette";
import { THUMBS, SLOP, KEEP, CENTRE, LOOSE, APPLE } from "./palette";
import { useKeyCommands } from "./useKeyCommands";

export function usePointers(session: ReturnType<typeof useKeyCommands>) {
  const file = session.file;
  const hist = session.hist;
  const live = session.live;
  const title = session.title;
  const named = session.named;
  const ids = session.ids;
  const sheet = session.sheet;
  const drawers = session.drawers;
  const drawer = session.drawer;
  const swipe = session.swipe;
  const showLeft = session.showLeft;
  const showRight = session.showRight;
  const setMod = session.setMod;
  const setTemplates = session.setTemplates;
  const zoomNow = session.zoomNow;
  const sizeNow = session.sizeNow;
  const thumb = session.thumb;
  const setThumb = session.setThumb;
  const setPan = session.setPan;
  const setPanning = session.setPanning;
  const spaced = session.spaced;
  const spaceButton = session.spaceButton;
  const stage = session.stage;
  const desk = session.desk;
  const moveable = session.moveable;
  const strip = session.strip;
  const tug = session.tug;
  const press = session.press;
  const auto = session.auto;
  const pinch = session.pinch;
  const zoomTo = session.zoomTo;
  const from = session.from;
  const free = session.free;
  const onKey = session.onKey;
  const steer = (...a: any[]) => (session as Record<string, any>).steer(...a);
  const scale = (...a: any[]) => (session as Record<string, any>).scale(...a);
  const quit = (...a: any[]) => (session as Record<string, any>).quit(...a);
  const aim = (...a: any[]) => (session as Record<string, any>).aim(...a);
  const scrollEdge = (...a: any[]) => (session as Record<string, any>).scrollEdge(...a);
  const release = (...a: any[]) => (session as Record<string, any>).release(...a);
useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      setMod((e.shiftKey ? KEEP : 0) | ((APPLE ? e.altKey : e.ctrlKey) ? CENTRE : 0) | ((APPLE ? e.metaKey : e.altKey) ? LOOSE : 0));
      // Any key but a letter, which types the space before it, takes the waiting space back: Enter or F2 would open
      // the text with all of it picked, and the space would take its place.
      const letter = e.key.length === 1 && (e.getModifierState("AltGraph") || !(e.ctrlKey || e.metaKey || e.altKey));
      if (e.type === "keydown" && e.code !== "Space" && !letter) spaced.current = null;
      // Letting Space go puts the hand down. A drag that is on goes on until the pointer lifts.
      if (e.type === "keyup" && e.code === "Space") {
        setPan(false);
        const open = spaced.current;
        const button = spaceButton.current;
        spaced.current = null;
        spaceButton.current = null;
        if (open) {
          flushSync(open);
          document.execCommand("insertText", false, " ");
        } else if (button?.isConnected) button.click();
      }
    };
    const onBlur = () => {
      setMod(0);
      setPan(false);
      spaced.current = null;
      spaceButton.current = null;
      setPanning(false);
    };
    // A press anywhere, on the hand or in the panel, takes the waiting space back too.
    const onPress = () => {
      spaced.current = null;
      spaceButton.current = null;
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("keyup", onKey);
    window.addEventListener("blur", onBlur);
    window.addEventListener("pointerdown", onPress, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("keyup", onKey);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("pointerdown", onPress, true);
    };
  }, []);

  useEffect(() => {
    attempt("Die Vorlagen konnten nicht geladen werden.", () => signed(api<Template[]>("/templates")).then(setTemplates));
  }, []);

  // The sheet's saver (saves.ts) saves a change two seconds after the last one, tries a failed save again, and goes
  // on when this editor has gone. It hears of each change here, and of the last one as the editor goes.
  useEffect(() => set(file.id, { doc: hist.doc, title }), [hist.doc, title]);
  useEffect(() => attach(file.id, () => ({ doc: live.current.doc, title: named.current })), []);

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
  // On the iPad held upright a swipe in from a window's edge opens that side's drawer, and a swipe of an open drawer
  // back to its edge shuts it. Only one finger counts, and only a swipe across more than a vertical one: a scroll
  // of the drawer or a drag of a block keeps its own. Set by hand, as the desk must not pan once a swipe is taken.
  useEffect(() => {
    if (!drawers) return;
    function onStart(e: globalThis.TouchEvent) {
      swipe.current = undefined;
      if (e.touches.length !== 1) return;
      const { clientX: x, clientY: y } = e.touches[0];
      const on = e.target as Element;
      const free = !on.closest(".sheet, header, aside, .dock, .moveable-control-box");
      const panel = drawer && on.closest(drawer === "left" ? "aside.left" : "aside.panel");
      const shut = panel && !on.closest("input, select, textarea, [draggable=true]") && !tug.current?.held ? drawer : undefined;
      const open = free && x <= 24 ? "left" : free && x >= innerWidth - 24 ? "right" : undefined;
      if (open || shut) swipe.current = { x, y, open, shut };
    }
    function onMove(e: globalThis.TouchEvent) {
      const s = swipe.current;
      if (!s) return;
      // A thumbnail held for the long press is dragged, not swiped: the drawer stays as it is.
      if (e.touches.length !== 1 || tug.current?.held) {
        swipe.current = undefined;
        return;
      }
      const dx = e.touches[0].clientX - s.x;
      const dy = e.touches[0].clientY - s.y;
      if (s.decided) return e.preventDefault();
      if (Math.abs(dx) <= 40 || Math.abs(dx) <= 2 * Math.abs(dy)) {
        // A scroll that runs up or down first is not a swipe.
        if (Math.abs(dy) > 40 && Math.abs(dy) > 2 * Math.abs(dx)) swipe.current = undefined;
        return;
      }
      if (s.open === "left" && dx > 0) showLeft(true);
      else if (s.open === "right" && dx < 0) showRight(true);
      else if (s.shut === "left" && dx < 0) showLeft(false);
      else if (s.shut === "right" && dx > 0) showRight(false);
      else {
        swipe.current = undefined;
        return;
      }
      s.decided = true;
      e.preventDefault();
    }
    function onEnd() {
      swipe.current = undefined;
    }
    window.addEventListener("touchstart", onStart, { passive: true });
    window.addEventListener("touchmove", onMove, { passive: false });
    window.addEventListener("touchend", onEnd);
    window.addEventListener("touchcancel", onEnd);
    return () => {
      window.removeEventListener("touchstart", onStart);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onEnd);
      window.removeEventListener("touchcancel", onEnd);
    };
  });
  // Ctrl and the wheel zoom the page about the pointer, and never the window: over the bar and the panels they do
  // nothing, and over the thumbnails they make those larger and smaller, as in PowerPoint. A trackpad's pinch comes
  // the same way. React's own wheel listener is passive, so this one is set by hand.
  useEffect(() => {
    function onWheel(e: globalThis.WheelEvent) {
      const on = e.target as Element;
      if (!e.ctrlKey && !e.metaKey) {
        // The hand lies over the desk, so a wheel on it scrolls the desk from here.
        if (on.closest(".hand")) {
          steer();
          desk.current!.scrollBy(e.deltaX, e.deltaY);
        }
        return;
      }
      e.preventDefault();
      // A whole delta is a mouse wheel: one step of the buttons per 100.
      // One that is not whole is a trackpad pinch. Chrome sends about -100 * ln(scale),
      // and exp(-delta / 100) gives that scale back, so the page follows the fingers.
      const pinch = !Number.isInteger(e.deltaY);
      const by = pinch ? Math.exp(-e.deltaY / 100) : 1.25 ** (-e.deltaY / 100);
      if (on.closest(".pages")) return setThumb((w) => Math.min(THUMBS[1], Math.max(THUMBS[0], w * by)));
      if (!stage.current!.contains(on)) return;
      // The page under the pointer, not the one in use: the gaps between the pages do not grow with them.
      const under = document.elementsFromPoint(e.clientX, e.clientY).find((el): el is HTMLElement => el.matches(".sheet")) ?? sheet.current!;
      const mm = sizeNow.current[+under.dataset.page!][0];
      // The listener closes over the scale of the render that set it, and it is replaced only after paint.
      // A busy runner delivers the wheel once the desk has been measured and drawn, while the listener still
      // holds the old scale: the point then misses the page by whole centimetres and never arrives (#325).
      // The box is the scale on the screen. The ref is the zoom drawn, or the one a zoom just asked for.
      let box = under.getBoundingClientRect();
      const kNow = box.width / mm;
      const [x, y] = [(e.clientX - box.left) / kNow, (e.clientY - box.top) / kNow];
      const next = Math.min(4, Math.max(0.25, zoomNow.current * by));
      flushSync(() => zoomTo(next));
      // Scroll the page point that was under the pointer back under it. The scale is the box after the
      // zoom, not fit times the step: the same turn may have measured the desk anew.
      box = under.getBoundingClientRect();
      const scale = box.width / mm;
      // Whole px: Safari cuts a fraction off, always the same way, and the page creeps with each step.
      desk.current!.scrollBy(Math.round(box.left + x * scale - e.clientX), Math.round(box.top + y * scale - e.clientY));
    }
    window.addEventListener("wheel", onWheel, { passive: false });
    return () => window.removeEventListener("wheel", onWheel);
  });
  useEffect(() => () => cancelAnimationFrame(auto.current.frame), []);
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
      press.current = window.setTimeout(() => {
        tug.current!.held = true;
        aim(x, y);
      }, 500);
    }
    function onMove(e: globalThis.TouchEvent) {
      if (!tug.current) return;
      if (Math.hypot(e.touches[0].clientX - tug.current.x, e.touches[0].clientY - tug.current.y) > SLOP) tug.current.left = true;
      if (tug.current.slot === undefined) {
        // No preventDefault during the hold: it would keep the panel still for the whole swipe.
        // A second finger may have come down beside the panel, where the start of a touch is not heard.
        if (e.touches.length > 1 || Math.hypot(e.touches[0].clientX - tug.current.x, e.touches[0].clientY - tug.current.y) > SLOP) quit();
        return;
      }
      e.preventDefault();
      aim(e.touches[0].clientX, e.touches[0].clientY);
      scrollEdge(e.touches[0].clientX, e.touches[0].clientY);
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

    return session;
}
