import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { api } from "../api";
import { K, Paper, bowed, lengthened, read, type Doc } from "../sheet";

// What the server's Chromium prints into the PDF: every page of a sheet at its true size, `?loesungen` with the
// answers. No one is logged in there; the server lets Chromium in by the token it sends along.
export default function Print() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const [doc, setDoc] = useState<Doc>();

  const variante = params.get("variante");
  useEffect(() => {
    api<Doc>(`/render/${id}${variante ? `?variante=${variante}` : ""}`).then((doc) => setDoc(read(doc)));
  }, [id, variante]);
  // Chromium waits for this class: fonts and pictures load only once the pages that use them are laid out.
  useEffect(() => {
    if (!doc) return;
    document.body.getBoundingClientRect();
    const pictures = [...document.images].map((img) => img.decode().catch(() => {}));
    // The bows of a text are measured once its font is in, so they come last.
    Promise.all([document.fonts.ready, ...pictures]).then(() => {
      // A Lineatur on lines stored too short for its text grows first, and is drawn so before the print.
      const next = lengthened(doc);
      if (next !== doc) return setDoc(next);
      return bowed().then(() => document.body.classList.add("ready"));
    });
  }, [doc]);

  return (
    <div className="print">
      {doc?.pages.map((_, n) => <Paper key={n} doc={doc} k={K} page={n} solved={params.has("loesungen")} letter={params.get("buchstabe") ?? undefined} />)}
    </div>
  );
}
