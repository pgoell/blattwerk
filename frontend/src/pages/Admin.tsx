import { useEffect, useState } from "react";
import { api, post, type User } from "../api";
import { attempt } from "../fault";
import { signed } from "../saves";

// The folder of a deleted account that would not go. `since` is UTC, "YYYY-MM-DD HH:MM:SS".
type Leftover = { folder: string; since: string; error: string };

const when = (since: string) =>
  new Date(`${since.replace(" ", "T")}Z`).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });

export default function Admin() {
  const [users, setUsers] = useState<User[]>([]);
  const [leftovers, setLeftovers] = useState<Leftover[]>([]);
  // The newest link, shown once so it can be copied and sent by hand.
  const [link, setLink] = useState({ label: "", url: "" });

  useEffect(() => {
    // Asked with the session run out, each brings the login. One that fails says so above the page.
    attempt("Die Konten konnten nicht geladen werden.", () => signed(api<User[]>("/admin/users")).then(setUsers));
    attempt("Die nicht gelöschten Ordner konnten nicht geladen werden.", () => signed(api<Leftover[]>("/admin/leftovers")).then(setLeftovers));
  }, []);

  const make = (what: string, path: string, page: string, label: string) =>
    attempt(what, async () => {
      const made = await signed(post<{ token: string }>(path));
      setLink({ label, url: `${location.origin}/${page}/${made.token}` });
    });

  return (
    <main>
      <h1>Admin</h1>
      {leftovers.length > 0 && (
        <div className="card alert" role="alert">
          <label>Nicht gelöschte Ordner</label>
          <p className="hint">Das Konto ist gelöscht, sein Ordner liegt noch auf dem Server. Jeder Neustart versucht es erneut.</p>
          <ul className="rows">
            {leftovers.map((left) => (
              <li key={left.folder}>
                <span>{left.folder}, seit {when(left.since)}: {left.error}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="card">
        <button type="button" className="primary" onClick={() => make("Die Einladung konnte nicht erstellt werden.", "/admin/invites", "einladung", "Einladung")}>Einladung erstellen</button>
      </div>
      {link.url && (
        <div className="card">
          <label>{link.label}</label>
          <p className="hint">Gilt einmal, 7 Tage lang. Kopieren und verschicken:</p>
          <p className="link">{link.url}</p>
        </div>
      )}
      <div className="card">
        <label>Konten</label>
        <ul className="rows">
          {users.map((user) => (
            <li key={user.id}>
              <span>{user.email}{user.admin && " (Admin)"}</span>
              <button type="button" className="plain" onClick={() => make("Der Passwort-Link konnte nicht erstellt werden.", `/admin/users/${user.id}/reset`, "passwort", `Neues Passwort für ${user.email}`)}>
                Passwort-Link
              </button>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
