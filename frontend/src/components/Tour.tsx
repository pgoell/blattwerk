import { useEffect, useRef, useState } from "react";
import type { Doc } from "../sheet";

// What the tour watches of the editor, to tell that the teacher has done what a step asks.
export type Seen = { doc: Doc; blocks: number; sel: number; editing: boolean; tab: string };

type Step = {
  title: string;
  // One text, or one for a mouse and one for a finger.
  text: string | [string, string];
  // The element the ring goes round.
  find?: string;
  // The panel the step needs open: a tab of the right one, or Vorlagen for the left one.
  tab?: string;
  // True once the step's task is done, from the editor now and as the step began; the tour then moves on by itself.
  done?: (now: Seen, start: Seen) => boolean;
};

const STEPS: Step[] = [
  {
    title: "Willkommen bei Blattomat",
    text: "Dieser Rundgang zeigt dir in zwei Minuten, wie ein Blatt entsteht. Du probierst jeden Schritt gleich selbst aus.",
  },
  {
    title: "Ein Textfeld einfügen",
    text: ["Klicke auf Text. Ein Textfeld landet auf dem Blatt.", "Tippe auf Text. Ein Textfeld landet auf dem Blatt."],
    find: "[data-tour=text]",
    done: (now, start) => now.blocks > start.blocks,
  },
  {
    title: "Schreiben",
    text: [
      "Schreib ein paar Wörter und klicke dann neben das Feld. Ein Doppelklick auf das Feld öffnet es wieder.",
      "Schreib ein paar Wörter und tippe dann neben das Feld. Ein zweiter Tipp auf das ausgewählte Feld öffnet es wieder.",
    ],
    find: ".block.sel",
    done: (now, start) => start.editing && !now.editing,
  },
  {
    title: "Bewegen und Größe ändern",
    text: [
      "Klicke das Feld an und zieh es an eine andere Stelle. Die Punkte an Ecken und Kanten ändern die Größe, grüne Linien zeigen, wo das Feld einrastet.",
      "Tippe das Feld an und zieh es an eine andere Stelle. Die Punkte an Ecken und Kanten ändern die Größe, grüne Linien zeigen, wo das Feld einrastet.",
    ],
    find: ".block.sel",
    done: (now, start) => !now.editing && now.doc !== start.doc,
  },
  {
    title: "Format",
    text: "Hier steht alles zu dem, was ausgewählt ist: Schrift, Größe, Farbe, Nummerierung. Der Knopf oben rechts blendet die Leiste ein und aus.",
    find: ".panel",
    tab: "Format",
  },
  {
    title: "Rechenaufgaben",
    text: ["Klicke auf Rechnen. Zwölf Plusaufgaben landen auf dem Blatt.", "Tippe auf Rechnen. Zwölf Plusaufgaben landen auf dem Blatt."],
    find: "[data-tour=maths]",
    done: (now, start) => now.blocks > start.blocks,
  },
  {
    title: "Aufgaben einstellen",
    text: "Im Format legst du Rechenart, Zahlenraum, die Ziffern jeder Stelle und den Übertrag fest. Probier es aus: „Neu würfeln“ bringt neue Zahlen in denselben Grenzen.",
    find: ".panel",
    tab: "Format",
  },
  {
    title: "Mehrere Felder auswählen",
    text: [
      "Halte die Umschalttaste und klicke beide Felder an, oder zieh neben dem Blatt beginnend einen Rahmen um sie. Strg+A wählt alle.",
      "Halte ein Feld gedrückt, bis es ausgewählt ist, und tippe dann das zweite an. Der Knopf Mehrere macht dasselbe.",
    ],
    find: "[data-tour=multi]",
    done: (now) => now.sel > 1,
  },
  {
    title: "Ausrichten, kopieren, löschen",
    text: "Zu mehreren Feldern zeigt das Format Ausrichten und Verteilen. Kopieren, Duplizieren, Löschen und Gruppieren stehen oben in der Leiste oder dort unter „Mehr“: gruppierte Felder bleiben beisammen.",
    find: ".panel",
    tab: "Format",
  },
  {
    title: "Rückgängig",
    text: "Etwas ist verrutscht? Rückgängig nimmt Schritt für Schritt alles zurück.",
    find: "[data-tour=undo]",
  },
  {
    title: "Ansicht",
    text: ["Klicke auf den Reiter Ansicht.", "Tippe auf den Reiter Ansicht."],
    find: "[data-tour=Ansicht]",
    done: (now) => now.tab === "Ansicht",
  },
  {
    title: "Zoom, Raster und Hilfslinien",
    text: [
      "Hier legst du ein Raster aufs Blatt und setzt eigene Hilfslinien. Die Lupen zoomen das Blatt, das Auge oben zeigt die Ergebnisse der Rechenaufgaben. Fehlt der Leiste der Platz, steht beides unter „Mehr“.",
      "Hier legst du ein Raster aufs Blatt und setzt eigene Hilfslinien. Das Auge, oben in der Leiste oder dort unter „Mehr“, zeigt die Ergebnisse der Rechenaufgaben. Mit zwei Fingern zoomst du das Blatt.",
    ],
    find: ".panel",
    tab: "Ansicht",
  },
  {
    title: "Seiten und Vorlagen",
    text: "Links stehen die Seiten des Blatts und die Vorlagen. Eine Vorlage ersetzt das Blatt durch einen fertigen Anfang, etwa für eine Klassenarbeit. Jedes deiner Blätter kannst du hier als eigene Vorlage speichern.",
    find: ".left",
    tab: "Vorlagen",
  },
  {
    title: "Drucken",
    text: "„PDF“ lädt das Blatt zum Drucken, „Lösungen“ dasselbe Blatt mit den Ergebnissen. Speichern musst du nie: Das Blatt sichert sich von selbst.",
    find: "[data-tour=pdf]",
  },
  {
    title: "Das war's",
    // Where the bar has folded the button away, the editor puts this mark on "Mehr".
    text: "Den Rundgang findest du jederzeit hinter dem Fragezeichen, oben in der Leiste oder dort unter „Mehr“. Viel Freude mit deinem ersten Blatt!",
    find: "[data-tour=help]",
  },
];

const finger = matchMedia("(pointer: coarse)").matches;

// A card that leads through the editor step by step, with a ring round the control in question. The editor stays
// in full use under it. `show` opens a panel.
export default function Tour({ seen, show, close }: { seen: Seen; show: (tab: string) => void; close: () => void }) {
  const [n, setN] = useState(0);
  const start = useRef(seen);
  const ring = useRef<HTMLDivElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const step = STEPS[n];

  function go(to: number) {
    if (to === STEPS.length) return close();
    start.current = seen;
    const { tab } = STEPS[to];
    if (tab) show(tab);
    setN(to);
  }

  useEffect(() => {
    if (step.done?.(seen, start.current)) go(n + 1);
  });

  // The ring follows its element every frame: blocks move, the desk scrolls and the bar wraps.
  useEffect(() => {
    let frame = 0;
    const follow = () => {
      const box = step.find ? document.querySelector(step.find)?.getBoundingClientRect() : undefined;
      const at = ring.current!.style;
      at.display = box ? "" : "none";
      if (box) {
        // Round a control as wide as the window, the ring stays inside it.
        const left = Math.max(2, box.left - 4);
        const top = Math.max(2, box.top - 4);
        at.left = `${left}px`;
        at.top = `${top}px`;
        at.width = `${Math.min(innerWidth - 2, box.right + 4) - left}px`;
        at.height = `${Math.min(innerHeight - 2, box.bottom + 4) - top}px`;
      }
      // The card keeps to the half of the window the element is not in.
      card.current!.classList.toggle("up", !!box && box.top + box.height / 2 > innerHeight / 2);
      frame = requestAnimationFrame(follow);
    };
    follow();
    return () => cancelAnimationFrame(frame);
  }, [step]);

  return (
    <>
      <div className="tour-ring" ref={ring} />
      <section className="tour" ref={card} aria-label="Rundgang" aria-live="polite">
        <small>
          Schritt {n + 1} von {STEPS.length}
        </small>
        <h2>{step.title}</h2>
        <p>{typeof step.text === "string" ? step.text : step.text[+finger]}</p>
        <div>
          <button onClick={close}>Beenden</button>
          {n > 0 && <button onClick={() => go(n - 1)}>Zurück</button>}
          <button className="primary" onClick={() => go(n + 1)}>
            {n === 0 ? "Los geht's" : n === STEPS.length - 1 ? "Fertig" : "Weiter"}
          </button>
        </div>
      </section>
    </>
  );
}
