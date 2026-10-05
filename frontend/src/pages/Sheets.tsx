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

export default function Sheets() {
  const [hist, setHist] = useState<{ past: Block[][]; blocks: Block[]; future: Block[][] }>({ past: [], blocks: [], future: [] });
  const [ids, setIds] = useState<string[]>([]);
  const [targets, setTargets] = useState<HTMLElement[]>([]);
  const [clip, setClip] = useState<Block[]>([]);
  const [editing, setEditing] = useState("");
  const [multi, setMulti] = useState(false);
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
    if (editing) sheet.current!.querySelector<HTMLElement>(`[data-id="${editing}"] textarea`)?.focus();
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

  function add(w: number, h: number, rest: Pick<TextBlock, "type" | "props"> | Pick<ShapeBlock, "type" | "props">) {
    const id = crypto.randomUUID();
    let x = (W - w) / 2;
    let y = Math.min(round(desk.current!.scrollTop / k) + MARGIN, H - h);
    // Step clear of a block already at that spot, as far as the page allows.
    while (blocks.some((b) => b.x === x && b.y === y) && x + w + 5 <= W && y + h + 5 <= H) {
      x += 5;
      y += 5;
    }
    const block = { id, x, y, w, h, z: top + 1, locked: false, ...rest };
    change((bs) => [...bs, block]);
    setIds([id]);
    if (rest.type === "text") setEditing(id);
  }
  function put(from: Block[]) {
    const copies = [...from]
      .sort((a, b) => a.z - b.z)
      .map((b, i) => ({ ...b, id: crypto.randomUUID(), x: b.x + 5, y: b.y + 5, z: top + 1 + i }));
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
    const end = Math.max(...row.map((b) => b[axis] + b[size]));
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

  // Moveable snaps to within a pixel of a guide. These put an edge, or an edge or centre, that close exactly on it.
  const edge = (at: number, guides: number[]) => guides.find((g) => Math.abs(g - at) < 1 / k) ?? at;
  const settle = (at: number, size: number, guides: number[]) => {
    const part = [0, size / 2, size].find((part) => edge(at + part, guides) !== at + part);
    return round(part === undefined ? at : edge(at + part, guides) - part);
  };

  // Moveable reports px, the document keeps mm. It reads the new size back at once, so render before returning.
  const drag = (events: OnDrag[]) =>
    flushSync(() =>
      place(
        events.map((e) => {
          const b = blocks.find((b) => b.id === idOf(e.target))!;
          return [b.id, { x: settle(e.left / k, b.w, XS), y: settle(e.top / k, b.h, YS) }];
        }),
        "drag",
      ),
    );
  const resize = (events: OnResize[]) =>
    flushSync(() =>
      place(
        events.map((e) => {
          const [x, y] = [edge(e.drag.left / k, XS), edge(e.drag.top / k, YS)];
          const box = { x: round(x), y: round(y), w: round(edge(x + e.width / k, XS) - x), h: round(edge(y + e.height / k, YS) - y) };
          return [idOf(e.target), box];
        }),
        "drag",
      ),
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
  // Moves one end of a line with the pointer; the other end stays. Near level or upright it snaps straight.
  function stretch(e: PointerEvent, b: ShapeBlock, end: boolean) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const fx = b.x + (far(b, 1, !end) ? b.w : 0);
    const fy = b.y + (far(b, 0, !end) ? b.h : 0);
    let [px, py] = point(e);
    if (Math.abs(px - fx) < 6 / k) px = fx;
    if (Math.abs(py - fy) < 6 / k) py = fy;
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
    const s = Math.max(0.1, w && (px - fx) / (right ? w : -w), h && (py - fy) / (low ? h : -h));
    place(
      start.current.map((b) => [b.id, { x: round(fx + (b.x - fx) * s), y: round(fy + (b.y - fy) * s), w: round(b.w * s), h: round(b.h * s) }]),
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
    if (ids.length > 1 && ids.includes(id)) moveable.current!.dragStart(e.nativeEvent);
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
                    className="end"
                    style={{ left: far(line, 1, end) ? b.w * k : 0, top: far(line, 0, end) ? b.h * k : 0 }}
                    onPointerDown={grip}
                    onPointerMove={(e) => stretch(e, line, end)}
                  />
                ))}
            </div>
          ))}
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
