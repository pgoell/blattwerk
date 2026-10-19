// The format panel's settings for a Magisches Quadrat block: its squares, their size and Zahlenraum, the given numbers, the
// Zielzahl and the numbers typed in.
import { useRef, useState, type ChangeEvent, type KeyboardEvent, type MouseEvent } from "react";
import type { MagischesQuadratBlock } from "../sheet";
import { draw } from "../bank";
import { DEFAULT_GIVEN, GIVEN, made, sane, type MagischesQuadratProps, type MagischesQuadratTyped } from "../magischesquadrat";

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

export default function MagischesQuadrat({ block, apply }: { block: MagischesQuadratBlock; apply: (props: Partial<MagischesQuadratProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, p.count - 1);
  const square = m.squares[c];
  const raw = Array.isArray(block.props.typed) ? block.props.typed : [];

  // The number a box shows: the given number, typed or drawn; an empty box is not given.
  function shownText(r: number, s: number): string {
    return square?.given[r - 1]?.[s - 1] ? String(square.cells[r - 1][s - 1]) : "";
  }

  // Stores the number of the box in row r and column s (from 1) of square c. The first number typed into a square keeps
  // the drawn given numbers of that square as typed entries too.
  function setTyped(r: number, s: number, text: string) {
    const own = raw.some((e) => Array.isArray(e) && e[0] === c);
    const drawn: MagischesQuadratTyped[] = [];
    if (!own && square) {
      square.given.forEach((row, i) =>
        row.forEach((given, j) => {
          if (given) drawn.push([c, i + 1, j + 1, square.cells[i][j]]);
        }),
      );
    }
    const list = [...raw, ...drawn].filter((e) => Array.isArray(e) && (e[0] !== c || e[1] !== r || e[2] !== s));
    if (text !== "") list.push([c, r, s, Number(text)] as MagischesQuadratTyped);
    apply({ typed: list.length ? list : undefined }, `typed:${c}:${r}:${s}`);
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

  // A number field for the box of row r and column s (from 1).
  function numberField(r: number, s: number) {
    const key = `${c},${r},${s}`;
    const text = shownText(r, s);
    return (
      <input
        key={key}
        className="typed"
        inputMode="numeric"
        aria-label={`Zeile ${r}, Spalte ${s}`}
        value={draft?.key === key ? draft.text : text}
        {...fieldHandlers(key, text, (value) => setTyped(r, s, value))}
      />
    );
  }

  const [lo, hi] = GIVEN[p.size];
  const zahlenraum = [20, 100, 1000].includes(p.max) ? String(p.max) : "own";

  return (
    <>
      <h2>Magisches Quadrat</h2>
      {stepper("Ein Quadrat weniger", "Ein Quadrat mehr", plural(p.count, "Quadrat", "Quadrate"), p.count, 1, 4, () => apply({ count: p.count - 1 }), () => apply({ count: p.count + 1 }))}
      {stepper(
        "Weniger Quadrate nebeneinander",
        "Mehr Quadrate nebeneinander",
        `${p.columns} nebeneinander`,
        p.columns,
        1,
        3,
        () => apply({ columns: p.columns - 1 }),
        () => apply({ columns: p.columns + 1 }),
      )}
      {stepper(
        "Eine vorgegebene Zahl weniger",
        "Eine vorgegebene Zahl mehr",
        plural(p.given, "Zahl vorgegeben", "Zahlen vorgegeben"),
        p.given,
        lo,
        hi,
        () => apply({ given: p.given - 1 }),
        () => apply({ given: p.given + 1 }),
      )}
      <label>
        Größe
        <select
          aria-label="Größe"
          value={p.size}
          onChange={(e) => {
            const size = Number(e.target.value) as 3 | 5;
            // One step: the new size's default number of given cells, the typed numbers dropped.
            apply({ size, given: DEFAULT_GIVEN[size], typed: undefined, ...(size === 5 && p.max < 25 ? { max: 100 } : {}) });
          }}
        >
          <option value={3}>3 × 3</option>
          <option value={5}>5 × 5</option>
        </select>
      </label>
      <label>
        Zahlenraum
        <select
          aria-label="Zahlenraum"
          value={zahlenraum}
          onChange={(e) => apply({ max: e.target.value === "own" ? 50 : Number(e.target.value) })}
        >
          <option value="20" disabled={p.size === 5}>
            bis 20
          </option>
          <option value="100">bis 100</option>
          <option value="1000">bis 1000</option>
          <option value="own">Eigener</option>
        </select>
      </label>
      {zahlenraum === "own" && (
        <input
          className="typed"
          inputMode="numeric"
          aria-label="Eigener Zahlenraum"
          value={draft?.key === "max" ? draft.text : String(p.max)}
          {...fieldHandlers("max", String(p.max), (value) => {
            if (value !== "") apply({ max: Number(value) }, "max");
          })}
        />
      )}
      <label>
        <input type="checkbox" aria-label="Zielzahl anzeigen" checked={p.showSum} onChange={() => apply({ showSum: !p.showSum })} />
        Zielzahl anzeigen
      </label>
      <label>
        Eigene Zahlen
        <select aria-label="Magisches Quadrat für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
          {Array.from({ length: p.count }, (_, i) => (
            <option key={i} value={i}>
              {`Magisches Quadrat ${i + 1}`}
            </option>
          ))}
        </select>
      </label>
      <div className="mauer">
        {Array.from({ length: p.size }, (_, r) => (
          <div className="mauer-row" key={r}>
            {Array.from({ length: p.size }, (_, s) => numberField(r + 1, s + 1))}
          </div>
        ))}
      </div>
      {m.squares.map((s, i) => {
        if (s.wrong) return <p key={i} className="hint" role="status">{`Magisches Quadrat ${i + 1}: Die Zahlen passen nicht zusammen.`}</p>;
        if (s.many) return <p key={i} className="hint" role="status">{`Magisches Quadrat ${i + 1}: Es gibt mehr als eine Lösung.`}</p>;
        return null;
      })}
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).squares) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
