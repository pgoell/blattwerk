// The size of a Selbstkontrolle's snake, caterpillar or train, shared by the drawing and the height.

export type ShapeLook = "snake" | "caterpillar" | "train";

const CELL = {
  snake: { cols: 6, dx: 44, dy: 44, pad: 8 },
  caterpillar: { cols: 5, dx: 30, dy: 46, pad: 8 },
  train: { cols: 4, dx: 72, dy: 58, pad: 8 },
} as const;

export function shapeBox(look: ShapeLook, n: number) {
  const cell = CELL[look];
  const cols = Math.min(cell.cols, Math.max(n, 1));
  const rows = Math.max(1, Math.ceil(Math.max(n, 1) / cols));
  return { ...cell, cols, rows, w: cols * cell.dx + cell.pad * 2, h: rows * cell.dy + cell.pad * 2 };
}

// Centres of `n` items, winding back on every other row so a snake turns at the edge.
export function wound(n: number, cols: number, dx: number, dy: number, ox: number, oy: number): [number, number][] {
  return Array.from({ length: n }, (_, i) => {
    const row = Math.floor(i / cols);
    const along = i % cols;
    const col = row % 2 ? cols - 1 - along : along;
    return [ox + col * dx, oy + row * dy];
  });
}
