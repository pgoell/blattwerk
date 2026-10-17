import { useEffect, useState } from "react";
import { useLocation } from "react-router";
import { api } from "../api";

// The authorization request's own parameters, as the server takes them back.
const FIELDS = ["client_id", "redirect_uri", "response_type", "code_challenge", "code_challenge_method", "state", "resource"];

type Client = { client_name: string; redirect_host: string; loopback: boolean };

// A program asks to connect to the teacher's account. The teacher allows or refuses it here, and the server sends the
// browser back to the program with the answer.
export default function Consent() {
  const { search } = useLocation();
  const [client, setClient] = useState<Client>();
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Client & { redirect?: string }>(`/oauth/authorize${search}`).then(
      (to) => {
        if (to.redirect) return location.assign(to.redirect);
        setClient(to);
      },
      (e: Error & { detail?: string }) => setProblem(e.detail ?? "Die Verbindung konnte nicht geprüft werden."),
    );
  }, [search]);

  function answer(approve: boolean) {
    const query = new URLSearchParams(search);
    const body = Object.fromEntries(FIELDS.filter((key) => query.has(key)).map((key) => [key, query.get(key)]));
    setBusy(true);
    api<{ redirect: string }>("/oauth/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, approve }),
    }).then(
      (to) => location.assign(to.redirect),
      () => {
        setBusy(false);
        setProblem("Die Antwort konnte nicht gesendet werden. Versuche es noch einmal.");
      },
    );
  }

  return (
    <main>
      {client ? (
        <>
          <h1>„{client.client_name}“ möchte sich mit deinem Blattomat-Konto verbinden</h1>
          <div className="card">
            <label>Wer fragt</label>
            <p>{client.client_name}</p>
            <p className="hint">Nach dem Erlauben geht es weiter zu: {client.redirect_host}</p>
            {client.loopback && (
              <p className="notice">Dieses Programm läuft auf deinem Computer. Erlaube es nur, wenn du es gerade selbst gestartet hast.</p>
            )}
          </div>
          <div className="card">
            <label>Was es darf</label>
            <p>
              Es darf deine Blätter ansehen, anlegen, ändern, kopieren und löschen, Bilder hochladen und deine Vorlagen sehen. Dein
              Passwort erfährt es nicht.
            </p>
          </div>
          <div className="card">
            <label>So beendest du es</label>
            <p>Unter „Konto“ bei „Verbundene Programme“ trennst du die Verbindung mit einem Klick.</p>
          </div>
          <div className="row">
            <button type="button" className="primary" disabled={busy} onClick={() => answer(true)}>
              Erlauben
            </button>
            <button type="button" className="plain" disabled={busy} onClick={() => answer(false)}>
              Ablehnen
            </button>
          </div>
        </>
      ) : (
        <h1>{problem}</h1>
      )}
      {problem && client && <p role="alert" className="notice">{problem}</p>}
    </main>
  );
}
