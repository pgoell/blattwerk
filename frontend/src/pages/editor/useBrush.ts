// The format painter, and undo and redo.
import { useRef } from "react";
import { flushSync } from "react-dom";
import { fresh } from "../../history";
import { TextSelection } from "prosemirror-state";
import { bandOf, boxed, cleared, isLine, listOf, listed, mathsHeight, overFoot, parasOf, sizeOf, stored, tall, type Block, type List } from "../../sheet";
import { hole, list, tint, type Marks } from "../Field";
import { allCells, allGaps, everyNth, everyNthCell } from "../../gaps";
import { next } from "../../cells";
import { has } from "../Format";
import type { Coat } from "./palette";
import { WORDS, takes, BARE, round, step } from "./palette";
import { useBlockStyle } from "./useBlockStyle";

export function useBrush(session: ReturnType<typeof useBlockStyle>) {
  const opened = session.opened;
  const hist = session.hist;
  const live = session.live;
  const setHist = session.setHist;
  const own = session.own;
  const setAt = session.setAt;
  const setChosen = session.setChosen;
  const ids = session.ids;
  const setIds = session.setIds;
  const coat = session.coat;
  const setCoat = session.setCoat;
  const openNow = session.openNow;
  const editing = session.editing;
  const slot = session.slot;
  const clicked = session.clicked;
  const field = session.field;
  const sheet = session.sheet;
  const left = session.left;
  const name = session.name;
  const setDraft = session.setDraft;
  const desk = session.desk;
  const mergeKey = session.mergeKey;
  const tight = session.tight;
  const press = session.press;
  const start = session.start;
  const pages = session.pages;
  const page = session.page;
  const blocks = session.blocks;
  const sel = session.sel;
  const from = session.from;
  const stroke = session.stroke;
  const source = session.source;
  const rulers = session.rulers;
  const table = session.table;
  const top = session.top;
  const turn = session.turn;
  const change = session.change;
  const place = session.place;
  const style = session.style;
  const edge = (...a: any[]) => (session as Record<string, any>).edge(...a);
  const mark = (...a: any[]) => (session as Record<string, any>).mark(...a);
  const edit = (...a: any[]) => (session as Record<string, any>).edit(...a);
  const all = (...a: any[]) => (session as Record<string, any>).all(...a);
  const seek = (...a: any[]) => (session as Record<string, any>).seek(...a);
// Sets what a shape and a text share: the frame, and the text in it.
  function look(props: object, key?: string) {
    tight.current = true;
    // A line style or a width turns on the border of each box that has none, as in PowerPoint.
    const edge = "dash" in props || "strokeWidth" in props;
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || (b.type !== "shape" && b.type !== "text")) return b;
          // A line holds no words: what belongs to them passes it by, and the frame's look lands as on any shape.
          const own = isLine(b) ? Object.fromEntries(Object.entries(props).filter(([name]) => !WORDS.includes(name))) : props;
          if (!Object.keys(own).length) return b;
          const on = edge && (b.props.stroke ?? "none") === "none" && { stroke: "#222222" };
          return { ...b, props: { ...b.props, ...fresh(b, own), ...on } } as Block;
        }),
      key,
    );
  }
  // A picture's see-through, on every picked picture, in one step.
  function fadePicture(opacity: number) {
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === "image" ? { ...b, props: { ...b.props, opacity } } : b)), "opacity");
  }
  // Sets the trace text's look on every picked block that carries text, in one step: a text, a shape, a table and a
  // Lineatur each have it. A Lineatur that shows the Lernwörter has a look of its own and takes none.
  function traced(props: object) {
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && (b.type === "table" || (b.type === "ruling" && !listOf(b)) ||((b.type === "text" || b.type === "shape") && !isLine(b))) ? ({ ...b, props: { ...b.props, ...fresh(b, props) } } as Block) : b)));
  }
  // The panel's bold, italic, underline and colour go to the field while a text is written, as in PowerPoint.
  // Else they go to the whole of every selected block, and there take the place of what its words had of their own.
  function paint(props: Marks, key?: string) {
    if (field.current && tint(field.current, props, boxed(sel.find((b) => b.id === editing)!)!, key)) return;
    tight.current = true;
    change(
      (bs) =>
        bs.map((b) => {
          const text = ids.includes(b.id) && boxed(b);
          return text ? ({ ...b, props: { ...b.props, ...(text.rich && cleared(text.rich, props)), ...fresh(b, props) } } as Block) : b;
        }),
      key,
    );
  }
  // The brush picks up the look of the source. Every key is in it, also where the block has nothing
  // there: the block painted then loses its own, as in PowerPoint.
  function dip(marks?: Marks) {
    if (!source) return;
    const from = { ...(boxed(source) ?? source.props), ...marks, mark: source.mark } as Coat;
    // A table's `color` is the colour of its text: its lines have `line`.
    from.rule = source.type === "table" ? source.props.line : from.color;
    // The band a Lineatur shows, set by hand or its kind's own: a Lineatur 3 with none takes the band off a Lineatur 1.
    if (source.type === "ruling") from.band = bandOf(source);
    // A field says "not bold" where a block says nothing: both are the same look. A band switched off is a look too:
    // it stays false, or the target would fall back to its kind's default, which is on for Lineatur 1 and 2.
    setCoat(Object.fromEntries(takes(source).map((name) => [name, from[name] === false && name !== "band" ? undefined : from[name]])));
  }
  // Lays the brush's look on the picked words of a text being written, in one undo step. A look that says "not bold"
  // says it as false, so the words lose their own bold and colour where the look has none.
  function wordPaint(b: Block) {
    const text = b && boxed(b);
    // Only what the look has of words: one from a line or a picture has none, and leaves the words as they are.
    const has = (name: keyof Coat) => !!coat && name in coat;
    if (!field.current || !text || !coat || !(["bold", "italic", "underline", "color"] as const).some(has)) return false;
    const marks: Marks = {};
    for (const name of ["bold", "italic", "underline"] as const) if (has(name)) marks[name] = coat[name] ?? false;
    if (has("color")) marks.color = coat.color ?? text.color ?? "#222222";
    return tint(field.current, marks, text, "");
  }
  openNow.current = (id, el) => {
    clicked.current = undefined;
    edit(id, el);
  };
  // A drag with the brush over a text or a shape with words: the field opens at the press, and the words the pointer
  // crosses take the look. A press that does not move paints the whole block, as a click does.
  function brushDrag(id: string, el: Element, press: globalThis.MouseEvent, on: string[]) {
    const start: [number, number] = [press.clientX, press.clientY];
    let opened = false;
    const move = (e: globalThis.PointerEvent) => {
      if (!opened) {
        if (Math.hypot(e.clientX - start[0], e.clientY - start[1]) <= 3) return;
        opened = true;
        if (editing !== id) {
          // A text of a picked group is picked alone, as the field's words go to every picked block. A locked or a
          // linked text opens no field: its group stays picked, and it is painted whole.
          if (on.length > 1) flushSync(() => setIds([id]));
          flushSync(() => openNow.current(id, el));
          if (on.length > 1 && !field.current) flushSync(() => setIds(on));
        }
      }
      const view = field.current;
      const from = view?.posAtCoords({ left: start[0], top: start[1] });
      const to = view?.posAtCoords({ left: e.clientX, top: e.clientY });
      if (view && from && to) view.dispatch(view.state.tr.setSelection(TextSelection.between(view.state.doc.resolve(from.pos), view.state.doc.resolve(to.pos))));
    };
    // The words are picked, not moved: the browser's drag of a selected text would move them.
    const stop = (e: Event) => e.preventDefault();
    // A drag the browser calls off, or that the window loses, paints nothing.
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", end);
      window.removeEventListener("blur", end);
      window.removeEventListener("dragstart", stop);
    };
    const up = () => {
      end();
      const view = field.current;
      if (!(opened && view && !view.state.selection.empty && wordPaint(blocks.find((b) => b.id === id)!))) daub(on, page);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", end);
    window.addEventListener("blur", end);
    window.addEventListener("dragstart", stop);
  }
  // Lays the look on blocks of page `n`. Each takes what it has, and its words lose what they had of their own
  // there. All of it is one undo step, and none where nothing changes.
  function daub(on: string[], n = page) {
    if (!coat) return;
    const dab = (b: Block) => {
      if (!on.includes(b.id)) return b;
      // A line never vanishes: it takes a border only from a block that has one.
      // Nor do a table's or a Lineatur's lines: a table made outside the editor may name no colour for its own.
      // A Lineatur that shows its band as the brush does keeps what it stores of it: the band of its kind stays unset.
      const own = takes(b).filter((name) => name in coat && name !== "mark" && !(isLine(b) && (coat.stroke ?? "none") === "none") && !(name === "rule" && !coat.rule) && !(name === "band" && b.type === "ruling" && bandOf(b) === coat.band));
      // The colour of a Lineatur's lines is its `color`, that of a table's lines its `line`.
      const props = Object.fromEntries(own.map((name) => [name === "rule" ? (b.type === "table" ? "line" : "color") : name, coat[name] ?? (b.type === "shape" ? BARE[name] : undefined)]));
      const rich = own.length ? boxed(b)?.rich : undefined;
      // What is left unset goes, so a saved sheet opens as it looks here.
      const all = Object.entries({ ...b.props, ...(rich && cleared(rich, props)), ...props }).filter(([, value]) => value !== undefined);
      const next = { ...b, mark: coat.mark, props: Object.fromEntries(all) } as Block;
      if (!next.mark) delete next.mark;
      // A maths block is as high as its exercises need, as from the panel.
      if (next.type === "maths" && b.type === "maths" && overFoot(b, next.props, sizeOf(live.current.doc, n)[1])) {
        // A painted type size that would push the block past the page's foot is not painted: the size stays.
        return { ...next, props: { ...next.props, size: b.props.size } };
      }
      return next.type === "maths" && b.type === "maths" && mathsHeight(next.props) !== mathsHeight(b.props) ? { ...next, ...tall(b, mathsHeight(next.props)) } : next;
    };
    if (pages[n].blocks.every((b) => JSON.stringify(dab(b)) === JSON.stringify(b))) return;
    tight.current = true;
    turn((p) => ({ ...p, blocks: p.blocks.map(dab) }), undefined, n);
  }
  // A list is for the paragraphs the caret stands in, or with no field for every paragraph of the selected blocks.
  // Asked for again, it goes.
  function itemize(kind: List) {
    if (field.current) return list(field.current, kind);
    const on = sel.map(boxed).find((p) => p)!;
    const to = parasOf(on)[0].list === kind ? undefined : kind;
    tight.current = true;
    change((bs) => bs.map((b) => (ids.includes(b.id) && boxed(b) ? ({ ...b, props: { ...b.props, ...listed(boxed(b)!, to) } } as Block) : b)));
  }
  // The gaps of a Lückentext. In a text being written in, the picked words become a gap or stop being one; in a table
  // cell being written in, that cell does. Else every selected block that holds words is a gap as a whole.
  // A block with no words takes no gap: its props stay as they are.
  const wordy = (b: Block) => {
    const text = boxed(b);
    // A linked text draws the sheet's list, which takes no gap.
    if (text?.list === true) return false;
    return b.type === "table" ? b.props.cells.flat().some(Boolean) : !!text && parasOf(text).some((p) => p.runs.some((r) => r.text));
  };
  function gapping(on: boolean) {
    if (field.current) return hole(field.current, on);
    if (!sel.some(wordy)) return;
    tight.current = true;
    if (table && editing === table.id) {
      const { cols, cells, gaps } = table.props;
      const [r, c] = [Math.floor(slot / cols.length), slot % cols.length];
      const next = cells.map((row, i) => row.map((_, j) => (i === r && j === c ? on : !!gaps?.[i]?.[j])));
      return style("table", { gaps: next.some((row) => row.some(Boolean)) ? next : undefined }, "");
    }
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || !wordy(b)) return b;
          if (b.type === "table") return { ...b, props: { ...b.props, gaps: allCells(b.props.cells, on) } } as Block;
          const text = boxed(b);
          return text ? ({ ...b, props: { ...b.props, ...stored(allGaps(parasOf(text), on)) } } as Block) : b;
        }),
      "",
    );
  }
  // Every n-th word of each selected block that holds words is a gap, counted through its text, in one undo step.
  function gapEvery(n: number) {
    if (!sel.some(wordy)) return;
    tight.current = true;
    change(
      (bs) =>
        bs.map((b) => {
          if (!ids.includes(b.id) || !wordy(b)) return b;
          if (b.type === "table") return { ...b, props: { ...b.props, gaps: everyNthCell(b.props.cells, n) } } as Block;
          const text = boxed(b);
          return text ? ({ ...b, props: { ...b.props, ...stored(everyNth(parasOf(text), n)) } } as Block) : b;
        }),
      "",
    );
  }
  // Gives the selected lines a length in mm. Each keeps its angle and the top left corner of its box.
  function extend(to: number) {
    place(
      rulers.map((b) => {
        const now = Math.hypot(b.w, b.h);
        return [b.id, now ? { w: round((b.w * to) / now), h: round((b.h * to) / now) } : { w: to }];
      }),
      "length",
    );
  }
  // The page that fills most of the desk's view becomes the page in use when the teacher scrolls the desk (the wheel,
  // a finger, its scroll bar), so a new block lands where the teacher looks. A scroll the editor makes itself, to
  // show a page or a block, or a zoom with Ctrl and the wheel, leaves the page in use as it is.
  // `steered` is the time until which a scroll counts as the teacher's; `scrollHeld` holds while the scroll bar is held.
  // A text being typed keeps its page; `lagged` says the view moved meanwhile, and the page in view is in use once the
  // text closes.
  const steered = useRef(0);
  const scrollHeld = useRef(false);
  const lagged = useRef(false);
  // Undo and redo show the page of their step, as PowerPoint does: page `n` is in use, and the desk scrolls to it.
  // On another page than before nothing is selected, and a crop ends with the picture as it was.
  function show(n: number, step: (h: typeof hist) => typeof hist) {
    mergeKey.current = "";
    [steered.current, scrollHeld.current, lagged.current] = [0, false, false];
    flushSync(() => {
      setHist(step);
      setAt(n);
      // The step may have added or taken pages before the choice: the page of the step alone is chosen.
      setChosen([]);
      if (n === page) return;
      setIds([]);
      setDraft(undefined);
    });
    // A page in use that lies partly in view stays put: the desk does not jump to its top.
    const [on, view] = [sheet.current!.getBoundingClientRect(), desk.current!.getBoundingClientRect()];
    if (n !== page || on.bottom <= view.top || on.top >= view.bottom) seek();
  }
    return Object.assign(session, { look, fadePicture, traced, paint, dip, wordPaint, brushDrag, daub, itemize, wordy, gapping, gapEvery, extend, steered, scrollHeld, lagged, show });
}
