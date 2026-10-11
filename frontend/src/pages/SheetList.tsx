import { useEffect, useRef, useState } from "react";
import { Copy, Pencil, Plus, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { api, post } from "../api";
import Failed from "../components/Failed";
import { attempt } from "../fault";
import { ask, forget, served, signed, useSaves } from "../saves";
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
      (all) => (served(all[0]?.user_id), on && setSheets(all)),
      () => on && setFailed(true),
    );
    return () => void (on = false);
  }, [landed, tries]);
  const retry = () => {
    setFailed(false);
    setTries((n) => n + 1);
  };

  // The word that the list loads comes when a try has taken half a second.
  const [late, setLate] = useState(false);
  useEffect(() => {
    setLate(false);
    const wait = setTimeout(() => setLate(true), 500);
    return () => clearTimeout(wait);
  }, [tries]);

  // Each of the four finds a session that ran out and brings the login then. One that the server could not do says
  // so above the page, and its `Erneut versuchen` runs the whole of it again: the question is asked once. While one
  // is out, a second press on the same button does nothing.
  const out = useRef(new Set<string>());
  const act = (what: string, sheet: Sheet | undefined, run: () => Promise<void>) =>
    attempt(
      what,
      async () => {
        const key = `${what}${sheet?.id}`;
        if (out.current.has(key)) return;
        out.current.add(key);
        await run().finally(() => out.current.delete(key));
      },
      // The sheet was deleted on another device: its row goes, and no try would bring it back.
      (status) => {
        if (status !== "404" || !sheet) return;
        setSheets((all) => all?.filter((s) => s.id !== sheet.id));
        return "Dieses Blatt wurde auf einem anderen Gerät gelöscht.";
      },
    );
  const create = () =>
    act("Das neue Blatt konnte nicht angelegt werden.", undefined, async () => {
      const sheet = await signed(post<Sheet>("/sheets", { title: "Unbenanntes Blatt", doc: EMPTY }));
      navigate(`/blatt/${sheet.id}`);
    });
  function rename(sheet: Sheet) {
    const title = prompt("Titel des Blatts", sheet.title)?.trim().slice(0, 80);
    if (!title) return;
    act("Das Blatt konnte nicht umbenannt werden.", sheet, async () => {
      const saved = await signed(post<Sheet>(`/sheets/${sheet.id}`, { title }, { method: "PATCH" }));
      setSheets((all) => all?.map((s) => (s.id === saved.id ? saved : s)));
    });
  }
  const duplicate = (sheet: Sheet) =>
    act("Das Blatt konnte nicht dupliziert werden.", sheet, async () => {
      const copy = await signed(post<Sheet>(`/sheets/${sheet.id}/duplicate`));
      setSheets((all) => [copy, ...(all ?? [])]);
    });
  function remove(sheet: Sheet) {
    if (!confirm(`Blatt „${sheet.title}“ löschen?`)) return;
    act("Das Blatt konnte nicht gelöscht werden.", sheet, async () => {
      await signed(api(`/sheets/${sheet.id}`, { method: "DELETE" }));
      // A saver that waits for the teacher's choice or for a login would never hear that the sheet is gone.
      forget(sheet.id);
      setSheets((all) => all?.filter((s) => s.id !== sheet.id));
    });
  }

  return (
    <main>
      <h1>Meine Blätter</h1>
      <button type="button" className="primary" onClick={create}>
        <Plus size={16} aria-hidden />
        Neues Blatt
      </button>
      {!failed && !sheets && <p className="lead" role="status">{late && "Lädt"}</p>}
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
