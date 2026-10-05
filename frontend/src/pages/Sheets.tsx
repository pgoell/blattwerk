import { useEffect, useLayoutEffect, useRef, useState, type TouchEvent } from "react";
import { flushSync } from "react-dom";
import Moveable, { type OnDrag, type OnResize } from "react-moveable";
import Selecto from "react-selecto";

// One page's blocks, as the sheet document stores them: mm from the page's top-left corner.
type Box = { id: string; x: number; y: number; w: number; h: number; z: number; locked: boolean };
type Kind = "rect" | "rounded" | "circle" | "line" | "arrow";
type Align = "left" | "center" | "right";
type TextBlock = Box & { type: "text"; props: { text: string; size: number; align: Align } };
type ShapeBlock = Box & { type: "shape"; props: { kind: Kind; fill: string; stroke: string; strokeWidth: number } };
type Block = TextBlock | ShapeBlock;
type Axis = "x" | "y";

const W = 210;
const H = 297;
const MARGIN = 15;
const PT = 25.4 / 72; // mm per point
const SIDES = { top: true, left: true, bottom: true, right: true, center: true, middle: true };
const CORNERS = ["nw", "ne", "sw", "se"];
const SHAPES: [Kind, string][] = [["rect", "Rechteck"], ["rounded", "Abgerundet"], ["circle", "Kreis"], ["line", "Linie"], ["arrow", "Pfeil"]];
const ALIGNS: [Align, string][] = [["left", "Links"], ["center", "Mitte"], ["right", "Rechts"]];

const round = (n: number) => Math.round(n * 100) / 100;
const idOf = (el: Element) => (el as HTMLElement).dataset.id!;
const spread = (e: TouchEvent) => Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);

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
  const pinch = useRef({ spread: 1, zoom: 1 });

  const { blocks } = hist;
  const k = fit * zoom;
  const sel = blocks.filter((b) => ids.includes(b.id));
  const free = sel.filter((b) => !b.locked);
  const texts = sel.filter((b) => b.type === "text");
  const shapes = sel.filter((b) => b.type === "shape");
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
    const block = { id, x: (W - w) / 2, y: round(desk.current!.scrollTop / k) + MARGIN, w, h, z: top + 1, locked: false, ...rest };
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

  // Moveable reports px, the document keeps mm. It reads the new size back at once, so render before returning.
  const drag = (events: OnDrag[]) =>
    flushSync(() => place(events.map((e) => [idOf(e.target), { x: round(e.left / k), y: round(e.top / k) }]), "drag"));
  const resize = (events: OnResize[]) =>
    flushSync(() =>
      place(
        events.map((e) => [idOf(e.target), { x: round(e.drag.left / k), y: round(e.drag.top / k), w: round(e.width / k), h: round(e.height / k) }]),
        "drag",
      ),
    );

  // `press` is the mouse press that selects, so the same press can drag.
  function pick(el: Element, shift: boolean, press?: globalThis.MouseEvent) {
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
      pinch.current = { spread: spread(e), zoom };
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
    if (e.touches.length === 2) setZoom(Math.min(4, Math.max(0.25, (pinch.current.zoom * spread(e)) / pinch.current.spread)));
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
            </div>
          ))}
          <Moveable
            ref={moveable}
            target={targets}
            draggable={free.length === sel.length}
            resizable={free.length === sel.length}
            renderDirections={CORNERS}
            origin={false}
            checkInput
            snappable
            snapThreshold={6}
            isDisplaySnapDigit={false}
            snapDirections={SIDES}
            elementSnapDirections={SIDES}
            elementGuidelines={[".block:not(.sel)"]}
            verticalGuidelines={[MARGIN, W / 2, W - MARGIN].map((mm) => mm * k)}
            horizontalGuidelines={[MARGIN, H / 2, H - MARGIN].map((mm) => mm * k)}
            // Moveable swallows a tap on what is selected, and a group's box covers its blocks.
            onClick={(e) => touch.current && pick(e.inputTarget, false)}
            onClickGroup={(e) => pick(e.inputTarget, e.inputEvent.shiftKey)}
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
          if (e.inputEvent.type === "touchstart" || el.closest(".block") || moveable.current!.isMoveableElement(el)) e.stop();
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
                add(kind === "circle" ? 40 : 60, kind === "line" || kind === "arrow" ? 10 : 40, {
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
  if (kind === "line" || kind === "arrow") {
    // Drawn along the longer side, through the middle: left to right, or top to bottom.
    const flat = block.w >= block.h;
    const [length, mid] = flat ? [block.w, block.h / 2] : [block.h, block.w / 2];
    const head = kind === "arrow" ? 2 + strokeWidth * 3 : 0;
    return (
      <svg viewBox={`0 0 ${block.w} ${block.h}`}>
        <g transform={flat ? undefined : "matrix(0 1 1 0 0 0)"} stroke={stroke} strokeWidth={strokeWidth} fill={stroke}>
          <line x1={0} y1={mid} x2={length - head} y2={mid} />
          {head > 0 && <polygon stroke="none" points={`${length},${mid} ${length - head},${mid - head / 2} ${length - head},${mid + head / 2}`} />}
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
