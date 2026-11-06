// Draws one Zahlzerlegung block.

import { sane, made, items, layout, type Item } from "../../zahlzerlegung";
import { SvgInk } from "../places";
import type { ZahlzerlegungBlock } from "../tasks";

// A Zahlzerlegung: its tasks side by side, each a line of numbers, signs, place letters and gaps. The key writes the
// answers into the gaps. Its layout is the contract's.
export function Zahlzerlegung({ block, solved }: { block: ZahlzerlegungBlock; solved: boolean }) {
  const p = sane(block.props);
  const { tasks } = made(p);
  const { LH, RG, CG, TW, NW, across, vbW, vbH } = layout(p);
  // A whole number takes the sheet's place colours; a count before its letter ("12 Z") does not.
  const ink = (it: Item) => (it.w === NW ? <SvgInk text={it.text} /> : it.text);
  return (
    <div className={`zahlzerlegung${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        <g transform="translate(0.5 0.5)">
          {tasks.map((t, i) => {
            const x0 = (i % across) * (TW + CG);
            const y0 = Math.floor(i / across) * (LH + RG);
            return (
              <g key={i} className={`task${t.wrong ? " wrong" : ""}`} data-task={i}>
                {items(p, t).map((it, j) => {
                  const x = x0 + it.x;
                  if (it.kind === "gap")
                    return (
                      <g key={j}>
                        <rect className="gap" x={x} y={y0} width={it.w} height={8} fill="white" stroke="#222" strokeWidth={0.3} />
                        {solved && it.text !== "" && (
                          <text className="answer" x={x + it.w / 2} y={y0 + 6} fontSize={5.5} fill="#c0392b" textAnchor="middle">
                            {ink(it)}
                          </text>
                        )}
                      </g>
                    );
                  const cls = it.kind === "given" ? "given" : it.kind === "sign" ? "eq" : "letter";
                  return (
                    <text key={j} className={cls} x={x + it.w / 2} y={y0 + 6} fontSize={5.5} fill="#222" textAnchor="middle">
                      {it.kind === "given" ? ink(it) : it.text}
                    </text>
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
