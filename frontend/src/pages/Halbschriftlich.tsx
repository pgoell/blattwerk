// The format panel's settings for a Halbschriftlich block: its tasks, their columns, Rechenart, Zahlenraum, the places of
// the second number, the Übergang, the drawing options and the numbers typed in.
import { useRef, useState, type ChangeEvent, type KeyboardEvent, type MouseEvent } from "react";
import type { HalbschriftlichBlock } from "../sheet";
import { draw } from "../bank";
import { NAMES, acts, made, sane, type HalbschriftlichProps, type HalbschriftlichTyped, type Rule } from "../halbschriftlich";

const plural = (n: number, one: string, many: string) => (n === 1 ? `1 ${one}` : `${n} ${many}`);

// The panel's words for the Übergang rules, by the stored value.
const RULES: [Rule, string][] = [
  ["any", "egal"],
  ["yes", "mit Übergang"],
  ["no", "ohne Übergang"],
];

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

export default function Halbschriftlich({ block, apply }: { block: HalbschriftlichBlock; apply: (props: Partial<HalbschriftlichProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const k = acts(p);
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, p.count - 1);
  const task = m.tasks[c];

  // Stores the number at position pos of task c. The first number typed into a task keeps the drawn given positions of
  // that task as typed entries too, unless no task fits.
  function setTyped(pos: number, text: string) {
    const own = (p.typed ?? []).some((e) => e[0] === c);
    const drawn: HalbschriftlichTyped[] = [];
    if (!own && task && !m.none) {
      task.given.forEach((given, q) => {
        if (given) drawn.push([c, q, task.values[q]]);
      });
    }
    const raw = Array.isArray(block.props.typed) ? block.props.typed : [];
    const list = [...raw, ...drawn].filter((e) => Array.isArray(e) && (e[0] !== c || e[1] !== pos));
    if (text !== "") list.push([c, pos, Number(text)] as HalbschriftlichTyped);
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
      <label key={pos} style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        {NAMES[pos]}
        <input
          style={{ width: "100%", boxSizing: "border-box" }}
          className="typed"
          inputMode="numeric"
          aria-label={NAMES[pos]}
          value={draft?.key === key ? draft.text : text}
          {...fieldHandlers(key, text, (value) => setTyped(pos, value))}
        />
      </label>
    );
  }

  // A select for an Übergang rule: the panel's words, the stored value.
  function ruleSelect(label: string, value: Rule, set: (rule: Rule) => void) {
    return (
      <label>
        {label}
        <select aria-label={label} value={value} onChange={(e) => set(e.target.value as Rule)}>
          {RULES.map(([rule, word]) => (
            <option key={rule} value={rule}>
              {word}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <>
      <h2>Halbschriftlich rechnen</h2>
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
        <select aria-label="Zahlenraum" value={p.max} onChange={(e) => apply({ max: Number(e.target.value) }, "max")}>
          <option value={100}>bis 100</option>
          <option value={1000}>bis 1000</option>
        </select>
      </label>
      <label>
        Stellen der zweiten Zahl
        <select aria-label="Stellen der zweiten Zahl" value={k.k} onChange={(e) => apply({ digits: Number(e.target.value) }, "digits")}>
          <option value={1}>einstellig</option>
          <option value={2}>zweistellig</option>
          {p.max === 1000 && <option value={3}>dreistellig</option>}
        </select>
      </label>
      {ruleSelect("Übergang bei den Einern", k.einer, (einer) => apply({ einer }, "einer"))}
      {p.max === 1000 && k.k >= 2 && ruleSelect("Übergang bei den Zehnern", k.zehner, (zehner) => apply({ zehner }, "zehner"))}
      <label>
        <input type="checkbox" aria-label="Karo" checked={p.grid} onChange={(e) => apply({ grid: e.target.checked }, "grid")} />
        Karo
      </label>
      <label>
        <input type="checkbox" aria-label="Stellenwerte zeigen" checked={p.head} onChange={(e) => apply({ head: e.target.checked }, "head")} />
        Stellenwerte zeigen
      </label>
      <label>
        <input type="checkbox" aria-label="Zweite Zahl färben" checked={p.tint} onChange={(e) => apply({ tint: e.target.checked }, "tint")} />
        Zweite Zahl färben
      </label>
      <label>
        <input
          type="checkbox"
          aria-label="Rechenzeichen der Schritte drucken"
          checked={p.ops}
          onChange={(e) => apply({ ops: e.target.checked }, "ops")}
        />
        Rechenzeichen der Schritte drucken
      </label>
      {p.count >= 2 && (
        <label>
          Aufgabe für eigene Zahlen
          <select aria-label="Aufgabe für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
            {Array.from({ length: p.count }, (_, j) => (
              <option key={j} value={j}>
                {`Aufgabe ${j + 1}`}
              </option>
            ))}
          </select>
        </label>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 4 }}>
        {Array.from({ length: 3 }, (_, pos) => numberField(pos))}
      </div>
      {m.none && (
        <p className="hint" role="status">
          Mit diesen Einstellungen gibt es keine Aufgabe.
        </p>
      )}
      {m.tasks.map((t, j) => {
        if (t.wrong) return <p key={j} className="hint" role="status">{`Aufgabe ${j + 1}: Die Zahlen passen nicht zusammen.`}</p>;
        if (t.many) return <p key={j} className="hint" role="status">{`Aufgabe ${j + 1}: Es gibt mehr als eine Lösung.`}</p>;
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
