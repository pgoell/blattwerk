// The sheet document and how a page of it draws, shared by the editor and the list's thumbnails.

// One page's blocks, as the sheet document stores them: mm from the page's top-left corner.
export type Box = { id: string; x: number; y: number; w: number; h: number; z: number; locked: boolean };
export type Kind = "rect" | "rounded" | "circle" | "line" | "arrow";
export type Corner = "nw" | "ne" | "sw" | "se";
export type Align = "left" | "center" | "right";
export type TextBlock = Box & { type: "text"; props: { text: string; size: number; align: Align } };
// A line or arrow runs from the corner `from` of its box to the opposite one.
export type ShapeBlock = Box & { type: "shape"; props: { kind: Kind; fill: string; stroke: string; strokeWidth: number; from?: Corner } };
export type Block = TextBlock | ShapeBlock;
export type Axis = "x" | "y";
// The teacher's own guide lines, in mm.
export type Guides = Record<Axis, number[]>;
// A page can have guide lines of its own, beside the sheet's, and a grid of its own in place of the sheet's.
export type Page = { blocks: Block[]; guides?: Guides; grid?: number };
// The pages, and what every page shares: guide lines and the grid's cell in mm (0 for none).
export type Doc = { pages: Page[]; guides: Guides; grid: number };
// The server counts a sheet's saved documents in `version`.
export type Sheet = { id: number; title: string; updated: string; version: number; doc: Doc };

export const W = 210;
export const H = 297;
export const PT = 25.4 / 72; // mm per point
export const EMPTY: Doc = { pages: [{ blocks: [] }], guides: { x: [], y: [] }, grid: 0 };
// The editor's last save. The list waits for it, so it shows the sheet as it was left.
export const last = { save: Promise.resolve() as Promise<unknown> };

// Templates saved before sheets had pages hold one page's blocks.
export const read = ({ pages, blocks, guides, grid }: Doc & { blocks?: Block[] }): Doc => ({ pages: pages ?? [{ blocks: blocks! }], guides, grid });
export const isLine = (b: Block): b is ShapeBlock => b.type === "shape" && (b.props.kind === "line" || b.props.kind === "arrow");
// Whether a line's start, or its end, sits at the bottom (axis 0) or the right (axis 1) of its box.
export const far = (b: ShapeBlock, axis: 0 | 1, end: boolean) => ((b.props.from ?? "nw")[axis] === "se"[axis]) !== end;

export function Shape({ block, k }: { block: ShapeBlock; k: number }) {
  const { kind, fill, stroke, strokeWidth } = block.props;
  if (isLine(block)) {
    // Drawn from the start corner along its own axis; a wide unseen stroke is what a finger grabs.
    const [x, y] = [far(block, 1, false) ? block.w : 0, far(block, 0, false) ? block.h : 0];
    const angle = (Math.atan2(block.h - 2 * y, block.w - 2 * x) * 180) / Math.PI;
    const length = Math.hypot(block.w, block.h);
    const head = kind === "arrow" ? 2 + strokeWidth * 3 : 0;
    return (
      <svg>
        <g transform={`scale(${k}) translate(${x} ${y}) rotate(${angle})`} stroke={stroke} strokeWidth={strokeWidth} fill={stroke}>
          <line x2={length} stroke="transparent" strokeWidth={10} />
          <line x2={length - head} />
          {head > 0 && <polygon stroke="none" points={`${length},0 ${length - head},${-head / 2} ${length - head},${head / 2}`} />}
        </g>
      </svg>
    );
  }
  return (
    <div
      style={{
        background: fill,
        border: `${strokeWidth * k}px solid ${stroke}`,
        borderRadius: kind === "circle" ? "50%" : kind === "rounded" ? 4 * k : 0,
      }}
    />
  );
}

// Page one, drawn small at `k` pixels per mm.
export function Thumb({ doc, k }: { doc: Doc; k: number }) {
  return (
    <div className="thumb" style={{ width: W * k, height: H * k }}>
      {read(doc).pages[0].blocks.map((b) => (
        <div key={b.id} className="block" style={{ left: b.x * k, top: b.y * k, width: b.w * k, height: b.h * k, zIndex: b.z }}>
          {b.type === "text" ? <p style={{ fontSize: b.props.size * PT * k, textAlign: b.props.align }}>{b.props.text}</p> : <Shape block={b} k={k} />}
        </div>
      ))}
    </div>
  );
}
