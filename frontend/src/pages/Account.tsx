import { useState } from "react";
import { api, post, type User } from "../api";

// The theme: Blattform until the teacher picks another; "" is the device's own. index.html sets it before the first paint.
const THEMES = [["leaf", "Blattform"], ["", "System"], ["light", "Hell"], ["dark", "Dunkel"]];

export default function Account({ user, onGone }: { user: User; onGone: () => void }) {
  const [sure, setSure] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") ?? "leaf");

  function show(to: string) {
    localStorage.setItem("theme", to);
    document.documentElement.dataset.theme = to;
    setTheme(to);
  }

  return (
    <main>
      <h1>Konto</h1>
      <div className="card">
        <p>Angemeldet als {user.email}</p>
        <button type="button" onClick={() => post("/logout").then(onGone)}>Abmelden</button>
      </div>
      <div className="card">
        <label>Darstellung</label>
        <p className="hint">Grün als Blattform, so wie dein Gerät eingestellt ist, hell oder dunkel. Das Blatt selbst bleibt immer weiß.</p>
        <div className="seg">
          {THEMES.map(([to, label]) => (
            <button key={to} type="button" className={theme === to ? "on" : ""} aria-pressed={theme === to} onClick={() => show(to)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="card">
        <label>Konto löschen</label>
        <p className="hint">Löscht dein Konto und alles, was du geschickt hast. Das lässt sich nicht rückgängig machen.</p>
        {sure ? (
          <button type="button" className="danger" onClick={() => api("/me", { method: "DELETE" }).then(onGone)}>
            Ja, endgültig löschen
          </button>
        ) : (
          <button type="button" className="plain" onClick={() => setSure(true)}>Konto löschen …</button>
        )}
      </div>
    </main>
  );
}
