import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Copy, Ellipsis, FolderInput, Pencil, Plus, Search, Share2, Trash2 } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api, post, type Refusal } from "../api";
import Confirm from "../components/Confirm";
import Failed from "../components/Failed";
import Menu from "../components/Menu";
import NewSheet from "../components/NewSheet";
import ShareDialog from "../components/ShareDialog";
import { attempt } from "../fault";
import { ask, forget, served, signed, useSaves } from "../saves";
import { EMPTY, Paper, read, sizeOf, type Sheet } from "../sheet";
import { sheetOf } from "../templates";
import type { Template } from "./editor/palette";
import { type Folder, type FolderEntry } from "./FolderSheet";

// The width of a row's small page, in px.
const SMALL = 56;
// The server keeps UTC, as "2026-10-06 09:30:00".
const day = (stamp: string) => new Date(`${stamp.replace(" ", "T")}Z`).toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });
// A change of today or yesterday says so; an older one has its date. By the days of this teacher's clock.
const when = (stamp: string) => {
  const then = new Date(`${stamp.replace(" ", "T")}Z`);
  const noon = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 12).getTime();
  const days = Math.round((noon(new Date()) - noon(then)) / 86400000);
  return days <= 0 ? "heute" : days === 1 ? "gestern" : day(stamp);
};
const pagesOf = (sheet: { doc: Sheet["doc"] }) => {
  const n = read(sheet.doc).pages.length;
  return `${n} ${n === 1 ? "Seite" : "Seiten"}`;
};
// The columns a click on their head sorts by, each with the way it starts: the newest first, the titles from A.
const COLUMNS = [["title", "Titel", false], ["date", "Zuletzt geändert", true]] as const;
type Column = (typeof COLUMNS)[number][0];
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
  // "Neues Blatt" opens the chooser. A sheet made from a template takes the template's name as its title.
  const [choosing, setChoosing] = useState(false);
  const create = (t?: Template) =>
    act("Das neue Blatt konnte nicht angelegt werden.", undefined, async () => {
      const made = t ? { title: t.name, doc: await sheetOf(t) } : { title: "Unbenanntes Blatt", doc: EMPTY };
      const sheet = await signed(post<Sheet>("/sheets", made));
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
  // Deleting asks in the app's own dialog, with the sheet's name.
  const [doomed, setDoomed] = useState<Sheet>();
  const [leaving, setLeaving] = useState<FolderEntry>();
  function remove(sheet: Sheet) {
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
    act("Das Blatt konnte nicht aus dem Schulordner gelöscht werden.", undefined, async () => {
      await signed(api(`/folder/${entry.id}`, { method: "DELETE" }));
      setFolder((got) => got && { ...got, sheets: got.sheets.filter((s) => s.id !== entry.id) });
    });
  }

  // The list as the teacher asked for it: the titles that hold the search's words, in the order of the picked column.
  const [find, setFind] = useState("");
  const [order, setOrder] = useState<{ by: Column; down: boolean }>({ by: "date", down: true });
  const sortBy = (by: Column, down: boolean) => setOrder((now) => (now.by === by ? { by, down: !now.down } : { by, down }));
  const words = find.trim().toLocaleLowerCase("de");
  const hits = sheets?.filter((sheet) => sheet.title.toLocaleLowerCase("de").includes(words));
  // Sheets changed in the same second stand as the server gives them: the later made first.
  const rows = hits && [...hits].sort((a, b) => {
    const way = order.by === "title" ? a.title.localeCompare(b.title, "de", { numeric: true, sensitivity: "base" }) : a.updated.localeCompare(b.updated) || a.id - b.id;
    return order.down ? -way : way;
  });
  // The row whose "Weitere Aktionen" is open, and where its menu lies.
  const [more, setMore] = useState<{ sheet: Sheet; x: number; y: number }>();
  // The button stands over the list, or in the empty list's own words once the sheets have come and there are none.
  // It is another element there, so the one that leaves hands the focus it held on to the one that comes.
  const opener = useRef<HTMLButtonElement | null>(null);
  const held = useRef(false);
  const stand = useCallback((el: HTMLButtonElement | null) => {
    if (!el) return void (held.current = document.activeElement === opener.current);
    opener.current = el;
    if (held.current) el.focus();
    held.current = false;
  }, []);
  const newSheet = (
    <button ref={stand} type="button" className="primary" aria-haspopup="dialog" onClick={() => setChoosing(true)}>
      <Plus size={16} aria-hidden />
      Neues Blatt
    </button>
  );
  // An empty list and a search without a hit offer the new sheet themselves: then the button over the list is theirs.
  const none = sheets?.length === 0;
  const missed = !!sheets?.length && rows?.length === 0;

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
      {tab === "mine" && !none && !missed && newSheet}
      {tab === "mine" && !!sheets?.length && (
        <div className="list-bar">
          <label className="find">
            <Search size={15} aria-hidden />
            <input type="search" value={find} maxLength={80} placeholder="Blatt suchen" aria-label="Blätter suchen" onChange={(e) => setFind(e.target.value)} />
          </label>
        </div>
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
      {tab === "mine" && none && (
        <div className="empty">
          <p className="lead">Noch kein Blatt. Leg dein erstes an.</p>
          {newSheet}
        </div>
      )}
      {tab === "mine" && missed && (
        <div className="empty" role="status">
          <p className="lead">Kein Blatt passt zu „{find.trim()}“.</p>
          <div>
            <button type="button" onClick={() => setFind("")}>Suche leeren</button>
            {newSheet}
          </div>
        </div>
      )}
      {tab === "mine" && !!rows?.length && (
        <div className="sheets-head">
          <span />
          {COLUMNS.map(([by, word, down]) => (
            <button key={by} type="button" className="plain" aria-pressed={order.by === by} aria-label={`Nach ${word} sortieren`} data-order={order.by === by ? (order.down ? "down" : "up") : undefined} onClick={() => sortBy(by, down)}>
              {word}
              {order.by === by && (order.down ? <ArrowDown size={13} aria-hidden /> : <ArrowUp size={13} aria-hidden />)}
            </button>
          ))}
          <span>Seiten</span>
          <span />
        </div>
      )}
      {tab === "ordner" && folder?.sheets.length === 0 && <p className="lead">{q.trim() ? "Kein Blatt dazu." : "Noch kein Blatt im Schulordner."}</p>}
      <ul className="sheets">
        {tab === "mine" && rows?.map((sheet) => (
          <li key={sheet.id}>
            <Link to={`/blatt/${sheet.id}`}>
              <Paper doc={sheet.doc} k={SMALL / sizeOf(read(sheet.doc), 0)[0]} />
              <strong>{sheet.title}</strong>
              <small title={day(sheet.updated)}>{when(sheet.updated)}</small>
              <small>{pagesOf(sheet)}</small>
            </Link>
            <div>
              <button type="button" className="plain" aria-label={`${sheet.title} teilen`} onClick={() => setSharing(sheet)}>
                <Share2 size={15} aria-hidden />
                Teilen
              </button>
              <button type="button" className="plain" aria-label={`${sheet.title} duplizieren`} onClick={() => duplicate(sheet)}>
                <Copy size={15} aria-hidden />
                Kopie
              </button>
              <button
                type="button"
                className="plain"
                aria-label={`${sheet.title}: weitere Aktionen`}
                title="Weitere Aktionen"
                aria-haspopup="menu"
                onClick={(e) => {
                  const at = e.currentTarget.getBoundingClientRect();
                  setMore({ sheet, x: at.left, y: at.bottom + 4 });
                }}
              >
                <Ellipsis size={16} aria-hidden />
              </button>
            </div>
          </li>
        ))}
        {tab === "ordner" && folder?.sheets.map((entry) => (
          <li key={entry.id}>
            <Link to={`/ordner/${entry.id}`}>
              <Paper doc={entry.doc} k={SMALL / sizeOf(read(entry.doc), 0)[0]} />
              <strong>{entry.title}</strong>
              <small>{entry.author_name} · {when(entry.updated)}{entry.label ? ` · ${entry.label}` : ""}</small>
              <small>{pagesOf(entry)}</small>
            </Link>
            {(folder.school.admin || entry.mine) && (
              <div>
                <button type="button" className="plain" aria-label={`${entry.title} aus dem Schulordner löschen`} title="Löschen" onClick={() => setLeaving(entry)}>
                  <Trash2 size={16} aria-hidden />
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {more && (
        <Menu
          x={more.x}
          y={more.y}
          items={[
            { label: "Umbenennen", icon: Pencil, run: () => rename(more.sheet) },
            ...(folder ? [{ label: "In den Schulordner", icon: FolderInput, run: () => intoFolder(more.sheet) }] : []),
            "sep",
            { label: "Löschen", icon: Trash2, run: () => setDoomed(more.sheet) },
          ]}
          onClose={() => setMore(undefined)}
          onElsewhere={() => setMore(undefined)}
        />
      )}
      {doomed && (
        <Confirm title={`Blatt „${doomed.title}“ löschen?`} yes="Blatt löschen" danger onYes={() => remove(doomed)} onClose={() => setDoomed(undefined)}>
          <p>Das Blatt mit {pagesOf(doomed)} wird gelöscht und kommt nicht zurück.</p>
        </Confirm>
      )}
      {leaving && (
        <Confirm title={`Blatt „${leaving.title}“ aus dem Schulordner löschen?`} yes="Aus dem Ordner löschen" danger onYes={() => removeFromFolder(leaving)} onClose={() => setLeaving(undefined)}>
          <p>Das Blatt verschwindet für alle aus dem Schulordner.</p>
        </Confirm>
      )}
      {choosing && <NewSheet onPick={create} onClose={() => setChoosing(false)} back={() => opener.current} />}
      {sharing && <ShareDialog id={sharing.id} title={sharing.title} onClose={() => setSharing(undefined)} />}
    </main>
  );
}
