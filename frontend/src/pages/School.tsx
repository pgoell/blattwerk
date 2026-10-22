import { useEffect, useState, type FormEvent } from "react";
import { api, post, type Refusal, type User } from "../api";
import { attempt, status } from "../fault";
import { signed } from "../saves";

type Invoice = { id: number; number: string; status: string };
type Member = { id: number; email: string };
type Pending = { email: string };
type Info = {
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
  head: boolean;
  invoices: Invoice[];
  avv: boolean;
  members?: Member[];
  invites?: Pending[];
};

const day = (iso: string) => {
  const [year, month, date] = iso.slice(0, 10).split("-");
  return `${date}.${month}.${year}`;
};

// A refusal that is the action's own (the seats are full, the year is over) says the server's sentence.
const own = (s: string, e: unknown) => (s === "409" ? (e as Refusal).detail : undefined);

export default function School({ user }: { user: User }) {
  const [school, setSchool] = useState<Info | null>();
  const [link, setLink] = useState("");

  const load = () =>
    signed(api<Info>("/school")).then(
      (next) => setSchool(next),
      (e: Error) => {
        if (status(e) === "404") return setSchool(null);
        throw e;
      },
    );

  useEffect(() => {
    attempt("Die Schule konnte nicht geladen werden.", load);
  }, []);

  function order(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const body = {
      name: String(data.get("name") ?? ""),
      street: String(data.get("street") ?? ""),
      postcode: String(data.get("postcode") ?? ""),
      city: String(data.get("city") ?? ""),
      country: String(data.get("country") ?? ""),
      seats: Number(data.get("seats")),
    };
    attempt("Die Schule konnte nicht angelegt werden.", () => signed(post<Info>("/school", body)).then(setSchool), own);
  }

  function invite(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const email = String(new FormData(form).get("email") ?? "");
    attempt(
      "Die Einladung konnte nicht erstellt werden.",
      async () => {
        const made = await signed(post<{ token: string }>("/school/invites", { email }));
        setLink(`${location.origin}/schulplatz/${made.token}`);
        form.reset();
        await load();
      },
      own,
    );
  }

  if (school === undefined) return null;
  if (!school) {
    return (
      <main>
        <h1>Schule</h1>
        <p className="hint">Ein Platz gilt zu Hause wie in der Schule. Den Preis setzt Pascal auf der Rechnung, es gibt hier keinen.</p>
        <form className="card" onSubmit={order}>
          <label htmlFor="name">Name der Schule</label>
          <input id="name" name="name" required maxLength={120} />
          <label htmlFor="street">Straße</label>
          <input id="street" name="street" required maxLength={120} />
          <label htmlFor="postcode">Postleitzahl</label>
          <input id="postcode" name="postcode" required maxLength={120} />
          <label htmlFor="city">Ort</label>
          <input id="city" name="city" required maxLength={120} />
          <label htmlFor="country">Land</label>
          <input id="country" name="country" required maxLength={120} defaultValue="Deutschland" />
          <label htmlFor="seats">Plätze</label>
          <input id="seats" name="seats" type="number" required min={1} max={500} />
          <button className="wide primary">Schule anlegen</button>
        </form>
      </main>
    );
  }

  return (
    <main>
      <h1>{school.name}</h1>
      <p className="hint">
        {school.street}, {school.postcode} {school.city}, {school.country}. {school.taken} von {school.seats} Plätzen belegt.
        {school.year_ends
          ? ` Schuljahr bis ${day(school.year_ends)}${school.active ? "" : ", es läuft nicht"}.`
          : " Das Schuljahr hat noch kein Datum."}
      </p>
      {school.head && (
        <div className="card">
          <label>Einladung</label>
          {school.active ? (
            <form onSubmit={invite}>
              <p className="hint">Gilt einmal, 7 Tage lang. Kopieren und verschicken:</p>
              <input name="email" type="email" autoComplete="off" required aria-label="E-Mail" />
              <button className="primary">Link erstellen</button>
            </form>
          ) : (
            <p className="hint">Einladen geht, sobald das Schuljahr läuft.</p>
          )}
          {link && <p className="link">{link}</p>}
          {!!school.invites?.length && (
            <ul className="rows">
              {school.invites.map((row) => (
                <li key={row.email}>
                  <span>{row.email}</span>
                  <button
                    type="button"
                    className="plain"
                    onClick={() =>
                      attempt("Die Einladung konnte nicht zurückgenommen werden.", async () => {
                        await signed(post("/school/invites/revoke", { email: row.email }));
                        await load();
                      })
                    }
                  >
                    Zurücknehmen
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {school.head && (
        <div className="card">
          <label>Lehrkräfte</label>
          <ul className="rows">
            {school.members?.map((member) => (
              <li key={member.id}>
                <span>{member.email}{member.id === user.id && " (Leitung)"}</span>
                {member.id !== user.id && (
                  <button
                    type="button"
                    className="plain"
                    onClick={() =>
                      attempt("Die Lehrkraft konnte nicht entfernt werden.", async () => {
                        await signed(api(`/school/members/${member.id}`, { method: "DELETE" }));
                        await load();
                      }, own)
                    }
                  >
                    Entfernen
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {school.head && (
        <div className="card">
          <label>Rechnung</label>
          {school.invoices.map((invoice) =>
            invoice.status === "draft" ? (
              <p key={invoice.id}>Rechnung {invoice.number} ist noch nicht ausgestellt.</p>
            ) : (
              <p key={invoice.id}>
                <a href={`/api/school/invoices/${invoice.id}`}>Rechnung {invoice.number} als PDF</a>
                {invoice.status === "paid" ? ", bezahlt" : ""}
              </p>
            ),
          )}
          {school.avv ? (
            <p><a href="/api/school/avv">AVV herunterladen</a></p>
          ) : (
            <p className="hint">Der AVV liegt noch nicht vor.</p>
          )}
        </div>
      )}
      {!school.head && !school.active && <p>Das Schuljahr ist zu Ende. Deine Blätter bleiben.</p>}
    </main>
  );
}
