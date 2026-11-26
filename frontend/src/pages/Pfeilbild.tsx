// The format panel's settings for a Pfeilbild block: its pictures, columns, boxes, Zahlenraum and Rechenarten, its arrows, the given parts and the numbers typed in.
import type { PfeilbildBlock } from "../sheet";
import { draw } from "../bank";
import { fitColumns, made, sane, type PfeilbildProps } from "../pfeilbild";
import { Switch } from "../components/Switch";
import { Pane } from "./format/pane";

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


  function toggleOp(op: Op, on: boolean) {
    apply({ ops: ORDER.filter((o) => (o === op ? on : p.ops.includes(o))) });
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
          <Switch key={op} label={label} on={on} disabled={(op === "*" || op === ":") && p.max < 20 ? true : on && p.ops.length === 1} onChange={(to) => toggleOp(op, to)} />
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
      <Switch label="Operatoren zeichnen" on={p.drawOps} onChange={(drawOps) => apply({ drawOps })} />
      <p className="hint">Eigene Zahlen tippst du ins Blatt: Doppelklick auf ein Feld, Tab geht zum nächsten.</p>
      {m.pictures.map((pic, i) =>
        pic.wrong ? (
          <p key={i} className="hint" role="status">
            {p.typed?.some((t) => t[0] === i)
              ? `Pfeilbild ${i + 1}: die Zahlen passen nicht zu den Operatoren.`
              : `Pfeilbild ${i + 1}: die Operatoren passen nicht in den Zahlenraum.`}
          </p>
        ) : null,
      )}
      {m.pictures.some((pic) => pic.over) && (
        <p className="hint" role="status">Pfeilbilder, die nicht in den Zahlenraum passen, werden nicht gezeigt. Nimm mehr Rechenarten oder einen größeren Zahlenraum.</p>
      )}
      {(p.typed || p.typedOps) && (
        <button
          onClick={() => {
            apply({ typed: undefined, typedOps: undefined });
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
