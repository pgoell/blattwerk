// The list beside the zoom: the grid, and the guide lines. A modal dialog like the menus: a pick shuts it, so the
// sheet is free again for the new line.
import { useLayoutEffect, useRef } from "react";
import { Eraser, SeparatorHorizontal, SeparatorVertical } from "lucide-react";
import { beside } from "../../components/useBackdrop";
import { GRIDS, NONE } from "./palette";
import { useTools } from "./useTools";

export default function RasterMenu({ s: session }: { s: ReturnType<typeof useTools> }) {
  const { x, y, up } = session.raster!;
  const own = session.own;
  const setOwn = session.setOwn;
  const grid = session.grid;
  const guides = session.guides;
  const mine = session.mine;
  const page = session.page;
  const pages = session.pages;
  const rule = session.rule;
  const rules = session.rules;
  const turn = session.turn;
  const update = session.update;
  const ref = useRef<HTMLDialogElement>(null);
  useLayoutEffect(() => {
    const d = ref.current!;
    if (!d.open) d.showModal();
    // Near the right or the bottom edge the list moves back into the window.
    const box = d.getBoundingClientRect();
    d.style.left = `${Math.max(0, Math.min(x, innerWidth - box.width))}px`;
    d.style.top = `${Math.max(0, Math.min(up ? y - box.height : y, innerHeight - box.height))}px`;
  }, [x, y, own]);
  // Shuts the list at once: the browser's `close` comes a task later, and until then the list's button keeps the focus.
  const shut = () => {
    ref.current?.close();
    session.setRaster(undefined);
  };
  // In a window of another size the list's place is no longer right: it shuts.
  useLayoutEffect(() => {
    addEventListener("resize", shut);
    return () => removeEventListener("resize", shut);
  }, []);
  const pick = (run: () => void) => () => {
    shut();
    run();
  };
  const lines = own ? mine : guides;
  return (
    <dialog
      ref={ref}
      className="raster"
      aria-label="Raster und Hilfslinien"
      onClose={() => session.setRaster(undefined)}
      onKeyDown={(e) => {
        // An Escape after the list has shut is the sheet's.
        if (e.key !== "Escape" || !ref.current!.open) return;
        e.preventDefault();
        e.stopPropagation();
        shut();
      }}
      onMouseDown={(e) => e.button !== 2 && beside(ref.current!, e) && shut()}
    >
      {/* A page's own grid stands in for the sheet's; "Wie Blatt" gives the page the sheet's again. */}
      <div className="seg">
        <button className={own ? "" : "on"} aria-pressed={!own} onClick={() => setOwn(false)}>Alle Seiten</button>
        <button className={own ? "on" : ""} aria-pressed={own} onClick={() => setOwn(true)}>Nur diese Seite</button>
      </div>
      <h2>Raster</h2>
      <div className="seg">
        {(own ? [undefined, ...GRIDS] : GRIDS).map((c) => {
          const on = (own ? pages[page].grid : grid) === c;
          return (
            <button key={c ?? "sheet"} className={on ? "on" : ""} aria-pressed={on} onClick={pick(() => (own ? turn((p) => ({ ...p, grid: c })) : update((doc) => ({ ...doc, grid: c! }))))}>
              {c === undefined ? "Wie Blatt" : c ? `${c} mm` : "Aus"}
            </button>
          );
        })}
      </div>
      <h2>Hilfslinien</h2>
      <div className="acts">
        <button onClick={pick(() => rule("x"))}>
          <SeparatorVertical size={14} aria-hidden />
          Senkrecht
        </button>
        <button onClick={pick(() => rule("y"))}>
          <SeparatorHorizontal size={14} aria-hidden />
          Waagerecht
        </button>
      </div>
      <button className="wide" disabled={!lines.x.length && !lines.y.length} onClick={pick(() => rules(own ? page : undefined, () => NONE))}>
        <Eraser size={14} aria-hidden />
        Alle entfernen
      </button>
      <p className="hint">Eine einzelne Hilfslinie entfernen: an ihrer Zahl vom Blatt ziehen oder mit der rechten Maustaste auf die Zahl klicken.</p>
    </dialog>
  );
}
