// What is picked, the brush, the open field, and which panels are open.
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ArrowRight } from "lucide-react";
import { DRAWERS, opening } from "../../components/Blank";
import type { EditorView } from "prosemirror-view";
import { open } from "../../saves";
import type { Axis } from "../../sheet";
import type { Marks, Picked } from "../Field";
import type { Coat } from "./palette";
import { TABS, whenTurned } from "./palette";
import { useDocument } from "./useDocument";

export function useSelectionState(session: ReturnType<typeof useDocument>) {
  const redo = (...a: any[]) => (session as Record<string, any>).redo(...a);
  const undo = (...a: any[]) => (session as Record<string, any>).undo(...a);
  const rule = (...a: any[]) => (session as Record<string, any>).rule(...a);
// Whether a new guide line or grid is for the page in use alone.
  const [own, setOwn] = useState(false);
  const [at, setAt] = useState(0);
  // The pages chosen in the panel Seiten, with the page in use among them.
  const [chosen, setChosen] = useState<number[]>([]);
  // A thumbnail being dragged: the page it shows, the gap between the thumbnails it would drop into, and whether
  // the line stands after the thumbnail before that gap.
  const [haul, setHaul] = useState<{ from: number; slot: number; after: boolean }>();
  const [ids, setIds] = useState<string[]>([]);
  const [targets, setTargets] = useState<HTMLElement[]>([]);
  // The blocks that stay put. Moveable reads a selector as its first match only, so it gets the elements.
  const [rest, setRest] = useState<HTMLElement[]>([]);
  // The format painter: the look it picked up, as it was then, and whether it is on: 1 for one block, 2 until ended.
  const [coat, setCoat] = useState<Coat>();
  const [brush, setBrush] = useState(0);
  // What the words picked in a field have of their own, read before the press on the brush ends the field.
  const wet = useRef<Marks>(undefined);
  // Opens a text's field for a drag of the brush, from the latest render: the drag's listeners outlive the press.
  const openNow = useRef((_id: string, _el: Element) => {});
  const [editing, setEditing] = useState("");
  // The stone of a Zahlenmauer opened by a double click: its block, wall and stone, the number as typed, and its box in the block.
  const [stone, setStone] = useState<{ id: string; wall: number; at: number; text: string; box: number[] } | null>(null);
  // Whether the last press was a finger's, and where the handles of the picked table's range stand.
  const [finger, setFinger] = useState(false);
  const [grips, setGrips] = useState<{ corner: string; x: number; y: number }[]>([]);
  // The cell of the table being edited, counted row by row.
  const [slot, setSlot] = useState(0);
  // The far corner of a selection of cells in the table being edited, and whether a drag picks cells.
  const [reach, setReach] = useState<number | undefined>(undefined);
  const cellDrag = useRef(false);
  // A press with the brush in the open text picks its words: Moveable must not drag the block by it.
  const brushing = useRef(false);
  // The element a brush press lands on: the text under Moveable's frame, not the frame.
  const brushed = useRef<Element | undefined>(undefined);
  // The heights of the rows of the picked table as its grid laid them out, in px.
  const [laid, setLaid] = useState("");
  // Where the caret stood in a cell that a new row or column moves to another place.
  const caret = useRef<number>(undefined);
  // Where the click that opened a text's field landed, on the screen: its caret goes there.
  const clicked = useRef<[number, number]>(undefined);
  // Whether the field that opens next has all its text picked.
  const entire = useRef(false);
  // A name line's words while it is written in, and the words it was opened with.
  const [words, setWords] = useState<string[]>([]);
  const wordsKept = useRef("");
  // The name line being written in, and the page it stands on.
  const nameWriting = useRef<{ id: string; n: number } | undefined>(undefined);
  // The field of the text being edited, and what is picked in it.
  const field = useRef<EditorView>(null);
  const [part, setPart] = useState<Picked>();
  // Whether the last press was in the format panel, with no key since: the field then stays open though it loses
  // the focus, and a select or a colour picked there hands the keys back.
  const inPanel = useRef(false);
  // The accent of a dead key that was the first key from the panel. The browser composes one only in a
  // control that can take text, and a colour or a list cannot, so the next letter is made with it here.
  const accent = useRef("");
  // What is written in stays open when it loses the focus to the panel: by the keys, or by a press, which on the
  // word beside a colour names nothing that takes the focus. So does it under the bar's menu "Mehr", which hands
  // the focus back when it shuts.
  const stays = (e: { relatedTarget: EventTarget | null }) => cellDrag.current || inPanel.current || !!(e.relatedTarget as Element | null)?.closest(menu?.more || menu?.cells ? ".panel, .menu" : ".panel");
  const sheet = useRef<HTMLDivElement>(null);
  // The text, the Lineatur or the cell being written in.
  const written = () => field.current ?? sheet.current?.querySelector<HTMLElement>("textarea:not([readonly])");
  // Gives the keys back from a control of the panel, as PowerPoint does: to what is written in, whose caret is
  // where it was, or else to the sheet.
  const back = (from: HTMLElement) => {
    const open = written();
    if (open) open.focus();
    else from.blur();
  };
  // Where an arrow, Home and End take the caret.
  const MOVES: Record<string, string[]> = {
    ArrowLeft: ["left", "character"],
    ArrowRight: ["right", "character"],
    ArrowUp: ["backward", "line"],
    ArrowDown: ["forward", "line"],
    Home: ["backward", "lineboundary"],
    End: ["forward", "lineboundary"],
  };
  // Does in what is written in what a key does there that types no letter, and says whether it did. The browser
  // still counts the key that gave the focus back as the control's: only a letter follows the focus by itself. A
  // text's field takes its own keys first, as Ctrl+B. Deleting and the caret's moves are the browser's, done by hand.
  // Any other key with Ctrl is the browser's too and follows the focus by itself, as Ctrl+X or Ctrl+Backspace.
  const act = (e: KeyboardEvent) => {
    const view = field.current;
    const mod = e.ctrlKey || e.metaKey;
    const erase = e.key === "Backspace" || e.key === "Delete";
    if (e.altKey || !(mod || erase || MOVES[e.key])) return false;
    if (view?.someProp("handleKeyDown", (f) => f(view, e))) return true;
    const key = e.key.toLowerCase();
    // Undo and redo of a text and a cell are the sheet's, as with the second key: the browser's own would run in
    // their place. A Lineatur's are the browser's.
    if (mod && (key === "z" || key === "y") && document.activeElement!.closest(".ProseMirror, .table")) {
      (key === "y" || e.shiftKey ? redo : undo)();
      return true;
    }
    // Ctrl and an arrow step by a word. A select would walk by it.
    const word = e.ctrlKey && (e.key === "ArrowLeft" || e.key === "ArrowRight");
    if (mod && !word) return false;
    if (erase) document.execCommand(e.key === "Delete" ? "forwardDelete" : "delete");
    else getSelection()!.modify(e.shiftKey ? "extend" : "move", MOVES[e.key][0], word ? "word" : MOVES[e.key][1]);
    return true;
  };
  const [multi, setMulti] = useState(false);
  // The right click's menu and where it stands: a thumbnail's with `thumb`, its page, else the one for blocks. With
  // `more` it is the bar's menu instead, of the commands the bar has no room for.
  const [menu, setMenu] = useState<{ x: number; y: number; thumb?: number; more?: boolean; cells?: boolean; cell?: number; rule?: { axis: Axis; i: number; n?: number } }>();
  const [mathMenu, setMathMenu] = useState<{ x: number; y: number }>();
  const [lens, setLens] = useState<{ x: number; y: number; up: boolean }>();
  const [tab, setTab] = useState(TABS[0]);
  // A block picked on the list's tab shows its settings, as in PowerPoint (#429).
  const idKey = ids.join();
  useEffect(() => {
    if (idKey) setTab((now) => (now === "Lernwörter" ? "Format" : now));
  }, [idKey]);
  // So does a click on a block that is picked already: the pick does not change then.
  useEffect(() => {
    if (tab !== "Lernwörter") return;
    const down = (e: Event) => {
      if (e.target instanceof Element && e.target.closest(".block") && sheet.current?.contains(e.target)) setTab("Format");
    };
    document.addEventListener("pointerdown", down, true);
    return () => document.removeEventListener("pointerdown", down, true);
  }, [tab]);
  // Whether several blocks line up with the page, not with each other.
  const [onPage, setOnPage] = useState(false);
  const [pane, setPane] = useState(true);
  // Blattform lays the editor out anew on a wide window: the left panel holds what can be inserted, and Start,
  // Ansicht and Vorlagen in the bar pick what the panels show. `side` then means that Vorlagen is open. `opening`
  // tells when the layout is that one and how the panel of pages and templates starts.
  const { leafy } = opening();
  const [side, setSide] = useState(() => opening().side);
  // Upright, at most one panel is open and both start shut. `side` and `pane` keep what the window on its side shows.
  const drawers = useSyncExternalStore(whenTurned, () => DRAWERS.matches);
  const [drawer, setDrawer] = useState<"left" | "right">();
  // The finger on a drawer's swipe: where it came down, which drawer it may open or shut, and whether it has.
  const swipe = useRef<{ x: number; y: number; open?: "left" | "right"; shut?: "left" | "right"; decided?: boolean } | undefined>(undefined);
    return Object.assign(session, { own, setOwn, at, setAt, chosen, setChosen, haul, setHaul, ids, setIds, targets, setTargets, rest, setRest, coat, setCoat, brush, setBrush, wet, openNow, editing, setEditing, stone, setStone, finger, setFinger, grips, setGrips, slot, setSlot, reach, setReach, cellDrag, brushing, brushed, laid, setLaid, caret, clicked, entire, words, setWords, wordsKept, nameWriting, field, part, setPart, inPanel, accent, stays, sheet, written, back, MOVES, act, multi, setMulti, menu, setMenu, mathMenu, setMathMenu, lens, setLens, tab, setTab, idKey, onPage, setOnPage, pane, setPane, leafy, side, setSide, drawers, drawer, setDrawer, swipe });
}
