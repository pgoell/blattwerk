// The format panel's settings for a Rechendreieck block: its triangles, its numbers and which fields are given.
import type { RechendreieckBlock } from "../sheet";
import { draw } from "../bank";
import { fixes, made, NAMES, sane, ZAHLENRAUM, type RechendreieckProps } from "../rechendreieck";
import { Switch } from "../components/Switch";
import { Pane } from "./format/pane";

const GIVEN = { inner: "Innen (leicht)", mix: "Gemischt (mittel)", outer: "Außen (schwer)", free: "Freie Wahl" } as const;
// The fields as the drawing has them: the inner ones at the corners, the outer ones beside the sides.
const SHAPE = [
  [null, 0, null],
  [3, null, 5],
  [1, 4, 2],
];

export default function Rechendreieck({ block, apply }: { block: RechendreieckBlock; apply: (props: Partial<RechendreieckProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);


  return (
    <>
      <h2>Rechendreieck</h2>
      <div className="seg">
        <button aria-label="Ein Dreieck weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 })}>
          −
        </button>
        <output>{p.count === 1 ? "1 Dreieck" : `${p.count} Dreiecke`}</output>
        <button aria-label="Ein Dreieck mehr" disabled={p.count === 12} onClick={() => apply({ count: p.count + 1 })}>
          ＋
        </button>
      </div>
      <Pane tab="Aussehen">
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.columns === 1} onClick={() => apply({ columns: p.columns - 1 })}>
          −
        </button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" disabled={p.columns === 4} onClick={() => apply({ columns: p.columns + 1 })}>
          ＋
        </button>
      </div>
      </Pane>
      <select aria-label="Zahlenraum" value={p.max} onChange={(e) => apply({ max: Number(e.target.value) })}>
        {ZAHLENRAUM.map((n) => (
          <option key={n} value={n}>
            {`bis ${n}`}
          </option>
        ))}
      </select>
      <div className="seg">
        <button className={p.op === "+" ? "on" : ""} aria-pressed={p.op === "+"} onClick={() => apply({ op: "+" })}>
          Plus
        </button>
        <button className={p.op === "*" ? "on" : ""} aria-pressed={p.op === "*"} onClick={() => apply({ op: "*" })}>
          Mal
        </button>
      </div>
      <select aria-label="Gegebene Felder" value={p.given} onChange={(e) => apply({ given: e.target.value as RechendreieckProps["given"] })}>
        {Object.entries(GIVEN).map(([given, label]) => (
          <option key={given} value={given}>
            {label}
          </option>
        ))}
      </select>
      {p.given === "free" && (
        <>
          <div className="dreieck">
            {SHAPE.map((row, r) => (
              <div key={r} className="dreieck-row">
                {row.map((i, c) =>
                  i === null ? (
                    <span key={c} />
                  ) : (
                    <button
                      key={c}
                      className={p.free?.[i] ? "on" : ""}
                      aria-label={`Feld ${NAMES[i]}`}
                      aria-pressed={p.free?.[i]}
                      onClick={() => apply({ free: (p.free ?? []).map((v, j) => (j === i ? !v : v)) })}
                    />
                  ),
                )}
              </div>
            ))}
          </div>
          {!fixes(p.free ?? []) && <p className="hint" role="status">Die gegebenen Felder legen das Dreieck nicht fest.</p>}
        </>
      )}
      <Switch label="Leer" on={p.empty} onChange={() => apply({ empty: !p.empty })} />
      <p className="hint">Eigene Zahlen tippst du ins Blatt: Doppelklick auf ein Feld, Tab geht zum nächsten.</p>
      {m.triangles.map((t, i) =>
        t.wrong ? (
          <p key={i} className="hint" role="status">{`Dreieck ${i + 1} geht mit diesen Zahlen nicht auf.`}</p>
        ) : t.numbers.some((v) => v > p.max) ? (
          <p key={i} className="hint" role="status">{`Dreieck ${i + 1} geht über den Zahlenraum bis ${p.max} hinaus.`}</p>
        ) : null,
      )}
      {p.typed && (
        <button
          onClick={() => {
            apply({ typed: undefined });
          }}
        >
          Eigene Zahlen entfernen
        </button>
      )}
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).triangles) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
