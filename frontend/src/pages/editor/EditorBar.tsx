// The bar: the title, the commands that fit, and the clash.
import { CircleHelp, ClipboardPaste, Copy, CopyPlus, Ellipsis, Eye, Group, FileCheck, FileDown, Layers, MessageSquare, Paintbrush, PanelLeft, PanelRight, Redo2, Scissors, Trash2, Undo2, Ungroup } from "lucide-react";
import Feedback from "../../components/Feedback";
import Variants from "../../components/Variants";
import { fresh } from "../../history";
import { newer } from "../../saves";
import Format from "../Format";
import { holdName, Tool } from "./Tool";
import { span, CLASH_BAR } from "./palette";
import { useTools } from "./useTools";

export default function EditorBar({ s: session }: { s: ReturnType<typeof useTools> }) {
  const asNew = session.asNew;
  const back = session.back;
  const bar = session.bar;
  const brand = session.brand;
  const brush = session.brush;
  const choice = session.choice;
  const copy = session.copy;
  const count = session.count;
  const cut = session.cut;
  const dip = session.dip;
  const dirty = session.dirty;
  const discard = session.discard;
  const feedback = session.feedback;
  const file = session.file;
  const fits = session.fits;
  const free = session.free;
  const fromPress = session.fromPress;
  const hist = session.hist;
  const inBar = session.inBar;
  const join = session.join;
  const joinable = session.joinable;
  const leaf = session.leaf;
  const left = session.left;
  const letters = session.letters;
  const lockIt = session.lockIt;
  const locked = session.locked;
  const menu = session.menu;
  const mode = session.mode;
  const more = session.more;
  const newerSheet = session.newerSheet;
  const openVariants = session.openVariants;
  const over = session.over;
  const part = session.part;
  const pasteAny = session.pasteAny;
  const pdf = session.pdf;
  const pdfWaits = session.pdfWaits;
  const pressed = session.pressed;
  const put = session.put;
  const redo = session.redo;
  const refit = session.refit;
  const reload = session.reload;
  const remove = session.remove;
  const right = session.right;
  const saver = session.saver;
  const sel = session.sel;
  const setBrush = session.setBrush;
  const setCount = session.setCount;
  const setFromPress = session.setFromPress;
  const setLetters = session.setLetters;
  const setMenu = session.setMenu;
  const setPane = session.setPane;
  const setSide = session.setSide;
  const setSolved = session.setSolved;
  const setTab = session.setTab;
  const setTitle = session.setTitle;
  const setTour = session.setTour;
  const setVariants = session.setVariants;
  const showLeft = session.showLeft;
  const showRight = session.showRight;
  const solved = session.solved;
  const source = session.source;
  const split = session.split;
  const splittable = session.splittable;
  const title = session.title;
  const tour = session.tour;
  const undo = session.undo;
  const variants = session.variants;
  const variantsDoor = session.variantsDoor;
  const wet = session.wet;
  const zoomer = session.zoomer;
  return (
    <>
      <header>
        {/* Blank.tsx draws this bar's boxes, and the panel's below, for a phone that loads: a change here goes there too. */}
        <div className="top" ref={bar} onPointerOver={holdName}>
          {leaf ? (
            <span className="modes" role="tablist">
              {["Start", "Ansicht", "Vorlagen"].map((m) => (
                <button
                  key={m}
                  role="tab"
                  data-tour={m}
                  aria-selected={mode === m}
                  onClick={() => {
                    setSide(m === "Vorlagen");
                    setTab(m === "Ansicht" ? "Ansicht" : "Format");
                    if (m === "Ansicht") setPane(true);
                  }}
                >
                  {m}
                </button>
              ))}
            </span>
          ) : (
            <>
              {brand}
              <Tool icon={PanelLeft} label="Seiten und Vorlagen" className={`pin${left ? " on" : ""}`} aria-pressed={left} onClick={() => showLeft(!left)} />
            </>
          )}
          <input
            type="text"
            aria-label="Titel"
            placeholder="Unbenanntes Blatt"
            maxLength={80}
            value={title}
            // A title the bar cuts shows whole under the pointer, and while it is edited: see `refit`.
            title={title}
            onChange={(e) => setTitle(e.target.value)}
            onFocus={refit}
            // A press that takes the focus from the stand-in title picks it whole, as PowerPoint does, so that typing replaces it.
            // The press then does not place the caret, and a second press, with the focus already here, does.
            onMouseDown={(e) => {
              if (document.activeElement === e.currentTarget || e.currentTarget.value.trim() !== "Unbenanntes Blatt") return;
              e.preventDefault();
              e.currentTarget.focus();
              e.currentTarget.select();
            }}
            // A press that took the focus has its click still to come: the bar waits until the mouse button is up and
            // the click is through, or the button pressed would move from under the pointer. A key ends it at once.
            onBlur={() => (document.querySelector(":active") ? addEventListener("mouseup", () => setTimeout(refit), { once: true, capture: true }) : refit())}
            // Enter ends the edit, as in PowerPoint, and gives the keys back; Escape does so for any field.
            onKeyDown={(e) => e.key === "Enter" && back(e.currentTarget)}
          />
          <span className="hint" role="status">
            {!dirty ? "Gespeichert" : !saver || saver.failed || saver.clash ? "Nicht gespeichert" : "Speichert …"}
          </span>
          <Tool icon={Undo2} label="Rückgängig" data-tour="undo" disabled={!hist.past.length} onClick={undo} />
          <Tool icon={Redo2} label="Wiederholen" disabled={!hist.future.length} onClick={redo} />
          <i className="sep" />
          {inBar("Ausschneiden") && <Tool icon={Scissors} label="Ausschneiden" disabled={!free.length} onClick={cut} />}
          {inBar("Kopieren") && <Tool icon={Copy} label="Kopieren" disabled={!sel.length} onClick={() => copy()} />}
          {inBar("Einfügen") && <Tool icon={ClipboardPaste} label="Einfügen" onClick={pasteAny} />}
          {inBar("Format übertragen") && (
            <Tool
              icon={Paintbrush}
              label="Format übertragen"
              disabled={!brush && !source}
              className={brush ? "on" : ""}
              aria-pressed={brush > 0}
              onPointerDown={() => (wet.current = part?.marks)}
              // One click picks the look up for one block, or puts the brush down. The second click of a double click
              // keeps the brush on with the look the first one picked up.
              onClick={(e) => {
                // A press by the keys has no pointer before it, and must not find an earlier one's words.
                const marks = wet.current;
                wet.current = undefined;
                if (brush && e.detail < 2) return setBrush(0);
                if (!brush) dip(marks);
                setBrush(e.detail < 2 ? 1 : 2);
              }}
            />
          )}
          {inBar("Duplizieren") && <Tool icon={CopyPlus} label="Duplizieren" disabled={!sel.length} onClick={() => put(sel)} />}
          {inBar("Löschen") && <Tool icon={Trash2} label="Löschen" disabled={!free.length} onClick={remove} />}
          {inBar(lockIt.label) && <Tool icon={lockIt.icon!} label={lockIt.label} disabled={!sel.length} className={locked ? "on" : ""} onClick={lockIt.run} />}
          {inBar("Gruppieren") && <Tool icon={Group} label="Gruppieren" disabled={!joinable} onClick={join} />}
          {inBar("Gruppierung aufheben") && <Tool icon={Ungroup} label="Gruppierung aufheben" disabled={!splittable} onClick={split} />}
          {/* With none of them left in the bar, the divider before them is enough. */}
          {fits !== 0 && <i className="sep" />}
          {inBar("Lösungen zeigen") && <Tool icon={Eye} label="Lösungen zeigen" className={solved ? "on" : ""} aria-pressed={solved} onClick={() => setSolved(!solved)} />}
          {!leaf && inBar("Kleiner") && zoomer}
          <Tool icon={PanelRight} label="Format und Ansicht" className={`pin${right ? " on" : ""}`} aria-pressed={right} onClick={() => showRight(!right)} />
          {inBar("Rundgang") && <Tool icon={CircleHelp} label="Rundgang" data-tour="help" onClick={() => setTour(true)} />}
          <Feedback className="ib" aria-label="Feedback" opener={inBar("Feedback") ? undefined : feedback}>
            <MessageSquare size={16} aria-hidden />
          </Feedback>
          {inBar("Varianten drucken") && <Tool icon={Layers} label="Varianten drucken" onClick={(e) => openVariants(e.currentTarget)} />}
          {more.length > 0 && (
            <Tool
              icon={Ellipsis}
              label="Mehr"
              className="more"
              aria-haspopup="menu"
              aria-expanded={!!menu?.more}
              // The tour's last step is about its own button, which lies in here when the bar has folded it.
              data-tour={inBar("Rundgang") ? undefined : "help"}
              onClick={(e) => {
                const box = e.currentTarget.getBoundingClientRect();
                setMenu({ x: box.left, y: box.bottom + 4, more: true });
              }}
            />
          )}
          <span className="pdf" data-tour="pdf">
            <button onClick={() => pdf(true)}>
              <FileCheck size={14} aria-hidden />
              Lösungen
            </button>
            <button className="primary" onClick={() => pdf(false)}>
              <FileDown size={14} aria-hidden />
              PDF
            </button>
          </span>
          {variants && (
            <Variants
              id={file.id}
              doc={hist.doc}
              count={count}
              setCount={setCount}
              letters={letters}
              setLetters={setLetters}
              opener={variantsDoor}
              onClose={() => { setVariants(false); setFromPress(undefined); }}
              clash={!!saver?.clash}
              newer={(key) => newerSheet({ count, letters, print: key, newer: true })}
              print={fromPress?.print}
              fresh={fromPress?.newer}
            />
          )}
        </div>
        {saver?.refused && (
          <div className="clash" role="alert">
            Nicht gespeichert: Das Blatt passt nicht zum Format.
            <ul>
              {saver.refused.map((problem, i) => (
                <li key={i}>{problem}</li>
              ))}
            </ul>
          </div>
        )}
        {saver?.clash && (
          <div className="clash" role="alert">
            {CLASH_BAR}
            {pdfWaits && " Danach kommt dein PDF."}
            <button disabled={choice === "busy"} onClick={reload}>Andere Version laden</button>
            {/* Based on the version the server has now, this document takes its place; a change that lands in between clashes again. */}
            <button disabled={choice === "busy"} onClick={over}>Mit dieser überschreiben</button>
            {choice && <span>{choice === "busy" ? "Lädt …" : "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."}</span>}
          </div>
        )}
        {/* The editor works on under it: what shows at the press is what is kept. */}
        {saver?.gone && (
          <div className="clash" role="alert">
            Dieses Blatt wurde auf einem anderen Gerät gelöscht. Was du hier siehst, ist noch da.
            <button disabled={saver.choice === "busy"} onClick={asNew}>Als neues Blatt behalten</button>
            <button disabled={saver.choice === "busy"} onClick={discard}>Verwerfen</button>
            {saver.choice && (
              <span>
                {saver.choice === "busy" ? "Lädt …" : saver.choiceProblems ? `Das hat nicht geklappt: das Blatt passt nicht zum Format. ${saver.choiceProblems.join("; ")}` : "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."}
              </span>
            )}
          </div>
        )}
      </header>
    </>
  );
}
