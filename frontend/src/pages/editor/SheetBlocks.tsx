// The blocks of one page, scaled as the PDF draws them.
import type { CSSProperties } from "react";
import { Draw, K, keepsFractions, Mark, Numbers, PageNumber, ScoreInput, boxed, fadeOf, listOf, stepOf, sum, traceOf, turned, writtenStyle, type Page } from "../../sheet";
import Field from "../Field";
import { GroundView } from "../../ground";
import { EDGE, heightsOf, next } from "../../cells";
import { round } from "./palette";
import { useTools } from "./useTools";

export default function SheetBlocks({ s: session, p, n }: { s: ReturnType<typeof useTools>; p: Page; n: number }) {
  const all = session.all;
  const at = session.at;
  const beginGround = session.beginGround;
  const boxOf = session.boxOf;
  const change = session.change;
  const clicked = session.clicked;
  const dragGround = session.dragGround;
  const editing = session.editing;
  const endGround = session.endGround;
  const entire = session.entire;
  const field = session.field;
  const fill = session.fill;
  const grid = session.grid;
  const hist = session.hist;
  const hop = session.hop;
  const ids = session.ids;
  const k = session.k;
  const laidMm = session.laidMm;
  const left = session.left;
  const live = session.live;
  const look = session.look;
  const ns = session.ns;
  const own = session.own;
  const page = session.page;
  const pick = session.pick;
  const reach = session.reach;
  const scoreOn = session.scoreOn;
  const setEditing = session.setEditing;
  const setPart = session.setPart;
  const setReach = session.setReach;
  const setStone = session.setStone;
  const setWords = session.setWords;
  const shaping = session.shaping;
  const sink = session.sink;
  const sizes = session.sizes;
  const slot = session.slot;
  const solved = session.solved;
  const stays = session.stays;
  const stone = session.stone;
  const style = session.style;
  const top = session.top;
  const trimming = session.trimming;
  const typeRuling = session.typeRuling;
  const typeStone = session.typeStone;
  const words = session.words;
  return (
    <>
              {/* The blocks are laid out as the PDF's are and scaled to the zoom as one. What marks or moves them lies
                  beside them, in px of the screen. */}
              <div className={keepsFractions() ? "scaled fractions" : "scaled"} style={{ width: sizes[n][0] * K, height: sizes[n][1] * K, transform: `scale(${k / K})`, "--px": `${K / k}px` } as CSSProperties}>
                {p.ground && (
                  <div className="ground-clip">
                    <GroundView
                      ground={p.ground}
                      w={sizes[n][0]}
                      h={sizes[n][1]}
                      k={K}
                      live={shaping && n === page && !trimming}
                      onPointerDown={shaping && n === page && !trimming ? (e) => beginGround(e, "move") : undefined}
                      onPointerMove={shaping && n === page ? dragGround : undefined}
                      onPointerUp={endGround}
                    />
                  </div>
                )}
                <PageNumber doc={hist.doc} page={n} />
                {p.blocks.map((b) => (

                  <div
                    key={b.id}
                    data-id={b.id}
                    className={ids.includes(b.id) ? "block sel" : "block"}
                    style={{ left: b.x * K, top: b.y * K, width: b.w * K, height: b.h * K, zIndex: b.z, ...turned(b) }}
                  >
                    <Draw block={b} k={K} solved={solved} at={editing === b.id ? slot : undefined} reach={editing === b.id ? reach : undefined}>
                      {/* Only the text being edited needs a field; the others draw as they do in the PDF. */}
                      {boxed(b) && editing === b.id ? (
                        <Field
                          view={field}
                          props={boxed(b)!}
                          hint={b.type === "text"}
                          all={entire.current}
                          at={clicked.current}
                          change={look}
                          pick={(next) => setPart((now) => (JSON.stringify(now) === JSON.stringify(next) ? now : next))}
                          blur={(e) => stays(e) || setEditing("")}
                          end={() => setEditing("")}
                        />
                      ) : b.type === "text" && !b.props.text && !b.props.rich && b.props.list !== true ? (
                        <div className="rich" data-hint="">
                          <p>
                            <br />
                          </p>
                        </div>
                      ) : b.type === "ruling" && !listOf(b) ? (
                        <textarea
                          className="written"
                          data-trace={traceOf(b.props)}
                          data-fade={fadeOf(b.props)}
                          value={b.props.text ?? ""}
                          readOnly={editing !== b.id}
                          // Tab from a field of the panel does not stop at a Lineatur that is not written in.
                          tabIndex={editing === b.id ? undefined : -1}
                          style={writtenStyle(b, K)}
                          onChange={(e) => typeRuling(b, e.target.value, e.currentTarget)}
                          // Tab types nothing and stays here: the browser's would end the writing. Escape and F2 end
                          // it themselves: after a press in the panel the blur would not.
                          onKeyDown={(e) => {
                            if (e.key === "Tab") e.preventDefault();
                            if (e.key !== "Escape" && e.key !== "F2") return;
                            e.currentTarget.blur();
                            setEditing("");
                          }}
                          onBlur={(e) => stays(e) || setEditing("")}
                          // A line typed past the last row would scroll the others off their rows.
                          onScroll={(e) => (e.currentTarget.scrollTop = 0)}
                        />
                      ) : b.type === "table" && editing === b.id ? (
                        <textarea
                          value={b.props.cells.flat()[slot]}
                          onChange={(e) => {
                            setReach(undefined);
                            // A table without row heights gets, with the first text typed in it, the heights its rows have
                            // now: from then on a row grows alone, as in PowerPoint, and comes back when its text goes. A
                            // table saved lower than its texts need has no such heights.
                            const grid = e.currentTarget.closest<HTMLElement>(".table")!;
                            // The box of solution words is the grid's rows after the table's own, so the rows fill b.h less that.
                            // What the box is stretched by goes to the rows, so they and the box as it needs to be fill b.h.
                            const boxMm = getComputedStyle(grid).gridTemplateRows.split(" ").slice(b.props.cells.length).reduce((all, p) => all + parseFloat(p) / K, 0);
                            const fill = boxMm > 0 ? b.h - EDGE - boxOf(grid, b.props.cells.length) : sum(laidMm);
                            const rows = !heightsOf(b.props) && laidMm.length && Math.abs(sum(laidMm) - (b.h - EDGE - boxMm)) <= 0.05 ? { rows: laidMm.map((h) => round((h * fill) / sum(laidMm))) } : {};
                            // The table may come down with its text when it has no spare room now: a table made taller
                            // than its rows need keeps that height.
                            const own = grid.style.height;
                            grid.style.height = "auto";
                            sink.current = "rows" in rows || parseFloat(getComputedStyle(grid).height) / K >= b.h - 0.05;
                            grid.style.height = own;
                            style("table", { cells: b.props.cells.map((row, r) => row.map((text, c) => (r * row.length + c === slot ? e.target.value : text))), ...rows }, "text");
                          }}
                          onKeyDown={(e) => hop(e, b)}
                          onBlur={(e) => stays(e) || setEditing("")}
                        />
                      ) : b.type === "points" && editing === b.id ? (
                        <ScoreInput max={b.props.max} change={(max) => scoreOn(b.id, max, n)} end={() => setEditing("")} blur={(e) => stays(e) || setEditing("")} />
                      ) : b.type === "name" && editing === b.id ? (
                        // Each word is a field of its own, in its place on the line. Enter and leaving the line keep them.
                        // A hidden field has no input: its word stays as it is.
                        words.map((word, i) => !(b.props.hidden ?? []).includes(i) && (
                          <input
                            key={i}
                            aria-label={`Feld ${i + 1}`}
                            value={word}
                            onChange={(e) => setWords((ws) => ws.map((w, j) => (j === i ? e.target.value : w)))}
                            onKeyDown={(e) => {
                              if (e.key === "Escape") setEditing("");
                              if (e.key === "Enter" || e.key === "F2") e.currentTarget.blur();
                            }}
                            onBlur={(e) => {
                              if ((e.relatedTarget as Element | null)?.closest(`[data-id="${b.id}"]`)) return;
                              stays(e) || setEditing("");
                            }}
                          />
                        ))
                      ) : undefined}
                    </Draw>
                    {stone?.id === b.id && (
                      <input
                        className="stone-field"
                        inputMode="numeric"
                        aria-label="Zahl im Stein"
                        autoFocus
                        value={stone.text}
                        style={{ left: stone.box[0], top: stone.box[1], width: stone.box[2], height: stone.box[3], fontSize: stone.box[3] * 0.6 }}
                        onFocus={(e) => e.currentTarget.select()}
                        onKeyDown={(e) => {
                          // The keys are the field's: the sheet's own keys do not take the digits or the Enter.
                          e.stopPropagation();
                          if (e.key === "Enter" || e.key === "Escape") setStone(null);
                        }}
                        onBlur={() => setStone(null)}
                        onChange={(e) => {
                          if (!/^\d{0,4}$/.test(e.target.value)) return;
                          setStone({ ...stone, text: e.target.value });
                          typeStone(b, stone.wall, stone.at, e.target.value);
                        }}
                      />
                    )}
                    {b.type === "text" && stepOf(b.props.lines) > 0 && <Numbers block={b} />}
                    <Mark block={b} k={K} n={ns.get(b.id)} />
                  </div>
                ))}
              </div>
    </>
  );
}
