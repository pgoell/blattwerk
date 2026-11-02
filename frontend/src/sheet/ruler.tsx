// The ticks and numbers of a line drawn as a ruler.

import { PT } from "../height";
import { NUMBER_GAP, NUMBER_PT, ticksOf } from "../ruler";

// Drawn in the line's own coordinates, on the side y < 0. When the line points left the group is
// mirrored, and each number is turned back, so the ticks stay with the numbers and the numbers read upright.
export function RulerMarks({ length, mm, angle }: { length: number; mm: boolean; angle: number }) {
  const flip = Math.abs(angle) > 90;
  return (
    <g className="ruler" transform={flip ? "scale(1 -1)" : undefined}>
      {ticksOf(length, mm).map((t) => {
        const y = -t.reach - NUMBER_GAP;
        return (
          <g key={t.at}>
            <line className={t.kind} x1={t.at} x2={t.at} y1={0} y2={-t.reach} />
            {t.n !== undefined && (
              <text className="n" x={t.at} y={y} transform={flip ? `rotate(180 ${t.at} ${y})` : undefined} textAnchor="middle" fontFamily="Andika" fontSize={NUMBER_PT * PT} stroke="none">
                {t.n}
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}
