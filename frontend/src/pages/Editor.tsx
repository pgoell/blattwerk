import { useEffect, useRef, useState, type ReactNode } from "react";
import { flushSync } from "react-dom";
import { useNavigate, useParams } from "react-router";
import type { User } from "../api";
import Failed from "../components/Failed";
import { drop as dropFault } from "../fault";
import { ask, discard, get, inClash, isGone, keepAsNew, open, overwrite, refused, reset } from "../saves";
import type { Sheet } from "../sheet";
import type { Opened } from "./editor/palette";
import { pdfFault } from "./editor/palette";
import Canvas from "./editor/Canvas";

export default function Editor({ user, wait, first }: { user: User; wait: ReactNode; first: ReturnType<typeof get> }) {
  const { id } = useParams();
  // undefined while the sheet is loading, null when it is not there. `n` counts the loads.
  // `variants` opens the print variants in a sheet loaded anew for them.
  const [file, setFile] = useState<{ sheet: Sheet | null | "failed"; n: number; variants?: Opened }>();
  const show = (sheet: Sheet | null | "failed") => setFile((was) => ({ sheet, n: (was?.n ?? 0) + 1 }));
  // The tries after a load that failed. Each asks anew, with the loading page up meanwhile.
  const [tries, setTries] = useState(0);
  const retry = () => {
    setFile(undefined);
    setTries((n) => n + 1);
  };
  const here = useRef(true);
  // A PDF pressed in a clash, Lösungen where true: it comes once the teacher has chosen, also in the editor a load starts anew.
  const waiting = useRef<boolean | undefined>(undefined);
  useEffect(() => {
    here.current = true;
    return () => void (here.current = false);
  }, []);

  // The other version of a clash: the saver starts over from it. An answer that comes when the teacher has gone on,
  // or has chosen this version meanwhile, changes nothing. Either choice may find the sheet deleted elsewhere, which
  // ends the clash in the choice of a deleted sheet, or the session gone or another account's, which brings the
  // login and keeps the change for its owner. Any other failure, and no answer after 20 s, says so and leaves the
  // choice: the kept change is dropped only once the other version has come. While a choice is under way the banner
  // says so and takes no second press, and it stops saying so with whatever the choice ends in.
  const [choice, setChoice] = useState<"busy" | "failed">();
  const ended = (end: "failed" | void) => void (here.current && setChoice(end || undefined));
  // The two answers to a sheet deleted elsewhere: what shows becomes a new sheet, which opens, or it is dropped.
  const navigate = useNavigate();
  const keep = () => void keepAsNew(Number(id)).then((sheet) => {
    if (!sheet || sheet === "failed") return;
    dropFault(pdfFault);
    navigate(`/blatt/${sheet.id}`);
  });
  // Only from the dead sheet's own address: the teacher may have gone on while the server was asked.
  const drop = () => void discard(Number(id)).then((gone) => gone && location.pathname === `/blatt/${id}` && navigate("/"));
  function load() {
    setChoice("busy");
    ask<Sheet>(`/sheets/${id}`).then(
      (sheet) => {
        ended();
        dropFault(pdfFault);
        const other = here.current && reset(sheet);
        if (other) show(other);
      },
      (e: Error) => ended(refused(Number(id), e)),
    );
  }
  function over() {
    setChoice("busy");
    overwrite(Number(id)).then((end) => {
      // Where this version took the other's place: what shows is what the next PDF prints.
      if (!inClash(Number(id)) && !isGone(Number(id))) dropFault(pdfFault);
      ended(end);
    });
  }
  // The newer sheet of another window is shown where this window has no change of its own (#720).
  // At once: the saver is the new sheet's already, and a key typed into the old editor meanwhile would be lost.
  const renew = (sheet: Sheet, variants?: Opened) => void (here.current && flushSync(() => setFile((was) => ({ sheet, n: (was?.n ?? 0) + 1, variants }))));
  // The sheet's saver says what shows: the answer, or a change that is still unsaved. An answer that comes when the
  // teacher has gone on is not for the saver either, nor is the late answer of a try before this one. A change the
  // browser kept waits through a load that failed, and shows with the try that brings the sheet.
  useEffect(() => {
    let on = true;
    (tries ? get(id!) : first).then((sheet) => on && show(sheet && sheet !== "failed" ? open(sheet) : sheet));
    return () => void (on = false);
  }, [first, tries]);

  if (file === undefined) return wait;
  if (file.sheet === "failed") return <main><Failed retry={retry}><h1>Das Blatt konnte nicht geladen werden</h1></Failed></main>;
  if (!file.sheet) return <main><h1>Blatt nicht gefunden</h1></main>;
  // A sheet loaded anew starts the editor over.
  return <Canvas key={file.n} file={file.sheet} user={user} reload={load} over={over} choice={choice} asNew={keep} discard={drop} renew={renew} opened={file.variants} waiting={waiting} />;
}

// The print variants opened in an editor loaded anew: the dialog's choice as it was, and the press that loaded it.
// `print` prints at once, Lösungen where true; `newer` says that a newer version was loaded for it.
