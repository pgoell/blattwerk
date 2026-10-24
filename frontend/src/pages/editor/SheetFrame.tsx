// One page on the desk: its blocks, its guide lines, and the handles when it is the page in use.
import type { CSSProperties } from "react";
import type { Page } from "../../sheet";
import { useTools } from "./useTools";
import SheetBlocks from "./SheetBlocks";
import Guides from "./Guides";
import PageChrome from "./PageChrome";

export default function SheetFrame({ s: session, p, n }: { s: ReturnType<typeof useTools>; p: Page; n: number }) {
  const across = session.across;
  const cellOf = session.cellOf;
  const down = session.down;
  const k = session.k;
  const page = session.page;
  const sheet = session.sheet;
  const sizes = session.sizes;
  const style = session.style;
  return (
    <>
            <div
              key={n}
              data-page={n}
              className={`sheet${cellOf(p) ? " grid" : ""}${n === page ? " on" : ""}`}
              ref={n === page ? sheet : undefined}
              style={{ width: sizes[n][0] * k, height: sizes[n][1] * k, "--cell": `${cellOf(p) * k}px`, "--across": `${across}px`, "--down": `${down}px` } as CSSProperties}
            >
      <SheetBlocks s={session} p={p} n={n} />
      <Guides s={session} p={p} n={n} />
      <PageChrome s={session} p={p} n={n} />
    </div>

    </>
  );
}
