import { useEffect, useRef, useState } from "react";
import { Copy, FolderInput, Pencil, Plus, Share2, Trash2 } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api, post, type Refusal } from "../api";
import Failed from "../components/Failed";
import ShareDialog from "../components/ShareDialog";
import { attempt } from "../fault";
import { ask, forget, served, signed, useSaves } from "../saves";
import { EMPTY, Paper, read, sizeOf, type Sheet } from "../sheet";
import { type Folder, type FolderEntry } from "./FolderSheet";

// The server keeps UTC, as "2026-10-06 09:30:00".
const day = (stamp: string) => new Date(`${stamp.replace(" ", "T")}Z`).toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });
const ORDERS = [["date", "Datum"], ["name", "Name"], ["label", "Kennzeichen"]] as const;

export default function SheetList() {
  const [sheets, setSheets] = useState<Sheet[]>();
  const [sharing, setSharing] = useState<Sheet>();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  // Asked for at once, and again whenever a save lands: a sheet just left shows as it was left once its save is in.
  // A load that failed says so where no list stands yet, and `tries` counts the tries after it. A list that stands
  // stays as it is. The folder is the same ask: 404 means this teacher has no seat, and the tab stays away.
  const { landed } = useSaves();
  const [failed, setFailed] = useState(false);
  const [tries, setTries] = useState(0);
  const [folder, setFolder] = useState<Folder | null>();
  const [folderFailed, setFolderFailed] = useState(false);
  const [round, setRound] = useState(0);
  const [sort, setSort] = useState<(typeof ORDERS)[number][0]>("date");
  const [q, setQ] = useState("");
  useEffect(() => {
    let on = true;
    ask<Sheet[]>("/sheets").then(
      (all) => (served(all[0]?.user_id), on && setSheets(all)),
      () => on && setFailed(true),
    );
    return () => void (on = false);
  }, [landed, tries]);
  useEffect(() => {
    let on = true;
    const query = new URLSearchParams({ sort });
    if (q.trim()) query.set("q", q.trim());
    ask<Folder>(`/folder?${query}`).then(
      (got) => on && (setFolder(got), setFolderFailed(false)),
      (e: Refusal) => {
        if (!on) return;
        if (e.message === "404") (setFolder(null), setFolderFailed(false));
        else setFolderFailed(true);
      },
    );
    return () => void (on = false);
  }, [landed, tries, round, sort, q]);
  const retry = () => {
    setLate(false);
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

  // Each of these finds a session that ran out and brings the login then. One that the server could not do says
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
      // The sheet was deleted on another device: its row goes, and no try would bring it back. Only where the 404
      // was served for the sheet's owner: under another account's session the sheet is still there, and the app
      // asks who is signed in. One that names nobody is a failure like any other.
      (status, e) => {
        const { by } = e as Refusal;
        if (status !== "404" || !sheet || by === undefined) return;
        // The list is that account's from now on, and is asked for anew.
        if (by !== sheet.user_id) return (served(by), setTries((n) => n + 1), null);
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
  function intoFolder(sheet: Sheet) {
    const label = prompt("Kennzeichen, zum Beispiel Klasse 2 oder Mathe. Leer lassen geht.");
    if (label === null) return;
    act("Das Blatt konnte nicht in den Schulordner gelegt werden.", sheet, async () => {
      await signed(post("/folder", { sheet_id: sheet.id, label: label.trim().slice(0, 40) }));
      setQ("");
      setSort("date");
      setRound((n) => n + 1);
      setParams({ tab: "ordner" }, { replace: true });
    });
  }
  function removeFromFolder(entry: FolderEntry) {
    if (!confirm(`Blatt „${entry.title}“ aus dem Schulordner löschen?`)) return;
    act("Das Blatt konnte nicht aus dem Schulordner gelöscht werden.", undefined, async () => {
      await signed(api(`/folder/${entry.id}`, { method: "DELETE" }));
      setFolder((got) => got && { ...got, sheets: got.sheets.filter((s) => s.id !== entry.id) });
    });
  }

  const tab = params.get("tab") === "ordner" && folder ? "ordner" : "mine";
  const show = (next: "mine" | "ordner") => setParams(next === "ordner" ? { tab: "ordner" } : {}, { replace: true });

  return (
    <main>
      {folder && (
        <div className="tabs" role="tablist">
          <button type="button" role="tab" aria-selected={tab === "mine"} onClick={() => show("mine")}>Meine Blätter</button>
          <button type="button" role="tab" aria-selected={tab === "ordner"} onClick={() => show("ordner")}>Schulordner</button>
        </div>
      )}
      <h1>{tab === "ordner" ? "Schulordner" : "Meine Blätter"}</h1>
      {tab === "mine" && (
        <button type="button" className="primary" onClick={create}>
          <Plus size={16} aria-hidden />
          Neues Blatt
        </button>
      )}
      {tab === "ordner" && folder && (
        <>
          <p className="lead">{folder.school.name}</p>
          <div className="folder-bar">
            <input type="search" value={q} maxLength={80} placeholder="Titel oder Kennzeichen" aria-label="Suche im Schulordner" onChange={(e) => setQ(e.target.value)} />
            <div className="seg" role="group" aria-label="Sortierung">
              {ORDERS.map(([key, word]) => (
                <button key={key} type="button" className={sort === key ? "on" : undefined} aria-pressed={sort === key} onClick={() => setSort(key)}>{word}</button>
              ))}
            </div>
          </div>
        </>
      )}
      {folderFailed && !folder && <p className="lead">Der Schulordner konnte nicht geladen werden.</p>}
      {tab === "mine" && !failed && !sheets && <p className="lead" role="status">{late && "Lädt"}</p>}
      {tab === "mine" && failed && !sheets && <Failed retry={retry}><p><strong>Die Blätter konnten nicht geladen werden</strong></p></Failed>}
      {tab === "mine" && sheets?.length === 0 && <p className="lead">Noch kein Blatt. Leg dein erstes an.</p>}
      {tab === "ordner" && folder?.sheets.length === 0 && <p className="lead">{q.trim() ? "Kein Blatt dazu." : "Noch kein Blatt im Schulordner."}</p>}
      <ul className="sheets">
        {tab === "mine" && sheets?.map((sheet) => (
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
              <button type="button" className="plain" aria-label={`${sheet.title} teilen`} title="Teilen" onClick={() => setSharing(sheet)}>
                <Share2 size={16} aria-hidden />
              </button>
              <button type="button" className="plain" aria-label={`${sheet.title} duplizieren`} title="Duplizieren" onClick={() => duplicate(sheet)}>
                <Copy size={16} aria-hidden />
              </button>
              {folder && (
                <button type="button" className="plain" aria-label={`${sheet.title} in den Schulordner`} title="In den Schulordner" onClick={() => intoFolder(sheet)}>
                  <FolderInput size={16} aria-hidden />
                </button>
              )}
              <button type="button" className="plain" aria-label={`${sheet.title} löschen`} title="Löschen" onClick={() => remove(sheet)}>
                <Trash2 size={16} aria-hidden />
              </button>
            </div>
          </li>
        ))}
        {tab === "ordner" && folder?.sheets.map((entry) => (
          <li key={entry.id}>
            <Link to={`/ordner/${entry.id}`}>
              <Paper doc={entry.doc} k={147 / sizeOf(read(entry.doc), 0)[0]} />
              <strong>{entry.title}</strong>
              <small>{entry.author_name} · {day(entry.updated)}{entry.label ? ` · ${entry.label}` : ""}</small>
            </Link>
            {(folder.school.admin || entry.mine) && (
              <div>
                <button type="button" className="plain" aria-label={`${entry.title} aus dem Schulordner löschen`} title="Löschen" onClick={() => removeFromFolder(entry)}>
                  <Trash2 size={16} aria-hidden />
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {sharing && <ShareDialog id={sharing.id} title={sharing.title} onClose={() => setSharing(undefined)} />}
    </main>
  );
}
