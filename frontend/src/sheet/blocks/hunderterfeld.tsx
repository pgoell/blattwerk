// Draws one Hunderterfeld block.

import { sane as saneFeld, made as drawnFeld, dotAt, TINT } from "../../hunderterfeld";
import type { HunderterfeldBlock } from "../tasks";

// A Hunderterfeld, drawn as the contract at the top of hunderterfeld.ts says. Its lines are 0.3 and its outer frame
// 0.6 of a 100 field, so they keep that share when a cut-out makes the field smaller.
export function Hunderterfeld({ block, solved }: { block: HunderterfeldBlock; k: number; solved: boolean }) {
  const p = saneFeld(block.props);
  const { cells, frame, filled } = drawnFeld(p);
  const line = (0.3 * frame[2]) / 100;
  // The frame grows by a line on each side, so no line lies on the svg's edge, where it would be cut in half and
  // fall on other pixels in print than on screen.
  const [fx, fy, side] = frame;
  return (
    <div className={`hunderterfeld${solved ? " solved" : ""}`}>
      <svg viewBox={[fx - line, fy - line, side + 2 * line, side + 2 * line].join(" ")}>
        {p.look === "punkte"
          ? filled.map((on, i) => (
              <circle
                key={i}
                className={`dot${on ? " filled" : ""}`}
                data-i={i}
                cx={dotAt(i % 10)}
                cy={dotAt(Math.floor(i / 10))}
                r={3.6}
                fill={on ? "#222" : "none"}
                stroke={on ? "none" : "#222"}
                strokeWidth={0.4}
              />
            ))
          : cells
              .filter((c) => c.drawn)
              .map((c) => {
                const x = (c.i % 10) * 10;
                const y = Math.floor(c.i / 10) * 10;
                return (
                  <g key={c.i} className="cell" data-i={c.i} data-value={c.value} data-tint={c.tint || undefined}>
                    <rect x={x} y={y} width={10} height={10} fill={c.tint ? TINT[c.tint] : "none"} stroke="#222" strokeWidth={line} />
                    {c.shown && (
                      <text className="given" x={x + 5} y={y + 5} fontSize={4} textAnchor="middle" dominantBaseline="central" fill="#222">
                        {c.value}
                      </text>
                    )}
                    {!c.shown && solved && (
                      <text className="answer" x={x + 5} y={y + 5} fontSize={4} textAnchor="middle" dominantBaseline="central" fill="#c0392b">
                        {c.value}
                      </text>
                    )}
                  </g>
                );
              })}
        {p.look === "tafel" && !p.cut && <rect className="frame" x={line} y={line} width={100 - 2 * line} height={100 - 2 * line} fill="none" stroke="#222" strokeWidth={2 * line} />}
      </svg>
    </div>
  );
}
