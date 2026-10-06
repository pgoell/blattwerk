// The format panel's settings for the school blocks, and the numbering any block can have.
import { useState } from "react";
import { FONTS, MARKS, RULINGS, rowsOf, symbol, type Align, type Block, type Box, type Ruling } from "../sheet";
import { SYMBOLS } from "../symbols";

type Props = {
  sel: Block[];
  // Sets props on every selected block of one type.
  style: (type: Block["type"], props: object, key?: string) => void;
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
};

const ALIGNS: [Align, string][] = [["left", "Links"], ["center", "Mitte"], ["right", "Rechts"]];
const SIDES = ["Links", "Oben", "Rechts", "Unten"];
const round = (n: number) => Math.round(n * 100) / 100;

export default function Format({ sel, style, place }: Props) {
  const of = <T extends Block["type"]>(type: T) => sel.filter((b): b is Extract<Block, { type: T }> => b.type === type);
  // The first block of a type shows its settings; a change goes to all of them.
  const [text] = of("text");
  const rulings = of("ruling");
  const [points] = of("points");
  const [sign] = of("symbol");
  const images = of("image");
  const { mark } = sel[0];

  // A ruling keeps its rows when its type changes, so the block's height follows.
  const rule = (kind: Ruling, rows?: number) => {
    style("ruling", { kind }, "ruling");
    place(rulings.map((b) => [b.id, { h: round(Math.max(1, rows ?? rowsOf(b)) * RULINGS[kind].row) }]), "ruling");
  };
  // A cut leaves the rest of the picture where and as large as it was: the block shrinks or grows around it.
  const cut = (side: number, share: number) => {
    const to = images[0].props.cut.map((old, i) => (i === side ? share : old));
    style("image", { cut: to }, "cut");
    place(
      images.map((b) => {
        const old = b.props.cut;
        const full = b.w / (1 - old[0] - old[2]);
        const tall = full / b.props.ratio;
        const box = { x: b.x + full * (to[0] - old[0]), y: b.y + tall * (to[1] - old[1]), w: full * (1 - to[0] - to[2]), h: tall * (1 - to[1] - to[3]) };
        return [b.id, { x: round(box.x), y: round(box.y), w: round(box.w), h: round(box.h) }];
      }),
      "cut",
    );
  };
  const number = (to?: string) => place(sel.map((b) => [b.id, { mark: to }]));

  return (
    <>
      {text && (
        <>
          <h2>Schrift</h2>
          <select aria-label="Schriftart" value={text.props.font ?? "andika"} onChange={(e) => style("text", { font: e.target.value })}>
            {Object.entries(FONTS).map(([font, [name]]) => (
              <option key={font} value={font}>
                {name}
              </option>
            ))}
          </select>
          <div className="row">
            <button aria-label="Schrift kleiner" onClick={() => style("text", { size: Math.max(8, text.props.size - 2) })}>−</button>
            <output>{text.props.size} pt</output>
            <button aria-label="Schrift größer" onClick={() => style("text", { size: text.props.size + 2 })}>＋</button>
            {([["bold", "Fett"], ["italic", "Kursiv"], ["underline", "Unterstrichen"]] as const).map(([prop, label]) => (
              <button key={prop} className={`${prop}${text.props[prop] ? " on" : ""}`} aria-label={label} aria-pressed={!!text.props[prop]} onClick={() => style("text", { [prop]: !text.props[prop] })}>
                {label[0]}
              </button>
            ))}
            {ALIGNS.map(([value, label]) => (
              <button key={value} className={text.props.align === value ? "on" : ""} onClick={() => style("text", { align: value })}>
                {label}
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={text.props.color ?? "#222222"} onChange={(e) => style("text", { color: e.target.value }, "color")} />
          </label>
          <label>
            Zeilenabstand
            <input type="range" min={1} max={3} step={0.1} value={text.props.spacing ?? 1.3} onChange={(e) => style("text", { spacing: +e.target.value }, "spacing")} />
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
          <div className="row">
            <button aria-label="Eine Zeile weniger" onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) - 1)}>−</button>
            <output>{rowsOf(rulings[0])} Zeilen</output>
            <button aria-label="Eine Zeile mehr" onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) + 1)}>＋</button>
          </div>
          <label>
            Farbe
            <input type="color" value={rulings[0].props.color} onChange={(e) => style("ruling", { color: e.target.value }, "color")} />
          </label>
        </>
      )}
      {points && (
        <>
          <h2>Punkte</h2>
          <div className="row">
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
      {images.length > 0 && (
        <>
          <h2>Zuschneiden</h2>
          {SIDES.map((side, i) => (
            <label key={side}>
              {side}
              <input type="range" min={0} max={0.45} step={0.01} value={images[0].props.cut[i]} onChange={(e) => cut(i, +e.target.value)} />
            </label>
          ))}
        </>
      )}
      <h2>Nummerierung</h2>
      <div className="row">
        <button className={mark ? "" : "on"} onClick={() => number()}>Keine</button>
        {Object.keys(MARKS).map((m) => (
          <button key={m} className={mark === m ? "on" : ""} onClick={() => number(m)}>
            {m}
          </button>
        ))}
        <button className={mark && !MARKS[mark] ? "on" : ""} onClick={() => number("2B50")}>Symbol</button>
      </div>
      {mark && !MARKS[mark] && <Symbols value={mark} onPick={number} />}
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
