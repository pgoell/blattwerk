// A picture from Pixabay, searched through our server. The file box stays for a picture of the teacher's own.
import { useState, type FormEvent } from "react";
import { api, type Refusal } from "../api";
import { signed } from "../saves";

type Hit = {
  id: number;
  preview: string;
  source: string;
  author: string;
  licence: string;
  page: string;
  width: number;
  height: number;
};

export default function PictureSearch({ onFile, onPlace, onClose }: { onFile: () => void; onPlace: (id: number) => void; onClose: () => void }) {
  const [term, setTerm] = useState("");
  const [drawings, setDrawings] = useState(true);
  const [hits, setHits] = useState<Hit[]>([]);
  const [status, setStatus] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setStatus("");
    try {
      const body = await signed(api<{ hits: Hit[] }>(`/picture-search?q=${encodeURIComponent(term)}&drawings=${drawings ? "true" : "false"}`));
      setHits(body.hits);
      setStatus(body.hits.length ? "" : "Nichts gefunden.");
    } catch (err) {
      setHits([]);
      setStatus((err as Refusal).detail || "Die Bildsuche ist gerade nicht erreichbar.");
    }
  }

  return (
    <dialog
      className="pictures"
      ref={(el) => void (el && !el.open && el.showModal())}
      onClose={onClose}
      onKeyDown={(e) => {
        if (e.key !== "Escape" || !e.currentTarget.open) return;
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.close();
      }}
    >
      <form onSubmit={submit}>
        <h1>Bild</h1>
        <label>
          Suchbegriff
          <input type="text" value={term} autoComplete="off" onChange={(e) => setTerm(e.target.value)} />
        </label>
        <label className="tick">
          <input type="checkbox" checked={drawings} onChange={(e) => setDrawings(e.target.checked)} /> Zeichnungen
        </label>
        <p className="hint">Zeichnungen und Vektoren. Fotos bleiben draußen: sie kopieren in Schwarzweiß schlecht.</p>
        <div className="row">
          <button type="button" onClick={() => { onFile(); onClose(); }}>
            Datei wählen
          </button>
          <button className="primary">Suchen</button>
        </div>
      </form>
      {status && <p className="hint" role="status">{status}</p>}
      <div className="hits">
        {hits.map((hit) => (
          <button type="button" key={hit.id} onClick={() => onPlace(hit.id)}>
            <img src={hit.preview} alt="" />
            <span>{hit.author}</span>
            <small>
              {hit.source}, {hit.licence}
            </small>
          </button>
        ))}
      </div>
    </dialog>
  );
}
