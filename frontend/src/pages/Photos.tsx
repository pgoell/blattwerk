import { useState, type FormEvent } from "react";
import { api } from "../api";
import PhotoPicker, { shrink } from "../components/PhotoPicker";

export default function Photos() {
  const [photos, setPhotos] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!photos.length) return setStatus("Bitte mindestens ein Foto hinzufügen.");
    const form = e.currentTarget;
    const data = new FormData(form);
    data.append("art", "fotos");
    setBusy(true);
    setStatus("Wird gesendet …");
    try {
      for (const photo of photos) data.append("photo", await shrink(photo), "photo");
      await api("/feedback", { method: "POST", body: data });
      form.reset();
      setPhotos([]);
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
          <input type="text" id="titel" name="titel" />
        </div>
        <div className="card">
          <label>Seiten</label>
          <PhotoPicker photos={photos} onChange={setPhotos} />
        </div>
        <div className="card">
          <label htmlFor="notiz">Was gefällt dir daran?</label>
          <p className="hint">Oder was würdest du anders machen? Stichpunkte reichen.</p>
          <textarea id="notiz" name="notiz" />
        </div>
        <button className="wide primary" disabled={busy}>Abschicken</button>
        <div className="status" role="status">{status}</div>
      </form>
    </main>
  );
}
