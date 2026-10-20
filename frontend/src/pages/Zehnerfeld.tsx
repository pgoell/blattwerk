// The format panel's settings for a Zehnerfeld block: its tasks, the field, the Rechenart and Aufgabentyp, the Zahlenraum,
// the Zehnerübergang, the drawing options, the dots set by hand and the numbers typed in.
import { useRef, useState, type ChangeEvent, type KeyboardEvent, type MouseEvent } from "react";
import type { ZehnerfeldBlock } from "../sheet";
import { draw } from "../bank";
import { MAXES, acts, colorsOf, made, sane, type Cross, type Field, type ZehnerfeldProps, type ZehnerfeldTyped } from "../zehnerfeld";

const plural = (n: number, one: string, many: string) => (n === 1 ? `1 ${one}` : `${n} ${many}`);

const FIELDS: [Field, string][] = [
  ["zehn", "Zehnerfeld 1 × 10"],
  ["zehn2", "Zehnerfeld 2 × 5"],
  ["zwanzig", "Zwanzigerfeld 2 × 10"],
  ["hundert", "Hunderterfeld 10 × 10"],
];
const TASKS: [ZehnerfeldProps["task"], string][] = [
  ["dots", "Punkte gegeben, Aufgabe schreiben"],
  ["write", "Aufgabe gegeben, Punkte malen"],
  ["mixed", "Gemischt"],
];
const CROSSES: [Cross, string][] = [
  ["any", "egal"],
  ["yes", "mit Zehnerübergang"],
  ["no", "ohne Zehnerübergang"],
];
const COLORS: [ZehnerfeldProps["colors"], string][] = [
  ["color", "Farbe"],
  ["grey", "Graustufen"],
  ["own", "Eigene Farben"],
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

export default function Zehnerfeld({ block, apply }: { block: ZehnerfeldBlock; apply: (props: Partial<ZehnerfeldProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const k = acts(p);
  const [col1, col2] = colorsOf(p);
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, p.count - 1);
  const task = m.tasks[c];
  const raw = Array.isArray(block.props.typed) ? block.props.typed : [];
  const rawMarks = Array.isArray(block.props.marks) ? block.props.marks : [];

  // Stores the number at position pos of task c. The first number typed into a task keeps the drawn a and b of that
  // task as typed entries too, unless no task fits.
  function setTyped(pos: number, text: string) {
    const own = (p.typed ?? []).some((e) => e[0] === c);
    const drawn: ZehnerfeldTyped[] = [];
    if (!own && task && !task.none && !m.none) {
      [0, 1].forEach((q) => drawn.push([c, q, task.values[q]]));
    }
    const list = [...raw, ...drawn].filter((e) => Array.isArray(e) && (e[0] !== c || e[1] !== pos));
    if (text !== "") list.push([c, pos, Number(text)] as ZehnerfeldTyped);
    apply({ typed: list.length ? list : undefined }, `typed:${c}:${pos}`);
  }

  // A click on dot k cycles its mark 0, 1, 2, 3, 0: one undo step each.
  function cycle(j: number) {
    const current = rawMarks.find((e) => Array.isArray(e) && e[0] === c && e[1] === j)?.[2] ?? 0;
    const next = (current + 1) % 4;
    const list = rawMarks.filter((e) => Array.isArray(e) && (e[0] !== c || e[1] !== j));
    if (next) list.push([c, j, next]);
    apply({ marks: list.length ? list : undefined });
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
        if (!/^\d{0,3}$/.test(e.target.value)) return;
        setDraft({ key, text: e.target.value });
        change(e.target.value);
      },
    };
  }

  // A number field for position pos (0 the first number, 1 the second) of task c.
  function numberField(pos: number) {
    const key = `${c},${pos}`;
    const text = task && !task.wrong && !task.none ? String(task.values[pos]) : "";
    const name = pos === 0 ? "Erste Zahl" : "Zweite Zahl";
    return (
      <label key={pos} style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        {name}
        <input
          style={{ width: "100%", boxSizing: "border-box" }}
          className="typed"
          inputMode="numeric"
          aria-label={name}
          value={draft?.key === key ? draft.text : text}
          {...fieldHandlers(key, text, (value) => setTyped(pos, value))}
        />
      </label>
    );
  }

  return (
    <>
      <h2>Zehnerfeld</h2>
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
        4,
        () => apply({ columns: p.columns - 1 }, "columns"),
        () => apply({ columns: p.columns + 1 }, "columns"),
      )}
      <label>
        Feld
        <select aria-label="Feld" value={p.field} onChange={(e) => apply({ field: e.target.value as Field, typed: undefined }, "field")}>
          {FIELDS.map(([field, word]) => (
            <option key={field} value={field}>
              {word}
            </option>
          ))}
        </select>
      </label>
      <label>
        Rechenart
        <select aria-label="Rechenart" value={p.op} onChange={(e) => apply({ op: e.target.value as "+" | "-", typed: undefined }, "op")}>
          <option value="+">Plus</option>
          <option value="-">Minus</option>
        </select>
      </label>
      <label>
        Aufgabentyp
        <select aria-label="Aufgabentyp" value={p.task} onChange={(e) => apply({ task: e.target.value as ZehnerfeldProps["task"] }, "task")}>
          {TASKS.map(([task, word]) => (
            <option key={task} value={task}>
              {word}
            </option>
          ))}
        </select>
      </label>
      <label>
        Zahlenraum
        <select aria-label="Zahlenraum" value={k.M} onChange={(e) => apply({ max: Number(e.target.value) }, "max")}>
          {MAXES.filter((v) => v <= k.C).map((v) => (
            <option key={v} value={v}>
              {`bis ${v}`}
            </option>
          ))}
        </select>
      </label>
      {k.C >= 20 && (
        <label>
          Zehnerübergang
          <select aria-label="Zehnerübergang" value={k.cross} onChange={(e) => apply({ cross: e.target.value as Cross }, "cross")}>
            {CROSSES.map(([cross, word]) => (
              <option key={cross} value={cross}>
                {word}
              </option>
            ))}
          </select>
        </label>
      )}
      <label>
        <input type="checkbox" aria-label="Trennlinien" checked={p.lines} onChange={(e) => apply({ lines: e.target.checked }, "lines")} />
        Trennlinien
      </label>
      <label>
        Farben
        <select aria-label="Farben" value={p.colors} onChange={(e) => apply({ colors: e.target.value as ZehnerfeldProps["colors"] }, "colors")}>
          {COLORS.map(([colors, word]) => (
            <option key={colors} value={colors}>
              {word}
            </option>
          ))}
        </select>
      </label>
      {p.colors === "own" && (
        <>
          <label>
            Erste Farbe
            <input type="color" aria-label="Erste Farbe" value={col1} onChange={(e) => apply({ color1: e.target.value }, "color1")} />
          </label>
          <label>
            Zweite Farbe
            <input type="color" aria-label="Zweite Farbe" value={col2} onChange={(e) => apply({ color2: e.target.value }, "color2")} />
          </label>
        </>
      )}
      <label>
        <input type="checkbox" aria-label="Punkte selbst setzen" checked={p.manual} onChange={(e) => apply({ manual: e.target.checked }, "manual")} />
        Punkte selbst setzen
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
      {p.manual ? (
        <div className="punkte" style={{ display: "grid", gridTemplateColumns: `repeat(${k.cols}, 1fr)`, gap: 4 }}>
          {Array.from({ length: k.C }, (_, j) => {
            const mark = rawMarks.find((e) => Array.isArray(e) && e[0] === c && e[1] === j)?.[2] ?? 0;
            return <button key={j} aria-label={`Punkt ${j + 1}`} data-mark={mark} onClick={() => cycle(j)} />;
          })}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 4 }}>
          {Array.from({ length: 2 }, (_, pos) => numberField(pos))}
        </div>
      )}
      {!p.manual && m.none && (
        <p className="hint" role="status">
          Mit diesen Einstellungen gibt es keine Aufgabe.
        </p>
      )}
      {!p.manual &&
        m.tasks.map((t, j) =>
          t.wrong ? (
            <p key={j} className="hint" role="status">{`Aufgabe ${j + 1}: Die Zahlen passen nicht ins Feld.`}</p>
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
