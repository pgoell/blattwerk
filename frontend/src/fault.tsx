import { useEffect, useSyncExternalStore } from "react";
import { useLocation } from "react-router";

// One rule for every action that needs the server: where it cannot be done, the app stays as it is and a line
// above the page says so in German, with a button that tries the same again. What the teacher had typed goes
// along with that try. `what` names the action, as a whole sentence: one line per action, and a new try takes the
// old line away.
type Fault = { what: string; text: string; retry?: () => void };
let faults: Fault[] = [];
const heard = new Set<() => void>();
const listen = (hear: () => void) => {
  heard.add(hear);
  return () => void heard.delete(hear);
};
function show(to: Fault[]) {
  faults = to;
  heard.forEach((hear) => hear());
}
const drop = (what: string) => faults.some((f) => f.what === what) && show(faults.filter((f) => f.what !== what));

// What went wrong, as the HTTP status where the server answered, "offline" where no answer came (the browser's
// fetch refuses with a TypeError, a request given up after 20 s with an AbortError), and "" for anything else.
export function status(e: unknown) {
  const { name, message = "" } = (e ?? {}) as Error;
  return /^\d{3}$/.test(message) ? message : e instanceof TypeError || name === "AbortError" ? "offline" : "";
}
// The second sentence of a line: why, and what to do.
export const why = (s: string) =>
  s === "offline" ? "Prüfe deine Verbindung und versuche es noch einmal." : s.startsWith("5") ? "Blattomat hat gerade eine Störung. Versuche es gleich noch einmal." : "Versuche es noch einmal.";

// Runs an action that asks the server. Gives what it gave, or undefined where it failed, and says so then. Not for
// a session that ran out ("401"), nor for an answer about the session before ("stale"): the login shows or has
// shown. `own` gives the whole line for a refusal that is the action's own, a file the server does not take, say:
// that line has no button, for the same try would end the same. It gets the refusal too, and null from it says
// nothing at all. Once the teacher has gone on to another page the line still says so, with no button: the try
// would act where the action no longer is.
export async function attempt<T>(what: string, run: () => Promise<T>, own?: (status: string, e: unknown) => string | null | undefined): Promise<T | undefined> {
  drop(what);
  const page = location.pathname;
  try {
    return await run();
  } catch (e) {
    const s = status(e);
    if (s === "401" || (e as Error)?.message === "stale") return;
    const text = location.pathname === page ? own?.(s, e) : `${what} ${why(s)}`;
    if (text === null) return;
    const fault = text ? { what, text } : { what, text: `${what} ${why(s)}`, retry: () => void attempt(what, run, own) };
    show([...faults.filter((f) => f.what !== what), fault]);
  }
}

// Another account's login takes every line away: its button would act for the account before.
export const clear = () => show([]);

// The lines, above every page. They go with a try, a press on `Schließen`, and with the page they were said on.
export function Faults() {
  const list = useSyncExternalStore(listen, () => faults);
  const { pathname } = useLocation();
  useEffect(() => () => show([]), [pathname]);
  return list.map((f) => (
    <p key={f.what} className="notice fault" role="alert">
      {f.text}
      {f.retry && <button type="button" onClick={f.retry}>Erneut versuchen</button>}
      <button type="button" aria-label="Meldung schließen" onClick={() => drop(f.what)}>Schließen</button>
    </p>
  ));
}
