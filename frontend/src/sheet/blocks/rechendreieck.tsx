// Draws one Rechendreieck block.

import { sane as saneRechen, made as drawnRechen, layout, FIELDS as RECHEN_FIELDS } from "../../rechendreieck";
import { useLetters, LetterBox } from "../context";
import type { RechendreieckBlock } from "../tasks";

// A Rechendreieck: its triangles in columns, in its own units. A triangle has sides of 60 units: its inner fields
// are circles just inside the corners, its outer fields rectangles beyond the middle of each side. The svg scales
// with the block.
export function Rechendreieck({ block, solved }: { block: RechendreieckBlock; k: number; solved: boolean }) {
  const p = saneRechen(block.props);
  const { triangles } = drawnRechen(p);
  const { GAP, RING, BOX, corner, inner, outer, minX, cellW, cellH, cols, vbW, vbH } = layout(p);
  const letters = useLetters(block.id);
  // A wrong triangle gives no task, and a block with `empty` none: the letter boxes number the triangles that have one.
  let next = 0;
  const task = triangles.map((tri) => (tri.wrong || p.empty || tri.given.every(Boolean) ? -1 : next++));
  return (
    <div className={`rechendreieck${solved ? " solved" : ""}`}>
      {/* Half a unit of room around the triangles, so the lines at the edge show whole. */}
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {triangles.map((tri, t) => {
          const [x, y] = [(t % cols) * (cellW + GAP) - minX, Math.floor(t / cols) * (cellH + GAP)];
          return (
            <g key={t} className={`triangle${tri.wrong ? " wrong" : ""}`} data-triangle={t} transform={`translate(${x} ${y})`}>
              <polygon points={corner.map((c) => c.join(",")).join(" ")} fill="none" stroke="#222" strokeWidth={0.6} />
              {/* The box stands at the top left of the triangle's cell, its side the height of an outer field. */}
              {letters && task[t] >= 0 && <LetterBox x={minX} y={0} side={BOX[1]} task={task[t]} letter={letters[task[t]] ?? ""} solved={solved} />}
              {Array.from({ length: RECHEN_FIELDS }, (_, j) => {
                const [cx, cy] = j < 3 ? inner[j] : outer[j - 3];
                const shows = !p.empty && (tri.given[j] || (solved && !tri.wrong));
                return (
                  <g key={j} className="field" data-field={j}>
                    {j < 3
                      ? <circle cx={cx} cy={cy} r={RING} fill="white" stroke="#222" strokeWidth={0.4} />
                      : <rect x={cx - BOX[0] / 2} y={cy - BOX[1] / 2} width={BOX[0]} height={BOX[1]} fill="white" stroke="#222" strokeWidth={0.4} />}
                    {shows && (
                      <text x={cx} y={cy} fontSize={5.5} textAnchor="middle" dominantBaseline="central"
                        fill={tri.given[j] ? "#222" : "#c0392b"} className={tri.given[j] ? "given" : "answer"}>{tri.numbers[j]}</text>
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
