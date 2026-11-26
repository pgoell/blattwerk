// What can be inserted, and the commands the bar folds under Mehr.
import { useState, type MouseEvent } from "react";
import { BookA, Calculator, Files, Shapes, Sigma, CircleHelp, Grid3x3, Fullscreen, Heading, ImagePlus, MessageSquare, Paintbrush, Rows3, Ruler, Smile, SquareDashedMousePointer, SquareSlash, Table, Type, UserPen, ZoomIn, ZoomOut } from "lucide-react";
import type { Item } from "../../components/Menu";
import { newSeed } from "../Maths";
import { INSERTS } from "../../insert";
import type { Command } from "./useMenus";
import { Named, Tool } from "./Tool";
import { MORE_SHAPES, SHAPES, TYPES, span } from "./palette";
import { useMenus } from "./useMenus";

export function useTools(session: ReturnType<typeof useMenus>) {
  const brush = session.brush;
  const setBrush = session.setBrush;
  const part = session.part;
  const multi = session.multi;
  const setMulti = session.setMulti;
  const mathMenu = session.mathMenu;
  const setMathMenu = session.setMathMenu;
  const [shapeMenu, setShapeMenu] = useState<{ x: number; y: number }>();
  // The list a group of the tablet's rail opens beside itself.
  const [railMenu, setRailMenu] = useState<{ x: number; y: number; items: Item[] }>();
  const left = session.left;
  const showLeft = session.showLeft;
  const setLens = session.setLens;
  const leaf = session.leaf;
  const tab = session.tab;
  const setTab = session.setTab;
  const bar = session.bar;
  const fits = session.fits;
  const feedback = session.feedback;
  const tour = session.tour;
  const setTour = session.setTour;
  const solved = session.solved;
  const setSolved = session.setSolved;
  const name = session.name;
  const picker = session.picker;
  const source = session.source;
  const dip = session.dip;
  const pressed = session.pressed;
  const upload = session.upload;
  const addInsert = session.addInsert;
  const addMaths = session.addMaths;
  const openVariants = session.openVariants;
  const clips = session.clips;
  const copies = session.copies;
  const lockIt = session.lockIt;
  const groups = session.groups;
  const zoomBy = session.zoomBy;
  const fitPage = session.fitPage;
  const setMenu = session.setMenu;
// The bar's commands that may fold, in the bar's order, and those of them that "Mehr" holds now. A menu has no
  // double click, so the brush picked there stays on, as after one on its button, until its ticked item is picked
  // again or Escape puts it down.
  const folding: Command[] = [
    ...clips,
    { label: "Format übertragen", icon: Paintbrush, disabled: !brush && !source, on: brush > 0, run: () => (brush ? setBrush(0) : (dip(part?.marks), setBrush(2))) },
    ...copies,
    lockIt,
    ...groups,
    ...(leaf
      ? []
      : [
          { label: "Kleiner", icon: ZoomOut, run: () => zoomBy(-1) },
          // The bar's zoom button, which opens the list below "Mehr" as the button does in the bar.
          {
            label: "Zoom",
            run: () => {
              // The list gives the focus back to what has it when it opens: that is "Mehr", not the item just picked.
              const more = bar.current!.querySelector<HTMLElement>(".more")!;
              more.focus();
              const box = more.getBoundingClientRect();
              setLens({ x: box.left, y: box.bottom, up: false });
            },
          },
          { label: "Ganze Seite", icon: Fullscreen, run: fitPage },
          { label: "Größer", icon: ZoomIn, run: () => zoomBy(1) },
        ]),
    { label: "Rundgang", icon: CircleHelp, run: () => setTour(true) },
    // The form gives the focus back to what has it when it opens: "Mehr", as for the zoom.
    { label: "Feedback", icon: MessageSquare, run: () => (bar.current!.querySelector<HTMLElement>(".more")!.focus(), feedback.current!()) },
  ];
  const more = folding.slice(fits ?? folding.length);
  const inBar = (label: string) => !more.some((item) => item.label === label);
  const moreShapes: Item[] = MORE_SHAPES.map(([kind, label, icon]) => ({ label, icon, run: () => addInsert(INSERTS.shape(kind)) }));
  // What can go on the page. A divider's name is its group's heading in the wide window's left panel.
  const tools = (
    <>
      <Tool
        icon={SquareDashedMousePointer}
        label="Mehrere"
        data-tour="multi"
        className={multi ? "on" : ""}
        aria-pressed={multi}
        onClick={() => setMulti(!multi)}
      />
      <i className="sep" data-name="Einfügen" />
      <Tool icon={Type} label="Text" data-tour="text" onClick={() => addInsert(INSERTS.text())} />
      <Tool icon={Heading} label="Überschrift" onClick={() => addInsert(INSERTS.heading())} />
      <Tool icon={ImagePlus} label="Bild" onClick={() => picker.current!.click()} />
      <input
        ref={picker}
        type="file"
        accept={TYPES.join()}
        hidden
        onChange={(e) => {
          upload(e.target.files?.[0]);
          // The same picture can be picked again.
          e.target.value = "";
        }}
      />
      <Tool icon={Smile} label="Symbol" onClick={() => addInsert(INSERTS.symbol())} />
      <Tool icon={Table} label="Tabelle" onClick={() => addInsert(INSERTS.table())} />
      <i className="sep" data-name="Schule" />
      <Tool icon={Rows3} label="Lineatur" onClick={() => addInsert(INSERTS.ruling())} />
      <Tool icon={UserPen} label="Namenszeile" onClick={() => addInsert(INSERTS.name())} />
      <Tool icon={SquareSlash} label="Punkte" onClick={() => addInsert(INSERTS.points())} />
      <Tool icon={Grid3x3} label="Suchsel" onClick={() => addInsert(INSERTS.suchsel(newSeed()))} />
      {/* What makes exercises, a group to a subject. */}
      {/* The sheet's list of words is no block, so its tool opens the list in the panel at the right. A wide window
          has no tab for it; a narrow one has. */}
      {leaf && (
        <>
          <i className="sep" data-name="Deutsch" />
          <Tool icon={BookA} label="Lernwörter" className={tab === "Lernwörter" ? "on" : ""} aria-pressed={tab === "Lernwörter"} onClick={() => setTab(tab === "Lernwörter" ? "Format" : "Lernwörter")} />
        </>
      )}
      <i className="sep" data-name="Mathe" />
      <Tool icon={Calculator} label="Rechnen" data-tour="maths" onClick={addMaths} />
      <Tool
        icon={Sigma}
        label="Mathe-Blöcke"
        aria-haspopup="dialog"
        aria-expanded={!!mathMenu}
        onClick={(e) => {
          // Beside an upright list of tools the library opens to its right; over a row of them, above it.
          const box = e.currentTarget.getBoundingClientRect();
          const list = e.currentTarget.closest(".insert")?.getBoundingClientRect();
          setMathMenu(list ? { x: list.right + 8, y: Math.min(box.top, list.top + 60) } : { x: box.left - 120, y: box.top - 10, up: true });
        }}
      />
      <Tool icon={Ruler} label="Strecke" onClick={() => addInsert(INSERTS.strecke())} />
      <i className="sep" data-name="Formen" />
      <span className="shapes">
        {SHAPES.map(([kind, label, icon]) => (
          <Tool
            key={kind}
            icon={icon}
            label={label}
            onClick={() => addInsert(INSERTS.shape(kind))}
          />
        ))}
      </span>
      <Tool
        icon={Shapes}
        label="Weitere Formen"
        aria-haspopup="menu"
        aria-expanded={!!shapeMenu}
        onClick={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          setShapeMenu(shapeMenu ? undefined : { x: box.left, y: box.top - 4 });
        }}
      />
    </>
  );
  // The tablet held upright has a rail at its left instead: a group to a button, each with its name under its icon.
  // A group of several tools opens their list beside it, Mathe the library, and Seiten the drawer of pages.
  const lists = (items: Item[]) => (e: MouseEvent<HTMLButtonElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    setRailMenu({ x: box.right + 6, y: box.top, items });
  };
  const rail = (
    <>
      <Named icon={SquareDashedMousePointer} label="Mehrere" data-tour="multi" className={multi ? "on" : ""} aria-pressed={multi} onClick={() => setMulti(!multi)} />
      <Named
        icon={Type}
        label="Text"
        data-tour="text"
        aria-haspopup="menu"
        onClick={lists([
          { label: "Text", icon: Type, run: () => addInsert(INSERTS.text()) },
          { label: "Überschrift", icon: Heading, run: () => addInsert(INSERTS.heading()) },
        ])}
      />
      <Named
        icon={ImagePlus}
        label="Bild"
        aria-haspopup="menu"
        onClick={lists([
          { label: "Bild", icon: ImagePlus, run: () => picker.current!.click() },
          { label: "Symbol", icon: Smile, run: () => addInsert(INSERTS.symbol()) },
        ])}
      />
      <input
        ref={picker}
        type="file"
        accept={TYPES.join()}
        hidden
        onChange={(e) => {
          upload(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <Named
        icon={Rows3}
        label="Schreiben"
        aria-haspopup="menu"
        onClick={lists([
          { label: "Lineatur", icon: Rows3, run: () => addInsert(INSERTS.ruling()) },
          { label: "Namenszeile", icon: UserPen, run: () => addInsert(INSERTS.name()) },
          { label: "Punkte", icon: SquareSlash, run: () => addInsert(INSERTS.points()) },
          { label: "Suchsel", icon: Grid3x3, run: () => addInsert(INSERTS.suchsel(newSeed())) },
        ])}
      />
      <Named
        icon={Sigma}
        label="Mathe"
        data-tour="maths"
        aria-haspopup="dialog"
        aria-expanded={!!mathMenu}
        onClick={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          setMathMenu({ x: box.right + 8, y: Math.min(box.top, 120) });
        }}
      />
      <Named icon={Table} label="Tabelle" onClick={() => addInsert(INSERTS.table())} />
      <Named
        icon={Shapes}
        label="Formen"
        aria-haspopup="menu"
        onClick={lists([...SHAPES, ...MORE_SHAPES].map(([kind, label, icon]) => ({ label, icon, run: () => addInsert(INSERTS.shape(kind)) })))}
      />
      <Named icon={Files} label="Seiten" aria-pressed={left} className={left ? "on" : ""} onClick={() => showLeft(!left)} />
    </>
  );
  // What the library shows before its cards there: the two maths tools that are no cards of it.
  const mathLead: Exclude<Item, "sep">[] = [
    { label: "Rechnen", icon: Calculator, run: () => void addMaths() },
    { label: "Strecke", icon: Ruler, run: () => addInsert(INSERTS.strecke()) },
  ];
    return Object.assign(session, { folding, more, inBar, moreShapes, shapeMenu, setShapeMenu, tools, rail, railMenu, setRailMenu, mathLead });
}
