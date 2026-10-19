// The format panel's settings for a Rechenrad block: its Rechenräder, rings, segments, Zahlenraum, Rechenart, Aufgabe and the numbers typed in.
import { useRef, useState } from "react";
import type { RechenradBlock } from "../sheet";
import { draw } from "../bank";
import { made, sane, type Op, type RechenradProps, type RechenradTyped } from "../rechenrad";

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
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, m.wheels.length - 1);
  const wheel = m.wheels[c];

  function setTyped(ring: number, segment: number, text: string) {
    // The stored entries as they are, so that the other boxes and wheels keep their numbers.
    const raw = block.props.typed;
    const others = (Array.isArray(raw) ? raw : []).filter((t) => Array.isArray(t) && (t[0] !== c || t[1] !== ring || t[2] !== segment));
    const key = `typed:${c}:${ring}:${segment}`;
    if (text === "") return apply({ typed: others.length ? others : undefined }, key);
    apply({ typed: [...others, [c, ring, segment, Number(text)] as RechenradTyped] }, key);
  }

  // A number field for the box of ring `ring` (0 is the centre) and segment `segment`.
  function numberField(ring: number, segment: number, n: number, label: string) {
    const key = `${c},${ring},${segment}`;
    return (
      <input
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
          setTyped(ring, segment, e.target.value);
        }}
      />
    );
  }

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
      <label>
        Eigene Zahlen
        <select aria-label="Rechenrad für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
          {m.wheels.map((_, i) => (
            <option key={i} value={i}>
              {`Rechenrad ${i + 1}`}
            </option>
          ))}
        </select>
      </label>
      <div className="mauer">
        <div className="mauer-row">{numberField(0, 0, wheel?.centre ?? 0, "Zahl im Zentrum")}</div>
        {wheel?.rings.map((ring, ri) => (
          <div className="mauer-row" key={ri}>
            {ring.map((n, s) => numberField(ri + 1, s, n, `Ring ${ri + 1}, Feld ${s + 1}`))}
          </div>
        ))}
      </div>
      {m.wheels.map((w, i) =>
        w.wrong ? (
          <p key={i} className="hint" role="status">{`Rechenrad ${i + 1}: Die Zahlen passen nicht zum Zentrum.`}</p>
        ) : null,
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).wheels) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
