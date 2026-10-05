import { useState } from "react";
import { api, post, type User } from "../api";

export default function Account({ user, onGone }: { user: User; onGone: () => void }) {
  const [sure, setSure] = useState(false);

  return (
    <main>
      <h1>Konto</h1>
      <div className="card">
        <p>Angemeldet als {user.email}</p>
        <button type="button" onClick={() => post("/logout").then(onGone)}>Abmelden</button>
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
