// Print variants: the sheet once per variant, so neighbours cannot copy. Nothing here is stored. The count and the
// letters switch live in the editor, so they stay while it is open.
import { useEffect, useRef, useState, type KeyboardEvent, type RefObject } from "react";
import { FileDown, FileCheck } from "lucide-react";
import { api } from "../api";
import { ask, flush, signed } from "../saves";
import { Paper, read, sizeOf, type Doc, type SelbstkontrolleBlock, type SuchselBlock } from "../sheet";
import { checked, sane as saneSelbst } from "../selbstkontrolle";
import { laid } from "../suchsel";

const LETTERS = ["A", "B", "C", "D"];
// A page is about 60 mm wide on the screen, until the preview has measured its room.
const WIDTH = 227;
// The space between the pages in the preview (styles.css).
const GAP = 12;

// Each page is as large as fits its share of the row, and as its own shape allows: an upright page and a Quer one
// keep their proportions and both stay whole. Never narrower than 120 px: past that the row scrolls sideways.
function fit(doc: Doc, n: number, pages: number, room: { w: number; h: number }) {
  const [w, h] = sizeOf(read(doc), n);
  if (!room.w) return WIDTH / w;
  return Math.max(120 / w, Math.min((room.w - GAP * (pages - 1)) / pages / w, room.h / h));
}

// The PDF of a clash waits for the teacher's choice, here and in the editor: the server holds the other device's sheet.
export const CLASH = "Dieses Blatt wurde auf einem anderen Gerät geändert. Wähle erst, welche Version gilt; dann druckt das PDF, was du hier siehst.";
// A newer version saved in another window, loaded by the press (#720).
export const NEWER = "Dieses Blatt wurde in einem anderen Fenster oder auf einem anderen Gerät geändert. Hier steht jetzt der neue Stand.";

type Short = { letter: string; page: number; id: string; type: string };
type Variant = { doc: Doc; short: Short[] };

function message({ letter, page, type }: Short) {
  const kind = type === "maths" ? "Rechnen" : type === "selbstkontrolle" ? "Selbstkontrolle" : "Suchsel";
  return `Variante ${letter}: Der ${kind}-Block auf Seite ${page} lässt sich nicht neu füllen. Würfle ihn neu, lockere die Vorgaben oder drucke weniger Varianten.`;
}

// Tab goes round the dialog and does not leave it for the page.
function round(e: KeyboardEvent<HTMLDialogElement>) {
  if (e.key !== "Tab") return;
  // A radio group has one tab stop, its checked button: the others are not on the trap's list.
  const all = e.currentTarget.querySelectorAll<HTMLElement>("input:not(:disabled, [type=radio]:not(:checked)), button:not(:disabled)");
  const first = all[0];
  const last = all[all.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}

function blocks(doc: Doc) {
  return doc.pages.flatMap((page, n) => page.blocks.map((block) => ({ block, page: n + 1 })));
}

// The Suchsel blocks the variant cannot fill: it leaves out more words than the stored sheet does.
function suchselShort(letter: string, variant: Doc, stored: Doc): Short[] {
  const found: Short[] = [];
  for (const { block, page } of blocks(variant)) {
    if (block.type !== "suchsel") continue;
    const was = blocks(stored).find((s) => s.block.id === block.id)?.block as SuchselBlock | undefined;
    if (was && laid(block.props).missed.length > laid(was.props).missed.length) found.push({ letter, page, id: block.id, type: block.type });
  }
  return found;
}

// The Selbstkontrollen the variant cannot fill: their word has a fault there and not on the stored sheet.
function selbstkontrolleShort(letter: string, variant: Doc, stored: Doc): Short[] {
  const found: Short[] = [];
  for (const { block, page } of blocks(variant)) {
    if (block.type !== "selbstkontrolle") continue;
    const was = blocks(stored).find((s) => s.block.id === block.id)?.block as SelbstkontrolleBlock | undefined;
    if (was && !checked(saneSelbst(was.props), stored).fault && checked(saneSelbst(block.props), variant).fault) found.push({ letter, page, id: block.id, type: block.type });
  }
  return found;
}

// What the variants of the count cannot fill, the first one named. Nothing until they have loaded.
function shorts(count: number, doc: Doc, got: Record<string, Variant>): Short[] {
  return LETTERS.slice(1, count).flatMap((letter) =>
    got[letter]
      ? [...got[letter].short.map((s) => ({ ...s, letter })), ...suchselShort(letter, got[letter].doc, doc), ...selbstkontrolleShort(letter, got[letter].doc, doc)]
      : [],
  );
}

export default function Variants({ id, doc, count, setCount, letters, setLetters, opener, onClose, clash, newer: loadNewer, print: printNow, fresh }: {
  id: number;
  doc: Doc;
  count: number;
  setCount: (n: number) => void;
  letters: boolean;
  setLetters: (on: boolean) => void;
  opener: RefObject<HTMLElement | null>;
  onClose: () => void;
  // Another device's version waits for the teacher's choice: the preview would not be what prints.
  clash: boolean;
  // Loads a newer version saved elsewhere before a press; true when the editor has taken it over.
  newer: (key: boolean) => Promise<boolean>;
  // Set when the dialog opens from a press: that press prints once at once (undefined: no print, false PDF, true Lösungen).
  print?: boolean;
  // A newer version was loaded for this dialog: the line says so.
  fresh?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [shown, setShown] = useState("A");
  const [got, setGot] = useState<Record<string, Variant>>({});
  const [failed, setFailed] = useState("");
  const [busy, setBusy] = useState(false);
  const ready = useRef<Promise<Record<string, Variant>> | undefined>(undefined);
  useEffect(() => ref.current?.showModal(), []);

  // The variants are asked for once, after the sheet's waiting change is saved: the server must hold what is shown.
  function load() {
    if (!ready.current) {
      ready.current = (async () => {
        await flush(id);
        const all = await Promise.all(
          LETTERS.slice(1).map(async (letter) => [letter, await signed(api<Variant>(`/sheets/${id}/variante/${letter}`))] as const),
        );
        return Object.fromEntries(all);
      })().catch((e) => {
        ready.current = undefined;
        throw e;
      });
    }
    return ready.current;
  }
  useEffect(() => {
    load().then(setGot, () => setFailed("Die Varianten konnten nicht geladen werden."));
  }, []);
  // A press that opened the dialog on the newer sheet prints once, at once: also where the effect runs twice.
  const printed = useRef(false);
  useEffect(() => {
    if (printNow === undefined || printed.current) return;
    printed.current = true;
    setBusy(true);
    void print(printNow);
  }, []);

  // The room the preview's pages share, measured as the dialog allows it.
  const box = useRef<HTMLDivElement>(null);
  const [room, setRoom] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const watch = new ResizeObserver(([entry]) => setRoom({ w: entry.contentRect.width, h: entry.contentRect.height }));
    if (box.current) watch.observe(box.current);
    return () => watch.disconnect();
  }, []);

  // A preview of a letter the count has put away shows the last one left.
  const letter = LETTERS[Math.min(LETTERS.indexOf(shown), count - 1)];
  const variant = letter === "A" ? doc : got[letter]?.doc;
  const blocked = shorts(count, doc, got)[0];
  // The newer line comes last: a clash, a block or a failure is what the teacher must act on.
  const line = clash ? CLASH : blocked ? message(blocked) : failed || (fresh ? NEWER : "");

  async function print(key: boolean) {
    // A newer version saved elsewhere is loaded first: this dialog goes, and the editor's new one takes over.
    if (await loadNewer(key)) return;
    setFailed("");
    try {
      // A load that failed before is tried again here, and what it brings is shown from now on.
      // A lost session goes on to the login, as below.
      const now = await load().catch((e) => {
        if (e.message === "401" || e.message === "stale") throw e;
        return null;
      });
      if (!now) return setFailed("Die Varianten konnten nicht geladen werden.");
      setGot(now);
      if (shorts(count, doc, now)[0]) return;
      // The variants were asked for once, at the load: the server may hold an older sheet than the editor shows now.
      const current = await flush(id);
      await ask("/me");
      const query = `varianten=${count}&buchstaben=${letters}${key ? "&solved=true" : ""}`;
      const res = await signed(fetch(`/api/sheets/${id}/pdf?${query}`));
      // The server names the block it cannot fill.
      if (res.status === 409) {
        const { detail } = await res.json();
        return setFailed(message(detail.short[0]));
      }
      if (!res.ok) throw new Error(String(res.status));
      const link = document.createElement("a");
      link.href = URL.createObjectURL(await res.blob());
      link.download = decodeURIComponent(/filename\*=UTF-8''(.+)/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "Blatt.pdf");
      link.click();
      // After the browser has taken the file.
      setTimeout(() => URL.revokeObjectURL(link.href), 60000);
      // Shown in the dialog, which stays open: the teacher can read it before shutting.
      if (!current) setFailed("Die Varianten zeigen den zuletzt gespeicherten Stand, nicht deine letzte Änderung: sie ist noch nicht gespeichert.");
    } catch (e) {
      // A lost session brings the login, which takes the dialog away.
      const s = (e as Error).message;
      if (s !== "401" && s !== "stale") setFailed("Das PDF konnte nicht erstellt werden.");
    } finally {
      setBusy(false);
    }
  }

  // Escape shuts the dialog at once: the browser's `close` comes a task later, and until then the focus stays inside it.
  // Schließen does the same.
  function shut() {
    ref.current!.close();
    opener.current?.focus();
    onClose();
  }
  function key(e: KeyboardEvent<HTMLDialogElement>) {
    if (e.key === "Escape" && ref.current!.open) {
      e.preventDefault();
      e.stopPropagation();
      shut();
      return;
    }
    round(e);
  }

  return (
    <dialog className="variants" ref={ref} onKeyDown={key} onClose={() => { opener.current?.focus(); onClose(); }}>
      <h1>Varianten drucken</h1>
      <fieldset>
        <legend>Varianten</legend>
        {[1, 2, 3, 4].map((n) => (
          <label key={n}>
            <input type="radio" name="varianten" checked={count === n} onChange={() => setCount(n)} />
            {n}
          </label>
        ))}
      </fieldset>
      <label>
        <input type="checkbox" checked={letters} onChange={(e) => setLetters(e.target.checked)} />
        Buchstabe auf jedem Blatt
      </label>
      <p className="lead">Die Lösungen tragen den Buchstaben immer.</p>
      <fieldset>
        <legend>Vorschau</legend>
        {LETTERS.slice(0, count).map((l) => (
          <label key={l}>
            <input type="radio" name="vorschau" checked={letter === l} onChange={() => setShown(l)} />
            {l}
          </label>
        ))}
      </fieldset>
      <div className="preview" data-variant={letter} ref={box}>
        {variant
          ? variant.pages.map((_, n) => <Paper key={n} doc={variant} k={fit(variant, n, variant.pages.length, room)} page={n} />)
          : "Lädt …"}
      </div>
      {line && <div className="clash" role="alert">{line}</div>}
      <div className="row">
        <button type="button" onClick={shut}>Schließen</button>
        <button type="button" disabled={busy || clash} onClick={() => { setBusy(true); print(true); }}>
          <FileCheck size={14} aria-hidden />
          Lösungen
        </button>
        <button type="button" className="primary" disabled={busy || clash} onClick={() => { setBusy(true); print(false); }}>
          <FileDown size={14} aria-hidden />
          PDF
        </button>
      </div>
    </dialog>
  );
}
