import { useEffect, useState } from "react";
import { api, post, type User } from "../api";
import { attempt } from "../fault";
import { signed } from "../saves";

// The folder of a deleted account that would not go. `since` is UTC, "YYYY-MM-DD HH:MM:SS".
type Leftover = { folder: string; since: string; error: string };

const when = (since: string) =>
  new Date(`${since.replace(" ", "T")}Z`).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });

type Seat = { user_id: number; email: string; admin: boolean };
type School = { id: number; name: string; seats: Seat[] };

export default function Admin() {
  const [users, setUsers] = useState<User[]>([]);
  const [leftovers, setLeftovers] = useState<Leftover[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [schoolName, setSchoolName] = useState("");
  // The newest link, shown once so it can be copied and sent by hand.
  const [link, setLink] = useState({ label: "", url: "" });

  const loadSchools = () => signed(api<School[]>("/admin/schools")).then(setSchools);

  useEffect(() => {
    // Asked with the session run out, each brings the login. One that fails says so above the page.
    attempt("Die Konten konnten nicht geladen werden.", () => signed(api<User[]>("/admin/users")).then(setUsers));
    attempt("Die nicht gelöschten Ordner konnten nicht geladen werden.", () => signed(api<Leftover[]>("/admin/leftovers")).then(setLeftovers));
    attempt("Die Schulen konnten nicht geladen werden.", () => loadSchools());
  }, []);

  const make = (what: string, path: string, page: string, label: string) =>
    attempt(what, async () => {
      const made = await signed(post<{ token: string }>(path));
      setLink({ label, url: `${location.origin}/${page}/${made.token}` });
    });

  function createSchool(e: React.FormEvent) {
    e.preventDefault();
    const name = schoolName.trim();
    if (!name) return;
    attempt("Die Schule konnte nicht angelegt werden.", async () => {
      await signed(post("/admin/schools", { name }));
      setSchoolName("");
      await loadSchools();
    });
  }

  function addSeat(e: React.FormEvent<HTMLFormElement>, schoolId: number) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const email = String(data.get("email") ?? "").trim();
    if (!email) return;
    const form = e.currentTarget;
    attempt("Der Platz konnte nicht vergeben werden.", async () => {
      await signed(post(`/admin/schools/${schoolId}/seats`, { email, admin: data.get("admin") === "on" }));
      form.reset();
      await loadSchools();
    });
  }

  function removeSeat(schoolId: number, seat: Seat) {
    if (!confirm(`Platz von ${seat.email} entziehen?`)) return;
    attempt("Der Platz konnte nicht entzogen werden.", async () => {
      await signed(api(`/admin/schools/${schoolId}/seats/${seat.user_id}`, { method: "DELETE" }));
      await loadSchools();
    });
  }

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
      <div className="card schools">
        <label>Schulen</label>
        <p className="hint">Ein Platz öffnet den Schulordner. Schulleitung darf Blätter dort ersetzen und löschen.</p>
        <form onSubmit={createSchool}>
          <input type="text" aria-label="Name der Schule" value={schoolName} placeholder="Name der Schule" onChange={(e) => setSchoolName(e.target.value)} />
          <button type="submit" className="primary">Schule anlegen</button>
        </form>
        {schools.map((school) => (
          <div key={school.id}>
            <strong>{school.name}</strong>
            <ul className="rows">
              {school.seats.map((seat) => (
                <li key={seat.user_id}>
                  <span>{seat.email}{seat.admin ? " (Schulleitung)" : ""}</span>
                  <button type="button" className="plain" onClick={() => removeSeat(school.id, seat)}>Entziehen</button>
                </li>
              ))}
            </ul>
            <form onSubmit={(e) => addSeat(e, school.id)}>
              <input type="email" name="email" aria-label={`Platz an ${school.name}`} placeholder="lehrerin@schule.de" />
              <label><input type="checkbox" name="admin" /> Schulleitung</label>
              <button type="submit">Platz geben</button>
            </form>
          </div>
        ))}
      </div>
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
