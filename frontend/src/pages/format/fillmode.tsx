// Füllung of a closed shape: Keine, Farbe, Muster, Lineatur. A line and a text keep the colour alone.

import { COLOUR, RULE, fillMode, motifOf, paperOf, scaleOf, type Motif, type Paper } from "../../sheet/motif";

const MODES = [
  ["none", "Keine", "Keine Füllung"],
  ["color", "Farbe", "Farbe"],
  ["pattern", "Muster", "Muster"],
  ["ruling", "Lineatur", "Lineatur"],
] as const;
const MOTIFS: [Motif, string][] = [
  ["stripes", "Streifen"],
  ["dots", "Punkte"],
  ["checks", "Kariert"],
  ["waves", "Wellen"],
];
const PAPERS: [Paper, string][] = [
  ["mm", "Millimeterpapier"],
  ["k5", "Karo 5 mm"],
  ["k7", "Karo 7 mm"],
  ["k10", "Karo 10 mm"],
];

type Props = { fill?: string; motif?: unknown; scale?: unknown; mono?: unknown; paper?: unknown };

export default function FillModes({ props, look }: { props: Props; look: (next: object, key?: string) => void }) {
  const mode = fillMode(props);
  const colour = props.fill && props.fill !== "none" ? props.fill : undefined;
  function setMode(next: (typeof MODES)[number][0]) {
    if (next === "none") look({ fill: "none", opacity: undefined, motif: undefined, paper: undefined, scale: undefined, mono: undefined }, "fill");
    else if (next === "color") look({ motif: undefined, paper: undefined, scale: undefined, mono: undefined, ...(colour ? {} : { fill: COLOUR }) }, "fill");
    else if (next === "pattern") look({ paper: undefined, motif: motifOf(props) ?? "stripes", ...(colour ? {} : { fill: COLOUR }) }, "fill");
    else look({ motif: undefined, scale: undefined, mono: undefined, paper: paperOf(props) ?? "mm", ...(colour ? {} : { fill: RULE }) }, "fill");
  }
  return (
    <>
      <div className="seg">
        {MODES.map(([id, label, name]) => (
          <button key={id} type="button" className={mode === id ? "on" : ""} aria-label={id === "none" ? name : undefined} disabled={id === "none" && mode === "none"} onClick={() => setMode(id)}>
            {label}
          </button>
        ))}
      </div>
      {mode === "pattern" && (
        <>
          <div className="seg">
            {MOTIFS.map(([id, label]) => (
              <button key={id} type="button" className={(motifOf(props) ?? "stripes") === id ? "on" : ""} onClick={() => look({ motif: id }, "motif")}>
                {label}
              </button>
            ))}
          </div>
          <label>
            Skalierung
            <input type="range" min={2} max={20} step={1} value={scaleOf(props.scale)} onChange={(e) => look({ scale: +e.target.value }, "scale")} />
          </label>
          <label className="tick">
            <input type="checkbox" checked={props.mono === true} onChange={(e) => look({ mono: e.target.checked || undefined }, "mono")} /> Schwarz-Weiß
          </label>
        </>
      )}
      {mode === "ruling" && (
        <div className="seg">
          {PAPERS.map(([id, label]) => (
            <button key={id} type="button" className={(paperOf(props) ?? "mm") === id ? "on" : ""} onClick={() => look({ paper: id }, "paper")}>
              {label}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
