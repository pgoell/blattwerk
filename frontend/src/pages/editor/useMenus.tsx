// The commands of the right-click menu and the zoom control.
import { useLayoutEffect } from "react";
import { flushSync } from "react-dom";
import { ChevronLeft, ClipboardPaste, Copy, CopyPlus, Eraser, Group, FilePlus, FileX, Fullscreen, Lock, LockOpen, Paintbrush, RotateCcw, RotateCw, Scissors, Trash2, Ungroup, ZoomIn, ZoomOut } from "lucide-react";
import { Link } from "react-router";
import Logo from "../../components/Logo";
import type { Item } from "../../components/Menu";
import { isLine, tied } from "../../sheet";
import { spanAt } from "../../cells";
import { Tool } from "./Tool";
import { ALIGNS, APPLE, grouped } from "./palette";
import { usePick } from "./usePick";

export type Command = Exclude<Item, "sep">;

export function useMenus(session: ReturnType<typeof usePick>) {
  const over = session.over;
  const title = session.title;
  const at = session.at;
  const setAt = session.setAt;
  const ids = session.ids;
  const setIds = session.setIds;
  const brush = session.brush;
  const setBrush = session.setBrush;
  const editing = session.editing;
  const slot = session.slot;
  const reach = session.reach;
  const part = session.part;
  const menu = session.menu;
  const setMenu = session.setMenu;
  const setLens = session.setLens;
  const tab = session.tab;
  const side = session.side;
  const left = session.left;
  const right = session.right;
  const room = session.room;
  const zoom = session.zoom;
  const setZoom = session.setZoom;
  const fitted = session.fitted;
  const fitOn = session.fitOn;
  const fitTick = session.fitTick;
  const setFitTick = session.setFitTick;
  const thumb = session.thumb;
  const asked = session.asked;
  const desk = session.desk;
  const moveable = session.moveable;
  const pages = session.pages;
  const page = session.page;
  const chosenNow = session.chosenNow;
  const choiceOf = session.choiceOf;
  const W = session.W;
  const H = session.H;
  const fit = session.fit;
  const cell = session.cell;
  const k = session.k;
  const zoomTo = session.zoomTo;
  const sel = session.sel;
  const free = session.free;
  const thing = session.thing;
  const things = session.things;
  const source = session.source;
  const table = session.table;
  const top = session.top;
  const rules = session.rules;
  const place = session.place;
  const dip = session.dip;
  const addPage = session.addPage;
  const visit = session.visit;
  const removePages = session.removePages;
  const copyPages = session.copyPages;
  const pageOf = session.pageOf;
  const put = session.put;
  const copy = session.copy;
  const cut = session.cut;
  const clippedPages = session.clippedPages;
  const storePages = session.storePages;
  const pastePages = session.pastePages;
  const cutPages = session.cutPages;
  const pasteAny = session.pasteAny;
  const remove = session.remove;
  const wide = session.wide;
  const joinable = session.joinable;
  const splittable = session.splittable;
  const join = session.join;
  const split = session.split;
  const stacked = session.stacked;
  const raise = session.raise;
  const align = session.align;
  const spin = session.spin;
  const merge = session.merge;
  const unmerge = session.unmerge;
  const writable = session.writable;
  const edit = session.edit;
  const done = session.done;
// With nothing free in it the selection is held, be it by a locked block of its group that is not picked.
  const locked = sel.length > 0 && !free.length;
  // A right click on the desk picks as in PowerPoint and opens the menu. In a field the browser's own stays: false.
  function menuAt(el: Element, x: number, y: number) {
    // In the table being edited the menu holds the merge commands, once cells are picked or a merged cell is open.
    const onCell = table && editing === table.id && el.closest(`[data-id="${table.id}"] :is([data-cell], textarea)`);
    if (onCell && (reach !== undefined || spanAt(table.props, slot)[2] * spanAt(table.props, slot)[3] > 1)) {
      setMenu({ x, y, cells: true });
      return true;
    }
    if (el.closest(".ProseMirror, textarea, input, select")) return false;
    // Moveable's area and a line's handles lie over a selection, so the block is looked up under them. Beside a block
    // there the selection stays.
    const over = moveable.current!.isMoveableElement(el) || !!el.closest(".end, .adjust, .bar, .crop");
    const id = (over ? document.elementsFromPoint(x, y).find((o) => o.matches(".block")) : el.closest(".block"))?.getAttribute("data-id");
    const to = pageOf(el);
    // A block of the selection keeps it whole. Another one is picked with its group, and the empty page picks nothing.
    if (to !== page || (id ? !ids.includes(id) : !over)) {
      done();
      setAt(to);
      setIds(id ? grouped([id], pages[to].blocks) : []);
    }
    // The cell under the click, for Text bearbeiten: the menu runs after the click has closed it, so it is kept here.
    const cell = el.closest<HTMLElement>("[data-cell]")?.dataset.cell;
    setMenu({ x, y, cell: cell === undefined ? undefined : +cell });
    return true;
  }
  function thumbMenu(n: number, x: number, y: number) {
    // The menu hands the focus back when it closes: to a field, that would keep the sheet's keys.
    (document.activeElement as HTMLElement | null)?.blur();
    // A page in the choice keeps it; any other is chosen alone.
    if (!chosenNow.includes(n)) visit(n);
    setMenu({ x, y, thumb: n });
  }
  const none = !sel.length;
  const ctrl = APPLE ? "⌘" : "Strg+";
  const shift = APPLE ? "⇧" : "Umschalt+";
  const thumbed = menu?.thumb;
  const ruled = menu?.rule;
  const menuCell = menu?.cell;
  // One block with words of its own, or a score or a name, opens for writing from its menu, as F2 does. Not a linked one.
  // It opens a moment later: the menu's dialog gives the focus back as it shuts, and in WebKit after the text took it.
  const [only] = sel;
  const writeIn: Item[] =
    sel.length === 1 && (writable(only) || only.type === "points" || only.type === "name") && !tied(only) && editing !== only.id
      ? ["sep", { label: "Text bearbeiten", keys: "F2", disabled: !free.length, run: () => {
            asked.current = { id: only.id, cell: menuCell };
            setTimeout(() => {
              // A key typed in the meantime has opened it already. The request stays until the sheet's keys know the
              // block is open: a key in between opens it again in its cell, not the first cell after its text.
              if (asked.current?.id !== only.id) return;
              flushSync(() => edit(only.id, undefined, true, menuCell));
            });
          } }, "sep"]
      : [];
  const clips: Command[] = [
    { label: "Ausschneiden", icon: Scissors, keys: `${ctrl}X`, disabled: !free.length, run: cut },
    { label: "Kopieren", icon: Copy, keys: `${ctrl}C`, disabled: none, run: copy },
    { label: "Einfügen", icon: ClipboardPaste, keys: `${ctrl}V`, run: pasteAny },
  ];
  const copies: Command[] = [
    { label: "Duplizieren", icon: CopyPlus, keys: `${ctrl}D`, disabled: none, run: () => put(sel) },
    { label: "Löschen", icon: Trash2, keys: "Entf", disabled: !free.length, run: remove },
  ];
  const lockIt: Command = { label: locked ? "Entsperren" : "Sperren", icon: locked ? LockOpen : Lock, disabled: none, run: () => place((locked ? wide : sel).map((b) => [b.id, { locked: !locked }])) };
  const groups: Command[] = [
    { label: "Gruppieren", icon: Group, keys: `${ctrl}G`, disabled: !joinable, run: join },
    { label: "Gruppierung aufheben", icon: Ungroup, keys: `${ctrl}${shift}G`, disabled: !splittable, run: split },
  ];
  // The block menu's row of icon buttons: turn, align and the brush, as the panel and the bar have them.
  // A selection held by a locked block, though that one is not picked, turns no more than in the panel.
  const turnless = free.length !== sel.length || sel.some((b) => b.type === "table" || (isLine(b) && thing(b) === b.id));
  const mini: Command[] = [
    { label: "Linksdrehung 90°", icon: RotateCcw, disabled: turnless, run: () => spin(-90) },
    { label: "Rechtsdrehung 90°", icon: RotateCw, disabled: turnless, run: () => spin(90) },
    ...ALIGNS.map(([axis, at, label, icon]): Command => ({ label, icon, disabled: !things.length, run: () => align(axis, at) })),
    { label: "Format übertragen", icon: Paintbrush, disabled: !brush && !source, run: () => (dip(part?.marks), setBrush(1)) },
  ];
  // The block menu, which has the row. Not the Mehr list, the thumbs, a guide line or a table's cells.
  const blockMenu = !menu?.more && menu?.thumb === undefined && !menu?.rule && !menu?.cells && sel.length > 0;
  // The box around the picked blocks, which the row keeps clear of.
  const pickedBox = () => {
    // On the whole desk: a right click on a block of another page picks it in the same render that brings its page.
    const rs = sel.map((b) => desk.current?.querySelector(`[data-id="${b.id}"]`)?.getBoundingClientRect()).filter((r): r is DOMRect => !!r);
    if (!rs.length) return undefined;
    return { left: Math.min(...rs.map((r) => r.left)), top: Math.min(...rs.map((r) => r.top)), right: Math.max(...rs.map((r) => r.right)), bottom: Math.max(...rs.map((r) => r.bottom)) };
  };
  const items: Item[] =
    ruled
      ? // Only the one line goes, as one undo step: no merge key, so no other change joins it.
        [{ label: "Hilfslinie entfernen", icon: Eraser, run: () => rules(ruled.n, (g) => ({ ...g, [ruled.axis]: g[ruled.axis].filter((_, j) => j !== ruled.i) })) }]
      : thumbed !== undefined
      ? [
          { label: "Neue Seite", icon: FilePlus, run: () => addPage(thumbed) },
          { label: "Seite duplizieren", icon: CopyPlus, run: () => copyPages(choiceOf(thumbed)) },
          { label: "Seite löschen", icon: FileX, disabled: choiceOf(thumbed).length >= pages.length, run: () => removePages(choiceOf(thumbed)) },
          { label: "Ausschneiden", icon: Scissors, keys: `${ctrl}X`, disabled: choiceOf(thumbed).length >= pages.length, run: () => cutPages(choiceOf(thumbed)) },
          { label: "Kopieren", icon: Copy, keys: `${ctrl}C`, run: () => storePages(choiceOf(thumbed)) },
          { label: "Einfügen", icon: ClipboardPaste, keys: `${ctrl}V`, disabled: !clippedPages().pages.length, run: () => pastePages(thumbed) },
        ]
      : [
          ...(table && editing === table.id
            ? ([
                { label: "Zellen verbinden", disabled: reach === undefined, run: merge },
                { label: "Zellen teilen", disabled: !(spanAt(table.props, slot)[2] * spanAt(table.props, slot)[3] > 1), run: unmerge },
                "sep",
              ] as Item[])
            : []),
          ...clips,
          ...writeIn,
          ...copies,
          "sep",
          lockIt,
          "sep",
          ...groups,
          "sep",
          { label: "In den Vordergrund", disabled: none || !stacked(true), run: () => raise(true) },
          { label: "Eine Ebene nach vorn", disabled: none || !stacked(true, true), run: () => raise(true, true) },
          { label: "Eine Ebene nach hinten", disabled: none || !stacked(false, true), run: () => raise(false, true) },
          { label: "In den Hintergrund", disabled: none || !stacked(false), run: () => raise(false) },
        ];
  const mode = side ? "Vorlagen" : tab === "Ansicht" ? "Ansicht" : "Start";
  const brand = (
    <Link to="/" className="brand" aria-label="Meine Blätter" title="Meine Blätter">
      <Logo />
      <ChevronLeft size={16} aria-hidden />
    </Link>
  );
  // The buttons walk fixed steps of a quarter around the page's width, so the way back passes the same sizes, also
  // from either end and after a pinch.
  function zoomBy(by: number) {
    const n = Math.log(zoom) / Math.log(1.25);
    const to = by > 0 ? Math.floor(n + 1e-6) + 1 : Math.ceil(n - 1e-6) - 1;
    zoomTo(1.25 ** to);
  }
  // The whole page in use, width and height, until a zoom by hand: it follows the desk when the window changes.
  function fitPage() {
    fitted.current = true;
    fitOn.current = page;
    // 120 is the desk's padding above and below. The whole box, not clientHeight: that leaves out the bar along the
    // bottom, which goes once the page fits, and the desk has no border to take off.
    setZoom(Math.min(4, Math.max(0.25, Math.min(room / W, (desk.current!.offsetHeight - 120) / H) / fit)));
    setFitTick((n) => n + 1);
  }
  // The scroll follows the zoom once it is drawn: the rects read before that are the old size's. The page is the one
  // in use when the fit was made.
  useLayoutEffect(() => {
    if (!fitted.current) return;
    const el = desk.current!;
    const [sheetRect, box] = [el.querySelector(`.sheet[data-page="${fitOn.current}"]`)!.getBoundingClientRect(), el.getBoundingClientRect()];
    // The page lies in the middle, across, also beside a wider one, and its top under the desk's padding.
    el.scrollBy(sheetRect.left + sheetRect.width / 2 - box.left - el.clientWidth / 2, sheetRect.top - box.top - 32);
  }, [fitTick]);
  const zoomer = (
    <>
      <Tool icon={ZoomOut} label="Kleiner" onClick={() => zoomBy(-1)} />
      {/* The page's size on the screen against its size on paper. */}
      {/* The list opens over the button: upward from the dock, downward from the bar. */}
      <button
        className="zoom"
        title="Zoom"
        aria-haspopup="dialog"
        onClick={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          const up = !!e.currentTarget.closest(".dock");
          setLens({ x: box.left, y: up ? box.top : box.bottom, up });
        }}
      >
        {Math.round((k * 2540) / 96)} %
      </button>
      <Tool icon={Fullscreen} label="Ganze Seite" onClick={fitPage} />
      <Tool icon={ZoomIn} label="Größer" onClick={() => zoomBy(1)} />
    </>
  );
    return Object.assign(session, { locked, menuAt, thumbMenu, none, ctrl, shift, thumbed, ruled, menuCell, only, writeIn, clips, copies, lockIt, groups, turnless, mini, blockMenu, pickedBox, items, mode, brand, zoomBy, fitPage, zoomer });
}
