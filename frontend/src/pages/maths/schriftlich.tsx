// The written format: how many numbers a plus stacks, where the signs sit, which minus is drawn, and the place letters.
import type { Limits, MathsProps } from "../../sheet";

const METHODS = [
  ["fill", "Ergänzen", "Ergänzungsverfahren"],
  ["unbundle", "Entbündeln", "Entbündelungsverfahren"],
  ["extend", "Erweitern", "Abziehverfahren mit Erweitern"],
] as const;

export default function Schriftlich({ p, limit, plus }: { p: MathsProps; limit: (change: Partial<Limits>) => void; plus: boolean }) {
  const onlyPlus = p.ops.length === 1 && p.ops[0] === "+";
  const count = p.numbers ?? 2;
  const minus = p.ops.includes("-");
  return (
    <>
      {onlyPlus && (
        <>
          <h2>Zahlen pro Aufgabe</h2>
          <div className="seg">
            {([2, 3, 4] as const).map((n) => (
              <button key={n} aria-label={`${n} Zahlen`} className={count === n ? "on" : ""} aria-pressed={count === n} onClick={() => limit({ numbers: n })}>
                {n}
              </button>
            ))}
          </div>
          {count > 2 && (
            <>
              <h2>Rechenzeichen</h2>
              <div className="seg">
                <button aria-label="Alle Rechenzeichen" className={(p.signs ?? "all") === "all" ? "on" : ""} aria-pressed={(p.signs ?? "all") === "all"} onClick={() => limit({ signs: "all" })}>
                  alle
                </button>
                <button aria-label="Nur das letzte Rechenzeichen" className={p.signs === "last" ? "on" : ""} aria-pressed={p.signs === "last"} onClick={() => limit({ signs: "last" })}>
                  nur das letzte
                </button>
              </div>
            </>
          )}
        </>
      )}
      {minus && (
        <>
          <h2>Verfahren</h2>
          <div className="seg">
            {METHODS.map(([id, label, name]) => (
              <button key={id} aria-label={name} className={(p.minus ?? "fill") === id ? "on" : ""} aria-pressed={(p.minus ?? "fill") === id} onClick={() => limit({ minus: id })}>
                {label}
              </button>
            ))}
          </div>
        </>
      )}
      {plus && (
        <label>
          <input type="checkbox" aria-label="Stellenwerte zeigen" checked={!!p.stellen} onChange={(e) => limit({ stellen: e.target.checked })} />
          Stellenwerte zeigen
        </label>
      )}
    </>
  );
}
