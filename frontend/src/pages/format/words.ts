// What a block that holds words says of its syllables, and a change that reaches every such block at once.
import { cellEntries, entries } from "../../bank";
import { boxed, parasOf, type Block } from "../../sheet";

// What a block that holds words says of its syllables: a text, a shape with text and a table.
export const worded = (b: Block) => (b.type === "table" ? b.props : boxed(b));
// A Lineatur takes the bows and the colours too, on its written line and on its Lernwörter list, Karo included.
export const ruled = (b: Block) => (b.type === "ruling" ? b.props : undefined);
export const syllabled = (b: Block) => ruled(b) ?? worded(b);
// A stored seed that is a finite number, or none: a seed that is no number counts as no seed.
export const seedOf = (n: unknown) => (typeof n === "number" && Number.isFinite(n) ? n : undefined);
// A text and a shape take it through `look`, a table through `style`: the key they share makes one undo step,
// so there is always one, the names of the props where none is given.
export const both =
  (
    held: Block[],
    look: (props: object, key?: string) => void,
    style: (type: Block["type"], props: object, key?: string, only?: string[]) => void,
  ) =>
  (props: object, key = Object.keys(props).join()) => {
    if (held.some(boxed)) look(props, key);
    if (held.some((b) => b.type === "table")) style("table", props, key);
    const rulings = held.filter((b) => b.type === "ruling").map((b) => b.id);
    if (rulings.length) style("ruling", props, key, rulings);
  };
// The solution words of a block: the cells of a table, or the words of a text or a shape, in reading order.
export const solutions = (b: Block) => (b.type === "table" ? cellEntries(b.props.cells, b.props.gaps) : entries(parasOf(boxed(b)!)));
