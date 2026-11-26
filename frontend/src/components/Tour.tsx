import { useEffect, useRef, useState } from "react";
import type { Doc } from "../sheet";

// What the tour watches of the editor, to tell that the teacher has done what a step asks.
export type Seen = { doc: Doc; blocks: number; sel: number; editing: boolean; tab: string };

type Step = {
  title: string;
  // One text, or one for a mouse and one for a finger.
  text: string | [string, string];
  // The text on the tablet held upright, where the tools are groups in a rail and the Format panel comes from below.
  rail?: string;
  // The element the ring goes round.
  find?: string;
  // The tab of the right panel that the step needs open.
  tab?: string;
  // True once the step's task is done, from the editor now and as the step began; the tour then moves on by itself.
  done?: (now: Seen, start: Seen) => boolean;
};

// Five steps, each on what a first sheet needs: a text, its place, a maths block, the panel and the download.
const STEPS: Step[] = [
  {
    title: "Willkommen bei Blattomat",
    text: [
      "In fünf Schritten entsteht dein erstes Blatt. Klicke auf Text: Ein Textfeld landet auf dem Blatt.",
      "In fünf Schritten entsteht dein erstes Blatt. Tippe auf Text: Ein Textfeld landet auf dem Blatt.",
    ],
    rail: "In fünf Schritten entsteht dein erstes Blatt. Tippe links auf Einfügen und dann in der Liste auf Text: Ein Textfeld landet auf dem Blatt.",
    find: "[data-tour=text]",
    done: (now, start) => now.blocks > start.blocks,
  },
  {
    title: "Schreiben und verschieben",
    text: [
      "Schreib ein paar Wörter und klicke dann neben das Feld. Danach ziehst du es an seine Stelle; die Punkte an Ecken und Kanten ändern die Größe.",
      "Schreib ein paar Wörter und tippe dann neben das Feld. Danach ziehst du es an seine Stelle; die Punkte an Ecken und Kanten ändern die Größe.",
    ],
    find: ".block.sel",
    done: (now, start) => start.editing && !now.editing,
  },
  {
    title: "Rechenaufgaben",
    text: ["Klicke auf Rechnen. Zwölf Plusaufgaben landen auf dem Blatt.", "Tippe auf Rechnen. Zwölf Plusaufgaben landen auf dem Blatt."],
    rail: "Tippe links auf Mathe und dann auf Rechnen. Zwölf Plusaufgaben landen auf dem Blatt.",
    find: "[data-tour=maths]",
    done: (now, start) => now.blocks > start.blocks,
  },
  {
    title: "Auswahl und Blatt",
    text: "Unter Auswahl steht alles zu dem, was ausgewählt ist: hier Rechenart, Zahlenraum und „Neu würfeln“. Der Reiter Blatt daneben gilt für das ganze Blatt: Hoch oder Quer, Seitenzahlen, ein Hintergrund.",
    rail: "Unter Auswahl steht alles zu dem, was ausgewählt ist: hier Rechenart, Zahlenraum und „Neu würfeln“. Die Leiste kommt von unten, sobald du etwas antippst, und „Fertig“ schließt sie. Der Reiter Blatt daneben gilt für das ganze Blatt.",
    find: ".panel",
    tab: "Auswahl",
  },
  {
    title: "Drucken",
    // Where the bar has folded the tour's button away, it lies under "Mehr".
    text: "„Herunterladen“ lädt das Blatt als PDF zum Drucken. Der Pfeil daneben öffnet ein Fenster für alles Weitere: das Blatt mit Lösungen, als Word oder PowerPoint, oder in mehreren Varianten, damit der Nachbar nicht abschreibt. Speichern musst du nie: Das Blatt sichert sich von selbst. Den Rundgang findest du jederzeit wieder, hinter dem Fragezeichen oben in der Leiste oder dort unter „Mehr“.",
    find: "[data-tour=pdf]",
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
        <p>{(document.querySelector(".rail") && step.rail) || (typeof step.text === "string" ? step.text : step.text[+finger])}</p>
        <div>
          <button onClick={close}>Beenden</button>
          {n > 0 && <button onClick={() => go(n - 1)}>Zurück</button>}
          <button className="primary" onClick={() => go(n + 1)}>
            {n === STEPS.length - 1 ? "Fertig" : "Weiter"}
          </button>
        </div>
      </section>
    </>
  );
}
