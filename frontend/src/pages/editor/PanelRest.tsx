// The Lernwörter and the Ansicht of the format panel.
import { Eraser, Layers, SeparatorHorizontal, SeparatorVertical } from "lucide-react";
import { RULINGS, type PageNumbers } from "../../sheet";
import { MONTESSORI, NAMES, storedPlaces, type PlaceName } from "../../places";
import { KEY_RED } from "../../sheet/doc";
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
  const keyColor = typeof hist.doc.keyColor === "string" ? hist.doc.keyColor : undefined;
  const keyAsText = hist.doc.keyAsText === true;
  // A picked colour stays while "Wie der Text" is on, so coming back shows it again.
  const places = storedPlaces(hist.doc.places) ?? {};
  const placesOn = places.on === true;
  const placeColor = (name: PlaceName) => places[name] ?? MONTESSORI[name];
  const answers = (color: string | undefined, asText: boolean) => {
    const next = color && /^#[0-9a-fA-F]{6}$/.test(color) ? color.toLowerCase() : undefined;
    if (keyAsText === asText && keyColor?.toLowerCase() === next) return;
    update((doc) => {
      const kept = { ...doc };
      if (asText) kept.keyAsText = true;
      else delete kept.keyAsText;
      if (next) kept.keyColor = next;
      else delete kept.keyColor;
      return kept;
    }, "keyColor");
  };
  // A picked colour stays while the switch is off, so turning it on shows that colour again.
  const stellen = (on: boolean, name?: PlaceName, color?: string) => {
    const next = { ...places };
    if (on) next.on = true;
    else delete next.on;
    if (name && color && /^#[0-9a-fA-F]{6}$/.test(color)) {
      const hex = color.toLowerCase();
      if (hex === MONTESSORI[name]) delete next[name];
      else next[name] = hex;
    }
    if (!next.on && !NAMES.some((key) => next[key])) {
      if (!placesOn && !NAMES.some((key) => places[key])) return;
      update((doc) => {
        const kept = { ...doc };
        delete kept.places;
        return kept;
      }, "places");
      return;
    }
    if (placesOn === !!next.on && NAMES.every((key) => places[key] === next[key])) return;
    update((doc) => ({ ...doc, places: next }), "places");
  };
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
              <h2>Lösungsfarbe</h2>
              <div className="seg" role="group" aria-label="Lösungsfarbe">
                <button className={keyAsText ? "" : "on"} aria-pressed={!keyAsText} onClick={() => answers(keyColor, false)}>Farbe</button>
                <button className={keyAsText ? "on" : ""} aria-pressed={keyAsText} onClick={() => answers(keyColor, true)}>Wie der Text</button>
              </div>
              {!keyAsText && (
                <label>
                  Farbe
                  <input type="color" aria-label="Farbe der Lösungen" value={(keyColor ?? KEY_RED).toLowerCase()} onChange={(e) => answers(e.target.value, false)} />
                </label>
              )}
              <h2>Stellenwerte</h2>
              <div className="seg" role="group" aria-label="Stellenwerte">
                <button className={placesOn ? "" : "on"} aria-pressed={!placesOn} onClick={() => stellen(false)}>Aus</button>
                <button className={placesOn ? "on" : ""} aria-pressed={placesOn} onClick={() => stellen(true)}>An</button>
              </div>
              {placesOn && (
                <>
                  {(
                    [
                      ["einer", "Einer"],
                      ["zehner", "Zehner"],
                      ["hunderter", "Hunderter"],
                      ["tausender", "Tausender"],
                    ] as const
                  ).map(([name, label]) => (
                    <label key={name}>
                      {label}
                      <input type="color" aria-label={`Farbe der ${label}`} value={placeColor(name)} onChange={(e) => stellen(true, name, e.target.value)} />
                    </label>
                  ))}
                  <p className="hint">Einer, Zehner, Hunderter und Tausender in jedem Mathe-Block. Text und Dezimalzahlen bleiben schwarz.</p>
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
