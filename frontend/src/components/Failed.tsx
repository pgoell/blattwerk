import { useLayoutEffect, type ReactNode } from "react";

// What stands where a load failed: `children` says what, read out at once. It is there only while the load has
// failed, so it tries again by itself when the network is back, and never while a try is out. It listens from the
// moment it is drawn: the page that showed before has stopped listening by then, and an online event between the
// two was lost (#959).
export default function Failed({ children, retry }: { children: ReactNode; retry: () => void }) {
  useLayoutEffect(() => {
    addEventListener("online", retry);
    return () => removeEventListener("online", retry);
  }, []);
  return (
    <div role="alert">
      {children}
      <p className="lead">Prüfe deine Verbindung. Blattomat versucht es wieder, sobald sie da ist.</p>
      <button type="button" className="primary" autoFocus onClick={retry}>
        Erneut versuchen
      </button>
    </div>
  );
}
