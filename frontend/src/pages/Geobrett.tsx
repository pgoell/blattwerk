// The format panel for a Geobrett: its size, its task, its figures and the band in hand.
import { useEffect, useState, type KeyboardEvent } from "react";
import { ASK, COLORS, figures, mirrored, moved, sane, scaled, turned, type Band, type GeobrettProps, type Aufgabe } from "../geobrett";
import type { GeobrettBlock } from "../sheet";

type Apply = (props: Partial<GeobrettProps>, key?: string) => void;

const TASKS: [Aufgabe, string][] = [
  ["leer", "Leeres Brett"],
  ["spiegel", "Spiegelbild ergänzen"],
  ["achsen", "Spiegelachsen finden"],
  ["drehung", "Drehung um 90°"],
  ["winkel", "Rechte Winkel finden"],
  ["parallelen", "Parallelen finden"],
  ["flaeche", "Flächeninhalt"],
  ["umfang", "Umfang"],
  ["koordinaten", "Koordinaten"],
];
const COLOR_NAME = ["Rot", "Blau", "Grün", "Orange", "Lila", "Schwarz"];

function Whole({ label, value, ok, onChange }: { label: string; value: number; ok: (v: number) => boolean; onChange: (v: number) => void }) {
  const [draft, setDraft] = useState<string | null>(null);
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
          if (/^\d+$/.test(text) && ok(Number(text))) onChange(Number(text));
        }}
        onBlur={() => setDraft(null)}
      />
    </label>
  );
}

const fits = (v: number) => v >= 2 && v <= 12;

function span(bands: Band[]): [number, number] {
  const nails = bands.flatMap((b) => b.nails);
  if (!nails.length) return [0, 0];
  return [1 + Math.max(...nails.map((n) => n[0])), 1 + Math.max(...nails.map((n) => n[1]))];
}

export default function Geobrett({ block, apply }: { block: GeobrettBlock; apply: Apply }) {
  const p = sane(block.props);
  const [at, setAt] = useState(0);
  const band = p.bands[at] ?? p.bands[0];
  const index = band ? p.bands.indexOf(band) : 0;
  const gallery = figures(p.task);

  const write = (bands: Band[]) => apply({ bands, figure: undefined });
  const replace = (next: Band) => {
    if (next === band) return;
    write(p.bands.map((b, i) => (i === index ? next : b)));
  };
  const choose = (task: Aufgabe) => {
    const figure = figures(task)[0];
    if (!figure) {
      apply({ task, bands: [], figure: undefined, axis: undefined, centre: undefined });
      return;
    }
    const [cols, rows] = span(figure.bands);
    apply({ task, figure: 0, bands: figure.bands, axis: figure.axis, centre: figure.centre, cols: Math.max(p.cols, cols), rows: Math.max(p.rows, rows) });
  };
  const onKey = (e: KeyboardEvent) => {
    if (!band || (e.target instanceof HTMLElement && e.target.matches("input, select, textarea"))) return;
    const next =
      e.key === "ArrowLeft" ? moved(band, -1, 0, p.cols, p.rows)
      : e.key === "ArrowRight" ? moved(band, 1, 0, p.cols, p.rows)
      : e.key === "ArrowUp" ? moved(band, 0, -1, p.cols, p.rows)
      : e.key === "ArrowDown" ? moved(band, 0, 1, p.cols, p.rows)
      : e.key === "r" || e.key === "R" ? turned(band, p.cols, p.rows)
      : e.key === "x" || e.key === "X" ? mirrored(band, "x")
      : e.key === "y" || e.key === "Y" ? mirrored(band, "y")
      : e.key === "+" || e.key === "=" ? scaled(band, 2, p.cols, p.rows)
      : e.key === "-" ? scaled(band, 0.5, p.cols, p.rows)
      : undefined;
    if (!next) return;
    e.preventDefault();
    e.stopPropagation();
    replace(next);
  };

  return (
    <>
      <h2>Geobrett</h2>
      <select aria-label="Aufgabe" value={p.task} onChange={(e) => choose(e.target.value as Aufgabe)}>
        {TASKS.map(([task, label]) => (
          <option key={task} value={task}>{label}</option>
        ))}
      </select>
      {p.task !== "leer" && <p className="hint">{ASK[p.task]}</p>}
      {gallery.length > 0 && (
        <div className="acts">
          {gallery.map((_, i) => (
            <button key={i} aria-pressed={p.figure === i} onClick={() => {
              const figure = gallery[i];
              const [cols, rows] = span(figure.bands);
              apply({ figure: i, bands: figure.bands, axis: figure.axis, centre: figure.centre, cols: Math.max(p.cols, cols), rows: Math.max(p.rows, rows) });
            }}>
              Figur {i + 1}
            </button>
          ))}
        </div>
      )}
      <Whole label="Nägel breit" value={p.cols} ok={fits} onChange={(cols) => apply({ cols }, "cols")} />
      <Whole label="Nägel hoch" value={p.rows} ok={fits} onChange={(rows) => apply({ rows }, "rows")} />
      {p.task === "spiegel" && (
        <>
          <select
            aria-label="Achse"
            value={p.axis?.dir === "h" ? "h" : "v"}
            onChange={(e) => apply({ axis: { dir: e.target.value as "v" | "h", at: p.axis?.dir === e.target.value ? p.axis.at : 0 }, figure: undefined })}
          >
            <option value="v">Senkrecht</option>
            <option value="h">Waagerecht</option>
          </select>
          <Whole
            label={p.axis?.dir === "h" ? "Zeile" : "Spalte"}
            value={p.axis && (p.axis.dir === "v" || p.axis.dir === "h") ? p.axis.at : 0}
            ok={(v) => v >= 0 && v < (p.axis?.dir === "h" ? p.rows : p.cols)}
            onChange={(at) => apply({ axis: { dir: p.axis?.dir === "h" ? "h" : "v", at }, figure: undefined }, "axis")}
          />
        </>
      )}
      {p.task === "drehung" && (
        <>
          <Whole label="Drehpunkt Spalte" value={p.centre?.[0] ?? Math.floor((p.cols - 1) / 2)} ok={(v) => v >= 0 && v < p.cols} onChange={(c) => apply({ centre: [c, p.centre?.[1] ?? Math.floor((p.rows - 1) / 2)], figure: undefined }, "centre")} />
          <Whole label="Drehpunkt Zeile" value={p.centre?.[1] ?? Math.floor((p.rows - 1) / 2)} ok={(v) => v >= 0 && v < p.rows} onChange={(r) => apply({ centre: [p.centre?.[0] ?? Math.floor((p.cols - 1) / 2), r], figure: undefined }, "centre")} />
        </>
      )}
      <div className="acts">
        <button onClick={() => {
          const color = COLORS[p.bands.length % COLORS.length];
          write([...p.bands, { nails: [[0, 0], [Math.min(1, p.cols - 1), 0]], color, fill: false }]);
          setAt(p.bands.length);
        }}>Band dazu</button>
        <button disabled={!band} onClick={() => write(p.bands.filter((_, i) => i !== index))}>Band löschen</button>
      </div>
      {p.bands.length > 1 && (
        <div className="acts">
          {p.bands.map((_, i) => (
            <button key={i} aria-pressed={i === index} onClick={() => setAt(i)}>Band {i + 1}</button>
          ))}
        </div>
      )}
      {band && (
        <>
          <select aria-label="Bandfarbe" value={band.color} onChange={(e) => replace({ ...band, color: e.target.value })}>
            {COLORS.map((color, i) => (
              <option key={color} value={color}>{COLOR_NAME[i]}</option>
            ))}
          </select>
          <label className="tick">
            <input type="checkbox" aria-label="Gefüllt" checked={band.fill} onChange={() => replace({ ...band, fill: !band.fill })} />
            Gefüllt
          </label>
          <div className="naegel" tabIndex={0} aria-label="Nägel" onKeyDown={onKey} style={{ gridTemplateColumns: `repeat(${p.cols}, minmax(0, 1fr))` }}>
            {Array.from({ length: p.rows * p.cols }, (_, i) => {
              const [c, r] = [i % p.cols, Math.floor(i / p.cols)];
              const on = band.nails.some(([x, y]) => x === c && y === r);
              return (
                <button
                  key={i}
                  type="button"
                  aria-label={`Nagel ${c} ${r}`}
                  data-on={on ? "" : undefined}
                  onClick={() => {
                    const last = band.nails[band.nails.length - 1];
                    if (last && last[0] === c && last[1] === r) return;
                    replace({ ...band, nails: [...band.nails, [c, r]] });
                  }}
                />
              );
            })}
          </div>
          <div className="acts">
            <button onClick={() => replace(moved(band, -1, 0, p.cols, p.rows))}>Nach links</button>
            <button onClick={() => replace(moved(band, 1, 0, p.cols, p.rows))}>Nach rechts</button>
          </div>
          <div className="acts">
            <button onClick={() => replace(moved(band, 0, -1, p.cols, p.rows))}>Nach oben</button>
            <button onClick={() => replace(moved(band, 0, 1, p.cols, p.rows))}>Nach unten</button>
          </div>
          <div className="acts">
            <button onClick={() => replace(turned(band, p.cols, p.rows))}>Drehen</button>
            <button onClick={() => replace(scaled(band, 2, p.cols, p.rows))}>Größer</button>
            <button onClick={() => replace(scaled(band, 0.5, p.cols, p.rows))}>Kleiner</button>
          </div>
          <div className="acts">
            <button onClick={() => replace(mirrored(band, "x"))}>Links-rechts</button>
            <button onClick={() => replace(mirrored(band, "y"))}>Oben-unten</button>
          </div>
          <button className="wide" disabled={band.nails.length < 2} onClick={() => {
            if (band.nails.length > 2) replace({ ...band, nails: band.nails.slice(0, -1) });
            else write(p.bands.filter((_, i) => i !== index));
          }}>Nagel weg</button>
          <p className="hint">Pfeiltasten verschieben, R dreht, X spiegelt links-rechts, Y spiegelt oben-unten, Plus vergrößert und Minus verkleinert, solange die Nägel den Fokus haben.</p>
        </>
      )}
    </>
  );
}
