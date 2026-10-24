// The Lernwörter and the Ansicht of the format panel.
import { Eraser, Layers, SeparatorHorizontal, SeparatorVertical } from "lucide-react";
import { RULINGS, type PageNumbers } from "../../sheet";
import { pasted } from "../../words";
import Format from "../Format";
import { INSERTS } from "../../insert";
import { GRIDS, NONE } from "./palette";
import { useTools } from "./useTools";

export default function PanelRest({ s: session }: { s: ReturnType<typeof useTools> }) {
  const H = session.H;
  const W = session.W;
  const addBlatt = session.addBlatt;
  const addInsert = session.addInsert;
  const at = session.at;
  const caretAt = session.caretAt;
  const crowded = session.crowded;
  const field = session.field;
  const folio = session.folio;
  const from = session.from;
  const grid = session.grid;
  const guides = session.guides;
  const hist = session.hist;
  const lay = session.lay;
  const learnt = session.learnt;
  const listField = session.listField;
  const listWords = session.listWords;
  const mine = session.mine;
  const numbering = session.numbering;
  const onPaste = session.onPaste;
  const openVariants = session.openVariants;
  const own = session.own;
  const page = session.page;
  const pages = session.pages;
  const pressed = session.pressed;
  const rule = session.rule;
  const rules = session.rules;
  const setOwn = session.setOwn;
  const tab = session.tab;
  const title = session.title;
  const turn = session.turn;
  const update = session.update;
  const words = session.words;
  return (
    <>
          {tab === "Lernwörter" && (
            <>
              <h2>Lernwörter</h2>
              <textarea
                aria-label="Lernwörter"
                className="wordlist"
                rows={10}
                // The browser's check knows no German on most machines and marks every word (#580).
                spellCheck={false}
                placeholder="Ein Wort pro Zeile"
                ref={listField}
                value={Array.isArray(hist.doc.words) ? hist.doc.words.filter((w) => typeof w === "string").join("\n") : ""}
                onChange={(e) => listWords(e.target.value)}
                // A paste brings its words one to a line, in place of what is picked in the field.
                onPaste={(e) => {
                  e.preventDefault();
                  const field = e.currentTarget;
                  const [from, to] = [field.selectionStart, field.selectionEnd];
                  // A paste that holds no word changes nothing.
                  if (!pasted(e.clipboardData.getData("text/plain")).length) return;
                  const [before, after] = [field.value.slice(0, from), field.value.slice(to)];
                  // The pasted words keep to lines of their own: a word before or behind them is not joined to one.
                  const words = (/[^\n]$/.test(before) ? "\n" : "") + pasted(e.clipboardData.getData("text/plain")).join("\n") + (/^[^\n]/.test(after) ? "\n" : "");
                  caretAt.current = from + words.length;
                  listWords(before + words + after);
                }}
              />
              <p className="hint">Ein Wort pro Zeile. Eine Lineatur oder ein Text nimmt die Wörter unter Format, „Text“.</p>
              {/* Said here too: the list is where a word too many comes from, and the Lernwörter-Blatt picks no block. */}
              {crowded > 0 && (
                <p className="hint" role="status">
                  {crowded === 1 ? "In einer Lineatur passt 1 Wort nicht in die Zeilen." : `In einer Lineatur passen ${crowded} Wörter nicht in die Zeilen.`}
                </p>
              )}
              <button
                disabled={!learnt.length}
                onClick={addBlatt}
                title="Ein Blatt mit Überschrift, Namenszeile und drei Lineaturen: abschreiben, nachspuren, ganze Zeile nachspuren. Viele Wörter gehen auf weiteren Seiten weiter."
              >
                Lernwörter-Blatt
              </button>
              <p className="hint">Ein Blatt mit Überschrift, Namenszeile und drei Lineaturen: abschreiben, nachspuren, ganze Zeile nachspuren. Viele Wörter gehen auf weiteren Seiten weiter.</p>
              {/* A Lineatur as wide as the page between the margins, a row for each word, at most as many as a page holds. */}
              <button
                disabled={!learnt.length}
                title="Eine Lineatur zum Falten: links die Wörter, rechts leere Spalten zum Üben aus dem Gedächtnis."
                onClick={() => addInsert(INSERTS.wordList(learnt.length, [W, H], RULINGS.l3.row))}
              >
                Knickblatt
              </button>
              <p className="hint">Eine Lineatur zum Falten: links die Wörter, rechts leere Spalten zum Üben aus dem Gedächtnis.</p>
            </>
          )}
          {tab === "Ansicht" && (
            <>
              <h2>Format, Raster und Hilfslinien für</h2>
              <div className="seg">
                <button className={own ? "" : "on"} aria-pressed={!own} onClick={() => setOwn(false)}>Alle Seiten</button>
                <button className={own ? "on" : ""} aria-pressed={own} onClick={() => setOwn(true)}>Nur diese Seite</button>
              </div>
              {/* A page's own format or grid stands in for the sheet's; "Wie Blatt" gives the page the sheet's again. */}
              <h2>Format</h2>
              <div className="seg">
                {(own ? [undefined, false, true] : [false, true]).map((c) => {
                  const on = own ? pages[page].landscape === c : !!hist.doc.landscape === c;
                  return (
                    <button key={String(c)} className={on ? "on" : ""} aria-pressed={on} onClick={() => lay(c, own ? page : undefined)}>
                      {c === undefined ? "Wie Blatt" : c ? "Quer" : "Hoch"}
                    </button>
                  );
                })}
              </div>
              <h2>Raster</h2>
              <div className="seg">
                {(own ? [undefined, ...GRIDS] : GRIDS).map((c) => {
                  const on = (own ? pages[page].grid : grid) === c;
                  return (
                    <button
                      key={c ?? "sheet"}
                      className={on ? "on" : ""}
                      aria-pressed={on}
                      onClick={() => (own ? turn((p) => ({ ...p, grid: c })) : update((doc) => ({ ...doc, grid: c! })))}
                    >
                      {c === undefined ? "Wie Blatt" : c ? `${c} mm` : "Aus"}
                    </button>
                  );
                })}
              </div>
              <h2>Hilfslinien</h2>
              <div className="acts">
                <button onClick={() => rule("x")}>
                  <SeparatorVertical size={14} aria-hidden />
                  Senkrecht
                </button>
                <button onClick={() => rule("y")}>
                  <SeparatorHorizontal size={14} aria-hidden />
                  Waagerecht
                </button>
              </div>
              <button
                className="wide"
                disabled={!(own ? mine : guides).x.length && !(own ? mine : guides).y.length}
                onClick={() => rules(own ? page : undefined, () => NONE)}
              >
                <Eraser size={14} aria-hidden />
                Alle entfernen
              </button>
              <p className="hint">Eine einzelne Hilfslinie entfernen: an ihrer Zahl vom Blatt ziehen oder mit der rechten Maustaste auf die Zahl klicken.</p>
              <h2>Seitenzahlen</h2>
              <div className="seg" role="group" aria-label="Seitenzahlen">
                <button className={folio.on ? "" : "on"} aria-pressed={!folio.on} onClick={() => numbering({}, false)}>Aus</button>
                <button className={folio.on ? "on" : ""} aria-pressed={folio.on} onClick={() => numbering({})}>An</button>
              </div>
              {folio.on && (
                <>
                  <h2>Ort</h2>
                  <div className="seg">
                    {[
                      ["bottom", "Unten Mitte"],
                      ["right", "Unten rechts"],
                      ["outer", "Unten außen"],
                      ["top", "Oben rechts"],
                    ].map(([at, label]) => (
                      <button key={at} className={folio.at === at ? "on" : ""} aria-pressed={folio.at === at} onClick={() => numbering({ at: at as PageNumbers["at"] })}>
                        {label}
                      </button>
                    ))}
                  </div>
                  <h2>Form</h2>
                  <div className="seg">
                    {[
                      ["n", "2"],
                      ["seite", "Seite 2"],
                      ["of", "2 / 5"],
                      ["seiteVon", "Seite 2 von 5"],
                    ].map(([form, label]) => (
                      <button key={form} className={folio.form === form ? "on" : ""} aria-pressed={folio.form === form} onClick={() => numbering({ form: form as PageNumbers["form"] })}>
                        {label}
                      </button>
                    ))}
                  </div>
                  <label className="tick">
                    <input type="checkbox" checked={folio.notFirst} onChange={(e) => numbering({ notFirst: e.target.checked })} /> Nicht auf der ersten Seite
                  </label>
                  <h2>Farbe</h2>
                  <div className="seg">
                    <button className={folio.black ? "" : "on"} aria-pressed={!folio.black} onClick={() => numbering({ black: false })}>Grau</button>
                    <button className={folio.black ? "on" : ""} aria-pressed={folio.black} onClick={() => numbering({ black: true })}>Schwarz</button>
                  </div>
                </>
              )}
              {/* Here too, not only in the bar: an iPad's bar has no room for it and folds it under "Mehr". */}
              <h2>Drucken</h2>
              <button className="wide" onClick={(e) => openVariants(e.currentTarget)}>
                <Layers size={14} aria-hidden />
                Varianten drucken
              </button>
            </>
          )}
    </>
  );
}
