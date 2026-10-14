// The format panel's settings for a Rechendreieck block: its triangles, its numbers and which fields are given.
import { useRef, useState } from "react";
import type { RechendreieckBlock } from "../sheet";
import { draw } from "../bank";
import { fixes, made, NAMES, sane, ZAHLENRAUM, type RechendreieckProps } from "../rechendreieck";

const GIVEN = { inner: "Innen (leicht)", mix: "Gemischt (mittel)", outer: "Außen (schwer)", free: "Freie Wahl" } as const;
// The fields as the drawing has them: the inner ones at the corners, the outer ones beside the sides.
const SHAPE = [
  [null, 0, null],
  [3, null, 5],
  [1, 4, 2],
];

export default function Rechendreieck({ block, apply }: { block: RechendreieckBlock; apply: (props: Partial<RechendreieckProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const w = Math.min(which, m.triangles.length - 1);

  function setTyped(field: number, text: string) {
    // The stored entries as they are, so that the triangles beyond `count` keep their numbers.
    const raw = block.props.typed;
    const others = (Array.isArray(raw) ? raw : []).filter((t) => Array.isArray(t) && (t[0] !== w || t[1] !== field));
    const key = `typed:${w}:${field}`;
    if (text === "") return apply({ typed: others.length ? others : undefined }, key);
    apply({ typed: [...others, [w, field, Number(text)]] }, key);
  }

  return (
    <>
      <h2>Rechendreieck</h2>
      <div className="seg">
        <button aria-label="Ein Dreieck weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 })}>
          −
        </button>
        <output>{p.count === 1 ? "1 Dreieck" : `${p.count} Dreiecke`}</output>
        <button aria-label="Ein Dreieck mehr" disabled={p.count === 12} onClick={() => apply({ count: p.count + 1 })}>
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
      <select aria-label="Zahlenraum" value={p.max} onChange={(e) => apply({ max: Number(e.target.value) })}>
        {ZAHLENRAUM.map((n) => (
          <option key={n} value={n}>
            {`bis ${n}`}
          </option>
        ))}
      </select>
      <select aria-label="Gegebene Felder" value={p.given} onChange={(e) => apply({ given: e.target.value as RechendreieckProps["given"] })}>
        {Object.entries(GIVEN).map(([given, label]) => (
          <option key={given} value={given}>
            {label}
          </option>
        ))}
      </select>
      {p.given === "free" && (
        <>
          <div className="dreieck">
            {SHAPE.map((row, r) => (
              <div key={r} className="dreieck-row">
                {row.map((i, c) =>
                  i === null ? (
                    <span key={c} />
                  ) : (
                    <button
                      key={c}
                      className={p.free?.[i] ? "on" : ""}
                      aria-label={`Feld ${NAMES[i]}`}
                      aria-pressed={p.free?.[i]}
                      onClick={() => apply({ free: (p.free ?? []).map((v, j) => (j === i ? !v : v)) })}
                    />
                  ),
                )}
              </div>
            ))}
          </div>
          {!fixes(p.free ?? []) && <p className="hint" role="status">Die gegebenen Felder legen das Dreieck nicht fest.</p>}
        </>
      )}
      <button className={p.empty ? "on" : ""} aria-pressed={p.empty} onClick={() => apply({ empty: !p.empty })}>
        Leer
      </button>
      <select aria-label="Dreieck für eigene Zahlen" value={w} onChange={(e) => setWhich(Number(e.target.value))}>
        {m.triangles.map((_, i) => (
          <option key={i} value={i}>
            {`Dreieck ${i + 1}`}
          </option>
        ))}
      </select>
      <div className="dreieck">
        {SHAPE.map((row, r) => (
          <div key={r} className="dreieck-row">
            {row.map((i, c) => {
              if (i === null) return <span key={c} />;
              const key = `${w},${i}`;
              return (
                <input
                  key={c}
                  inputMode="numeric"
                  aria-label={`Zahl im Feld ${NAMES[i]}`}
                  value={draft?.key === key ? draft.text : String(m.triangles[w].numbers[i])}
                  onFocus={() => {
                    fresh.current = true;
                    setDraft({ key, text: String(m.triangles[w].numbers[i]) });
                  }}
                  onMouseUp={(e) => {
                    if (!fresh.current) return;
                    fresh.current = false;
                    e.preventDefault();
                    e.currentTarget.select();
                  }}
                  onBlur={() => setDraft(null)}
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
      {m.triangles.map((t, i) =>
        t.wrong ? (
          <p key={i} className="hint" role="status">{`Dreieck ${i + 1} geht mit diesen Zahlen nicht auf.`}</p>
        ) : t.numbers.some((v) => v > p.max) ? (
          <p key={i} className="hint" role="status">{`Dreieck ${i + 1} geht über den Zahlenraum bis ${p.max} hinaus.`}</p>
        ) : null,
      )}
      {p.typed && <button onClick={() => apply({ typed: undefined })}>Eigene Zahlen entfernen</button>}
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).triangles) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
