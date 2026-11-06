// Draws one Stellenwerttafel block.

import { sane, made, layout, placesOf } from "../../stellenwerttafel";
import { SvgInk } from "../places";
import type { StellenwerttafelBlock } from "../tasks";

// The height of a number box and of a move box.
const BOX = 8;

// A Stellenwerttafel: its tasks side by side, each a table of place columns with dots (Plättchen) and the line under
// it (the number box with its sign, or the boxes of the moves). The key adds the answers. Its layout is the contract's.
export function Stellenwerttafel({ block, solved }: { block: StellenwerttafelBlock; solved: boolean }) {
  const p = sane(block.props);
  const { tasks } = made(p);
  const { CW, HH, BH, TBW, TBH, R, SW, NB, G, TW, TH, CG, RG, across, vbW, vbH } = layout(p);
  const places = placesOf(p);
  const kind = p.task;
  return (
    <div className={`stellenwerttafel${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        <g transform="translate(0.5 0.5)">
          {tasks.map((t, i) => {
            const x0 = (i % across) * (TW + CG);
            const y0 = Math.floor(i / across) * (TH + RG);
            const bodyTop = y0 + HH;
            // A wrong or empty task shows no dot, number or move; the key shows the answers of the rest.
            const shown = !t.wrong && !t.none;
            const answered = solved && shown;
            // The middle of the body, where the sign and the number box sit.
            const mid = bodyTop + BH / 2;
            return (
              <g key={i} className={`task${t.wrong ? " wrong" : ""}${t.none ? " none" : ""}`} data-task={i}>
                <g className="table">
                  {places.map((pl, j) => {
                    const colLeft = x0 + j * CW;
                    return (
                      <g key={pl.v}>
                        <rect x={colLeft} y={y0} width={CW} height={HH} fill="white" stroke="#222" strokeWidth={0.3} />
                        <text className="head" x={colLeft + CW / 2} y={y0 + HH / 2} fontSize={4} fill="#222" textAnchor="middle" dominantBaseline="central">
                          {pl.letter}
                        </text>
                        <g className="cell" data-v={pl.v}>
                          <rect x={colLeft} y={bodyTop} width={CW} height={BH} fill="white" stroke="#222" strokeWidth={0.3} />
                        </g>
                      </g>
                    );
                  })}
                </g>
                {shown &&
                  (kind !== "lay" || solved) &&
                  places.map((pl, j) =>
                    Array.from({ length: t.digits[j] }, (_, q) => {
                      const cx = x0 + j * CW + 4 + (q % 3) * 4;
                      const cy = bodyTop + 3 + Math.floor(q / 3) * 4;
                      const answer = kind === "lay";
                      return (
                        <circle
                          key={`${pl.v}-${q}`}
                          className={answer ? "dot answer" : "dot"}
                          data-v={pl.v}
                          cx={cx}
                          cy={cy}
                          r={R}
                          fill={answer ? "#c0392b" : "#222"}
                        />
                      );
                    }),
                  )}
                {kind !== "move" && (
                  <>
                    <text className="eq" x={x0 + TBW + SW / 2} y={mid} fontSize={5.5} fill="#222" textAnchor="middle" dominantBaseline="central">
                      =
                    </text>
                    <g className="slot">
                      <rect x={x0 + TBW + SW} y={mid - BOX / 2} width={NB} height={BOX} fill="white" stroke="#222" strokeWidth={0.3} />
                      {(kind === "lay" ? shown : answered) && (
                        <text
                          className={kind === "lay" ? "given" : "answer"}
                          x={x0 + TBW + SW + NB / 2}
                          y={mid}
                          fontSize={5.5}
                          fill={kind === "lay" ? "#222" : "#c0392b"}
                          textAnchor="middle"
                          dominantBaseline="central"
                        >
                          <SvgInk text={t.n} />
                        </text>
                      )}
                    </g>
                  </>
                )}
                {kind === "move" &&
                  Array.from({ length: places.length * (places.length - 1) }, (_, b) => {
                    const bx = x0 + (b % places.length) * CW;
                    const by = y0 + TBH + G + Math.floor(b / places.length) * (BOX + 2);
                    return (
                      <g key={b} className="slot">
                        <rect className="box" x={bx} y={by} width={CW} height={BOX} fill="white" stroke="#222" strokeWidth={0.3} />
                        {answered && b < t.moves.length && (
                          <text className="answer" x={bx + CW / 2} y={by + BOX / 2} fontSize={5.5} fill="#c0392b" textAnchor="middle" dominantBaseline="central">
                            <SvgInk text={t.moves[b]} />
                          </text>
                        )}
                      </g>
                    );
                  })}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
