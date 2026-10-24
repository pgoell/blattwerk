// Draws one Zerlegungsfeld block.

import { numberSize } from "../../zahlenhaus";
import { sane as saneZerlegungsfeld, made as zerlegungsfeldMade, layout as zerlegungsfeldLayout, opLabel as zerlegungsfeldOp } from "../../zerlegungsfeld";
import type { ZerlegungsfeldBlock } from "../tasks";
import { ZERLEGUNG_LINES } from "./malquadrat";

export const ZERLEGUNG_LINE_Y = [0, 14, 26, 38];
export function Zerlegungsfeld({ block, solved }: { block: ZerlegungsfeldBlock; solved: boolean }) {
  const p = saneZerlegungsfeld(block.props);
  const { tasks } = zerlegungsfeldMade(p);
  const { BW, BH, CG, RG, TW, TH, NOTE_H, vbW, vbH } = zerlegungsfeldLayout(p);
  return (
    <div className={`zerlegungsfeld${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {tasks.map((t, i) => {
          const [x0, y0] = [(i % p.columns) * (TW + CG), Math.floor(i / p.columns) * (TH + RG)];
          const open = solved && !t.wrong;
          return (
            <g key={i} className={`task${t.wrong ? " wrong" : ""}${t.many ? " many" : ""}`} data-task={i}>
              {ZERLEGUNG_LINES.map((line, l) => {
                const y = y0 + ZERLEGUNG_LINE_Y[l];
                return (
                  <g key={l}>
                    {line.map(([pos, dx]) => {
                      const x = x0 + dx;
                      const state = t.given[pos] ? "given" : open ? "answer" : null;
                      return (
                        <g key={pos} className="box" data-pos={pos} data-line={l}>
                          <rect x={x} y={y} width={BW} height={BH} fill="white" stroke="#222" strokeWidth={0.4} />
                          {state && (
                            <text x={x + BW / 2} y={y + BH / 2} fontSize={numberSize(String(t.values[pos]).length, BW * 0.85, 5)} textAnchor="middle" dominantBaseline="central"
                              fill={state === "given" ? "#222" : "#c0392b"} className={state}>{t.values[pos]}</text>
                          )}
                        </g>
                      );
                    })}
                    {l !== 1 && (
                      <>
                        <text className="op" x={x0 + 14.5} y={y + BH / 2} fontSize={BH * 0.85} textAnchor="middle" dominantBaseline="central">{zerlegungsfeldOp(t.op)}</text>
                        <text className="eq" x={x0 + 31.5} y={y + BH / 2} fontSize={BH * 0.85} textAnchor="middle" dominantBaseline="central">=</text>
                      </>
                    )}
                  </g>
                );
              })}
              <line className="branch" x1={x0 + 23} y1={y0 + 8} x2={x0 + 15} y2={y0 + 14} stroke="#222" strokeWidth={0.4} />
              <line className="branch" x1={x0 + 23} y1={y0 + 8} x2={x0 + 31} y2={y0 + 14} stroke="#222" strokeWidth={0.4} />
              {solved && t.many && !t.wrong && (
                <text className="note" x={x0 + TW / 2} y={y0 + TH - NOTE_H / 2} fontSize={Math.min(3.2, TW / 19)} textAnchor="middle" dominantBaseline="central" fill="#c0392b">
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
