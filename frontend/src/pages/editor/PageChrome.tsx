// Crop and resize handles, and the frame around the picked blocks, on the page in use.
import Moveable from "react-moveable";
import { far, isLine, reachOf, sum, tailReach, type Page, type TextProps } from "../../sheet";
import { paint as paintGround } from "../../ground";
import { adjustable, drawn } from "../Format";
import { Crop } from "./Crop";
import { turnedAt, SIDES, CENTRE, FRAME } from "./palette";
import { useTools } from "./useTools";

export default function PageChrome({ s: session, p, n }: { s: ReturnType<typeof useTools>; p: Page; n: number }) {
  const H = session.H;
  const W = session.W;
  const adjust = session.adjust;
  const adjustAt = session.adjustAt;
  const adjusting = session.adjusting;
  const at = session.at;
  const begin = session.begin;
  const beginGround = session.beginGround;
  const brushing = session.brushing;
  const cellDrag = session.cellDrag;
  const cover = session.cover;
  const cropping = session.cropping;
  const cut = session.cut;
  const draft = session.draft;
  const drag = session.drag;
  const dragGround = session.dragGround;
  const edge = session.edge;
  const endGround = session.endGround;
  const frame = session.frame;
  const free = session.free;
  const grip = session.grip;
  const gripDown = session.gripDown;
  const gripMove = session.gripMove;
  const gripUp = session.gripUp;
  const grips = session.grips;
  const group = session.group;
  const guide = session.guide;
  const handles = session.handles;
  const held = session.held;
  const k = session.k;
  const keep = session.keep;
  const leave = session.leave;
  const left = session.left;
  const line = session.line;
  const loose = session.loose;
  const mod = session.mod;
  const moveable = session.moveable;
  const onDrag = session.onDrag;
  const onTouchStart = session.onTouchStart;
  const oneGroup = session.oneGroup;
  const page = session.page;
  const pageXs = session.pageXs;
  const pageYs = session.pageYs;
  const pick = session.pick;
  const resize = session.resize;
  const resizeEnded = session.resizeEnded;
  const rest = session.rest;
  const rotate = session.rotate;
  const rotated = session.rotated;
  const scale = session.scale;
  const sel = session.sel;
  const setGuide = session.setGuide;
  const shaping = session.shaping;
  const shown = session.shown;
  const sizes = session.sizes;
  const spot = session.spot;
  const start = session.start;
  const stretch = session.stretch;
  const style = session.style;
  const table = session.table;
  const targets = session.targets;
  const thing = session.thing;
  const tight = session.tight;
  const top = session.top;
  const touch = session.touch;
  const trim = session.trim;
  const trimming = session.trimming;
  const turnedLine = session.turnedLine;
  const whole = session.whole;
  const widen = session.widen;
  const wrote = session.wrote;
  return (
    <>
              {n === page && (
                <>
                  {guide[0] !== undefined && <i className="guide" style={{ left: guide[0] * k, height: "100%" }} />}
                  {guide[1] !== undefined && <i className="guide" style={{ top: guide[1] * k, width: "100%" }} />}
                  {table?.props.cols.slice(1).flatMap((_, i) =>
                    // A line that runs through a merged cell does not show there: its handle keeps to the rows where it does.
                    shown(table, i).map(([top, height]) => (
                      <i
                        key={`${i} ${top}`}
                        className="bar"
                        style={{ left: (table.x + (sum(table.props.cols.slice(0, i + 1)) / sum(table.props.cols)) * table.w) * k, top: top * k, height: height * k }}
                        onPointerDown={grip}
                        onPointerMove={(e) => widen(e, table, i)}
                      />
                    )),
                  )}
                  {/* Over the lines' handles, which run along the cells' edges where these stand. The sheet's touch, a
                      hold that opens a menu, is not theirs: it took the click of the next tap. */}
                  {table && grips.map((g) => (
                    <i key={g.corner} className={`cell-handle cell-handle-${g.corner}`} style={{ left: g.x, top: g.y }} onPointerDown={(e) => gripDown(e, g.corner)} onTouchStart={(e) => e.stopPropagation()} onPointerMove={gripMove} onPointerUp={gripUp} onPointerCancel={gripUp} />
                  ))}
                  {cropping && <Crop block={cropping} box={whole(cropping)} cut={draft!.cut} k={k} grip={grip} trim={trim} />}
                  {p.ground && shaping && !trimming && (
                    <i
                      className="ground-handle scale"
                      aria-label="Hintergrund skalieren"
                      style={{ left: (paintGround(sizes[n][0], sizes[n][1], p.ground).x + paintGround(sizes[n][0], sizes[n][1], p.ground).width) * k, top: (paintGround(sizes[n][0], sizes[n][1], p.ground).y + paintGround(sizes[n][0], sizes[n][1], p.ground).height) * k }}
                      onPointerDown={(e) => beginGround(e, "scale")}
                      onPointerMove={dragGround}
                      onPointerUp={endGround}
                      onPointerCancel={endGround}
                    />
                  )}
                  {p.ground && trimming &&
                    [0, 1, 2, 3].map((edge) => {
                      const box = paintGround(sizes[n][0], sizes[n][1], p.ground!);
                      const [W, H] = sizes[n];
                      const at = [
                        [Math.min(W, Math.max(0, box.x)), Math.min(H, Math.max(0, box.y + box.height / 2))],
                        [Math.min(W, Math.max(0, box.x + box.width / 2)), Math.min(H, Math.max(0, box.y))],
                        [Math.min(W, Math.max(0, box.x + box.width)), Math.min(H, Math.max(0, box.y + box.height / 2))],
                        [Math.min(W, Math.max(0, box.x + box.width / 2)), Math.min(H, Math.max(0, box.y + box.height))],
                      ][edge];
                      return (
                        <i
                          key={edge}
                          className="ground-handle"
                          data-edge={edge}
                          aria-label={["Links kürzen", "Oben kürzen", "Rechts kürzen", "Unten kürzen"][edge]}
                          style={{ left: at[0] * k, top: at[1] * k }}
                          onPointerDown={(e) => beginGround(e, "trim", edge)}
                          onPointerMove={dragGround}
                          onPointerUp={endGround}
                          onPointerCancel={endGround}
                        />
                      );
                    })}
                  {line &&
                    [false, true].map((end) => (
                      <i
                        key={+end}
                        className={line.props.kind === "double" || (end && line.props.kind === "arrow") ? "end tip" : "end"}
                        style={{ left: (line.x + (far(line, 1, end) ? line.w : 0)) * k, top: (line.y + (far(line, 0, end) ? line.h : 0)) * k }}
                        onPointerDown={grip}
                        onPointerMove={(e) => stretch(e, line, end)}
                        onLostPointerCapture={() => setGuide([])}
                      />
                    ))}
                  {/* A picked bubble whose tail reaches out of its box: a frame round both, the handles stay on the box. */}
                  {sel.filter((b) => drawn(b) && tailReach({ ...b, props: b.props as TextProps }).some((mm) => mm > 0)).map((b) => {
                    const r = reachOf(b);
                    return <i key={`reach-${b.id}`} className="reach" data-id={b.id} style={{ left: (r.x - r.hw) * k, top: (r.y - r.hh) * k, width: 2 * r.hw * k, height: 2 * r.hh * k, transform: b.angle ? `rotate(${b.angle}deg)` : undefined }} />;
                  })}
                  {/* One handle per picked bubble, star or triangle, which moves the point its shape takes. */}
                  {free.length === sel.length && !cropping && sel.filter((b) => adjustable(b) && !b.locked).map((b) => (
                    <i
                      key={b.id}
                      className="adjust"
                      data-id={b.id}
                      style={{ left: adjustAt(b)[0] * k, top: adjustAt(b)[1] * k }}
                      onPointerDown={(e) => {
                        adjusting.current = e.pointerId;
                        // A drag of the handle does not grow the shape: the grow would move the handle from the pointer.
                        wrote.current = "";
                        // WebKit captures no pointer it no longer knows, such as a touch a script made: its moves
                        // still come here, by `adjusting`.
                        try {
                          grip(e);
                        } catch {
                          /* not captured */
                        }
                      }}
                      onPointerUp={() => (adjusting.current = undefined)}
                      onPointerCancel={() => (adjusting.current = undefined)}
                      onLostPointerCapture={() => (adjusting.current = undefined)}
                      onTouchStart={(e) => e.stopPropagation()}
                      onPointerMove={(e) => adjust(e, b)}
                    />
                  ))}
                  {/* Moveable's frame round a turned group with a line takes in the line's level box, so the group's own
                      frame is drawn here, where its handles stand. */}
                  {turnedLine &&
                    ((nw, off) => (
                      <div
                        className="turned-frame"
                        style={{ left: nw[0] * k + off[0], top: nw[1] * k + off[1], width: group!.w * k + FRAME.left + FRAME.right, height: group!.h * k + FRAME.top + FRAME.bottom, transform: `rotate(${frame!.turn}deg)` }}
                      />
                    ))(turnedAt([group!.x, group!.y], frame!.turn, frame!.about), turnedAt([-FRAME.left, -FRAME.top], frame!.turn, [0, 0]))}
                  {group &&
                    [0, 1, 2, 3].map((i) => {
                      // On the frame's corners, which stand outside the group's. A turned frame turns them about its middle.
                      const at = turnedAt([group.x + (i % 2) * group.w, group.y + (i >> 1) * group.h], frame!.turn, frame!.about);
                      const off = turnedAt([i % 2 ? FRAME.right : -FRAME.left, i >> 1 ? FRAME.bottom : -FRAME.top], frame!.turn, [0, 0]);
                      return (
                      <i
                        key={i}
                        className="end"
                        style={{ left: at[0] * k + off[0], top: at[1] * k + off[1] }}
                        onPointerDown={(e) => {
                          grip(e);
                          start.current = free;
                        }}
                        onPointerMove={(e) => scale(e, i % 2 > 0, i > 1)}
                        // The render this asks for also measures a text the group made too small.
                        onLostPointerCapture={() => {
                          tight.current = true;
                          setGuide([]);
                        }}
                      />
                      );
                    })}
                  <Moveable
                    ref={moveable}
                    // In crop mode the frame's handles stand in for Moveable's.
                    target={cropping ? [] : targets}
                    draggable={free.length === sel.length}
                    resizable={free.length === sel.length && !sel.some(isLine)}
                    renderDirections={turnedLine ? [] : handles}
                    hideDefaultLines={turnedLine}
                    // A lone line keeps its own handles at its ends, and has no frame.
                    padding={sel.length === 1 && isLine(sel[0]) ? undefined : FRAME}
                    // Each loose block has its own outline from Moveable, which the padding does not reach. Blocks of one
                    // group keep only the frame about them all, so the outlines do not cut their letters.
                    hideChildMoveableDefaultLines={oneGroup}
                    // Loose blocks turned alike would get a frame turned about their middle. Their frame stays level.
                    // A turned group with a line has blocks of two angles: its frame takes the group's own.
                    useDefaultGroupRotate={!oneGroup || !!turnedLine}
                    defaultGroupRotate={turnedLine ? frame!.turn : 0}
                    origin={false}
                    checkInput
                    // Two fingers zoom the desk and are none of Moveable's. Waiting for a second one outside the block,
                    // it would take the next tap anywhere for that finger when the first lifted before its timer ran.
                    pinchOutside={false}
                    snappable={!loose}
                    keepRatio={keep}
                    snapThreshold={6}
                    isDisplaySnapDigit={false}
                    snapDirections={SIDES}
                    elementSnapDirections={SIDES}
                    elementGuidelines={rest}
                    verticalGuidelines={pageXs.map((mm) => mm * k)}
                    horizontalGuidelines={pageYs.map((mm) => mm * k)}
                    // Moveable swallows a tap on what is selected, and a group's box covers its blocks. To Moveable the
                    // lift of a finger that held still is a tap too, on one block and on several: it is none.
                    onClick={(e) => touch.current && !held.current && pick(e.inputTarget, false)}
                    // A press on a block is the desk's to pick by. Moveable drags by it too, and would take it for a click
                    // on the group where the point the mouse reports lies beside what was pressed.
                    onClickGroup={(e) => cover.current && !held.current && !brushing.current && pick(e.inputTarget, e.inputEvent.shiftKey)}
                    // A press on a cell of the table being edited picks cells: it moves no block.
                    onDragStart={(e) => (cellDrag.current || brushing.current ? e.stopDrag() : begin([e.target]))}
                    onDragGroupStart={(e) => (brushing.current ? e.stopDrag() : begin(e.targets))}
                    onDrag={(e) => !brushing.current && drag([e])}
                    onDragGroup={(e) => !brushing.current && drag(e.events, e)}
                    onDragEnd={(e) => leave(e.isDrag)}
                    onDragGroupEnd={(e) => leave(e.isDrag)}
                    // Ctrl resizes about the centre.
                    onBeforeResize={(e) => mod & CENTRE && e.setFixedDirection([0, 0])}
                    onBeforeResizeGroup={(e) => mod & CENTRE && e.setFixedDirection([0, 0])}
                    onResizeStart={(e) => begin([e.target])}
                    onResizeGroupStart={(e) => begin(e.targets)}
                    // A table stays level, and a line turns by its ends.
                    rotatable={!cropping && free.length === sel.length && !sel.some((b) => b.type === "table") && !sel.some((b) => isLine(b) && thing(b) === b.id)}
                    rotationPosition="top"
                    onRotateStart={(e) => {
                      spot.current = [e.clientX, e.clientY];
                      begin([e.target]);
                    }}
                    onRotateGroupStart={(e) => {
                      spot.current = [e.clientX, e.clientY];
                      begin(e.targets);
                    }}
                    onRotate={rotate}
                    onRotateGroup={rotate}
                    onRotateEnd={rotated}
                    // Moveable measures the box around the blocks anew: turned with one group's blocks, else level.
                    onRotateGroupEnd={(e) => {
                      moveable.current!.updateRect();
                      rotated(e);
                    }}
                    onResize={(e) => resize([e])}
                    onResizeGroup={(e) => resize(e.events)}
                    onResizeEnd={resizeEnded}
                    onResizeGroupEnd={resizeEnded}
                  />
                </>
              )}
    </>
  );
}
