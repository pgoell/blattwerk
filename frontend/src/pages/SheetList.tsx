import { useEffect, useState } from "react";
import { Copy, Pencil, Plus, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { api, post } from "../api";
import { EMPTY, Paper, last, type Sheet } from "../sheet";

// The server keeps UTC, as "2026-10-06 09:30:00".
const day = (stamp: string) => new Date(`${stamp.replace(" ", "T")}Z`).toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });

export default function SheetList() {
  const [sheets, setSheets] = useState<Sheet[]>();
  const navigate = useNavigate();

  useEffect(() => {
    last.save.then(() => api<Sheet[]>("/sheets")).then(setSheets);
  }, []);

  async function create() {
    const sheet = await post<Sheet>("/sheets", { title: "Unbenanntes Blatt", doc: EMPTY });
    navigate(`/blatt/${sheet.id}`);
  }
  async function rename(sheet: Sheet) {
    const title = prompt("Titel des Blatts", sheet.title)?.trim().slice(0, 80);
    if (!title) return;
    const saved = await post<Sheet>(`/sheets/${sheet.id}`, { title }, { method: "PATCH" });
    setSheets((all) => all!.map((s) => (s.id === saved.id ? saved : s)));
  }
  async function duplicate(sheet: Sheet) {
    const copy = await post<Sheet>(`/sheets/${sheet.id}/duplicate`);
    setSheets((all) => [copy, ...all!]);
  }
  async function remove(sheet: Sheet) {
    if (!confirm(`Blatt „${sheet.title}“ löschen?`)) return;
    await api(`/sheets/${sheet.id}`, { method: "DELETE" });
    setSheets((all) => all!.filter((s) => s.id !== sheet.id));
  }

  return (
    <main>
      <h1>Meine Blätter</h1>
      <button type="button" className="primary" onClick={create}>
        <Plus size={16} aria-hidden />
        Neues Blatt
      </button>
      {sheets?.length === 0 && <p className="lead">Noch kein Blatt. Leg dein erstes an.</p>}
      <ul className="sheets">
        {sheets?.map((sheet) => (
          <li key={sheet.id}>
            <Link to={`/blatt/${sheet.id}`}>
              <Paper doc={sheet.doc} k={0.7} />
              <strong>{sheet.title}</strong>
              <small>{day(sheet.updated)}</small>
            </Link>
            <div>
              <button type="button" className="plain" aria-label={`${sheet.title} umbenennen`} title="Umbenennen" onClick={() => rename(sheet)}>
                <Pencil size={16} aria-hidden />
              </button>
              <button type="button" className="plain" aria-label={`${sheet.title} duplizieren`} title="Duplizieren" onClick={() => duplicate(sheet)}>
                <Copy size={16} aria-hidden />
              </button>
              <button type="button" className="plain" aria-label={`${sheet.title} löschen`} title="Löschen" onClick={() => remove(sheet)}>
                <Trash2 size={16} aria-hidden />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
