// The format panel's settings for an Operatorfeld block: its fields, Variante, boxes, Zahlenraum, Rechenarten, Einschränkung, the given parts and the numbers typed in.
import { useRef, useState } from "react";
import type { OperatorfeldBlock } from "../sheet";
import { draw } from "../bank";
import { made, sane, type OperatorfeldProps } from "../operatorfeld";

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
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, m.fields.length - 1);
  const field = m.fields[c];

  function toggleOp(op: Op, on: boolean) {
    apply({ ops: ORDER.filter((o) => (o === op ? on : p.ops.includes(o))) });
  }

  function setTyped(box: number, text: string) {
    // The stored entries as they are, so that the fields beyond `count` keep their numbers.
    const raw = block.props.typed;
    const others = (Array.isArray(raw) ? raw : []).filter((t) => Array.isArray(t) && (t[0] !== c || t[1] !== box));
    const key = `typed:${c}:${box}`;
    if (text === "") return apply({ typed: others.length ? others : undefined }, key);
    apply({ typed: [...others, [c, box, Number(text)]] }, key);
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
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.columns === 1} onClick={() => apply({ columns: p.columns - 1 })}>
          −
        </button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" disabled={p.columns === 3} onClick={() => apply({ columns: p.columns + 1 })}>
          ＋
        </button>
      </div>
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
          <label key={op} className="check">
            <input
              type="checkbox"
              checked={on}
              disabled={(op === "*" || op === ":") && (p.centre || p.max < 20) ? true : on && p.ops.length === 1}
              onChange={(e) => toggleOp(op, e.target.checked)}
            />
            {label}
          </label>
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
      <label className="check">
        <input type="checkbox" checked={p.drawOps} onChange={(e) => apply({ drawOps: e.target.checked })} />
        Operatoren zeichnen
      </label>
      <label>
        Eigene Zahlen
        <select aria-label="Operatorfeld für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
          {m.fields.map((_, i) => (
            <option key={i} value={i}>
              {`Operatorfeld ${i + 1}`}
            </option>
          ))}
        </select>
      </label>
      <div className="mauer">
        <div className="mauer-row">
          {field?.numbers.map((n, r) => {
            const key = `${c},${r}`;
            // With a centre box 0 is the Zentrum, and the outer boxes count from 1.
            const label = p.centre ? (r === 0 ? "Zahl im Zentrum" : `Zahl in Kästchen ${r}`) : `Zahl in Kästchen ${r + 1}`;
            return (
              <input
                key={r}
                className="typed"
                inputMode="numeric"
                aria-label={label}
                value={draft?.key === key ? draft.text : String(n)}
                onFocus={() => {
                  fresh.current = true;
                  setDraft({ key, text: String(n) });
                }}
                // The click that focuses the field also places the caret; this mouseup selects the whole number instead.
                onMouseUp={(e) => {
                  if (!fresh.current) return;
                  fresh.current = false;
                  e.preventDefault();
                  e.currentTarget.select();
                }}
                onBlur={() => setDraft(null)}
                onKeyDown={(e) => {
                  // Ctrl+Z and Ctrl+Y are the sheet's here: the field then shows the number that the undo or redo gives.
                  if ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key)) setDraft(null);
                }}
                onChange={(e) => {
                  if (!/^\d{0,4}$/.test(e.target.value)) return;
                  setDraft({ key, text: e.target.value });
                  setTyped(r, e.target.value);
                }}
              />
            );
          })}
        </div>
      </div>
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
            setDraft(null);
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
