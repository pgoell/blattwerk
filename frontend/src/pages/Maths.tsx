// The format panel's settings for a maths block: every limit of the generator in one place.
import Numbering from "../components/Numbering";
import type { Owed } from "../saves";
import { SIGNS, type Limits, type MathsBlock, type MathsProps, type Op } from "../sheet";
import { AFTER, anyDigits, CARRIES, DIGITS, FAMILIES, FORMATS, FRACTIONS, LOOSEN, NACH, NTH, PLACES, ROOMS, SIDES, newSeed, type Key } from "./maths/ask";
import { useFlight } from "./maths/flight";

export { generate, kept, newSeed } from "./maths/ask";

export default function Maths({ block, apply, foot, owe }: { block: MathsBlock; apply: (props: MathsProps, key?: string) => boolean; foot: number; owe: (entry: Owed) => void }) {
  const { p, limit, toggle, own, setOwn, typed, setTyped, wrong, commit, room, ranges, digit, show, gap, refused, line, scale, plus, times, open, dec, money, numbered, three, free, pvs, brackets, fam, families, whole, shown, lit } = useFlight(block, apply, foot, owe);
  return (
    <>
      <h2>Rechenart</h2>
      <div className="seg">
        {(Object.keys(SIGNS) as Op[]).map((op) => (
          <button key={op} className={p.ops.includes(op) ? "on" : ""} aria-pressed={p.ops.includes(op)} onClick={() => toggle(op)}>
            {SIGNS[op]}
          </button>
        ))}
      </div>
      <div className="seg switch">
        <button className={p.zero !== false ? "on" : ""} aria-pressed={p.zero !== false} onClick={() => limit({ zero: p.zero === false })}>
          Aufgaben mit 0
        </button>
      </div>
      <div className="seg switch">
        <button className={p.one !== false ? "on" : ""} aria-pressed={p.one !== false} disabled={!times} onClick={() => limit({ one: p.one === false })}>
          Aufgaben mit 1 beim Malnehmen und Teilen
        </button>
      </div>
      <div className="seg switch">
        <button className={p.small ? "on" : ""} aria-pressed={!!p.small} disabled={!times || three} onClick={() => limit({ small: !p.small })}>
          Kleines Einmaleins
        </button>
      </div>
      <div className="seg switch">
        <button className={p.distinct ? "on" : ""} aria-pressed={!!p.distinct} onClick={() => limit({ distinct: !p.distinct })}>
          keine gleichen Zahlen
        </button>
      </div>
      <h2>Zahlenraum</h2>
      <select
        aria-label="Zahlenraum"
        value={own ? "" : p.max}
        onChange={(e) => {
          setOwn(!e.target.value);
          if (e.target.value) room(+e.target.value);
        }}
      >
        {ROOMS.map((max) => (
          <option key={max} value={max}>
            bis {max.toLocaleString("de")}
          </option>
        ))}
        <option value="">Eigener</option>
      </select>
      {own && (
        <input
          type="number"
          aria-label="Größte Zahl"
          min={1}
          max={1000000}
          value={typed ?? p.max}
          onChange={(e) => setTyped(e.target.value)}
          // Enter and leaving the field apply what is typed, when it fits, and show the number in use.
          onKeyDown={(e) => e.key === "Enter" && commit()}
          onBlur={commit}
        />
      )}
      {own && wrong && <p className="hint" role="status">{wrong} Die Aufgaben gehen bis {p.max.toLocaleString("de")}.</p>}
      <h2>Nachkommastellen</h2>
      <div className="seg">
        {([0, 1, 2] as const).map((n) => (
          // With Geld on, a number takes its place in one step: Geld goes off and the number is lit.
          <button key={n} aria-label={NACH[n]} className={dec === n && !money ? "on" : ""} aria-pressed={dec === n && !money} disabled={!open} onClick={() => limit({ decimals: n, money: false })}>
            {n}
          </button>
        ))}
        <button className={money ? "on" : ""} aria-pressed={money} disabled={!open} onClick={() => limit({ money: !p.money })}>
          Geld
        </button>
      </div>
      {(["a", "b", "c"] as const).slice(0, three ? 3 : 2).map((who) => {
        // One row of a place: its label, then the lowest and the highest digit.
        const row = (key: Key, i: number, label: string, name: string) => [
          <span key={i}>{label}</span>,
          ...([0, 1] as const).map((end) => (
            <select key={`${i}${end}`} aria-label={`${name} ${end ? "bis" : "von"}`} value={ranges(key)[i][end]} onChange={(e) => digit(key, i, end, +e.target.value)}>
              {DIGITS.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          )),
        ];
        return (
          <div key={who}>
            <h2>{NTH[who]}: Ziffern von, bis</h2>
            <div className="places">
              {ranges(who).map((_, i) => row(who, i, PLACES[i], PLACES[i])).reverse()}
              {ranges(AFTER[who]).slice(0, dec).map((_, i) => row(AFTER[who], i, FRACTIONS[i][0], FRACTIONS[i][1]))}
            </div>
          </div>
        );
      })}
      {plus && (
        <>
          <h2>Übertrag</h2>
          <div className="seg">
            {CARRIES.map(([carry, label]) => (
              <button key={carry} className={p.carry === carry ? "on" : ""} onClick={() => limit({ carry })}>
                {label}
              </button>
            ))}
          </div>
        </>
      )}
      {p.ops.includes("/") && p.format !== "compare" && !three && (
        <>
          <h2>Division</h2>
          <div className="seg">
            {/* An Umkehraufgabe leaves no Rest: the buttons are greyed and show that, and keep their value. */}
            <button className={p.rest && !whole ? "" : "on"} disabled={whole} onClick={() => limit({ rest: false })}>Ohne Rest</button>
            <button className={p.rest && !whole ? "on" : ""} disabled={whole} onClick={() => limit({ rest: true })}>Mit Rest</button>
          </div>
        </>
      )}
      <h2>Format</h2>
      <div className="seg">
        {FORMATS.map(([format, label]) => (
          <button key={format} className={p.format === format ? "on" : ""} onClick={() => limit({ format })}>
            {label}
          </button>
        ))}
      </div>
      {p.format === "gap" && (
        <>
          <h2>Lücke</h2>
          <div className="seg">
            {shown.map((k) => (
              <button key={k} aria-label={`Lücke: ${k === "result" ? "Ergebnis" : NTH[k]}`} className={lit.includes(k) ? "on" : ""} aria-pressed={lit.includes(k)} onClick={() => gap(k)}>
                {k === "result" ? "Ergebnis" : NTH[k]}
              </button>
            ))}
          </div>
        </>
      )}
      {numbered && (
        <>
          <h2>Zahlen pro Aufgabe</h2>
          <div className="seg">
            <button aria-label="2 Zahlen" className={three ? "" : "on"} aria-pressed={!three} onClick={() => limit({ numbers: 2 })}>
              2
            </button>
            {/* A third number starts with any digit in each place, unless the block has digits for it already. */}
            <button aria-label="3 Zahlen" className={three ? "on" : ""} aria-pressed={three} onClick={() => limit({ numbers: 3, c: p.c ?? anyDigits(p.max) })}>
              3
            </button>
          </div>
          <div className="seg">
            <button className={pvs ? "on" : ""} aria-pressed={pvs} disabled={!free} onClick={() => limit({ pvs: !p.pvs })}>
              Punkt vor Strich
            </button>
            <button className={brackets ? "on" : ""} aria-pressed={brackets} disabled={!pvs} onClick={() => limit({ brackets: !p.brackets })}>
              mit Klammern
            </button>
          </div>
          <h2>Aufgabenfamilien</h2>
          <select aria-label="Aufgabenfamilien" value={p.family ?? "none"} disabled={three} onChange={(e) => limit({ family: e.target.value as Limits["family"] })}>
            {FAMILIES.map(([family, label]) => (
              <option key={family} value={family}>
                {label}
              </option>
            ))}
          </select>
          {p.family === "neighbour" && !three && (
            <div className="seg">
              <button aria-label="1. Zahl wandert" className={(p.moves ?? "a") === "a" ? "on" : ""} aria-pressed={(p.moves ?? "a") === "a"} onClick={() => limit({ moves: "a" })}>
                1. Zahl
              </button>
              <button aria-label="2. Zahl wandert" className={p.moves === "b" ? "on" : ""} aria-pressed={p.moves === "b"} onClick={() => limit({ moves: "b" })}>
                2. Zahl
              </button>
            </div>
          )}
          {numbered && !three && p.family === "swap" && (p.ops.includes("-") || p.ops.includes("/")) && <p className="hint" role="status">Tauschaufgaben gibt es nur für + und ·.</p>}
        </>
      )}
      {p.format === "compare" && (
        <>
          <h2>Seiten</h2>
          <select aria-label="Seiten" value={p.sides ?? "tn"} onChange={(e) => limit({ sides: e.target.value as Limits["sides"] })}>
            {SIDES.map(([sides, label]) => (
              <option key={sides} value={sides}>
                {label}
              </option>
            ))}
          </select>
          <h2>Abstand</h2>
          <div className="seg">
            <button className={p.close ? "" : "on"} aria-pressed={!p.close} onClick={() => limit({ close: false })}>Beliebig</button>
            <button className={p.close ? "on" : ""} aria-pressed={!!p.close} onClick={() => limit({ close: true })}>Knapp</button>
          </div>
          <h2>Aufgaben mit =</h2>
          <div className="seg">
            <button className={p.equal === "none" ? "on" : ""} aria-label="Keine mit =" aria-pressed={p.equal === "none"} onClick={() => limit({ equal: "none" })}>Keine</button>
            <button className={p.equal === "none" ? "" : "on"} aria-label="Einige mit =" aria-pressed={p.equal !== "none"} onClick={() => limit({ equal: "some" })}>Einige</button>
          </div>
        </>
      )}
      <h2>Anzahl</h2>
      <div className="seg">
        <button aria-label="Eine Aufgabe weniger" onClick={() => limit({ count: Math.max(1, p.count - 1) })}>−</button>
        <output>{p.count === 1 ? (fam ? "1 Familie" : "1 Aufgabe") : fam ? `${p.count} Familien` : `${p.count} Aufgaben`}</output>
        <button aria-label="Eine Aufgabe mehr" onClick={() => limit({ count: Math.min(100, p.count + 1) })}>＋</button>
      </div>
      {fam && <p className="hint">{p.exercises.length === 1 ? "Das ist 1 Aufgabe." : `Das sind ${p.exercises.length} Aufgaben.`}</p>}
      {refused && (
        <p className="hint" role="status" data-foot="full" ref={line}>
          Das passt nicht mehr auf die Seite: Der Block würde unten über den Rand ragen. Mehr Platz gibt es mit weniger Aufgaben, mehr Spalten, kleinerer Schrift oder weiter oben auf der Seite.
        </p>
      )}
      <div className="seg">
        <button aria-label="Eine Spalte weniger" onClick={() => show({ columns: Math.max(1, p.columns - 1) })}>−</button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" onClick={() => show({ columns: Math.min(6, p.columns + 1) })}>＋</button>
      </div>
      {scale < 0.97 && (
        <p className="hint" role="status">
          {p.columns > 1 ? `Für ${p.columns} Spalten sind die Aufgaben zu breit und stehen kleiner da. Mit weniger Spalten werden sie größer.` : "Die Aufgaben sind zu breit für den Block und stehen kleiner da."}
        </p>
      )}
      {p.format !== "written" && (
        <div className="seg">
          <button aria-label="Schrift kleiner" onClick={() => show({ size: Math.max(8, p.size - 2) })}>−</button>
          <output>{p.size} pt</output>
          <button aria-label="Schrift größer" onClick={() => show({ size: p.size + 2 })}>＋</button>
        </div>
      )}
      {p.loosen && (
        <p className="hint" role="status">
          {fam
            ? p.exercises.length
              ? `Mit diesen Grenzen gibt es nur ${families === 1 ? "1 Familie" : `${families} verschiedene Familien`}.`
              : "Mit diesen Grenzen gibt es keine Familie."
            : p.exercises.length
              ? `Mit diesen Grenzen gibt es nur ${p.exercises.length === 1 ? "1 Aufgabe" : `${p.exercises.length} verschiedene Aufgaben`}.`
              : "Mit diesen Grenzen gibt es keine Aufgabe."}
          {p.loosen.length > 0 && ` Mehr gibt es mit einer lockereren Grenze: ${p.loosen.map((name) => LOOSEN[name]).join(", ")}.`}
        </p>
      )}
      <button className="wide" onClick={() => limit({ seed: newSeed() })}>Neu würfeln</button>
      <h2>Aufgaben nummerieren</h2>
      <Numbering value={p.numbering} onChange={(numbering) => show({ numbering })} />
    </>
  );
}
