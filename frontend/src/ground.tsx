// The picture a page lies on: how it fills the page, and how it is drawn. The type lives on the page in sheet.tsx.
import type { PointerEvent } from "react";
import type { Ground } from "./sheet";

export type { Ground };

export const FADES = [1, 0.5, 0.25] as const;
export const SCALE_MIN = 0.25;
export const SCALE_MAX = 4;
// Shown beside the file control. The rights line is a placeholder, not a decision.
export const GROUND_HINT = "JPEG, PNG oder PDF, bis 30 MB. Eine PDF bis 20 Seiten.";
export const RIGHTS_PLACEHOLDER = "[Platzhalter] Text zu Rechten: noch offen.";

// The size that fills the page at `scale` and keeps `ratio` (width over height).
export function cover(pageW: number, pageH: number, ratio: number, scale = 1) {
  const width = Math.max(pageW, pageH * ratio) * scale;
  return { w: width, h: width / ratio };
}

function cutOf(cut: number[]): [number, number, number, number] {
  const raw = [0, 1, 2, 3].map((i) => (typeof cut[i] === "number" && cut[i] > 0 ? cut[i] : 0));
  let [l, t, r, b] = raw;
  if (l + r > 0.95) {
    const over = l + r - 0.95;
    l = Math.max(0, l - over / 2);
    r = Math.max(0, r - over / 2);
  }
  if (t + b > 0.95) {
    const over = t + b - 0.95;
    t = Math.max(0, t - over / 2);
    b = Math.max(0, b - over / 2);
  }
  return [l, t, r, b];
}

export function turnsOf(turns?: number) {
  const n = turns ?? 0;
  return ((n % 4) + 4) % 4;
}

// Where the ground is drawn, in mm, and where the picture sits inside that box before it is turned.
export function paint(pageW: number, pageH: number, ground: Ground) {
  const turns = turnsOf(ground.turns);
  const [l, t, r, b] = cutOf(ground.cut ?? []);
  const cw = 1 - l - r;
  const ch = 1 - t - b;
  const cropped = (Math.max(0.01, ground.ratio) * cw) / ch;
  const shown = turns % 2 ? 1 / cropped : cropped;
  const scale = Math.min(SCALE_MAX, Math.max(SCALE_MIN, ground.scale ?? 1));
  const { w: width, h: height } = cover(pageW, pageH, shown, scale);
  const [dx, dy] = ground.at ?? [0, 0];
  const odd = turns % 2 === 1;
  const iw = odd ? height : width;
  const ih = odd ? width : height;
  return {
    x: (pageW - width) / 2 + dx,
    y: (pageH - height) / 2 + dy,
    width,
    height,
    turns,
    opacity: ground.opacity ?? 1,
    ix: (width - iw) / 2,
    iy: (height - ih) / 2,
    iw,
    ih,
    sx: (-l / cw) * iw,
    sy: (-t / ch) * ih,
    sw: iw / cw,
    sh: ih / ch,
  };
}

// The crop after a quarter turn clockwise, so the same edges stay cropped.
export function turnedCut(cut: number[]): number[] {
  const [l, t, r, b] = cutOf(cut);
  return [b, l, t, r];
}

// `edge` is 0 left, 1 top, 2 right, 3 bottom. `by` adds to that edge's crop, as a fraction of the picture.
export function trim(cut: number[], edge: number, by: number): number[] {
  const next = cutOf(cut);
  const opposite = edge ^ 2;
  const room = 1 - next[opposite] - 0.05;
  next[edge] = Math.min(room, Math.max(0, next[edge] + by));
  return [...next];
}

// The ground, laid out at `k` pixels per mm. It does not take the pointer unless `live`.
export function GroundView({
  ground,
  w,
  h,
  k,
  live = false,
  onPointerDown,
  onPointerMove,
  onPointerUp,
}: {
  ground: Ground;
  w: number;
  h: number;
  k: number;
  live?: boolean;
  onPointerDown?: (e: PointerEvent<HTMLDivElement>) => void;
  onPointerMove?: (e: PointerEvent<HTMLDivElement>) => void;
  onPointerUp?: (e: PointerEvent<HTMLDivElement>) => void;
}) {
  const drawn = paint(w, h, ground);
  const px = (mm: number) => mm * k;
  return (
    <div
      className={live ? "ground live" : "ground"}
      data-upload={ground.upload}
      data-turns={drawn.turns}
      data-opacity={drawn.opacity}
      data-cut={ground.cut.join(",")}
      style={{ left: px(drawn.x), top: px(drawn.y), width: px(drawn.width), height: px(drawn.height), opacity: drawn.opacity }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <div
        className="ground-turn"
        style={{
          left: px(drawn.ix),
          top: px(drawn.iy),
          width: px(drawn.iw),
          height: px(drawn.ih),
          transform: drawn.turns ? `rotate(${drawn.turns * 90}deg)` : undefined,
        }}
      >
        <img
          src={`/api/uploads/${ground.upload}`}
          alt=""
          draggable={false}
          style={{ left: px(drawn.sx), top: px(drawn.sy), width: px(drawn.sw), height: px(drawn.sh) }}
        />
      </div>
    </div>
  );
}
