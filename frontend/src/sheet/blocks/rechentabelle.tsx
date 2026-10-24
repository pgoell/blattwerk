// Draws one Rechentabelle block.

import { sane as saneTable, made as tableMade, layout as tableLayout, TINT as tableTint, opLabel as tableLabel } from "../../rechentabelle";
import { numberSize } from "../../zahlenhaus";
import type { RechentabelleBlock } from "../tasks";

// A Rechentabelle: its tables side by side. Each has the operator in its corner, the row values down the left, the column
// values along the top and the result cells; a number shows when it is given, or in the key when the table is solved and
// not wrong. A struck cell has a line, a made-up cell stays empty.
export function Rechentabelle({ block, solved }: { block: RechentabelleBlock; solved: boolean }) {
  const p = saneTable(block.props);
  const { tables } = tableMade(p);
  const { CELL, CG, RG, TW, TH, vbW, vbH } = tableLayout(p);
  const tint = p.tint === "none" ? null : tableTint[p.tint];
  return (
    <div className={`rechentabelle${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {tables.map((t, i) => {
          const [x0, y0] = [(i % p.columns) * (TW + CG), Math.floor(i / p.columns) * (TH + RG)];
          const open = solved && !t.wrong;
          const stateOf = (given: boolean): "given" | "answer" | null => (given ? "given" : open ? "answer" : null);
          const text = (n: number, x: number, y: number, state: "given" | "answer" | null) =>
            state && (
              <text x={x + CELL / 2} y={y + CELL / 2} fontSize={numberSize(String(n).length, CELL * 0.85, 5)} textAnchor="middle" dominantBaseline="central"
                fill={state === "given" ? "#222" : "#c0392b"} className={state}>{n}</text>
            );
          return (
            <g key={i} className={`table${t.wrong ? " wrong" : ""}`} data-table={i}>
              <g className="corner">
                <rect x={x0} y={y0} width={CELL} height={CELL} fill={tint ? tint[1] : "white"} stroke="#222" strokeWidth={0.4} />
                <text x={x0 + CELL / 2} y={y0 + CELL / 2} fontSize={numberSize(1, CELL * 0.85, 5)} textAnchor="middle" dominantBaseline="central"
                  fill="#222" className="given">{tableLabel(p.op)}</text>
              </g>
              {t.cols.map((n, j) => {
                const [x, y] = [x0 + (j + 1) * CELL, y0];
                return (
                  <g key={`c${j}`} className="head" data-row={0} data-col={j + 1}>
                    <rect x={x} y={y} width={CELL} height={CELL} fill={tint ? tint[0] : "white"} stroke="#222" strokeWidth={0.4} />
                    {text(n, x, y, stateOf(t.colShown[j]))}
                  </g>
                );
              })}
              {t.rows.map((n, r) => {
                const [x, y] = [x0, y0 + (r + 1) * CELL];
                return (
                  <g key={`r${r}`} className="head" data-row={r + 1} data-col={0}>
                    <rect x={x} y={y} width={CELL} height={CELL} fill={tint ? tint[0] : "white"} stroke="#222" strokeWidth={0.4} />
                    {text(n, x, y, stateOf(t.rowShown[r]))}
                  </g>
                );
              })}
              {t.cells.map((row, r) =>
                row.map((n, c) => {
                  const [x, y] = [x0 + (c + 1) * CELL, y0 + (r + 1) * CELL];
                  return (
                    <g key={`${r}:${c}`} className="cell" data-row={r + 1} data-col={c + 1}>
                      <rect x={x} y={y} width={CELL} height={CELL} fill="white" stroke="#222" strokeWidth={0.4} />
                      {t.struck[r][c] ? (
                        <line className="strike" x1={x} y1={y} x2={x + CELL} y2={y + CELL} stroke="#222" strokeWidth={0.4} />
                      ) : t.madeUp[r][c] ? null : (
                        text(n, x, y, stateOf(t.given[r][c]))
                      )}
                    </g>
                  );
                }),
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
