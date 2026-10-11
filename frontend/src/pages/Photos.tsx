import { useState, type FormEvent } from "react";
import { api } from "../api";
import PhotoPicker, { shrink } from "../components/PhotoPicker";
import { signed } from "../saves";

// What is entered outlives the page: a send that finds the session gone brings the login, which takes the page
// away, and the photos, the title and the note stand again after it. The app empties it when the account is another.
const NONE = { photos: [] as File[], titel: "", notiz: "" };
let draft = NONE;
export const forgetPhotos = () => void (draft = NONE);

export default function Photos() {
  const [{ photos, titel, notiz }, write] = useState(draft);
  const keep = (change: Partial<typeof NONE>) => write((draft = { ...draft, ...change }));
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!photos.length) return setStatus("Bitte mindestens ein Foto hinzufügen.");
    const data = new FormData(e.currentTarget);
    data.append("art", "fotos");
    setBusy(true);
    setStatus("Wird gesendet …");
    try {
      for (const photo of photos) data.append("photo", await shrink(photo), "photo");
      // With no limit of time: photos may take long. Sent with the session run out, they bring the login.
      await signed(api("/feedback", { method: "POST", body: data }));
      keep(NONE);
      setStatus("Danke! Ist angekommen. Du kannst gleich das nächste schicken.");
    } catch {
      setStatus("Das hat nicht geklappt. Die Fotos sind noch da, versuch es gleich nochmal.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>Fotos von Blättern</h1>
      <p className="lead">
        Fotografier Arbeitsblätter oder Klassenarbeiten, die dir gefallen. Ein Blatt oder eine ganze Klassenarbeit pro
        Sendung, die Seiten in der richtigen Reihenfolge. Bitte keine Namen, Gesichter oder Handschrift von Kindern.
      </p>
      <form onSubmit={submit}>
        <div className="card">
          <label htmlFor="titel">Was ist das?</label>
          <p className="hint">z. B. „Klassenarbeit Mathe Kl. 3, Schriftliche Addition“</p>
          <input type="text" id="titel" name="titel" value={titel} onChange={(e) => keep({ titel: e.target.value })} />
        </div>
        <div className="card">
          <label>Seiten</label>
          <PhotoPicker photos={photos} onChange={(photos) => keep({ photos })} />
        </div>
        <div className="card">
          <label htmlFor="notiz">Was gefällt dir daran?</label>
          <p className="hint">Oder was würdest du anders machen? Stichpunkte reichen.</p>
          <textarea id="notiz" name="notiz" value={notiz} onChange={(e) => keep({ notiz: e.target.value })} />
        </div>
        <button className="wide primary" disabled={busy}>Abschicken</button>
        <div className="status" role="status">{status}</div>
      </form>
    </main>
  );
}
