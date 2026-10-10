import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, Route, Routes, useMatch } from "react-router";
import { api, type User } from "./api";
import Blank from "./components/Blank";
import Feedback from "./components/Feedback";
import Logo from "./components/Logo";
import About from "./pages/About";
import Account from "./pages/Account";
import Admin from "./pages/Admin";
import Login from "./pages/Login";
import Photos from "./pages/Photos";
import Print from "./pages/Print";
import SetPassword from "./pages/SetPassword";
import SheetList from "./pages/SheetList";
import { last, type Sheet } from "./sheet";

// The editor brings the canvas libraries; the login page loads without them.
const Editor = lazy(() => import("./pages/Editor"));

export default function App() {
  // undefined while /me is loading, null when logged out.
  const [user, setUser] = useState<User | null>();

  useEffect(() => {
    api<User>("/me").then(setUser, () => setUser(null));
  }, []);

  // A login or a logout empties the block clipboard: what one account copied is not the next one's.
  const [entered, setEntered] = useState(0);
  const enter = (to: User | null) => {
    localStorage.removeItem("clip");
    setUser(to);
    setEntered((n) => n + 1);
  };

  // A sheet shows its loading page at once, and one clock runs while the account, the editor's script and the
  // sheet load. A login on a sheet's address starts the clock anew: the time at the login page is no loading.
  const { id } = useMatch("/blatt/:id")?.params ?? {};
  const since = useMemo(() => performance.now(), [id, entered]);
  const wait = <Blank since={since} />;
  // The sheet is asked for as soon as the account is known, side by side with the editor's script and not after
  // it. Each visit asks anew. A sheet that is not there is null: nobody may hear of it before the script has come.
  // Each sheet has an editor of its own: on to another sheet, the one left saves and goes, the loading page stands
  // at once, and a late answer for the sheet left finds nobody to show it.
  // The sheet left saves as it goes, and the next one is asked for when that save is done: back on the sheet left,
  // the answer holds what was saved. An effect, not the render: the editor left has started its save by then.
  const [first, setFirst] = useState<{ id: string; sheet: Promise<Sheet | null> }>();
  useEffect(() => {
    setFirst(user && id ? { id, sheet: last.save.then(() => api<Sheet>(`/sheets/${id}`)).catch(() => null) } : undefined);
  }, [user, id]);

  if (user === undefined) return id ? wait : null;
  return (
    <>
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
            <Route path="/konto" element={<Account user={user} onGone={() => enter(null)} />} />
            {user.admin && <Route path="/admin" element={<Admin />} />}
            <Route path="*" element={<main><h1>Seite nicht gefunden</h1></main>} />
          </Route>
        ) : (
          // Logged out, every path shows the login; the page asked for opens after it.
          <Route path="*" element={<Login onDone={enter} />} />
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
