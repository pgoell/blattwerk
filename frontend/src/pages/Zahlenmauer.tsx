// The format panel's settings for a Zahlenmauer block: its walls, its numbers and which stones are given.
import { useRef, useState } from "react";
import type { ZahlenmauerBlock, ZahlenmauerProps } from "../sheet";
import { draw } from "../bank";
import { at, fixes, made, sane, stones } from "../zahlenmauer";

const ZAHLENRAUM = [10, 20, 100, 1000];
const GIVEN = { base: "Grundreihe (leicht)", mix: "Gemischt (mittel)", free: "Freie Wahl" } as const;
const LOOSEN = { max: "größerem Zahlenraum", base: "weniger Grundsteinen" } as const;

export default function Zahlenmauer({ block, apply }: { block: ZahlenmauerBlock; apply: (props: Partial<ZahlenmauerProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const w = Math.min(which, m.walls.length - 1);
  const free = p.free ?? Array.from({ length: stones(p.base) }, (_, i) => i < p.base);
  const rows = Array.from({ length: p.base }, (_, i) => p.base - 1 - i);

  function setTyped(stone: number, text: string) {
    // The stored entries as they are, so that the walls beyond `count` keep their numbers.
    const raw = block.props.typed;
    const others = (Array.isArray(raw) ? raw : []).filter((t) => Array.isArray(t) && (t[0] !== w || t[1] !== stone));
    const key = `typed:${w}:${stone}`;
    if (text === "") return apply({ typed: others.length ? others : undefined }, key);
    apply({ typed: [...others, [w, stone, Number(text)]] }, key);
  }

  return (
    <>
      <h2>Zahlenmauer</h2>
      {/* Each list says what it sets, as "4 Mauern" does (#899). */}
      <label>
        Grundsteine
        <select aria-label="Grundsteine" value={p.base} onChange={(e) => apply({ base: Number(e.target.value) as 3 | 4 | 5, free: undefined, typed: undefined })}>
          {[3, 4, 5].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>
      <div className="seg">
        <button aria-label="Eine Mauer weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 })}>
          −
        </button>
        <output>{p.count === 1 ? "1 Mauer" : `${p.count} Mauern`}</output>
        <button aria-label="Eine Mauer mehr" disabled={p.count === 12} onClick={() => apply({ count: p.count + 1 })}>
          ＋
        </button>
      </div>
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.columns === 1} onClick={() => apply({ columns: p.columns - 1 })}>
          −
        </button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" disabled={p.columns === 4} onClick={() => apply({ columns: p.columns + 1 })}>
          ＋
        </button>
      </div>
      <label>
        Zahlenraum
        <select aria-label="Zahlenraum" value={p.max} onChange={(e) => apply({ max: Number(e.target.value) as ZahlenmauerProps["max"] })}>
          {ZAHLENRAUM.map((n) => (
            <option key={n} value={n}>
              {`bis ${n}`}
            </option>
          ))}
        </select>
      </label>
      <div className="seg">
        <button className={p.op === "+" ? "on" : ""} aria-pressed={p.op === "+"} onClick={() => apply({ op: "+" })}>
          Plus
        </button>
        <button className={p.op === "*" ? "on" : ""} aria-pressed={p.op === "*"} onClick={() => apply({ op: "*" })}>
          Mal
        </button>
      </div>
      <label>
        Gegebene Steine
        <select aria-label="Gegebene Steine" value={p.given} onChange={(e) => apply({ given: e.target.value as ZahlenmauerProps["given"] })}>
          {Object.entries(GIVEN).map(([given, label]) => (
            <option key={given} value={given}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {p.given === "free" && (
        <>
          <div className="mauer">
            {rows.map((r) => (
              <div key={r} className="mauer-row">
                {Array.from({ length: p.base - r }, (_, c) => {
                  const i = at(p.base, r, c);
                  return (
                    <button
                      key={c}
                      className={free[i] ? "on" : ""}
                      aria-label={`Stein ${c + 1} der Reihe ${r + 1}`}
                      aria-pressed={free[i]}
                      onClick={() => apply({ free: free.map((v, j) => (j === i ? !v : v)) })}
                    />
                  );
                })}
              </div>
            ))}
          </div>
          {!fixes(p.base, free) && <p className="hint" role="status">Die gegebenen Steine legen die Mauer nicht fest.</p>}
        </>
      )}
      <button className={p.empty ? "on" : ""} aria-pressed={p.empty} onClick={() => apply({ empty: !p.empty })}>
        Leer
      </button>
      <label>
        Eigene Zahlen
        <select aria-label="Mauer für eigene Zahlen" value={w} onChange={(e) => setWhich(Number(e.target.value))}>
          {m.walls.map((_, i) => (
            <option key={i} value={i}>
              {`Mauer ${i + 1}`}
            </option>
          ))}
        </select>
      </label>
      <div className="mauer">
        {rows.map((r) => (
          <div key={r} className="mauer-row">
            {Array.from({ length: p.base - r }, (_, c) => {
              const i = at(p.base, r, c);
              const key = `${w},${i}`;
              return (
                <input
                  key={c}
                  className="typed"
                  inputMode="numeric"
                  aria-label={`Zahl im Stein ${c + 1} der Reihe ${r + 1}`}
                  value={draft?.key === key ? draft.text : String(m.walls[w].numbers[i])}
                  onFocus={() => {
                    fresh.current = true;
                    setDraft({ key, text: String(m.walls[w].numbers[i]) });
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
                    setTyped(i, e.target.value);
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>
      {m.walls.map((mw, i) =>
        mw.wrong ? (
          <p key={i} className="hint" role="status">{`Mauer ${i + 1} geht mit diesen Zahlen nicht auf.`}</p>
        ) : mw.numbers.some((v) => v > p.max) ? (
          <p key={i} className="hint" role="status">{`Mauer ${i + 1} geht über den Zahlenraum bis ${p.max} hinaus.`}</p>
        ) : null,
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
      {m.loosen.length > 0 && m.walls.length < p.count && (
        <p className="hint" role="status">
          {`Nur ${m.walls.length} Mauern möglich. Mehr gibt es mit: ${m.loosen.map((l) => LOOSEN[l]).join(", ")}.`}
        </p>
      )}
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).walls) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
