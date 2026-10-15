// A sheet's marked total score boxes follow its task boxes: when the tasks' points change, each total moves by the same sum.
import type { Block, Doc, PointsBlock } from "./sheet";

const isPoints = (b: Block): b is PointsBlock => b.type === "points";
const pointsOf = (doc: Doc) => doc.pages.flatMap((p) => p.blocks.filter(isPoints));

// The change of the task boxes moves every marked total, as long as the set of boxes stays and no total was set by hand.
// A sheet with no marked total stays as it is.
export function totals(before: Doc, after: Doc): Doc {
  const boxes = pointsOf(before);
  const totalIds = new Set(boxes.filter((b) => b.props.total === true).map((b) => b.id));
  if (totalIds.size === 0) return after;
  const was = new Map(boxes.map((b) => [b.id, b.props.max]));
  const now = pointsOf(after);
  if (now.length !== boxes.length || now.some((b) => !was.has(b.id))) return after;
  if (now.some((b) => totalIds.has(b.id) && b.props.max !== was.get(b.id))) return after;
  const delta = now.reduce((sum, b) => (totalIds.has(b.id) ? sum : sum + b.props.max - (was.get(b.id) ?? 0)), 0);
  if (delta === 0) return after;
  const pages = after.pages.map((p) =>
    p.blocks.some((b) => isPoints(b) && totalIds.has(b.id))
      ? { ...p, blocks: p.blocks.map((b) => (isPoints(b) && totalIds.has(b.id) ? ({ ...b, props: { ...b.props, max: Math.min(999, Math.max(1, (was.get(b.id) ?? 0) + delta)) } } as Block) : b)) }
      : p,
  );
  return { ...after, pages };
}
