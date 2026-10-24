// The PDF and the print variants.
import { useEffect, useRef, useState } from "react";
import { NEWER } from "../../components/Variants";
import { attempt, drop as dropFault, note } from "../../fault";
import { ask, flush, inClash, isGone, newer, signed } from "../../saves";
import { pdfFault } from "./palette";
import { useGuides } from "./useGuides";

export function usePrint(session: ReturnType<typeof useGuides>) {
  const file = session.file;
  const opened = session.opened;
  const waiting = session.waiting;
  const newerSheet = session.newerSheet;
  const setPdfWaits = session.setPdfWaits;
  const dialogState = session.dialogState;
  const bar = session.bar;
// The PDF is made of what the server holds, so a change still waiting is saved first: after a save under way,
  // which may hold an older document. A save that fails or never answers holds the PDF up for 20 s at most.
  // The session is asked for first: where it is gone the login shows, and nothing goes to the PDF's address. The
  // PDF is fetched, so a failure leaves the sheet where it is, and goes to the browser as a download under the name
  // the server gives it. With no limit of time: a long sheet takes long to print.
  // The PDF waits for the clash's choice, and the bar says so.
  const holdPdf = (key: boolean) => void (waiting.current = key, setPdfWaits(true));
  async function pdf(key: boolean) {
    // A sheet deleted elsewhere: another try ends the same, so the line names the choice and has no button.
    const deleted = "Das PDF konnte nicht erstellt werden. Dieses Blatt wurde auf einem anderen Gerät gelöscht. Wähle „Als neues Blatt behalten“, dann gibt es wieder ein PDF.";
    const what = pdfFault;
    await attempt(what, async () => {
      // In a clash the server holds the other device's sheet: the PDF waits until the teacher has chosen. Also where
      // the save it waits for is the one turned down.
      if (inClash(file.id)) return holdPdf(key);
      // A newer version saved in another window is what prints: the editor shows it first (#720).
      dropFault(NEWER);
      await newerSheet();
      // Deleted elsewhere: the PDF has no sheet to print, and the line names the choice.
      if (isGone(file.id)) throw new Error("404");
      const current = await flush(file.id);
      if (inClash(file.id)) return holdPdf(key);
      await ask("/me");
      const res = await signed(
        fetch(`/api/sheets/${file.id}/pdf${key ? "?solved=true" : ""}`).then((res) => {
          if (!res.ok) throw new Error(String(res.status));
          return res;
        }),
      );
      const link = document.createElement("a");
      link.href = URL.createObjectURL(await res.blob());
      link.download = decodeURIComponent(/filename\*=UTF-8''(.+)/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "Blatt.pdf");
      link.click();
      // After the browser has taken the file.
      setTimeout(() => URL.revokeObjectURL(link.href), 60000);
      if (!current) note(what, "Das PDF zeigt den zuletzt gespeicherten Stand, nicht deine letzte Änderung: sie ist noch nicht gespeichert.");
    }, (s) => (s === "404" && isGone(file.id) ? deleted : undefined));
  }

  // The print variants: the dialog's choice lives here, so it stays while the editor is open.
  const [variants, setVariants] = useState(!!opened);
  // What opened the dialog: a press that came with a newer sheet prints once, and the line stays while the dialog is open.
  const [fromPress, setFromPress] = useState(opened);
  const [count, setCount] = useState(opened?.count ?? 2);
  const [letters, setLetters] = useState(opened?.letters ?? true);
  // The button that opened the dialog gets the focus back when it shuts.
  const variantsDoor = useRef<HTMLElement | null>(null);
  dialogState.current = variants ? { count, letters, newer: true } : undefined;
  // A press that re-mounted the editor has the dialog open: Schließen gives the focus back to the bar's button.
  useEffect(() => {
    if (!opened) return;
    variantsDoor.current = bar.current?.querySelector<HTMLElement>('[aria-label="Varianten drucken"]') ?? bar.current?.querySelector<HTMLElement>(".more") ?? null;
  }, []);
  // A newer version saved in another window: the dialog opens on it, in the editor that shows it (#720).
  const openVariants = async (door: HTMLElement) => {
    dropFault(NEWER);
    if (await newerSheet({ count, letters, newer: true })) return;
    variantsDoor.current = door;
    setVariants(true);
  };

    return Object.assign(session, { holdPdf, pdf, variants, setVariants, fromPress, setFromPress, count, setCount, letters, setLetters, variantsDoor, openVariants });
}
