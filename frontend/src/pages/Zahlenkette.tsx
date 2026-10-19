// The format panel's settings for a Zahlenkette block: its chains and rings, its Zahlenraum and Rechenart, the step, which rings are given and the numbers typed in.
import { useRef, useState } from "react";
import type { ZahlenketteBlock } from "../sheet";
import { draw } from "../bank";
import { fitColumns, made, sane, startFlags, type ZahlenketteProps } from "../zahlenkette";

const ZAHLENRAUM = [10, 20, 100, 1000];
const RECHENART = { "+": "Plus", "-": "Minus", "*": "Mal" } as const;
const GIVEN = { start: "Anfang", ends: "Anfang und Ende", random: "Zufällig", free: "Freie Wahl" } as const;

// Why a typed step is not stored: plus and minus take 1 to 1000, Mal takes 2 to 10.
function stepWrong(text: string, op: string) {
  const n = Number(text);
  const [lo, hi] = op === "*" ? [2, 10] : [1, 1000];
  return n < lo ? `Mindestens ${lo}.` : n > hi ? `Höchstens ${hi}.` : "";
}

export default function Zahlenkette({ block, apply }: { block: ZahlenketteBlock; apply: (props: Partial<ZahlenketteProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const free = p.free ?? startFlags(p.rings);
  const [which, setWhich] = useState(0);
  // "Fest" chosen while no step is stored yet: the input shows until a step is stored.
  const [fixed, setFixed] = useState(false);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);
  // Set by Escape in the step field, until the blur that follows has passed.
  const dropped = useRef(false);

  const c = Math.min(which, m.chains.length - 1);
  const fixedShown = fixed || p.step !== undefined;

  function toggleFree(r: number) {
    apply({ free: free.map((v, j) => (j === r ? !v : v)) });
  }

  // The step applies on Enter and on leaving the field, when it is in range; else the field shows the step in use.
  function stepDone(text: string) {
    setDraft(null);
    if (stepWrong(text, p.op)) return;
    if (Number(text) !== p.step) apply({ step: Number(text) }, "step");
  }

  function setTyped(ring: number, text: string) {
    // The stored entries as they are, so that the chains beyond `count` keep their numbers.
    const raw = block.props.typed;
    const others = (Array.isArray(raw) ? raw : []).filter((t) => Array.isArray(t) && (t[0] !== c || t[1] !== ring));
    const key = `typed:${c}:${ring}`;
    if (text === "") return apply({ typed: others.length ? others : undefined }, key);
    apply({ typed: [...others, [c, ring, Number(text)]] }, key);
  }

  return (
    <>
      <h2>Zahlenkette</h2>
      {/* Each list says what it sets, as "4 Ketten" does. */}
      <label>
        Ringe
        <select aria-label="Ringe" value={p.rings} onChange={(e) => {
          const rings = Number(e.target.value);
          // More rings make each chain wider: fewer Spalten keep the rings at their size, and the block grows down instead.
          const columns = rings > p.rings ? fitColumns(p, rings, block.w) : p.columns;
          apply({ rings, free: Array.from({ length: rings }, (_, j) => free[j] ?? false), ...(columns !== p.columns ? { columns } : {}) });
        }}>
          {Array.from({ length: 9 }, (_, i) => i + 4).map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>
      <div className="seg">
        <button aria-label="Eine Kette weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 })}>
          −
        </button>
        <output>{p.count === 1 ? "1 Kette" : `${p.count} Ketten`}</output>
        <button aria-label="Eine Kette mehr" disabled={p.count === 12} onClick={() => apply({ count: p.count + 1 })}>
          ＋
        </button>
      </div>
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.columns === 1} onClick={() => apply({ columns: p.columns - 1 })}>
          −
        </button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" disabled={p.columns === 4} onClick={() => apply({ columns: p.columns + 1 })}>
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
            apply(max < 100 && p.op === "*" ? { max, op: "+" } : { max });
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
        <select
          aria-label="Rechenart"
          value={p.op}
          onChange={(e) => {
            const op = e.target.value as ZahlenketteProps["op"];
            apply(op === "*" || p.op === "*" ? { op, step: undefined } : { op });
          }}
        >
          {Object.entries(RECHENART).map(([op, label]) => (
            <option key={op} value={op} disabled={op === "*" && p.max < 100}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Schrittweite
        <select
          aria-label="Schrittweite"
          value={fixedShown ? "fixed" : "random"}
          onChange={(e) => {
            if (e.target.value === "fixed") return setFixed(true);
            setFixed(false);
            if (p.step !== undefined) apply({ step: undefined });
          }}
        >
          <option value="random">Zufällig</option>
          <option value="fixed">Fest</option>
        </select>
      </label>
      {fixedShown && (
        <input
          className="own"
          inputMode="numeric"
          aria-label="Schritt"
          value={draft?.key === "step" ? draft.text : String(p.step ?? "")}
          onFocus={() => {
            fresh.current = true;
            setDraft({ key: "step", text: String(p.step ?? "") });
          }}
          // The click that focuses the field also places the caret; this mouseup selects the whole number instead.
          onMouseUp={(e) => {
            if (!fresh.current) return;
            fresh.current = false;
            e.preventDefault();
            e.currentTarget.select();
          }}
          onBlur={(e) => (dropped.current ? (dropped.current = false) : stepDone(e.target.value))}
          onKeyDown={(e) => {
            if (e.key === "Enter") stepDone(e.currentTarget.value);
            // Escape drops what was typed: the blur that the editor gives with it stores nothing.
            if (e.key === "Escape") {
              dropped.current = true;
              setDraft(null);
            }
          }}
          onChange={(e) => {
            if (!/^\d{0,4}$/.test(e.target.value)) return;
            dropped.current = false;
            setDraft({ key: "step", text: e.target.value });
          }}
        />
      )}
      {fixedShown && draft?.key === "step" && stepWrong(draft.text, p.op) && (
        <p className="hint" role="status">{stepWrong(draft.text, p.op)}</p>
      )}
      <label className="check">
        <input type="checkbox" checked={p.showStep} onChange={(e) => apply({ showStep: e.target.checked })} />
        Schritt anschreiben
      </label>
      <label>
        Gegebene Ringe
        <select aria-label="Gegebene Ringe" value={p.given} onChange={(e) => apply({ given: e.target.value as ZahlenketteProps["given"] })}>
          {Object.entries(GIVEN).map(([given, label]) => (
            <option key={given} value={given}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {p.given === "free" && (
        <div className="mauer">
          <div className="mauer-row">
            {free.map((on, r) => (
              <button key={r} className={on ? "on" : ""} aria-label={`Ring ${r + 1}`} aria-pressed={on} onClick={() => toggleFree(r)} />
            ))}
          </div>
        </div>
      )}
      <label>
        Eigene Zahlen
        <select aria-label="Kette für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
          {m.chains.map((_, i) => (
            <option key={i} value={i}>
              {`Kette ${i + 1}`}
            </option>
          ))}
        </select>
      </label>
      <div className="mauer">
        <div className="mauer-row">
          {m.chains[c].numbers.map((n, r) => {
            const key = `${c},${r}`;
            return (
              <input
                key={r}
                className="typed"
                inputMode="numeric"
                aria-label={`Zahl in Ring ${r + 1}`}
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
      {m.chains.map((ch, i) =>
        ch.wrong ? (
          <p key={i} className="hint" role="status">{`Kette ${i + 1}: die Zahlen passen nicht zum Schritt.`}</p>
        ) : null,
      )}
      {m.chains.some((ch) => ch.over) && (
        <p className="hint" role="status">Ketten, die nicht in den Zahlenraum passen, werden nicht gezeigt. Nimm weniger Ringe, einen kleineren Schritt oder einen größeren Zahlenraum.</p>
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).chains) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
