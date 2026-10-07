// The format panel's settings for the school blocks, and the numbering any block can have.
import { useState, type MouseEvent } from "react";
import { AlignVerticalJustifyCenter, AlignVerticalJustifyEnd, AlignVerticalJustifyStart, List as Bullets, ListOrdered, TextAlignCenter, TextAlignEnd, TextAlignStart, type LucideIcon } from "lucide-react";
import Numbering from "../components/Numbering";
import { FONTS, MARGIN, RULINGS, boxed, counts, mathsHeight, parasOf, rowsOf, sized, symbol, type Align, type Block, type Box, type List, type MathsProps, type Ruling, type Valign } from "../sheet";
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
  // Starts or ends crop mode; absent unless one picture that is not locked is selected.
  crop?: () => void;
  cropping: boolean;
  // The width and height in mm of the page in use.
  size: number[];
};

const ALIGNS: [Align, string, LucideIcon][] = [["left", "Links", TextAlignStart], ["center", "Mitte", TextAlignCenter], ["right", "Rechts", TextAlignEnd]];
const LISTS: [List, string, LucideIcon][] = [["bullet", "Aufzählung", Bullets], ["number", "Nummerierung", ListOrdered]];
const VALIGNS: [Valign, string, LucideIcon][] = [["top", "Oben", AlignVerticalJustifyStart], ["middle", "Mitte", AlignVerticalJustifyCenter], ["bottom", "Unten", AlignVerticalJustifyEnd]];
const round = (n: number) => Math.round(n * 100) / 100;

export default function Format({ sel, style, look, paint, itemize, part, place, crop, cropping, size: [W, H] }: Props) {
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
  // More or fewer rows and columns, for one table: each has cells of its own.
  const grid = (rows: number, cols: number) => {
    const to = sized(tables[0], Math.max(1, rows), Math.max(1, cols));
    style("table", to.props, "table");
    place([[to.id, { h: to.h }]], "table");
  };
  const number = (to?: string) => place(sel.map((b) => [b.id, { mark: to }]));

  return (
    <>
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
              <button key={prop} className={`${prop}${shown[prop] ? " on" : ""}`} aria-label={label} aria-pressed={!!shown[prop]} onClick={() => paint({ [prop]: !shown[prop] })}>
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
          {tables.length === 1 &&
            (["Zeile", "Spalte"] as const).map((name, i) => {
              const n = [tables[0].props.cells.length, tables[0].props.cols.length];
              const by = (d: number) => grid(n[0] + (i ? 0 : d), n[1] + (i ? d : 0));
              return (
                <div key={name} className="seg">
                  <button aria-label={`Eine ${name} weniger`} onClick={() => by(-1)}>−</button>
                  <output>{n[i]} {name}n</output>
                  <button aria-label={`Eine ${name} mehr`} onClick={() => by(1)}>＋</button>
                </div>
              );
            })}
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
      <h2>Nummerierung</h2>
      <Numbering value={mark} onChange={number} symbol={() => number("2B50")} />
      {mark && !counts(mark) && <Symbols value={mark} onPick={number} />}
    </>
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
