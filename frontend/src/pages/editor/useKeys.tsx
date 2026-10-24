// Keys a field, a dialog or Escape takes before the sheet's own shortcuts.
import { returned } from "../../history";
import { open } from "../../saves";
import { list } from "../Field";
import { next } from "../../cells";
import { APPLE, SPACING, deadMark } from "./palette";
import { useDrop } from "./useDrop";

export function useKeys(session: ReturnType<typeof useDrop>) {
  const setHist = session.setHist;
  const haul = session.haul;
  const coat = session.coat;
  const brush = session.brush;
  const setBrush = session.setBrush;
  const editing = session.editing;
  const part = session.part;
  const inPanel = session.inPanel;
  const accent = session.accent;
  const written = session.written;
  const back = session.back;
  const act = session.act;
  const setDraft = session.setDraft;
  const moveable = session.moveable;
  const mergeKey = session.mergeKey;
  const ahead = session.ahead;
  const grasp = session.grasp;
  const away = session.away;
  const adjusting = session.adjusting;
  const spot = session.spot;
  const sel = session.sel;
  const mark = (...a: any[]) => (session as Record<string, any>).mark(...a);
  const quit = (...a: any[]) => (session as Record<string, any>).quit(...a);
  const stopDeskScroll = (...a: any[]) => (session as Record<string, any>).stopDeskScroll(...a);
  const dip = (...a: any[]) => (session as Record<string, any>).dip(...a);
  const wordPaint = (...a: any[]) => (session as Record<string, any>).wordPaint(...a);
const keyFocus = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement;
    // The dead key itself only moved the caret back. Its accent is still waiting, and this key is
    // the letter it marks, a second press of it, or Space, which types the accent alone.
    if (accent.current) {
      const mark = accent.current;
      const fieldNow = written();
      const root = !fieldNow ? null : "dom" in fieldNow ? fieldNow.dom : fieldNow;
      const here = !!root && (root === target || root.contains(target));
      const next = e.key === "Dead" ? deadMark(e) : "";
      if (here && e.key === "Dead" && e.repeat) {
        e.preventDefault();
        return;
      }
      if (here && next && next !== mark) {
        accent.current = next;
        e.preventDefault();
        return;
      }
      accent.current = "";
      const letter = e.key.length === 1 && !(e.ctrlKey || e.metaKey || e.altKey);
      if (here && (e.key === "Dead" || letter)) {
        e.preventDefault();
        const alone = e.key === "Dead" || e.key === " ";
        document.execCommand("insertText", false, alone ? SPACING[mark] : (e.key + mark).normalize("NFC"));
        return;
      }
    }
    const select = target.matches(".panel select");
    // Shift alone is no key yet, and a key that only switches something or opens the menu is none either.
    const real = !["Shift", "Control", "Alt", "AltGraph", "Meta", "CapsLock", "NumLock", "ScrollLock", "ContextMenu"].includes(e.key);
    // A list still open keeps its keys. Chromium sends none of them here, Firefox does. A browser that does not
    // know `:open` throws.
    let list = false;
    try {
      list = select && (target.matches(":open") || target.hasAttribute("data-open"));
    } catch {
      // The list counts as shut.
    }
    // Enter in a select of the panel gives the keys back, as in PowerPoint's box of fonts. A list or a colour picker
    // opened with the mouse and shut with no pick tells nobody, and its control keeps the focus: the first key since
    // the press is then not the control's either. A colour has no key of its own while its picker is shut. A select
    // keeps the arrows, which walk it, a letter while its list is open, and Escape, whose keyup gives the keys back.
    // An arrow with Ctrl walks no select.
    const walks = e.key.startsWith("Arrow") && !e.ctrlKey && !e.metaKey;
    const first = real && inPanel.current && (select ? e.key === "Tab" || !(list || e.key === "Escape" || walks) : target.matches(".panel input[type=color]"));
    const shut = first || (select && e.key === "Enter");
    // Who walks a select of the panel with the keys keeps the focus there.
    if (real) inPanel.current = false;
    // Ctrl and + or - never zoom the browser's window, which would take the bar and the panels with it: in a field
    // or a dialog, where they zoom nothing, they type nothing either. With AltGr they type a character.
    if ((e.ctrlKey || e.metaKey) && !e.getModifierState("AltGraph") && ["+", "=", "-"].includes(e.key)) e.preventDefault();
    // Alt+Left and Alt+Right never take the browser back or forward out of the sheet, also in a text or a dialog. A
    // Mac's Option with an arrow goes by words in a text, and is no way back, so it stays.
    const turnKey = e.altKey && !e.ctrlKey && !e.metaKey && (e.key === "ArrowLeft" || e.key === "ArrowRight");
    if (turnKey && !APPLE) e.preventDefault();
    // The keys are a dialog's own while it is open.
    if (document.querySelector("dialog:modal")) return;
    if (shut) {
      const open = written();
      back(target);
      // Tab and Enter do no more. A letter goes on to what is written in, with the keypress that types it there;
      // a key of the field's that types none, as Backspace or Ctrl+Z, is done there by hand, and any other only brings
      // the caret back. With nothing written in the key goes on to the sheet.
      if (e.key === "Enter" || (open && (e.key === "Tab" || act(e)))) e.preventDefault();
      // A dead key does not follow the caret: the browser has already called it "Dead" and will not
      // compose it in the text. The accent is kept for the letter that comes next.
      if (e.key === "Dead" && open) {
        const mark = deadMark(e);
        if (mark) {
          accent.current = mark;
          e.preventDefault();
        }
      }
      if (open || e.key === "Enter" || e.key === "Escape") return;
    }
    // Escape calls a thumbnail's drag off.
    if (e.key === "Escape" && haul) {
      quit();
      return;
    }
    // Escape puts the brush down from anywhere, also from a field that keeps the key to itself, and does no more.
    if (e.key === "Escape" && brush) {
      setBrush(0);
      return;
    }
    // Escape during a press makes its release no click: the block stays picked and closed.
    if (e.key === "Escape") spot.current = undefined;
    // Escape calls a move, a resize or a turn off while the pointer is still down, as in PowerPoint: the blocks are
    // back where they began, with no undo step, and what redo held stays. Moveable ends its drag with no event.
    // So it is with a handle the pointer holds: a line's end, a table's column line, a guide line, a crop's frame.
    if (e.key === "Escape" && (moveable.current?.isDragging() || grasp.current?.el.hasPointerCapture(grasp.current.id))) {
      if (moveable.current?.isDragging()) {
        // Moveable sends no end of the drag: the desk's scroll at its edge stops here.
        stopDeskScroll();
        moveable.current.stopDrag();
      } else {
        grasp.current!.el.releasePointerCapture(grasp.current!.id);
        setDraft(grasp.current!.draft);
      }
      adjusting.current = undefined;
      // A drag that has changed nothing yet has no step to take back.
      if (mergeKey.current === "drag") setHist((h) => returned(h, ahead.current));
      mergeKey.current = "";
      return;
    }
    // A text being written in keeps F6, and its own Escape, which ends the writing.
    const away = !target.closest(".ProseMirror, .sheet textarea:not([readonly])");
    // F6 walks the focus as in PowerPoint: from the sheet to the bar Einfügen, the header, the panel and back to
    // the sheet, and with Shift the other way round. Tab cannot: on the sheet it picks blocks. The browser's own
    // F6 would go to its address bar. A part that is shut, or holds nothing to press, is no stop.
    if (e.key === "F6" && away && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      const lead = (el: Element | null) => [...(el?.querySelectorAll<HTMLElement>("button:enabled, select:enabled, input:enabled") ?? [])].find((c) => c.getClientRects().length);
      const parts = ['[role=toolbar][aria-label="Einfügen"]', "header", ".panel"].map((s) => document.querySelector(s)).filter(lead);
      if (e.shiftKey) parts.reverse();
      const to = lead(parts[parts.findIndex((el) => el!.contains(target)) + 1] ?? null);
      if (to) to.focus();
      // Back on the sheet a text still open gets its caret back.
      else back(target);
      return;
    }
    // Escape on a button or a field gives the keys back, as in PowerPoint's ribbon, and the selection stays. Not on
    // a button of a menu that has just shut: it holds the focus until the menu is gone, and the key is the sheet's.
    if (e.key === "Escape" && away && target.closest("button, a, input, select") && !target.closest("dialog")) return back(target);
    // Ctrl+B, I and U alone never reach the browser while a block is selected: Chrome has shortcuts of its own on
    // them. With Shift or Alt they stay the browser's.
    const mark = (e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey;
    if (mark && /^[biu]$/i.test(e.key) && sel.length && !target.closest("input, select")) e.preventDefault();
    // In a text's field, in a table's cell, in the panel's fields for place and size, on its sliders, its checkboxes
    // and its number fields, and on its lists only undo and redo are the sheet's. A number field that holds a number
    // for the panel alone keeps them.
    const ours = (e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key) && target.closest(".ProseMirror, .table, input.mm, input.score, input[type=range], input[type=checkbox], input[type=number]:not(.own), input.typed, select, textarea.wordlist");
    // Ctrl+Shift+C copies the look of the caret's word, Ctrl+Shift+V lays it on the picked words of the text being
    // written, as in PowerPoint. The field's own copy and paste are not wanted for them. With no look picked up,
    // Ctrl+Shift+V stays the browser's paste of plain words.
    const lookKey = (e.ctrlKey || e.metaKey) && e.shiftKey && !e.altKey && e.key.toLowerCase();
    if ((lookKey === "c" || (lookKey === "v" && coat)) && target.closest(".sheet .ProseMirror")) {
      e.preventDefault();
      if (e.key.toLowerCase() === "c") dip(part?.marks);
      else wordPaint(sel.find((b) => b.id === editing)!);
      return;
    }
    return { target, shut, turnKey, mark, ours };
};
  return Object.assign(session, { keyFocus });
}
