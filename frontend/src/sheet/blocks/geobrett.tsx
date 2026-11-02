// Draws one Geobrett block, on screen and in print.

import { ASK, boardBox, centreOf, dotAt, sane, segments, solution, type Axis, type Band, type Nail } from "../../geobrett";
import type { GeobrettBlock } from "../tasks";

const KEY = "#c0392b";

function ends(axis: Axis, cols: number, rows: number): [[number, number], [number, number]] | undefined {
  if (axis.dir === "v") {
    const c = axis.mid ? axis.at + 0.5 : axis.at;
    return [dotAt(c, 0), dotAt(c, rows - 1)];
  }
  if (axis.dir === "h") {
    const r = axis.mid ? axis.at + 0.5 : axis.at;
    return [dotAt(0, r), dotAt(cols - 1, r)];
  }
  const pts: [number, number][] = [];
  for (let c = 0; c < cols; c++) {
    const r = axis.dir === "d" ? c + axis.at : axis.at - c;
    if (r >= 0 && r <= rows - 1) pts.push(dotAt(c, r));
  }
  return pts.length < 2 ? undefined : [pts[0], pts[pts.length - 1]];
}

function BandPath({ band, answer }: { band: Band; answer?: boolean }) {
  const pts = band.nails.map(([c, r]) => dotAt(c, r).join(",")).join(" ");
  const stroke = answer ? KEY : band.color;
  const common = { className: answer ? "band answer" : "band", points: pts, fill: band.fill ? stroke : "none", fillOpacity: band.fill ? 0.28 : 0, stroke, strokeWidth: 1.5, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };
  return band.fill ? <polygon {...common} /> : <polyline {...common} />;
}

function corner(band: Band, at: Nail): string | undefined {
  const i = band.nails.findIndex(([c, r]) => c === at[0] && r === at[1]);
  if (i < 0 || band.nails.length < 2) return;
  const prev = band.nails[(i - 1 + band.nails.length) % band.nails.length];
  const next = band.nails[(i + 1) % band.nails.length];
  const [ax, ay] = dotAt(at[0], at[1]);
  const unit = (n: Nail): [number, number] => {
    const [x, y] = dotAt(n[0], n[1]);
    const len = Math.hypot(x - ax, y - ay) || 1;
    return [(x - ax) / len, (y - ay) / len];
  };
  const [ux, uy] = unit(prev);
  const [vx, vy] = unit(next);
  const s = 2.4;
  return `M ${ax + ux * s} ${ay + uy * s} L ${ax + (ux + vx) * s} ${ay + (uy + vy) * s} L ${ax + vx * s} ${ay + vy * s}`;
}

export function Geobrett({ block, solved }: { block: GeobrettBlock; k: number; solved: boolean }) {
  const p = sane(block.props);
  const answer = solution(p);
  const caption = p.task !== "leer";
  const [w, h] = boardBox(p.cols, p.rows, caption);
  const bands = p.task === "leer" ? [] : p.bands;
  const axes = p.task === "spiegel" && p.axis ? [p.axis] : solved && answer.kind === "achsen" ? answer.axes : [];
  const extra = solved && (answer.kind === "spiegel" || answer.kind === "drehung") ? answer.bands : [];
  const shown = answer.kind === "flaeche" || answer.kind === "umfang" ? answer.text : "";
  return (
    <div className={`geobrett${solved ? " solved" : ""}`} data-task={p.task}>
      <svg viewBox={`0 0 ${w} ${h}`}>
        {axes.map((axis, i) => {
          const line = ends(axis, p.cols, p.rows);
          return line && <line key={i} className="axis" data-dir={axis.dir} x1={line[0][0]} y1={line[0][1]} x2={line[1][0]} y2={line[1][1]} stroke={solved && p.task === "achsen" ? KEY : "#222"} strokeWidth={0.7} strokeDasharray="1.6 1.2" />;
        })}
        {bands.map((band, i) => <BandPath key={i} band={band} />)}
        {extra.map((band, i) => <BandPath key={`a${i}`} band={band} answer />)}
        {p.task === "drehung" && <circle className="centre" cx={dotAt(...centreOf(p))[0]} cy={dotAt(...centreOf(p))[1]} r={2.4} fill="none" stroke="#222" strokeWidth={0.7} />}
        {solved && answer.kind === "winkel" && bands.flatMap((band, bi) => answer.nails.map((nail, ni) => {
          const d = corner(band, nail);
          return d && <path key={`${bi}-${ni}`} className="angle answer" d={d} fill="none" stroke={KEY} strokeWidth={0.7} />;
        }))}
        {solved && answer.kind === "parallelen" && bands[0] && answer.groups.flatMap((group, gi) => group.map((edge) => {
          const seg = segments(bands[0])[edge];
          if (!seg) return null;
          const [[c, r], [u, v]] = seg;
          const [x1, y1] = dotAt(c, r);
          const [x2, y2] = dotAt(u, v);
          const [mx, my] = [(x1 + x2) / 2, (y1 + y2) / 2];
          const len = Math.hypot(x2 - x1, y2 - y1) || 1;
          const [px, py] = [-(y2 - y1) / len, (x2 - x1) / len];
          return Array.from({ length: gi + 1 }, (_, t) => {
            const shift = (t - gi / 2) * 1.3;
            const [sx, sy] = [mx + ((x2 - x1) / len) * shift, my + ((y2 - y1) / len) * shift];
            return <line key={`${gi}-${edge}-${t}`} className="tick answer" x1={sx - px * 1.6} y1={sy - py * 1.6} x2={sx + px * 1.6} y2={sy + py * 1.6} stroke={KEY} strokeWidth={0.7} />;
          });
        }))}
        {Array.from({ length: p.rows * p.cols }, (_, i) => {
          const [c, r] = [i % p.cols, Math.floor(i / p.cols)];
          const [x, y] = dotAt(c, r);
          return <circle key={i} className="nail" data-c={c} data-r={r} cx={x} cy={y} r={1.15} fill="#222" />;
        })}
        {p.task === "koordinaten" && Array.from({ length: p.cols }, (_, c) => (
          <text key={`c${c}`} className="coord" x={dotAt(c, 0)[0]} y={dotAt(0, p.rows - 1)[1] + 5} textAnchor="middle" fontSize={3.2} fill="#222">{c}</text>
        ))}
        {p.task === "koordinaten" && Array.from({ length: p.rows }, (_, r) => (
          <text key={`r${r}`} className="coord" x={dotAt(0, 0)[0] - 2} y={dotAt(0, r)[1]} textAnchor="end" dominantBaseline="central" fontSize={3.2} fill="#222">{p.rows - 1 - r}</text>
        ))}
        {solved && answer.kind === "koordinaten" && answer.nails.map(([c, row], i) => (
          <text key={`k${i}`} className="answer" x={dotAt(c, p.rows - 1 - row)[0] + 1.6} y={dotAt(c, p.rows - 1 - row)[1] - 1.6} fontSize={3.2} fill={KEY}>{c}|{row}</text>
        ))}
        {caption && (
          <text className="ask" x={w / 2} y={h - 2.5} textAnchor="middle" fontSize={4} fill="#222">
            {ASK[p.task]}
            {solved && shown && <tspan className="answer" fill={KEY}> {shown}</tspan>}
          </text>
        )}
      </svg>
    </div>
  );
}
