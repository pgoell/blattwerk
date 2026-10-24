// Draws one Suchsel block.

import { PT } from "../../height";
import { sane, laid } from "../../suchsel";
import type { SuchselBlock } from "../tasks";

// A word search: squared paper with a letter to a square, the hidden words ringed once solved, and the words or
// their count under the grid. It draws in its own units, so it scales to the room its block gives it. A square is
// `S` units wide: with a square of one unit the letters are under a unit high, and Chromium sets so small a type a
// whole square too high.
export function Suchsel({ block, k, solved }: { block: SuchselBlock; k: number; solved: boolean }) {
  const p = sane(block.props);
  const { grid, hidden } = laid(p);
  const S = 10;
  const [wide, high] = [p.cols * S, p.rows * S];
  const each = (n: number) => Array.from({ length: n - 1 }, (_, i) => (i + 1) * S);
  return (
    <div className={`suchsel${solved ? " solved" : ""}`} style={{ fontSize: 12 * PT * k }}>
      <svg viewBox={`0 0 ${wide} ${high}`} preserveAspectRatio="xMidYMin meet" style={{ aspectRatio: `${p.cols} / ${p.rows}` }}>
        <g className="mesh" stroke="#9db4c8" strokeWidth={0.3}>
          {each(p.cols).map((x) => <line key={`x${x}`} x1={x} x2={x} y1={0} y2={high} />)}
          {each(p.rows).map((y) => <line key={`y${y}`} x1={0} x2={wide} y1={y} y2={y} />)}
        </g>
        <rect className="edge" x={0} y={0} width={wide} height={high} fill="none" stroke="#222" strokeWidth={0.6} />
        {grid.map((row, r) => row.map((letter, c) => (
          <text key={`${c},${r}`} data-at={`${c},${r}`} x={(c + 0.5) * S} y={(r + 0.5) * S} fontSize={0.62 * S} textAnchor="middle" dominantBaseline="central" fill="#222">{letter}</text>
        )))}
        {solved && hidden.map((h) => {
          const n = h.letters.length;
          const length = ((n - 1) * Math.hypot(h.dc, h.dr) + 0.8) * S;
          const cx = (h.col + 0.5 + (h.dc * (n - 1)) / 2) * S;
          const cy = (h.row + 0.5 + (h.dr * (n - 1)) / 2) * S;
          const angle = (Math.atan2(h.dr, h.dc) * 180) / Math.PI;
          return (
            <rect key={`${h.word}${h.col},${h.row}`} className="ring answer" data-word={h.word} data-col={h.col} data-row={h.row} data-dc={h.dc} data-dr={h.dr} data-n={n}
              x={cx - length / 2} y={cy - 0.4 * S} width={length} height={0.8 * S} rx={0.4 * S} ry={0.4 * S} strokeWidth={0.6} transform={`rotate(${angle} ${cx} ${cy})`} />
          );
        })}
      </svg>
      {p.show === "words" && hidden.length > 0 && (
        <ul className="found">{hidden.map((h) => <li key={`${h.word}${h.col},${h.row}`}>{h.word}</li>)}</ul>
      )}
      {p.show === "count" && hidden.length > 0 && (
        <p className="found">Finde {hidden.length} {hidden.length === 1 ? "Wort" : "Wörter"}.</p>
      )}
    </div>
  );
}
