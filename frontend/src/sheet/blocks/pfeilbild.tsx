// Draws one Pfeilbild block.

import { sane as saneArrow, made as arrowMade, layout as arrowLayout, opLabel, inverse, noted as arrowNoted } from "../../pfeilbild";
import { numberSize } from "../../zahlenhaus";
import type { PfeilbildBlock } from "../tasks";

// A Pfeilbild: its pictures in columns, in its own units. The boxes stand in a row, and each arrow arches over two
// neighbours with its operator on top; in "both" a back arrow arches under them with the inverse. A wrong picture shows
// no answer and is marked `wrong`; a picture past the Zahlenraum is not drawn.
export function Pfeilbild({ block, solved }: { block: PfeilbildBlock; k: number; solved: boolean }) {
  const p = saneArrow(block.props);
  const { pictures } = arrowMade(p);
  const { D, G, A, B, picW, picH, CG, RG, vbW, vbH } = arrowLayout(p);
  // The curve from x1 to x2 at height y, bent 6 units towards `s` (-1 up, 1 down): its apex is 3 units out.
  // The arrow head is a filled triangle at x2, along the curve's end.
  const arc = (x1: number, x2: number, y: number, s: number) => {
    const [xm, ctrl] = [(x1 + x2) / 2, y + 6 * s];
    const [dx, dy] = [x2 - xm, y - ctrl];
    const len = Math.hypot(dx, dy);
    const [ux, uy] = [dx / len, dy / len];
    const [bx, by] = [x2 - 2 * ux, y - 2 * uy];
    const [px, py] = [-uy * 1.1, ux * 1.1];
    return {
      curve: `M${x1} ${y} Q${xm} ${ctrl} ${x2} ${y}`,
      head: `M${x2} ${y} L${bx + px} ${by + py} L${bx - px} ${by - py} Z`,
      apex: [xm, y + 3 * s] as const,
    };
  };
  return (
    <div className={`pfeilbild${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {pictures.map((pic, i) => {
          const [x, y] = [(i % p.columns) * (picW + CG), Math.floor(i / p.columns) * (picH + RG)];
          const left = (j: number) => x + j * (D + G);
          const mid = (j: number) => left(j) + D / 2;
          // The label of an arrow: its operator in a white ellipse on the arc, shown when given, or in the key when not.
          const label = (at: readonly [number, number], text: string, given: boolean, shows: boolean) => (
            <>
              {p.drawOps && <ellipse cx={at[0]} cy={at[1]} rx={5} ry={2.6} fill="white" stroke="#222" strokeWidth={0.3} />}
              {shows && (
                <text x={at[0]} y={at[1]} fontSize={3.2} textAnchor="middle" dominantBaseline="central"
                  fill={given ? "#222" : "#c0392b"} className={given ? "op" : "answer"}>{text}</text>
              )}
            </>
          );
          return (
            <g key={i} className={`picture${pic.wrong ? " wrong" : ""}${pic.over ? " over" : ""}`} data-picture={i}>
              {!pic.over && pic.numbers.map((n, j) => {
                const shows = pic.given[j] || (solved && !pic.wrong);
                return (
                  <g key={j} className="box" data-box={j}>
                    <rect x={left(j)} y={y + A} width={D} height={D} fill="white" stroke="#222" strokeWidth={0.4} />
                    {shows && (
                      <text x={mid(j)} y={y + A + D / 2} fontSize={numberSize(String(n).length, D, 0.55 * D)} textAnchor="middle" dominantBaseline="central"
                        fill={pic.given[j] ? "#222" : "#c0392b"} className={pic.given[j] ? "given" : "answer"}>{n}</text>
                    )}
                  </g>
                );
              })}
              {!pic.over && pic.steps.map((step, j) => {
                const fwd = arc(mid(j), mid(j + 1), y + A, -1);
                const shows = pic.opGiven[j] || (solved && !pic.wrong);
                return (
                  <g key={j} className="arrow" data-arrow={j}>
                    <path d={fwd.curve} fill="none" stroke="#222" strokeWidth={0.4} />
                    <path d={fwd.head} fill="#222" />
                    {label(fwd.apex, opLabel(step), pic.opGiven[j], shows)}
                  </g>
                );
              })}
              {!pic.over && p.arrows === "both" && pic.steps.map((step, j) => {
                const back = arc(mid(j + 1), mid(j), y + A + D, 1);
                const shows = pic.opGiven[j] || (solved && !pic.wrong);
                return (
                  <g key={j} className="back" data-arrow={j}>
                    <path d={back.curve} fill="none" stroke="#222" strokeWidth={0.4} />
                    <path d={back.head} fill="#222" />
                    {label(back.apex, opLabel(inverse(step)), pic.opGiven[j], shows)}
                  </g>
                );
              })}
            </g>
          );
        })}
        {/* With only the start and the goal given, several answers can be right: the key says so in its own line. */}
        {/* Its size fits the drawing's width, so that a narrow block of three boxes keeps the whole sentence. */}
        {solved && arrowNoted(p) && (
          <text x={vbW / 2} y={vbH - 3.5} fontSize={Math.min(3.2, vbW / 18)} textAnchor="middle" dominantBaseline="central" fill="#c0392b" className="note">
            Auch andere Lösungen sind richtig.
          </text>
        )}
      </svg>
    </div>
  );
}
