import { useEffect, useRef, useState } from "react";
import { api, post, signed } from "../api";
import { attempt } from "../fault";

// The server keeps UTC, as "2026-10-06 09:30:00".
const day = (stamp: string) =>
  new Date(`${stamp.replace(" ", "T")}Z`).toLocaleDateString("de-DE", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

type Off = { on: false };
type On = { on: true; token: string; updated: string };
type State = Off | On;

// Teilen, from the list: the link is on or off, and the owner can point it at the saved sheet.
export default function ShareDialog({ id, title, onClose }: { id: number; title: string; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [state, setState] = useState<State>();
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);
  useEffect(() => void ref.current?.showModal(), []);
  useEffect(() => {
    let on = true;
    signed(api<State>(`/sheets/${id}/share`)).then(
      (next) => on && setState(next),
      () => on && setFailed(true),
    );
    return () => void (on = false);
  }, [id]);

  const url = state?.on ? `${location.origin}/teilen/${state.token}` : "";
  const run = (what: string, go: () => Promise<State>) =>
    void attempt(what, async () => {
      setCopied(false);
      setState(await signed(go()));
    });

  return (
    <dialog ref={ref} className="ask" aria-labelledby="share-title" onClose={onClose}>
      <h1 id="share-title">{title} teilen</h1>
      {failed && <p>Der Stand des Links konnte nicht geladen werden.</p>}
      {!failed && !state && <p>Lädt …</p>}
      {state && !state.on && (
        <>
          <p>
            Der Link zeigt das Blatt so, wie es jetzt gespeichert ist. Wer ihn hat, kann es ansehen und eine Kopie in
            die eigenen Blätter legen. Eine Liste aller Links gibt es nicht.
          </p>
          <div className="row">
            <button type="button" className="primary" onClick={() => run("Der Link konnte nicht eingeschaltet werden.", () => post<On>(`/sheets/${id}/share`))}>
              Link einschalten
            </button>
            <button type="button" className="plain" onClick={() => ref.current?.close()}>
              Schließen
            </button>
          </div>
        </>
      )}
      {state?.on && (
        <>
          <p>Der Link ist an. Er zeigt den Stand vom {day(state.updated)}, nicht jede spätere Änderung.</p>
          <p className="link">{url}</p>
          <div className="row">
            <button
              type="button"
              onClick={() => void navigator.clipboard.writeText(url).then(() => setCopied(true), () => setCopied(false))}
            >
              {copied ? "Kopiert" : "Link kopieren"}
            </button>
            <button
              type="button"
              onClick={() =>
                run("Der Link konnte nicht aktualisiert werden.", () => post<On>(`/sheets/${id}/share/renew`))
              }
            >
              aktualisieren
            </button>
            <button
              type="button"
              className="plain"
              onClick={() =>
                run("Der Link konnte nicht ausgeschaltet werden.", () =>
                  api<Off>(`/sheets/${id}/share`, { method: "DELETE" }),
                )
              }
            >
              Link ausschalten
            </button>
          </div>
        </>
      )}
    </dialog>
  );
}
