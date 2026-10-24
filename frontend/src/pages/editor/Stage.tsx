// The desk the pages lie on, and the hand that moves it.
import type { CSSProperties } from "react";
import Selecto from "react-selecto";
import { boxed, type Page } from "../../sheet";
import { anchorOf } from "../../cells";
import { holdName } from "./Tool";
import { idOf, grouped } from "./palette";
import { useTools } from "./useTools";
import SheetFrame from "./SheetFrame";

export default function Stage({ s: session }: { s: ReturnType<typeof useTools> }) {
  const at = session.at;
  const away = session.away;
  const blocks = session.blocks;
  const brush = session.brush;
  const brushed = session.brushed;
  const brushing = session.brushing;
  const cellDrag = session.cellDrag;
  const cover = session.cover;
  const desk = session.desk;
  const downOn = session.downOn;
  const dragDesk = session.dragDesk;
  const edit = session.edit;
  const editing = session.editing;
  const follow = session.follow;
  const free = session.free;
  const hand = session.hand;
  const held = session.held;
  const hold = session.hold;
  const ids = session.ids;
  const k = session.k;
  const leaf = session.leaf;
  const menuAt = session.menuAt;
  const middlePan = session.middlePan;
  const moveable = session.moveable;
  const onTouchMove = session.onTouchMove;
  const onTouchStart = session.onTouchStart;
  const openStone = session.openStone;
  const over = session.over;
  const page = session.page;
  const pages = session.pages;
  const pan = session.pan;
  const panning = session.panning;
  const pick = session.pick;
  const scrollHeld = session.scrollHeld;
  const sel = session.sel;
  const setFinger = session.setFinger;
  const setIds = session.setIds;
  const setPanning = session.setPanning;
  const setReach = session.setReach;
  const setSlot = session.setSlot;
  const sheet = session.sheet;
  const slot = session.slot;
  const spaced = session.spaced;
  const spot = session.spot;
  const stage = session.stage;
  const steer = session.steer;
  const still = session.still;
  const style = session.style;
  const table = session.table;
  const tools = session.tools;
  const touch = session.touch;
  const widest = session.widest;
  const written = session.written;
  const zoomer = session.zoomer;
  return (
    <>
      {/* The release may land on the hand, beside the desk: the click is the stage's, not the desk's. */}
      <div
        className="stage"
        ref={stage}
        onMouseUp={(e) => e.button === 1 && e.preventDefault()}
        onAuxClick={(e) => e.button === 1 && e.preventDefault()}
        // Capture: Moveable's frame over a picked block would hear the press first otherwise. The hand lies beside the desk, so the stage takes its press too.
        onPointerDownCapture={(e) => {
          if (e.button !== 1 || e.pointerType !== "mouse") return;
          e.stopPropagation();
          middlePan(e.clientX, e.clientY);
        }}
        // The press is not cancelled as a pointer: Chrome then sends no mouseup, and a middle paste would follow it.
        onMouseDownCapture={(e) => {
          if (e.button !== 1) return;
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        <div
          className="desk"
          ref={desk}
          // How wide the widest page lies on the desk: the room an open Format drawer adds starts past it.
          style={{ "--reach": `${widest * k}px` } as CSSProperties}
          onScroll={follow}
          onWheel={(e) => !(e.ctrlKey || e.metaKey) && steer()}
          onPointerDown={(e) => {
            if (e.target === e.currentTarget) {
              scrollHeld.current = true;
              const let_go = () => {
                scrollHeld.current = false;
                window.removeEventListener("pointerup", let_go);
                window.removeEventListener("pointercancel", let_go);
              };
              window.addEventListener("pointerup", let_go);
              window.addEventListener("pointercancel", let_go);
            }
            touch.current = e.pointerType === "touch";
            setFinger(touch.current);
            cover.current =moveable.current!.isMoveableElement(e.target as Element);
            // The hold before is over with the next press, not with its own lift: Moveable hears of that lift later.
            held.current = false;
            // A press of the mouse on a cell of the table being edited picks cells. Moveable takes the focus from the
            // field before the mouse's own event: the field stays open through that.
            cellDrag.current = !touch.current && !!table && editing === table.id && !!(e.target as Element).closest(`[data-id="${table.id}"] [data-cell]`);
            // A press with the brush on a picked text is the brush's: Moveable, which hears of it before the mouse's
            // own event, would drag the block (#756). The click after it picks nothing more.
            // Under Moveable's frame the block is the one the point finds, as onClickCapture finds it.
            // A handle of the frame resizes or turns: only its area lies over the text.
            const hit = cover.current && (e.target as Element).matches(".moveable-area") ? document.elementsFromPoint(e.clientX, e.clientY).find((el) => el.closest(".block")) : undefined;
            brushed.current = hit ?? (e.target as Element);
            const id = brushed.current.closest<HTMLElement>(".block")?.dataset.id;
            const text = blocks.find((b) => b.id === id);
            brushing.current = !touch.current && e.button === 0 && !!brush && !!text && !!boxed(text) && ids.includes(text.id);
            if (brushing.current) {
              const off = () => setTimeout(() => (brushing.current = false));
              addEventListener("pointerup", off, { once: true });
              addEventListener("pointercancel", off, { once: true });
            }
          }}
          onMouseDown={(e) => {
            // Moveable keeps the press from moving the focus, so an input, or a button reached by the keys, would keep
            // Enter and Tab.
            if (!document.activeElement?.closest(".block")) (document.activeElement as HTMLElement | null)?.blur();
            // In the table being edited a press on a cell picks cells: Shift picks up to that cell, a drag picks across.
            const hit = table && editing === table.id && (e.target as Element).closest(`[data-id="${table.id}"]`) ? (e.target as Element).closest<HTMLElement>("[data-cell]") : null;
            if (hit && e.button === 0) {
              const at = anchorOf(table!.props, +hit.dataset.cell!);
              // Shift on another cell keeps the letters of the cells unpicked; in the open field it picks text, and a
              // plain press there sets the caret.
              if (e.shiftKey && at !== slot) e.preventDefault();
              else if (!e.shiftKey) setSlot(at);
              setReach(e.shiftKey && at !== slot ? at : undefined);
              spot.current = undefined;
              return;
            }
            // With the brush a press in the open text picks its words, and a drag paints them.
            // The brush's press on a picked text (see onPointerDown) paints, and its drag picks words.
            if (brushing.current) return void pick(brushed.current!, e.shiftKey, e.nativeEvent);
            // The right button drags nothing: its menu picks the block.
            if (touch.current || e.button === 2 || moveable.current!.isMoveableElement(e.target as Element)) return;
            // A press on a picked block may drag it. Only a click that stays on its spot picks a block out of its group.
            spot.current = !e.shiftKey && !e.ctrlKey && !e.metaKey && ids.includes((e.target as Element).closest<HTMLElement>(".block")?.dataset.id ?? "") ? [e.clientX, e.clientY] : undefined;
            pick(e.target as Element, e.shiftKey, e.nativeEvent);
          }}
          // Moveable keeps a click on a selection it cannot drag to itself, so the block under its area is looked up on the way down.
          onClickCapture={(e) => {
            if (free.length === sel.length || !moveable.current!.isMoveableElement(e.target as Element)) return;
            const under = document.elementsFromPoint(e.clientX, e.clientY).find((el) => el.closest(".block"));
            if (under) pick(under, e.shiftKey);
          }}
          onClick={(e) => {
            if (moveable.current!.isMoveableElement(e.target as Element)) return;
            // Moveable took the focus from the field with a press on a cell: it goes back to the cell that is open now.
            if (table && editing === table.id && (e.target as Element).closest(`[data-id="${table.id}"]`)) return void written()?.focus();
            const still = spot.current && Math.hypot(e.clientX - spot.current[0], e.clientY - spot.current[1]) < 3;
            // The second click of a double click does not open the field: the double click does, with no word picked.
            if (touch.current || (still && e.detail < 2)) pick(e.target as Element, false, undefined, [e.clientX, e.clientY]);
          }}
          // A drag over the cells of the table being edited picks the cells between its start and the pointer.
          onMouseMove={(e) => {
            if (!cellDrag.current || e.buttons !== 1 || !table) return;
            const over = document.elementsFromPoint(e.clientX, e.clientY).map((el) => el.closest<HTMLElement>("[data-cell]")).find((el) => el && el.closest(`[data-id="${table.id}"]`));
            if (!over) return;
            const at = anchorOf(table.props, +over.dataset.cell!);
            setReach(at === slot ? undefined : at);
          }}
          onDoubleClick={(e) => brush || openStone(e.target as Element) || edit((e.target as Element).closest<HTMLElement>(".block")?.dataset.id, e.target as Element)}
          // A held finger gets no menu, and a mouse the editor's own, unless a field keeps the browser's.
          // In a field the browser's own menu stays, a finger's and a mouse's alike.
          onContextMenu={(e) => {
            const el = e.target as Element;
            if (touch.current ? !el.closest(".ProseMirror, textarea, input, select") : menuAt(el, e.clientX, e.clientY)) e.preventDefault();
          }}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={(e) => {
            clearTimeout(hold.current);
            // Lifting the finger after a hold is not a tap.
            if (held.current) e.preventDefault();
            // A finger held still opens the menu on the lift, where it lies.
            if (held.current && !away.current && !e.touches.length) menuAt(downOn.current!, e.changedTouches[0].clientX, e.changedTouches[0].clientY);
          }}
          // The browser took the touch for its own, a scroll: no finger holds, and the next lift is a tap again.
          onTouchCancel={() => {
            clearTimeout(hold.current);
            held.current = false;
          }}
        >
          {pages.map((p: Page, n: number) => (
            <SheetFrame key={n} s={session} p={p} n={n} />
          ))}
        </div>
        {/* The hand lies over the desk and takes the press, so no block under it is picked or moved. */}
        {(pan || panning) && (
          <div
            className="hand"
            onPointerDown={(e) => {
              // The left button only: the right one opens the menu.
              if (e.button) return;
              e.currentTarget.setPointerCapture(e.pointerId);
              hand.current = [e.clientX, e.clientY, desk.current!.scrollLeft, desk.current!.scrollTop];
              // A drag: the Space was the hand's, not a space to type.
              spaced.current = null;
              setPanning(true);
              // A button that has the focus would take Space's keyup as its click.
              if (document.activeElement instanceof HTMLButtonElement) document.activeElement.blur();
            }}
            onPointerMove={(e) => {
              if (!panning) return;
              // The button came up where the hand could not see it.
              if (!e.buttons) return setPanning(false);
              steer();
              dragDesk(e);
            }}
            onPointerUp={() => setPanning(false)}
            onPointerCancel={() => setPanning(false)}
          />
        )}
        {/* What can go on the page floats over the desk's lower edge. */}
        {leaf ? (
          <>
            <div className="dock">{zoomer}</div>
            {pages.length > 1 && (
              <div className="dock at">
                Seite {page + 1} von {pages.length}
              </div>
            )}
          </>
        ) : (
          <div className="dock" role="toolbar" aria-label="Einfügen" onPointerOver={holdName}>
            {tools}
          </div>
        )}
      </div>
      {/* The drag box is for a mouse on empty desk; a finger there scrolls. */}
      <Selecto
        dragContainer=".desk"
        selectableTargets={[".block"]}
        hitRate={0}
        selectByClick={false}
        onDragStart={(e) => {
          const el = e.inputEvent.target as Element;
          if (e.inputEvent.type === "touchstart" || el.closest(".block, .end, .adjust, .rule, .bar, .crop") || moveable.current!.isMoveableElement(el)) e.stop();
        }}
        // The box selects on the page in use, which the press that began it has set.
        onSelectEnd={(e) => setIds((now) => grouped([...now, ...e.selected.filter((el) => sheet.current!.contains(el)).map(idOf)], blocks))}
      />

    </>
  );
}
