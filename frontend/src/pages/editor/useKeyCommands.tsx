// The sheet's shortcuts: moving, zoom, the clipboard and the rest.
import { flushSync } from "react-dom";
import { ask } from "../../saves";
import { boxed, isLine, tied } from "../../sheet";
import { next } from "../../cells";
import { has } from "../Format";
import { round, grouped, step } from "./palette";
import { useKeys } from "./useKeys";

export function useKeyCommands(session: ReturnType<typeof useKeys>) {
  const ids = session.ids;
  const setIds = session.setIds;
  const editing = session.editing;
  const part = session.part;
  const sheet = session.sheet;
  const setMulti = session.setMulti;
  const setMenu = session.setMenu;
  const tab = session.tab;
  const name = session.name;
  const setPan = session.setPan;
  const spaced = session.spaced;
  const spaceButton = session.spaceButton;
  const asked = session.asked;
  const desk = session.desk;
  const held = session.held;
  const blocks = session.blocks;
  const cell = session.cell;
  const sel = session.sel;
  const from = session.from;
  const free = session.free;
  const thing = session.thing;
  const cropping = session.cropping;
  const onKey = session.onKey;
  const keyFocus = session.keyFocus;
  const mark = (...a: any[]) => (session as Record<string, any>).mark(...a);
  const spin = (...a: any[]) => (session as Record<string, any>).spin(...a);
  const steer = (...a: any[]) => (session as Record<string, any>).steer(...a);
  const inView = (...a: any[]) => (session as Record<string, any>).inView(...a);
  const typed = (...a: any[]) => (session as Record<string, any>).typed(...a);
  const edit = (...a: any[]) => (session as Record<string, any>).edit(...a);
  const writable = (...a: any[]) => (session as Record<string, any>).writable(...a);
  const place = (...a: any[]) => (session as Record<string, any>).place(...a);
  const paint = (...a: any[]) => (session as Record<string, any>).paint(...a);
  const done = (...a: any[]) => (session as Record<string, any>).done(...a);
  const raise = (...a: any[]) => (session as Record<string, any>).raise(...a);
  const zoomBy = (...a: any[]) => (session as Record<string, any>).zoomBy(...a);
  const fitPage = (...a: any[]) => (session as Record<string, any>).fitPage(...a);
  const redo = (...a: any[]) => (session as Record<string, any>).redo(...a);
  const undo = (...a: any[]) => (session as Record<string, any>).undo(...a);
  const cut = (...a: any[]) => (session as Record<string, any>).cut(...a);
  const dip = (...a: any[]) => (session as Record<string, any>).dip(...a);
  const copy = (...a: any[]) => (session as Record<string, any>).copy(...a);
  const daub = (...a: any[]) => (session as Record<string, any>).daub(...a);
  const put = (...a: any[]) => (session as Record<string, any>).put(...a);
  const all = (...a: any[]) => (session as Record<string, any>).all(...a);
  const split = (...a: any[]) => (session as Record<string, any>).split(...a);
  const join = (...a: any[]) => (session as Record<string, any>).join(...a);
  const remove = (...a: any[]) => (session as Record<string, any>).remove(...a);
onKey.current = (e) => {
    // A new Space starts with no button. A repeat keeps the one the first press named, and a dialog or a
    // field that returns below leaves it clear so a later keyup cannot press a button from before.
    if (e.code === "Space" && !e.repeat) spaceButton.current = null;
    const held = keyFocus(e);
    if (!held) return;
    const { target, shut, turnKey, mark, ours } = held;
    if (!ours && !shut && target.closest(".ProseMirror, textarea, input, select")) return;
    // Alt+Left and Alt+Right turn the picked blocks 15° counter-clockwise and clockwise, as in PowerPoint. A locked
    // block, a table and a line on its own do not turn, as the buttons of the panel do not.
    if (turnKey) {
      e.preventDefault();
      if (sel.length && free.length === sel.length && !cropping && !sel.some((b) => b.type === "table" || (isLine(b) && thing(b) === b.id))) spin(e.key === "ArrowRight" ? 15 : -15);
      return;
    }
    // Shift+F10 and the Menu key open the menu of the selection, as in PowerPoint: at the middle of the picked blocks, or
    // with nothing picked near the corner of the page in use. A focused button keeps the key for itself.
    if (((e.key === "F10" && e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) || e.key === "ContextMenu") && !target.closest("button, a, summary, .panel, header, .dock")) {
      e.preventDefault();
      const rects = sel.map((b) => sheet.current!.querySelector(`[data-id="${b.id}"]`)?.getBoundingClientRect()).filter((r): r is DOMRect => !!r);
      const paper = document.querySelector(".sheet.on")?.getBoundingClientRect();
      const x = rects.length ? (Math.min(...rects.map((r) => r.left)) + Math.max(...rects.map((r) => r.right))) / 2 : (paper?.left ?? 0) + 20;
      const y = rects.length ? (Math.min(...rects.map((r) => r.top)) + Math.max(...rects.map((r) => r.bottom))) / 2 : (paper?.top ?? 0) + 20;
      setMenu({ x: Math.max(0, Math.min(x, innerWidth)), y: Math.max(0, Math.min(y, innerHeight)) });
      return;
    }
    // With the focus on a button or on nothing, as after Ganze Seite, a page key scrolls the desk: the browser would
    // scroll the window instead. The left strip keeps them for its own long list of pages.
    if (!target.closest(".desk, .left, .ProseMirror, input, textarea, select, .panel, .menu, dialog, [role=menu]") && /^(PageUp|PageDown|Home|End)$/.test(e.key) && !(e.ctrlKey || e.metaKey || e.altKey)) {
      e.preventDefault();
      const d = desk.current!;
      if (!sel.length) steer();
      d.scrollTop = e.key === "End" ? d.scrollHeight : e.key === "Home" ? 0 : d.scrollTop + d.clientHeight * (e.key === "PageDown" ? 0.9 : -0.9);
      // The view has moved now: the page in view is in use at once, the scroll events that follow keep it.
      if (!sel.length) inView();
      return;
    }
    // The page keys scroll the desk; with nothing picked the page that then fills the view becomes the page in use.
    if (!sel.length && /^(PageUp|PageDown|Home|End|Arrow(Up|Down|Left|Right))$/.test(e.key) && !(e.ctrlKey || e.metaKey || e.altKey)) steer();
    // A number field drops a number it refused, as on leaving it, so it shows what the undo gives back.
    if (ours && target.matches("input[type=number]")) {
      target.blur();
      target.focus();
    }
    // A letter typed with one picked text, shape, table or Lineatur opens it for writing, and the caret goes to the end
    // of its text. The focus moves in the same flush, so the browser types the key into the textarea: no preventDefault.
    // Keys that are commands, and a field, a button or the panel that keep their own, stay as they are. Space is also
    // the hand's key: on a picked block it opens it at the keyup and types the space, unless the hand dragged first.
    // A dead key, as ^ on a German keyboard, opens it too: the letter that follows makes ê there. An IME or an on-screen
    // keyboard sends 229 or "Process" for a letter, and the text comes after it as input: it opens too.
    const typed = (e.key.length === 1 || e.key === "Dead" || e.keyCode === 229 || e.key === "Process") && (e.getModifierState("AltGraph") || !(e.ctrlKey || e.metaKey || e.altKey));
    const space = e.code === "Space" && !e.ctrlKey && !e.metaKey && !e.altKey;
    // A key that comes before Text bearbeiten has opened its block opens it now, in its cell and all picked, so the
    // key replaces the text there. It went to the first cell before, after the text (#640).
    const ask = asked.current;
    if (typed && ask) {
      asked.current = undefined;
      if (!editing && free.length === 1 && free[0].id === ask.id) {
        flushSync(() => edit(ask.id, undefined, true, ask.cell));
        return;
      }
    }
    if (typed && !editing && sel.length === 1 && free.length === 1 && writable(free[0]) && !tied(free[0]) && !target.closest("button, a, summary, .panel")) {
      const id = free[0].id;
      if (space) {
        e.preventDefault();
        if (!e.repeat) {
          setPan(true);
          spaced.current = () => edit(id);
        }
        return;
      }
      flushSync(() => edit(id));
      // A key that comes while Space is still down: the space first, then the key.
      if (spaced.current) {
        spaced.current = null;
        document.execCommand("insertText", false, " ");
      }
      return;
    }
    // Space is the hand's key and does not scroll the desk, also while it repeats. The button, link or
    // summary it went down on is pressed when the key comes up: WebKit never fires the click if the
    // focus has moved by then, and shutting a dialog moves it (#582). The hand's press clears it.
    if (space) {
      e.preventDefault();
      if (!e.repeat) {
        spaceButton.current = target.closest("button, a, summary");
        setPan(true);
      }
      return;
    }
    // An arrow moves by 1 mm, or by a grid cell, and with Shift by 10 mm. A run of them makes one undo step.
    const step = e.shiftKey ? 10 : cell || 1;
    const nudge = (dx: number, dy: number) => place(free.map((b) => [b.id, { x: round(b.x + dx * step), y: round(b.y + dy * step) }]), "nudge");
    // Ctrl+B, I and U do what the panel's buttons do.
    const flip = (name: "bold" | "italic" | "underline") => mark && sel.some(boxed) && (() => paint({ [name]: !has(sel, part, name) }));
    // Enter and F2 open the one selected block to write in it, with all its text picked, as in PowerPoint. A
    // picture is not cropped, and a locked block stays shut as it does for a double click.
    const write = sel.length === 1 && free[0] && free[0].type !== "image" && (() => edit(free[0].id, undefined, true));
    // Tab picks the next block from back to front and Shift+Tab the one before, as in PowerPoint. A group is one stop.
    const next = () => {
      const order = [...blocks].sort((a, b) => a.z - b.z);
      if (e.shiftKey) order.reverse();
      const from = order.map((b) => ids.includes(b.id)).lastIndexOf(true);
      const to = [...order.slice(from + 1), ...order].find((b) => !ids.includes(b.id));
      if (!to) return;
      done();
      const picked = grouped([to.id], blocks);
      // Drawn at once: under a narrow window's desk the panel grows with the first block picked, and the desk
      // scrolls at the height that leaves it.
      flushSync(() => setIds(picked));
      // The desk scrolls to what is picked, as in PowerPoint: a group as far as it fits, and the block itself last.
      for (const id of [...picked, to.id]) sheet.current!.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
    };
    // A button that has the focus keeps Enter and Tab. With nothing selected Tab picks the block at the back and
    // Shift+Tab the one in front.
    const plain = !target.closest("button, a");
    // Ctrl+] and Ctrl+[ step the picked blocks in the stack, with Shift to the front or the back, as in PowerPoint.
    // With Alt or AltGr the key types a character, so it is no order key.
    const order = (front: boolean) => sel.length > 0 && !e.altKey && !e.getModifierState("AltGraph") && (() => raise(front, !e.shiftKey));
    // Ctrl and + or - zoom the sheet a step, as the buttons do, and Ctrl+Alt+O fits the page, not the browser's zoom.
    // With AltGr the keys type characters, so they are no zoom keys.
    const zoomStep = (by: number) => !e.getModifierState("AltGraph") && (() => zoomBy(by));
    const fitKey = e.altKey && !e.getModifierState("AltGraph") && (() => fitPage());
    // Ctrl+V alone is not here: a key stopped on its way down brings no paste.
    const keys: Record<string, (() => void) | false | undefined> =
      e.ctrlKey || e.metaKey
        ? { z: e.shiftKey ? redo : undo, y: redo, x: cut, c: e.shiftKey ? () => dip() : copy, v: e.shiftKey && (() => daub(ids)), d: () => put(sel), a: all, g: e.shiftKey ? split : join, b: flip("bold"), i: flip("italic"), u: flip("underline"), "]": order(true), "}": order(true), "[": order(false), "{": order(false), "+": zoomStep(1), "=": zoomStep(1), "-": zoomStep(-1), o: fitKey }
        : {
            delete: remove,
            backspace: remove,
            // Escape ends a crop, or else selects nothing, as in PowerPoint. A part of one group goes back to the
            // whole group first.
            escape: cropping
              ? done
              : () => {
                  const mates = grouped(ids, blocks);
                  setIds(new Set(sel.map((b) => b.group?.[0])).size === 1 && mates.length > ids.length ? mates : []);
                  setMulti(false);
                },
            arrowleft: () => nudge(-1, 0),
            arrowright: () => nudge(1, 0),
            arrowup: () => nudge(0, -1),
            arrowdown: () => nudge(0, 1),
            enter: plain && write,
            f2: write,
            tab: plain && blocks.length > 0 && next,
          };
    // A Mac's Option+O types ø, so the key is read by its place on the keyboard.
    const run = keys[e.code === "KeyO" && e.altKey ? "o" : e.key.toLowerCase()];
    // With nothing to move the arrows scroll the desk, and Alt with an arrow stays the browser's way back.
    if (!run || (e.key.startsWith("Arrow") && (!free.length || cropping || e.altKey))) return;
    e.preventDefault();
    run();
  };

    return session;
}
