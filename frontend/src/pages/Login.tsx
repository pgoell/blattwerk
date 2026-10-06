import { useState, type FormEvent } from "react";
import { post, type User } from "../api";
import AuthShell from "../components/AuthShell";

export default function Login({ onDone }: { onDone: (user: User) => void }) {
  const [status, setStatus] = useState("");

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      onDone(await post<User>("/login", Object.fromEntries(new FormData(e.currentTarget))));
    } catch (err) {
      setStatus(
        (err as Error).message === "429"
          ? "Zu viele Versuche. Bitte in einer Viertelstunde nochmal."
          : "E-Mail oder Passwort stimmt nicht.",
      );
    }
  }

  return (
    <AuthShell title="Anmelden" lead="Schön, dass du da bist.">
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
