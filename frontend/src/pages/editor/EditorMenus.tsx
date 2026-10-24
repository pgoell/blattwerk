// The tour, the zoom list, and the menus.
import { flushSync } from "react-dom";
import Menu from "../../components/Menu";
import ZoomList from "../../components/ZoomList";
import Tour from "../../components/Tour";
import type { Axis } from "../../sheet";
import { useTools } from "./useTools";

export default function EditorMenus({ s: session }: { s: ReturnType<typeof useTools> }) {
  const blockMenu = session.blockMenu;
  const blocks = session.blocks;
  const editing = session.editing;
  const fit = session.fit;
  const fitPage = session.fitPage;
  const guide = session.guide;
  const hist = session.hist;
  const items = session.items;
  const k = session.k;
  const late = session.late;
  const lens = session.lens;
  const mathBlocks = session.mathBlocks;
  const mathMenu = session.mathMenu;
  const menu = session.menu;
  const menuAt = session.menuAt;
  const mini = session.mini;
  const more = session.more;
  const pickedBox = session.pickedBox;
  const refit = session.refit;
  const rule = session.rule;
  const seen = session.seen;
  const sel = session.sel;
  const setLens = session.setLens;
  const setMathMenu = session.setMathMenu;
  const setMenu = session.setMenu;
  const setTab = session.setTab;
  const setTour = session.setTour;
  const show = session.show;
  const showLeft = session.showLeft;
  const showRight = session.showRight;
  const tab = session.tab;
  const thumbMenu = session.thumbMenu;
  const tools = session.tools;
  const tour = session.tour;
  const zoomTo = session.zoomTo;
  return (
    <>
      {tour && (
        <Tour
          seen={{ doc: hist.doc, blocks: blocks.length, sel: sel.length, editing: !!editing, tab }}
          show={(t) => {
            if (t === "Vorlagen") return showLeft(true);
            setTab(t);
            showRight(true);
          }}
          close={() => {
            localStorage.setItem("tour", "1");
            setTour(false);
          }}
        />
      )}
      {lens && (
        <ZoomList
          x={lens.x}
          y={lens.y}
          up={lens.up}
          current={Math.round((k * 2540) / 96)}
          onPercent={(p) => zoomTo((p * 96) / 2540 / fit)}
          onWidth={() => zoomTo(1)}
          onFit={fitPage}
          onClose={() => setLens(undefined)}
        />
      )}
      {mathMenu && (
        <Menu
          x={mathMenu.x}
          y={mathMenu.y}
          up
          items={mathBlocks}
          onClose={() => setMathMenu(undefined)}
          onElsewhere={() => setMathMenu(undefined)}
        />
      )}
      {menu && (
        <Menu
          x={menu.x}
          y={menu.y}
          // A command picked in "Mehr" first ends what is written in, as the press of its button in the bar does:
          // the menu has just handed the focus back to it.
          items={
            menu.more
              ? more.map((item) => ({
                  ...item,
                  run: () => {
                    if (document.activeElement?.closest(".block")) (document.activeElement as HTMLElement).blur();
                    item.run();
                  },
                }))
              : items
          }
          // The row of the block menu only, over the picked blocks: not on the page, thumb, rule or cells menus.
          tools={blockMenu ? mini : undefined}
          avoid={blockMenu ? pickedBox() : undefined}
          onClose={() => {
            setMenu(undefined);
            if (late.current) refit();
          }}
          // A right click beside the menu opens it anew on what lies there.
          onElsewhere={(x, y) => {
            flushSync(() => setMenu(undefined));
            // This way no `onClose` comes: the bar that waited under the menu is measured now.
            if (late.current) refit();
            const el = document.elementFromPoint(x, y);
            const n = el?.closest<HTMLElement>("[data-thumb]")?.dataset.thumb;
            const guide = el?.closest<HTMLElement>("[data-axis]");
            if (n) thumbMenu(+n, x, y);
            else if (guide) setMenu({ x, y, rule: { axis: guide.dataset.axis as Axis, i: +guide.dataset.i!, n: guide.dataset.page === undefined ? undefined : +guide.dataset.page } });
            else if (el?.closest(".desk")) menuAt(el, x, y);
          }}
        />
      )}
    </>
  );
}
