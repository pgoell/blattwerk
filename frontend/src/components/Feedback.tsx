// Feedback from any page: a button that opens a form for text, voice notes and pictures.
import { useImperativeHandle, useRef, useState, type ButtonHTMLAttributes, type FormEvent, type Ref } from "react";
import { api } from "../api";
import PhotoPicker, { shrink } from "./PhotoPicker";
import VoiceNotes from "./VoiceNotes";

// With `opener` the form has no button of its own: the editor's bar has folded it into a menu, whose item opens the
// form through it. The form and what is written in it stay while the button comes and goes.
export default function Feedback({ opener, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { opener?: Ref<() => void> }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [clips, setClips] = useState<Blob[]>([]);
  const [photos, setPhotos] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const shot = useRef<Promise<Blob | null>>(Promise.resolve(null));

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
    setStatus("");
    setOpen(true);
  }
  useImperativeHandle(opener, () => show);

  async function submit(e: FormEvent) {
    e.preventDefault();
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
      await api("/feedback", { method: "POST", body: data });
      setText("");
      setClips([]);
      setPhotos([]);
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
        <dialog className="feedback" ref={(el) => void (el && !el.open && el.showModal())} onClose={() => setOpen(false)}>
          <form onSubmit={submit}>
            <h1>Feedback</h1>
            <p className="lead">Was fällt dir auf, was fehlt, was nervt? Ein Bild von dieser Seite, so wie du sie gerade siehst, geht von selbst mit.</p>
            <label htmlFor="feedback-text">Schreiben</label>
            <textarea id="feedback-text" value={text} onChange={(e) => setText(e.target.value)} />
            <label>Sprechen</label>
            <VoiceNotes clips={clips} onChange={setClips} />
            <label>Bilder</label>
            <PhotoPicker photos={photos} onChange={setPhotos} name="Bild" />
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
