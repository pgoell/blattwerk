import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, post, signed, type User } from "../api";
import Failed from "../components/Failed";
import { attempt } from "../fault";
import { K, Paper, read, sizeOf, type Doc, type Sheet } from "../sheet";
import Login from "./Login";

type Preview = { title: string; doc: Doc };

// The page a share link opens. It draws the frozen sheet and nothing of the account that owns it.
// A visitor without an account can look. The copy needs an account, and sign-up stays by invite.
export default function ShareView({ user, onDone }: { user: User | null; onDone: (user: User) => void }) {
  const { token } = useParams();
  const navigate = useNavigate();
  const [sheet, setSheet] = useState<Preview | null>();
  const [missing, setMissing] = useState(false);
  const [login, setLogin] = useState(false);
  const [tries, setTries] = useState(0);

  useEffect(() => {
    let on = true;
    setMissing(false);
    setSheet(undefined);
    api<Preview>(`/shares/${token}`).then(
      (next) => on && setSheet(next),
      (e: Error) => on && (e.message === "404" ? setMissing(true) : setSheet(null)),
    );
    return () => void (on = false);
  }, [token, tries]);

  async function copy() {
    const made = await attempt("Die Kopie konnte nicht angelegt werden.", () =>
      signed(post<Sheet>(`/shares/${token}/copy`)),
    );
    if (made) navigate(`/blatt/${made.id}`);
  }

  if (login && !user) return <Login onDone={onDone} />;
  if (missing) {
    return (
      <main className="share-page">
        <p><Link to="/">← Blattomat</Link></p>
        <h1>Dieser Link gilt nicht mehr</h1>
        <p className="lead">Das Blatt wurde gelöscht, oder die Lehrkraft hat den Link ausgeschaltet.</p>
      </main>
    );
  }
  if (sheet === null) {
    return (
      <main className="share-page">
        <Failed retry={() => setTries((n) => n + 1)}>
          <h1>Die Vorschau konnte nicht geladen werden</h1>
        </Failed>
      </main>
    );
  }
  if (!sheet) return <main className="share-page"><p>Lädt …</p></main>;

  const drawn = read(sheet.doc);
  const fit = Math.min(window.innerWidth, 960) - 32;
  return (
    <main className="share-page">
      <p><Link to="/">← Blattomat</Link></p>
      <h1>{sheet.title}</h1>
      <p className="lead">Vorschau. So war das Blatt, als der Link erstellt oder zuletzt aktualisiert wurde.</p>
      <div className="pages">
        {drawn.pages.map((_, n) => {
          const [w] = sizeOf(drawn, n);
          return <Paper key={n} doc={drawn} k={Math.min(K, fit / w)} page={n} />;
        })}
      </div>
      <div className="row">
        <button type="button" className="primary" onClick={() => (user ? void copy() : setLogin(true))}>
          Kopie in meine Blätter
        </button>
      </div>
      {!user && <p className="hint">Zum Kopieren brauchst du ein Konto. Ein Konto gibt es nur auf Einladung.</p>}
    </main>
  );
}
