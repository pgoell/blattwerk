// The format panel's settings for a Rechenrad block: its Rechenräder, rings, segments, Zahlenraum, Rechenart, Aufgabe and the numbers typed in.
import type { RechenradBlock } from "../sheet";
import { draw } from "../bank";
import { made, sane, type Op, type RechenradProps } from "../rechenrad";
import { Pane } from "./format/pane";

const ZAHLENRAUM = [10, 20, 100, 1000];
const RECHENART = [
  ["+", "Plus"],
  ["-", "Minus"],
  ["*", "Mal"],
  [":", "Geteilt"],
] as const;

export default function Rechenrad({ block, apply }: { block: RechenradBlock; apply: (props: Partial<RechenradProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);


  return (
    <>
      <h2>Rechenrad</h2>
      <div className="seg">
        <button aria-label="Ein Rechenrad weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 })}>
          −
        </button>
        <output>{p.count === 1 ? "1 Rechenrad" : `${p.count} Rechenräder`}</output>
        <button aria-label="Ein Rechenrad mehr" disabled={p.count === 6} onClick={() => apply({ count: p.count + 1 })}>
          ＋
        </button>
      </div>
      <Pane tab="Aussehen">
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.columns === 1} onClick={() => apply({ columns: p.columns - 1 })}>
          −
        </button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" disabled={p.columns === 3} onClick={() => apply({ columns: p.columns + 1 })}>
          ＋
        </button>
      </div>
      </Pane>
      <div className="seg">
        <button aria-label="Ein Ring weniger" disabled={p.rings === 2} onClick={() => apply(p.task === "middle" ? { rings: 2, task: "outer" } : { rings: 2 })}>
          −
        </button>
        <output>{`${p.rings} Ringe`}</output>
        <button aria-label="Ein Ring mehr" disabled={p.rings === 3} onClick={() => apply({ rings: 3 })}>
          ＋
        </button>
      </div>
      <div className="seg">
        <button aria-label="Ein Segment weniger" disabled={p.segments === 4} onClick={() => apply({ segments: p.segments - 1 })}>
          −
        </button>
        <output>{`${p.segments} Segmente`}</output>
        <button aria-label="Ein Segment mehr" disabled={p.segments === 12} onClick={() => apply({ segments: p.segments + 1 })}>
          ＋
        </button>
      </div>
      <label>
        Zahlenraum
        <select
          aria-label="Zahlenraum"
          value={p.max}
          onChange={(e) => {
            const max = Number(e.target.value);
            // Under 20 there is no Mal and no Geteilt: the operator falls back to Plus in the same step.
            apply(max < 20 && (p.op === "*" || p.op === ":") ? { max, op: "+" } : { max });
          }}
        >
          {ZAHLENRAUM.map((n) => (
            <option key={n} value={n}>
              {`bis ${n}`}
            </option>
          ))}
        </select>
      </label>
      <label>
        Rechenart
        <select aria-label="Rechenart" value={p.op} onChange={(e) => apply({ op: e.target.value as Op })}>
          {RECHENART.map(([op, label]) => (
            <option key={op} value={op} disabled={(op === "*" || op === ":") && p.max < 20}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Aufgabe
        <select aria-label="Aufgabe" value={p.task} onChange={(e) => apply({ task: e.target.value as RechenradProps["task"] })}>
          <option value="outer">Äußerer Ring leer</option>
          <option value="inner">Innerer Ring leer</option>
          <option value="middle" disabled={p.rings === 2}>
            Mittlerer Ring leer
          </option>
          <option value="mixed">Gemischt: ein leeres Feld je Segment</option>
        </select>
      </label>
      <p className="hint">Eigene Zahlen tippst du ins Blatt: Doppelklick auf ein Feld, Tab geht zum nächsten.</p>
      {m.wheels.map((w, i) =>
        w.wrong ? (
          <p key={i} className="hint" role="status">{`Rechenrad ${i + 1}: Die Zahlen passen nicht zum Zentrum.`}</p>
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).wheels) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
