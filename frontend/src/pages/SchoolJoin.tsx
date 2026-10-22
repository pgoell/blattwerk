import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";
import { api, post, type Refusal, type User } from "../api";
import AuthShell from "../components/AuthShell";
import { status as reason, why } from "../fault";

type Invite = { email: string; school: string };

// A school link. Logged out, it makes the account. Logged in, it takes the seat.
export default function SchoolJoin({ user, onDone }: { user: User | null; onDone: (user: User) => void }) {
  const { token } = useParams();
  const navigate = useNavigate();
  const [invite, setInvite] = useState<Invite | null>();
  const [status, setStatus] = useState("");

  useEffect(() => {
    api<Invite>(`/school/invites/${token}`).then(setInvite, () => setInvite(null));
  }, [token]);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      if (user) {
        await post("/school/accept", { token });
      } else {
        const body = { token, ...Object.fromEntries(new FormData(e.currentTarget)) };
        onDone(await post<User>("/school/signup", body));
      }
      navigate("/schule");
    } catch (err) {
      const s = reason(err);
      const detail = (err as Refusal).detail;
      setStatus(
        s === "409" && detail
          ? detail
          : s === "offline" || s.startsWith("5")
            ? `Das hat nicht geklappt. ${why(s)}`
            : "Der Link gilt nicht mehr. Bitte frag nach einem neuen.",
      );
    }
  }

  if (invite === undefined) return null;
  const other = user && invite && user.email !== invite.email;
  return (
    <AuthShell
      title={invite ? invite.school : "Schulplatz"}
      lead={invite ? `Ein Platz an der ${invite.school}.` : "Der Link gilt nicht mehr."}
    >
      {invite && !other && (
        <form className="card" onSubmit={submit}>
          {!user && (
            <>
              <label htmlFor="email">E-Mail</label>
              <input id="email" name="email" type="email" readOnly value={invite.email} />
              <label htmlFor="password">Passwort</label>
              <p className="hint">Mindestens 8 Zeichen.</p>
              <input id="password" name="password" type="password" autoComplete="new-password" minLength={8} required />
            </>
          )}
          <button className="wide primary">{user ? "Platz annehmen" : "Konto anlegen"}</button>
          <div className="status" role="status">{status}</div>
        </form>
      )}
      {other && <p className="hint">Diese Einladung gilt für {invite.email}.</p>}
    </AuthShell>
  );
}
