// What can be inserted, and the commands the bar folds under Mehr.
import { ArrowRightLeft, BrickWall, Calculator, Sigma, CircleHelp, Eye, Grid3x3, Clock3, ListChecks, Fullscreen, Layers, Heading, House, ImagePlus, Link2, MessageSquare, Disc3, Table2, Grid2x2Plus, Split, LayoutGrid, Orbit, Paintbrush, Rows3, Ruler, Smile, SquareDashedMousePointer, SquareSlash, Table, TriangleDashed, MoveRight, Type, UserPen, ZoomIn, ZoomOut } from "lucide-react";
import type { Item } from "../../components/Menu";
import { newSeed } from "../Maths";
import { INSERTS } from "../../insert";
import type { Command } from "./useMenus";
import { Tool } from "./Tool";
import { SHAPES, TYPES, span } from "./palette";
import { useMenus } from "./useMenus";

export function useTools(session: ReturnType<typeof useMenus>) {
  const brush = session.brush;
  const setBrush = session.setBrush;
  const part = session.part;
  const multi = session.multi;
  const setMulti = session.setMulti;
  const mathMenu = session.mathMenu;
  const setMathMenu = session.setMathMenu;
  const setLens = session.setLens;
  const leaf = session.leaf;
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
// The bar's commands that may fold, in the bar's order, and those of them that "Mehr" holds now. A menu has no
  // double click, so the brush picked there stays on, as after one on its button, until its ticked item is picked
  // again or Escape puts it down.
  const folding: Command[] = [
    ...clips,
    { label: "Format übertragen", icon: Paintbrush, disabled: !brush && !source, on: brush > 0, run: () => (brush ? setBrush(0) : (dip(part?.marks), setBrush(2))) },
    ...copies,
    lockIt,
    ...groups,
    { label: "Lösungen zeigen", icon: Eye, on: solved, run: () => setSolved(!solved) },
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
    { label: "Feedback", icon: MessageSquare, run: () => feedback.current!() },
    { label: "Varianten drucken", icon: Layers, run: () => openVariants(bar.current!.querySelector<HTMLElement>(".more")!) },
  ];
  const more = folding.slice(fits ?? folding.length);
  const inBar = (label: string) => !more.some((item) => item.label === label);
  // The maths blocks, picked from the "Mathe-Blöcke" menu.
  const mathBlocks: Item[] = [
    { label: "Zahlenmauer", icon: BrickWall, run: () => addInsert(INSERTS.zahlenmauer(newSeed())) },
    { label: "Zahlenhaus", icon: House, run: () => addInsert(INSERTS.zahlenhaus(newSeed())) },
    { label: "Zahlenkette", icon: Link2, run: () => addInsert(INSERTS.zahlenkette(newSeed())) },
    { label: "Pfeilbild", icon: ArrowRightLeft, run: () => addInsert(INSERTS.pfeilbild(newSeed())) },
    { label: "Operatorfeld", icon: Orbit, run: () => addInsert(INSERTS.operatorfeld(newSeed())) },
    { label: "Rechenrad", icon: Disc3, run: () => addInsert(INSERTS.rechenrad(newSeed())) },
    { label: "Rechentabelle", icon: Table2, run: () => addInsert(INSERTS.rechentabelle(newSeed())) },
    { label: "Magisches Quadrat", icon: LayoutGrid, run: () => addInsert(INSERTS.magischesquadrat(newSeed())) },
    { label: "Malquadrat", icon: Grid2x2Plus, run: () => addInsert(INSERTS.malquadrat(newSeed())) },
    { label: "Zerlegungsfeld", icon: Split, run: () => addInsert(INSERTS.zerlegungsfeld(newSeed())) },
    { label: "Halbschriftlich rechnen", icon: Split, run: () => addInsert(INSERTS.halbschriftlich(newSeed())) },
    { label: "Zehnerfeld", icon: Grid2x2Plus, run: () => addInsert(INSERTS.zehnerfeld(newSeed())) },
    { label: "Rechendreieck", icon: TriangleDashed, run: () => addInsert(INSERTS.rechendreieck(newSeed())) },
    { label: "Zahlenstrahl", icon: MoveRight, run: () => addInsert(INSERTS.zahlenstrahl(newSeed())) },
    { label: "Hunderterfeld", icon: Grid3x3, run: () => addInsert(INSERTS.hunderterfeld(newSeed())) },
    { label: "Uhr", icon: Clock3, run: () => addInsert(INSERTS.uhr(newSeed())) },
    { label: "Selbstkontrolle", icon: ListChecks, run: () => addInsert(INSERTS.selbstkontrolle(newSeed())) },
  ];
  // What can go on the page. A divider's name is its group's heading in Blattform's left panel.
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
      <i className="sep" data-name="Mathe" />
      <Tool icon={Calculator} label="Rechnen" data-tour="maths" onClick={addMaths} />
      <Tool
        icon={Sigma}
        label="Mathe-Blöcke"
        aria-haspopup="menu"
        aria-expanded={!!mathMenu}
        onClick={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          setMathMenu({ x: box.left, y: box.top - 4 });
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
    </>
  );
    return Object.assign(session, { folding, more, inBar, mathBlocks, tools });
}
