import { useEffect, useRef, useState } from "react";
import { api, post, type Refusal, type User } from "../api";
import { attempt, status } from "../fault";
import { signed } from "../saves";
import { mark, wipe } from "../clip";

// The theme: Blattform until the teacher picks another; "" is the device's own. index.html sets it before the first paint.
const THEMES = [["leaf", "Blattform"], ["", "System"], ["light", "Hell"], ["dark", "Dunkel"]];

// `created` and `last_used` are UTC, "YYYY-MM-DD HH:MM:SS".
type Token = { id: number; name: string; created: string; last_used: string | null };
// A program connected over OAuth: the same times as a key.
type Connection = { id: number; name: string; created: string; last_used: string | null };
const TAKEN = "Diesen Namen hat schon ein Schlüssel. Gib jedem Gerät einen eigenen Namen.";
const TOO_LONG = "Der Name ist zu lang: höchstens 80 Zeichen.";
const EMPTY = "Gib dem Schlüssel einen Namen.";
// The note of a try that ran into the end of the session. One item, with the id of the account that made the try.
const NOTE = "konto-note";
type Note = { uid: number; text: string; name?: string };
function readNote(uid: number): Note | null {
  try {
    const note = JSON.parse(sessionStorage.getItem(NOTE) ?? "null") as Note | null;
    if (note?.uid === uid) return note;
    dropNote();
  } catch {}
  return null;
}
function writeNote(note: Note) {
  try {
    sessionStorage.setItem(NOTE, JSON.stringify(note));
  } catch {}
}
function dropNote() {
  try {
    sessionStorage.removeItem(NOTE);
  } catch {}
}

const when = (utc: string) =>
  new Date(`${utc.replace(" ", "T")}Z`).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });

export default function Account({ user, onGone }: { user: User; onGone: () => void }) {
  const [sure, setSure] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") ?? "leaf");
  const [tokens, setTokens] = useState<Token[]>([]);
  // What a try left when the session ran out, read once here: the line, and the name typed. Taken out of storage
  // at mount, so it shows once. Only for the account that made the try.
  const [note] = useState(() => readNote(user.id));
  const [name, setName] = useState(note?.name ?? "");
  // Under the name field: why the name was refused. Gone with the next typing.
  const [fieldNote, setFieldNote] = useState("");
  // The new key, shown once. It lives in this state only: not in storage, not in the URL.
  const [made, setMade] = useState<{ id: number; token: string } | null>(null);
  const [left, setLeft] = useState<string | null>(note?.text ?? null);
  const [ask, setAsk] = useState<Token | null>(null);
  const [links, setLinks] = useState<Connection[]>([]);
  const [unlink, setUnlink] = useState<Connection | null>(null);
  const linkDialog = useRef<HTMLDialogElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const rowButtons = useRef(new Map<number, HTMLButtonElement>());
  const askedId = useRef<number | null>(null);
  // A create is out: a press meanwhile does nothing.
  const busy = useRef(false);
  // A key was made and nothing typed since: the second press of a double one says nothing.
  const done = useRef(false);
  // What the copy button shows: "Kopiert" for two seconds, or the failure line.
  const [copy, setCopy] = useState<"done" | "failed" | null>(null);
  const copyTimer = useRef(0);
  const codeEl = useRef<HTMLElement>(null);

  function copyKey(token: string) {
    window.clearTimeout(copyTimer.current);
    const failed = () => {
      setCopy("failed");
      if (codeEl.current) window.getSelection()?.selectAllChildren(codeEl.current);
    };
    try {
      navigator.clipboard.writeText(token).then(() => {
        mark(token);
        setCopy("done");
        copyTimer.current = window.setTimeout(() => setCopy(null), 2000);
      }, failed);
    } catch {
      failed();
    }
  }

  function leave(text: string, typed?: string) {
    writeNote({ uid: user.id, text, name: typed });
    setLeft(text);
  }

  function forget() {
    setLeft(null);
    dropNote();
  }

  function show(to: string) {
    localStorage.setItem("theme", to);
    document.documentElement.dataset.theme = to;
    setTheme(to);
  }

  // Quiet when it fails: the list is not what the teacher came for, and the next make or revoke loads it again.
  const load = () => signed(api<Token[]>("/tokens")).then(setTokens, () => {});

  // The programs the teacher has connected: quiet when it fails, as the keys are.
  const loadLinks = () => signed(api<Connection[]>("/connections")).then(setLinks, () => {});

  function askUnlink(connection: Connection) {
    setUnlink(connection);
    linkDialog.current?.showModal();
  }

  function confirmUnlink(connection: Connection) {
    linkDialog.current?.close();
    attempt("Das Programm konnte nicht getrennt werden.", async () => {
      await signed(api(`/connections/${connection.id}`, { method: "DELETE" }));
      await loadLinks();
    });
  }

  useEffect(() => {
    dropNote();
    load();
    loadLinks();
  }, []);

  function create(e: React.FormEvent) {
    e.preventDefault();
    if (busy.current || done.current) return;
    const label = name.trim();
    if (!label) return setFieldNote("Gib dem Schlüssel einen Namen.");
    if (label.length > 80) return setFieldNote("Der Name ist zu lang: höchstens 80 Zeichen.");
    if (tokens.some((t) => t.name.toLowerCase() === label.toLowerCase())) return setFieldNote(TAKEN);
    busy.current = true;
    attempt("Der Schlüssel konnte nicht erstellt werden.", async () => {
      try {
        const fresh = await signed(post<Token & { token: string }>("/tokens", { name: label }));
        setMade({ id: fresh.id, token: fresh.token });
        window.clearTimeout(copyTimer.current);
        setCopy(null);
        setName("");
        setFieldNote("");
        forget();
        // At once: the field still holds the name until React draws it empty, and the list lacks the key until
        // `load` is back.
        done.current = true;
      } catch (err) {
        // The server's refusal: the name it already has, or a name it does not take.
        if (status(err) === "422") {
          const dup = (err as Refusal).detail === TAKEN;
          return setFieldNote(dup ? TAKEN : label.length > 80 ? TOO_LONG : EMPTY);
        }
        if (status(err) === "401" || (err as Error).message === "stale") leave(`Der Schlüssel „${label}“ wurde nicht erstellt: du warst abgemeldet. Erstelle ihn jetzt noch einmal.`, label);
        throw err;
      } finally {
        busy.current = false;
      }
      await load();
    });
  }

  function revoke(token: Token) {
    askedId.current = token.id;
    setAsk(token);
    dialog.current?.showModal();
    // Abbrechen has the focus, so Enter keeps the key.
    cancel.current?.focus();
  }

  function confirmRevoke(token: Token) {
    dialog.current?.close();
    attempt("Der Schlüssel konnte nicht widerrufen werden.", async () => {
      try {
        await signed(api(`/tokens/${token.id}`, { method: "DELETE" }));
      } catch (err) {
        // Already gone, from another tab: the list is what is left to show.
        if (status(err) === "401" || (err as Error).message === "stale") leave(`Der Schlüssel „${token.name}“ ist noch nicht widerrufen: du warst abgemeldet. Widerrufe ihn jetzt noch einmal.`);
        if (status(err) !== "404") throw err;
      }
      if (made?.id === token.id) setMade(null);
      forget();
      await load();
    });
  }

  return (
    <main>
      <h1>Konto</h1>
      <div className="card">
        <p>Angemeldet als {user.email}</p>
        <button
          type="button"
          // The editor's copy leaves the system's clipboard in the click, which lets the page write there.
          onClick={() => attempt("Abmelden hat nicht geklappt.", () => Promise.all([wipe(), signed(post("/logout"))]).then(onGone))}
        >
          Abmelden
        </button>
      </div>
      <div className="card">
        <label>Darstellung</label>
        <p className="hint">Grün als Blattform, so wie dein Gerät eingestellt ist, hell oder dunkel. Das Blatt selbst bleibt immer weiß.</p>
        <div className="seg">
          {THEMES.map(([to, label]) => (
            <button key={to} type="button" className={theme === to ? "on" : ""} aria-pressed={theme === to} onClick={() => show(to)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="card">
        <label>Zugang für Claude</label>
        <p className="hint">Claude ist ein KI-Assistent der Firma Anthropic aus den USA. Du schreibst Claude in ganzen Sätzen, was du brauchst, und Claude macht daraus Arbeitsblätter.</p>
        <p className="hint">Mit der Erweiterung für Claude Desktop und einem Schlüssel von hier darf Claude in deinem Konto Blätter anlegen und ändern. Dafür sieht Claude die Titel und Inhalte deiner Blätter, auch die Lernwörter, und Bilder der Seiten. Das und was du Claude schreibst, geht an Anthropic.</p>
        <p className="hint">Willst du aufhören, entfern die Erweiterung in Claude Desktop und klick unten beim Schlüssel auf Widerrufen.</p>
        <p>
          <a href="/blattomat.mcpb" download="blattomat.mcpb">
            Erweiterung für Claude Desktop herunterladen
          </a>
        </p>
        <p>
          <a href="/anleitung/claude" target="_blank" rel="noopener">
            So installierst du die Erweiterung
          </a>
        </p>
        <p>
          <a href="/datenschutz#claude" target="_blank" rel="noopener">
            Was an Anthropic geht: Datenschutz, Abschnitt 9
          </a>
        </p>
        {left && <p role="status" className="notice">{left}</p>}
        <form onSubmit={create}>
          <label htmlFor="key-name">Name des Schlüssels, z. B. Laptop Schule</label>
          <input
            id="key-name"
            type="text"
            aria-describedby="name-hint name-note"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setFieldNote("");
              done.current = false;
            }}
          />
          <p id="name-hint" className="hint">Gib jedem Schlüssel einen eigenen Namen, einen je Gerät.</p>
          <button type="submit">Schlüssel erstellen</button>
          <p id="name-note" className="hint">{fieldNote}</p>
        </form>
        {made && (
          <div data-testid="new-token">
            <p className="hint">Nur jetzt sichtbar. Kopiere den Schlüssel jetzt; Blattomat zeigt ihn nicht noch einmal.</p>
            <code ref={codeEl}>{made.token}</code>{" "}
            <button type="button" className="plain" aria-live="polite" onClick={() => copyKey(made.token)}>
              {copy === "done" ? "Kopiert" : "Kopieren"}
            </button>
            {copy === "failed" && <p role="alert" className="hint warn">Kopieren hat nicht geklappt. Markiere den Schlüssel und kopiere ihn mit Strg+C.</p>}
          </div>
        )}
        <ul className="rows">
          {tokens.map((token) => (
            <li key={token.id}>
              <span>
                {token.name}
                <br />
                <span className="hint">
                  erstellt {when(token.created)}, {token.last_used ? `zuletzt benutzt ${when(token.last_used)}` : "zuletzt benutzt: noch nie"}
                </span>
              </span>
              <button
                type="button"
                className="plain"
                aria-label={`Widerrufen: ${token.name}`}
                ref={(el) => {
                  if (el) rowButtons.current.set(token.id, el);
                  else rowButtons.current.delete(token.id);
                }}
                onClick={() => revoke(token)}
              >
                Widerrufen
              </button>
            </li>
          ))}
        </ul>
        <dialog
          ref={dialog}
          className="ask"
          aria-labelledby="ask-revoke"
          onClose={() => {
            const back = askedId.current;
            if (back !== null) rowButtons.current.get(back)?.focus();
          }}
        >
          <p id="ask-revoke">Schlüssel „{ask?.name}“ widerrufen? Was diesen Schlüssel nutzt, verliert den Zugang.</p>
          <div className="row">
            <button type="button" onClick={() => ask && confirmRevoke(ask)}>
              Widerrufen
            </button>
            <button type="button" className="plain" ref={cancel} onClick={() => dialog.current?.close()}>
              Abbrechen
            </button>
          </div>
        </dialog>
      </div>
      <div className="card">
        <label>Verbundene Programme</label>
        <p className="hint">Programme wie Claude, die du auf einer Seite von Blattomat erlaubt hast.</p>
        {links.length === 0 && <p>Noch kein Programm verbunden.</p>}
        <ul className="rows">
          {links.map((connection) => (
            <li key={connection.id}>
              <span>
                {connection.name}
                <br />
                <span className="hint">
                  verbunden {when(connection.created)}, {connection.last_used ? `zuletzt benutzt ${when(connection.last_used)}` : "zuletzt benutzt: noch nie"}
                </span>
              </span>
              <button type="button" className="plain" aria-label={`Trennen: ${connection.name}`} onClick={() => askUnlink(connection)}>
                Trennen
              </button>
            </li>
          ))}
        </ul>
        <dialog ref={linkDialog} className="ask" aria-labelledby="ask-unlink">
          <p id="ask-unlink">„{unlink?.name}“ trennen? Das Programm verliert den Zugang zu deinem Konto.</p>
          <div className="row">
            <button type="button" onClick={() => unlink && confirmUnlink(unlink)}>
              Trennen
            </button>
            <button type="button" className="plain" onClick={() => linkDialog.current?.close()}>
              Abbrechen
            </button>
          </div>
        </dialog>
      </div>
      <div className="card">
        <label>Konto löschen</label>
        <p className="hint">Löscht dein Konto und alles, was du geschickt hast. Das lässt sich nicht rückgängig machen.</p>
        {sure ? (
          <button type="button" className="danger" onClick={() => attempt("Das Konto konnte nicht gelöscht werden.", () => signed(api("/me", { method: "DELETE" })).then(onGone))}>
            Ja, endgültig löschen
          </button>
        ) : (
          <button type="button" className="plain" onClick={() => setSure(true)}>Konto löschen …</button>
        )}
      </div>
    </main>
  );
}
