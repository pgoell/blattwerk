import { useEffect, useState } from "react";
import { Copy, Pencil, Plus, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { api, post } from "../api";
import Failed from "../components/Failed";
import { ask, forget, useSaves } from "../saves";
import { EMPTY, Paper, read, sizeOf, type Sheet } from "../sheet";

// The server keeps UTC, as "2026-10-06 09:30:00".
const day = (stamp: string) => new Date(`${stamp.replace(" ", "T")}Z`).toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });

export default function SheetList() {
  const [sheets, setSheets] = useState<Sheet[]>();
  const navigate = useNavigate();

  // Asked for at once, and again whenever a save lands: a sheet just left shows as it was left once its save is in.
  // A load that failed says so where no list stands yet, and `tries` counts the tries after it. A list that stands
  // stays as it is.
  const { landed } = useSaves();
  const [failed, setFailed] = useState(false);
  const [tries, setTries] = useState(0);
  useEffect(() => {
    let on = true;
    ask<Sheet[]>("/sheets").then(
      (all) => on && setSheets(all),
      () => on && setFailed(true),
    );
    return () => void (on = false);
  }, [landed, tries]);
  const retry = () => {
    setFailed(false);
    setTries((n) => n + 1);
  };

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
    // A saver that waits for the teacher's choice or for a login would never hear that the sheet is gone.
    forget(sheet.id);
    setSheets((all) => all!.filter((s) => s.id !== sheet.id));
  }

  return (
    <main>
      <h1>Meine Blätter</h1>
      <button type="button" className="primary" onClick={create}>
        <Plus size={16} aria-hidden />
        Neues Blatt
      </button>
      {failed && !sheets && <Failed retry={retry}><p><strong>Die Blätter konnten nicht geladen werden</strong></p></Failed>}
      {sheets?.length === 0 && <p className="lead">Noch kein Blatt. Leg dein erstes an.</p>}
      <ul className="sheets">
        {sheets?.map((sheet) => (
          <li key={sheet.id}>
            <Link to={`/blatt/${sheet.id}`}>
              <Paper doc={sheet.doc} k={147 / sizeOf(read(sheet.doc), 0)[0]} />
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
