// Draws one Hunderterfeld block.

import { sane as saneFeld, made as drawnFeld, dotAt, TINT, GREY } from "../../hunderterfeld";
import type { HunderterfeldBlock } from "../tasks";

// A cell next to a hole loses the shared line: the hole is the gap, not an empty square.
function besideHole(i: number, holes: Set<number>): boolean {
  const col = i % 10;
  const row = Math.floor(i / 10);
  return (col > 0 && holes.has(i - 1)) || (col < 9 && holes.has(i + 1)) || (row > 0 && holes.has(i - 10)) || (row < 9 && holes.has(i + 10));
}

// The four sides of cell i, each dropped when the neighbour is a hole. The rim stays.
function edges(i: number, holes: Set<number>): [number, number, number, number][] {
  const col = i % 10;
  const row = Math.floor(i / 10);
  const x = col * 10;
  const y = row * 10;
  const keep = (dir: number, rim: boolean) => rim || !holes.has(i + dir);
  const out: [number, number, number, number][] = [];
  if (keep(-10, row === 0)) out.push([x, y, x + 10, y]);
  if (keep(10, row === 9)) out.push([x, y + 10, x + 10, y + 10]);
  if (keep(-1, col === 0)) out.push([x, y, x, y + 10]);
  if (keep(1, col === 9)) out.push([x + 10, y, x + 10, y + 10]);
  return out;
}

// Runs of cells along one edge that are not holes, as [start, end) in 0 to 10.
function borderRuns(holes: Set<number>, at: (k: number) => number): [number, number][] {
  const runs: [number, number][] = [];
  let start = -1;
  for (let k = 0; k <= 10; k++) {
    if (k === 10 || holes.has(at(k))) {
      if (start >= 0) runs.push([start, k]);
      start = -1;
    } else if (start < 0) start = k;
  }
  return runs;
}

// A Hunderterfeld, drawn as the contract at the top of hunderterfeld.ts says. Its lines are 0.3 and its outer frame
// 0.6 of a 100 field, so they keep that share when a cut-out makes the field smaller.
export function Hunderterfeld({ block, solved }: { block: HunderterfeldBlock; k: number; solved: boolean }) {
  const p = saneFeld(block.props);
  const { cells, frame, filled } = drawnFeld(p);
  const line = (0.3 * frame[2]) / 100;
  const holes = new Set(solved ? [] : cells.filter((c) => c.drawn && c.blank === "gone").map((c) => c.i));
  const broken = [...holes].some((i) => i < 10 || i >= 90 || i % 10 === 0 || i % 10 === 9);
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
              .filter((c) => c.drawn && !holes.has(c.i))
              .map((c) => {
                const x = (c.i % 10) * 10;
                const y = Math.floor(c.i / 10) * 10;
                const size = c.value >= 1000 ? 2.8 : 4;
                const open = besideHole(c.i, holes);
                const fill = c.tint ? TINT[c.tint] : !solved && c.blank === "grey" ? GREY : "none";
                return (
                  <g key={c.i} className="cell" data-i={c.i} data-value={c.value} data-tint={c.tint || undefined} data-blank={c.blank === "empty" ? undefined : c.blank}>
                    <rect x={x} y={y} width={10} height={10} fill={fill} stroke={open ? "none" : "#222"} strokeWidth={line} />
                    {open && edges(c.i, holes).map(([x1, y1, x2, y2], n) => <line key={n} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#222" strokeWidth={line} />)}
                    {c.shown && (
                      <text className="given" x={x + 5} y={y + 5} fontSize={size} textAnchor="middle" dominantBaseline="central" fill="#222">
                        {c.value}
                      </text>
                    )}
                    {!c.shown && solved && (
                      <text className="answer" x={x + 5} y={y + 5} fontSize={size} textAnchor="middle" dominantBaseline="central" fill="#c0392b">
                        {c.value}
                      </text>
                    )}
                  </g>
                );
              })}
        {p.look === "tafel" && !p.cut && !broken && <rect className="frame" x={line} y={line} width={100 - 2 * line} height={100 - 2 * line} fill="none" stroke="#222" strokeWidth={2 * line} />}
        {p.look === "tafel" && !p.cut && broken && (
          <>
            {borderRuns(holes, (k) => k).map(([a, b]) => (
              <line key={`n${a}`} x1={a * 10} y1={line} x2={b * 10} y2={line} stroke="#222" strokeWidth={2 * line} />
            ))}
            {borderRuns(holes, (k) => 90 + k).map(([a, b]) => (
              <line key={`s${a}`} x1={a * 10} y1={100 - line} x2={b * 10} y2={100 - line} stroke="#222" strokeWidth={2 * line} />
            ))}
            {borderRuns(holes, (k) => k * 10).map(([a, b]) => (
              <line key={`w${a}`} x1={line} y1={a * 10} x2={line} y2={b * 10} stroke="#222" strokeWidth={2 * line} />
            ))}
            {borderRuns(holes, (k) => k * 10 + 9).map(([a, b]) => (
              <line key={`e${a}`} x1={100 - line} y1={a * 10} x2={100 - line} y2={b * 10} stroke="#222" strokeWidth={2 * line} />
            ))}
          </>
        )}
      </svg>
    </div>
  );
}
