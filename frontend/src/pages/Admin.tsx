import { useEffect, useState, type FormEvent } from "react";
import { api, post, type Refusal, type User } from "../api";
import { attempt } from "../fault";
import { signed } from "../saves";

// The folder of a deleted account that would not go. `since` is UTC, "YYYY-MM-DD HH:MM:SS".
type Leftover = { folder: string; since: string; error: string };

const when = (since: string) =>
  new Date(`${since.replace(" ", "T")}Z`).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });

const day = (iso: string) => {
  const [year, month, date] = iso.slice(0, 10).split("-");
  return `${date}.${month}.${year}`;
};

type Invoice = { id: number; number: string; status: string };
type SchoolRow = {
  id: number;
  name: string;
  street: string;
  postcode: string;
  city: string;
  country: string;
  seats: number;
  taken: number;
  year_ends: string | null;
  active: boolean;
  admin_email: string;
  invoices: Invoice[];
};

// "1,5" is 150 cents. "19" is 1900 basis points. A comma is the German decimal mark.
function cents(typed: string): number | null {
  const match = typed.trim().match(/^(\d+)(?:,(\d{1,2}))?$/);
  if (!match) return null;
  const whole = Number(match[1]);
  if (whole > 1000000) return null;
  return whole * 100 + Number((match[2] ?? "").padEnd(2, "0"));
}

function basis(typed: string): number | null {
  const match = typed.trim().match(/^(\d+)(?:,(\d{1,2}))?$/);
  if (!match) return null;
  const points = Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
  return points <= 10000 ? points : null;
}

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
      <Schools />
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

// Quiet when it fails. The accounts and the folders already say when the server cannot be reached.
function Schools() {
  const [schools, setSchools] = useState<SchoolRow[]>();
  const [note, setNote] = useState("");
  const load = () => signed(api<SchoolRow[]>("/admin/schools")).then(setSchools, () => {});
  useEffect(() => {
    load();
  }, []);

  function issue(invoice: Invoice, e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const amount = cents(String(data.get("amount") ?? ""));
    const rate = basis(String(data.get("vat") ?? ""));
    const vatNote = String(data.get("vat_note") ?? "").trim();
    if (amount === null || rate === null) return setNote("Betrag und Umsatzsteuer brauchen eine Zahl, mit Komma.");
    if (rate === 0 && !vatNote) return setNote("Bei 0 % Umsatzsteuer braucht es einen Hinweis.");
    setNote("");
    attempt("Die Rechnung konnte nicht ausgestellt werden.", async () => {
      await signed(post(`/admin/invoices/${invoice.id}`, {
        amount_cents: amount,
        vat_rate: rate,
        vat_note: vatNote,
        tax_number: String(data.get("tax_number") ?? ""),
        seller_address: String(data.get("seller_address") ?? ""),
        due: String(data.get("due") ?? ""),
      }));
      await load();
    }, (s, err) => ((s === "409" || s === "422") && (err as Refusal).detail) || undefined);
  }

  if (!schools) return null;
  return (
    <div className="card">
      <label>Schulen</label>
      {schools.length === 0 && <p className="hint">Noch keine Schule.</p>}
      {note && <p className="hint">{note}</p>}
      {schools.map((school) => {
        const open = school.invoices.some((invoice) => invoice.status !== "paid");
        return (
          <div key={school.id}>
            <p>
              {school.name}, {school.admin_email}. {school.street}, {school.postcode} {school.city}. {school.taken} von {school.seats} Plätzen.
              {school.year_ends ? ` Bis ${day(school.year_ends)}${school.active ? "" : ", läuft nicht"}.` : " Noch kein Schuljahr."}
            </p>
            {school.invoices.map((invoice) => (
              <div key={invoice.id}>
                {invoice.status === "draft" ? (
                  <form onSubmit={(e) => issue(invoice, e)}>
                    <p>Rechnung {invoice.number}, Entwurf. Den Betrag schreibst du hier. Es gibt keinen Listenpreis.</p>
                    <label htmlFor={`amount-${invoice.id}`}>Netto in EUR</label>
                    <input id={`amount-${invoice.id}`} name="amount" required />
                    <label htmlFor={`vat-${invoice.id}`}>Umsatzsteuer in %</label>
                    <input id={`vat-${invoice.id}`} name="vat" required />
                    <label htmlFor={`note-${invoice.id}`}>Hinweis zur Umsatzsteuer</label>
                    <input id={`note-${invoice.id}`} name="vat_note" />
                    <label htmlFor={`tax-${invoice.id}`}>Steuernummer</label>
                    <input id={`tax-${invoice.id}`} name="tax_number" required />
                    <label htmlFor={`seller-${invoice.id}`}>Deine Anschrift auf der Rechnung</label>
                    <input id={`seller-${invoice.id}`} name="seller_address" required />
                    <label htmlFor={`due-${invoice.id}`}>Fällig am</label>
                    <input id={`due-${invoice.id}`} name="due" type="date" required />
                    <button className="primary">Rechnung ausstellen</button>
                  </form>
                ) : (
                  <p>
                    <a href={`/api/admin/invoices/${invoice.id}`}>Rechnung {invoice.number}</a>
                    {invoice.status === "paid" ? ", bezahlt" : ""}
                    {invoice.status === "issued" && (
                      <button
                        type="button"
                        className="plain"
                        onClick={() => attempt("Die Rechnung konnte nicht als bezahlt markiert werden.", () => signed(post(`/admin/invoices/${invoice.id}/paid`)).then(load))}
                      >
                        Als bezahlt markieren
                      </button>
                    )}
                  </p>
                )}
              </div>
            ))}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const when = String(new FormData(e.currentTarget).get("year_ends") ?? "");
                attempt("Das Schuljahr konnte nicht gesetzt werden.", () => signed(post(`/admin/schools/${school.id}/year`, { year_ends: when })).then(load));
              }}
            >
              <label htmlFor={`year-${school.id}`}>Schuljahr bis</label>
              <p className="hint">Ein vergangenes Datum beendet das Jahr, ein kommendes verlängert es. Die Plätze bleiben denselben Lehrkräften.</p>
              <input id={`year-${school.id}`} name="year_ends" type="date" required />
              <button>Schuljahr setzen</button>
            </form>
            {!open && (
              <button type="button" onClick={() => attempt("Die Rechnung konnte nicht angelegt werden.", () => signed(post(`/admin/schools/${school.id}/invoices`)).then(load))}>
                Neue Rechnung
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
