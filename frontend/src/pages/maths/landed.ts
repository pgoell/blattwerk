import type { MathsProps } from "../../sheet";

// What the editor does with owed maths clicks a later click carried and landed (#908).
// The maths page calls `owedLanded` and does not import the saver: the sheet model tests load that page in node,
// and the saver reads `window` as it loads. `useDocument` wires `dropOwed` in before a click can land.
let drop: (block: string, changes: Partial<MathsProps>[]) => void = () => {};
export const onOwedLanded = (fn: typeof drop) => void (drop = fn);
export const owedLanded = (block: string, changes: Partial<MathsProps>[]) => drop(block, changes);
