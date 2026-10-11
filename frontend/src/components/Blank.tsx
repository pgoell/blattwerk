import Logo from "./Logo";

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

// The editor while a sheet loads: its frame, empty, with a white page where the first page comes to lie. `late`
// is whether the loading has taken half a second: then the page says so. The account, the editor's script and the
// sheet each draw this anew, so the clock is not its own (App.tsx).
export default function Blank({ late }: { late: boolean }) {
  const { leafy, side } = opening();
  const drawers = DRAWERS.matches;
  const leaf = leafy && !drawers;
  // A phone's bar wraps, and its height is what its buttons wrap to; its panel is as high as what it opens with.
  // So there the frame holds what the editor's bar and panel hold when they open (the `.top` and the `.panel` in
  // Editor.tsx, in the same order), dead and unseen, and the same styles lay it out. The hint's word comes from
  // the styles: it is the word a test waits for to know that the editor stands.
  const phone = matchMedia("(max-width: 700px)").matches;
  const ib = (n: number) => Array.from({ length: n }, (_, i) => <i key={i} className="ib" />);
  return (
    <main className={`editor${leaf ? " leaf" : ""}`}>
      <header>
        {phone ? (
          <div className="top" inert aria-hidden>
            <span className="brand">
              <Logo />
              <svg width={16} height={16} />
            </span>
            {ib(1)}
            <input type="text" />
            <span className="hint" />
            {ib(2)}
            <i className="sep" />
            {ib(9)}
            <i className="sep" />
            {ib(2)}
            <button className="zoom">100 %</button>
            {ib(5)}
            <span className="pdf">
              <button>
                <svg width={14} height={14} />
                Lösungen
              </button>
              <button>
                <svg width={14} height={14} />
                PDF
              </button>
            </span>
          </div>
        ) : (
          <div className="top" />
        )}
      </header>
      {(leaf || side) && !drawers && <aside className="left" />}
      <div className="stage">
        <div className="desk">
          <div className="sheet blank" role="status">
            {late && "Lädt"}
          </div>
        </div>
      </div>
      {phone ? (
        <aside className="panel" inert aria-hidden>
          <div className="tabs">
            <button>Format</button>
            <button>Ansicht</button>
          </div>
          <p className="hint">Wähle etwas auf dem Blatt aus, um es zu formatieren.</p>
        </aside>
      ) : (
        !drawers && <aside className="panel" />
      )}
    </main>
  );
}
