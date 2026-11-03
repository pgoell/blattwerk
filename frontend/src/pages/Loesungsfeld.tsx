// The format panel for a Lösungsfeld: the answer, the blank, and the falsche Lösungen.
import { useState } from "react";
import { api, signed } from "../api";
import { sane, type LoesungsfeldProps, type Wrong } from "../loesungsfeld";
import type { Doc, LoesungsfeldBlock } from "../sheet";
import { SYMBOLS } from "../symbols";
import { Symbols } from "./format/symbols";

type Apply = (props: Partial<LoesungsfeldProps>, key?: string) => void;

const BLANKS: [LoesungsfeldProps["blank"], string][] = [
  ["line", "Unterstrich"],
  ["box", "Rahmen"],
  ["none", "Nichts"],
];

const textOf = (wrongs: unknown) =>
  (Array.isArray(wrongs) ? wrongs : [])
    .flatMap((w) => (w && typeof w === "object" && w.kind === "text" && typeof w.text === "string" ? [w.text] : []))
    .join("\n");

const imagesOf = (wrongs: Wrong[]) => wrongs.filter((w): w is Extract<Wrong, { kind: "image" }> => w.kind === "image");

export default function Loesungsfeld({
  block,
  doc,
  apply,
  markEven,
}: {
  block: LoesungsfeldBlock;
  doc: Doc;
  apply: Apply;
  markEven: (on: boolean) => void;
}) {
  const p = sane(block.props);
  const [mode, setMode] = useState<"right" | "wrong">("right");
  const [fault, setFault] = useState("");
  const page = doc.pages.find((pg) => pg.blocks.some((b) => b.id === block.id));
  const fields = (page?.blocks ?? []).filter((b) => b.type === "loesungsfeld");
  const allEven = fields.length > 0 && fields.every((b) => b.type === "loesungsfeld" && sane(b.props).even);
  const name = new Map(SYMBOLS.map(([code, de]) => [code, de]));
  const images = imagesOf(p.wrongs ?? []);
  const writeWrongs = (value: string) => {
    const texts = value.split("\n").map((text): Wrong => ({ kind: "text", text }));
    apply({ wrongs: [...texts, ...images] }, "wrongs");
  };
  const take = async (file?: File) => {
    if (!file) return;
    setFault("");
    const body = new FormData();
    body.append("file", file);
    try {
      const { id } = await signed(api<{ id: number }>("/uploads", { method: "POST", body }));
      const img = new Image();
      img.src = `/api/uploads/${id}`;
      await img.decode().catch(() => undefined);
      const ratio = img.naturalWidth > 0 && img.naturalHeight > 0 ? img.naturalWidth / img.naturalHeight : 1;
      apply({ upload: id, ratio, kind: "image" });
    } catch {
      setFault("Das Bild ließ sich nicht hochladen.");
    }
  };
  const toggleWrong = (code: string) => {
    const has = images.some((w) => w.code === code);
    const next = has ? images.filter((w) => w.code !== code) : [...images, { kind: "image" as const, code }];
    const texts = (p.wrongs ?? []).filter((w) => w.kind === "text");
    apply({ wrongs: [...texts, ...next] }, "wrongs");
  };

  return (
    <>
      <h2>Lösungsfeld</h2>
      <p className="hint">Auf dem Blatt bleibt es leer. Der Text oder das Bild steht nur in den Lösungen.</p>
      <label>
        Art
        <select aria-label="Art" value={p.kind} onChange={(e) => apply({ kind: e.target.value as LoesungsfeldProps["kind"] })}>
          <option value="text">Lösungstext</option>
          <option value="image">Lösungsbild</option>
        </select>
      </label>
      {p.kind === "text" && (
        <label>
          Lösungstext
          <input aria-label="Lösungstext" value={p.text} onChange={(e) => apply({ text: e.target.value }, "text")} />
        </label>
      )}
      {p.kind === "image" && (
        <label>
          Eigenes Bild
          <input aria-label="Eigenes Bild" type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml" onChange={(e) => void take(e.target.files?.[0])} />
        </label>
      )}
      {fault && <p className="hint" role="status">{fault}</p>}
      {p.kind === "image" && p.upload !== undefined && (
        <button type="button" onClick={() => apply({ upload: undefined, ratio: undefined })}>Eigenes Bild entfernen</button>
      )}
      {p.kind === "image" && p.upload === undefined && (
        <>
          <div className="seg" role="group" aria-label="Bild setzen">
            <button type="button" className={mode === "right" ? "on" : ""} aria-pressed={mode === "right"} onClick={() => setMode("right")}>Lösung</button>
            <button type="button" className={mode === "wrong" ? "on" : ""} aria-pressed={mode === "wrong"} onClick={() => setMode("wrong")}>Falsche Lösung</button>
          </div>
          <Symbols value={mode === "right" ? p.code ?? "" : ""} onPick={mode === "right" ? (code) => apply({ code }) : toggleWrong} />
          {images.length > 0 && (
            <p className="hint">Falsche Bilder: {images.map((w) => (w.code ? name.get(w.code) ?? w.code : "Bild")).join(", ")}.</p>
          )}
        </>
      )}
      <label>
        Leerfeld
        <select aria-label="Leerfeld" value={p.blank} onChange={(e) => apply({ blank: e.target.value as LoesungsfeldProps["blank"] })}>
          {BLANKS.map(([blank, label]) => (
            <option key={blank} value={blank}>{label}</option>
          ))}
        </select>
      </label>
      <label>
        Schriftgröße
        <input aria-label="Schriftgröße" type="number" min={8} max={48} value={p.size} onChange={(e) => apply({ size: Number(e.target.value) }, "size")} />
      </label>
      <label className="tick">
        <input type="checkbox" checked={allEven} onChange={() => markEven(!allEven)} /> Alle Lösungsfelder gleich breit
      </label>
      {p.kind === "text" && (
        <label>
          Falsche Lösungen
          <textarea aria-label="Falsche Lösungen" rows={3} value={textOf(block.props.wrongs)} onChange={(e) => writeWrongs(e.target.value)} />
        </label>
      )}
    </>
  );
}
