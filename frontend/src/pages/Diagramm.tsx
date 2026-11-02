// The format panel for a Diagramm: its kind, its points and what of the chart is drawn.
import { useState } from "react";
import { COLORS, sane, type ChartAxes, type ChartGrid, type ChartKind, type DiagrammProps, type Point, type ValuePlace } from "../diagramm";
import type { DiagrammBlock } from "../sheet";

type Apply = (props: Partial<DiagrammProps>, key?: string) => void;

const KINDS: [ChartKind, string][] = [["saeulen", "Säulen"], ["balken", "Balken"], ["kreis", "Kreis"]];
const PLACES: [ValuePlace, string][] = [["keine", "Keine"], ["innen", "Innen"], ["aussen", "Außen"]];
const AXES: [ChartAxes, string][] = [["keine", "Keine"], ["x", "x-Achse"], ["y", "y-Achse"], ["beide", "Beide"]];
const GRIDS: [ChartGrid, string][] = [["keine", "Keine"], ["haupt", "Hauptschritte"], ["zwischen", "Haupt- und Zwischenschritte"]];
const COLOR_NAME = ["Rot", "Blau", "Grün", "Orange", "Lila", "Schwarz"];

export default function Diagramm({ block, apply }: { block: DiagrammBlock; apply: Apply }) {
  const p = sane(block.props);
  const [at, setAt] = useState(0);
  const index = p.points.length ? Math.min(at, p.points.length - 1) : 0;
  const point = p.points[index];
  const write = (points: Point[]) => apply({ points });
  const replace = (next: Point) => write(p.points.map((item, i) => (i === index ? next : item)));

  return (
    <>
      <h2>Diagramm</h2>
      <label>
        Art
        <select aria-label="Art" value={p.kind} onChange={(e) => apply({ kind: e.target.value as ChartKind })}>
          {KINDS.map(([kind, label]) => <option key={kind} value={kind}>{label}</option>)}
        </select>
      </label>
      <label className="tick">
        <input type="checkbox" aria-label="Legende" checked={p.legend} onChange={() => apply({ legend: !p.legend })} />
        Legende
      </label>
      <label>
        Werte
        <select aria-label="Werte" value={p.values} onChange={(e) => apply({ values: e.target.value as ValuePlace })}>
          {PLACES.map(([place, label]) => <option key={place} value={place}>{label}</option>)}
        </select>
      </label>
      <label>
        Achsen
        <select aria-label="Achsen" value={p.axes} onChange={(e) => apply({ axes: e.target.value as ChartAxes })}>
          {AXES.map(([axes, label]) => <option key={axes} value={axes}>{label}</option>)}
        </select>
      </label>
      {(p.axes === "x" || p.axes === "beide") && (
        <label>
          Titel der x-Achse
          <input aria-label="Titel der x-Achse" value={p.xTitle} onChange={(e) => apply({ xTitle: e.target.value })} />
        </label>
      )}
      {(p.axes === "y" || p.axes === "beide") && (
        <label>
          Titel der y-Achse
          <input aria-label="Titel der y-Achse" value={p.yTitle} onChange={(e) => apply({ yTitle: e.target.value })} />
        </label>
      )}
      <label>
        Hilfslinien
        <select aria-label="Hilfslinien" value={p.grid} onChange={(e) => apply({ grid: e.target.value as ChartGrid })}>
          {GRIDS.map(([grid, label]) => <option key={grid} value={grid}>{label}</option>)}
        </select>
      </label>
      <div className="acts">
        <button
          disabled={p.points.length >= 8}
          onClick={() => {
            write([...p.points, { value: "", label: "", color: COLORS[p.points.length % COLORS.length] }]);
            setAt(p.points.length);
          }}
        >
          Punkt dazu
        </button>
        <button disabled={!point} onClick={() => write(p.points.filter((_, i) => i !== index))}>Punkt löschen</button>
      </div>
      {p.points.length > 1 && (
        <div className="acts">
          {p.points.map((_, i) => (
            <button key={i} aria-pressed={i === index} onClick={() => setAt(i)}>Punkt {i + 1}</button>
          ))}
        </div>
      )}
      {point && (
        <>
          <label>
            Wert
            <input aria-label="Wert" value={point.value} onChange={(e) => replace({ ...point, value: e.target.value })} />
          </label>
          <label>
            Lösung
            <input
              aria-label="Lösung"
              value={point.answer ?? ""}
              onChange={(e) => {
                const answer = e.target.value;
                const next: Point = { value: point.value, label: point.label, color: point.color };
                if (answer) next.answer = answer;
                replace(next);
              }}
            />
          </label>
          <p className="hint">Leer lassen: die Schüler zeichnen den Balken. Die Lösungen zeigen die Lösung.</p>
          <label>
            Beschriftung
            <input aria-label="Beschriftung" value={point.label} onChange={(e) => replace({ ...point, label: e.target.value })} />
          </label>
          <label>
            Farbe
            <select aria-label="Farbe" value={point.color} onChange={(e) => replace({ ...point, color: e.target.value })}>
              {!(COLORS as readonly string[]).includes(point.color) && <option value={point.color}>{point.color}</option>}
              {COLORS.map((color, i) => <option key={color} value={color}>{COLOR_NAME[i]}</option>)}
            </select>
          </label>
        </>
      )}
    </>
  );
}
