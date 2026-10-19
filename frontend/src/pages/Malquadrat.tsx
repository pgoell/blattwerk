// The format panel's settings for a Malquadrat block: its squares, their size, Rechenart, Reihen or Zahlenraum, Aufgabentyp
// and the numbers typed in.
import { useRef, useState, type ChangeEvent, type KeyboardEvent, type MouseEvent } from "react";
import type { MalquadratBlock } from "../sheet";
import { draw } from "../bank";
import { made, sane, type MalquadratProps, type MalquadratTyped } from "../malquadrat";

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
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, p.count - 1);
  const square = m.squares[c];
  const raw = Array.isArray(block.props.typed) ? block.props.typed : [];

  // Every box of the (n + 2) × (n + 2) grid is a position but the three corners.
  const isPosition = (i: number, j: number) => i >= 0 && j >= 0 && i <= n + 1 && j <= n + 1 && !((i === 0 && j === 0) || (i === 0 && j === n + 1) || (i === n + 1 && j === 0));

  // Stores the number of the box in row i and column j of square c. The first number typed into a square keeps the drawn
  // given numbers of that square as typed entries too.
  function setTyped(i: number, j: number, text: string) {
    const own = (p.typed ?? []).some((e) => e[0] === c && isPosition(e[1], e[2]));
    const drawn: MalquadratTyped[] = [];
    if (!own && square) {
      square.given.forEach((row, r) =>
        row.forEach((given, s) => {
          if (given && isPosition(r, s)) drawn.push([c, r, s, square.cells[r][s]]);
        }),
      );
    }
    const list = [...raw, ...drawn].filter((e) => Array.isArray(e) && (e[0] !== c || e[1] !== i || e[2] !== j));
    if (text !== "") list.push([c, i, j, Number(text)] as MalquadratTyped);
    apply({ typed: list.length ? list : undefined }, `typed:${c}:${i}:${j}`);
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

  // A number field for the box of row i and column j.
  function numberField(i: number, j: number) {
    const key = `${c},${i},${j}`;
    const text = square?.given[i]?.[j] ? String(square.cells[i][j]) : "";
    return (
      <input
        key={`${i},${j}`}
        className="typed"
        inputMode="numeric"
        aria-label={`Zeile ${i}, Spalte ${j}`}
        value={draft?.key === key ? draft.text : text}
        {...fieldHandlers(key, text, (value) => setTyped(i, j, value))}
      />
    );
  }

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
        <div className="reihen">
          {Array.from({ length: 10 }, (_, k) => k + 1).map((r) => {
            const on = p.reihen.includes(r);
            return (
              <label key={r}>
                <input
                  type="checkbox"
                  aria-label={`${r}er-Reihe`}
                  checked={on}
                  disabled={on && p.reihen.length === 1}
                  onChange={() => apply({ reihen: on ? p.reihen.filter((x) => x !== r) : [...p.reihen, r].sort((a, b) => a - b) }, "reihen")}
                />
                {r}
              </label>
            );
          })}
        </div>
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
      {p.count >= 2 && (
        <label>
          Eigene Zahlen
          <select aria-label="Malquadrat für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
            {Array.from({ length: p.count }, (_, k) => (
              <option key={k} value={k}>
                {`Malquadrat ${k + 1}`}
              </option>
            ))}
          </select>
        </label>
      )}
      <div className="mauer" style={{ display: "grid", gridTemplateColumns: `repeat(${n + 2}, auto)`, gap: 4 }}>
        {Array.from({ length: (n + 2) * (n + 2) }, (_, k) => {
          const i = Math.floor(k / (n + 2));
          const j = k % (n + 2);
          return isPosition(i, j) ? numberField(i, j) : <span key={`${i},${j}`} />;
        })}
      </div>
      {m.squares.map((s, k) => {
        if (s.unsure) return null;
        if (s.wrong) return <p key={k} className="hint" role="status">{`Malquadrat ${k + 1}: Die Zahlen passen nicht zusammen.`}</p>;
        if (s.many) return <p key={k} className="hint" role="status">{`Malquadrat ${k + 1}: Es gibt mehr als eine Lösung.`}</p>;
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).squares) }]) }, "seed")}>
        Neu würfeln
      </button>
    </>
  );
}
