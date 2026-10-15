// A sheet's total score box follows its task boxes: when the tasks' points change, the total moves by the same sum.
import type { Block, Doc, PointsBlock } from "./sheet";

const isPoints = (b: Block): b is PointsBlock => b.type === "points";
const pointsOf = (doc: Doc) => doc.pages.flatMap((p) => p.blocks.filter(isPoints));

// The total is the max that equals the sum of the other maxes. It needs a box with another max too.
function totalOf(boxes: PointsBlock[]): number | undefined {
  const maxes = [...new Set(boxes.map((b) => b.props.max))];
  return maxes.find((s) => {
    const others = boxes.filter((b) => b.props.max !== s);
    return others.length > 0 && others.length < boxes.length && others.reduce((sum, b) => sum + b.props.max, 0) === s;
  });
}

// The change of the task boxes moves every total box, as long as the set of boxes stays and no total was set by hand.
export function totals(before: Doc, after: Doc): Doc {
  const boxes = pointsOf(before);
  const total = totalOf(boxes);
  if (total === undefined) return after;
  const was = new Map(boxes.map((b) => [b.id, b.props.max]));
  const now = pointsOf(after);
  if (now.length !== boxes.length || now.some((b) => !was.has(b.id))) return after;
  const totalIds = new Set(boxes.filter((b) => b.props.max === total).map((b) => b.id));
  if (now.some((b) => totalIds.has(b.id) && b.props.max !== was.get(b.id))) return after;
  const delta = now.reduce((sum, b) => (totalIds.has(b.id) ? sum : sum + b.props.max - (was.get(b.id) ?? 0)), 0);
  if (delta === 0) return after;
  const max = Math.min(999, Math.max(1, total + delta));
  const pages = after.pages.map((p) => (p.blocks.some((b) => isPoints(b) && totalIds.has(b.id)) ? { ...p, blocks: p.blocks.map((b) => (isPoints(b) && totalIds.has(b.id) ? ({ ...b, props: { ...b.props, max } } as Block) : b)) } : p));
  return { ...after, pages };
}
