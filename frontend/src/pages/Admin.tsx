import { useEffect, useState } from "react";
import { api, post, type User } from "../api";

export default function Admin() {
  const [users, setUsers] = useState<User[]>([]);
  // The newest link, shown once so it can be copied and sent by hand.
  const [link, setLink] = useState({ label: "", url: "" });

  useEffect(() => {
    api<User[]>("/admin/users").then(setUsers);
  }, []);

  async function make(path: string, page: string, label: string) {
    const { token } = await post<{ token: string }>(path);
    setLink({ label, url: `${location.origin}/${page}/${token}` });
  }

  return (
    <main>
      <h1>Admin</h1>
      <div className="card">
        <button type="button" onClick={() => make("/admin/invites", "einladung", "Einladung")}>Einladung erstellen</button>
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
              <button type="button" className="plain" onClick={() => make(`/admin/users/${user.id}/reset`, "passwort", `Neues Passwort für ${user.email}`)}>
                Passwort-Link
              </button>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
