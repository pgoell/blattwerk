// The format panel's settings for a Zerlegungsfeld block: its tasks, their columns, Rechenart, Zahlenraum, Übergang,
// Aufgabentyp and the numbers typed in.
import type { ZerlegungsfeldBlock } from "../sheet";
import { draw } from "../bank";
import { made, sane, type ZerlegungsfeldProps } from "../zerlegungsfeld";
import { clean } from "../zerlegungsfeld/pattern";
import { Switch } from "../components/Switch";

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

export default function Zerlegungsfeld({ block, apply }: { block: ZerlegungsfeldBlock; apply: (props: Partial<ZerlegungsfeldProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);


  return (
    <>
      <h2>Zerlegungsfeld</h2>
      {stepper(
        "Eine Aufgabe weniger",
        "Eine Aufgabe mehr",
        plural(p.count, "Aufgabe", "Aufgaben"),
        p.count,
        1,
        12,
        () => apply({ count: p.count - 1 }, "count"),
        () => apply({ count: p.count + 1 }, "count"),
      )}
      {stepper(
        "Weniger Aufgaben nebeneinander",
        "Mehr Aufgaben nebeneinander",
        `${p.columns} nebeneinander`,
        p.columns,
        1,
        3,
        () => apply({ columns: p.columns - 1 }, "columns"),
        () => apply({ columns: p.columns + 1 }, "columns"),
      )}
      <label>
        Rechenart
        <select aria-label="Rechenart" value={p.op} onChange={(e) => apply({ op: e.target.value as "+" | "-", typed: undefined }, "op")}>
          <option value="+">Plus</option>
          <option value="-">Minus</option>
        </select>
      </label>
      <label>
        Zahlenraum
        <select
          aria-label="Zahlenraum"
          value={p.max}
          onChange={(e) => {
            const max = Number(e.target.value);
            // A change to or from bis 1000 changes the unit of a Hunderterübergang, so the typed numbers go too.
            const drop = p.step === "hunderter" && (p.max === 1000) !== (max === 1000);
            apply(drop ? { max, typed: undefined } : { max }, "max");
          }}
        >
          <option value={20}>bis 20</option>
          <option value={100}>bis 100</option>
          <option value={1000}>bis 1000</option>
        </select>
      </label>
      {p.max === 1000 && (
        <label>
          Übergang
          <select aria-label="Übergang" value={p.step} onChange={(e) => apply({ step: e.target.value as "zehner" | "hunderter", typed: undefined }, "step")}>
            <option value="zehner">Zehner</option>
            <option value="hunderter">Hunderter</option>
          </select>
        </label>
      )}
      <Switch label="Zweite Zahl mehrstellig" on={p.big} onChange={(on) => apply({ big: on }, "big")} />
      <label>
        Muster der 1. Zahl
        <input aria-label="Muster der 1. Zahl" type="text" spellCheck={false} placeholder="z. B. X3" value={p.pa ?? ""} onChange={(e) => apply({ pa: clean(e.target.value) || undefined }, "pa")} />
      </label>
      <label>
        Muster der 2. Zahl
        <input aria-label="Muster der 2. Zahl" type="text" spellCheck={false} placeholder="z. B. X" value={p.pb ?? ""} onChange={(e) => apply({ pb: clean(e.target.value) || undefined }, "pb")} />
      </label>
      <Switch label="Die Null darf vorkommen" on={p.nil !== false} onChange={() => apply({ nil: p.nil === false ? undefined : false }, "nil")} />
      {(p.pa || p.pb || p.nil === false) && !p.typed && m.tasks.every((t) => t.wrong) && (
        <p className="hint" role="status">Mit diesem Muster gibt es keine Aufgabe.</p>
      )}
      <label>
        Aufgabentyp
        <select aria-label="Aufgabentyp" value={p.task} onChange={(e) => apply({ task: e.target.value as ZerlegungsfeldProps["task"] }, "task")}>
          <option value="task">Nur die Aufgabe</option>
          <option value="split">Aufgabe und Zerlegung</option>
          <option value="result">Erste Zahl und Ergebnis</option>
        </select>
      </label>
      <p className="hint">Eigene Zahlen tippst du ins Blatt: Doppelklick auf ein Feld, Tab geht zum nächsten.</p>
      {m.tasks.map((t, k) => {
        if (t.wrong) return <p key={k} className="hint" role="status">{`Aufgabe ${k + 1}: Die Zahlen passen nicht zusammen.`}</p>;
        if (t.many) return <p key={k} className="hint" role="status">{`Aufgabe ${k + 1}: Es gibt mehr als eine Lösung.`}</p>;
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).tasks) }]) }, "seed")}>
        Neu würfeln
      </button>
    </>
  );
}
