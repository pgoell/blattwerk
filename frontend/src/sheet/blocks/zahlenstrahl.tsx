// Draws one Zahlenstrahl block.

import { sane as saneStrahl, made as drawnStrahl, xOf, below, arrowXs, LEFT as STRAHL_LEFT, boxUnder } from "../../zahlenstrahl";
import type { ZahlenstrahlBlock } from "../tasks";

// A Zahlenstrahl, drawn in the block's mm as the contract at the top of zahlenstrahl.ts says.
export function Zahlenstrahl({ block, solved }: { block: ZahlenstrahlBlock; k: number; solved: boolean }) {
  const p = saneStrahl(block.props);
  const { w } = block;
  const { ticks, arrows, arcs } = drawnStrahl(p, w);
  const FS = (p.size * 25.4) / 72;
  const tickX = (v: number) => xOf((v - p.start) / p.minor, ticks.length, w);
  // An arc's height above the line: a wide jump stays a flat arc.
  const rise = (a: { from: number; to: number }) => Math.min(((tickX(a.to) - tickX(a.from)) / 2) * 0.7, 6);
  // The room the line needs below it, and above it for its ticks, or its arcs and their numbers (an arrow's number
  // keeps inside by itself). A block too short for both, saved so or held at the page's foot, draws the whole line a
  // little smaller, so nothing leaves it.
  const room = below(p, w);
  const h = Math.max(block.h, room + Math.max(3.5, ...arcs.map((a) => rise(a) + 2 + 0.8 * FS)));
  const y = h - room;
  const cut = p.cut && p.start > 0;
  const axs = arrowXs(arrows.length, ticks.length, w);
  // An arrow's number stands on the baseline y - 7.6, raised when its digits would pass the block's top; its stub
  // runs from under the digits to y - 5, and is left out where a short block leaves no room for it.
  const base = Math.max(y - 7.6, 0.75 * FS);
  return (
    <div className={`zahlenstrahl${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${w} ${h}`}>
        <line className="axis" x1={cut ? 0.5 : STRAHL_LEFT - 2} y1={y} x2={w - 2.5} y2={y} stroke="#222" strokeWidth={0.4} />
        <path className="head" d={`M ${w - 3.2} ${y - 1.2} L ${w - 1} ${y} L ${w - 3.2} ${y + 1.2} Z`} fill="#222" />
        {cut && (
          <g className="cut" stroke="#222" strokeWidth={0.4}>
            <line x1={2.1} y1={y + 1.6} x2={2.9} y2={y - 1.6} />
            <line x1={3.1} y1={y + 1.6} x2={3.9} y2={y - 1.6} />
          </g>
        )}
        {ticks.map((t, i) => {
          const x = xOf(i, ticks.length, w);
          const reach = t.long ? 3 : 1.5;
          // The box's size, and a box that would cover a number shown beside it, which goes one row lower.
          const { bw, bh, covers, dy } = t.task === "box" ? boxUnder(ticks, i, w, p.size) : { bw: 0, bh: 0, covers: false, dy: 0 };
          const top = y + dy;
          // The leader stops short of a shown number's digits where one stands on it. A digit is taken as 0.65 em wide,
          // more than Andika's, so a line that only grazes a number breaks too.
          const through = covers && ticks.some((o, j) => o.label && !o.task && j !== i && Math.abs(xOf(j, ticks.length, w) - x) <= (String(o.value).length * 0.65 * FS) / 2 + 0.5);
          const gapTop = y + 4.5;
          const gapBottom = y + 5 + 0.75 * FS + 0.5;
          return (
            <g key={t.value} className={`tick${t.long ? " long" : ""}`} data-value={t.value}>
              <line x1={x} y1={y - reach} x2={x} y2={y + reach} stroke="#222" strokeWidth={0.4} />
              {t.label && !t.task && (
                <text className="label" x={x} y={y + 5} fontSize={FS} textAnchor="middle" dominantBaseline="hanging" fill="#222">{t.value}</text>
              )}
              {t.task === "box" && (
                <g className="box">
                  {covers && !through && <line x1={x} y1={y + reach} x2={x} y2={top} stroke="#222" strokeWidth={0.2} />}
                  {covers && through && (
                    <>
                      <line x1={x} y1={y + reach} x2={x} y2={gapTop} stroke="#222" strokeWidth={0.2} />
                      <line x1={x} y1={gapBottom} x2={x} y2={top} stroke="#222" strokeWidth={0.2} />
                    </>
                  )}
                  <rect x={x - bw / 2} y={top} width={bw} height={bh} fill="none" stroke="#222" strokeWidth={0.3} />
                  {solved && (
                    <text className="answer" x={x} y={top + bh / 2} fontSize={FS} textAnchor="middle" dominantBaseline="central" fill="#c0392b">{t.value}</text>
                  )}
                </g>
              )}
            </g>
          );
        })}
        {arrows.map((v, k) => {
          const ax = axs[k];
          return (
            <g key={v} className="arrow" data-value={v}>
              <text className="given" x={ax} y={base} fontSize={FS} textAnchor="middle" fill="#222">{v}</text>
              {base + 0.4 < y - 5 && <line x1={ax} y1={Math.max(base + 0.4, y - 7)} x2={ax} y2={y - 5} stroke="#222" strokeWidth={0.4} />}
              {solved && <path className="answer" d={`M ${ax} ${y - 5} L ${tickX(v)} ${y - 0.5}`} fill="none" stroke="#c0392b" strokeWidth={0.4} />}
            </g>
          );
        })}
        {arcs.map((a) => {
          const [x1, x2] = [tickX(a.from), tickX(a.to)];
          const [rx, ry] = [(x2 - x1) / 2, rise(a)];
          return (
            <g key={`${a.from}-${a.to}`} className="arc" data-from={a.from} data-to={a.to}>
              <path d={`M ${x1} ${y - 0.5} A ${rx} ${ry} 0 0 1 ${x2} ${y - 0.5}`} fill="none" stroke="#222" strokeWidth={0.3} />
              <text x={x1 + rx} y={y - ry - 2} fontSize={FS} textAnchor="middle" fill="#222">{a.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
