// The format panel's settings for the school blocks, and the numbering any block can have.
import { useState } from "react";
import { AlignVerticalJustifyCenter, AlignVerticalJustifyEnd, AlignVerticalJustifyStart, TextAlignCenter, TextAlignEnd, TextAlignStart, type LucideIcon } from "lucide-react";
import Numbering from "../components/Numbering";
import { FONTS, H, MARGIN, RULINGS, W, boxed, counts, mathsHeight, rowsOf, symbol, type Align, type Block, type Box, type MathsProps, type Ruling, type Valign } from "../sheet";
import Maths from "./Maths";
import { SYMBOLS } from "../symbols";

type Props = {
  sel: Block[];
  // Sets props on every selected block of one type.
  style: (type: Block["type"], props: object, key?: string) => void;
  // Sets what a text and a shape share on every selected one of them.
  look: (props: object, key?: string) => void;
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
  // Starts or ends crop mode; absent unless one picture that is not locked is selected.
  crop?: () => void;
  cropping: boolean;
};

const ALIGNS: [Align, string, LucideIcon][] = [["left", "Links", TextAlignStart], ["center", "Mitte", TextAlignCenter], ["right", "Rechts", TextAlignEnd]];
const VALIGNS: [Valign, string, LucideIcon][] = [["top", "Oben", AlignVerticalJustifyStart], ["middle", "Mitte", AlignVerticalJustifyCenter], ["bottom", "Unten", AlignVerticalJustifyEnd]];
const round = (n: number) => Math.round(n * 100) / 100;

export default function Format({ sel, style, look, place, crop, cropping }: Props) {
  const of = <T extends Block["type"]>(type: T) => sel.filter((b): b is Extract<Block, { type: T }> => b.type === type);
  // The first block of a type shows its settings; a change goes to all of them.
  // A shape that is no line holds text as a text block does.
  const text = sel.map(boxed).find((p) => p);
  const rulings = of("ruling");
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
          <div className="seg">
            {([["bold", "Fett"], ["italic", "Kursiv"], ["underline", "Unterstrichen"]] as const).map(([prop, label]) => (
              <button key={prop} className={`${prop}${text[prop] ? " on" : ""}`} aria-label={label} aria-pressed={!!text[prop]} onClick={() => look({ [prop]: !text[prop] })}>
                {label[0]}
              </button>
            ))}
          </div>
          <div className="seg">
            {ALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={text.align === value ? "on" : ""} aria-label={label} title={label} aria-pressed={text.align === value} onClick={() => look({ align: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg">
            {VALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={(text.valign ?? "top") === value ? "on" : ""} aria-label={label} title={label} aria-pressed={(text.valign ?? "top") === value} onClick={() => look({ valign: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={text.color ?? "#222222"} onChange={(e) => look({ color: e.target.value }, "color")} />
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
