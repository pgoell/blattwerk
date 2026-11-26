// The format panel's settings for a Magisches Quadrat block: its squares, their size and Zahlenraum, the given numbers, the
// Zielzahl and the numbers typed in.
import { useRef, useState, type ChangeEvent, type KeyboardEvent, type MouseEvent } from "react";
import type { MagischesQuadratBlock } from "../sheet";
import { draw } from "../bank";
import { DEFAULT_GIVEN, GIVEN, MIN_MAX, made, sane, type MagischesQuadratProps } from "../magischesquadrat";
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

export default function MagischesQuadrat({ block, apply }: { block: MagischesQuadratBlock; apply: (props: Partial<MagischesQuadratProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);


  // The focus, mouseup and undo handling of the own Zahlenraum's field.
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
      {/* Kept while it has the draft, so that a number typed on the way (a 100 of 1000) does not unmount it. */}
      {(zahlenraum === "own" || draft?.key === "max") && (
        <input
          className="typed"
          inputMode="numeric"
          aria-label="Eigener Zahlenraum"
          value={draft?.key === "max" ? draft.text : String(p.max)}
          {...fieldHandlers("max", String(p.max), (value) => {
            // Only a whole number the size allows is stored; a shorter number typed on the way waits in the draft.
            const n = Number(value);
            if (value !== "" && n >= MIN_MAX[p.size] && n <= 9999) apply({ max: n }, "max");
          })}
        />
      )}
      <Switch label="Zielzahl anzeigen" on={p.showSum} onChange={() => apply({ showSum: !p.showSum })} />
      <p className="hint">Eigene Zahlen tippst du ins Blatt: Doppelklick auf ein Feld, Tab geht zum nächsten.</p>
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
