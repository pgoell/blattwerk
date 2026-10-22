import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { api } from "../api";
import { K, Paper, bowed, lengthened, read, type Credit, type Doc } from "../sheet";

// What the server's Chromium prints into the PDF: every page of a sheet at its true size, `?loesungen` with the
// answers. No one is logged in there; the server lets Chromium in by the token it sends along.
export default function Print() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const [print, setPrint] = useState<{ doc: Doc; notes: Credit[] }>();

  const variante = params.get("variante");
  useEffect(() => {
    let gone = false;
    api<Doc>(`/render/${id}${variante ? `?variante=${variante}` : ""}`).then(async (raw) => {
      const doc = read(raw);
      const ids = [...new Set(doc.pages.flatMap((p) => p.blocks.flatMap((b) => (b.type === "image" ? [b.props.upload] : []))))];
      let notes: Credit[] = [];
      if (ids.length)
        try {
          notes = await api<Credit[]>(`/picture-notes?ids=${ids.join(",")}`);
        } catch {
          notes = [];
        }
      if (!gone) setPrint({ doc, notes });
    });
    return () => void (gone = true);
  }, [id, variante]);
  // Chromium waits for this class: fonts and pictures load only once the pages that use them are laid out.
  // The credits are in the same state as the pages, so they are drawn before the class.
  useEffect(() => {
    if (!print) return;
    document.body.getBoundingClientRect();
    const pictures = [...document.images].map((img) => img.decode().catch(() => {}));
    // The bows of a text are measured once its font is in, so they come last.
    Promise.all([document.fonts.ready, ...pictures]).then(() => {
      // A Lineatur on lines stored too short for its text grows first, and is drawn so before the print.
      const next = lengthened(print.doc);
      if (next !== print.doc) return setPrint({ ...print, doc: next });
      return bowed().then(() => document.body.classList.add("ready"));
    });
  }, [print]);

  return (
    <div className="print">
      {print && print.doc.pages.map((_, n) => (
        <Paper key={n} doc={print.doc} k={K} page={n} solved={params.has("loesungen")} letter={params.get("buchstabe") ?? undefined} notes={print.notes} />
      ))}
    </div>
  );
}
