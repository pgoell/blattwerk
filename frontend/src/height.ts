// What a maths block's height is made of, in a module with no React: the MCP server (frontend/mcp) runs it in Node.
import type { MathsProps } from "./sheet";

export const PT = 25.4 / 72; // mm per point
// The side of a square of a written exercise, in mm.
export const KARO = 5;
// The height in mm a maths block needs for its exercises.
export function mathsHeight(p: MathsProps) {
  // With families, each family is one item of the grid: as tall as its most tasks, with a gap of 0.9 lines to the next.
  const sizes = new Map<number, number>();
  for (const e of p.exercises) if (!("sign" in e) && e.family !== undefined) sizes.set(e.family, (sizes.get(e.family) ?? 0) + 1);
  if (sizes.size) {
    const lines = Math.ceil(sizes.size / p.columns);
    return Math.max(10, Math.round(lines * (Math.max(...sizes.values()) * 1.8 + 0.9) * p.size * PT));
  }
  const lines = Math.ceil(p.exercises.length / p.columns);
  // A comparison is a row of its own, with no squared paper.
  const rows = Math.max(0, ...p.exercises.map((e) => ("sign" in e ? 0 : e.grid?.rows ?? 0)));
  return Math.max(10, Math.round(lines * (p.format === "written" ? (rows + 1) * KARO : p.size * PT * 2.4)));
}
