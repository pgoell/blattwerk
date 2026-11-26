// The format panel's settings for a Zahlenmauer block: its walls, its numbers and which stones are given.
import type { ZahlenmauerBlock, ZahlenmauerProps } from "../sheet";
import { draw } from "../bank";
import { at, fixes, made, sane, stones } from "../zahlenmauer";
import { Switch } from "../components/Switch";
import { Pane } from "./format/pane";

const ZAHLENRAUM = [10, 20, 100, 1000];
const GIVEN = { base: "Grundreihe (leicht)", mix: "Gemischt (mittel)", free: "Freie Wahl" } as const;
const LOOSEN = { max: "größerem Zahlenraum", base: "weniger Grundsteinen" } as const;

export default function Zahlenmauer({ block, apply }: { block: ZahlenmauerBlock; apply: (props: Partial<ZahlenmauerProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);

  const free = p.free ?? Array.from({ length: stones(p.base) }, (_, i) => i < p.base);
  const rows = Array.from({ length: p.base }, (_, i) => p.base - 1 - i);

  return (
    <>
      <h2>Zahlenmauer</h2>
      {/* Each list says what it sets, as "4 Mauern" does (#899). */}
      <label>
        Grundsteine
        <select aria-label="Grundsteine" value={p.base} onChange={(e) => apply({ base: Number(e.target.value) as 2 | 3 | 4 | 5 | 6, free: undefined, typed: undefined })}>
          {[2, 3, 4, 5, 6].map((n) => (
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
      <Pane tab="Aussehen">
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.columns === 1} onClick={() => apply({ columns: p.columns - 1 })}>
          −
        </button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" disabled={p.columns === 4} onClick={() => apply({ columns: p.columns + 1 })}>
          ＋
        </button>
      </div>
      </Pane>
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
      <Switch label="Leer" on={p.empty} onChange={() => apply({ empty: !p.empty })} />
      <p className="hint">Eigene Zahlen tippst du ins Blatt: Doppelklick auf ein Feld, Tab geht zum nächsten.</p>
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
