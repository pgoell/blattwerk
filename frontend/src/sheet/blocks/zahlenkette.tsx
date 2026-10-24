// Draws one Zahlenkette block.

import { numberSize } from "../../zahlenhaus";
import { sane as saneChain, made as chained, layout as chainLayout, stepLabel } from "../../zahlenkette";
import type { ZahlenketteBlock } from "../tasks";

// A Zahlenkette: its chains in columns, in its own units. A ring is a circle, and the arc from one ring to the next
// holds the step. A wrong chain shows no answer and is marked `wrong`.
export function Zahlenkette({ block, solved }: { block: ZahlenketteBlock; k: number; solved: boolean }) {
  const p = saneChain(block.props);
  const { chains } = chained(p);
  const { D, G, A, chainW, chainH, CG, RG, vbW, vbH } = chainLayout(p);
  return (
    <div className={`zahlenkette${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {chains.map((c, i) => {
          const [x, y] = [(i % p.columns) * (chainW + CG), Math.floor(i / p.columns) * (chainH + RG)];
          const top = (j: number) => x + j * (D + G) + D / 2;
          return (
            // A chain that leaves the Zahlenraum is not drawn: its group stays, empty, with the class `over`.
            <g key={i} className={`chain${c.wrong ? " wrong" : ""}${c.over ? " over" : ""}`} data-chain={i}>
              {!c.over && c.numbers.map((n, j) => {
                const shows = c.given[j] || (solved && !c.wrong);
                return (
                  <g key={j} className="ring" data-ring={j}>
                    <circle cx={top(j)} cy={y + A + D / 2} r={D / 2} fill="white" stroke="#222" strokeWidth={0.4} />
                    {shows && (
                      <text x={top(j)} y={y + A + D / 2} fontSize={numberSize(String(n).length, D, 0.55 * D)} textAnchor="middle" dominantBaseline="central"
                        fill={c.given[j] ? "#222" : "#c0392b"} className={c.given[j] ? "given" : "answer"}>{n}</text>
                    )}
                  </g>
                );
              })}
              {!c.over && c.numbers.slice(1).map((_, j) => {
                // The arc from ring j's top centre to ring j+1's, 2.5 units high, with its label above it in the band of A units.
                const [x1, x2, ya] = [top(j), top(j + 1), y + A];
                const xm = (x1 + x2) / 2;
                const shows = p.showStep || (solved && !c.wrong);
                return (
                  <g key={j} className="arc" data-arc={j}>
                    <path d={`M${x1} ${ya} Q${xm} ${ya - 5} ${x2} ${ya}`} fill="none" stroke="#222" strokeWidth={0.4} />
                    {shows && (
                      <text x={xm} y={ya - 4.2} fontSize={3.2} textAnchor="middle" dominantBaseline="central"
                        fill={p.showStep ? "#222" : "#c0392b"} className={p.showStep ? "step" : "answer"}>{stepLabel(p.op, c.step)}</text>
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
