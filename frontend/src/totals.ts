// A sheet's marked total score boxes show the sum of its task boxes: every unmarked points box of the sheet.
import type { Block, Doc, PointsBlock } from "./sheet";

const isPoints = (b: Block): b is PointsBlock => b.type === "points";
const pointsOf = (doc: Doc) => doc.pages.flatMap((p) => p.blocks.filter(isPoints));
const isTotal = (b: PointsBlock) => b.props.total === true;

// The task boxes as id and max, so that an added, removed or changed task shows as a change.
const tasksOf = (doc: Doc) => pointsOf(doc).filter((b) => !isTotal(b)).map((b) => `${b.id}:${b.props.max}`).sort();

// Recomputes every marked total when the task boxes change. A sheet with no marked total stays as it is.
export function totals(before: Doc, after: Doc): Doc {
  const marked = [...pointsOf(before), ...pointsOf(after)].some(isTotal);
  if (!marked) return after;
  const old = tasksOf(before);
  const now = tasksOf(after);
  if (old.length === now.length && old.every((t, i) => t === now[i])) return after;
  // A total typed by hand in the same step wins, as when the panel sets a total and a task picked together.
  const was = new Map(pointsOf(before).filter(isTotal).map((b) => [b.id, b.props.max]));
  if (pointsOf(after).some((b) => isTotal(b) && was.has(b.id) && was.get(b.id) !== b.props.max)) return after;
  const tasks = pointsOf(after).filter((b) => !isTotal(b));
  if (tasks.length === 0) return after;
  const sum = Math.min(999, Math.max(1, tasks.reduce((n, b) => n + b.props.max, 0)));
  if (pointsOf(after).every((b) => !isTotal(b) || b.props.max === sum)) return after;
  const pages = after.pages.map((p) =>
    p.blocks.some((b) => isPoints(b) && isTotal(b))
      ? { ...p, blocks: p.blocks.map((b) => (isPoints(b) && isTotal(b) ? ({ ...b, props: { ...b.props, max: sum } } as Block) : b)) }
      : p,
  );
  return { ...after, pages };
}
