// The format of the picked blocks.
import { flushSync } from "react-dom";
import { owe } from "../../saves";
import { isLine, type ImageBlock, type NameBlock } from "../../sheet";
import { list } from "../Field";
import { canHelp } from "../../texthelp";
import Format from "../Format";
import TextHelp from "../TextHelp";
import { Tool } from "./Tool";
import { FRAMES, DASHES, LABELS, ALIGNS, pickName, TABS, lines, step } from "./palette";
import { useTools } from "./useTools";
import PanelRest from "./PanelRest";

export default function FormatPanel({ s: session }: { s: ReturnType<typeof useTools> }) {
  const H = session.H;
  const W = session.W;
  const align = session.align;
  const among = session.among;
  const at = session.at;
  const blocks = session.blocks;
  const border = session.border;
  const boxes = session.boxes;
  const bump = session.bump;
  const cell = session.cell;
  const cramped = session.cramped;
  const cropping = session.cropping;
  const cutting = session.cutting;
  const distribute = session.distribute;
  const done = session.done;
  const drawLines = session.drawLines;
  const edit = session.edit;
  const editing = session.editing;
  const evenCells = session.evenCells;
  const extend = session.extend;
  const fadePicture = session.fadePicture;
  const feed = session.feed;
  const file = session.file;
  const fill = session.fill;
  const fit = session.fit;
  const free = session.free;
  const from = session.from;
  const full = session.full;
  const gapEvery = session.gapEvery;
  const gapping = session.gapping;
  const held = session.held;
  const heldIds = session.heldIds;
  const help = session.help;
  const helping = session.helping;
  const hist = session.hist;
  const ids = session.ids;
  const itemize = session.itemize;
  const laid = session.laid;
  const laidMm = session.laidMm;
  const layer = session.layer;
  const leaf = session.leaf;
  const learnt = session.learnt;
  const lineaturen = session.lineaturen;
  const lock = session.lock;
  const locked = session.locked;
  const look = session.look;
  const mendWord = session.mendWord;
  const merge = session.merge;
  const mirror = session.mirror;
  const name = session.name;
  const nameFields = session.nameFields;
  const onlyShown = session.onlyShown;
  const page = session.page;
  const paint = session.paint;
  const panelSized = session.panelSized;
  const part = session.part;
  const place = session.place;
  const pressed = session.pressed;
  const rank = session.rank;
  const reach = session.reach;
  const right = session.right;
  const rulers = session.rulers;
  const same = session.same;
  const seek = session.seek;
  const sel = session.sel;
  const setAt = session.setAt;
  const setChosen = session.setChosen;
  const setFrom = session.setFrom;
  const setHelp = session.setHelp;
  const setIds = session.setIds;
  const setLock = session.setLock;
  const setOnPage = session.setOnPage;
  const setTab = session.setTab;
  const showField = session.showField;
  const shown = session.shown;
  const sizable = session.sizable;
  const sizeCells = session.sizeCells;
  const slot = session.slot;
  const spin = session.spin;
  const stacked = session.stacked;
  const stroke = session.stroke;
  const style = session.style;
  const tab = session.tab;
  const table = session.table;
  const takeList = session.takeList;
  const takeText = session.takeText;
  const thing = session.thing;
  const things = session.things;
  const tight = session.tight;
  const title = session.title;
  const tour = session.tour;
  const traced = session.traced;
  const unmerge = session.unmerge;
  const update = session.update;
  const words = session.words;
  return (
    <>
      {right && (
        <aside className="panel">
          {!leaf && (
            <div className="tabs" role="tablist">
              {TABS.map((t) => (
                <button key={t} role="tab" data-tour={t} aria-selected={tab === t} onClick={() => setTab(t)}>
                  {t}
                </button>
              ))}
            </div>
          )}
          {tab === "Format" && !sel.length && <p className="hint">Wähle etwas auf dem Blatt aus, um es zu formatieren.</p>}
          {/* Blattform's panel has no tabs, and its bar no room for one more mode: there this button leads to the
              list, and "Start" in the bar leads back. */}
          {tab === "Format" && !sel.length && leaf && <button onClick={() => setTab("Lernwörter")}>Lernwörter</button>}
          {tab === "Format" && sel.length > 0 && (
            <>
              <p className="what">
                {pickName(sel, blocks)}
              </p>
              <Format
                owe={(entry) => owe(file.id, entry)}
                // A block of a group with a locked one is as fixed there as the locked one.
                sel={sel.map((b) => (free.includes(b) ? b : { ...b, locked: true }))}
                style={style}
                bump={bump}
                look={look}
                mendWord={mendWord}
                traced={traced}
                paint={paint}
                itemize={itemize}
                gap={gapping}
                every={gapEvery}
                part={part}
                // A text that a typed size left higher than its box grows back, as after a resize by handle.
                place={(boxes, key) => {
                  tight.current = true;
                  place(boxes, key);
                }}
                rank={rank}
                cell={editing && editing === table?.id ? slot : undefined}
                reach={editing && editing === table?.id ? reach : undefined}
                merge={merge}
                unmerge={unmerge}
                laid={laidMm}
                full={full}
                cramped={cramped}
                held={heldIds}
                onSize={(ids) => (panelSized.current = ids)}
                sizeCells={sizeCells}
                evenCells={evenCells}
                lines={drawLines}
                border={table && border}
                cutting={cutting}
                cropping={!!cropping}
                spin={spin}
                mirror={mirror}
                alone={(b) => thing(b) === b.id}
                lock={lock}
                setLock={setLock}
                from={from}
                setFrom={setFrom}
                size={[W, H]}
                doc={hist.doc}
                crop={sel.length === 1 && free[0]?.type === "image" ? () => (cropping ? done() : edit(free[0].id)) : undefined}
                words={learnt}
                lineaturen={lineaturen}
                list={takeList}
                link={takeText}
                feed={feed}
                onHelp={canHelp(sel) ? () => setHelp({ id: sel[0].id, page }) : undefined}
                toList={() => setTab("Lernwörter")}
              />
              {helping && help && (
                <TextHelp
                  block={helping}
                  page={help.page}
                  onClose={() => setHelp(null)}
                  onTake={(fn, to) => {
                    const from = help.page;
                    // The box grows with the new words, in this same step, as a text the teacher typed does.
                    tight.current = true;
                    flushSync(() => {
                      update(fn, "", to ?? from);
                      setHelp(null);
                      if (to !== undefined && to !== from) {
                        setAt(to);
                        setChosen([to]);
                        setIds([]);
                      }
                    });
                    if (to !== undefined && to !== from) seek();
                  }}
                />
              )}
              {free.length > 0 && free.every((b) => b.type === "image") && (
                <>
                  <h2>Bild</h2>
                  <label>
                    Transparenz
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={Math.round((1 - ((free[0] as ImageBlock).props.opacity ?? 1)) * 100)}
                      onChange={(e) => fadePicture(Math.round(100 - +e.target.value) / 100)}
                    />
                  </label>
                </>
              )}
              {nameFields.length > 0 && (
                <>
                  <h2>Namenszeile</h2>
                  {/* The last field a picked line shows stays shown. */}
                  {nameFields.map((word, i) => {
                    const off = (free[0] as NameBlock).props.hidden ?? [];
                    const shown = !off.includes(i);
                    return (
                      <label key={i} className="tick">
                        <input type="checkbox" checked={shown} disabled={shown && free.some((b) => onlyShown(b as NameBlock, i))} onChange={(e) => showField(i, e.target.checked)} /> {word}
                      </label>
                    );
                  })}
                </>
              )}
              {boxes.length > 0 && (
                <>
                  <h2>Füllung und Rand</h2>
                  {/* A line stays a line. */}
                  {!rulers.length && (
                    <div className="seg">
                      {FRAMES.map(([kind, label]) => (
                        <button key={kind} className={(boxes[0].props.kind ?? "rect") === kind ? "on" : ""} onClick={() => look((boxes[0].props.kind ?? "rect") === kind ? { kind } : { kind, inside: true })}>
                          {label}
                        </button>
                      ))}
                    </div>
                  )}
                  <label>
                    Füllung
                    <input type="color" value={fill === "none" ? "#ffffff" : fill} onChange={(e) => look({ fill: e.target.value }, "fill")} />
                  </label>
                  {/* How far the fill lets through what lies behind it: the text and the border stay solid. */}
                  {!isLine(boxes[0]) && <label>
                    Transparenz
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={Math.round((1 - (boxes[0].props.opacity ?? 1)) * 100)}
                      disabled={fill === "none"}
                      onChange={(e) => look({ opacity: Math.round(100 - +e.target.value) / 100 }, "opacity")}
                    />
                  </label>}
                  {/* The next fill is solid again, as in PowerPoint. */}
                  <button className="wide" disabled={fill === "none"} onClick={() => look({ fill: "none", opacity: undefined })}>Keine Füllung</button>
                  <label>
                    Rand
                    <input type="color" value={stroke === "none" ? "#222222" : stroke} onChange={(e) => look({ stroke: e.target.value }, "stroke")} />
                  </label>
                  {!rulers.length && <button className="wide" disabled={stroke === "none"} onClick={() => look({ stroke: "none", strokeOpacity: undefined })}>Kein Rand</button>}
                  <label>
                    Randstärke
                    <input
                      type="range"
                      min={0.25}
                      max={3}
                      step={0.25}
                      value={boxes[0].props.strokeWidth ?? 0.5}
                      onChange={(e) => look({ strokeWidth: +e.target.value }, "strokeWidth")}
                    />
                  </label>
                  {/* How far the border lets through what lies behind it. A line has only this slider. */}
                  <label>
                    {isLine(boxes[0]) ? "Transparenz" : "Transparenz Linie"}
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={Math.round((1 - (boxes[0].props.strokeOpacity ?? 1)) * 100)}
                      disabled={stroke === "none"}
                      onChange={(e) => look({ strokeOpacity: Math.round(100 - +e.target.value) / 100 }, "strokeOpacity")}
                    />
                  </label>
                  {/* No style is lit while there is no border to show it. */}
                  <div className="seg">
                    {DASHES.map(([dash, label, sign]) => (
                      <button key={label} className={stroke !== "none" && boxes[0].props.dash === dash ? "on" : ""} aria-label={label} title={label} onClick={() => look({ dash })}>
                        {sign}
                      </button>
                    ))}
                  </div>
                  {/* A circle, triangle or star keeps its text in a share of its outline, and a linked text grows on. */}
                  {boxes.every((b) => ["rect", "rounded", "bubble"].includes(b.props.kind ?? "rect") && b.props.list !== true) && (
                    <label className="tick">
                      <input type="checkbox" checked={boxes[0].props.fit === true} onChange={(e) => look({ fit: e.target.checked || undefined })} /> An Text anpassen
                    </label>
                  )}
                </>
              )}
              {rulers.length > 0 && rulers.length === sel.length && (
                <>
                  <h2>Strecke</h2>
                  <label>
                    Länge in cm
                    <input
                      type="number"
                      min={0.1}
                      step={0.1}
                      value={Math.round(Math.hypot(rulers[0].w, rulers[0].h) * 10) / 100}
                      disabled={free.length < sel.length}
                      onChange={(e) => +e.target.value > 0 && extend(+e.target.value * 10)}
                    />
                  </label>
                  <button className={rulers[0].props.ticks ? "wide on" : "wide"} aria-pressed={!!rulers[0].props.ticks} onClick={() => style("shape", { ticks: !rulers[0].props.ticks })}>
                    Striche an den Enden
                  </button>
                  <h2>Länge anschreiben</h2>
                  <div className="seg">
                    {LABELS.map(([label, name]) => (
                      <button key={name} className={rulers[0].props.label === label ? "on" : ""} onClick={() => style("shape", { label })}>
                        {name}
                      </button>
                    ))}
                  </div>
                </>
              )}
              <h2>Ausrichten</h2>
              {/* What the blocks line up with. One block has only the page. */}
              <div className="seg">
                <button className={among ? "on" : ""} aria-pressed={among} disabled={things.length < 2} onClick={() => setOnPage(false)}>Auswahl</button>
                <button className={among ? "" : "on"} aria-pressed={!among} disabled={things.length < 2} onClick={() => setOnPage(true)}>Seite</button>
              </div>
              <div className="acts">
                {ALIGNS.map(([axis, at, label, icon]) => (
                  <Tool key={label} icon={icon} label={label} title={label} disabled={!things.length} onClick={() => align(axis, at)} />
                ))}
              </div>
              <h2>Verteilen</h2>
              <div className="acts">
                <button disabled={among ? things.length < 3 : !things.length} onClick={() => distribute("x")}>Waagerecht</button>
                <button disabled={among ? things.length < 3 : !things.length} onClick={() => distribute("y")}>Senkrecht</button>
              </div>
              <h2>Größe angleichen</h2>
              <div className="acts">
                <button disabled={sizable.length < 2} onClick={() => same("w")}>Gleiche Breite</button>
                <button disabled={sizable.length < 2} onClick={() => same("h")}>Gleiche Höhe</button>
              </div>
              <h2>Ebene</h2>
              <div className="acts">
                <button disabled={!stacked(true)} onClick={(e) => layer(e, true)}>Nach vorn</button>
                <button disabled={!stacked(false)} onClick={(e) => layer(e, false)}>Nach hinten</button>
              </div>
              <div className="acts">
                <button disabled={!stacked(true, true)} onClick={(e) => layer(e, true, true)}>Eine nach vorn</button>
                <button disabled={!stacked(false, true)} onClick={(e) => layer(e, false, true)}>Eine nach hinten</button>
              </div>
            </>
          )}
          <PanelRest s={session} />
        </aside>
      )}
    </>
  );
}
