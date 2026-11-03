// Patterns for the two numbers and the result, and the zero switch of each operation family.
import { useState } from "react";
import { SIGNS, type Limits, type MathsProps } from "../../sheet";

const fixed = (pattern: string) => pattern.length > 0 && !pattern.includes("X");
const textOf = (raw: string) => raw.toUpperCase().replace(/[^0-9X]/g, "").slice(0, 7);

export default function Muster({
  p,
  limit,
  plus,
  times,
  decimals,
}: {
  p: MathsProps;
  limit: (change: Partial<Limits>) => void;
  plus: boolean;
  times: boolean;
  decimals: boolean;
}) {
  // Bumped when a third fixed number is refused, so the field shows the pattern that is in use.
  const [rev, setRev] = useState(0);
  const patterns = { pa: p.pa ?? "", pb: p.pb ?? "", pr: p.pr ?? "" };

  function setPattern(key: "pa" | "pb" | "pr", raw: string) {
    const text = textOf(raw);
    const next = { ...patterns, [key]: text };
    const shown = p.format === "compare" ? [next.pa, next.pb] : [next.pa, next.pb, next.pr];
    if (shown.filter(fixed).length > 2) {
      setRev((n) => n + 1);
      return;
    }
    limit({ [key]: text });
  }

  function field(key: "pa" | "pb" | "pr", label: string, name: string, hint: string) {
    return (
      <label key={`${key}${rev}`}>
        {label}
        <input
          aria-label={name}
          type="text"
          spellCheck={false}
          placeholder={hint}
          disabled={decimals}
          value={patterns[key]}
          onChange={(e) => setPattern(key, e.target.value)}
        />
      </label>
    );
  }

  function zero(family: "strich" | "punkt", name: string, label: string) {
    const on = p.nil?.[family] !== false;
    return (
      <button
        key={family}
        aria-label={name}
        className={on ? "on" : ""}
        aria-pressed={on}
        disabled={decimals}
        onClick={() => limit({ nil: { ...p.nil, [family]: !on } })}
      >
        {label}
      </button>
    );
  }

  return (
    <>
      <h2>Muster</h2>
      {field("pa", "1. Zahl", "Muster der 1. Zahl", "z. B. X0")}
      {field("pb", "2. Zahl", "Muster der 2. Zahl", "z. B. X")}
      {p.format !== "compare" && field("pr", "Ergebnis", "Muster des Ergebnisses", "z. B. 100")}
      <p className="hint" role="status">
        Höchstens zwei der drei Zahlen können feststehen.
      </p>
      {decimals && <p className="hint">Muster gelten für ganze Zahlen.</p>}
      {(plus || times) && (
        <>
          <h2>Die Null darf vorkommen</h2>
          <div className="seg switch">
            {plus && zero("strich", `Die Null darf bei + und ${SIGNS["-"]} vorkommen`, `+ und ${SIGNS["-"]}`)}
            {times && zero("punkt", "Die Null darf bei · und : vorkommen", "· und :")}
          </div>
        </>
      )}
    </>
  );
}
