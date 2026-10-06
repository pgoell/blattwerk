// The format panel's settings for a maths block: every limit of the generator in one place.
import { useRef, useState } from "react";
import { post } from "../api";
import Numbering from "../components/Numbering";
import { SIGNS, type Limits, type Made, type MathsBlock, type MathsProps, type Op, type Range } from "../sheet";

const ROOMS = [10, 20, 100, 1000, 1000000];
// Einer, Zehner, Hunderter, Tausender and so on up to the million.
const PLACES = ["E", "Z", "H", "T", "ZT", "HT", "M"];
const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
const CARRIES = [["none", "Ohne"], ["required", "Mit"], ["either", "Egal"]] as const;
const FORMATS = [["row", "Zeile"], ["gap", "Lücke"], ["written", "Schriftlich"]] as const;
const LOOSEN: Record<string, string> = { carry: "Übertrag", rest: "Rest", a: "Ziffern der 1. Zahl", b: "Ziffern der 2. Zahl", max: "Zahlenraum" };

export const newSeed = () => Math.floor(Math.random() * 1e9);
export const generate = ({ ops, max, a, b, carry, rest, format, count, seed }: Limits) =>
  post<Made>("/maths", { ops, max, a, b, carry, rest, format, count, seed });

export default function Maths({ block, apply }: { block: MathsBlock; apply: (props: MathsProps) => void }) {
  // The limits as last set, shown until the server's exercises for them are on the sheet.
  const [pending, setPending] = useState<MathsProps>();
  const [failed, setFailed] = useState(false);
  const [own, setOwn] = useState(!ROOMS.includes(block.props.max));
  const asked = useRef(0);
  const p = pending ?? block.props;

  // A new limit asks for new exercises. Only the answer to the last question counts.
  async function limit(change: Partial<Limits>) {
    const next = { ...p, ...change };
    const n = ++asked.current;
    setPending(next);
    const made = await generate(next).catch(() => undefined);
    if (n !== asked.current) return;
    if (made) apply({ ...next, ...made });
    setFailed(!made);
    setPending(undefined);
  }
  // A number has as many places as the Zahlenraum; a new place takes any digit.
  function room(max: number) {
    const fit = (places: Range[]) => Array.from(String(max), (_, i) => places[i] ?? [0, 9]);
    limit({ max, a: fit(p.a), b: fit(p.b) });
  }
  function toggle(op: Op) {
    const ops = p.ops.includes(op) ? p.ops.filter((o) => o !== op) : [...p.ops, op];
    if (ops.length) limit({ ops });
  }
  // The lowest digit of a place never lies above its highest: the other end moves along.
  function digit(who: "a" | "b", place: number, end: 0 | 1, to: number) {
    const range = ([lo, hi]: Range): Range => (end ? [Math.min(lo, to), to] : [to, Math.max(hi, to)]);
    limit({ [who]: p[who].map((r, i) => (i === place ? range(r) : r)) });
  }
  const show = (change: Partial<MathsProps>) => apply({ ...p, ...change });
  const plus = p.ops.includes("+") || p.ops.includes("-");

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
          defaultValue={p.max}
          onChange={(e) => e.target.validity.valid && e.target.value && room(Math.floor(+e.target.value))}
        />
      )}
      {(["a", "b"] as const).map((who) => (
        <div key={who}>
          <h2>{who === "a" ? "1. Zahl" : "2. Zahl"}: Ziffern von, bis</h2>
          <div className="places">
            {p[who]
              .map((range, i) => [
                <span key={i}>{PLACES[i]}</span>,
                ...([0, 1] as const).map((end) => (
                  <select key={`${i}${end}`} aria-label={`${PLACES[i]} ${end ? "bis" : "von"}`} value={range[end]} onChange={(e) => digit(who, i, end, +e.target.value)}>
                    {DIGITS.map((d) => (
                      <option key={d}>{d}</option>
                    ))}
                  </select>
                )),
              ])
              .reverse()}
          </div>
        </div>
      ))}
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
      {p.ops.includes("/") && (
        <>
          <h2>Division</h2>
          <div className="seg">
            <button className={p.rest ? "" : "on"} onClick={() => limit({ rest: false })}>Ohne Rest</button>
            <button className={p.rest ? "on" : ""} onClick={() => limit({ rest: true })}>Mit Rest</button>
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
      <h2>Anzahl</h2>
      <div className="seg">
        <button aria-label="Eine Aufgabe weniger" onClick={() => limit({ count: Math.max(1, p.count - 1) })}>−</button>
        <output>{p.count} Aufgaben</output>
        <button aria-label="Eine Aufgabe mehr" onClick={() => limit({ count: Math.min(100, p.count + 1) })}>＋</button>
      </div>
      <div className="seg">
        <button aria-label="Eine Spalte weniger" onClick={() => show({ columns: Math.max(1, p.columns - 1) })}>−</button>
        <output>{p.columns} Spalten</output>
        <button aria-label="Eine Spalte mehr" onClick={() => show({ columns: Math.min(6, p.columns + 1) })}>＋</button>
      </div>
      {p.format !== "written" && (
        <div className="seg">
          <button aria-label="Schrift kleiner" onClick={() => show({ size: Math.max(8, p.size - 2) })}>−</button>
          <output>{p.size} pt</output>
          <button aria-label="Schrift größer" onClick={() => show({ size: p.size + 2 })}>＋</button>
        </div>
      )}
      {p.loosen && (
        <p className="hint" role="status">
          {p.exercises.length ? `Mit diesen Grenzen gibt es nur ${p.exercises.length} verschiedene Aufgaben.` : "Mit diesen Grenzen gibt es keine Aufgabe."}
          {p.loosen.length > 0 && ` Mehr gibt es mit einer lockereren Grenze: ${p.loosen.map((name) => LOOSEN[name]).join(", ")}.`}
        </p>
      )}
      {failed && <p className="hint" role="alert">Die Aufgaben ließen sich nicht erzeugen. Ist das Gerät online?</p>}
      <button className="wide" onClick={() => limit({ seed: newSeed() })}>Neu würfeln</button>
      <h2>Aufgaben nummerieren</h2>
      <Numbering value={p.numbering} onChange={(numbering) => show({ numbering })} />
    </>
  );
}
