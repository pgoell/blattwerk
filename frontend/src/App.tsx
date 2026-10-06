import { lazy, Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, Route, Routes } from "react-router";
import { api, type User } from "./api";
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

// The editor brings the canvas libraries; the login page loads without them.
const Editor = lazy(() => import("./pages/Editor"));

export default function App() {
  // undefined while /me is loading, null when logged out.
  const [user, setUser] = useState<User | null>();

  useEffect(() => {
    api<User>("/me").then(setUser, () => setUser(null));
  }, []);

  if (user === undefined) return null;
  return (
    <>
      <Routes>
        <Route path="/einladung/:token" element={<SetPassword invite onDone={setUser} />} />
        <Route path="/passwort/:token" element={<SetPassword onDone={setUser} />} />
        <Route path="/ueber" element={<About />} />
        <Route path="/druck/:id" element={<Print />} />
        {user ? (
          <Route element={<Layout user={user} />}>
            <Route path="/" element={<SheetList />} />
            <Route path="/blatt/:id" element={<Suspense><Editor /></Suspense>} />
            <Route path="/feedback/fotos" element={<Photos />} />
            <Route path="/konto" element={<Account user={user} onGone={() => setUser(null)} />} />
            {user.admin && <Route path="/admin" element={<Admin />} />}
            <Route path="*" element={<main><h1>Seite nicht gefunden</h1></main>} />
          </Route>
        ) : (
          // Logged out, every path shows the login; the page asked for opens after it.
          <Route path="*" element={<Login onDone={setUser} />} />
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
