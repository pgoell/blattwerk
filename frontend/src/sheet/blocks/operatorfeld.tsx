// Draws one Operatorfeld block.

import { sane as saneOp, made as opMade, layout as opLayout, boxAt, opLabel as opLabelOf, noted as opNoted } from "../../operatorfeld";
import { numberSize } from "../../zahlenhaus";
import type { OperatorfeldBlock } from "../tasks";

// An Operatorfeld: its fields in columns. Each field is a ring of boxes, or a centre with outer boxes, and each link
// between two boxes carries an operator. A wrong field shows no answers and is marked `wrong`; a field past the
// Zahlenraum is not drawn.
export function Operatorfeld({ block, solved }: { block: OperatorfeldBlock; k: number; solved: boolean }) {
  const p = saneOp(block.props);
  const { fields } = opMade(p);
  const { D, R, F, CG, RG, vbW, vbH } = opLayout(p);
  return (
    <div className={`operatorfeld${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {fields.map((field, i) => {
          const [x, y] = [(i % p.columns) * (F + CG), Math.floor(i / p.columns) * (F + RG)];
          const [cx, cy] = [x + F / 2, y + F / 2];
          const mid = (j: number) => boxAt(p.centre, p.boxes, j, cx, cy, R);
          // A link from the edge of box a to the edge of box b: its arrow head's tip at b, the head's base 2 units back.
          const span = (a: [number, number], b: [number, number]) => {
            const [dx, dy] = [b[0] - a[0], b[1] - a[1]];
            const len = Math.hypot(dx, dy);
            const [ux, uy] = [dx / len, dy / len];
            const t = (D / 2) / Math.max(Math.abs(ux), Math.abs(uy)) + 0.5;
            const [sx, sy] = [a[0] + ux * t, a[1] + uy * t];
            const [tx, ty] = [b[0] - ux * t, b[1] - uy * t];
            const [bx, by] = [tx - 2 * ux, ty - 2 * uy];
            const [px, py] = [-uy * 1.1, ux * 1.1];
            return {
              line: `M${sx} ${sy} L${bx} ${by}`,
              head: `M${tx} ${ty} L${bx + px} ${by + py} L${bx - px} ${by - py} Z`,
              middle: [(sx + tx) / 2, (sy + ty) / 2] as const,
            };
          };
          return (
            <g key={i} className={`field${field.wrong ? " wrong" : ""}${field.over ? " over" : ""}`} data-field={i}>
              {!field.over && field.links.map((link, j) => {
                const arrow = span(mid(link.from), mid(link.to));
                const shows = field.opGiven[j] || (solved && !field.wrong);
                const text = opLabelOf(link);
                return (
                  <g key={j} className="link" data-link={j}>
                    <path d={arrow.line} fill="none" stroke="#222" strokeWidth={0.4} />
                    <path d={arrow.head} fill="#222" />
                    {p.drawOps && (
                      <ellipse cx={arrow.middle[0]} cy={arrow.middle[1]} rx={5.5} ry={2.6} fill="white" stroke="#222" strokeWidth={0.3} />
                    )}
                    {shows && (
                      <text x={arrow.middle[0]} y={arrow.middle[1]} fontSize={text.length > 3 ? 2.8 : 3.2} textAnchor="middle" dominantBaseline="central"
                        fill={field.opGiven[j] ? "#222" : "#c0392b"} className={field.opGiven[j] ? "op" : "answer"}>{text}</text>
                    )}
                  </g>
                );
              })}
              {!field.over && field.numbers.map((n, j) => {
                const [bx, by] = mid(j);
                const shows = field.given[j] || (solved && !field.wrong);
                return (
                  <g key={j} className="box" data-box={j}>
                    <rect x={bx - D / 2} y={by - D / 2} width={D} height={D} fill="white" stroke="#222" strokeWidth={0.4} />
                    {shows && (
                      <text x={bx} y={by} fontSize={numberSize(String(n).length, D, 0.55 * D)} textAnchor="middle" dominantBaseline="central"
                        fill={field.given[j] ? "#222" : "#c0392b"} className={field.given[j] ? "given" : "answer"}>{n}</text>
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}
        {/* With a noted field the key says that other answers count too, in its own line at the foot. */}
        {solved && opNoted(p) && (
          <text x={vbW / 2} y={vbH - 3.5} fontSize={Math.min(3.2, vbW / 18)} textAnchor="middle" dominantBaseline="central" fill="#c0392b" className="note">
            Auch andere Lösungen sind richtig.
          </text>
        )}
      </svg>
    </div>
  );
}
