// The format panel's settings for a Zerlegungsfeld block: its tasks, their columns, Rechenart, Zahlenraum, Übergang,
// Aufgabentyp and the numbers typed in.
import { useRef, useState, type ChangeEvent, type KeyboardEvent, type MouseEvent } from "react";
import type { ZerlegungsfeldBlock } from "../sheet";
import { draw } from "../bank";
import { NAMES, made, sane, type ZerlegungsfeldProps, type ZerlegungsfeldTyped } from "../zerlegungsfeld";

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
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, p.count - 1);
  const task = m.tasks[c];
  const raw = Array.isArray(block.props.typed) ? block.props.typed : [];

  // Stores the number at position pos of task c. The first number typed into a task keeps the drawn given positions of
  // that task as typed entries too.
  function setTyped(pos: number, text: string) {
    const own = (p.typed ?? []).some((e) => e[0] === c);
    const drawn: ZerlegungsfeldTyped[] = [];
    if (!own && task) {
      task.given.forEach((given, q) => {
        if (given) drawn.push([c, q, task.values[q]]);
      });
    }
    const list = [...raw, ...drawn].filter((e) => Array.isArray(e) && (e[0] !== c || e[1] !== pos));
    if (text !== "") list.push([c, pos, Number(text)] as ZerlegungsfeldTyped);
    apply({ typed: list.length ? list : undefined }, `typed:${c}:${pos}`);
  }

  // The focus, mouseup and undo handling shared by the number fields.
  function fieldHandlers(key: string, text: string, change: (text: string) => void) {
    return {
      onFocus: () => {
        fresh.current = true;
        setDraft({ key, text });
      },
      // The click that focuses the field also places the caret; this mouseup selects the whole number instead.
      onMouseUp: (e: MouseEvent<HTMLInputElement>) => {
        if (!fresh.current) return;
        fresh.current = false;
        e.preventDefault();
        e.currentTarget.select();
      },
      onBlur: () => setDraft(null),
      onKeyDown: (e: KeyboardEvent<HTMLInputElement>) => {
        // Ctrl+Z and Ctrl+Y are the sheet's here: the field then shows the number that the undo or redo gives.
        if ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key)) setDraft(null);
      },
      onChange: (e: ChangeEvent<HTMLInputElement>) => {
        if (!/^\d{0,4}$/.test(e.target.value)) return;
        setDraft({ key, text: e.target.value });
        change(e.target.value);
      },
    };
  }

  // A number field for position pos of task c.
  function numberField(pos: number) {
    const key = `${c},${pos}`;
    const text = task?.given[pos] ? String(task.values[pos]) : "";
    return (
      <input
        key={pos}
        className="typed"
        inputMode="numeric"
        aria-label={NAMES[pos]}
        value={draft?.key === key ? draft.text : text}
        {...fieldHandlers(key, text, (value) => setTyped(pos, value))}
      />
    );
  }

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
      <label>
        <input type="checkbox" aria-label="Zweite Zahl mehrstellig" checked={p.big} onChange={(e) => apply({ big: e.target.checked }, "big")} />
        Zweite Zahl mehrstellig
      </label>
      <label>
        Aufgabentyp
        <select aria-label="Aufgabentyp" value={p.task} onChange={(e) => apply({ task: e.target.value as ZerlegungsfeldProps["task"] }, "task")}>
          <option value="task">Nur die Aufgabe</option>
          <option value="split">Aufgabe und Zerlegung</option>
          <option value="result">Erste Zahl und Ergebnis</option>
        </select>
      </label>
      {p.count >= 2 && (
        <label>
          Eigene Zahlen
          <select aria-label="Aufgabe für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
            {Array.from({ length: p.count }, (_, k) => (
              <option key={k} value={k}>
                {`Aufgabe ${k + 1}`}
              </option>
            ))}
          </select>
        </label>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 4 }}>
        {Array.from({ length: 6 }, (_, pos) => numberField(pos))}
      </div>
      {m.tasks.map((t, k) => {
        if (t.wrong) return <p key={k} className="hint" role="status">{`Aufgabe ${k + 1}: Die Zahlen passen nicht zusammen.`}</p>;
        if (t.many) return <p key={k} className="hint" role="status">{`Aufgabe ${k + 1}: Es gibt mehr als eine Lösung.`}</p>;
        return null;
      })}
      {p.typed && (
        <button
          onClick={() => {
            setDraft(null);
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
