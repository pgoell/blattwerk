// Feedback from any page: a button that opens a form for text, voice notes and pictures.
import { useImperativeHandle, useRef, useState, type ButtonHTMLAttributes, type FormEvent, type Ref } from "react";
import { api } from "../api";
import { signed } from "../saves";
import PhotoPicker, { shrink } from "./PhotoPicker";
import VoiceNotes, { lost } from "./VoiceNotes";

// What is typed outlives the form: a send that finds the session gone brings the login, which takes the form away,
// and the text, the voice notes and the pictures stand in the form opened after it. The app empties it when the
// account is another, and a clip that ends after that does not come into the new account's draft.
const NONE = { text: "", clips: [] as Blob[], photos: [] as File[] };
let draft = NONE;
let generation = 0;
export const forgetDraft = () => {
  draft = NONE;
  generation++;
};

const KEPT = "Deine Aufnahme lief noch, als das Formular zuging. Sie ist unten gespeichert.";
const STOPPED = "Aufnahme beendet. Hör sie dir an und drück dann nochmal auf Abschicken.";

// With `opener` the form has no button of its own: the editor's bar has folded it into a menu, whose item opens the
// form through it. The form and what is written in it stay while the button comes and goes.
export default function Feedback({ opener, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { opener?: Ref<() => void> }) {
  const [open, setOpen] = useState(false);
  const [{ text, clips, photos }, write] = useState(draft);
  const keep = (change: Partial<typeof NONE>) => write((draft = { ...draft, ...change }));
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const shot = useRef<Promise<Blob | null>>(Promise.resolve(null));
  const stopper = useRef<() => boolean>(null);
  const gen = generation;

  // The screen as it is when the form is asked for, without the form, goes along with what is sent. The library
  // that draws it loads only now.
  function show() {
    shot.current = import("modern-screenshot")
      .then(({ domToBlob }) =>
        domToBlob(document.body, {
          width: innerWidth,
          height: innerHeight,
          type: "image/jpeg",
          quality: 0.8,
          backgroundColor: getComputedStyle(document.body).backgroundColor,
          filter: (node) => !(node instanceof Element && node.matches("dialog")),
        }),
      )
      .catch(() => null);
    // A clip kept from a form that shut while recording is told once; the draft empty after a logout tells nothing.
    setStatus(lost.recording && clips.length ? KEPT : "");
    lost.recording = false;
    setOpen(true);
  }
  useImperativeHandle(opener, () => show);

  async function submit(e: FormEvent) {
    e.preventDefault();
    // A recording goes on until the teacher has heard it: this send only stops it.
    if (stopper.current?.()) return setStatus(STOPPED);
    if (!text.trim() && !clips.length && !photos.length) return setStatus("Schreib etwas, nimm eine Sprachnotiz auf oder füg ein Bild hinzu.");
    const data = new FormData();
    data.append("art", "feedback");
    data.append("text", text);
    data.append("seite", location.pathname);
    clips.forEach((clip) => data.append("audio", clip, "clip"));
    setBusy(true);
    setStatus("Wird gesendet …");
    try {
      for (const photo of photos) data.append("photo", await shrink(photo), "photo");
      const screen = await shot.current;
      if (screen) data.append("screenshot", screen, "screenshot");
      // With no limit of time: voice notes and pictures may take long.
      await signed(api("/feedback", { method: "POST", body: data }));
      keep(NONE);
      setStatus("Danke! Ist angekommen.");
    } catch {
      setStatus("Das hat nicht geklappt. Dein Feedback ist noch da, versuch es gleich nochmal.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {!opener && <button type="button" {...props} onClick={show} />}
      {open && (
        <dialog
          className="feedback"
          ref={(el) => void (el && !el.open && el.showModal())}
          onClose={() => setOpen(false)}
          // Escape shuts the form at once: the browser's `close` comes a task later. It is the form's, not the sheet's.
          onKeyDown={(e) => {
            if (e.key !== "Escape" || !e.currentTarget.open) return;
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.close();
            setOpen(false);
          }}
        >
          <form onSubmit={submit}>
            <h1>Feedback</h1>
            <p className="lead">Was fällt dir auf, was fehlt, was nervt? Ein Bild von dieser Seite, so wie du sie gerade siehst, geht von selbst mit.</p>
            <label htmlFor="feedback-text">Schreiben</label>
            <textarea id="feedback-text" value={text} onChange={(e) => keep({ text: e.target.value })} />
            <label>Sprechen</label>
            <VoiceNotes
              clips={clips}
              onChange={(clips) => {
                if (gen === generation) keep({ clips });
              }}
              stopper={stopper}
            />
            <label>Bilder</label>
            <PhotoPicker photos={photos} onChange={(photos) => keep({ photos })} name="Bild" />
            <div className="row">
              <button type="button" onClick={() => setOpen(false)}>Schließen</button>
              <button className="primary" disabled={busy}>Abschicken</button>
            </div>
            <div className="status" role="status">{status}</div>
          </form>
        </dialog>
      )}
    </>
  );
}
