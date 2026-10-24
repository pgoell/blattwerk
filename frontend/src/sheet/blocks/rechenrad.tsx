// Draws one Rechenrad block.

import { sane as saneWheel, made as wheelMade, layout as wheelLayout, edgeAngle, cellAt, opLabel as wheelLabel } from "../../rechenrad";
import { numberSize } from "../../zahlenhaus";
import type { RechenradBlock } from "../tasks";

// A Rechenrad: its wheels in columns. Each wheel has a centre with its operator and number, and rings of segments; a
// box shows its number when it is given, or in the key when the wheel is solved and not wrong.
export function Rechenrad({ block, solved }: { block: RechenradBlock; solved: boolean }) {
  const p = saneWheel(block.props);
  const { wheels } = wheelMade(p);
  const { C0, W, R, F, CG, RG, vbW, vbH } = wheelLayout(p);
  const S = p.segments;
  return (
    <div className={`rechenrad${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {wheels.map((wheel, i) => {
          const [x, y] = [(i % p.columns) * (F + CG), Math.floor(i / p.columns) * (F + RG)];
          const [cx, cy] = [x + R, y + R];
          return (
            <g key={i} className={`wheel${wheel.wrong ? " wrong" : ""}`} data-wheel={i}>
              {wheel.rings.map((ring, ri) => {
                const r = ri + 1;
                return ring.map((n, s) => {
                  const [a0, a1] = [edgeAngle(s, S), edgeAngle(s + 1, S)];
                  const [inner, outer] = [C0 + (r - 1) * W, C0 + r * W];
                  const point = (rad: number, a: number) => `${cx + rad * Math.cos(a)} ${cy + rad * Math.sin(a)}`;
                  const path = `M${point(outer, a0)} A${outer} ${outer} 0 0 1 ${point(outer, a1)} L${point(inner, a1)} A${inner} ${inner} 0 0 0 ${point(inner, a0)} Z`;
                  const shows = wheel.given[ri][s] || (solved && !wheel.wrong);
                  const digits = String(n).length;
                  const chord = 2 * (C0 + (r - 0.5) * W) * Math.sin(Math.PI / S);
                  const [tx, ty] = cellAt(r, s, S, cx, cy, C0, W);
                  return (
                    <g key={`${r}:${s}`} className="box" data-ring={r} data-segment={s}>
                      <path d={path} fill="white" stroke="#222" strokeWidth={0.4} />
                      {shows && (
                        <text x={tx} y={ty} fontSize={numberSize(digits, Math.min(chord, W) * 0.8, 4.4)} textAnchor="middle" dominantBaseline="central"
                          fill={wheel.given[ri][s] ? "#222" : "#c0392b"} className={wheel.given[ri][s] ? "given" : "answer"}>{n}</text>
                      )}
                    </g>
                  );
                });
              })}
              <g className="centre">
                <circle cx={cx} cy={cy} r={C0} fill="white" stroke="#222" strokeWidth={0.4} />
                <text x={cx} y={cy} fontSize={numberSize(wheelLabel(p.op, wheel.centre).length, 2 * C0 * 0.75, 4.6)} textAnchor="middle" dominantBaseline="central"
                  fill="#222" className="given">{wheelLabel(p.op, wheel.centre)}</text>
              </g>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
