// The format panel for a Karofeld: its look, its square size, and the square the caret is in.
import type { KarofeldBlock } from "../sheet";
import {
  deletedRow,
  deletedSign,
  insertedRow,
  insertedSign,
  painted,
  sane,
  type KarofeldProps,
  type Look,
} from "../karofeld";

type Apply = (props: Partial<KarofeldProps>, key?: string) => void;

const LOOKS: [Look, string][] = [
  ["karos", "Karos"],
  ["kreise", "Kreise"],
  ["punkte", "Punktefeld"],
  ["iso", "Isometrisches Gitter"],
];
const SIDES = ["Oben", "Rechts", "Unten", "Links"];

export default function Karofeld({ block, apply }: { block: KarofeldBlock; apply: Apply }) {
  const p = sane(block.props);
  const [c, r] = p.caret ?? [0, 0];
  const sq = p.cells?.[r]?.[c] ?? {};
  const thick = sq.thick ?? [false, false, false, false];
  const put = (props: KarofeldProps, key: string) => apply(props, key);
  const setSize = (text: string) => {
    const n = Number(text);
    if (Number.isInteger(n) && n >= 4 && n <= 16) apply({ size: n }, "size");
  };
  return (
    <>
      <h2>Karofeld</h2>
      <select aria-label="Darstellung" value={p.look} onChange={(e) => apply({ look: e.target.value as Look }, "look")}>
        {LOOKS.map(([look, label]) => (
          <option key={look} value={look}>
            {label}
          </option>
        ))}
      </select>
      <label>
        Kästchengröße
        <input type="number" inputMode="numeric" aria-label="Kästchengröße" min={4} max={16} value={p.size} onChange={(e) => setSize(e.target.value)} />
        mm
      </label>
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.cols <= 1} onClick={() => apply({ cols: p.cols - 1 }, "cols")}>
          −
        </button>
        <output>{p.cols} Spalten</output>
        <button aria-label="Eine Spalte mehr" disabled={p.cols >= 30} onClick={() => apply({ cols: p.cols + 1 }, "cols")}>
          ＋
        </button>
      </div>
      <div className="seg">
        <button aria-label="Eine Zeile weniger" disabled={p.rows <= 1} onClick={() => apply({ rows: p.rows - 1 }, "rows")}>
          −
        </button>
        <output>{p.rows} Zeilen</output>
        <button aria-label="Eine Zeile mehr" disabled={p.rows >= 40} onClick={() => apply({ rows: p.rows + 1 }, "rows")}>
          ＋
        </button>
      </div>
      <button onClick={() => put(insertedSign(p), "sign")}>Zeichen einfügen</button>
      <button onClick={() => put(deletedSign(p), "sign")}>Zeichen löschen</button>
      <button onClick={() => put(insertedRow(p), "row")}>Zeile einfügen</button>
      <button onClick={() => put(deletedRow(p), "row")} disabled={p.rows <= 1}>
        Zeile löschen
      </button>
      <p className="hint">
        Kästchen {c + 1}, {r + 1}. Tippen setzt eine Ziffer oder ein Zeichen und rückt weiter. Enter springt in die nächste Zeile.
      </p>
      <button className={sq.line ? "on" : ""} aria-pressed={!!sq.line} onClick={() => put(painted(p, { line: !sq.line }), "line")}>
        Lösungsstrich
      </button>
      <select
        aria-label="Komma oder Punkt"
        value={sq.mark ?? ""}
        onChange={(e) => put(painted(p, { mark: e.target.value === "" ? null : (e.target.value as "," | ".") }), "mark")}
      >
        <option value="">Kein Komma</option>
        <option value=",">Komma</option>
        <option value=".">Punkt</option>
      </select>
      <label>
        Hintergrund
        <input
          type="color"
          aria-label="Hintergrund"
          value={sq.fill ?? "#ffffff"}
          onChange={(e) => put(painted(p, { fill: e.target.value }), "fill")}
        />
      </label>
      <button onClick={() => put(painted(p, { fill: null }), "fill")}>Keine Farbe</button>
      {SIDES.map((label, i) => (
        <button
          key={label}
          className={thick[i] ? "on" : ""}
          aria-pressed={thick[i]}
          onClick={() => {
            const next = [...thick];
            next[i] = !next[i];
            put(painted(p, { thick: next }), "thick");
          }}
        >
          Rand {label}
        </button>
      ))}
    </>
  );
}
