// The right panel's tab "Blatt": what holds for the whole sheet.
import { Plus, Wallpaper } from "lucide-react";
import { FADES, GROUND_HINT } from "../../ground";
import { RULINGS, type PageNumbers } from "../../sheet";
import { MONTESSORI, NAMES, storedPlaces, type PlaceName } from "../../places";
import { KEY_RED } from "../../sheet/doc";
import Format from "../Format";
import { useTools } from "./useTools";
import { Switch } from "../../components/Switch";

export default function PanelRest({ s: session }: { s: ReturnType<typeof useTools> }) {
  const at = session.at;
  const chooseGround = session.chooseGround;
  const clearGround = session.clearGround;
  const fadeGround = session.fadeGround;
  const groundFile = session.groundFile;
  const name = session.name;
  const setName = session.setName;
  const store = session.store;
  const pdfAsk = session.pdfAsk;
  const setPdfAsk = session.setPdfAsk;
  const setShaping = session.setShaping;
  const setTrimming = session.setTrimming;
  const shaping = session.shaping;
  const takeAsked = session.takeAsked;
  const trimming = session.trimming;
  const turnGround = session.turnGround;
  const field = session.field;
  const folio = session.folio;
  const from = session.from;
  const grid = session.grid;
  const guides = session.guides;
  const hist = session.hist;
  const lay = session.lay;
  const mine = session.mine;
  const numbering = session.numbering;
  const onPaste = session.onPaste;
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
          {tab === "Blatt" && (
            <>
              {/* A page's own format stands in for the sheet's; "Wie Blatt" gives the page the sheet's again. */}
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
              <div className="seg">
                <button className={own ? "" : "on"} aria-pressed={!own} onClick={() => setOwn(false)}>Alle Seiten</button>
                <button className={own ? "on" : ""} aria-pressed={own} onClick={() => setOwn(true)}>Nur diese Seite</button>
              </div>
              <h2>Seitenzahlen</h2>
              <Switch label="Seitenzahlen" on={folio.on} onChange={(on) => numbering({}, on)} />
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
                  <Switch label="Nicht auf der ersten Seite" on={folio.notFirst} onChange={(on) => numbering({ notFirst: on })} />
                  <h2>Farbe</h2>
                  <div className="seg">
                    <button className={folio.black ? "" : "on"} aria-pressed={!folio.black} onClick={() => numbering({ black: false })}>Grau</button>
                    <button className={folio.black ? "on" : ""} aria-pressed={folio.black} onClick={() => numbering({ black: true })}>Schwarz</button>
                  </div>
                </>
              )}
              <h2>Hintergrund</h2>
              <div className="ground-box">
                <p className="hint">{GROUND_HINT}</p>
                <button onClick={() => groundFile.current?.click()}>
                  <Wallpaper size={16} aria-hidden />
                  Hintergrund wählen
                </button>
                <input
                  ref={groundFile}
                  type="file"
                  aria-label="Hintergrunddatei"
                  accept="image/jpeg,image/png,application/pdf,.pdf"
                  hidden
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    e.target.value = "";
                    if (file) void chooseGround(file);
                  }}
                />
                {pages[page].ground && (
                  <>
                    <button aria-pressed={shaping} className={shaping ? "on" : undefined} onClick={() => (setShaping((on) => !on), setTrimming(false))}>
                      Hintergrund bearbeiten
                    </button>
                    <div className="seg" role="group" aria-label="Deckkraft">
                      {FADES.map((opacity) => (
                        <button key={opacity} aria-pressed={(pages[page].ground?.opacity ?? 1) === opacity} className={(pages[page].ground?.opacity ?? 1) === opacity ? "on" : undefined} onClick={() => fadeGround(opacity)}>
                          {opacity * 100} %
                        </button>
                      ))}
                    </div>
                    <button onClick={turnGround}>Drehen</button>
                    <button aria-pressed={trimming} className={trimming ? "on" : undefined} onClick={() => setTrimming((on) => !on)}>
                      Zuschneiden
                    </button>
                    <button onClick={clearGround}>Hintergrund entfernen</button>
                  </>
                )}
                {pdfAsk && (
                  <>
                    <p className="hint">Die PDF hat {pdfAsk.pages} Seiten.</p>
                    <label className="tick">
                      Seite
                      <input
                        type="number"
                        aria-label="Seite der PDF"
                        min={1}
                        max={pdfAsk.pages}
                        value={pdfAsk.page}
                        onChange={(e) => setPdfAsk({ ...pdfAsk, page: Math.min(pdfAsk.pages, Math.max(1, Math.round(Number(e.target.value)) || 1)) })}
                      />
                    </label>
                    <button onClick={() => void takeAsked(String(pdfAsk.page))}>Diese Seite</button>
                    <button onClick={() => void takeAsked("all")}>Alle Seiten</button>
                    <button onClick={() => setPdfAsk(undefined)}>Abbrechen</button>
                  </>
                )}
              </div>
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
                <button className={placesOn ? "" : "on"} aria-pressed={!placesOn} onClick={() => stellen(false)}>Ungefärbt</button>
                <button className={placesOn ? "on" : ""} aria-pressed={placesOn} onClick={() => stellen(true)}>Gefärbt</button>
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
              {/* A template is a sheet to begin a new one from: it is picked under "Neues Blatt". */}
              <h2>Vorlage</h2>
              <input type="text" aria-label="Name der Vorlage" placeholder="Name der Vorlage" maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
              <button className="wide" disabled={!name.trim()} onClick={store}>
                <Plus size={14} aria-hidden />
                Als Vorlage speichern
              </button>
              <p className="hint" role="status">
                {session.stored ? `„${session.stored}“ ist gespeichert. Du findest die Vorlage unter „Neues Blatt“.` : "Eine Vorlage findest du unter „Neues Blatt“ wieder."}
              </p>
            </>
          )}
    </>
  );
}
