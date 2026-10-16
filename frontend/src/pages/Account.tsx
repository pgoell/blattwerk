import { useEffect, useRef, useState } from "react";
import { api, post, type Refusal, type User } from "../api";
import { attempt, status } from "../fault";
import { signed } from "../saves";

// The theme: Blattform until the teacher picks another; "" is the device's own. index.html sets it before the first paint.
const THEMES = [["leaf", "Blattform"], ["", "System"], ["light", "Hell"], ["dark", "Dunkel"]];

// `created` and `last_used` are UTC, "YYYY-MM-DD HH:MM:SS".
type Token = { id: number; name: string; created: string; last_used: string | null };
const TAKEN = "Diesen Namen hat schon ein Schlüssel. Gib jedem Gerät einen eigenen Namen.";
const TOO_LONG = "Der Name ist zu lang: höchstens 80 Zeichen.";
const EMPTY = "Gib dem Schlüssel einen Namen.";
const when = (utc: string) =>
  new Date(`${utc.replace(" ", "T")}Z`).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });

export default function Account({ user, onGone }: { user: User; onGone: () => void }) {
  const [sure, setSure] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") ?? "leaf");
  const [tokens, setTokens] = useState<Token[]>([]);
  // The name typed when the session ran out: put back after the login.
  const [name, setName] = useState(() => {
    try {
      return sessionStorage.getItem("konto-name") ?? "";
    } catch {
      return "";
    }
  });
  // Under the name field: why the name was refused. Gone with the next typing.
  const [fieldNote, setFieldNote] = useState("");
  // The new key, shown once. It lives in this state only: not in storage, not in the URL.
  const [made, setMade] = useState<{ id: number; token: string } | null>(null);
  // A try that ran into the end of the session: said again here, after the new login. Kept in storage only for that.
  const [left, setLeft] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem("konto-left");
    } catch {
      return null;
    }
  });
  const [ask, setAsk] = useState<Token | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const rowButtons = useRef(new Map<number, HTMLButtonElement>());
  const askedId = useRef<number | null>(null);

  function leave(text: string, typed?: string) {
    try {
      sessionStorage.setItem("konto-left", text);
      if (typed !== undefined) sessionStorage.setItem("konto-name", typed);
    } catch {}
    setLeft(text);
  }

  function forget() {
    setLeft(null);
    try {
      sessionStorage.removeItem("konto-left");
      sessionStorage.removeItem("konto-name");
    } catch {}
  }

  function show(to: string) {
    localStorage.setItem("theme", to);
    document.documentElement.dataset.theme = to;
    setTheme(to);
  }

  // Quiet when it fails: the list is not what the teacher came for, and the next make or revoke loads it again.
  const load = () => signed(api<Token[]>("/tokens")).then(setTokens, () => {});

  useEffect(() => {
    load();
  }, []);

  function create(e: React.FormEvent) {
    e.preventDefault();
    const label = name.trim();
    if (!label) return setFieldNote("Gib dem Schlüssel einen Namen.");
    if (label.length > 80) return setFieldNote("Der Name ist zu lang: höchstens 80 Zeichen.");
    if (tokens.some((t) => t.name.toLowerCase() === label.toLowerCase())) return setFieldNote(TAKEN);
    attempt("Der Schlüssel konnte nicht erstellt werden.", async () => {
      try {
        const fresh = await signed(post<Token & { token: string }>("/tokens", { name: label }));
        setMade({ id: fresh.id, token: fresh.token });
        setName("");
        setFieldNote("");
        forget();
      } catch (err) {
        // The server's refusal: the name it already has, or a name it does not take.
        if (status(err) === "422") {
          const dup = (err as Refusal).detail === TAKEN;
          return setFieldNote(dup ? TAKEN : label.length > 80 ? TOO_LONG : EMPTY);
        }
        if (status(err) === "401" || (err as Error).message === "stale") leave(`Der Schlüssel „${label}“ wurde nicht erstellt: du warst abgemeldet. Erstelle ihn jetzt noch einmal.`, label);
        throw err;
      }
      await load();
    });
  }

  function revoke(token: Token) {
    askedId.current = token.id;
    setAsk(token);
    dialog.current?.showModal();
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
        <button type="button" onClick={() => attempt("Abmelden hat nicht geklappt.", () => signed(post("/logout")).then(onGone))}>Abmelden</button>
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
        <p className="hint">Mit einem Schlüssel kann Claude Desktop Blätter in deinem Konto anlegen und ändern. Gib jedem Gerät einen eigenen Namen.</p>
        {left && <p role="status" className="notice">{left}</p>}
        <form onSubmit={create}>
          <input
            aria-label="Name des Schlüssels"
            aria-describedby="name-note"
            placeholder="Claude Desktop"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setFieldNote("");
            }}
          />{" "}
          <button type="submit">Schlüssel erstellen</button>
          <p id="name-note" className="hint">{fieldNote}</p>
        </form>
        {made && (
          <div data-testid="new-token">
            <p className="hint">Nur jetzt sichtbar. Kopiere den Schlüssel jetzt; Blattomat zeigt ihn nicht noch einmal.</p>
            <code>{made.token}</code>{" "}
            <button type="button" className="plain" onClick={() => navigator.clipboard.writeText(made.token).catch(() => {})}>
              Kopieren
            </button>
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
          className="feedback"
          aria-labelledby="ask-revoke"
          onClose={() => {
            const back = askedId.current;
            if (back !== null) rowButtons.current.get(back)?.focus();
          }}
        >
          <p id="ask-revoke">Schlüssel „{ask?.name}“ widerrufen? Claude Desktop auf diesem Gerät verliert den Zugang.</p>
          <div className="row">
            <button type="button" onClick={() => ask && confirmRevoke(ask)}>
              Widerrufen
            </button>
            <button type="button" className="plain" onClick={() => dialog.current?.close()}>
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
