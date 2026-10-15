// The format panel's settings for a Hunderterfeld block: its look, its numbers, its tints and its cut-out.
import { useEffect, useState } from "react";
import type { HunderterfeldBlock } from "../sheet";
import { sane, type HunderterfeldProps } from "../hunderterfeld";
import { newSeed } from "./Maths";

type Apply = (props: Partial<HunderterfeldProps>, key?: string) => void;
type Mode = "hide" | "tint" | "cut" | "fill";

const MODE_LABELS = { hide: "Verdecken", tint: "Färben", cut: "Ausschnitt", fill: "Füllen" } as const;

// A whole number in a field. The field keeps its draft while the number is one `ok` would not take.
function Whole({
  label,
  name,
  value,
  ok,
  apply,
}: {
  label: string;
  name: keyof HunderterfeldProps;
  value: number;
  ok: (v: number) => boolean;
  apply: Apply;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  // An undo or a redo changes the number under the field: the field shows that number, not the draft.
  useEffect(() => setDraft(null), [value]);
  return (
    <label>
      {label}
      <input
        type="number"
        inputMode="numeric"
        aria-label={label}
        value={draft ?? String(value)}
        onChange={(e) => {
          const text = e.target.value;
          setDraft(text);
          if (/^\d+$/.test(text) && ok(Number(text))) apply({ [name]: Number(text) }, name);
        }}
        onBlur={() => setDraft(null)}
      />
    </label>
  );
}

const inRange = (lo: number, hi: number) => (v: number) => v >= lo && v <= hi;

export default function Hunderterfeld({ block, apply }: { block: HunderterfeldBlock; apply: Apply }) {
  const p = sane(block.props);
  const hidden = p.hidden ?? [];
  const tints = p.tints ?? [];
  const shape = p.shape ?? [];
  const filled = p.filled ?? [];
  const tafel = p.look === "tafel";

  // The modes that take a click: the grid shows while one is on, and a select says which a click sets.
  // In a cut-out `show` does not count, so a click cannot hide there.
  const modes: Mode[] = tafel
    ? [...(p.show === "free" && !p.cut ? (["hide"] as Mode[]) : []),...(p.tint === "free" ? (["tint"] as Mode[]) : []), ...(p.cut ? (["cut"] as Mode[]) : [])]
    : p.fill === "free"
      ? ["fill"]
      : [];
  const [chosen, setChosen] = useState<Mode | null>(null);
  const mode = chosen && modes.includes(chosen) ? chosen : modes[0];
  // The given cell as `made` takes it: the stored one in the shape, else the shape's lowest.
  const given = shape.includes(p.given!) ? p.given! : Math.min(...shape);

  const click = (i: number) => {
    if (mode === "hide") {
      apply({ hidden: hidden.includes(i) ? hidden.filter((c) => c !== i) : [...hidden, i] });
    } else if (mode === "tint") {
      const t = tints.find(([c]) => c === i)?.[1];
      const next = t === undefined ? 1 : t === 1 ? 2 : undefined;
      const rest = tints.filter(([c]) => c !== i);
      apply({ tints: next ? [...rest, [i, next]] : rest });
    } else if (mode === "cut") {
      if (!shape.includes(i)) apply({ shape: [...shape, i].sort((a, b) => a - b), ...(shape.length === 0 && { given: i }) });
      else if (given !== i) apply({ given: i });
      else {
        // The given cell leaves the shape and hands its part to the lowest cell left, as `made` would.
        const rest = shape.filter((c) => c !== i);
        apply({ shape: rest, ...(rest.length > 0 && { given: Math.min(...rest) }) });
      }
    } else if (mode === "fill") {
      apply({ filled: filled.includes(i) ? filled.filter((c) => c !== i) : [...filled, i] });
    }
  };

  return (
    <>
      <h2>Hunderterfeld</h2>
      <select aria-label="Darstellung" value={p.look} onChange={(e) => apply({ look: e.target.value as HunderterfeldProps["look"] })}>
        <option value="tafel">Hundertertafel</option>
        <option value="punkte">Punktefeld</option>
      </select>
      <select aria-label="Erste Zahl" value={p.from} onChange={(e) => apply({ from: Number(e.target.value) as 0 | 1 })}>
        <option value="1">1 bis 100</option>
        <option value="0">0 bis 99</option>
      </select>
      {tafel ? (
        <>
          <select aria-label="Zahlen" value={p.show} onChange={(e) => apply({ show: e.target.value as HunderterfeldProps["show"] })}>
            <option value="all">Alle</option>
            <option value="none">Keine</option>
            <option value="random">Zufällig verdeckt</option>
            <option value="free">Selbst verdecken</option>
          </select>
          {p.show === "random" && (
            <>
              <Whole label="Verdeckt" name="hide" value={p.hide} ok={inRange(0, 100)} apply={apply} />
              <button className="wide" onClick={() => apply({ seed: newSeed() })}>
                Neu würfeln
              </button>
            </>
          )}
          <select aria-label="Färben" value={p.tint} onChange={(e) => apply({ tint: e.target.value as HunderterfeldProps["tint"] })}>
            <option value="none">Nicht</option>
            <option value="even">Gerade Zahlen</option>
            <option value="times">Einmaleins-Reihe</option>
            <option value="row">Eine Zeile</option>
            <option value="column">Eine Spalte</option>
            <option value="free">Selbst färben</option>
          </select>
          {p.tint === "times" && <Whole label="Reihe" name="times" value={p.times} ok={inRange(1, 10)} apply={apply} />}
          {(p.tint === "row" || p.tint === "column") && <Whole label="Nummer" name="line" value={p.line} ok={inRange(1, 10)} apply={apply} />}
          {p.tint !== "none" && p.tint !== "free" && (
            <select aria-label="Farbe" value={p.color} onChange={(e) => apply({ color: Number(e.target.value) as 1 | 2 })}>
              <option value="1">Gelb</option>
              <option value="2">Blau</option>
            </select>
          )}
          <label>
            <input type="checkbox" aria-label="Ausschnitt" checked={p.cut} onChange={() => apply({ cut: !p.cut })} />
            Ausschnitt
          </label>
        </>
      ) : (
        <>
          <select aria-label="Füllen" value={p.fill} onChange={(e) => apply({ fill: e.target.value as HunderterfeldProps["fill"] })}>
            <option value="count">Anzahl</option>
            <option value="free">Selbst füllen</option>
          </select>
          {p.fill === "count" && <Whole label="Gefüllt" name="dots" value={p.dots} ok={inRange(0, 100)} apply={apply} />}
        </>
      )}
      {modes.length > 0 && (
        <>
          {modes.length > 1 && (
            <select aria-label="Klick setzt" value={mode} onChange={(e) => setChosen(e.target.value as Mode)}>
              {modes.map((m) => (
                <option key={m} value={m}>
                  {MODE_LABELS[m]}
                </option>
              ))}
            </select>
          )}
          <div className="hundert">
            {Array.from({ length: 100 }, (_, i) => {
              const v = p.from + i;
              const tint = tints.find(([c]) => c === i)?.[1];
              return (
                <button
                  key={i}
                  aria-label={`Feld ${v}`}
                  data-hidden={modes.includes("hide") && hidden.includes(i) ? "" : undefined}
                  data-tint={modes.includes("tint") ? tint : undefined}
                  data-cut={!modes.includes("cut") ? undefined : given === i ? "given" : shape.includes(i) ? "in" : undefined}
                  data-filled={modes.includes("fill") && filled.includes(i) ? "" : undefined}
                  onClick={() => click(i)}
                >
                  {v}
                </button>
              );
            })}
          </div>
        </>
      )}
      {p.cut && shape.length === 0 && <p className="hint">Keine Felder im Ausschnitt: auf die Felder klicken.</p>}
    </>
  );
}
