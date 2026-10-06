import { Count, LOOKS, counts, lookOf } from "../sheet";

// Picks a numbering: numbers or letters, then the look. `symbol` is there where a symbol can stand in for a count.
export default function Numbering({ value, onChange, symbol }: { value?: string; onChange: (mark?: string) => void; symbol?: () => void }) {
  const kind = counts(value) ? (value.includes("1") ? "1" : "a") : "";
  return (
    <>
      <div className="seg">
        <button className={value ? "" : "on"} onClick={() => onChange()}>Keine</button>
        {[["1", "1 2 3"], ["a", "a b c"]].map(([to, label]) => (
          // A change between numbers and letters keeps the look.
          <button key={to} className={kind === to ? "on" : ""} onClick={() => onChange((counts(value) ? lookOf(value) : "#.").replace("#", to))}>
            {label}
          </button>
        ))}
        {symbol && <button className={value && !kind ? "on" : ""} onClick={symbol}>Symbol</button>}
      </div>
      {kind && (
        <div className="seg">
          {LOOKS.map((look) => look.replace("#", kind)).map((mark) => (
            <button key={mark} className={value === mark ? "on" : ""} aria-pressed={value === mark} onClick={() => onChange(mark)}>
              <Count mark={mark} n={1} />
            </button>
          ))}
        </div>
      )}
    </>
  );
}
