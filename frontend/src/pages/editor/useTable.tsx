// A table's cells, its lines and its borders.
import type { KeyboardEvent as Key, PointerEvent } from "react";
import { open } from "../../saves";
import { K, MARGIN, PT, spliced, sum, type Block, type TableBlock } from "../../sheet";
import { mark as markCopy } from "../../clip";
import { EDGE, anchorOf, beside, emptied, evened, merged, next, rectOf, sized, slotsIn, spanAt, spansOf, tsvOf, unmerged, widthsOf, type Rect } from "../../cells";
import { bordered, cutLines, lined, type Border } from "../../borders";
import type { LineStyle, Pen } from "../../edges";
import { round } from "./palette";
import { useMove } from "./useMove";

export function useTable(session: ReturnType<typeof useMove>) {
  const over = session.over;
  const hist = session.hist;
  const at = session.at;
  const ids = session.ids;
  const editing = session.editing;
  const setEditing = session.setEditing;
  const slot = session.slot;
  const setSlot = session.setSlot;
  const reach = session.reach;
  const setReach = session.setReach;
  const laid = session.laid;
  const caret = session.caret;
  const entire = session.entire;
  const field = session.field;
  const sheet = session.sheet;
  const left = session.left;
  const draft = session.draft;
  const mergeKey = session.mergeKey;
  const ahead = session.ahead;
  const grasp = session.grasp;
  const tight = session.tight;
  const sink = session.sink;
  const grab = session.grab;
  const grid = session.grid;
  const page = session.page;
  const sizes = session.sizes;
  const W = session.W;
  const k = session.k;
  const from = session.from;
  const free = session.free;
  const line = session.line;
  const table = session.table;
  const top = session.top;
  const cellsCopied = session.cellsCopied;
  const change = session.change;
  const snug = session.snug;
  const style = session.style;
  const add = session.add;
  const pending = session.pending;
  const all = session.all;
  const edge = session.edge;
  const each = session.each;
// Tab goes to the next cell of a table and Shift+Tab to the one before, as in PowerPoint. Past the last cell a
  // new row begins.
  // The text of cells on the system's clipboard, as copy() does for blocks: the browser's copy first, then the fallback.
  function copyCells(tsv: string) {
    cellsCopied.current = tsv;
    pending.current = tsv;
    document.execCommand("copy");
    markCopy(tsv);
    if (pending.current === null) return;
    pending.current = null;
    navigator.clipboard?.writeText(tsv).catch(() => {});
  }
  function hop(e: Key<HTMLTextAreaElement>, b: TableBlock) {
    // Escape and F2 end the writing themselves: after a press in the panel a blur would not.
    if (e.key === "Escape" || e.key === "F2") {
      setEditing("");
      setReach(undefined);
    }
    // With two or more cells picked, the keys work on all of them: Entf and Backspace empty them, Ctrl+C copies them as
    // text, Ctrl+X copies and empties them. The cells stay picked. Ctrl+V is the paste, see onPaste.
    if (reach !== undefined && slotsIn(b.props, rectOf(b.props, slot, reach)).length > 1) {
      const rect = rectOf(b.props, slot, reach);
      const ctrl = e.ctrlKey || e.metaKey;
      const key = e.key.toLowerCase();
      if (ctrl && (key === "c" || key === "x")) {
        e.preventDefault();
        copyCells(tsvOf(b.props, rect));
        if (key === "x") {
          mergeKey.current = "";
          tight.current = true;
          sink.current = snug(b);
          change((bs) => bs.map((o) => (o.id === b.id ? { ...b, props: emptied(b.props, rect) } : o)));
        }
        return;
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        // Not through the field's change, which would drop the pick.
        mergeKey.current = "";
        tight.current = true;
        sink.current = snug(b);
        change((bs) => bs.map((o) => (o.id === b.id ? { ...b, props: emptied(b.props, rect) } : o)));
        return;
      }
    }
    // An arrow at the edge of the text goes on to the next cell, when there is one in that way.
    const plain = !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey;
    const field = e.currentTarget;
    const at = field.selectionStart;
    const line = sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] [data-cell="${slot}"] p.open`);
    let to: number | undefined;
    if (e.key.startsWith("Arrow")) setReach(undefined);
    if (plain && line && at === field.selectionEnd) {
      if (e.key === "ArrowLeft" && at === 0) to = next(b.props, slot, -1);
      if (e.key === "ArrowRight" && at === field.value.length) to = next(b.props, slot, 1);
      if (e.key === "ArrowUp" && sameLine(line, at, 0)) to = beside(b.props, slot, "up");
      if (e.key === "ArrowDown" && sameLine(line, at, field.value.length)) to = beside(b.props, slot, "down");
    }
    if (to !== undefined) {
      e.preventDefault();
      mergeKey.current = "";
      setReach(undefined);
      setSlot(to);
      return;
    }
    if (e.key !== "Tab") return;
    e.preventDefault();
    // What is typed in the next cell is an undo step of its own.
    mergeKey.current = "";
    setReach(undefined);
    const after = next(b.props, slot, e.shiftKey ? -1 : 1);
    if (after !== undefined) {
      // The next cell's text is picked, so that typing replaces it.
      entire.current = true;
      setSlot(after);
    }
    else if (!e.shiftKey) {
      const rows = b.props.cells.length;
      rank(b, "row", rows, true);
      setSlot(rows * b.props.cols.length);
    }
  }
  // Whether the caret at `at` of a cell's text stands on its first (0) or last line: the same top as the text's edge.
  function sameLine(line: HTMLElement, at: number, edge: number) {
    const top = (n: number) => {
      let left = n;
      const walk = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
      for (let t = walk.nextNode() as Text | null; t; t = walk.nextNode() as Text | null) {
        if (left <= t.length) {
          const range = document.createRange();
          range.setStart(t, left);
          range.collapse(true);
          return range.getBoundingClientRect().top;
        }
        left -= t.length;
      }
      return line.getBoundingClientRect().top;
    };
    return Math.abs(top(at) - top(edge)) < 2;
  }
  // Makes the picked cells of the table being edited one cell. It is one step of undo.
  function merge() {
    if (!table || reach === undefined) return;
    const rect = rectOf(table.props, slot, reach);
    mergeKey.current = "";
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: merged(table.props, rect) } : o)));
    setSlot(rect[0] * table.props.cols.length + rect[1]);
    setReach(undefined);
  }
  // Brings back the single cells of the merged cell at the open cell. The freed cells stay picked.
  function unmerge() {
    if (!table) return;
    const [r, c, h, w] = spanAt(table.props, slot);
    if (h * w < 2) return;
    mergeKey.current = "";
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: unmerged(table.props, slot) } : o)));
    setReach((r + h - 1) * table.props.cols.length + c + w - 1);
  }
  // The heights of the rows as the grid lays them out now, in mm.
  // The grid's rows after the table's own hold no cells: the box of solution words is one. No heights are known
  // while the grid has not laid its rows out.
  const mmOf = (px: string) => {
    const all = px.split(" ").slice(0, table?.props.cells.length).map((p) => parseFloat(p) / K);
    return all.length === table?.props.cells.length && !all.some(Number.isNaN) ? all : [];
  };
  const laidMm = mmOf(laid);
  // The heights in mm that the rows' texts need, read from the grid with its rows free.
  function needs(grid: HTMLElement): number[] {
    const [rows, height] = [grid.style.gridTemplateRows, grid.style.height];
    grid.style.gridTemplateRows = "none";
    grid.style.height = "auto";
    const px = getComputedStyle(grid).gridTemplateRows;
    grid.style.gridTemplateRows = rows;
    grid.style.height = height;
    return mmOf(px);
  }
  // Sets the width of the picked columns, or the open cell's, or the height of the rows. With cells picked each
  // one becomes `mm`; else the open cell's lines keep their share and sum to `mm`. It is one step of undo.
  function sizeCells(axis: "col" | "row", mm: number) {
    if (!table || !(mm > 0)) return;
    const [r, c, h, w] = spanAt(table.props, slot);
    const [r0, c0, r1, c1]: Rect = reach === undefined ? [r, c, r + h - 1, c + w - 1] : rectOf(table.props, slot, reach);
    const each = reach !== undefined;
    const [from, to] = axis === "col" ? [c0, c1] : [r0, r1];
    const least = axis === "col" ? 5 : 0;
    const value = each ? Math.max(least, mm) : Math.max(least * (to - from + 1), mm);
    const base = axis === "col" ? widthsOf(table.props.cols, table.w) : laidMm;
    if (!base.length) return;
    // A share rounded to nothing would be no height at all.
    const sizes = sized(base.map(round), from, to, value, each).map((s) => Math.max(0.01, round(s)));
    tight.current = true;
    change((bs) =>
      bs.map((o) =>
        o.id !== table.id ? o : axis === "col" ? { ...table, w: round(sum(sizes) + EDGE), props: { ...table.props, cols: sizes } } : { ...table, h: round(sum(sizes) + EDGE), props: { ...table.props, rows: sizes } },
      ),
    );
  }
  // Makes the picked columns or rows equal within the room they hold: all of them with no cell picked. The rows
  // take the higher of their share and the height their texts need. It is one step of undo.
  function evenCells(axis: "col" | "row") {
    if (!table) return;
    const all: Rect = [0, 0, table.props.cells.length - 1, table.props.cols.length - 1];
    const [r0, c0, r1, c1] = reach === undefined ? all : rectOf(table.props, slot, reach);
    const [from, to] = axis === "col" ? [c0, c1] : [r0, r1];
    tight.current = true;
    if (axis === "col") {
      const cols = evened(widthsOf(table.props.cols, table.w), from, to).map(round);
      change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: { ...table.props, cols } } : o)));
      return;
    }
    const grid = sheet.current!.querySelector<HTMLElement>(`[data-id="${table.id}"] .table`);
    if (!grid || !laidMm.length) return;
    const top = needs(grid).slice(from, to + 1);
    const picked = laidMm.slice(from, to + 1);
    const share = round(Math.max(sum(picked) / picked.length, ...top));
    const rows = sized(laidMm.map(round), from, to, share, true).map(round);
    change((bs) => bs.map((o) => (o.id === table.id ? { ...table, h: round(sum(rows) + EDGE), props: { ...table.props, rows } } : o)));
  }
  // Sets the line style or width of every picked table, each line of it. A drag of the slider passes its `key`, so that
  // the whole drag is one step of undo.
  function drawLines(patch: { style?: LineStyle; width?: number }, key?: string) {
    if (!key) tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === "table" ? ({ ...b, props: lined(b.props, patch) } as Block) : b)), key);
  }
  // Draws the pen on the chosen borders: of the cells picked with the open one, or of the open cell alone, or with no
  // cell open, of the whole table. It is one step of undo, and the cells stay picked.
  function border(which: Border, pen: Pen) {
    if (!table) return;
    const open = editing === table.id;
    const [r, c, h, w] = spanAt(table.props, slot);
    const rect: Rect = !open ? [0, 0, table.props.cells.length - 1, table.props.cols.length - 1] : reach === undefined ? [r, c, r + h - 1, c + w - 1] : rectOf(table.props, slot, reach);
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === table.id ? { ...table, props: bordered(table.props, rect, which, pen) } : o)));
  }
  // Turns Schneidelinien on or off for every picked table.
  function cutting(on: boolean) {
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === "table" ? ({ ...b, props: cutLines(b.props, on) } as Block) : b)));
  }
  // Adds an empty row or column to a table before the one at `i`, or takes the one at `i` away; the last one
  // stays. A new row adds its height to the block, a line of text with the cell's padding and line, and
  // a row that goes takes with it the height it has now. The field stays with its cell, and goes to a neighbour
  // when its cell goes.
  function rank(b: TableBlock, axis: "row" | "col", i: number, add: boolean, after = false) {
    const [rows, cols] = [b.props.cells.length, b.props.cols.length];
    const n = axis === "row" ? rows : cols;
    if (!add && n < 2) return;
    // A row's height is read from its first cell, or from the grid when that cell is covered or spans rows.
    const table = sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] .table`)!;
    const first = table.querySelector<HTMLElement>(`[data-cell="${i * cols}"]`);
    const gone = first && !first.dataset.span ? first.getBoundingClientRect().height / k : parseFloat(getComputedStyle(table).gridTemplateRows.split(" ")[i]) / K;
    const dh = axis === "col" ? 0 : add ? b.props.size * PT * 1.6 + 0.25 : -gone;
    // A column that comes or goes takes its average width or its own width from the block, so the others keep theirs.
    const widths = widthsOf(b.props.cols, b.w);
    // A new column widens the table only to the right margin; there the columns narrow (#602).
    const dw = axis === "row" ? 0 : add ? Math.min(sum(widths) / widths.length, Math.max(0, W - MARGIN - b.x - b.w)) : -widths[i];
    const to = (at: number) => (add ? at + +(i <= at) : Math.min(at - +(i < at), n - 2));
    const [r, c] = [Math.floor(slot / cols), slot % cols];
    const target = axis === "row" ? to(r) * cols + c : r * (cols + (add ? 1 : -1)) + to(c);
    const props = spliced(b.props, axis, i, add, after);
    if (add && target !== slot) caret.current = sheet.current!.querySelector<HTMLTextAreaElement>(".table textarea")?.selectionStart;
    setSlot(anchorOf(props, target));
    setReach(undefined);
    tight.current = true;
    change((bs) => bs.map((o) => (o.id === b.id ? { ...b, w: round(b.w + dw), h: round(b.h + dh), props } : o)));
  }
  // Moves the line right of column `i` with the pointer. The columns on its two sides share the width they had,
  // and each keeps 5 mm, or half of it where they have less.
  function widen(e: PointerEvent, b: TableBlock, i: number) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const cols = [...b.props.cols];
    const mm = b.w / sum(cols);
    const left = sum(cols.slice(0, i));
    const pair = cols[i] + cols[i + 1];
    const least = Math.min(5 / mm, pair / 2);
    cols[i] = Math.max(least, Math.min(pair - least, (point(e)[0] - b.x) / mm - left));
    cols[i + 1] = pair - cols[i];
    style("table", { cols }, "drag");
  }
  // Where the line right of column `i` shows, as [top, height] in mm of the page: all of the table's height, or
  // the rows between the merged cells that lie over it. The rows' heights are the grid's own (`laid`).
  function shown(b: TableBlock, i: number): [number, number][] {
    const over = spansOf(b.props).filter(([, c, , w]) => c <= i && i + 1 < c + w);
    if (!over.length) return [[b.y, b.h]];
    const heights = laid.split(" ").map((px) => parseFloat(px) / K);
    if (heights.length < b.props.cells.length || heights.some(Number.isNaN)) return [];
    const free = b.props.cells.map((_, r) => !over.some(([at, , h]) => r >= at && r < at + h));
    return free.flatMap((is, r) => (is && !free[r - 1] ? [[b.y + sum(heights.slice(0, r)), sum(heights.slice(r, free.indexOf(false, r) < 0 ? free.length : free.indexOf(false, r)))] as [number, number]] : []));
  }
  // An end handle remembers where the pointer took hold of it, so the end does not jump under the finger.
  function grip(e: PointerEvent) {
    const at = e.currentTarget.getBoundingClientRect();
    grab.current = [e.clientX - at.left - at.width / 2, e.clientY - at.top - at.height / 2];
    ahead.current = hist.future;
    grasp.current = { el: e.currentTarget, id: e.pointerId, draft };
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  // Where on the page, in mm, the pointer puts the handle it holds.
  function point(e: PointerEvent) {
    const page = e.currentTarget.closest(".sheet")!.getBoundingClientRect();
    return [(e.clientX - grab.current[0] - page.left) / k, (e.clientY - grab.current[1] - page.top) / k];
  }
    return Object.assign(session, { copyCells, hop, sameLine, merge, unmerge, mmOf, laidMm, needs, sizeCells, evenCells, drawLines, border, cutting, rank, widen, shown, grip, point });
}
