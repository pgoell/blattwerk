// Files and pictures dropped or pasted onto the sheet.
import { useLayoutEffect, useRef } from "react";
import { pasted } from "../../words";
import { hash } from "../../clip";
import { putTsv } from "../../cells";
import type { Block } from "../../sheet";
import { useField } from "./useField";

export function useDrop(session: ReturnType<typeof useField>) {
  const hist = session.hist;
  const chosen = session.chosen;
  const slot = session.slot;
  const words = session.words;
  const field = session.field;
  const inPanel = session.inPanel;
  const written = session.written;
  const back = session.back;
  const desk = session.desk;
  const mergeKey = session.mergeKey;
  const tight = session.tight;
  const sink = session.sink;
  const press = session.press;
  const dragged = session.dragged;
  const page = session.page;
  const table = session.table;
  const dropped = (...a: any[]) => (session as Record<string, any>).dropped(...a);
  const dropLink = (...a: any[]) => (session as Record<string, any>).dropLink(...a);
  const clip = (...a: any[]) => (session as Record<string, any>).clip(...a);
  const snug = (...a: any[]) => (session as Record<string, any>).snug(...a);
  const change = (...a: any[]) => (session as Record<string, any>).change(...a);
  const ownCopy = (...a: any[]) => (session as Record<string, any>).ownCopy(...a);
  const paste = (...a: any[]) => (session as Record<string, any>).paste(...a);
  const typed = (...a: any[]) => (session as Record<string, any>).typed(...a);
  const upload = (...a: any[]) => (session as Record<string, any>).upload(...a);
// The keys do what the latest drawing says, from the moment the editor is drawn. The listener itself stays for
  // good: one that a new drawing swaps while a key is on its way would miss that key.
  const onKey = useRef((_e: KeyboardEvent) => {});
  const onPaste = useRef((_e: ClipboardEvent) => {});
  const onDrag = useRef((_e: DragEvent) => {});
  // A drag that starts in the page, as words dragged in a field do, is the page's own: only one that comes in is taken.
  const fromPage = useRef(false);
  // The sheet and the page in use as last drawn, for what comes back from the server after them.
  const latest = useRef({ doc: hist.doc, page });
  latest.current = { doc: hist.doc, page };
  useLayoutEffect(() => {
    const press = (e: KeyboardEvent) => onKey.current(e);
    const pasted = (e: ClipboardEvent) => onPaste.current(e);
    // A dragged file, like a pasted picture, is caught on the way down, before a text's field or the browser can take it.
    const dragged = (e: DragEvent) => onDrag.current(e);
    // A font or a colour picked with the mouse in the panel gives the keys back, as in PowerPoint: to the text being
    // edited, or else to the sheet. A colour's `change` comes when its picker closes, and after the pick is set.
    // A colour reached by the keys gives them back too: only so is it for what is typed next. Who walks a select
    // with the keys keeps the focus there, and so does who sets a colour with nothing written in.
    const chosen = (e: Event) => {
      const el = e.target as HTMLElement;
      if (!el.matches(".panel select, .panel input[type=color]")) return;
      if (inPanel.current || (el.matches("input") && written())) back(el);
    };
    // Escape and Enter shut the list of a select and give the keys back. Chromium keeps the keydown of a key that
    // shuts an open list to itself, so the keyup tells. Escape goes no further: the selection stays.
    const shut = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      // A font menu's own list is open: its keys are its own.
      if ((e.key === "Escape" || e.key === "Enter") && el.matches(".panel select") && !el.hasAttribute("data-open")) back(el);
    };
    window.addEventListener("change", chosen);
    window.addEventListener("keyup", shut);
    window.addEventListener("keydown", press);
    window.addEventListener("paste", pasted, true);
    window.addEventListener("dragover", dragged, true);
    window.addEventListener("drop", dragged, true);
    const began = () => (fromPage.current = true);
    const ended = () => (fromPage.current = false);
    window.addEventListener("dragstart", began);
    window.addEventListener("dragend", ended);
    return () => {
      window.removeEventListener("dragstart", began);
      window.removeEventListener("dragend", ended);
      window.removeEventListener("change", chosen);
      window.removeEventListener("keyup", shut);
      window.removeEventListener("keydown", press);
      window.removeEventListener("paste", pasted, true);
      window.removeEventListener("dragover", dragged, true);
      window.removeEventListener("drop", dragged, true);
    };
  }, []);
  // The browser would open a dropped file in place of the editor, so a drag with files is the editor's everywhere.
  // Only the desk takes them, and not while a dialog is open. Text dragged in a field and Moveable's own drags bring
  // no files and stay as they are. The photo field of the feedback dialog takes its own.
  // A picture dragged from another web page brings no file, only its address: the same rule, for the desk alone.
  // Only an address counts (selected words bring text/html too), and never over a field, which takes it as text.
  onDrag.current = (e) => {
    const types = e.dataTransfer?.types ?? [];
    if (e.type === "drop") fromPage.current = false;
    const files = types.includes("Files");
    const inField = e.target instanceof Element && !!e.target.closest(".ProseMirror, textarea, input");
    const link = !files && !fromPage.current && !inField && types.includes("text/uri-list");
    if (!files && !link) return;
    if (files && document.querySelector("dialog:modal .pick")?.contains(e.target as Node)) return;
    e.preventDefault();
    e.stopPropagation();
    const on = desk.current!.contains(e.target as Node) && !document.querySelector("dialog:modal");
    if (e.type === "dragover") e.dataTransfer!.dropEffect = on ? "copy" : "none";
    else if (on && files) dropped([...e.dataTransfer!.files], e.clientX, e.clientY);
    else if (on) dropLink(e.dataTransfer!, e.clientX, e.clientY);
  };
  // The text of the last cells copied: a paste of exactly that, with line breaks, spreads over the cells.
  const cellsCopied = useRef("");
  // In a browser that makes no such copy the words land a moment later: until then a paste still finds the older
  // picture there, which is stale.
  const writing = useRef(0);
  // Ctrl+V comes as the browser's paste, which alone brings a picture copied in another app. A field keeps a paste
  // of words as its own. A picture has no place in a text's, a cell's or a Lineatur's field, so it lands on the
  // sheet as from anywhere else; one that comes with words, as cells copied in Excel do, stays the field's.
  // Outside a field, words copied in another app make a text block; the editor's own bring the copied blocks.
  onPaste.current = (e) => {
    // Another account's copy: its words stay on the system's clipboard after its logout. No field or text of this account takes them.
    if (localStorage.getItem("copied") === hash((e.clipboardData?.getData("text/plain") ?? "").replace(/\r\n/g, "\n")) && !clip().length) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    if (document.querySelector("dialog:modal")) return;
    // Words with tabs, or the cells copied, spread over the table's cells from the open one on: one step of undo.
    const text = e.clipboardData?.getData("text/plain") ?? "";
    if ((e.target as HTMLElement).closest(".sheet .table textarea") && table && (text.includes("\t") || (text.includes("\n") && text.replace(/\r\n/g, "\n") === cellsCopied.current))) {
      e.preventDefault();
      e.stopPropagation();
      mergeKey.current = "";
      tight.current = true;
      sink.current = snug(table);
      change((bs: Block[]) => bs.map((o) => (o.id === table.id ? { ...table, props: putTsv(table.props,[Math.floor(slot / table.props.cols.length), slot % table.props.cols.length], text) } : o)));
      return;
    }
    const field = (e.target as HTMLElement).closest(".ProseMirror, textarea, input, select");
    const picture = [...(e.clipboardData?.files ?? [])].find((f) => f.type.startsWith("image/"));
    const words = !field?.matches(".sheet .ProseMirror, .sheet textarea") || e.clipboardData!.types.includes("text/plain");
    if (field && (words || !picture || writing.current)) return;
    // The editor's own copy comes with its picture: the blocks come first.
    if (ownCopy(text.replace(/\r\n/g, "\n")) && !writing.current) {
      e.preventDefault();
      e.stopPropagation();
      paste();
      return;
    }
    if (!picture || writing.current) {
      if (writing.current || !typed(e.clipboardData?.getData("text/plain") ?? "", e.clipboardData?.getData("text/html"))) paste();
      return;
    }
    e.preventDefault();
    // The field does not take it too.
    e.stopPropagation();
    upload(picture, true);
  };
    return Object.assign(session, { onKey, onPaste, onDrag, fromPage, latest, cellsCopied, writing });
}
