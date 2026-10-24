// The editor's frame: the keys, the focus, and the sheet around the panels.
import type { ReactNode } from "react";
import { Whole, Words } from "../../sheet";
import { useTools } from "./useTools";

export default function EditorMain({ s: session, children }: { s: ReturnType<typeof useTools>; children: ReactNode }) {
  const brush = session.brush;
  const drawers = session.drawers;
  const drawnRight = session.drawnRight;
  const field = session.field;
  const hist = session.hist;
  const inPanel = session.inPanel;
  const leaf = session.leaf;
  const learnt = session.learnt;
  const mergeKey = session.mergeKey;
  const pan = session.pan;
  const panning = session.panning;
  const setEditing = session.setEditing;
  return (
    // The Lernwörter reach every Lineatur that draws them, on the pages and on their thumbnails.
    <>
    <Words.Provider value={learnt}>
    <Whole.Provider value={hist.doc}>
    <main
      className={`editor${leaf ? " leaf" : ""}${brush ? " brush" : ""}${pan ? " pan" : ""}${panning ? " panning" : ""}${drawnRight ? " drawn" : ""}`}
      data-ready="1"
      // The keys end a run of changes as a press of the mouse does: when they take the focus elsewhere, and when
      // they press a button, also one that finds nothing to change. The next change is a step of its own.
      onFocusCapture={() => (mergeKey.current = "")}
      onClickCapture={() => (mergeKey.current = "")}
      // So does each value picked in a list, also when the arrows walk the list with no press between.
      onChangeCapture={(e) => (e.target as Element).matches("select") && (mergeKey.current = "")}
      onPointerDown={(e) => {
        mergeKey.current = "";
        inPanel.current = !!(e.target as Element).closest(".panel");
        // The browser tells the field only later where the caret went, and the field hears nothing once the panel
        // has the focus: a look picked there would go to the word the caret has left. So the field reads it now.
        if (inPanel.current && field.current) document.dispatchEvent(new Event("selectionchange"));
        // What is written in lost the focus to the panel and has no blur left to end it: a press beside the panel
        // and the blocks, as on the title, ends it.
        if (!inPanel.current && document.activeElement?.closest(".panel") && !(e.target as Element).closest(".block")) setEditing("");
      }}
      // A button pressed with the mouse does not take the focus, as PowerPoint's ribbon does not: Enter and Tab stay
      // the sheet's. A dialog's buttons are its own. What had the focus loses it to the main mouse button as before,
      // but a button of the format panel leaves it where it is: a text, a Lineatur or a cell being written in keeps
      // the caret, and a number of the panel its draft. So does the panel's bare ground, where a press on a disabled
      // button lands: a press there may also be the one that shuts a list or a colour picker with no pick, and its
      // control must keep the focus for the next key to give it back.
      onMouseDown={(e) => {
        const target = e.target as Element;
        const button = target.closest("button");
        const panel = target.closest(".panel");
        // A text being written in stays open while a drawer's button in the bar opens the drawer with its format.
        // A number of the panel does lose the focus to it, and so lands before the drawer shuts. The text stays open
        // under "Mehr" as well, until a command is picked there.
        const pin = target.closest(drawers ? ".pin, .more" : ".more") && document.activeElement?.closest(".block");
        if (panel && !button && !target.closest("input, select, textarea, label") && document.activeElement?.closest(".block, .panel select, .panel input[type=color]")) return e.preventDefault();
        if (e.defaultPrevented || !button || button.closest("dialog")) return;
        e.preventDefault();
        if (!e.button && !pin && !(panel && document.activeElement?.closest(".block, .panel"))) (document.activeElement as HTMLElement | null)?.blur();
      }}
    >
      {children}
    </main>
    </Whole.Provider>
    </Words.Provider>

    </>
  );
}
