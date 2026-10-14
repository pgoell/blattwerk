// The format panel's settings for a Rechendreieck block: its triangles, its numbers and which fields are given.
import type { RechendreieckBlock } from "../sheet";
import type { RechendreieckProps } from "../rechendreieck";

export default function Rechendreieck({ block, apply }: { block: RechendreieckBlock; apply: (props: Partial<RechendreieckProps>, key?: string) => void }) {
  void block;
  void apply;
  return <h2>Rechendreieck</h2>;
}
