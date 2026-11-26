// The format panel's settings for a word search block: its words, its grid, its directions and its letters.
import { draw } from "../bank";
import type { Doc, SuchselBlock, SuchselProps, Ways } from "../sheet";
import { fed, laid, sane, type Loosen } from "../suchsel";
import { WordList, type Listing } from "./format/wordlist";
import { Switch } from "../components/Switch";

const WAYS: [Ways, string][] = [
  ["across", "Nur waagerecht"],
  ["down", "Waagerecht und senkrecht"],
  ["diag", "Auch diagonal"],
  ["back", "Auch rückwärts"],
];
const LOOSEN: Record<Loosen, string> = { size: "mehr Spalten oder Zeilen", ways: "mehr Richtungen", words: "weniger Wörtern" };

export default function Suchsel({ block, words, doc, listing, apply }: { block: SuchselBlock; words: string[]; doc: Doc; listing: Listing; apply: (props: Partial<SuchselProps>, key?: string) => void }) {
  const linked = block.props.list === true;
  const p = sane(fed(block.props, words));
  const made = laid(p);

  return (
    <>
      <h2>Suchsel</h2>
      {/* The grid hides the sheet's Lernwörter and follows them, or words of its own. Cut loose, it keeps the words
          it showed. */}
      <Switch label="Lernwörter des Blatts" on={linked} onChange={() => apply(linked ? { list: undefined, words: [...words] } : { list: true })} />
      {linked ? (
        <WordList doc={doc} listing={listing} />
      ) : (
        <>
          <textarea
            className="wordlist"
            aria-label="Wörter des Suchsels"
            rows={6}
            spellCheck={false}
            value={p.words.join("\n")}
            onChange={(e) => apply({ words: e.target.value === "" ? [] : e.target.value.split("\n") }, "words")}
          />
          <p className="hint">Ein Wort pro Zeile.</p>
        </>
      )}
      <div className="seg">
        <button aria-label="Eine Spalte weniger" disabled={p.cols === 6} onClick={() => apply({ cols: p.cols - 1 })}>
          −
        </button>
        <output>{p.cols} Spalten</output>
        <button aria-label="Eine Spalte mehr" disabled={p.cols === 20} onClick={() => apply({ cols: p.cols + 1 })}>
          ＋
        </button>
      </div>
      <div className="seg">
        <button aria-label="Eine Zeile weniger" disabled={p.rows === 6} onClick={() => apply({ rows: p.rows - 1 })}>
          −
        </button>
        <output>{p.rows} Zeilen</output>
        <button aria-label="Eine Zeile mehr" disabled={p.rows === 20} onClick={() => apply({ rows: p.rows + 1 })}>
          ＋
        </button>
      </div>
      <select aria-label="Richtungen" value={p.ways} onChange={(e) => apply({ ways: e.target.value as Ways })}>
        {WAYS.map(([ways, label]) => (
          <option key={ways} value={ways}>
            {label}
          </option>
        ))}
      </select>
      <Switch label="Nur Großbuchstaben" on={p.caps} onChange={() => apply({ caps: !p.caps })} />
      <Switch label="Umlaute und ß behalten" on={p.umlauts} onChange={() => apply({ umlauts: !p.umlauts })} />
      <div className="seg">
        <button className={p.show === "words" ? "on" : ""} aria-pressed={p.show === "words"} onClick={() => apply({ show: "words" })}>
          Wörterliste
        </button>
        <button className={p.show === "count" ? "on" : ""} aria-pressed={p.show === "count"} onClick={() => apply({ show: "count" })}>
          Nur Anzahl
        </button>
      </div>
      {made.missed.length > 0 && (
        <p className="hint" role="status">
          {`Passt nicht ins Gitter: ${made.missed.join(", ")}.`}
          {/* With nothing to loosen the grid is as large and as free as it gets. */}
          {made.loosen.length > 0 ? ` Mehr Platz gibt es mit: ${made.loosen.map((l) => LOOSEN[l]).join(", ")}.` : " Dafür ist auch das größte Gitter zu klein."}
        </p>
      )}
      {made.short.length > 0 && <p className="hint" role="status">{`Zu kurz (unter 3 Buchstaben): ${made.short.join(", ")}.`}</p>}
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(laid({ ...p, seed }).grid) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
