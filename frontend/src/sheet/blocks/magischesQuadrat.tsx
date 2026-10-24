// Draws one MagischesQuadrat block.

import { sane as saneMagic, made as magicMade, layout as magicLayout } from "../../magischesquadrat";
import { numberSize } from "../../zahlenhaus";
import type { MagischesQuadratBlock } from "../tasks";

// A Magisches Quadrat: its squares side by side. Each has its given numbers on the sheet; in the key the others too,
// unless the square is wrong. A Zielzahl prints above it when shown, and the key notes when other solutions count too.
export function MagischesQuadrat({ block, solved }: { block: MagischesQuadratBlock; solved: boolean }) {
  const p = saneMagic(block.props);
  const { squares } = magicMade(p);
  const { CELL, CG, RG, SUM_H, NOTE_H, top, TW, TH, vbW, vbH } = magicLayout(p);
  return (
    <div className={`magischesquadrat${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {squares.map((s, i) => {
          const [x0, y0] = [(i % p.columns) * (TW + CG), Math.floor(i / p.columns) * (TH + RG)];
          const open = solved && !s.wrong;
          return (
            <g key={i} className={`square${s.wrong ? " wrong" : ""}${s.many ? " many" : ""}`} data-square={i}>
              {p.showSum && !s.wrong && (
                <text className="sum" x={x0 + TW / 2} y={y0 + SUM_H / 2} fontSize={SUM_H * 0.6} textAnchor="middle" dominantBaseline="central">
                  {`Zielzahl: ${s.sum}`}
                </text>
              )}
              {s.cells.map((row, r) =>
                row.map((n, c) => {
                  const [x, y] = [x0 + c * CELL, y0 + top + r * CELL];
                  const state = s.given[r][c] ? "given" : open ? "answer" : null;
                  return (
                    <g key={`${r}:${c}`} className="cell" data-row={r + 1} data-col={c + 1}>
                      <rect x={x} y={y} width={CELL} height={CELL} fill="white" stroke="#222" strokeWidth={0.4} />
                      {state && (
                        <text x={x + CELL / 2} y={y + CELL / 2} fontSize={numberSize(String(n).length, CELL * 0.85, 5)} textAnchor="middle" dominantBaseline="central"
                          fill={state === "given" ? "#222" : "#c0392b"} className={state}>{n}</text>
                      )}
                    </g>
                  );
                }),
              )}
              {solved && s.many && !s.wrong && (
                <text className="note" x={x0 + TW / 2} y={y0 + top + s.size * CELL + NOTE_H / 2} fontSize={Math.min(3.2, TW / 19)} textAnchor="middle" dominantBaseline="central" fill="#c0392b">
                  Auch andere Lösungen sind richtig.
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
