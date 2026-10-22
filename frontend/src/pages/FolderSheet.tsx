import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, post, type Refusal } from "../api";
import Failed from "../components/Failed";
import { attempt } from "../fault";
import { ask, signed } from "../saves";
import { Paper, read, sizeOf, type Doc, type Sheet } from "../sheet";

// The server keeps UTC, as "2026-10-06 09:30:00".
const day = (stamp: string) => new Date(`${stamp.replace(" ", "T")}Z`).toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });

export type School = { id: number; name: string; admin: boolean };
export type FolderEntry = {
  id: number;
  title: string;
  label: string;
  author_name: string;
  author_id: number | null;
  mine: boolean;
  created: string;
  updated: string;
  doc: Doc;
};
export type Folder = { school: School; sheets: FolderEntry[] };
type Opened = { school: School; sheet: FolderEntry };

export default function FolderSheet() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [row, setRow] = useState<Opened | null>();
  const [failed, setFailed] = useState(false);
  const [tries, setTries] = useState(0);
  const [late, setLate] = useState(false);
  const [mine, setMine] = useState<Sheet[]>([]);
  const [from, setFrom] = useState("");
  const [label, setLabel] = useState("");
  const frame = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);

  useEffect(() => {
    let on = true;
    setFailed(false);
    ask<Opened>(`/folder/${id}`).then(
      (got) => {
        if (!on) return;
        setRow(got);
        setLabel(got.sheet.label);
      },
      (e: Refusal) => {
        if (!on) return;
        if (e.message === "404" || e.message === "422") setRow(null);
        else setFailed(true);
      },
    );
    ask<Sheet[]>("/sheets").then(
      (all) => on && setMine(all),
      () => on && setMine([]),
    );
    return () => void (on = false);
  }, [id, tries]);

  useEffect(() => {
    setLate(false);
    const wait = setTimeout(() => setLate(true), 500);
    return () => clearTimeout(wait);
  }, [id, tries]);

  // The page is as wide as the column it sits in, so a phone does not scroll sideways.
  useEffect(() => {
    const el = frame.current;
    if (!el) return;
    const apply = () => setWidth(Math.max(1, el.clientWidth));
    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(el);
    return () => observer.disconnect();
  }, [row]);

  const reload = () => {
    setRow(undefined);
    setFailed(false);
    setTries((n) => n + 1);
  };
  const can = !!row && (row.school.admin || row.sheet.mine);

  function copy() {
    attempt("Die Kopie konnte nicht angelegt werden.", async () => {
      const sheet = await signed(post<Sheet>(`/folder/${id}/copy`));
      navigate(`/blatt/${sheet.id}`);
    });
  }
  function replace() {
    if (!from) return;
    attempt("Das Blatt konnte nicht ersetzt werden.", async () => {
      const saved = await signed(post<Opened>(`/folder/${id}/replace`, { sheet_id: Number(from) }));
      setRow(saved);
      setLabel(saved.sheet.label);
      setFrom("");
    });
  }
  function saveLabel(e: React.FormEvent) {
    e.preventDefault();
    attempt("Das Kennzeichen konnte nicht gespeichert werden.", async () => {
      const saved = await signed(post<Opened>(`/folder/${id}`, { label: label.trim().slice(0, 40) }, { method: "PATCH" }));
      setRow(saved);
      setLabel(saved.sheet.label);
    });
  }
  function remove() {
    if (!row || !confirm(`Blatt „${row.sheet.title}“ aus dem Schulordner löschen?`)) return;
    attempt("Das Blatt konnte nicht aus dem Schulordner gelöscht werden.", async () => {
      await signed(api(`/folder/${id}`, { method: "DELETE" }));
      navigate("/?tab=ordner");
    });
  }

  if (row === null) {
    return (
      <main>
        <h1>Blatt nicht gefunden</h1>
        <p><Link to="/?tab=ordner">Zum Schulordner</Link></p>
      </main>
    );
  }
  if (failed || !row) {
    return (
      <main>
        {failed ? <Failed retry={reload}><p><strong>Das Blatt konnte nicht geladen werden</strong></p></Failed> : <p className="lead" role="status">{late && "Lädt"}</p>}
      </main>
    );
  }

  const doc = read(row.sheet.doc);
  return (
    <main>
      <p><Link to="/?tab=ordner">Schulordner</Link></p>
      <h1>{row.sheet.title}</h1>
      <p className="lead">
        {row.sheet.author_name} · {day(row.sheet.updated)}
        {row.sheet.label ? ` · ${row.sheet.label}` : ""}
      </p>
      <p className="hint">Nur ansehen. Mit der Kopie wird es dein Blatt.</p>
      <div className="folder-bar">
        <button type="button" className="primary" onClick={copy}>Kopie in meine Blätter</button>
        {can && (
          <>
            <select aria-label="Blatt zum Ersetzen" value={from} onChange={(e) => setFrom(e.target.value)}>
              <option value="">Blatt wählen</option>
              {mine.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
            </select>
            <button type="button" disabled={!from} onClick={replace}>Ersetzen</button>
            <button type="button" className="danger" onClick={remove}>Löschen</button>
          </>
        )}
      </div>
      {can && (
        <form className="folder-bar" onSubmit={saveLabel}>
          <input type="text" aria-label="Kennzeichen" value={label} maxLength={40} placeholder="Klasse 2 oder Mathe" onChange={(e) => setLabel(e.target.value)} />
          <button type="submit">Kennzeichen speichern</button>
        </form>
      )}
      <div className="folder-pages" ref={frame}>
        {doc.pages.map((_, i) => <Paper key={i} doc={doc} page={i} k={width / sizeOf(doc, i)[0]} />)}
      </div>
    </main>
  );
}
