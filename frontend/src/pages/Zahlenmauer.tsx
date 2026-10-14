// The format panel's settings for a Zahlenmauer block: its walls, its numbers and which stones are given.
import type { ZahlenmauerBlock, ZahlenmauerProps } from "../sheet";
import { sane } from "../zahlenmauer";

// STUB: the panel's part replaces this body.
export default function Zahlenmauer({ block, apply }: { block: ZahlenmauerBlock; apply: (props: Partial<ZahlenmauerProps>, key?: string) => void }) {
  const p = sane(block.props);
  return (
    <>
      <h2>Zahlenmauer</h2>
      <button className={p.empty ? "on" : ""} aria-pressed={p.empty} onClick={() => apply({ empty: !p.empty })}>
        Leer
      </button>
    </>
  );
}
