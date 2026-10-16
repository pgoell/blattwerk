import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, Outlet, Route, Routes, useMatch, useNavigate } from "react-router";
import { api, type User } from "./api";
import Blank from "./components/Blank";
import Failed from "./components/Failed";
import Feedback, { forgetDraft } from "./components/Feedback";
import Logo from "./components/Logo";
import { clear, Faults, status } from "./fault";
import About from "./pages/About";
import Account from "./pages/Account";
import Admin from "./pages/Admin";
import Login from "./pages/Login";
import Photos, { forgetPhotos } from "./pages/Photos";
import Print from "./pages/Print";
import SetPassword from "./pages/SetPassword";
import SheetList from "./pages/SheetList";
import * as saves from "./saves";
import { type Sheet } from "./sheet";

// The editor brings the canvas libraries; the login page loads without them.
const Editor = lazy(() => import("./pages/Editor"));

export default function App() {
  // undefined while /me is loading, null when logged out.
  const [user, setUser] = useState<User | null>();

  // The savers hear who is there, and take up what the browser kept for that account. A save, or any request of a
  // sheet or the list, that finds the session gone brings the login here, on the address as it stands: a change is
  // kept, and saved after the login. `was` is who was signed in until then: the login page says whose change waits.
  const was = useRef<number>(undefined);
  // The account check: a 401 says the session is gone; any other failure says the server cannot be reached, and the
  // account stays unknown, so no kept change is touched. `down` shows that page in place of the login, and `trying`
  // shows the loading page while a try is out.
  const [down, setDown] = useState(false);
  const [trying, setTrying] = useState(false);
  // Each try takes the next number, and only the newest one's answer counts: an older try that answers late is no
  // answer about the account now. A sign-in takes a number too, so a check still out before it is outdated.
  const tries = useRef(0);
  const check = () => {
    const mine = ++tries.current;
    const newest = () => mine === tries.current;
    setTrying(true);
    api<User>("/me")
      .then(
        (to) => {
          if (!newest()) return;
          saves.enter(to.id);
          setDown(false);
          setUser(to);
        },
        (e) => {
          if (!newest()) return;
          if (status(e) === "401") {
            setDown(false);
            setUser(null);
          } else setDown(true);
        },
      )
      .finally(() => newest() && setTrying(false));
  };
  useEffect(() => {
    check();
    saves.onSignedOut(() => setUser(null));
    // A sheet served for another account: somebody signed in in another tab. The window asks who, one request at a
    // time, and goes on as at that one's login. Where the answer names the account the window holds, the sheet was
    // a late one of the account before, and nothing happens; nor where there is no answer: the next such sheet
    // asks again.
    let asking = false;
    saves.onOther(() => {
      if (asking) return;
      asking = true;
      saves
        .signed(api<User>("/me"))
        .then((to) => to.id !== was.current && enter(to), () => {})
        .finally(() => (asking = false));
    });
  }, []);
  if (user) was.current = user.id;

  // A login or a logout empties the block clipboard: what one account copied is not the next one's. An unsaved
  // change stays in the browser's store for its owner, and the savers hear who is there now.
  const [entered, setEntered] = useState(0);
  const enter = (to: User | null) => {
    localStorage.removeItem("clip");
    localStorage.removeItem("pages");
    // Feedback and photos entered when the session ran out wait for the teacher who entered them, and nobody else.
    // So does a line of an action that failed.
    if (to?.id !== was.current) (forgetDraft(), forgetPhotos(), clear());
    tries.current++;
    saves.enter(to?.id);
    // A login from a link's page answers the account check too: a logout after it shows the login.
    setDown(false);
    setUser(to);
    setEntered((n) => n + 1);
  };

  // A sheet shows its loading page at once, and one clock runs while the account, the editor's script and the
  // sheet load. A login on a sheet's address starts the clock anew: the time at the login page is no loading.
  const { id } = useMatch("/blatt/:id")?.params ?? {};
  const since = useMemo(() => performance.now(), [id, entered]);
  // The clock is kept here and not in the loading page: the account, the editor's script and the sheet each draw
  // that page anew, and one drawn before the half second whose effect ran after it set a timer for a time gone by.
  // `late` holds the `since` it is true for, so a new sheet or a login starts with no word.
  const [late, setLate] = useState<number>();
  useEffect(() => {
    if (!id) return;
    const left = 500 - (performance.now() - since);
    if (left <= 0) return setLate(since);
    const timer = setTimeout(() => setLate(since), left);
    return () => clearTimeout(timer);
  }, [since]);
  const wait = <Blank late={late === since} />;
  // The sheet is asked for as soon as the account is known, side by side with the editor's script and not after
  // it. Each visit asks anew. A sheet that is not there is null, and a load that failed says so: nobody may hear of
  // either before the script has come.
  // Each sheet has an editor of its own: on to another sheet, the one left saves and goes, the loading page stands
  // at once, and a late answer for the sheet left finds nobody to show it.
  // The sheet left saves as it goes, and no load waits for that save: back on the sheet left, its saver shows what
  // the answer does not hold yet.
  const [first, setFirst] = useState<{ id: string; sheet: ReturnType<typeof saves.get> }>();
  useEffect(() => {
    setFirst(user && id ? { id, sheet: saves.get(id) } : undefined);
  }, [user, id]);

  if (user === undefined && !down) return id ? wait : null;
  // Where the account is not known, the pages that need no account still show; the others wait for a try or say so.
  const reach = trying ? (id ? wait : null) : <main><Failed retry={check}><h1>Blattomat erreicht den Server nicht</h1></Failed></main>;
  return (
    <>
      <Notices owner={user?.id ?? was.current} id={user ? id : undefined} />
      <Faults />
      <Routes>
        <Route path="/einladung/:token" element={<SetPassword invite onDone={enter} />} />
        <Route path="/passwort/:token" element={<SetPassword onDone={enter} />} />
        <Route path="/ueber" element={<About />} />
        <Route path="/druck/:id" element={<Print />} />
        {user ? (
          <Route element={<Layout user={user} />}>
            <Route path="/" element={<SheetList />} />
            <Route path="/blatt/:id" element={first && first.id === id ? <Suspense fallback={wait}><Editor key={id} user={user} wait={wait} first={first.sheet} /></Suspense> : wait} />
            <Route path="/feedback/fotos" element={<Photos />} />
            {/* Another account starts the page anew: nothing of the one before stays on it, not a key shown once. */}
            <Route path="/konto" element={<Account key={user.id} user={user} onGone={() => enter(null)} />} />
            {user.admin && <Route path="/admin" element={<Admin />} />}
            <Route path="*" element={<main><h1>Seite nicht gefunden</h1></main>} />
          </Route>
        ) : (
          // Logged out, every path shows the login; the page asked for opens after it.
          <Route path="*" element={down ? reach : <Login onDone={enter} />} />
        )}
      </Routes>
      <footer>
        <a href="/impressum">Impressum</a>
        <a href="/datenschutz">Datenschutz</a>
        <Link to="/ueber">Über</Link>
      </footer>
    </>
  );
}

// A line for each sheet that is not on screen and whose last change is not saved yet: after a second, or as soon as
// the save failed. It goes when the save lands. Nothing stands here while there is nothing to say. At the login
// that a save brought, the sheet on the address has no editor, so its line stands too; a logout leaves no saver.
// A sheet deleted on another device has a line with the teacher's two choices, wherever its editor is not there:
// on its own address too, which shows no sheet after a reload. What was kept becomes a new sheet, which opens, or
// it is dropped, and the dead sheet's address gives way to the list.
function Notices({ owner, id }: { owner?: number; id?: string }) {
  const navigate = useNavigate();
  const open = saves.useSaves().list.filter((s) => s.owner === owner && (s.gone ? !s.open : String(s.id) !== id && s.unsaved && (s.clash || s.failed || s.late)));
  return open.map((s) => (
    <p key={s.id} className="notice" role={s.gone ? "alert" : "status"}>
      {s.gone ? (
        <>
          „{s.title}“ wurde auf einem anderen Gerät gelöscht. Deine letzte Änderung ist noch da.
          <button type="button" disabled={s.choice === "busy"} onClick={() => void saves.keepAsNew(s.id).then((sheet) => sheet && sheet !== "failed" && navigate(`/blatt/${sheet.id}`))}>
            Als neues Blatt behalten
          </button>
          <button type="button" disabled={s.choice === "busy"} onClick={() => void saves.discard(s.id).then((gone) => gone && location.pathname === `/blatt/${s.id}` && navigate("/"))}>
            Verwerfen
          </button>
          {s.choice && (
            <span>
              {s.choice === "busy" ? "Lädt …" : s.choiceProblems ? `Das hat nicht geklappt: das Blatt passt nicht zum Format. ${s.choiceProblems.join("; ")}` : "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."}
            </span>
          )}
        </>
      ) : s.stopped ? (
        // First of all: without a login a clash has no sheet to open either.
        `Die letzte Änderung an „${s.title}“ ist noch nicht gespeichert. Melde dich neu an, dann wird sie gespeichert.`
      ) : s.clash ? (
        <>
          „{s.title}“ wurde auf einem anderen Gerät geändert. <Link to={`/blatt/${s.id}`}>Öffne das Blatt</Link>, um zu wählen.
        </>
      ) : s.refused ? (
        `„${s.title}“ ist nicht gespeichert: das Blatt passt nicht zum Format.`
      ) : (
        `Die letzte Änderung an „${s.title}“ ist noch nicht gespeichert. Blattomat versucht es weiter.`
      )}
    </p>
  ));
}

function Layout({ user }: { user: User }) {
  return (
    <>
      <nav>
        <NavLink to="/" className="brand"><Logo /></NavLink>
        <Feedback>Feedback</Feedback>
        <NavLink to="/feedback/fotos">Fotos</NavLink>
        {user.admin && <NavLink to="/admin">Admin</NavLink>}
        <NavLink to="/konto">Konto</NavLink>
      </nav>
      <Outlet />
    </>
  );
}
