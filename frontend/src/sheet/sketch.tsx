// The Formen a CSS box cannot draw, and a shape told to stay square or round.

import type { CSSProperties, ReactNode } from "react";
import {
  THOUGHT_TAIL,
  arcGeometry,
  barStrips,
  bulgeOf,
  circlePath,
  diamondPoints,
  pieWedges,
  polygonPoints,
  replaces,
  roomOf,
  thoughtPath,
} from "./formen";
import { Outline, OUTLINES, dashes, radiusOf, tailOf } from "./shape";
import type { TextProps } from "./text";

const look = (p: Partial<TextProps>, edge: number, fill = p.fill ?? "none") => ({
  fill,
  fillOpacity: p.opacity ?? 1,
  stroke: p.stroke ?? "none",
  strokeOpacity: p.strokeOpacity,
  strokeWidth: edge,
  strokeLinejoin: "round" as const,
  strokeDasharray: dashes(p.dash, edge),
  strokeLinecap: p.dash === "dotted" ? ("round" as const) : undefined,
});

function roundBox(w: number, h: number, e: number, r: number) {
  const [x, y, right, low] = [e, e, w - e, h - e];
  const rad = Math.max(0, Math.min(r, (right - x) / 2, (low - y) / 2));
  return `M${x + rad},${y} H${right - rad} A${rad},${rad} 0 0 1 ${right},${y + rad} V${low - rad} A${rad},${rad} 0 0 1 ${right - rad},${low} H${x + rad} A${rad},${rad} 0 0 1 ${x},${low - rad} V${y + rad} A${rad},${rad} 0 0 1 ${x + rad},${y} Z`;
}

function draw(kind: TextProps["kind"], w: number, h: number, e: number, p: Partial<TextProps>, edge: number): ReactNode {
  const ink = look(p, edge);
  if (kind === "circle") return <Outline d={circlePath(0, 0, Math.min(w, h), e)} {...ink} />;
  if (kind === "rect") return <rect x={e} y={e} width={Math.max(0, w - 2 * e)} height={Math.max(0, h - 2 * e)} {...ink} />;
  if (kind === "rounded") return <Outline d={roundBox(w, h, e, radiusOf(p, w, h))} {...ink} />;
  if (kind === "diamond") return <polygon points={diamondPoints(w, h, e).join(" ")} {...ink} />;
  if (kind === "polygon") return <polygon points={polygonPoints(w, h, e, p).join(" ")} {...ink} />;
  if (kind === "arc" || kind === "bow") {
    const { curve, head } = arcGeometry(w, h, e, bulgeOf(p), kind === "bow" ? 2 + edge * 3 : 0);
    return (
      <>
        <path className="arc" d={curve} {...ink} fill="none" />
        {head && <polygon className="head" points={head.join(" ")} fill={p.stroke ?? "none"} fillOpacity={p.strokeOpacity} stroke="none" />}
      </>
    );
  }
  if (kind === "thought") return <Outline d={thoughtPath(w, h, e, tailOf(p) ?? THOUGHT_TAIL)} {...ink} />;
  if (kind === "pie")
    return pieWedges(w, h, e, p).map((wedge, i) => <path key={i} className={wedge.on ? "wedge on" : "wedge"} d={wedge.d} {...look(p, edge, wedge.on ? (p.fill ?? "none") : "none")} />);
  if (kind === "bars") {
    const strips = barStrips(w, h, e, p);
    return (
      <>
        <rect x={e} y={e} width={Math.max(0, w - 2 * e)} height={Math.max(0, h - 2 * e)} {...ink} fill="none" />
        {strips.map((s, i) => s.on && <rect key={i} className="strip on" x={s.x} y={s.y} width={s.w} height={s.h} fill={p.fill ?? "none"} fillOpacity={p.opacity ?? 1} stroke="none" />)}
        {strips.slice(1).map((s, i) => (
          <line key={i} x1={s.x} x2={s.x} y1={e} y2={h - e} stroke={p.stroke ?? "none"} strokeOpacity={p.strokeOpacity} strokeWidth={edge} />
        ))}
      </>
    );
  }
  const d = kind ? OUTLINES[kind]?.(w, h, e, p) : undefined;
  return d ? <Outline d={d} {...ink} /> : null;
}

function Hub({ cx, cy, colour }: { cx: number; cy: number; colour: string }) {
  return (
    <g className="hub" stroke={colour} fill={colour} strokeWidth={0.35}>
      <line x1={cx - 1.2} x2={cx + 1.2} y1={cy} y2={cy} />
      <line x1={cx} x2={cx} y1={cy - 1.2} y2={cy + 1.2} />
      <circle cx={cx} cy={cy} r={0.45} stroke="none" />
    </g>
  );
}

// `edge` is the stroke in mm. The cross of a circle sits at its centre, including when the shape is drawn in a square.
export function Sketch({ w, h, edge, p, flip }: { w: number; h: number; edge: number; p: Partial<TextProps>; flip?: CSSProperties }) {
  const form = p.form === "square" || p.form === "round" ? p.form : undefined;
  const room = roomOf(w, h, form);
  const [ox, oy, bw, bh] = room ? [room.x, room.y, room.s, room.s] : [0, 0, w, h];
  const kind = form === "round" ? "circle" : p.kind;
  const body = replaces(p) ? draw(kind, bw, bh, edge / 2, p, edge) : null;
  const mark = p.kind === "circle" && p.hub === true;
  return (
    <svg className="outline" viewBox={`0 0 ${w} ${h}`} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: replaces(p) ? -1 : 0, pointerEvents: "none", ...flip }}>
      {body && <g transform={ox || oy ? `translate(${ox} ${oy})` : undefined}>{body}</g>}
      {mark && <Hub cx={ox + bw / 2} cy={oy + bh / 2} colour={p.stroke && p.stroke !== "none" ? p.stroke : "#222222"} />}
    </svg>
  );
}
