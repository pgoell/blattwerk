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
// A page is about 60 mm wide on the screen.
const WIDTH = 227;

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

export default function Variants({ id, doc, count, setCount, letters, setLetters, opener, onClose }: {
  id: number;
  doc: Doc;
  count: number;
  setCount: (n: number) => void;
  letters: boolean;
  setLetters: (on: boolean) => void;
  opener: RefObject<HTMLElement | null>;
  onClose: () => void;
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

  // A preview of a letter the count has put away shows the last one left.
  const letter = LETTERS[Math.min(LETTERS.indexOf(shown), count - 1)];
  const variant = letter === "A" ? doc : got[letter]?.doc;
  const blocked = shorts(count, doc, got)[0];

  async function print(key: boolean) {
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
    } catch (e) {
      // A lost session brings the login, which takes the dialog away.
      const s = (e as Error).message;
      if (s !== "401" && s !== "stale") setFailed("Das PDF konnte nicht erstellt werden.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <dialog className="variants" ref={ref} onKeyDown={round} onClose={() => { opener.current?.focus(); onClose(); }}>
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
      <div className="preview" data-variant={letter}>
        {variant
          ? variant.pages.map((_, n) => <Paper key={n} doc={variant} k={WIDTH / sizeOf(read(variant), n)[0]} page={n} />)
          : "Lädt …"}
      </div>
      {(blocked ? message(blocked) : failed) && (
        <div className="clash" role="alert">{blocked ? message(blocked) : failed}</div>
      )}
      <div className="row">
        <button type="button" onClick={() => ref.current?.close()}>Schließen</button>
        <button type="button" disabled={busy} onClick={() => { setBusy(true); print(true); }}>
          <FileCheck size={14} aria-hidden />
          Lösungen
        </button>
        <button type="button" className="primary" disabled={busy} onClick={() => { setBusy(true); print(false); }}>
          <FileDown size={14} aria-hidden />
          PDF
        </button>
      </div>
    </dialog>
  );
}
