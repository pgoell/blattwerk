import { useEffect, useState } from "react";
import { api, post, type User } from "../api";
import { attempt } from "../fault";
import { signed } from "../saves";

// The theme: Blattform until the teacher picks another; "" is the device's own. index.html sets it before the first paint.
const THEMES = [["leaf", "Blattform"], ["", "System"], ["light", "Hell"], ["dark", "Dunkel"]];

// `created` and `last_used` are UTC, "YYYY-MM-DD HH:MM:SS".
type Token = { id: number; name: string; created: string; last_used: string | null };
const when = (utc: string) =>
  new Date(`${utc.replace(" ", "T")}Z`).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });

export default function Account({ user, onGone }: { user: User; onGone: () => void }) {
  const [sure, setSure] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") ?? "leaf");
  const [tokens, setTokens] = useState<Token[]>([]);
  const [name, setName] = useState("");
  // The new key, shown once. It lives in this state only: not in storage, not in the URL.
  const [made, setMade] = useState<{ id: number; token: string } | null>(null);

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
    if (!label) return;
    attempt("Der Schlüssel konnte nicht erstellt werden.", async () => {
      const fresh = await signed(post<Token & { token: string }>("/tokens", { name: label }));
      setMade({ id: fresh.id, token: fresh.token });
      setName("");
      await load();
    });
  }

  function revoke(token: Token) {
    attempt("Der Schlüssel konnte nicht widerrufen werden.", async () => {
      await signed(api(`/tokens/${token.id}`, { method: "DELETE" }));
      if (made?.id === token.id) setMade(null);
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
        <form onSubmit={create}>
          <input aria-label="Name des Schlüssels" placeholder="Claude Desktop" maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />{" "}
          <button type="submit">Schlüssel erstellen</button>
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
              <button type="button" className="plain" aria-label={`Widerrufen: ${token.name}`} onClick={() => revoke(token)}>
                Widerrufen
              </button>
            </li>
          ))}
        </ul>
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
