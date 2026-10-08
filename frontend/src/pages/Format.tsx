// The format panel's settings for the school blocks, and the numbering any block can have.
import { useEffect, useState, type MouseEvent } from "react";
import { AlignVerticalJustifyCenter, AlignVerticalJustifyEnd, AlignVerticalJustifyStart, FlipHorizontal2, FlipVertical2, List as Bullets, ListOrdered, Lock, LockOpen, RotateCcw, RotateCw, TextAlignCenter, TextAlignEnd, TextAlignStart, type LucideIcon } from "lucide-react";
import Numbering from "../components/Numbering";
import { FONTS, MARGIN, RULINGS, boxed, counts, isLine, mathsHeight, parasOf, rowsOf, symbol, type Align, type Axis, type Block, type Box, type List, type MathsProps, type Ruling, type TableBlock, type Valign } from "../sheet";
import type { Marks, Picked } from "./Field";
import Maths from "./Maths";
import { SYMBOLS } from "../symbols";

type Props = {
  sel: Block[];
  // Sets props on every selected block of one type.
  style: (type: Block["type"], props: object, key?: string) => void;
  // Sets what a text and a shape share on every selected one of them.
  look: (props: object, key?: string) => void;
  // Sets bold, italic, underline or colour on the words picked in the text being edited, or else as `look` does.
  paint: (props: Marks, key?: string) => void;
  // Makes a list of the paragraphs the caret stands in, or else of all the selected texts.
  itemize: (kind: List) => void;
  // What is picked in the text being edited.
  part?: Picked;
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
  // Adds a row or a column to a table before the one at `i`, or takes the one at `i` away.
  rank: (b: TableBlock, axis: "row" | "col", i: number, add: boolean) => void;
  // The cell of the table being edited, counted row by row.
  cell?: number;
  // Starts or ends crop mode; absent unless one picture that is not locked is selected.
  crop?: () => void;
  cropping: boolean;
  // Turns every selected block by so many degrees about its own centre.
  spin: (by: number) => void;
  // Mirrors the selected pictures, symbols and shapes across or down.
  mirror: (axis: Axis) => void;
  // Whether a new width sets the height to match, in the fields and on the handles.
  lock: boolean;
  setLock: (on: boolean) => void;
  // The width and height in mm of the page in use.
  size: number[];
};

const ALIGNS: [Align, string, LucideIcon][] = [["left", "Links", TextAlignStart], ["center", "Mitte", TextAlignCenter], ["right", "Rechts", TextAlignEnd]];
const LISTS: [List, string, LucideIcon][] = [["bullet", "Aufzählung", Bullets], ["number", "Nummerierung", ListOrdered]];
const VALIGNS: [Valign, string, LucideIcon][] = [["top", "Oben", AlignVerticalJustifyStart], ["middle", "Mitte", AlignVerticalJustifyCenter], ["bottom", "Unten", AlignVerticalJustifyEnd]];
// The turns by a quarter and the two flips: a flip has no degrees.
const TURNS: [string, LucideIcon, number][] = [["Rechtsdrehung 90°", RotateCw, 90], ["Linksdrehung 90°", RotateCcw, -90], ["Horizontal spiegeln", FlipHorizontal2, 0], ["Vertikal spiegeln", FlipVertical2, 0]];
const round = (n: number) => Math.round(n * 100) / 100;
// An angle as a block stores it: from 0 up to 360.
export const norm = (a: number) => round(((a % 360) + 360) % 360) % 360;
// The box around several blocks.
export const bounds = (bs: Box[]) => {
  const [x, y] = [Math.min(...bs.map((b) => b.x)), Math.min(...bs.map((b) => b.y))];
  return { x, y, w: Math.max(...bs.map((b) => b.x + b.w)) - x, h: Math.max(...bs.map((b) => b.y + b.h)) - y };
};

// Whether the words picked in the field have a look, or with no field every selected text: as in PowerPoint, a
// look goes on unless all have it.
export const has = (sel: Block[], part: Picked | undefined, name: "bold" | "italic" | "underline") =>
  part ? !!part.marks[name] : sel.every((b) => !boxed(b) || boxed(b)![name]);

export default function Format({ sel, style, look, paint, itemize, part, place, rank, cell, crop, cropping, spin, mirror, lock, setLock, size: [W, H] }: Props) {
  // A locked block neither turns nor flips. A table stays level, a line turns by its ends, and only a picture, a
  // symbol or a shape can flip.
  const fixed = sel.some((b) => b.locked);
  const level = fixed || sel.some((b) => b.type === "table" || isLine(b));
  const plain = fixed || !sel.some((b) => b.type === "image" || b.type === "symbol" || b.type === "shape");
  const of = <T extends Block["type"]>(type: T) => sel.filter((b): b is Extract<Block, { type: T }> => b.type === type);
  // The first block of a type shows its settings; a change goes to all of them.
  // A shape that is no line holds text as a text block does.
  const text = sel.map(boxed).find((p) => p);
  // Picked words show their own look, and the list is that of the caret's paragraph, or of the text's first.
  const shown = { ...text, ...part?.marks };
  const kind = text && (part ?? parasOf(text)[0]).list;
  // A press on these buttons leaves the focus, and so the picked words, in the field.
  const stay = (e: MouseEvent) => e.preventDefault();
  const rulings = of("ruling");
  const tables = of("table");
  const [points] = of("points");
  const [sign] = of("symbol");
  // The generator's limits belong to one block.
  const maths = sel.length === 1 && sel[0].type === "maths" ? sel[0] : undefined;
  const { mark } = sel[0];

  // A ruling keeps its rows when its type changes, so the block's height follows.
  const rule = (kind: Ruling, rows?: number) => {
    style("ruling", { kind }, "ruling");
    place(rulings.map((b) => [b.id, { h: round(Math.max(1, rows ?? rowsOf(b)) * RULINGS[kind].row) }]), "ruling");
  };
  // A maths block's height follows its exercises when they need more or less room than before.
  const calc = (props: MathsProps) => {
    style("maths", props, "maths");
    if (mathsHeight(props) !== mathsHeight(maths!.props)) place([[maths!.id, { h: mathsHeight(props) }]], "maths");
  };
  const number = (to?: string) => place(sel.map((b) => [b.id, { mark: to }]));

  // The fields for place, size and angle, as in PowerPoint's size pane. A field shows what all the blocks share.
  // A selection with a group in it is one thing: it shows the box around it, which only moves.
  const whole = sel.some((b) => b.group);
  const box = bounds(sel);
  const shared = (of: (b: Block) => number) => (whole ? undefined : sel.every((b) => of(b) === of(sel[0])) ? of(sel[0]) : undefined);
  // A picture and a symbol always keep their shape.
  const shaped = sel.some((b) => b.type === "image" || b.type === "symbol");
  const keep = lock || shaped;
  const move = (axis: Axis, to: number) => place(sel.map((b) => [b.id, { [axis]: whole ? round(b[axis] + to - box[axis]) : to }]));
  // The corner stays. With the lock each block keeps its own shape.
  const resize = (side: "w" | "h", to: number) => {
    const other = side === "w" ? "h" : "w";
    if (to > 0) place(sel.map((b) => [b.id, { [side]: to, ...(keep && b[side] > 0 && { [other]: round((b[other] * to) / b[side]) }) }]));
  };
  const angle = shared((b) => b.angle ?? 0);
  const turn = (to: number) => norm(to) !== angle && place(sel.map((b) => [b.id, { angle: norm(to) }]));

  return (
    <>
      <div className="geo">
        <h2>Position und Größe in mm</h2>
        <Num label="X" value={whole ? round(box.x) : shared((b) => b.x)} disabled={fixed} onCommit={(n) => move("x", n)} />
        <Num label="Y" value={whole ? round(box.y) : shared((b) => b.y)} disabled={fixed} onCommit={(n) => move("y", n)} />
        <Num label="Breite" value={whole ? round(box.w) : shared((b) => b.w)} disabled={fixed || whole || sel.some(isLine)} onCommit={(n) => resize("w", n)} />
        <Num label="Höhe" value={whole ? round(box.h) : shared((b) => b.h)} disabled={fixed || whole || sel.some(isLine)} onCommit={(n) => resize("h", n)} />
        <Num label="Drehung" value={angle} disabled={level || whole} onCommit={turn} />
        <span>
          °
          <button className={keep ? "ib on" : "ib"} aria-label="Seitenverhältnis sperren" title="Seitenverhältnis sperren" aria-pressed={keep} disabled={fixed || whole || shaped} onClick={() => setLock(!lock)}>
            {keep ? <Lock size={14} aria-hidden /> : <LockOpen size={14} aria-hidden />}
          </button>
        </span>
      </div>
      {text && (
        <>
          <h2>Schrift</h2>
          <select aria-label="Schriftart" value={text.font ?? "andika"} onChange={(e) => look({ font: e.target.value })}>
            {Object.entries(FONTS).map(([font, [name]]) => (
              <option key={font} value={font}>
                {name}
              </option>
            ))}
          </select>
          <div className="seg">
            <button aria-label="Schrift kleiner" onClick={() => look({ size: Math.max(8, text.size - 2) })}>−</button>
            <output>{text.size} pt</output>
            <button aria-label="Schrift größer" onClick={() => look({ size: text.size + 2 })}>＋</button>
          </div>
          <div className="seg" onMouseDown={stay}>
            {([["bold", "Fett"], ["italic", "Kursiv"], ["underline", "Unterstrichen"]] as const).map(([prop, label]) => (
              <button key={prop} className={`${prop}${has(sel, part, prop) ? " on" : ""}`} aria-label={label} aria-pressed={has(sel, part, prop)} onClick={() => paint({ [prop]: !has(sel, part, prop) })}>
                {label[0]}
              </button>
            ))}
          </div>
          <div className="seg" onMouseDown={stay}>
            {LISTS.map(([value, label, Icon]) => (
              <button key={value} className={kind === value ? "on" : ""} aria-label={label} title={label} aria-pressed={kind === value} onClick={() => itemize(value)}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg" onMouseDown={stay}>
            {ALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={text.align === value ? "on" : ""} aria-label={label} title={label} aria-pressed={text.align === value} onClick={() => look({ align: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg" onMouseDown={stay}>
            {VALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={(text.valign ?? "top") === value ? "on" : ""} aria-label={label} title={label} aria-pressed={(text.valign ?? "top") === value} onClick={() => look({ valign: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={shown.color ?? "#222222"} onChange={(e) => paint({ color: e.target.value }, "color")} />
          </label>
          <label>
            Zeilenabstand
            <input type="range" min={1} max={3} step={0.1} value={text.spacing ?? 1.3} onChange={(e) => look({ spacing: +e.target.value }, "spacing")} />
          </label>
        </>
      )}
      {rulings.length > 0 && (
        <>
          <h2>Lineatur</h2>
          <select aria-label="Art der Lineatur" value={rulings[0].props.kind} onChange={(e) => rule(e.target.value as Ruling)}>
            {Object.entries(RULINGS).map(([kind, { name }]) => (
              <option key={kind} value={kind}>
                {name}
              </option>
            ))}
          </select>
          <div className="seg">
            <button aria-label="Eine Zeile weniger" onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) - 1)}>−</button>
            <output>{rowsOf(rulings[0])} Zeilen</output>
            <button aria-label="Eine Zeile mehr" onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) + 1)}>＋</button>
          </div>
          <label>
            Farbe
            <input type="color" value={rulings[0].props.color} onChange={(e) => style("ruling", { color: e.target.value }, "color")} />
          </label>
          <div className="row">
            <button onClick={() => place(rulings.map((b) => [b.id, { x: MARGIN, w: W - 2 * MARGIN }]))}>Seitenbreite</button>
            <button onClick={() => place(rulings.map((b) => [b.id, { h: round(Math.max(1, Math.floor((H - MARGIN - b.y) / RULINGS[b.props.kind].row + 0.05)) * RULINGS[b.props.kind].row) }]))}>Bis Seitenende</button>
          </div>
          <p className="hint">Doppelklick auf die Lineatur, um hineinzuschreiben.</p>
          {RULINGS[rulings[0].props.kind].at && (
            <select aria-label="Schriftart auf den Zeilen" value={rulings[0].props.font ?? "andika"} onChange={(e) => style("ruling", { font: e.target.value })}>
              {Object.entries(FONTS).map(([font, [name]]) => (
                <option key={font} value={font}>
                  {name}
                </option>
              ))}
            </select>
          )}
          <button className={rulings[0].props.trace ? "on" : ""} aria-pressed={!!rulings[0].props.trace} onClick={() => style("ruling", { trace: !rulings[0].props.trace })}>
            Nachspurtext
          </button>
        </>
      )}
      {tables.length > 0 && (
        <>
          <h2>Tabelle</h2>
          {/* More or fewer rows and columns, for one table: each has cells of its own. They come and go at the end,
              or beside the cell being edited, as in PowerPoint. */}
          {tables.length === 1 &&
            (["Zeile", "Spalte"] as const).map((name, i) => {
              const axis = i ? "col" : "row";
              const n = [tables[0].props.cells.length, tables[0].props.cols.length];
              if (cell === undefined)
                return (
                  <div key={name} className="seg">
                    <button aria-label={`Eine ${name} weniger`} onClick={() => rank(tables[0], axis, n[i] - 1, false)}>−</button>
                    <output>{n[i]} {name}n</output>
                    <button aria-label={`Eine ${name} mehr`} onClick={() => rank(tables[0], axis, n[i], true)}>＋</button>
                  </div>
                );
              const at = i ? cell % n[1] : Math.floor(cell / n[1]);
              return (
                <div key={name} className="acts" onMouseDown={stay}>
                  <button onClick={() => rank(tables[0], axis, at, true)}>{name} {i ? "links" : "darüber"}</button>
                  <button onClick={() => rank(tables[0], axis, at + 1, true)}>{name} {i ? "rechts" : "darunter"}</button>
                </div>
              );
            })}
          {/* The last row or column stays. A disabled button would take the focus from the cell all the same. */}
          {tables.length === 1 && cell !== undefined && (
            <div className="acts" onMouseDown={stay}>
              <button aria-disabled={tables[0].props.cells.length < 2} onClick={() => rank(tables[0], "row", Math.floor(cell / tables[0].props.cols.length), false)}>Zeile löschen</button>
              <button aria-disabled={tables[0].props.cols.length < 2} onClick={() => rank(tables[0], "col", cell % tables[0].props.cols.length, false)}>Spalte löschen</button>
            </div>
          )}
          <select aria-label="Schriftart der Tabelle" value={tables[0].props.font ?? "andika"} onChange={(e) => style("table", { font: e.target.value })}>
            {Object.entries(FONTS).map(([font, [name]]) => (
              <option key={font} value={font}>
                {name}
              </option>
            ))}
          </select>
          <div className="seg">
            <button aria-label="Schrift kleiner" onClick={() => style("table", { size: Math.max(8, tables[0].props.size - 2) })}>−</button>
            <output>{tables[0].props.size} pt</output>
            <button aria-label="Schrift größer" onClick={() => style("table", { size: tables[0].props.size + 2 })}>＋</button>
          </div>
          <div className="seg">
            {ALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={tables[0].props.align === value ? "on" : ""} aria-label={label} title={label} aria-pressed={tables[0].props.align === value} onClick={() => style("table", { align: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={tables[0].props.color ?? "#222222"} onChange={(e) => style("table", { color: e.target.value }, "color")} />
          </label>
          <label>
            Linien
            <input type="color" value={tables[0].props.line} onChange={(e) => style("table", { line: e.target.value }, "line")} />
          </label>
          <button className={tables[0].props.head ? "on" : ""} aria-pressed={!!tables[0].props.head} onClick={() => style("table", { head: !tables[0].props.head })}>
            Kopfzeile
          </button>
          <p className="hint">Doppelklick auf eine Zelle, um hineinzuschreiben.</p>
        </>
      )}
      {maths && <Maths key={maths.id} block={maths} apply={calc} />}
      {points && (
        <>
          <h2>Punkte</h2>
          <div className="seg">
            <button aria-label="Ein Punkt weniger" onClick={() => style("points", { max: Math.max(1, points.props.max - 1) })}>−</button>
            <output>{points.props.max}</output>
            <button aria-label="Ein Punkt mehr" onClick={() => style("points", { max: points.props.max + 1 })}>＋</button>
          </div>
        </>
      )}
      {sign && (
        <>
          <h2>Symbol</h2>
          <Symbols value={sign.props.code} onPick={(code) => style("symbol", { code })} />
        </>
      )}
      {crop && (
        <>
          <h2>Bild</h2>
          <button className={cropping ? "wide on" : "wide"} aria-pressed={cropping} onClick={crop}>
            {cropping ? "Fertig" : "Zuschneiden"}
          </button>
        </>
      )}
      <h2>Drehen</h2>
      <div className="seg">
        {TURNS.map(([label, Icon, by]) => (
          <button key={label} aria-label={label} title={label} disabled={by ? level : plain} onClick={() => (by ? spin(by) : mirror(label[0] === "H" ? "x" : "y"))}>
            <Icon size={14} aria-hidden />
          </button>
        ))}
      </div>
      <h2>Nummerierung</h2>
      <Numbering value={mark} onChange={number} symbol={() => number("2B50")} />
      {mark && !counts(mark) && <Symbols value={mark} onPick={number} />}
    </>
  );
}

// A field for a number. What is typed counts on Enter or when the field is left, and Escape drops it. An arrow up
// or down steps by one. `value` is absent where the selected blocks differ.
function Num({ label, value, disabled, onCommit }: { label: string; value?: number; disabled: boolean; onCommit: (n: number) => void }) {
  const [draft, setDraft] = useState<string>();
  // The field follows the sheet: a drag or an undo takes the place of what was typed.
  useEffect(() => setDraft(undefined), [value]);
  // Only digits with a comma or a point count: "1e3" and "Infinity" are numbers to JavaScript alone.
  const read = () => (/^-?\d+([.,]\d+)?$/.test(draft?.trim() ?? "") ? round(Number(draft!.replace(",", "."))) : NaN);
  // Without a draft the blur that follows Enter finds nothing to set.
  const commit = (n: number) => {
    setDraft(undefined);
    if (!Number.isNaN(n) && n !== value) onCommit(n);
  };
  return (
    <label>
      {label}
      <input
        className="mm"
        type="text"
        inputMode="decimal"
        disabled={disabled}
        value={draft ?? (value === undefined ? "" : String(round(value)).replace(".", ","))}
        onChange={(e) => setDraft(e.target.value)}
        onFocus={(e) => e.target.select()}
        onBlur={() => draft !== undefined && commit(read())}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit(read());
          if (e.key === "Escape") setDraft(undefined);
          if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
          e.preventDefault();
          commit(round((draft === undefined ? (value ?? NaN) : read()) + (e.key === "ArrowUp" ? 1 : -1)));
        }}
      />
    </label>
  );
}

// Every symbol as a button, narrowed by a search through the German and English names.
function Symbols({ value, onPick }: { value: string; onPick: (code: string) => void }) {
  const [query, setQuery] = useState("");
  const found = SYMBOLS.filter(([, de, en]) => `${de} ${en}`.toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <>
      <input type="text" aria-label="Symbol suchen" placeholder="Suchen, z. B. Schere" value={query} onChange={(e) => setQuery(e.target.value)} />
      <div className="symbols">
        {found.map(([code, de]) => (
          <button key={code} className={code === value ? "on" : ""} aria-label={de} title={de} onClick={() => onPick(code)}>
            <img src={symbol(code)} alt="" />
          </button>
        ))}
      </div>
      {!found.length && <p className="hint">Kein Symbol gefunden.</p>}
    </>
  );
}
