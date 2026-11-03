// Draws one Diagramm, on screen and in print.

import { VIEW, chart, sane } from "../../diagramm";
import { SvgInk } from "../places";
import type { DiagrammBlock } from "../tasks";

export function Diagramm({ block, solved }: { block: DiagrammBlock; k: number; solved: boolean }) {
  const p = sane(block.props);
  const drawn = chart(p, solved);
  return (
    <div className={`diagramm${solved ? " solved" : ""}`} data-kind={p.kind}>
      <svg viewBox={`0 0 ${VIEW.w} ${VIEW.h}`}>
        {drawn.grid.map((g, i) => (
          <line key={i} className={`grid ${g.step}`} x1={g.x1} y1={g.y1} x2={g.x2} y2={g.y2} stroke="#c5c5c5" strokeWidth={g.step === "haupt" ? 0.45 : 0.25} />
        ))}
        {drawn.axes.map((a) => (
          <line key={a.dir} className="axis" data-dir={a.dir} x1={a.x1} y1={a.y1} x2={a.x2} y2={a.y2} stroke="#222" strokeWidth={0.7} />
        ))}
        {drawn.bars.map((b) => (
          <rect key={b.i} className={b.answer ? "balken answer" : "balken"} x={b.x} y={b.y} width={Math.max(b.w, 0)} height={Math.max(b.h, 0)} fill={b.color} />
        ))}
        {drawn.slices.map((s) => (
          <path key={s.i} className={s.answer ? "slice answer" : "slice"} d={s.d} fill={s.color} />
        ))}
        {drawn.ticks.map((t, i) => (
          <text key={i} className="tick" x={t.x} y={t.y} textAnchor={t.anchor} dominantBaseline="middle" fontSize={4.5} fill="#222"><SvgInk text={t.text} /></text>
        ))}
        {drawn.cats.map((c) => (
          <text key={c.i} className="cat" x={c.x} y={c.y} textAnchor={c.anchor} dominantBaseline="middle" fontSize={5} fill="#222"><SvgInk text={c.text} /></text>
        ))}
        {drawn.values.map((v) => (
          <text key={v.i} className={v.answer ? "value answer" : "value"} data-place={p.values} x={v.x} y={v.y} textAnchor={v.anchor} dominantBaseline="middle" fontSize={5} fill="#222"><SvgInk text={v.text} /></text>
        ))}
        {drawn.titles.map((t) => (
          <text key={t.axis} className="title" data-axis={t.axis} x={t.x} y={t.y} textAnchor="middle" dominantBaseline="middle" fontSize={5} fill="#222" transform={t.axis === "y" ? `rotate(-90 ${t.x} ${t.y})` : undefined}><SvgInk text={t.text} /></text>
        ))}
        {drawn.legend.map((item) => (
          <g key={item.i} className="legend">
            <rect x={item.x} y={item.y - 2.2} width={4.4} height={4.4} fill={item.color} />
            <text x={item.x + 6} y={item.y} textAnchor="start" dominantBaseline="middle" fontSize={4.5} fill="#222"><SvgInk text={item.text} /></text>
          </g>
        ))}
      </svg>
    </div>
  );
}
