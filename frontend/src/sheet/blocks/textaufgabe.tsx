// Draws one Textaufgabe block: story, question, optional drawing box, Karo for the Rechnung, Antwort line.

import { sane, made, layout, visible } from "../../textaufgabe";
import type { TextaufgabeBlock } from "../tasks";

export function Textaufgabe({ block, k, solved }: { block: TextaufgabeBlock; k: number; solved: boolean }) {
  const p = sane(block.props);
  const tasks = made(p).tasks;
  const L = layout(p);
  const px = (mm: number) => mm * k;
  const ink = (open: boolean, shown: boolean) => (open && !shown && solved ? "answer" : undefined);
  return (
    <div className={`textaufgabe${solved ? " solved" : ""}`} style={{ fontSize: px(3.2), lineHeight: `${px(L.LINE)}px` }}>
      {tasks.map((t, i) => {
        const frage = visible("frage", p, solved);
        const rechnung = visible("rechnung", p, solved);
        const antwort = visible("antwort", p, solved);
        return (
          <article key={i} className="task" data-task={i} data-fit={t.fit ? "yes" : "no"} style={{ boxSizing: "border-box", height: px(L.taskH), paddingTop: px(L.PAD), marginBottom: i + 1 < tasks.length ? px(L.GAP) : 0 }}>
            <p className="text" data-part="text" style={{ height: px(L.TEXT_LINES * L.LINE) }}>{t.text}</p>
            <p className="frage" data-part="frage" data-open={frage ? "yes" : "no"} style={{ height: px(L.FRAGE_LINES * L.LINE) }}>{frage ? t.frage : ""}</p>
            {p.sketch && <div className="sketch" data-part="sketch" style={{ height: px(L.SKETCH) }} />}
            <div
              className="rechnung"
              data-part="rechnung"
              data-open={rechnung ? "yes" : "no"}
              data-rows={L.rows}
              style={{
                height: px(L.rows * L.Q),
                backgroundImage: "linear-gradient(to right, #9fb4c8 1px, transparent 1px), linear-gradient(to bottom, #9fb4c8 1px, transparent 1px)",
                backgroundSize: `${px(L.Q)}px ${px(L.Q)}px`,
              }}
            >
              {rechnung && <span className={ink(rechnung, p.rechnung)}>{t.rechnung}</span>}
            </div>
            <p className="antwort" data-part="antwort" data-open={antwort ? "yes" : "no"} style={{ height: px(L.ANTWORT) }}>
              Antwort: {antwort ? <span className={ink(antwort, p.antwort)}>{t.antwort}</span> : <span className="line" />}
            </p>
          </article>
        );
      })}
    </div>
  );
}
