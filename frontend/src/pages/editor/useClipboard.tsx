// Copy, cut and paste of blocks and of pages.
import { useEffect, useRef } from "react";
import { flushSync } from "react-dom";
import { fresh } from "../../history";
import { stored, tied, type Block, type Page } from "../../sheet";
import { landed as carried } from "../../words";
import { pictureOf } from "../../picture";
import { atOnce, copied, hash, onTheWay, refused as refusedWords } from "../../clip";
import { parasFromHtml } from "../../pasted";
import { grouped, wholeBlock, cloned } from "./palette";
import { useInsert } from "./useInsert";

export function useClipboard(session: ReturnType<typeof useInsert>) {
  const user = session.user;
  const live = session.live;
  const setAt = session.setAt;
  const setChosen = session.setChosen;
  const ids = session.ids;
  const setIds = session.setIds;
  const words = session.words;
  const fits = session.fits;
  const tight = session.tight;
  const held = session.held;
  const pages = session.pages;
  const page = session.page;
  const blocks = session.blocks;
  const sel = session.sel;
  const free = session.free;
  const ns = session.ns;
  const writing = session.writing;
  const stamped = session.stamped;
  const update = session.update;
  const change = session.change;
  const removePages = session.removePages;
  const seek = session.seek;
  const looked = session.looked;
  const add = session.add;
  const upload = session.upload;
  const put = session.put;
  const pending = session.pending;
  const wordsOf = session.wordsOf;
  const carrying = session.carrying;
  const done = (...a: any[]) => (session as Record<string, any>).done(...a);
  const align = (...a: any[]) => (session as Record<string, any>).align(...a);
function copy(held = sel) {
    if (!held.length) return;
    // A linked Lineatur is drawn from the sheet's list, so the list goes along with it.
    const linkedAny = held.some(tied);
    localStorage.setItem("clip", JSON.stringify({ owner: user.id, blocks: carrying(held), ...(linkedAny && { words: live.current.doc.words }) }));
    // The newest copy wins: pages copied before are no longer what a paste on a thumbnail brings.
    localStorage.removeItem("pages");
    const words = wordsOf(held);
    localStorage.setItem("copied", hash(words));
    pending.current = words;
    stamped.current = false;
    // The copy event's clipboardchange is ours. A change we did not count is a picture copied afterwards.
    const watching = listens.current;
    if (watching) credited.current++;
    if (!document.execCommand("copy") && watching) credited.current = Math.max(0, credited.current - 1);
    pending.current = null;
    copied();
    writing.current++;
    onTheWay(toClipboard(held, words).catch(() => {}).finally(() => writing.current--));
  }
  // The words and a picture of the blocks go out together. The write starts in the key press, as Safari wants; the
  // picture is drawn after it, and a refused picture still leaves the words.
  // A copy made while an earlier one's picture is still drawn wins: the earlier write is called off.
  // So does a picture copied from elsewhere while this one is still drawn: the late write would replace it (#1011).
  const lastCopy = useRef(0);
  // clipboardchange events this page is about to cause. One it did not cause means the clipboard moved on.
  const credited = useRef(0);
  const listens = useRef(false);
  useEffect(() => {
    const clip = navigator.clipboard;
    if (!clip?.addEventListener) return;
    listens.current = true;
    const moved = () => {
      if (credited.current > 0) {
        credited.current--;
        return;
      }
      lastCopy.current++;
    };
    clip.addEventListener("clipboardchange", moved);
    return () => {
      listens.current = false;
      clip.removeEventListener("clipboardchange", moved);
    };
  }, []);
  const countChange = () => listens.current && credited.current++;
  const dropChange = () => {
    if (listens.current) credited.current = Math.max(0, credited.current - 1);
  };
  // Whether the clipboard still holds this copy's words. A read the browser refuses counts as yes: the picture
  // goes out as before, and a browser that can say the clipboard moved does so through clipboardchange.
  async function stillHolds(words: string): Promise<boolean> {
    try {
      const want = words.replace(/\r\n/g, "\n");
      for (const item of await navigator.clipboard.read()) {
        if (!item.types.includes("text/plain")) continue;
        const got = (await (await item.getType("text/plain")).text()).replace(/\r\n/g, "\n");
        if (got === want) return true;
      }
      return false;
    } catch {
      return true;
    }
  }
  // The write starts in the key press, as Safari wants, and the picture fills it in when drawn. It is filled in
  // only while the clipboard is still this copy: a picture copied from elsewhere meanwhile stays (#1011). A write
  // this page starts in between waits until this one has landed, so it cannot be replaced by the late picture.
  function toClipboard(held: Block[], words: string): Promise<void> {
    const n = ++lastCopy.current;
    let settle: (blob: Blob) => void = () => {};
    let cancel: (err: Error) => void = () => {};
    const png = new Promise<Blob>((res, rej) => {
      settle = res;
      cancel = rej;
    });
    png.catch(() => {});
    const text = new Blob([words], { type: "text/plain" });
    let gone = false;
    let backed = false;
    const giveUp = () => {
      if (lastCopy.current === n) lastCopy.current++;
      gone = true;
      cancel(new Error("clipboard moved"));
    };
    const wordsOnly = () => {
      if (backed || gone || n !== lastCopy.current || !navigator.clipboard?.writeText) return Promise.resolve();
      backed = true;
      countChange();
      return navigator.clipboard.writeText(words).catch(() => dropChange());
    };
    let gesture: Promise<void>;
    try {
      gesture = atOnce(() => navigator.clipboard.write([new ClipboardItem({ "image/png": png, "text/plain": text })]));
    } catch {
      cancel(new Error("no write"));
      return wordsOnly();
    }
    const drawn = pictureOf(held, live.current.doc, page)
      .then(async (blob) => {
        if (n !== lastCopy.current) {
          cancel(new Error("newer copy"));
          return;
        }
        if (!(await stillHolds(words)) || n !== lastCopy.current) {
          giveUp();
          return;
        }
        countChange();
        settle(blob);
      })
      .catch(() => {
        cancel(new Error("no picture"));
        return wordsOnly();
      });
    return Promise.all([gesture.catch(() => wordsOnly()), drawn]).then(() => {});
  }
  // Only what is free goes. With nothing free the clipboard keeps what it held.
  function cut() {
    copy(free);
    remove();
  }
  // The store is open to an older build and to anyone: only this account's whole blocks reach the sheet.
  // With the words the copy carried, if any: they are not checked here, as `landed` reads them.
  function clipped(): { blocks: Block[]; words?: unknown } {
    let held: { owner?: number; blocks?: Block[]; words?: unknown } | null = null;
    try {
      held = JSON.parse(localStorage.getItem("clip") ?? "null");
    } catch {
      return { blocks: [] };
    }
    return held?.owner === user.id && Array.isArray(held.blocks) && held.blocks.every(wholeBlock) ? { blocks: held.blocks, words: held.words } : { blocks: [] };
  }
  function clip(): Block[] {
    return clipped().blocks;
  }
  // The pages copied in the panel Seiten, read the same way: this account's, each page with whole blocks.
  function clippedPages(): { pages: Page[]; words?: unknown } {
    let held: { owner?: number; pages?: Page[]; words?: unknown } | null = null;
    try {
      held = JSON.parse(localStorage.getItem("pages") ?? "null");
    } catch {
      return { pages: [] };
    }
    const fits = (p: Page) => !!p && typeof p === "object" && Array.isArray(p.blocks) && p.blocks.every(wholeBlock);
    return held?.owner === user.id && Array.isArray(held.pages) && held.pages.every(fits) ? { pages: held.pages, words: held.words } : { pages: [] };
  }
  // Stores the pages chosen, in their order, with the words of a linked Lineatur as the block copy does.
  function storePages(ns: number[]) {
    const held = [...ns].sort((a, b) => a - b).map((i) => live.current.doc.pages[i]);
    const linkedAny = held.some((p) => p.blocks.some(tied));
    localStorage.setItem("pages", JSON.stringify({ owner: user.id, pages: held.map((p) => ({ ...p, blocks: carrying(p.blocks) })), ...(linkedAny && { words: live.current.doc.words }) }));
  }
  // The pasted pages come after page `after`, with blocks of their own, and are the choice from then on. One step of undo.
  function pastePages(after: number) {
    const { pages: held, words } = clippedPages();
    if (!held.length) return;
    const copies = held.map((p) => ({ ...p, blocks: cloned(p.blocks, p.blocks) }));
    const got = carried(copies.flatMap((p) => p.blocks), words, live.current.doc);
    let taken = 0;
    const fresh = copies.map((p) => {
      const blocks = got.blocks.slice(taken, (taken += p.blocks.length));
      return { ...p, blocks };
    });
    done();
    flushSync(() => {
      update((doc) => ({ ...doc, ...(got.words && { words: got.words }), pages: [...doc.pages.slice(0, after + 1), ...fresh, ...doc.pages.slice(after + 1)] }), "", after + 1);
      setAt(after + 1);
      setChosen(fresh.map((_, j) => after + 1 + j));
      setIds([]);
    });
    seek();
  }
  // Cut: the pages are stored, then taken away. Not when they are every page.
  function cutPages(ns: number[]) {
    if (ns.length >= live.current.doc.pages.length) return;
    storePages(ns);
    removePages(ns);
  }
  function paste() {
    const { blocks: held, words } = clipped();
    if (!held.length) return;
    const got = carried(held, words, live.current.doc);
    put(got.blocks, got.words);
  }
  // The system's clipboard holds the words of the newest copy. Words that are not the copied blocks' own were copied
  // in another app, or in a field: they make a text block that grows to hold them, as in PowerPoint. Says whether
  // they did. The editor's own words never do, for this account or the next: there the blocks' owner decides.
  // Whether words are the editor's own copy. A copy of the build before left no mark: its words are those of the stored blocks.
  function ownCopy(words: string) {
    const [copied, held] = [localStorage.getItem("copied"), clip()];
    return copied === null ? held.length > 0 && words === wordsOf(held) : copied === hash(words);
  }
  function typed(got: string, html = "") {
    const words = got.replace(/\r\n/g, "\n");
    if (!words.trim() || ownCopy(words)) return false;
    tight.current = true;
    // Words with their bold, italic, underline and colour keep them. Word ends a whole line with a break, which would make an empty last paragraph.
    const paras = parasFromHtml(html);
    const props = paras.length ? stored(paras) : { text: words.replace(/\n+$/, "") };
    add(80, 12, { type: "text", props: { ...props, size: 14, align: "left" } }, looked(), true);
    return true;
  }
  // A second press while the system's clipboard is still being read would paste onto the same spot.
  const reading = useRef(false);
  // The button has no paste of the browser's to go by, so it asks the system's clipboard itself: for a picture
  // first, then for words.
  async function pasteAny() {
    if (reading.current) return;
    if (writing.current && !stamped.current) {
      // The words have not reached the clipboard, so a picture there is the one copied before.
      reading.current = true;
      queueMicrotask(() => (reading.current = false));
      return paste();
    }
    reading.current = true;
    let words = "";
    let html = "";
    try {
      for (const item of await navigator.clipboard.read()) {
        // The editor's own copy brings its blocks, though it comes with a picture of them too.
        if (item.types.includes("text/plain")) {
          words = await (await item.getType("text/plain")).text();
          if (refusedWords(words)) return;
          if (ownCopy(words.replace(/\r\n/g, "\n"))) return paste();
        }
        const type = item.types.find((t) => t.startsWith("image/"));
        if (type) return upload(new File([await item.getType(type)], "bild", { type }), true);
        if (item.types.includes("text/html")) html = await (await item.getType("text/html")).text();
      }
    } catch {
      // No leave to read, or a browser that cannot: the copied blocks are still there.
    } finally {
      reading.current = false;
    }
    if (!typed(words, html)) paste();
  }
  // What is locked stays, and stays picked: "Entsperren" is one click away. With nothing free there is no undo step.
  function remove() {
    const gone = free.map((b) => b.id);
    if (!gone.length) return;
    change((bs) => bs.filter((b) => !gone.includes(b.id)));
    setIds(ids.filter((id) => !gone.includes(id)));
  }
  const all = () => setIds(blocks.map((b) => b.id));
  // The selection with its groups made whole: grouping and ungrouping work on whole groups.
  const wide = blocks.filter((b) => grouped(ids, blocks).includes(b.id));
  // Grouping needs two things to join: blocks or groups.
  const joinable = new Set(sel.map((b) => b.group?.[0] ?? b.id)).size > 1;
  const splittable = sel.some((b) => b.group);
  // What a click on a block picks: its whole group, or the block alone once a part of its group is picked.
  const unit = (id: string) => {
    const mates = grouped([id], blocks);
    const picked = mates.filter((i) => ids.includes(i)).length;
    return picked && picked < mates.length ? [id] : mates;
  };
    return Object.assign(session, { copy, lastCopy, toClipboard, cut, clipped, clip, clippedPages, storePages, pastePages, cutPages, paste, ownCopy, typed, reading, pasteAny, remove, all, wide, joinable, splittable, unit });
}
