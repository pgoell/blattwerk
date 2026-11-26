// The format panel's settings for a Malquadrat block: its squares, their size, Rechenart, Reihen or Zahlenraum, Aufgabentyp
// and the numbers typed in.
import type { MalquadratBlock } from "../sheet";
import { draw } from "../bank";
import { made, sane, type MalquadratProps } from "../malquadrat";
import { Reihen } from "./Reihen";

const plural = (n: number, one: string, many: string) => (n === 1 ? `1 ${one}` : `${n} ${many}`);

function stepper(less: string, more: string, text: string, n: number, lo: number, hi: number, down: () => void, up: () => void) {
  return (
    <div className="seg">
      <button aria-label={less} disabled={n <= lo} onClick={down}>
        −
      </button>
      <output>{text}</output>
      <button aria-label={more} disabled={n >= hi} onClick={up}>
        ＋
      </button>
    </div>
  );
}

export default function Malquadrat({ block, apply }: { block: MalquadratBlock; apply: (props: Partial<MalquadratProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const n = p.size;



  return (
    <>
      <h2>Malquadrat</h2>
      {stepper(
        "Ein Malquadrat weniger",
        "Ein Malquadrat mehr",
        plural(p.count, "Malquadrat", "Malquadrate"),
        p.count,
        1,
        4,
        () => apply({ count: p.count - 1 }, "count"),
        () => apply({ count: p.count + 1 }, "count"),
      )}
      {stepper(
        "Weniger Malquadrate nebeneinander",
        "Mehr Malquadrate nebeneinander",
        `${p.columns} nebeneinander`,
        p.columns,
        1,
        3,
        () => apply({ columns: p.columns - 1 }, "columns"),
        () => apply({ columns: p.columns + 1 }, "columns"),
      )}
      {stepper(
        "Kleiner",
        "Größer",
        `${n} × ${n} Felder`,
        n,
        2,
        4,
        () => apply({ size: n - 1, typed: undefined }, "size"),
        () => apply({ size: n + 1, typed: undefined }, "size"),
      )}
      <label>
        Rechenart
        <select
          aria-label="Rechenart"
          value={p.op}
          onChange={(e) => apply({ op: e.target.value as "*" | "+", typed: undefined }, "op")}
        >
          <option value="*">Mal</option>
          <option value="+">Plus</option>
        </select>
      </label>
      {p.op === "*" ? (
        <Reihen reihen={p.reihen} lockLast onChange={(reihen) => apply({ reihen }, "reihen")} />
      ) : (
        <label>
          Zahlenraum
          <select aria-label="Zahlenraum" value={p.max} onChange={(e) => apply({ max: Number(e.target.value) }, "max")}>
            <option value={20}>bis 20</option>
            <option value={100}>bis 100</option>
            <option value={1000}>bis 1000</option>
          </select>
        </label>
      )}
      <label>
        Aufgabentyp
        <select
          aria-label="Aufgabentyp"
          value={p.task}
          onChange={(e) => apply({ task: e.target.value as MalquadratProps["task"] }, "task")}
        >
          <option value="factors">Nur die Zahlen am Rand</option>
          <option value="mixed">Rand und Innen gemischt</option>
          <option value="knobel">Knobelaufgabe über die Summen</option>
        </select>
      </label>
      <p className="hint">Eigene Zahlen tippst du ins Blatt: Doppelklick auf ein Feld, Tab geht zum nächsten.</p>
      {m.squares.map((s, k) => {
        if (s.unsure) return null;
        if (s.wrong) return <p key={k} className="hint" role="status">{`Malquadrat ${k + 1}: Die Zahlen passen nicht zusammen.`}</p>;
        if (s.many) return <p key={k} className="hint" role="status">{`Malquadrat ${k + 1}: Es gibt mehr als eine Lösung.`}</p>;
        return null;
      })}
      {p.typed && (
        <button
          onClick={() => {
            apply({ typed: undefined }, "clear");
          }}
        >
          Eigene Zahlen entfernen
        </button>
      )}
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).squares) }]) }, "seed")}>
        Neu würfeln
      </button>
    </>
  );
}
