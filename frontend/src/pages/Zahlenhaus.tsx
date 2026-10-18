// The format panel's settings for a Zahlenhaus block: its houses, its Zahlenraum, which boxes are given and the numbers typed in.
import { useRef, useState } from "react";
import type { ZahlenhausBlock } from "../sheet";
import { draw } from "../bank";
import { made, sane, sideFlags, type ZahlenhausProps } from "../zahlenhaus";

const ZAHLENRAUM = [10, 20, 100];
const GIVEN = { side: "Dach und eine Seite", roof: "Nur Dach", mix: "Gemischt", free: "Freie Wahl" } as const;

// The name of a box: the roof, or floor f's left or right box (f from 0, the top floor).
const boxName = (b: number) => (b === 0 ? "Dach" : `Stockwerk ${Math.floor((b - 1) / 2) + 1} ${b % 2 === 1 ? "links" : "rechts"}`);

// The free flags for another number of floors: the boxes that are still there keep theirs (the roof and the top
// floors), a new floor takes the "side" flags. The typed numbers need nothing: `sane` drops those of the boxes gone.
const floorsOf = (free: boolean[] | undefined, floors: number) => sideFlags(floors).map((d, i) => free?.[i] ?? d);

export default function Zahlenhaus({ block, apply }: { block: ZahlenhausBlock; apply: (props: Partial<ZahlenhausProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const [which, setWhich] = useState(0);
  // The Zahlenraum at which "Eigener" was chosen or last typed: while the stored one is the same, the input shows,
  // also for 10, 20 or 100. An undo to another Zahlenraum shows the select's own entry again.
  const [ownAt, setOwnAt] = useState<number | null>(null);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const h = Math.min(which, m.houses.length - 1);
  const free = p.free ?? [];
  const showOwn = ownAt === p.max || !ZAHLENRAUM.includes(p.max);
  // The rows of a house's boxes, the roof first, then each floor from the top.
  const rows = [[0], ...Array.from({ length: p.floors }, (_, f) => [1 + 2 * f, 2 + 2 * f])];

  function toggleFree(b: number) {
    apply({ free: free.map((v, j) => (j === b ? !v : v)) });
  }

  // Why an own Zahlenraum that is typed is not stored: it must be from 2 to 1000.
  function ownWrong(text: string) {
    const n = Number(text);
    return n > 1000 ? "Höchstens 1000." : text === "" || n < 2 ? "Mindestens 2." : "";
  }

  // The own Zahlenraum applies on Enter and on leaving the field, when it is in range; else the field shows the number in use.
  function ownDone(text: string) {
    setDraft(null);
    if (ownWrong(text)) return;
    const n = Number(text);
    setOwnAt(n);
    if (n !== p.max) apply({ max: n }, "max");
  }

  function setTyped(box: number, text: string) {
    // The stored entries as they are, so that the houses beyond `count` keep their numbers.
    const raw = block.props.typed;
    const others = (Array.isArray(raw) ? raw : []).filter((t) => Array.isArray(t) && (t[0] !== h || t[1] !== box));
    const key = `typed:${h}:${box}`;
    if (text === "") return apply({ typed: others.length ? others : undefined }, key);
    apply({ typed: [...others, [h, box, Number(text)]] }, key);
  }

  return (
    <>
      <h2>Zahlenhaus</h2>
      <select aria-label="Stockwerke" value={p.floors} onChange={(e) => apply({ floors: Number(e.target.value), free: floorsOf(p.free, Number(e.target.value)) })}>
        {Array.from({ length: 9 }, (_, i) => i + 2).map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
      <div className="seg">
        <button aria-label="Ein Haus weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 })}>
          −
        </button>
        <output>{p.count === 1 ? "1 Haus" : `${p.count} Häuser`}</output>
        <button aria-label="Ein Haus mehr" disabled={p.count === 12} onClick={() => apply({ count: p.count + 1 })}>
          ＋
        </button>
      </div>
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.columns === 1} onClick={() => apply({ columns: p.columns - 1 })}>
          −
        </button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" disabled={p.columns === 6} onClick={() => apply({ columns: p.columns + 1 })}>
          ＋
        </button>
      </div>
      <select
        aria-label="Zahlenraum"
        value={showOwn ? "own" : p.max}
        onChange={(e) => {
          if (e.target.value === "own") return setOwnAt(p.max);
          setOwnAt(null);
          apply({ max: Number(e.target.value) });
        }}
      >
        {ZAHLENRAUM.map((n) => (
          <option key={n} value={n}>
            {`bis ${n}`}
          </option>
        ))}
        <option value="own">Eigener</option>
      </select>
      {showOwn && (
        <input
          className="own"
          inputMode="numeric"
          aria-label="Eigener Zahlenraum"
          value={draft?.key === "max" ? draft.text : String(p.max)}
          onFocus={() => {
            fresh.current = true;
            setDraft({ key: "max", text: String(p.max) });
          }}
          // The click that focuses the field also places the caret; this mouseup selects the whole number instead.
          onMouseUp={(e) => {
            if (!fresh.current) return;
            fresh.current = false;
            e.preventDefault();
            e.currentTarget.select();
          }}
          onBlur={(e) => ownDone(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ownDone(e.currentTarget.value)}
          onChange={(e) => {
            if (!/^\d{0,4}$/.test(e.target.value)) return;
            setDraft({ key: "max", text: e.target.value });
          }}
        />
      )}
      {showOwn && draft?.key === "max" && ownWrong(draft.text) && (
        <p className="hint" role="status">{`${ownWrong(draft.text)} Die Häuser gehen bis ${p.max}.`}</p>
      )}
      <select aria-label="Gegebene Felder" value={p.given} onChange={(e) => apply({ given: e.target.value as ZahlenhausProps["given"] })}>
        {Object.entries(GIVEN).map(([given, label]) => (
          <option key={given} value={given}>
            {label}
          </option>
        ))}
      </select>
      {p.given === "free" && (
        <div className="mauer">
          {rows.map((row, r) => (
            <div key={r} className="mauer-row">
              {row.map((b) => (
                <button
                  key={b}
                  className={free[b] ? "on" : ""}
                  aria-label={boxName(b)}
                  aria-pressed={free[b]}
                  onClick={() => toggleFree(b)}
                />
              ))}
            </div>
          ))}
        </div>
      )}
      <select aria-label="Haus für eigene Zahlen" value={h} onChange={(e) => setWhich(Number(e.target.value))}>
        {m.houses.map((_, i) => (
          <option key={i} value={i}>
            {`Haus ${i + 1}`}
          </option>
        ))}
      </select>
      <div className="mauer">
        {rows.map((row, r) => (
          <div key={r} className="mauer-row">
            {row.map((b) => {
              const key = `${h},${b}`;
              return (
                <input
                  key={b}
                  className="typed"
                  inputMode="numeric"
                  aria-label={b === 0 ? "Zahl im Dach" : `Zahl in ${boxName(b)}`}
                  value={draft?.key === key ? draft.text : String(m.houses[h].numbers[b])}
                  onFocus={() => {
                    fresh.current = true;
                    setDraft({ key, text: String(m.houses[h].numbers[b]) });
                  }}
                  // The click that focuses the field also places the caret; this mouseup selects the whole number instead.
                  onMouseUp={(e) => {
                    if (!fresh.current) return;
                    fresh.current = false;
                    e.preventDefault();
                    e.currentTarget.select();
                  }}
                  onBlur={() => setDraft(null)}
                  onKeyDown={(e) => {
                    // Ctrl+Z and Ctrl+Y are the sheet's here: the field then shows the number that the undo or redo gives.
                    if ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key)) setDraft(null);
                  }}
                  onChange={(e) => {
                    if (!/^\d{0,4}$/.test(e.target.value)) return;
                    setDraft({ key, text: e.target.value });
                    setTyped(b, e.target.value);
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>
      {m.houses.flatMap((hs, i) =>
        hs.wrong.map((bad, f) =>
          bad ? (
            <p key={`${i},${f}`} className="hint" role="status">{`Haus ${i + 1}: Stockwerk ${f + 1} ergibt nicht ${hs.numbers[0]}.`}</p>
          ) : null,
        ),
      )}
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
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).houses) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
