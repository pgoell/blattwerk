// The frame that crops a picture.
import type { PointerEvent } from "react";
import type { ImageBlock } from "../../sheet";

// Crop mode, drawn over the picture's block: the whole picture, pale outside the frame, and the frame with a handle
// on each corner and edge. `box` is the whole picture on the page; the block lies inside it.
export function Crop({ block, box, cut: [l, t, r, b], k, grip, trim }: {
  block: ImageBlock;
  box: { x: number; y: number; w: number; h: number };
  cut: number[];
  k: number;
  grip: (e: PointerEvent) => void;
  trim: (e: PointerEvent, b: ImageBlock, dx: number, dy: number) => void;
}) {
  const src = `/api/uploads/${block.props.upload}`;
  const inset = [t, r, b, l].map((share) => `${share * 100}%`).join(" ");
  // Along one axis: the frame's near edge, its middle and its far edge.
  const at = (d: number, lo: number, hi: number) => `${(d < 0 ? lo : d > 0 ? 1 - hi : (lo + 1 - hi) / 2) * 100}%`;
  // The picture turns and flips about its block's centre, as the block does.
  const turn = {
    transform: `rotate(${block.angle ?? 0}deg) scale(${block.flipX ? -1 : 1}, ${block.flipY ? -1 : 1})`,
    transformOrigin: `${(block.x + block.w / 2 - box.x) * k}px ${(block.y + block.h / 2 - box.y) * k}px`,
  };
  return (
    <div className="crop" style={{ left: box.x * k, top: box.y * k, width: box.w * k, height: box.h * k, ...turn }}>
      <img className="dim" src={src} alt="" draggable={false} />
      <img src={src} alt="" draggable={false} style={{ clipPath: `inset(${inset})` }} />
      <div style={{ inset }} onPointerDown={grip} onPointerMove={(e) => trim(e, block, 0, 0)} />
      {[-1, 0, 1].flatMap((dy) =>
        [-1, 0, 1].map(
          (dx) =>
            (dx || dy) !== 0 && (
              <i key={`${dx}${dy}`} className="end" style={{ left: at(dx, l, r), top: at(dy, t, b) }} onPointerDown={grip} onPointerMove={(e) => trim(e, block, dx, dy)} />
            ),
        ),
      )}
    </div>
  );
}

