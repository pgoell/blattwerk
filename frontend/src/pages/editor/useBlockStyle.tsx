// What a block shows: its words, its list, and its look.
import { useEffect, useRef } from "react";
import { flushSync } from "react-dom";
import { fresh } from "../../history";
import { FIELDS, K, RULINGS, boxed, colsOf, kindOf, rowsOf, sizeOf, squares, sum, tall, type Block, type Box, type Guides, type ListMode, type NameBlock, type TableBlock, type TextProps } from "../../sheet";
import { blatt, followDoc, linked, loose as cutLoose, looseText } from "../../words";
import { list } from "../Field";
import { EDGE, basisOf, heightsOf, next } from "../../cells";
import { grown } from "../../insert";
import { NONE, round } from "./palette";
import { useDocChange } from "./useDocChange";

export function useBlockStyle(session: ReturnType<typeof useDocChange>) {
  const hist = session.hist;
  const live = session.live;
  const own = session.own;
  const at = session.at;
  const setAt = session.setAt;
  const ids = session.ids;
  const setIds = session.setIds;
  const rest = session.rest;
  const setEditing = session.setEditing;
  const words = session.words;
  const sheet = session.sheet;
  const tight = session.tight;
  const pages = session.pages;
  const guides = session.guides;
  const grid = session.grid;
  const learnt = session.learnt;
  const page = session.page;
  const blocks = session.blocks;
  const W = session.W;
  const H = session.H;
  const sel = session.sel;
  const free = session.free;
  const boxes = session.boxes;
  const full = session.full;
  const update = session.update;
  const turn = session.turn;
  const all = (...a: any[]) => (session as Record<string, any>).all(...a);
  const seek = (...a: any[]) => (session as Record<string, any>).seek(...a);
  const shown = (...a: any[]) => (session as Record<string, any>).shown(...a);
function change(fn: (blocks: Block[]) => Block[], key?: string) {
    turn((p) => ({ ...p, blocks: fn(p.blocks) }), key);
  }
  // Sets the number of a score box on page n, the page it stands on: the page in use may have changed since it was
  // opened. Nothing is changed, and no step made, when the box is not there.
  function scoreOn(id: string, max: number, n: number) {
    if (!live.current.doc.pages[n]?.blocks.some((b) => b.id === id && b.type === "points")) return;
    turn((p) => ({ ...p, blocks: p.blocks.map((b) => (b.id === id && b.type === "points" ? ({ ...b, props: { ...b.props, max } } as Block) : b)) }), "", n);
  }
  // Adds `by` to the score of each picked score box, from its own number: the panel's field shows only the first one's.
  function bump(by: number) {
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === "points" ? ({ ...b, props: { ...b.props, max: Math.min(999, Math.max(1, b.props.max + by)) } } as Block) : b)));
  }
  // The Lineatur's text: a mode links each picked Lineatur to the sheet's list, none cuts each loose with its words.
  // One step for all of them.
  function takeList(mode?: ListMode) {
    // A Lineatur being written in ends its writing: linked, it has no field left to write in.
    if (mode) setEditing("");
    // A block of a group with a locked one is as fixed as the locked one: it takes the list and does not grow.
    const fixed = sel.filter((b) => !free.includes(b)).map((b) => b.id);
    change((bs) =>
      bs.map((b) => {
        if (!ids.includes(b.id) || b.type !== "ruling") return b;
        if (!mode) return cutLoose(b, learnt);
        return fixed.includes(b.id) ? { ...b, props: { ...b.props, list: mode } } : linked(b, mode, learnt, W, H);
      }),
    );
  }
  // A text or shape takes the sheet's list, or is cut loose with the words as its own text. One step for all of them.
  function takeText(on: boolean) {
    // A text being written in ends its writing: linked, it has no field left to write in.
    if (on) setEditing("");
    tight.current = true;
    change((bs) =>
      bs.map((b) => {
        const text = boxed(b);
        if (!ids.includes(b.id) || !text || (!on && text.list !== true)) return b;
        return { ...b, props: on ? { ...b.props, list: true } : looseText(b.props as Partial<TextProps>, learnt) } as Block;
      }),
    );
  }
  // Sets the columns, the Lückenwörter and their seed of a linked text or shape. Other blocks stay as they are.
  function feed(props: object, key?: string) {
    tight.current = true;
    change(
      (bs) => bs.map((b) => (ids.includes(b.id) && boxed(b)?.list === true ? ({ ...b, props: { ...b.props, ...fresh(b, props) } } as Block) : b)),
      key,
    );
  }
  // The list field of the Lernwörter tab shows the sheet's list, one word to a line. An empty field removes the list.
  // A changed list changes every linked text on the page, which the grow effect measures. Linked rulings grow in the
  // same step, and a stack the page cannot hold runs on to a new page.
  function listWords(value: string) {
    tight.current = true;
    update((doc) => followDoc({ ...doc, words: value === "" ? undefined : value.split("\n") }), "words");
  }
  // The caret of the list field goes behind a paste once the paste is drawn, as React sets the value only then.
  const listField = useRef<HTMLTextAreaElement>(null);
  const caretAt = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (caretAt.current === undefined) return;
    listField.current?.setSelectionRange(caretAt.current, caretAt.current);
    caretAt.current = undefined;
  });
  // The Lernwörter-Blatt comes behind the page in use, and is the page in use from then on. On an empty page it fills
  // that page instead. Its size is the sheet's, or the empty page's own.
  function addBlatt() {
    const n = page;
    const empty = live.current.doc.pages[n].blocks.length === 0;
    const [w, h] = empty ? sizeOf(live.current.doc, n) : live.current.doc.landscape ? [297, 210] : [210, 297];
    // One undo step for every page of the Blatt: the first fills the empty page or comes after the page in use, the rest follow it.
    const [first, ...rest] = blatt(learnt, w, h).map((page) => page.map((b, i) => ({ ...b, id: crypto.randomUUID(), z: i + 1, locked: false }) as Block));
    if (empty) {
      // The empty page keeps what is its own, and the run-on pages lie as it does.
      const { landscape } = live.current.doc.pages[n];
      const lie = landscape === undefined ? {} : { landscape };
      update((doc) => ({ ...doc, pages: [...doc.pages.slice(0, n), { ...doc.pages[n], blocks: first }, ...rest.map((blocks) => ({ ...lie, blocks })), ...doc.pages.slice(n + 1)] }), "", n);
      setIds([]);
      return;
    }
    flushSync(() => {
      update((doc) => ({ ...doc, pages: [...doc.pages.slice(0, n + 1), { blocks: first }, ...rest.map((blocks) => ({ blocks })), ...doc.pages.slice(n + 1)] }), "", n + 1);
      setAt(n + 1);
      setIds([]);
    });
    seek();
  }
  // Changes the sheet's guide lines, or with `n` those of that page alone.
  function rules(n: number | undefined, fn: (g: Guides) => Guides, key?: string) {
    if (n === undefined) update((doc) => ({ ...doc, guides: fn(doc.guides) }), key);
    else turn((p) => ({ ...p, guides: fn(p.guides ?? NONE) }), key, n);
  }
  // The heights of a table's own rows as the screen lays them out now, in mm. The grid's rows after them are the box of
  // solution words. Undefined when the grid is not there or its rows do not parse.
  function screenRows(b: Block): number[] | undefined {
    const grid = sheet.current?.querySelector<HTMLElement>(`[data-id="${b.id}"] .table`);
    if (!grid || b.type !== "table") return undefined;
    const px = getComputedStyle(grid).gridTemplateRows.split(" ").slice(0, b.props.cells.length).map((p) => parseFloat(p) / K);
    return px.length === b.props.cells.length && !px.some(Number.isNaN) ? px : undefined;
  }
  // Whether a table has no spare room now: then it may come down with the texts that go from its cells. A table made
  // taller than its rows need keeps that height.
  function snug(b: TableBlock): boolean {
    const grid = sheet.current?.querySelector<HTMLElement>(`[data-id="${b.id}"] .table`);
    if (!grid) return false;
    const own = grid.style.height;
    grid.style.height = "auto";
    const full = parseFloat(getComputedStyle(grid).height) / K >= b.h - 0.05;
    grid.style.height = own;
    return full;
  }
  // The height in mm that a table's box of solution words needs: the grid's rows after the table's own, read with the
  // grid's height free. In a table with spare room the box is stretched as the rows are, and that share is the rows'.
  function boxOf(grid: HTMLElement, rows: number): number {
    const own = grid.style.height;
    grid.style.height = "auto";
    const box = getComputedStyle(grid).gridTemplateRows.split(" ").slice(rows).reduce((all, p) => all + (parseFloat(p) || 0) / K, 0);
    grid.style.height = own;
    return box;
  }
  function place(boxes: [string, Partial<Box>][], key?: string) {
    const byId = new Map(boxes);
    change(
      (bs) =>
        bs.map((b) => {
          const patch = byId.get(b.id);
          // A table with row heights keeps them in proportion to its height. The rows are those on screen, unless a
          // press below the texts has flattened them: then the saved rows still hold the proportion (#514). A row the
          // text holds up is taller on screen than it is saved, and that proportion grows (#540).
          const rows = b.type === "table" && patch?.h !== undefined && b.h > EDGE && patch.h !== b.h ? heightsOf(b.props) : undefined;
          if (!rows) return { ...b, ...patch };
          // A row as high as it is saved is taken as saved: the screen lays rows out on parts of a pixel.
          const screen = screenRows(b)?.map((h, i) => (Math.abs(h - rows[i]) <= 0.05 ? rows[i] : h));
          if (screen && sum(screen) > 0) {
            // The rows fill the height without the table's line and the box of solution words.
            const to = patch!.h! - EDGE - boxOf(sheet.current!.querySelector<HTMLElement>(`[data-id="${b.id}"] .table`)!, screen.length);
            if (to <= 0) return { ...b, ...patch };
            const basis = basisOf(rows, screen);
            return { ...b, ...patch, props: { ...b.props, rows: basis.map((h) => (h * to) / sum(basis)) } } as Block;
          }
          const f = (patch!.h! - EDGE) / (b.h - EDGE);
          return { ...b, ...patch, props: { ...b.props, rows: rows.map((h) => h * f) } } as Block;
        }),
      key,
    );
  }
  // `only` names the picked blocks of the type that take the props, where not all of them do.
  function style(type: Block["type"], props: object, key?: string, only?: string[]) {
    if (type === "table" || key === "words") tight.current = true;
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || b.type !== type || (only && !only.includes(b.id))) return b;
          const next = { ...b, props: { ...b.props, ...fresh(b, props) } } as Block;
          return { ...next, ...grown(b, next, hist.doc, H) } as Block;
        }),
      key,
    );
  }
  // The text typed into a ruling is set, and in the same change the block grows by whole rows when the text needs more
  // rows than it has. A Karo needs the rows of its squares. A Lineatur's field scrolls past its last row, so its
  // scroll height is taller than its box: the lines are that height in rows. Growth stops at the foot of the page, and
  // a block never shrinks by itself. Text and height share the typing's key, so one undo step takes both back.
  function typeRuling(b: Extract<Block, { type: "ruling" }>, text: string, area: HTMLTextAreaElement) {
    const { row, at } = RULINGS[kindOf(b.props.kind)];
    const have = rowsOf(b);
    const need = at
      ? area.scrollHeight > area.clientHeight + 1 ? Math.round(area.scrollHeight / (row * K)) : 0
      : Math.max(0, ...squares(text, colsOf(b)).map(([, y]) => y + 1));
    // Near the foot it takes the rows that still fit the page, not none.
    const rows = Math.max(have, Math.min(need, Math.floor((H - b.y) / row + 0.05)));
    const h = round(rows * row);
    const grows = rows > have;
    change(
      (bs) =>
        bs.map((x) =>
          ids.includes(x.id) && x.type === "ruling"
            ? ({ ...x, ...(grows && x.id === b.id ? tall(x, h) : {}), props: { ...x.props, ...fresh(x, { text }) } } as Block)
            : x,
        ),
      "text",
    );
  }
  // Shows or hides field i of every picked name line, in one step. Each line has its own words, so i is its own field.
  // A line whose one shown field is i, which stays shown.
  const onlyShown = (b: NameBlock, i: number) => {
    const off = new Set(b.props.hidden ?? []);
    return !off.has(i) && (b.props.fields ?? FIELDS).every((_, j) => j === i || off.has(j));
  };
  function showField(i: number, shown: boolean) {
    change((bs) =>
      bs.map((b) => {
        if (!ids.includes(b.id) || b.type !== "name" || (!shown && onlyShown(b, i))) return b;
        const off = shown ? (b.props.hidden ?? []).filter((h) => h !== i) : [...new Set([...(b.props.hidden ?? []), i])].sort((x, y) => x - y);
        return { ...b, props: { ...b.props, hidden: off.length ? off : undefined } } as Block;
      }),
    );
  }
    return Object.assign(session, { change, scoreOn, bump, takeList, takeText, feed, listWords, listField, caretAt, addBlatt, rules, screenRows, snug, boxOf, place, style, typeRuling, onlyShown, showField });
}
