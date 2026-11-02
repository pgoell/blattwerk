// Draws one Uhr block.

import { sane as saneUhr, timesOf, CELL_W, CELL_H, hands, written, handStroke, INK as UHR_INK, RED } from "../../uhr";
import { useLetters, LetterBox } from "../context";
import type { UhrBlock } from "../tasks";

// An Uhr, drawn as the contract at the top of uhr.ts says: one svg, a cell of 100 by 130 per clock.
export function Uhr({ block, solved }: { block: UhrBlock; k: number; solved: boolean }) {
  const p = saneUhr(block.props);
  const letters = useLetters(block.id);
  const times = timesOf(p);
  const cols = Math.min(p.cols, times.length);
  const rows = Math.ceil(times.length / cols);
  // A point of the face at `r` from the centre, `deg` degrees clockwise from 12.
  const polar = (r: number, deg: number) => [50 + r * Math.sin((deg * Math.PI) / 180), 50 - r * Math.cos((deg * Math.PI) / 180)];
  const hour = (n: number, r: number) => polar(r, 30 * ((n - (n > 12 ? 12 : 0)) % 12));
  return (
    <div className={`uhr${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${CELL_W * cols} ${CELL_H * rows}`}>
        {times.map((t, i) => {
          const [hourDeg, minuteDeg] = hands(t);
          const [hx, hy] = polar(p.ring && p.numbers !== "none" ? 13 : 25, hourDeg);
          const [mx, my] = polar(40, minuteDeg);
          const text = written(t, p);
          const lines = text.split("\n");
          const two = lines.length > 1;
          const sizeOf = (line: string) => Math.min(two ? 9 : 10, 180 / line.length);
          const hourInk = handStroke("hour", p, solved);
          const minuteInk = handStroke("minute", p, solved);
          const numbers = p.numbers === "all" ? [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] : p.numbers === "quarters" ? [3, 6, 9, 12] : [];
          const ring = p.ring && p.numbers !== "none" ? [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24] : [];
          return (
            <g key={i} className="clock" data-i={i} data-time={t} transform={`translate(${CELL_W * (i % cols)} ${CELL_H * Math.floor(i / cols)})`}>
              <circle className="face" cx={50} cy={50} r={46} fill="none" stroke={UHR_INK} strokeWidth={1.2} />
              <g className="ticks">
                {Array.from({ length: 60 }, (_, m) => m)
                  .filter((m) => m % 5 === 0 || p.minutes)
                  .map((m) => {
                    const hourTick = m % 5 === 0;
                    const [x1, y1] = polar(46, 6 * m);
                    const [x2, y2] = polar(hourTick ? 39 : 42.5, 6 * m);
                    return <line key={m} x1={x1} y1={y1} x2={x2} y2={y2} stroke={UHR_INK} strokeWidth={hourTick ? 1.2 : 0.5} />;
                  })}
              </g>
              {numbers.map((n) => {
                const [x, y] = hour(n, 33);
                return (
                  <text key={`n${n}`} className="number" data-n={n} x={x} y={y} fontSize={10} textAnchor="middle" dominantBaseline="central" fill={UHR_INK}>
                    {n}
                  </text>
                );
              })}
              {ring.map((n) => {
                const [x, y] = hour(n, 22);
                return (
                  <text key={`r${n}`} className="number" data-n={n} x={x} y={y} fontSize={5.5} textAnchor="middle" dominantBaseline="central" fill={UHR_INK}>
                    {n}
                  </text>
                );
              })}
              {p.task === "read" && (
                <>
                  <line className="hour" x1={50} y1={50} x2={hx} y2={hy} stroke={hourInk} strokeWidth={4.5} strokeLinecap="round" />
                  <line className="minute" x1={50} y1={50} x2={mx} y2={my} stroke={minuteInk} strokeWidth={1.6} strokeLinecap="round" />
                </>
              )}
              {p.task === "draw" && solved && (
                <>
                  <line className="hour answer" x1={50} y1={50} x2={hx} y2={hy} stroke={hourInk} strokeWidth={4.5} strokeLinecap="round" />
                  <line className="minute answer" x1={50} y1={50} x2={mx} y2={my} stroke={minuteInk} strokeWidth={1.6} strokeLinecap="round" />
                </>
              )}
              <circle className="hub" cx={50} cy={50} r={2.5} fill={UHR_INK} />
              {letters && p.task === "read" && <LetterBox x={84} y={2} side={14} task={i} letter={letters[i] ?? ""} solved={solved} />}
              {p.task === "draw" &&
                lines.map((line, n) => (
                  <text key={n} className="task" x={50} y={two ? 110 + n * 12 : 120} fontSize={sizeOf(line)} textAnchor="middle" fill={UHR_INK}>
                    {line}
                  </text>
                ))}
              {p.task === "read" && p.answer === "box" && !solved &&
                (two ? ["__:__ Uhr", "__:__ Uhr"] : ["__:__ Uhr"]).map((line, n) => (
                  <text key={n} className="task" x={50} y={two ? 110 + n * 12 : 120} fontSize={10} textAnchor="middle" fill={UHR_INK}>
                    {line}
                  </text>
                ))}
              {p.task === "read" && solved &&
                lines.map((line, n) => (
                  <text key={n} className="answer" x={50} y={two ? 110 + n * 12 : 120} fontSize={sizeOf(line)} textAnchor="middle" fill={RED}>
                    {line}
                  </text>
                ))}
              {p.task === "read" && p.answer === "line" &&
                (two ? [112, 124] : [122]).map((yy) => (
                  <line key={yy} className="answer" x1={12} y1={yy} x2={88} y2={yy} stroke={UHR_INK} strokeWidth={0.6} />
                ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
