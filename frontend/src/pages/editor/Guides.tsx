// The guide lines on a page: the sheet's, and the page's own.
import type { Page } from "../../sheet";
import { NONE } from "./palette";
import { useTools } from "./useTools";

export default function Guides({ s: session, p, n }: { s: ReturnType<typeof useTools>; p: Page; n: number }) {
  const at = session.at;
  const drop = session.drop;
  const grip = session.grip;
  const guides = session.guides;
  const k = session.k;
  const left = session.left;
  const page = session.page;
  const rule = session.rule;
  const setMenu = session.setMenu;
  const sizes = session.sizes;
  const slide = session.slide;
  const sliding = session.sliding;
  const style = session.style;
  const top = session.top;
  return (
    <>
              {/* The sheet's guide lines lie on every page; a page's own are drawn dotted. */}
              {[undefined, n].flatMap((at) =>
                (["x", "y"] as const).flatMap((axis) =>
                  // A sheet's line past a smaller page is not drawn there, unless its tab is held on that page: the
                  // tab must stay to hear its letting go (#525).
                  (at === undefined ? guides : (p.guides ?? NONE))[axis].map((mm, i) => (at === undefined && mm > sizes[n][axis === "x" ? 0 : 1] && sliding.current !== `${n}${axis}${i}`) || (
                    <i key={`${at}${axis}${i}`} className={`rule ${axis}${at === undefined ? "" : " own"}`} style={axis === "x" ? { left: mm * k } : { top: mm * k }}>
                      <b
                        data-axis={axis}
                        data-i={i}
                        data-page={at}
                        // The right button drags nothing: its menu removes this one line, and picks no block.
                        onPointerDown={(e) => e.button === 0 && ((sliding.current = `${n}${axis}${i}`), grip(e))}
                        onPointerMove={(e) => slide(e, axis, i, at)}
                        onLostPointerCapture={() => ((sliding.current = ""), drop(axis, i, at))}
                        onContextMenu={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setMenu({ x: e.clientX, y: e.clientY, rule: { axis, i, n: at } });
                        }}
                      >
                        {mm}
                      </b>
                    </i>
                  )),
                ),
              )}
    </>
  );
}
