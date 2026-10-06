import { useState, type FormEvent } from "react";
import { api } from "../api";
import VoiceNotes from "../components/VoiceNotes";

export default function Feedback() {
  const [text, setText] = useState("");
  const [clips, setClips] = useState<Blob[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() && !clips.length) return setStatus("Schreib etwas oder nimm eine Sprachnotiz auf.");
    const data = new FormData();
    data.append("art", "feedback");
    data.append("text", text);
    clips.forEach((clip) => data.append("audio", clip, "clip"));
    setBusy(true);
    setStatus("Wird gesendet …");
    try {
      await api("/feedback", { method: "POST", body: data });
      setText("");
      setClips([]);
      setStatus("Danke! Ist angekommen.");
    } catch {
      setStatus("Das hat nicht geklappt. Dein Feedback ist noch da, versuch es gleich nochmal.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>Feedback</h1>
      <p className="lead">Was fällt dir auf, was fehlt, was nervt? Schreib es auf oder sprich es ein, wie es dir leichter fällt.</p>
      <form onSubmit={submit}>
        <div className="card">
          <label htmlFor="text">Schreiben</label>
          <textarea id="text" value={text} onChange={(e) => setText(e.target.value)} />
        </div>
        <div className="card">
          <label>Sprechen</label>
          <p className="hint">Du kannst mehrere Aufnahmen machen.</p>
          <VoiceNotes clips={clips} onChange={setClips} />
        </div>
        <button className="wide primary" disabled={busy}>Abschicken</button>
        <div className="status" role="status">{status}</div>
      </form>
    </main>
  );
}
