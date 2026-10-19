// The format panel's settings for a Pfeilbild block: its pictures, columns, boxes, Zahlenraum and Rechenarten, its arrows, the given parts and the numbers typed in.
import { useRef, useState } from "react";
import type { PfeilbildBlock } from "../sheet";
import { draw } from "../bank";
import { fitColumns, made, sane, type PfeilbildProps } from "../pfeilbild";

type Op = PfeilbildProps["ops"][number];

const ZAHLENRAUM = [10, 20, 100, 1000];
const ORDER: Op[] = ["+", "-", "*", ":"];
const RECHENART = [
  ["+", "Plus"],
  ["-", "Minus"],
  ["*", "Mal"],
  [":", "Geteilt"],
] as const;
const PFEILE = { one: "In eine Richtung", both: "In beide Richtungen" } as const;
const GEGEBEN = { start: "Startzahl und Operatoren", ends: "Start und Ziel, Operatoren fehlen", mixed: "Gemischt" } as const;

// The boxes a picture has, for the width of the block: "random" counts as 8.
const cells = (boxes: PfeilbildProps["boxes"]) => (boxes === "random" ? 8 : boxes);

export default function Pfeilbild({ block, apply }: { block: PfeilbildBlock; apply: (props: Partial<PfeilbildProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, m.pictures.length - 1);

  function toggleOp(op: Op, on: boolean) {
    apply({ ops: ORDER.filter((o) => (o === op ? on : p.ops.includes(o))) });
  }

  function setTyped(box: number, text: string) {
    // The stored entries as they are, so that the pictures beyond `count` keep their numbers.
    const raw = block.props.typed;
    const others = (Array.isArray(raw) ? raw : []).filter((t) => Array.isArray(t) && (t[0] !== c || t[1] !== box));
    const key = `typed:${c}:${box}`;
    if (text === "") return apply({ typed: others.length ? others : undefined }, key);
    apply({ typed: [...others, [c, box, Number(text)]] }, key);
  }

  return (
    <>
      <h2>Pfeilbild</h2>
      <label>
        Kästchen
        <select
          aria-label="Kästchen"
          value={p.boxes}
          onChange={(e) => {
            const boxes = e.target.value === "random" ? "random" : Number(e.target.value);
            // More boxes make each picture wider: fewer Spalten keep the boxes at their size, and the block grows down instead.
            const columns = cells(boxes) > cells(p.boxes) ? fitColumns(p, cells(boxes), block.w) : p.columns;
            apply({ boxes, ...(columns !== p.columns ? { columns } : {}) });
          }}
        >
          {[3, 4, 5, 6, 7, 8].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
          <option value="random">Zufällig</option>
        </select>
      </label>
      <div className="seg">
        <button aria-label="Ein Pfeilbild weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 })}>
          −
        </button>
        <output>{p.count === 1 ? "1 Pfeilbild" : `${p.count} Pfeilbilder`}</output>
        <button aria-label="Ein Pfeilbild mehr" disabled={p.count === 12} onClick={() => apply({ count: p.count + 1 })}>
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
      <label>
        Zahlenraum
        <select
          aria-label="Zahlenraum"
          value={p.max}
          onChange={(e) => {
            const max = Number(e.target.value);
            // Under 20 there is no Mal and no Geteilt: they leave the list in the same step.
            const ops = max < 20 ? p.ops.filter((o) => o === "+" || o === "-") : p.ops;
            apply({ max, ops: ops.length ? ops : ["+"] });
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
              disabled={(op === "*" || op === ":") && p.max < 20 ? true : on && p.ops.length === 1}
              onChange={(e) => toggleOp(op, e.target.checked)}
            />
            {label}
          </label>
        );
      })}
      <label>
        Pfeile
        <select aria-label="Pfeile" value={p.arrows} onChange={(e) => apply({ arrows: e.target.value as PfeilbildProps["arrows"] })}>
          {Object.entries(PFEILE).map(([arrows, label]) => (
            <option key={arrows} value={arrows}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Gegeben
        <select aria-label="Gegeben" value={p.given} onChange={(e) => apply({ given: e.target.value as PfeilbildProps["given"] })}>
          {Object.entries(GEGEBEN).map(([given, label]) => (
            <option key={given} value={given}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="check">
        <input type="checkbox" checked={p.drawOps} onChange={(e) => apply({ drawOps: e.target.checked })} />
        Operatoren zeichnen
      </label>
      <label>
        Eigene Zahlen
        <select aria-label="Pfeilbild für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
          {m.pictures.map((_, i) => (
            <option key={i} value={i}>
              {`Pfeilbild ${i + 1}`}
            </option>
          ))}
        </select>
      </label>
      <div className="mauer">
        <div className="mauer-row">
          {m.pictures[c].numbers.map((n, r) => {
            const key = `${c},${r}`;
            return (
              <input
                key={r}
                className="typed"
                inputMode="numeric"
                aria-label={`Zahl in Kästchen ${r + 1}`}
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
      {m.pictures.map((pic, i) =>
        pic.wrong ? (
          <p key={i} className="hint" role="status">{`Pfeilbild ${i + 1}: die Zahlen passen nicht zu den Operatoren.`}</p>
        ) : null,
      )}
      {m.pictures.some((pic) => pic.over) && (
        <p className="hint" role="status">Pfeilbilder, die nicht in den Zahlenraum passen, werden nicht gezeigt. Nimm mehr Rechenarten oder einen größeren Zahlenraum.</p>
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).pictures) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
