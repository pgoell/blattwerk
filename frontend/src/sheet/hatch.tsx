// The SVG tile of a shape's Muster or Lineatur. One id per drawing: the page and its thumbnail both draw the block.

import type { CSSProperties, ReactNode } from "react";
import type { Kind } from "./box";
import { inkOf, paperOf, tileOf, type Blob } from "./motif";
import { radiusOf } from "./shape";

type Props = { kind?: Kind; corner?: number; opacity?: number; motif?: unknown; paper?: unknown; fill?: string; mono?: unknown; scale?: unknown };
export type HatchPaint = { paint: string; defs: ReactNode };

function Mark({ mark, ink }: { mark: Blob; ink: string }) {
  if ("d" in mark) return <path d={mark.d} fill="none" stroke={ink} strokeWidth={mark.width} />;
  if ("r" in mark) return <circle cx={mark.cx} cy={mark.cy} r={mark.r} fill={ink} />;
  return <rect x={mark.x} y={mark.y} width={mark.w} height={mark.h} fill={ink} />;
}

export function hatchOf(id: string, p: Props): HatchPaint | undefined {
  const tile = tileOf(p);
  if (!tile) return undefined;
  const ink = inkOf(p.fill, p.mono === true && !paperOf(p));
  return {
    paint: `url(#${id})`,
    defs: (
      <defs>
        <pattern id={id} width={tile.size} height={tile.size} patternUnits="userSpaceOnUse">
          {tile.ground && <rect width={tile.size} height={tile.size} fill="#ffffff" />}
          {tile.pens.map((pen, i) => <line key={i} x1={pen.x1} y1={pen.y1} x2={pen.x2} y2={pen.y2} stroke={ink} strokeWidth={pen.width} />)}
          {tile.blobs.map((mark, i) => <Mark key={i} mark={mark} ink={ink} />)}
        </pattern>
      </defs>
    ),
  };
}

// A box the CSS border draws: the tile clipped to the box. An outline carries the same defs on its own path.
export function Hatch({ w, h, p, hatch, style }: { w: number; h: number; p: Props; hatch: HatchPaint; style: CSSProperties }) {
  const opacity = p.opacity ?? 1;
  const rx = p.kind === "rounded" ? radiusOf(p, w, h) : 0;
  return (
    <svg className="hatch" viewBox={`0 0 ${w} ${h}`} style={style}>
      {hatch.defs}
      {p.kind === "circle" ? (
        <ellipse cx={w / 2} cy={h / 2} rx={w / 2} ry={h / 2} fill={hatch.paint} fillOpacity={opacity} />
      ) : (
        <rect width={w} height={h} rx={rx || undefined} fill={hatch.paint} fillOpacity={opacity} />
      )}
    </svg>
  );
}
