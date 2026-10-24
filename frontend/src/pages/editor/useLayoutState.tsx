// The bar's folding, the zoom, and the desk the pages lie on.
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import Moveable from "react-moveable";
import type { Ground } from "../../ground";
import type { Template } from "./palette";
import { useSelectionState } from "./useSelectionState";

export function useLayoutState(session: ReturnType<typeof useSelectionState>) {
  const file = session.file;
  const over = session.over;
  const title = session.title;
  const ids = session.ids;
  const editing = session.editing;
  const caret = session.caret;
  const lens = session.lens;
  const pane = session.pane;
  const setPane = session.setPane;
  const leafy = session.leafy;
  const side = session.side;
  const setSide = session.setSide;
  const drawers = session.drawers;
  const drawer = session.drawer;
  const setDrawer = session.setDrawer;
  const look = (...a: any[]) => (session as Record<string, any>).look(...a);
  const cut = (...a: any[]) => (session as Record<string, any>).cut(...a);
  const edge = (...a: any[]) => (session as Record<string, any>).edge(...a);
  const steer = (...a: any[]) => (session as Record<string, any>).steer(...a);
// Each turn upright starts with both shut.
  useEffect(() => setDrawer(undefined), [drawers]);
  const leaf = leafy && !drawers;
  const left = drawers ? drawer === "left" : side;
  const right = drawers ? drawer === "right" : pane;
  const showLeft = (on: boolean) => (drawers ? setDrawer(on ? "left" : undefined) : setSide(on));
  const showRight = (on: boolean) => (drawers ? setDrawer(on ? "right" : undefined) : setPane(on));
  // The bar is one row, and what has no room in it lies behind "Mehr": `fits` is how many of the commands that may
  // fold stay in the bar, counted from its left. While it is not known all of them are drawn in the bar, where they
  // are measured and the count is set before the browser paints.
  const bar = useRef<HTMLDivElement>(null);
  const [fits, setFits] = useState<number>();
  const feedback = useRef<() => void>(null);
  // "Mehr" leaves the bar while it is measured, and the focus with it: where the button comes back, so does the focus.
  const focused = useRef(false);
  // Under an open menu the bar waits to be measured until the menu shuts: the menu hands the focus back to the
  // button that had it, and a "Mehr" that left the bar meanwhile is no longer that button.
  const late = useRef(false);
  // A measure is asked for and not yet taken: until it is, the focus "Mehr" had is not given back and not forgotten.
  const awaited = useRef(false);
  const refit = () => {
    late.current = !!document.querySelector("dialog.menu[open]");
    if (late.current) return;
    focused.current ||= !!document.activeElement?.matches(".more");
    awaited.current = true;
    setFits(undefined);
  };
  // The bar is measured anew when its width changes, as the window's does or the iPad turns, when its type has
  // loaded, and when Blattform's layout, which has the zoom elsewhere, comes or goes. A turn has shut an open "Mehr"
  // by then, as the window's new size shuts any menu; a type that loads under an open menu has not. So it is when
  // the title changes, and when its field gains or loses the focus: the bar's width stays, and tells of none.
  // This runs before the measure below: a render that is measured and whose layout changes at once would else have
  // its count wiped after it was taken, and the bar would stay unmeasured.
  useLayoutEffect(refit, [leaf, title]);
  useLayoutEffect(() => {
    if (fits !== undefined) {
      if (awaited.current) return;
      if (focused.current) bar.current!.querySelector<HTMLElement>(".more")?.focus();
      focused.current = false;
      return;
    }
    awaited.current = false;
    const row = bar.current!;
    const look = getComputedStyle(row);
    const may = [...row.querySelectorAll(".sep ~ :is(.ib, .zoom):not(.pin)")];
    const widths = may.map((el) => el.getBoundingClientRect().width + parseFloat(look.columnGap));
    // How far the row runs past the bar's end, and how much of the hint it has squeezed away before that.
    const hint = row.querySelector(".hint")!;
    let over = row.querySelector(".pdf")!.getBoundingClientRect().right + parseFloat(look.paddingRight) - row.getBoundingClientRect().right + hint.scrollWidth - hint.clientWidth;
    // The title gives way first, so the row may end in the bar with the title cut: what it lacks counts too, up to
    // the most a title may take. While it is edited that is all of it, and `none` is no number. Safari counts a
    // whole title a pixel wider than its field: that is no lack.
    const name = row.querySelector("input")!;
    const lack = name.scrollWidth - name.clientWidth;
    if (lack > 1) over += Math.min(lack, (parseFloat(getComputedStyle(name).maxWidth) || Infinity) - name.offsetWidth);
    let n = may.length;
    // A phone's bar wraps and keeps them all.
    if (look.flexWrap === "nowrap" && over > 0.5) {
      // "Mehr" needs the room of one of them.
      over += widths[0];
      while (n && over > 0.5) over -= widths[--n];
      // The zoom's four stay or go together.
      const lens = may.findIndex((el) => el.matches(".zoom"));
      if (lens > 0 && n >= lens && n < lens + 3) n = lens - 1;
    }
    setFits(n);
  });
  useLayoutEffect(() => {
    // Before the browser paints the bar at its new width.
    const again = () => flushSync(refit);
    const watch = new ResizeObserver(again);
    watch.observe(bar.current!);
    document.fonts.ready.then(again);
    return () => watch.disconnect();
  }, []);
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
  // The page ground, unlocked to shift and scale, or with its crop handles out. A PDF of several pages waits in `pdfAsk`.
  const [shaping, setShaping] = useState(false);
  const [trimming, setTrimming] = useState(false);
  const [pdfAsk, setPdfAsk] = useState<{ file: File; pages: number; page: number }>();
  const groundFile = useRef<HTMLInputElement>(null);
  const groundHold = useRef<{ kind: "move" | "scale" | "trim"; x: number; y: number; ground: Ground; edge?: number; dist?: number } | undefined>(undefined);
  // The desk's width in pixels. The widest page fills it; zoom multiplies that.
  const [room, setRoom] = useState(210);
  // The desk's height in pixels, which a fit follows too.
  const [high, setHigh] = useState(0);
  const [zoom, setZoom] = useState(1);
  // The zoom a wheel reads. The listener is replaced only after paint, so a wheel on a busy runner
  // still holds the previous render: the ref is the zoom drawn, or the one a zoom just asked for.
  const zoomNow = useRef(1);
  // Each page's width and height in mm, for the same reason.
  const sizeNow = useRef<number[][]>([]);
  // Set by Ganze Seite, cleared by a zoom by hand: while it is set, a new size of the desk fits the page again.
  const fitted = useRef(false);
  // The page in use when Ganze Seite was pressed, and a count that makes each press a change to draw.
  const fitOn = useRef(0);
  const [fitTick, setFitTick] = useState(0);
  // A thumbnail's width in px.
  const [thumb, setThumb] = useState(97);
  // Space held makes the pointer a hand, and a drag with it moves the desk. The drag may outlast the key.
  const [pan, setPan] = useState(false);
  const [panning, setPanning] = useState(false);
  // Where the hand's drag began: the pointer, and the desk's scroll.
  const hand = useRef([0, 0, 0, 0]);
  // Space pressed on a picked text, shape, table or Lineatur: opens it at the keyup, unless the hand dragged meanwhile.
  const spaced = useRef<(() => void) | null>(null);
  // The block, and the cell, that Text bearbeiten opens a moment later. A key typed before opens it at once (#640).
  const asked = useRef<{ id: string; cell?: number }>(undefined);
  useEffect(() => {
    if (editing) asked.current = undefined;
  }, [editing]);
  const stage = useRef<HTMLDivElement>(null);
  const desk = useRef<HTMLDivElement>(null);
  // Moves the desk by a drag from where hand.current says: the hand and the middle button share it.
  const dragDesk = (e: { clientX: number; clientY: number }) => {
    desk.current!.scrollLeft = hand.current[2] - (e.clientX - hand.current[0]);
    desk.current!.scrollTop = hand.current[3] - (e.clientY - hand.current[1]);
  };
  // The middle button pans the desk while it is held, over a block too. The window hears the moves and the lift.
  const middlePan = (x: number, y: number) => {
    hand.current = [x, y, desk.current!.scrollLeft, desk.current!.scrollTop];
    setPanning(true);
    const move = (e: { clientX: number; clientY: number; buttons: number }) => {
      if (!(e.buttons & 4)) return stop();
      steer();
      dragDesk(e);
    };
    const stop = () => {
      setPanning(false);
      removeEventListener("pointermove", move);
      removeEventListener("pointerup", stop);
      removeEventListener("pointercancel", stop);
    };
    addEventListener("pointermove", move);
    addEventListener("pointerup", stop);
    addEventListener("pointercancel", stop);
  };
  // An open Format drawer lies over the sheet's right end. The desk scrolls so the picked block, or the caret in the
  // open text, stays in view beside it: the drawer shows the room on the desk's right, see `.drawn` in styles.css.
  const drawnRight = drawers && drawer === "right";
  // The desk's scroll before the drawer moved it: shutting the drawer puts it back.
  const scrolledFrom = useRef<number | undefined>(undefined);
  useLayoutEffect(() => {
    const el = desk.current;
    if (!drawnRight) {
      if (el && scrolledFrom.current !== undefined) el.scrollLeft = scrolledFrom.current;
      scrolledFrom.current = undefined;
      return;
    }
    const panel = document.querySelector("aside.panel");
    if (!el || !panel || !ids.length) return;
    // The part to keep in view, as its left and right edges on the window.
    let rect: { left: number; right: number } | undefined;
    if (editing) {
      const caret = getSelection()?.rangeCount ? getSelection()!.getRangeAt(0).getBoundingClientRect() : undefined;
      // A caret at the end of a line may have no size: then the text's box stands in for it.
      rect = caret && (caret.width || caret.height) ? caret : document.querySelector(`.block[data-id="${editing}"]`)?.getBoundingClientRect();
    } else {
      const boxes = ids.map((id) => document.querySelector(`.block[data-id="${id}"]`)?.getBoundingClientRect()).filter((b): b is DOMRect => !!b);
      if (boxes.length) rect = { left: Math.min(...boxes.map((b) => b.left)), right: Math.max(...boxes.map((b) => b.right)) };
    }
    if (!rect) return;
    // Scroll until the part clears the panel's left edge with a gap, but no further than the desk's own left edge allows.
    const gap = 16;
    const dx = rect.right - (panel.getBoundingClientRect().left - gap);
    const by = dx > 0 ? Math.max(0, Math.min(dx, rect.left - (el.getBoundingClientRect().left + gap))) : 0;
    if (by > 0) {
      scrolledFrom.current = el.scrollLeft;
      el.scrollLeft += by;
    }
  }, [drawnRight]);
  const moveable = useRef<Moveable>(null);
  const picker = useRef<HTMLInputElement>(null);
    return Object.assign(session, { leaf, left, right, showLeft, showRight, bar, fits, setFits, feedback, focused, late, awaited, refit, tour, setTour, solved, setSolved, mod, setMod, templates, setTemplates, name, setName, guide, setGuide, draft, setDraft, shaping, setShaping, trimming, setTrimming, pdfAsk, setPdfAsk, groundFile, groundHold, room, setRoom, high, setHigh, zoom, setZoom, zoomNow, sizeNow, fitted, fitOn, fitTick, setFitTick, thumb, setThumb, pan, setPan, panning, setPanning, hand, spaced, asked, stage, desk, dragDesk, middlePan, drawnRight, scrolledFrom, moveable, picker });
}
