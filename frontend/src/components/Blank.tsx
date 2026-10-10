import { useEffect, useState } from "react";

// An iPad held upright: the panels are drawers over the desk. The same words as in styles.css.
export const DRAWERS = matchMedia("(orientation: portrait) and (min-width: 701px) and (max-width: 1099px)");
// How the editor opens. Blattform lays it out anew on a wide window, `leafy`, from the width of an iPad on its
// side: beside the green panel a narrower window has no room for the bar's one row. `side` is whether the panel of
// pages and templates starts open: not where it would lie over the desk, and not in Blattform at any width, for
// the window may grow or turn into that layout.
export const opening = () => {
  const blatt = document.documentElement.dataset.theme === "leaf";
  return { leafy: blatt && innerWidth >= 1024, side: innerWidth > 700 && !blatt };
};

// The editor while a sheet loads: its frame, empty, with a white page where the first page comes to lie. `since`
// is when the loading began: after half a second the page says so. The account, the editor's script and the sheet
// each draw this anew, so the clock is not its own.
export default function Blank({ since }: { since: number }) {
  const left = () => 500 - (performance.now() - since);
  const [late, setLate] = useState(() => left() <= 0);
  useEffect(() => {
    const timer = setTimeout(() => setLate(true), left());
    return () => clearTimeout(timer);
  }, []);
  const { leafy, side } = opening();
  const drawers = DRAWERS.matches;
  const leaf = leafy && !drawers;
  return (
    <main className={`editor${leaf ? " leaf" : ""}`}>
      <header>
        <div className="top" />
      </header>
      {(leaf || side) && !drawers && <aside className="left" />}
      <div className="stage">
        <div className="desk">
          <div className="sheet blank" role="status">
            {late && "Lädt"}
          </div>
        </div>
      </div>
      {!drawers && <aside className="panel" />}
    </main>
  );
}
