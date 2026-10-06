import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";
import { post, type User } from "../api";
import AuthShell from "../components/AuthShell";

// An invite link makes an account; a reset link sets a new password.
export default function SetPassword({ invite, onDone }: { invite?: boolean; onDone: (user: User) => void }) {
  const { token } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState("");

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const body = { token, ...Object.fromEntries(new FormData(e.currentTarget)) };
    try {
      onDone(await post<User>(invite ? "/signup" : "/reset", body));
      navigate("/");
    } catch (err) {
      setStatus(
        (err as Error).message === "409"
          ? "Für diese E-Mail gibt es schon ein Konto."
          : "Der Link gilt nicht mehr. Bitte frag nach einem neuen.",
      );
    }
  }

  return (
    <AuthShell
      title={invite ? "Willkommen bei Blattwerk" : "Neues Passwort"}
      lead={invite ? "Leg dein Konto an." : "Wähl ein neues Passwort."}
    >
      <form className="card" onSubmit={submit}>
        {invite && (
          <>
            <label htmlFor="email">E-Mail</label>
            <input id="email" name="email" type="email" autoComplete="username" required />
          </>
        )}
        <label htmlFor="password">Passwort</label>
        <p className="hint">Mindestens 8 Zeichen.</p>
        <input id="password" name="password" type="password" autoComplete="new-password" minLength={8} required />
        <button className="wide primary">{invite ? "Konto anlegen" : "Speichern"}</button>
        <div className="status" role="status">{status}</div>
      </form>
    </AuthShell>
  );
}
