// Draws one Zahlenmauer block.

import { sane as saneWall, made as walled, layout as wallLayout, at } from "../../zahlenmauer";
import { useLetters, LetterBox } from "../context";
import type { ZahlenmauerBlock } from "../tasks";

// A Zahlenmauer: its walls in columns, row by row, in its own units. A stone is twice as wide as high, and a row
// sits half a stone right of the one under it, so a wall is as wide as its base row. The svg scales with the block.
export function Zahlenmauer({ block, solved }: { block: ZahlenmauerBlock; k: number; solved: boolean }) {
  const p = saneWall(block.props);
  const { walls } = walled(p);
  const { S, wallW, wallH, gap, vbW, vbH } = wallLayout(p);
  const letters = useLetters(block.id);
  // A wrong wall gives no task, and a block with `empty` none: the letter boxes number the walls that have one.
  let next = 0;
  const task = walls.map((w) => (w.wrong || p.empty || w.given.every(Boolean) ? -1 : next++));
  return (
    <div className={`zahlenmauer${solved ? " solved" : ""}`}>
      {/* Half a unit of room around the walls, so the lines at the edge show whole. */}
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {walls.map((w, i) => {
          const [x0, y0] = [(i % p.columns) * (wallW + gap), Math.floor(i / p.columns) * (wallH + gap)];
          const stones = Array.from({ length: p.base }, (_, r) => Array.from({ length: p.base - r }, (_, c) => {
            const s = at(p.base, r, c);
            const [x, y] = [x0 + r * S + c * 2 * S, y0 + (p.base - 1 - r) * S];
            const shows = !p.empty && (w.given[s] || (solved && !w.wrong));
            return (
              <g key={s} className="stone" data-stone={s} data-row={r} data-col={c}>
                <rect x={x} y={y} width={2 * S} height={S} fill="white" stroke="#222" strokeWidth={0.4} />
                {shows && (
                  <text x={x + S} y={y + S / 2} fontSize={0.6 * S} textAnchor="middle" dominantBaseline="central"
                    fill={w.given[s] ? "#222" : "#c0392b"} className={w.given[s] ? "given" : "answer"}>{w.numbers[s]}</text>
                )}
              </g>
            );
          }));
          // The box stands at the right end of the top row, in the empty corner above the stones beside it.
          const t = task[i];
          return (
            <g key={i} className={`wall${w.wrong ? " wrong" : ""}`} data-wall={i}>
              {stones.flat()}
              {letters && t >= 0 && <LetterBox x={x0 + (p.base + 1.2) * S} y={y0} side={0.8 * S} task={t} letter={letters[t] ?? ""} solved={solved} />}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
