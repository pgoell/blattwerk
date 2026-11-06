// The format panel's settings for a Zahlzerlegung block: its tasks, the Zahlenraum, the Aufgabentyp, the number typed
// in for each task and the new draw.
import { useRef, useState, type ChangeEvent, type KeyboardEvent, type MouseEvent } from "react";
import type { ZahlzerlegungBlock } from "../sheet";
import { draw } from "../bank";
import { TYPES, made, sane, type ZahlzerlegungProps, type ZahlzerlegungTyped } from "../zahlzerlegung";

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

export default function Zahlzerlegung({ block, apply }: { block: ZahlzerlegungBlock; apply: (props: Partial<ZahlzerlegungProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when the number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, p.count - 1);
  const task = m.tasks[c];
  const raw = Array.isArray(block.props.typed) ? block.props.typed : [];

  // Stores the number of task c; an empty field removes the task's entry.
  function setTyped(text: string) {
    const list = raw.filter((e) => Array.isArray(e) && e[0] !== c);
    if (text !== "") list.push([c, Number(text)] as ZahlzerlegungTyped);
    apply({ typed: list.length ? list : undefined }, `typed:${c}`);
  }

  // The focus, mouseup and undo handling of the number field.
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

  const key = `${c}`;
  // A typed number that does not fit stays in the field, beside its hint.
  const mine = p.typed?.find((e) => e[0] === c);
  const text = task.wrong ? (mine ? String(mine[1]) : "") : String(task.n);

  return (
    <>
      <h2>Zahlzerlegung</h2>
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
        Zahlenraum
        <select aria-label="Zahlenraum" value={p.max} onChange={(e) => apply({ max: Number(e.target.value), typed: undefined }, "max")}>
          <option value={100}>bis 100</option>
          <option value={1000}>bis 1000</option>
          <option value={10000}>bis 10 000</option>
        </select>
      </label>
      <label>
        Aufgabentyp
        <select aria-label="Aufgabentyp" value={p.task} onChange={(e) => apply({ task: e.target.value as ZahlzerlegungProps["task"] }, "task")}>
          {TYPES.map(([task, word]) => (
            <option key={task} value={task}>
              {word}
            </option>
          ))}
        </select>
      </label>
      {p.count >= 2 && (
        <label>
          Aufgabe
          <select aria-label="Aufgabe" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
            {Array.from({ length: p.count }, (_, j) => (
              <option key={j} value={j}>
                {`Aufgabe ${j + 1}`}
              </option>
            ))}
          </select>
        </label>
      )}
      <label>
        Zahl
        <input
          style={{ width: "100%", boxSizing: "border-box" }}
          className="typed"
          inputMode="numeric"
          aria-label="Zahl"
          value={draft?.key === key ? draft.text : text}
          {...fieldHandlers(key, text, setTyped)}
        />
      </label>
      {m.tasks.map((t, j) =>
        t.wrong ? (
          <p key={j} className="hint" role="status">{`Aufgabe ${j + 1}: Die Zahl passt nicht zu den Einstellungen.`}</p>
        ) : null,
      )}
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
