// The format panel's settings for an Operatorfeld block: its fields, Variante, boxes, Zahlenraum, Rechenarten, Einschränkung, the given parts and the numbers typed in.
import type { OperatorfeldBlock } from "../sheet";
import { draw } from "../bank";
import { made, sane, type OperatorfeldProps } from "../operatorfeld";
import { Switch } from "../components/Switch";
import { Pane } from "./format/pane";

type Op = OperatorfeldProps["ops"][number];

const ZAHLENRAUM = [10, 20, 100, 1000];
const ORDER: Op[] = ["+", "-", "*", ":"];
const RECHENART = [
  ["+", "Plus"],
  ["-", "Minus"],
  ["*", "Mal"],
  [":", "Geteilt"],
] as const;

export default function Operatorfeld({ block, apply }: { block: OperatorfeldBlock; apply: (props: Partial<OperatorfeldProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);


  function toggleOp(op: Op, on: boolean) {
    apply({ ops: ORDER.filter((o) => (o === op ? on : p.ops.includes(o))) });
  }

  return (
    <>
      <h2>Operatorfeld</h2>
      <label>
        Variante
        <select
          aria-label="Variante"
          value={String(p.centre)}
          onChange={(e) => {
            const centre = e.target.value === "true";
            // With a centre only Plus and Minus stay: the other Rechenarten leave the list in the same step.
            const ops = centre ? p.ops.filter((o) => o === "+" || o === "-") : p.ops;
            apply({ centre, ops: ops.length ? ops : ["+"], typed: undefined });
          }}
        >
          <option value="false">Ohne Zentrum</option>
          <option value="true">Mit Zentrum</option>
        </select>
      </label>
      <div className="seg">
        <button aria-label="Ein Operatorfeld weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 })}>
          −
        </button>
        <output>{p.count === 1 ? "1 Operatorfeld" : `${p.count} Operatorfelder`}</output>
        <button aria-label="Ein Operatorfeld mehr" disabled={p.count === 6} onClick={() => apply({ count: p.count + 1 })}>
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
        <button aria-label="Ein Kästchen weniger" disabled={p.boxes === 3} onClick={() => apply({ boxes: p.boxes - 1 })}>
          −
        </button>
        <output>{`${p.boxes} Kästchen`}</output>
        <button aria-label="Ein Kästchen mehr" disabled={p.boxes === 8} onClick={() => apply({ boxes: p.boxes + 1 })}>
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
            // Under 20 there is no Mal and no Geteilt, and under 100 or 1000 no Einschränkung that the new max is too small for: they leave in the same step.
            const ops = max < 20 ? p.ops.filter((o) => o === "+" || o === "-") : p.ops;
            const only = (p.only === "tens" && max < 100) || (p.only === "hundreds" && max < 1000) ? "none" : p.only;
            apply({ max, ops: ops.length ? ops : ["+"], only });
          }}
        >
          {ZAHLENRAUM.map((n) => (
            <option key={n} value={n}>
              {`bis ${n}`}
            </option>
          ))}
        </select>
      </label>
      {RECHENART.map(([op, label]) => {
        const on = p.ops.includes(op);
        return (
          <Switch key={op} label={label} on={on} disabled={(op === "*" || op === ":") && (p.centre || p.max < 20) ? true : on && p.ops.length === 1} onChange={(to) => toggleOp(op, to)} />
        );
      })}
      <label>
        Einschränkung
        <select aria-label="Einschränkung" value={p.only} onChange={(e) => apply({ only: e.target.value as OperatorfeldProps["only"] })}>
          <option value="none">Keine</option>
          <option value="tens" disabled={p.max < 100}>
            Nur Zehnerzahlen
          </option>
          <option value="hundreds" disabled={p.max < 1000}>
            Nur Hunderterzahlen
          </option>
        </select>
      </label>
      <label>
        Gegeben
        <select aria-label="Gegeben" value={p.given} onChange={(e) => apply({ given: e.target.value as OperatorfeldProps["given"] })}>
          <option value="start">{p.centre ? "Zentrum und Operatoren" : "Startzahl und Operatoren"}</option>
          <option value="ops">Alle Zahlen, Operatoren fehlen</option>
          <option value="mixed">Gemischt</option>
        </select>
      </label>
      <Switch label="Operatoren zeichnen" on={p.drawOps} onChange={(drawOps) => apply({ drawOps })} />
      <p className="hint">Eigene Zahlen tippst du ins Blatt: Doppelklick auf ein Feld, Tab geht zum nächsten.</p>
      {m.fields.map((f, i) =>
        f.wrong ? (
          <p key={i} className="hint" role="status">{`Operatorfeld ${i + 1}: kein Operator passt zu diesen Zahlen.`}</p>
        ) : null,
      )}
      {m.fields.some((f) => f.over) && (
        <p className="hint" role="status">Operatorfelder, die nicht in den Zahlenraum passen, werden nicht gezeigt. Nimm mehr Rechenarten oder einen größeren Zahlenraum.</p>
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).fields) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
