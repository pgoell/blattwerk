// A Lineatur's rows, its width across the page, and the Lernwörter it writes.
import { round } from "../../arrange";
import { MARGIN, RULINGS, bandColorOf, bandOf, boxed, dir, foldsOf, fontOf, houseOf, houseTintOf, kindOf, listOf, lowest, rowsNeeded, rowsOf, shade, tall, type Block, type Box, type Doc, type ListMode, type Ruling, type RulingBlock } from "../../sheet";
import { filled, room, unshown } from "../../words";
import type { Picked } from "../Field";
import { FontSelect, unknownFont } from "./font";
import { Syllables } from "./syllables";
import { TraceControls } from "./trace";
import { syllabled } from "./words";

export function RulingPanel({
  sel, style, place, words, lineaturen, list, toList, part, look, mendWord, doc, traced, W, H,
}: {
  sel: Block[];
  style: (type: Block["type"], props: object, key?: string, only?: string[]) => void;
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
  words: string[];
  lineaturen: RulingBlock[];
  list: (mode?: ListMode) => void;
  toList: () => void;
  part?: Picked;
  look: (props: object, key?: string) => void;
  mendWord: (keys: string[], counts: number[] | undefined, id: string) => void;
  doc: Doc;
  traced: (props: object) => void;
  W: number;
  H: number;
}) {
  const fixed = sel.some((b) => b.locked);
  const rulings = sel.filter((b): b is RulingBlock => b.type === "ruling");
  if (!rulings.length) return null;
  const text = sel.map(boxed).find((p) => p);
  const tables = sel.filter((b) => b.type === "table");
  const mode = rulings.every((b) => listOf(b)) ? listOf(rulings[0]) : undefined;
  const n = unshown(rulings, words, lineaturen);
  // A ruling keeps its rows when its type changes, and grows to the rows its text needs, up to the foot of the page.
  // A kind change keeps its rows and takes rows away only where the page foot cuts them short; the buttons give the rows themselves.
  const rule = (kind: Ruling, rows?: number) => {
    style("ruling", { kind }, "ruling");
    const row = RULINGS[kindOf(kind)].row;
    place(
      rulings.map((b) => {
        if (rows !== undefined) return [b.id, tall(b, round(Math.max(1, rows) * row))];
        const next = { ...b, props: { ...b.props, kind } };
        // Past the foot it keeps the rows that still fit, measured by its lowest corner, so a turned one as it lies.
        let n = Math.max(rowsOf(b), rowsNeeded(next));
        while (n > 1 && lowest({ ...b, ...tall(b, round(n * row)) }) > H - MARGIN + 0.01) n--;
        return [b.id, tall(b, round(Math.max(1, n) * row))];
      }),
      "ruling",
    );
  };
  // A ruling fills the room between the margins along the way it lies: both ends go out from its centre until a
  // corner would cross a margin. A slanted one stays as it is when it lies past a margin along its way and has
  // less room there than it is high.
  const wide = (b: RulingBlock): Partial<Box> => {
    const [c, s] = dir(b);
    // The middle of each long edge.
    const mids = [-1, 1].map((side) => [b.x + (b.w - side * b.h * s) / 2, b.y + (b.h + side * b.h * c) / 2]);
    const [back, on] = [-1, 1].map((way) => Math.min(...mids.flatMap(([x, y]) => [room(x, way * c, W), room(y, way * s, H)])));
    // Rounded down, so that no corner crosses.
    const w = Math.floor((back + on) * 100 + 1e-6) / 100;
    // A slanted one that fills the room to a hair stays too: its place is rounded, so a second press would find
    // a little room again, and the more of it the closer the block lies to level or upright. So its place is
    // rounded finer, to keep that hair thin.
    const hair = 0.02 + 0.0001 / Math.min(Math.abs(c), Math.abs(s));
    const slanted = Math.abs(c * s) > 1e-9;
    const fine = (n: number) => (slanted ? Math.round(n * 1e4) / 1e4 : round(n));
    if (!(w > 0 && w < Infinity) || (slanted && (((back < 0 || on < 0) && w < b.h) || [back, on].every((end) => Math.abs(end - b.w / 2) < hair)))) return {};
    // A level block keeps its y as it is.
    return { w, x: fine(b.x + (b.w - w + (on - back) * c) / 2), ...(Math.abs(s) > 1e-9 && { y: fine(b.y + ((on - back) * s) / 2) }) };
  };
  return (
    <>
          <h2>Lineatur</h2>
          <select aria-label="Art der Lineatur" value={kindOf(rulings[0].props.kind)} onChange={(e) => rule(e.target.value as Ruling)}>
            {Object.entries(RULINGS).map(([kind, { name }]) => (
              <option key={kind} value={kind}>
                {name}
              </option>
            ))}
          </select>
          <div className="seg">
            <button aria-label="Eine Zeile weniger" disabled={fixed} onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) - 1)}>−</button>
            <output>{rowsOf(rulings[0]) === 1 ? "1 Zeile" : `${rowsOf(rulings[0])} Zeilen`}</output>
            <button aria-label="Eine Zeile mehr" disabled={fixed} onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) + 1)}>＋</button>
          </div>
          <label>
            Farbe
            <input type="color" value={rulings[0].props.color} onChange={(e) => style("ruling", { color: e.target.value }, "color")} />
          </label>
          {/* The house and the band: only the kinds with zones have them. A press is one undo step, and a drag over the colour is one. */}
          {RULINGS[kindOf(rulings[0].props.kind)].zones && (
            <>
              <button className={houseOf(rulings[0]) ? "on" : ""} aria-pressed={houseOf(rulings[0])} onClick={() => style("ruling", { house: !houseOf(rulings[0]) })}>Häuschen</button>
              {houseOf(rulings[0]) && (
                <select aria-label="Häuschen einfärben" value={houseTintOf(rulings[0]) ?? "none"} onChange={(e) => style("ruling", { houseTint: e.target.value === "none" ? undefined : e.target.value })}>
                  <option value="none">Nicht eingefärbt</option>
                  <option value="room">Zimmer eingefärbt</option>
                  <option value="all">Dach, Zimmer und Keller eingefärbt</option>
                </select>
              )}
              <button className={bandOf(rulings[0]) ? "on" : ""} aria-pressed={bandOf(rulings[0])} onClick={() => style("ruling", { band: !bandOf(rulings[0]) })}>Mittelband einfärben</button>
              {bandOf(rulings[0]) && (
                <label>
                  Farbe des Mittelbands
                  <input type="color" value={bandColorOf(rulings[0]) ?? shade(rulings[0].props.color)} onChange={(e) => style("ruling", { bandColor: e.target.value }, "bandColor")} />
                </label>
              )}
            </>
          )}
          <div className="row">
            <button disabled={fixed} onClick={() => place(rulings.map((b) => [b.id, wide(b)]))}>Seitenbreite</button>
            <button disabled={fixed} onClick={() => place(rulings.map((b) => [b.id, filled(b, W, H)]))}>Bis Seitenende</button>
          </div>
          {/* The text of a Lineatur: its own, or the sheet's Lernwörter in one of three modes. A mode shows only when
              every picked Lineatur has it. */}
          <select aria-label="Text der Lineatur" value={mode ?? "own"} onChange={(e) => list(e.target.value === "own" ? undefined : (e.target.value as ListMode))}>
            <option value="own">Eigener Text</option>
            <option value="copy">Lernwörter abschreiben</option>
            <option value="trace">Lernwörter nachspuren</option>
            <option value="row">Lernwörter, ganze Zeile nachspuren</option>
            <option value="fold">Lernwörter als Knickblatt</option>
          </select>
          {mode === "fold" && (
            <div className="seg">
              {[2, 3].map((n) => (
                <button key={n} className={foldsOf(rulings[0]) === n ? "on" : ""} aria-label={`${n} Spalten zum Schreiben`} aria-pressed={foldsOf(rulings[0]) === n} onClick={() => style("ruling", { folds: n }, "folds")}>
                  {n}
                </button>
              ))}
            </div>
          )}
          {n > 0 && (
            <p className="hint" role="status">
              {n === 1 ? "1 Wort passt nicht in die Zeilen." : `${n} Wörter passen nicht in die Zeilen.`}
            </p>
          )}
          {mode && <button onClick={toList}>Lernwörter bearbeiten</button>}
          {!mode && <p className="hint">Lineatur anklicken und lostippen, um auf die Zeilen zu schreiben.</p>}
          {RULINGS[kindOf(rulings[0].props.kind)].at && (
            <FontSelect label="Schriftart auf den Zeilen" value={fontOf(rulings[0].props.font)} unknown={unknownFont(rulings.map((b) => b.props.font))} onChange={(font) => style("ruling", { font })} />
          )}
          {!mode && (
            <TraceControls props={rulings[0].props} font={RULINGS[kindOf(rulings[0].props.kind)].at ? fontOf(rulings[0].props.font) : "andika"} onChange={traced} />
          )}
          {!text && !tables.length && <Syllables key={sel.find(syllabled)?.id} sel={sel} part={part} look={look} style={style} mendWord={mendWord} doc={doc} words={words} />}
    </>
  );
}
