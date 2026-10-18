import { useState, type FormEvent } from "react";
import { post, type User } from "../api";
import { wipeAt } from "../clip";
import AuthShell from "../components/AuthShell";
import { status as reason, why } from "../fault";
import { useSaves } from "../saves";

export default function Login({ onDone }: { onDone: (user: User) => void }) {
  const [status, setStatus] = useState("");
  const ran = useSaves().list.some((s) => s.stopped);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      const login = post<User>("/login", Object.fromEntries(new FormData(e.currentTarget)));
      wipeAt(login);
      onDone(await login);
    } catch (err) {
      // With no connection or a fault of the server the password is not the one to blame.
      const s = reason(err);
      setStatus(
        s === "429"
          ? "Zu viele Versuche. Bitte in einer Viertelstunde nochmal."
          : s === "offline" || s.startsWith("5")
            ? `Die Anmeldung hat nicht geklappt. ${why(s)}`
            : "E-Mail oder Passwort stimmt nicht.",
      );
    }
  }

  return (
    // A login that a run out session brought says so first: the sheet takes no more keys until the sign-in (#813).
    <AuthShell title="Anmelden" lead={ran ? "Deine Anmeldung ist abgelaufen. Bis du dich neu anmeldest, nimmt das Blatt keine Eingaben an. Was du bis hierher eingegeben hast, bleibt erhalten." : "Schön, dass du da bist."}>
      <form className="card" onSubmit={submit}>
        <label htmlFor="email">E-Mail</label>
        <input id="email" name="email" type="email" autoComplete="username" required />
        <label htmlFor="password">Passwort</label>
        <input id="password" name="password" type="password" autoComplete="current-password" required />
        <button className="wide primary">Anmelden</button>
        <div className="status" role="status">{status}</div>
      </form>
      <p className="hint">Passwort vergessen? Schreib mir, dann bekommst du einen Link.</p>
    </AuthShell>
  );
}
