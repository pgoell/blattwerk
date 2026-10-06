import { useEffect, useLayoutEffect, useRef, useState, type PointerEvent, type TouchEvent } from "react";
import { flushSync } from "react-dom";
import Moveable, { type OnDrag, type OnResize } from "react-moveable";
import Selecto from "react-selecto";

// One page's blocks, as the sheet document stores them: mm from the page's top-left corner.
type Box = { id: string; x: number; y: number; w: number; h: number; z: number; locked: boolean };
type Kind = "rect" | "rounded" | "circle" | "line" | "arrow";
type Corner = "nw" | "ne" | "sw" | "se";
type Align = "left" | "center" | "right";
type TextBlock = Box & { type: "text"; props: { text: string; size: number; align: Align } };
// A line or arrow runs from the corner `from` of its box to the opposite one.
type ShapeBlock = Box & { type: "shape"; props: { kind: Kind; fill: string; stroke: string; strokeWidth: number; from?: Corner } };
type Block = TextBlock | ShapeBlock;
type Axis = "x" | "y";

const W = 210;
const H = 297;
const MARGIN = 15;
const PT = 25.4 / 72; // mm per point
const SIDES = { top: true, left: true, bottom: true, right: true, center: true, middle: true };
const CORNERS = ["nw", "ne", "sw", "se"];
// Snap lines on the page: the margins and the centre.
const XS = [MARGIN, W / 2, W - MARGIN];
const YS = [MARGIN, H / 2, H - MARGIN];
const SHAPES: [Kind, string][] = [["rect", "Rechteck"], ["rounded", "Abgerundet"], ["circle", "Kreis"], ["line", "Linie"], ["arrow", "Pfeil"]];
const ALIGNS: [Align, string][] = [["left", "Links"], ["center", "Mitte"], ["right", "Rechts"]];

const round = (n: number) => Math.round(n * 100) / 100;
const idOf = (el: Element) => (el as HTMLElement).dataset.id!;
const spread = (e: TouchEvent) => Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
const centre = (e: TouchEvent) => [(e.touches[0].clientX + e.touches[1].clientX) / 2, (e.touches[0].clientY + e.touches[1].clientY) / 2];
const isLine = (b: Block): b is ShapeBlock => b.type === "shape" && (b.props.kind === "line" || b.props.kind === "arrow");
// Whether a line's start, or its end, sits at the bottom (axis 0) or the right (axis 1) of its box.
const far = (b: ShapeBlock, axis: 0 | 1, end: boolean) => ((b.props.from ?? "nw")[axis] === "se"[axis]) !== end;
// The box around several blocks.
const bounds = (bs: Box[]) => {
  const [x, y] = [Math.min(...bs.map((b) => b.x)), Math.min(...bs.map((b) => b.y))];
  return { x, y, w: Math.max(...bs.map((b) => b.x + b.w)) - x, h: Math.max(...bs.map((b) => b.y + b.h)) - y };
};
// Where the box around some blocks starts and ends.
const span = (boxes: Box[], axis: Axis) => {
  const size = axis === "x" ? "w" : "h";
  return [Math.min(...boxes.map((b) => b[axis])), Math.max(...boxes.map((b) => b[axis] + b[size]))];
};
// A new block's next step along one axis: 5 mm on, or back at the margin where the page ends.
const step = (at: number, max: number) => (at + 5 <= max ? at + 5 : Math.min(MARGIN, max));

export default function Sheets() {
  const [hist, setHist] = useState<{ past: Block[][]; blocks: Block[]; future: Block[][] }>({ past: [], blocks: [], future: [] });
  const [ids, setIds] = useState<string[]>([]);
  const [targets, setTargets] = useState<HTMLElement[]>([]);
  const [clip, setClip] = useState<Block[]>([]);
  const [editing, setEditing] = useState("");
  const [multi, setMulti] = useState(false);
  // The x and y, in mm, that a line's end or a group's corner has snapped to.
  const [guide, setGuide] = useState<(number | undefined)[]>([]);
  // Pixels per mm when the page fills the desk's width; zoom multiplies it.
  const [fit, setFit] = useState(1);
  const [zoom, setZoom] = useState(1);
  const desk = useRef<HTMLDivElement>(null);
  const sheet = useRef<HTMLDivElement>(null);
  const moveable = useRef<Moveable>(null);
  const mergeKey = useRef("");
  const touch = useRef(false);
  const hold = useRef(0);
  const held = useRef(false);
  const grab = useRef([0, 0]);
  const start = useRef<Block[]>([]);
  const pinch = useRef({ spread: 1, zoom: 1, x: 0, y: 0 });

  const { blocks } = hist;
  const k = fit * zoom;
  const sel = blocks.filter((b) => ids.includes(b.id));
  const free = sel.filter((b) => !b.locked);
  const texts = sel.filter((b) => b.type === "text");
  const shapes = sel.filter((b) => b.type === "shape");
  // A line on its own gets a handle at each end. Moveable cannot resize a box with no height, so lines get no corner handles.
  const line = sel.length === 1 ? free.find(isLine) : undefined;
  // Moveable collapses a group that holds a flat line, so a group with a line gets its own corner handles.
  const group = free.length > 1 && free.length === sel.length && sel.some(isLine) ? bounds(sel) : undefined;
  const top = Math.max(0, ...blocks.map((b) => b.z));
  // Snap lines: the page's, then the edges and centres of the blocks that stay put.
  const still = blocks.filter((b) => !ids.includes(b.id));
  const xs = [...XS, ...still.flatMap((b) => [b.x, b.x + b.w / 2, b.x + b.w])];
  const ys = [...YS, ...still.flatMap((b) => [b.y, b.y + b.h / 2, b.y + b.h])];

  useLayoutEffect(() => {
    const observer = new ResizeObserver(([entry]) => setFit(entry.contentRect.width / W));
    observer.observe(desk.current!);
    return () => observer.disconnect();
  }, []);

  // Moveable needs the elements, and they exist only after the blocks render.
  useLayoutEffect(() => {
    setTargets([...sheet.current!.querySelectorAll<HTMLElement>(".block.sel")]);
  }, [ids, blocks.length]);

  useLayoutEffect(() => {
    if (!moveable.current!.isDragging()) moveable.current!.updateRect();
  }, [blocks, k]);

  useLayoutEffect(() => {
    const area = editing ? sheet.current!.querySelector<HTMLTextAreaElement>(`[data-id="${editing}"] textarea`) : null;
    area?.focus();
    // A copy, or a text put back by undo, would start with the caret before the text.
    area?.setSelectionRange(area.value.length, area.value.length);
  }, [editing]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.target as Element).matches("textarea, input")) return;
      const keys: Record<string, () => void> =
        e.ctrlKey || e.metaKey
          ? { z: e.shiftKey ? redo : undo, y: redo, c: () => setClip(sel), v: paste, d: () => put(sel) }
          : { delete: remove, backspace: remove };
      const run = keys[e.key.toLowerCase()];
      if (!run) return;
      e.preventDefault();
      run();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

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

  // Changes that share a key within one gesture (a drag, typing, a colour picker) make one undo step.
  function change(fn: (blocks: Block[]) => Block[], key = "") {
    const merge = key !== "" && key === mergeKey.current;
    mergeKey.current = key;
    setHist((h) => ({ past: merge ? h.past : [...h.past, h.blocks], blocks: fn(h.blocks), future: [] }));
  }
  function place(boxes: [string, Partial<Box>][], key?: string) {
    const byId = new Map(boxes);
    change((bs) => bs.map((b) => ({ ...b, ...byId.get(b.id) })), key);
  }
  function style(type: Block["type"], props: object, key?: string) {
    change((bs) => bs.map((b) => (ids.includes(b.id) && b.type === type ? ({ ...b, props: { ...b.props, ...props } } as Block) : b)), key);
  }
  function undo() {
    mergeKey.current = "";
    setHist((h) => (h.past.length ? { past: h.past.slice(0, -1), blocks: h.past.at(-1)!, future: [h.blocks, ...h.future] } : h));
  }
  function redo() {
    mergeKey.current = "";
    setHist((h) => (h.future.length ? { past: [...h.past, h.blocks], blocks: h.future[0], future: h.future.slice(1) } : h));
  }

  // Moves new blocks as one onto the page, then in steps clear of a block already at that spot.
  function land<T extends Box>(boxes: T[]) {
    const [x, right] = span(boxes, "x");
    const [y, bottom] = span(boxes, "y");
    const [maxX, maxY] = [Math.max(0, W - right + x), Math.max(0, H - bottom + y)];
    let [dx, dy] = [Math.max(0, Math.min(x, maxX)) - x, Math.max(0, Math.min(y, maxY)) - y];
    const taken = () => blocks.some((b) => b.x === round(boxes[0].x + dx) && b.y === round(boxes[0].y + dy));
    // A step for each block is enough to find a free spot, unless the page has none.
    for (let n = 0; n < blocks.length && taken(); n++) {
      dx = step(x + dx, maxX) - x;
      dy = step(y + dy, maxY) - y;
    }
    return boxes.map((b) => ({ ...b, x: round(b.x + dx), y: round(b.y + dy) }));
  }
  function add(w: number, h: number, rest: Pick<TextBlock, "type" | "props"> | Pick<ShapeBlock, "type" | "props">) {
    const id = crypto.randomUUID();
    const y = round(desk.current!.scrollTop / k) + MARGIN;
    const [block] = land([{ id, x: (W - w) / 2, y, w, h, z: top + 1, locked: false, ...rest }]);
    change((bs) => [...bs, block]);
    setIds([id]);
    if (rest.type === "text") setEditing(id);
  }
  function put(from: Block[]) {
    const copies = land(
      [...from].sort((a, b) => a.z - b.z).map((b, i) => ({ ...b, id: crypto.randomUUID(), x: b.x + 5, y: b.y + 5, z: top + 1 + i })),
    );
    change((bs) => [...bs, ...copies]);
    setIds(copies.map((b) => b.id));
    return copies;
  }
  // Pasting again steps on from the last paste.
  const paste = () => setClip(put(clip));
  function remove() {
    change((bs) => bs.filter((b) => !ids.includes(b.id)));
    setIds([]);
  }

  function align(axis: Axis, at: number) {
    const size = axis === "x" ? "w" : "h";
    // One block lines up with the page, several with each other.
    const lo = free.length > 1 ? Math.min(...free.map((b) => b[axis])) : 0;
    const hi = free.length > 1 ? Math.max(...free.map((b) => b[axis] + b[size])) : axis === "x" ? W : H;
    place(free.map((b) => [b.id, { [axis]: round(lo + (hi - lo - b[size]) * at) }]));
  }
  function distribute(axis: Axis) {
    const size = axis === "x" ? "w" : "h";
    const row = [...free].sort((a, b) => a[axis] - b[axis]);
    const end = row.at(-1)![axis] + row.at(-1)![size];
    const gap = (end - row[0][axis] - row.reduce((sum, b) => sum + b[size], 0)) / (row.length - 1);
    let next = row[0][axis];
    place(
      row.map((b) => {
        const at = next;
        next += b[size] + gap;
        return [b.id, { [axis]: round(at) }];
      }),
    );
  }

  // Moveable works in whole pixels and leaves what it snaps up to two off the guide.
  // This is how far to move so that the nearest of `parts` that close lies exactly on it.
  const pull = (at: number, parts: number[], guides: number[]) =>
    parts
      .flatMap((part) => guides.map((g) => g - at - part))
      .filter((d) => Math.abs(d) < 2 / k)
      .sort((a, b) => Math.abs(a) - Math.abs(b))[0] ?? 0;
  const edge = (at: number, guides: number[]) => at + pull(at, [0], guides);

  // Moveable reports px, the document keeps mm. It reads the new size back at once, so render before returning.
  // A group snaps as one box, by its edges or its centre, and all its blocks move by the same amount.
  const drag = (events: OnDrag[]) => {
    const from = events.map((e) => blocks.find((b) => b.id === idOf(e.target))!);
    const to = events.map((e, i) => ({ ...from[i], x: e.left / k, y: e.top / k }));
    const [dx, dy] = (["x", "y"] as const).map((axis) => {
      const [lo, hi] = span(to, axis);
      return round(to[0][axis] + pull(lo, [0, (hi - lo) / 2, hi - lo], axis === "x" ? xs : ys) - from[0][axis]);
    });
    flushSync(() => place(from.map((b) => [b.id, { x: round(b.x + dx), y: round(b.y + dy) }]), "drag"));
  };
  const resize = (events: OnResize[]) =>
    flushSync(() =>
      place(
        events.map((e) => {
          const box = { x: round(e.drag.left / k), y: round(e.drag.top / k), w: round(e.width / k), h: round(e.height / k) };
          return [idOf(e.target), box];
        }),
        "drag",
      ),
    );
  // Moveable measures a block again after each step of a resize, so a pull would throw it off: the edges settle when it ends.
  // `dx` and `dy` say which handle moved: -1 the left or top edges, 1 the right or bottom ones.
  const settle = ([dx, dy]: number[]) =>
    place(
      free.map((b) => {
        const [x, y] = [dx < 0 ? round(edge(b.x, xs)) : b.x, dy < 0 ? round(edge(b.y, ys)) : b.y];
        const [right, bottom] = [dx > 0 ? edge(b.x + b.w, xs) : b.x + b.w, dy > 0 ? edge(b.y + b.h, ys) : b.y + b.h];
        return [b.id, { x, y, w: round(right - x), h: round(bottom - y) }];
      }),
      "drag",
    );
  // An end handle remembers where the pointer took hold of it, so the end does not jump under the finger.
  function grip(e: PointerEvent) {
    const at = e.currentTarget.getBoundingClientRect();
    grab.current = [e.clientX - at.left - at.width / 2, e.clientY - at.top - at.height / 2];
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  // Where on the page, in mm, the pointer puts the handle it holds.
  function point(e: PointerEvent) {
    const page = sheet.current!.getBoundingClientRect();
    return [(e.clientX - grab.current[0] - page.left) / k, (e.clientY - grab.current[1] - page.top) / k];
  }
  // The guide closest to a point, if one lies within the snap distance.
  const near = (at: number, guides: number[]) => guides.filter((g) => Math.abs(g - at) < 6 / k).sort((a, b) => Math.abs(a - at) - Math.abs(b - at))[0];
  // Moves one end of a line with the pointer; the other end stays. It snaps to the guides a block drag snaps to,
  // and to the other end, which makes the line level or upright.
  function stretch(e: PointerEvent, b: ShapeBlock, end: boolean) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const fx = b.x + (far(b, 1, !end) ? b.w : 0);
    const fy = b.y + (far(b, 0, !end) ? b.h : 0);
    const others = blocks.filter((o) => o !== b);
    const at = point(e);
    const gx = near(at[0], [fx, ...XS, ...others.flatMap((o) => [o.x, o.x + o.w / 2, o.x + o.w])]);
    const gy = near(at[1], [fy, ...YS, ...others.flatMap((o) => [o.y, o.y + o.h / 2, o.y + o.h])]);
    setGuide([gx, gy]);
    const [px, py] = [gx ?? at[0], gy ?? at[1]];
    const from = ((py > fy !== end ? "s" : "n") + (px > fx !== end ? "e" : "w")) as Corner;
    const box = { x: round(Math.min(px, fx)), y: round(Math.min(py, fy)), w: round(Math.abs(px - fx)), h: round(Math.abs(py - fy)) };
    change((bs) => bs.map((o) => (o.id === b.id ? { ...b, ...box, props: { ...b.props, from } } : o)), "drag");
  }
  // Resizes a group from the boxes it began with. The corner opposite the dragged one stays and the group keeps
  // its shape, as Moveable's groups do, so every line keeps its angle. A group can shrink to a tenth, not flip.
  function scale(e: PointerEvent, right: boolean, low: boolean) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const { x, y, w, h } = bounds(start.current);
    const [px, py] = point(e);
    const [fx, fy] = [right ? x : x + w, low ? y : y + h];
    const [sw, sh] = [right ? w : -w, low ? h : -h];
    let s = Math.max(0.1, w && (px - fx) / sw, h && (py - fy) / sh);
    // The dragged corner snaps to the guides a block drag snaps to. The group keeps its shape, so only the nearer
    // of the two guides holds it.
    const [mx, my] = [fx + sw * s, fy + sh * s];
    const gx = w ? near(mx, xs.filter((g) => (g - fx) / sw >= 0.1)) : undefined;
    const gy = h ? near(my, ys.filter((g) => (g - fy) / sh >= 0.1)) : undefined;
    const onX = gx !== undefined && (gy === undefined || Math.abs(gx - mx) <= Math.abs(gy - my));
    if (onX) s = (gx - fx) / sw;
    else if (gy !== undefined) s = (gy - fy) / sh;
    setGuide(onX ? [gx] : [undefined, gy]);
    // Each size comes from its block's two edges, so the edge on the guide lands exactly on it.
    place(
      start.current.map((b) => {
        const [bx, by] = [round(fx + (b.x - fx) * s), round(fy + (b.y - fy) * s)];
        return [b.id, { x: bx, y: by, w: round(fx + (b.x + b.w - fx) * s - bx), h: round(fy + (b.y + b.h - fy) * s - by) }];
      }),
      "drag",
    );
  }

  // `press` is the mouse press that selects, so the same press can drag.
  function pick(el: Element, shift: boolean, press?: globalThis.MouseEvent) {
    if (el.closest(".end")) return;
    const id = el.closest<HTMLElement>(".block")?.dataset.id;
    const more = shift || multi;
    if (!id) {
      if (shift) return;
      setIds([]);
      setMulti(false);
    } else if (ids.includes(id)) {
      if (more) setIds(ids.filter((i) => i !== id));
      // On touch a second tap on a text block edits it; a mouse double-clicks.
      else if (touch.current) edit(id);
      // Level lines in a row leave Moveable's group area no height, so a press on one lands here.
      else if (press && ids.length > 1) moveable.current!.dragStart(press);
    } else {
      setIds(more ? [...ids, id] : [id]);
      if (press) moveable.current!.waitToChangeTarget().then(() => moveable.current!.dragStart(press));
    }
  }
  function edit(id?: string) {
    if (id && free.length === 1 && free[0].id === id && free[0].type === "text") setEditing(id);
  }

  function onTouchStart(e: TouchEvent) {
    clearTimeout(hold.current);
    if (e.touches.length === 2) {
      moveable.current!.stopDrag();
      const page = sheet.current!.getBoundingClientRect();
      const [x, y] = centre(e);
      pinch.current = { spread: spread(e), zoom, x: (x - page.left) / k, y: (y - page.top) / k };
      return;
    }
    // Tap and hold on a block starts selecting several.
    const id = (e.target as Element).closest<HTMLElement>(".block")?.dataset.id;
    if (!id) return;
    hold.current = window.setTimeout(() => {
      held.current = true;
      setMulti(true);
      setIds((now) => (now.includes(id) ? now : [...now, id]));
    }, 500);
  }
  function onTouchMove(e: TouchEvent) {
    clearTimeout(hold.current);
    if (e.touches.length !== 2) return;
    const next = Math.min(4, Math.max(0.25, (pinch.current.zoom * spread(e)) / pinch.current.spread));
    flushSync(() => setZoom(next));
    // Scroll the page point the pinch began on back under the fingers.
    const page = sheet.current!.getBoundingClientRect();
    const [x, y] = centre(e);
    desk.current!.scrollBy(page.left + pinch.current.x * fit * next - x, page.top + pinch.current.y * fit * next - y);
  }

  const locked = sel.length > 0 && !free.length;
  return (
    <main className="editor" onPointerDown={() => (mergeKey.current = "")}>
      <div className="tools">
        <div>
          <button disabled={!hist.past.length} onClick={undo}>Rückgängig</button>
          <button disabled={!hist.future.length} onClick={redo}>Wiederholen</button>
        </div>
        <div>
          <button disabled={!sel.length} onClick={() => setClip(sel)}>Kopieren</button>
          <button disabled={!clip.length} onClick={paste}>Einfügen</button>
          <button disabled={!sel.length} onClick={() => put(sel)}>Duplizieren</button>
          <button disabled={!sel.length} onClick={remove}>Löschen</button>
          <button disabled={!sel.length} className={locked ? "on" : ""} onClick={() => place(sel.map((b) => [b.id, { locked: !locked }]))}>
            {locked ? "Entsperren" : "Sperren"}
          </button>
        </div>
        <div>
          <button className={multi ? "on" : ""} aria-pressed={multi} onClick={() => setMulti(!multi)}>Mehrere auswählen</button>
        </div>
        <div>
          <button aria-label="Verkleinern" onClick={() => setZoom(Math.max(0.25, zoom / 1.25))}>−</button>
          <button onClick={() => setZoom(1)}>Seitenbreite</button>
          <button aria-label="Vergrößern" onClick={() => setZoom(Math.min(4, zoom * 1.25))}>＋</button>
        </div>
      </div>

      <div
        className="desk"
        ref={desk}
        onPointerDown={(e) => (touch.current = e.pointerType === "touch")}
        onMouseDown={(e) => touch.current || moveable.current!.isMoveableElement(e.target as Element) || pick(e.target as Element, e.shiftKey, e.nativeEvent)}
        onClick={(e) => touch.current && !moveable.current!.isMoveableElement(e.target as Element) && pick(e.target as Element, false)}
        onDoubleClick={(e) => edit((e.target as Element).closest<HTMLElement>(".block")?.dataset.id)}
        onContextMenu={(e) => touch.current && e.preventDefault()}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={(e) => {
          clearTimeout(hold.current);
          // Lifting the finger after a hold is not a tap.
          if (held.current) e.preventDefault();
          held.current = false;
        }}
      >
        <div className="sheet" ref={sheet} style={{ width: W * k, height: H * k }}>
          {blocks.map((b) => (
            <div
              key={b.id}
              data-id={b.id}
              className={ids.includes(b.id) ? "block sel" : "block"}
              style={{ left: b.x * k, top: b.y * k, width: b.w * k, height: b.h * k, zIndex: b.z }}
            >
              {b.type === "text" ? (
                <textarea
                  value={b.props.text}
                  placeholder="Text"
                  readOnly={editing !== b.id}
                  style={{ fontSize: b.props.size * PT * k, textAlign: b.props.align }}
                  onChange={(e) => style("text", { text: e.target.value }, "text")}
                  onKeyDown={(e) => e.key === "Escape" && e.currentTarget.blur()}
                  onBlur={() => setEditing("")}
                />
              ) : (
                <Shape block={b} k={k} />
              )}
              {b === line &&
                [false, true].map((end) => (
                  <i
                    key={+end}
                    className={end && line.props.kind === "arrow" ? "end tip" : "end"}
                    style={{ left: far(line, 1, end) ? b.w * k : 0, top: far(line, 0, end) ? b.h * k : 0 }}
                    onPointerDown={grip}
                    onPointerMove={(e) => stretch(e, line, end)}
                    onLostPointerCapture={() => setGuide([])}
                  />
                ))}
            </div>
          ))}
          {guide[0] !== undefined && <i className="guide" style={{ left: guide[0] * k, height: "100%" }} />}
          {guide[1] !== undefined && <i className="guide" style={{ top: guide[1] * k, width: "100%" }} />}
          {group &&
            [0, 1, 2, 3].map((i) => (
              <i
                key={i}
                className="end"
                style={{ left: (group.x + (i % 2) * group.w) * k, top: (group.y + (i >> 1) * group.h) * k }}
                onPointerDown={(e) => {
                  grip(e);
                  start.current = free;
                }}
                onPointerMove={(e) => scale(e, i % 2 > 0, i > 1)}
                onLostPointerCapture={() => setGuide([])}
              />
            ))}
          <Moveable
            ref={moveable}
            target={targets}
            draggable={free.length === sel.length}
            resizable={free.length === sel.length && !sel.some(isLine)}
            renderDirections={CORNERS}
            origin={false}
            checkInput
            snappable
            snapThreshold={6}
            isDisplaySnapDigit={false}
            snapDirections={SIDES}
            elementSnapDirections={SIDES}
            elementGuidelines={[".block:not(.sel)"]}
            verticalGuidelines={XS.map((mm) => mm * k)}
            horizontalGuidelines={YS.map((mm) => mm * k)}
            // Moveable swallows a tap on what is selected, and a group's box covers its blocks.
            onClick={(e) => touch.current && pick(e.inputTarget, false)}
            onClickGroup={(e) => pick(e.inputTarget, e.inputEvent.shiftKey)}
            onDragStart={(e) => (e.inputEvent.target as Element).closest(".end") && e.stopDrag()}
            onDrag={(e) => drag([e])}
            onDragGroup={(e) => drag(e.events)}
            onResize={(e) => resize([e])}
            onResizeGroup={(e) => resize(e.events)}
            onResizeEnd={(e) => e.lastEvent && settle(e.lastEvent.direction)}
            onResizeGroupEnd={(e) => e.lastEvent && settle(e.lastEvent.direction)}
          />
        </div>
      </div>
      {/* The drag box is for a mouse on empty desk; a finger there scrolls. */}
      <Selecto
        dragContainer=".desk"
        selectableTargets={[".block"]}
        hitRate={0}
        selectByClick={false}
        onDragStart={(e) => {
          const el = e.inputEvent.target as Element;
          if (e.inputEvent.type === "touchstart" || el.closest(".block, .end") || moveable.current!.isMoveableElement(el)) e.stop();
        }}
        onSelectEnd={(e) => setIds((now) => [...new Set([...now, ...e.selected.map(idOf)])])}
      />

      <aside className="panel">
        <h2>Einfügen</h2>
        <div className="row">
          <button onClick={() => add(80, 12, { type: "text", props: { text: "", size: 14, align: "left" } })}>Text</button>
          {SHAPES.map(([kind, label]) => (
            <button
              key={kind}
              onClick={() =>
                add(kind === "circle" ? 40 : 60, kind === "line" || kind === "arrow" ? 0 : 40, {
                  type: "shape",
                  props: { kind, fill: "none", stroke: "#222222", strokeWidth: 0.5 },
                })
              }
            >
              {label}
            </button>
          ))}
        </div>

        <h2>Ausrichten</h2>
        <div className="row">
          <button disabled={!free.length} onClick={() => align("x", 0)}>Links</button>
          <button disabled={!free.length} onClick={() => align("x", 0.5)}>Mitte</button>
          <button disabled={!free.length} onClick={() => align("x", 1)}>Rechts</button>
          <button disabled={!free.length} onClick={() => align("y", 0)}>Oben</button>
          <button disabled={!free.length} onClick={() => align("y", 0.5)}>Mitte</button>
          <button disabled={!free.length} onClick={() => align("y", 1)}>Unten</button>
        </div>
        <h2>Verteilen</h2>
        <div className="row">
          <button disabled={free.length < 3} onClick={() => distribute("x")}>Waagerecht</button>
          <button disabled={free.length < 3} onClick={() => distribute("y")}>Senkrecht</button>
        </div>
        <h2>Ebene</h2>
        <div className="row">
          <button disabled={!sel.length} onClick={() => place(sel.map((b) => [b.id, { z: top + 1 }]))}>Nach vorn</button>
          <button disabled={!sel.length} onClick={() => place(sel.map((b) => [b.id, { z: Math.min(0, ...blocks.map((o) => o.z)) - 1 }]))}>
            Nach hinten
          </button>
        </div>

        {texts.length > 0 && (
          <>
            <h2>Schrift</h2>
            <div className="row">
              <button aria-label="Schrift kleiner" onClick={() => style("text", { size: Math.max(8, texts[0].props.size - 2) })}>−</button>
              <output>{texts[0].props.size} pt</output>
              <button aria-label="Schrift größer" onClick={() => style("text", { size: texts[0].props.size + 2 })}>＋</button>
              {ALIGNS.map(([value, label]) => (
                <button key={value} className={texts[0].props.align === value ? "on" : ""} onClick={() => style("text", { align: value })}>
                  {label}
                </button>
              ))}
            </div>
          </>
        )}
        {shapes.length > 0 && (
          <>
            <h2>Form</h2>
            <label>
              Füllung
              <input
                type="color"
                value={shapes[0].props.fill === "none" ? "#ffffff" : shapes[0].props.fill}
                onChange={(e) => style("shape", { fill: e.target.value }, "fill")}
              />
            </label>
            <button disabled={shapes[0].props.fill === "none"} onClick={() => style("shape", { fill: "none" })}>Keine Füllung</button>
            <label>
              Rand
              <input type="color" value={shapes[0].props.stroke} onChange={(e) => style("shape", { stroke: e.target.value }, "stroke")} />
            </label>
            <label>
              Randstärke
              <input
                type="range"
                min={0.25}
                max={3}
                step={0.25}
                value={shapes[0].props.strokeWidth}
                onChange={(e) => style("shape", { strokeWidth: +e.target.value }, "strokeWidth")}
              />
            </label>
          </>
        )}
      </aside>
    </main>
  );
}

function Shape({ block, k }: { block: ShapeBlock; k: number }) {
  const { kind, fill, stroke, strokeWidth } = block.props;
  if (isLine(block)) {
    // Drawn from the start corner along its own axis; a wide unseen stroke is what a finger grabs.
    const [x, y] = [far(block, 1, false) ? block.w : 0, far(block, 0, false) ? block.h : 0];
    const angle = (Math.atan2(block.h - 2 * y, block.w - 2 * x) * 180) / Math.PI;
    const length = Math.hypot(block.w, block.h);
    const head = kind === "arrow" ? 2 + strokeWidth * 3 : 0;
    return (
      <svg>
        <g transform={`scale(${k}) translate(${x} ${y}) rotate(${angle})`} stroke={stroke} strokeWidth={strokeWidth} fill={stroke}>
          <line x2={length} stroke="transparent" strokeWidth={10} />
          <line x2={length - head} />
          {head > 0 && <polygon stroke="none" points={`${length},0 ${length - head},${-head / 2} ${length - head},${head / 2}`} />}
        </g>
      </svg>
    );
  }
  return (
    <div
      style={{
        background: fill,
        border: `${strokeWidth * k}px solid ${stroke}`,
        borderRadius: kind === "circle" ? "50%" : kind === "rounded" ? 4 * k : 0,
      }}
    />
  );
}
