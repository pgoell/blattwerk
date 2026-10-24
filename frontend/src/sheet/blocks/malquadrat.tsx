// Draws one Malquadrat block.

import { sane as saneMalquadrat, made as malquadratMade, layout as malquadratLayout, opLabel as malquadratOp } from "../../malquadrat";
import { numberSize } from "../../zahlenhaus";
import type { MalquadratBlock } from "../tasks";

// A Malquadrat: its squares side by side. The factors sit at the edges, the products inside, the sums outside and the
// total in the corner. Its given numbers show on the sheet; in the key the others too, unless the square is wrong.
export function Malquadrat({ block, solved }: { block: MalquadratBlock; solved: boolean }) {
  const p = saneMalquadrat(block.props);
  const { squares } = malquadratMade(p);
  const { CELL, SG, NOTE_H, CG, RG, TW, TH, vbW, vbH } = malquadratLayout(p);
  const size = p.size;
  const far = size + 1;
  return (
    <div className={`malquadrat${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {squares.map((s, i) => {
          const [x0, y0] = [(i % p.columns) * (TW + CG), Math.floor(i / p.columns) * (TH + RG)];
          const open = solved && !s.wrong;
          const at = (r: number, c: number) => [x0 + c * CELL + (c === far ? SG : 0), y0 + r * CELL + (r === far ? SG : 0)];
          return (
            <g key={i} className={`square${s.wrong ? " wrong" : ""}${s.many ? " many" : ""}`} data-square={i}>
              <g className="corner">
                <rect x={x0} y={y0} width={CELL} height={CELL} fill="#eeeeee" stroke="#222" strokeWidth={0.4} />
                <text className="op" x={x0 + CELL / 2} y={y0 + CELL / 2} fontSize={CELL * 0.7} textAnchor="middle" dominantBaseline="central">
                  {malquadratOp(s.op)}
                </text>
              </g>
              {s.cells.map((row, r) =>
                row.map((v, c) => {
                  if (r === 0 && (c === 0 || c === far)) return null;
                  if (r === far && c === 0) return null;
                  const [x, y] = at(r, c);
                  const sum = r === far || c === far;
                  const state = s.given[r][c] ? "given" : open ? "answer" : null;
                  return (
                    <g key={`${r}:${c}`} className="cell" data-row={r} data-col={c}>
                      <rect x={x} y={y} width={CELL} height={CELL} fill={r === 0 || c === 0 ? "#eeeeee" : "white"} stroke="#222" strokeWidth={sum ? 0.8 : 0.4} />
                      {state && (
                        <text x={x + CELL / 2} y={y + CELL / 2} fontSize={numberSize(String(v).length, CELL * 0.85, 5)} textAnchor="middle" dominantBaseline="central"
                          fill={state === "given" ? "#222" : "#c0392b"} className={state}>{v}</text>
                      )}
                    </g>
                  );
                }),
              )}
              {solved && s.many && !s.wrong && (
                <text className="note" x={x0 + TW / 2} y={y0 + (size + 2) * CELL + SG + NOTE_H / 2} fontSize={Math.min(3.2, TW / 19)} textAnchor="middle" dominantBaseline="central" fill="#c0392b">
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

// A Zerlegungsfeld: its tasks side by side. Each task has four lines of boxes: the task, the split, the first step and
// the second step. The given boxes show on the sheet; in the key the others too, unless the task is wrong.
export const ZERLEGUNG_LINES: [number, number][][] = [
  [[0, 0], [1, 17], [2, 34]],
  [[3, 9], [4, 25]],
  [[0, 0], [3, 17], [5, 34]],
  [[5, 0], [4, 17], [2, 34]],
];
