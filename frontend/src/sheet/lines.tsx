// Draws a lineatur: the lines, the house, and the letters in the squares.

import { PT } from "../height";
import { pairOf, useSplitter, splitting, Bows } from "./bows";
import { useBreaks, Words } from "./context";
import { RULINGS, kindOf, rowsOf, colsOf, traceOf, fadeOf, fontScale, fontOf, writtenStyle, indentOf, bandOf, bandColorOf, houseOf, houseWidth, houseTintOf, HOUSE, fadeAt, FONTS } from "./look";
import { type RulingBlock, listOf, foldsOf, startOf, squares } from "./ruling";
import { classes } from "./shape";
import { type ReactNode, useContext, useState, useEffect, useRef, useLayoutEffect, Fragment, type CSSProperties } from "react";

// Drawn in mm: the SVG's own scale takes it to the block's size. The editor passes the field the text is typed in.
export function Lines({ block, k, children }: { block: RulingBlock; k: number; children?: ReactNode }) {
  const { row, at, zones, size } = RULINGS[kindOf(block.props.kind)];
  const { text = "" } = block.props;
  const breaks = useBreaks(block.props.breaks);
  const rows = rowsOf(block);
  const cols = colsOf(block);
  // A block set to the list shows the list alone: with no word in it, empty rows, and not its own text, which the
  // editor could not open there.
  const words = useContext(Words);
  const mode = listOf(block);
  // Karo draws its trace text in the squares, which have no dotted cut: a dotted trace there is grey. A Lernwörter
  // list draws its own look, so it has none.
  const karoLook = !at && !mode ? traceOf({ trace: block.props.trace }) : undefined;
  const karoFade = karoLook ? fadeOf(block.props) : undefined;
  const s = fontScale(fontOf(block.props.font));
  // A Knickblatt has its first column for the words and `folds` empty ones after it, all of the same width. On Karo
  // the first column is a whole number of squares, and the words are cut to it.
  const fold = mode === "fold";
  const folds = foldsOf(block);
  const first = at ? block.w / (folds + 1) : Math.max(1, Math.floor(cols / (folds + 1))) * row;
  const plain = mode === "copy" || fold;
  const shown = words.slice(startOf(block), startOf(block) + rows);
  const cut = (word: string) => [...word].slice(0, fold ? Math.round(first / row) : cols).join("");
  // On Karo a row of the list is its word, cut to the squares, and in "row" as often as whole words fit.
  const karo = mode === "row"
    ? shown.map((word) => {
        const c = cut(word);
        const reps = Math.max(1, Math.floor((cols + 1) / ([...c].length + 1)));
        return Array.from({ length: reps }, () => c).join(" ");
      }).join("\n")
    : shown.map(cut).join("\n");
  // Karo's syllables: the splitter cuts the text in the squares, and each syllable gets its colour in turn and its bow.
  // `failed` lets a page print without the bows when the splitter does not load.
  const on = !at && !!(block.props.syllables || pairOf(block.props.tints));
  const module = useSplitter(on);
  const [failed, setFailed] = useState(false);
  useEffect(() => void (on && splitting().catch(() => setFailed(true))), [on]);
  const shownText = mode ? karo : text;
  const letters = !at && cols > 0 ? squares(shownText, cols) : [];
  const place = new Map(letters.map(([x, y, , o]) => [o, [x, y]]));
  const tints = pairOf(block.props.tints);
  const colour = new Map<number, string>();
  const syllables: { plain: string; hue?: string; offsets: number[] }[] = [];
  // The splitter cuts whole words: a Lernwort cut to the squares keeps the syllables of the whole word, and only its
  // letters in the squares take a colour or a bow. `start` is where a run lies in the squares' text, `keep` how much
  // of it stands there.
  const runs: { start: number; whole: string; keep: number }[] = [];
  if (!mode) runs.push({ start: 0, whole: text, keep: text.length });
  else {
    let start = 0;
    for (const [i, line] of karo.split("\n").entries()) {
      const whole = shown[i] ?? "";
      const c = cut(whole);
      for (let s = 0; c && s < line.length; s += c.length + 1) runs.push({ start: start + s, whole, keep: c.length });
      start += line.length + 1;
    }
  }
  if (module) {
    let count = 0;
    for (const { start, whole, keep } of runs) {
      let [offset, word] = [0, undefined as number | undefined];
      for (const piece of module.pieces(whole, breaks)) {
        const from = offset;
        offset += piece.text.length;
        if (!piece.syl) continue;
        if (piece.word !== word) {
          word = piece.word;
          if (!block.props.tintsAcross) count = 0;
        }
        const hue = tints?.[count++ % 2];
        const offsets = Array.from({ length: Math.max(0, Math.min(module.shown(piece.text).length, keep - from)) }, (_, j) => start + from + j);
        if (hue) offsets.forEach((o) => colour.set(o, hue));
        if (offsets.length) syllables.push({ plain: module.plain(piece.text), hue, offsets });
      }
    }
  }
  // A bow under each syllable, cut where its letters leave a row of squares; a row past the block's rows gets none.
  const bowed = block.props.syllables && module ? syllables.flatMap(({ plain: syl, hue, offsets }, n) => {
    const runs: { y: number; x0: number; x1: number }[] = [];
    for (const o of offsets) {
      const spot = place.get(o);
      if (!spot || spot[1] >= rows) continue;
      const [x, y] = spot;
      const last = runs[runs.length - 1];
      if (last && last.y === y && last.x1 === x - 1) last.x1 = x;
      else runs.push({ y, x0: x, x1: x });
    }
    return runs.map(({ y, x0, x1 }) => {
      const [X0, X1, Y] = [x0 * row + 0.12 * row, (x1 + 1) * row - 0.12 * row, (y + 0.8) * row];
      const deep = Math.min(0.08 * row, (X1 - X0) / 2);
      return (
        <path key={`${n}-${y}-${x0}`} className="syl" data-syl={syl} d={`M${X0},${Y} Q${(X0 + X1) / 2},${Y + 2 * deep} ${X1},${Y}`} fill="none" stroke={hue ?? "currentColor"} strokeLinecap="round" strokeWidth={Math.max(0.05 * size, 0.15)} />
      );
    });
  }) : [];
  const each = (n: number) => Array.from({ length: n }, (_, i) => i * row);
  const ys = at ? each(rows).flatMap((top) => at.map((y) => top + y)) : each(rows + 1);
  const list = useRef<HTMLDivElement>(null);
  // A word wider than its column is pressed narrower, its letters as high as before, so it stays in the lines and
  // the house. The ratio does not depend on the scale k, so the thumbnail and the print press alike. Only a Knickblatt's
  // word has a width set, so the other lists are left alone. Measured after every render, and again when the fonts are in.
  const press = () => {
    for (const span of list.current?.querySelectorAll<HTMLElement>(".row > span") ?? []) {
      // The word inside is the one scaled: the span is the clip, and a scaled clip would cut the word.
      const word = span.firstElementChild as HTMLElement | null;
      if (!word) continue;
      word.style.transform = "";
      // The widths as laid out, not as drawn: a turned block's outline would measure wrong.
      const room = parseFloat(getComputedStyle(span).width);
      const natural = parseFloat(getComputedStyle(word).width);
      word.style.transform = natural > room ? `scaleX(${room / natural})` : "";
    }
  };
  useLayoutEffect(press);
  useLayoutEffect(() => {
    document.fonts.ready.then(press);
    document.fonts.addEventListener("loadingdone", press);
    return () => document.fonts.removeEventListener("loadingdone", press);
  }, []);
  const listed = mode && at && (
    <div ref={list} className="written listed" style={{ ...writtenStyle({ ...block, props: { ...block.props, trace: undefined, fade: undefined } }, k), color: plain ? undefined : "#aaaaaa" }}>
      {shown.map((word, i) => (
        <p className="row" key={i} style={{ height: row * k, margin: 0 }}>
          {mode === "row"
            ? Array.from({ length: Math.min(200, Math.ceil(block.w / (size * s * 0.3 * Math.max(1, word.length))) + 1) }, (_, j) => <Fragment key={j}>{j > 0 && " "}<span>{word}</span></Fragment>)
            : <span style={fold ? { width: Math.max(0, first - indentOf(block)) * k, overflow: "hidden" } : undefined}>{fold ? <span style={{ display: "inline-block", transformOrigin: "left" }}>{word}</span> : word}</span>}
        </p>
      ))}
    </div>
  );
  return (
    // The bows end where the rows do, with room for the last row's bows: a row cut off below shows no bow.
    <div className="lined" style={{ "--rows": `${(rows * row + 3) * k}px` } as CSSProperties}>
      <svg className="ruling" data-trace={karoLook} data-fade={karoFade} viewBox={`0 0 ${block.w} ${block.h}`} stroke={block.props.color} strokeWidth={0.2}>
        {/* The middle band lies between a row's second and third line. */}
        {zones && bandOf(block) && each(rows).map((top) => <rect key={top} className="band" y={top + zones[1]} width={block.w} height={zones[2] - zones[1]} fill={bandColorOf(block) ?? block.props.color} fillOpacity={bandColorOf(block) ? 1 : 0.12} stroke="none" />)}
        {ys.map((y) => (
          <line key={y} x2={at ? block.w : cols * row} y1={y} y2={y} />
        ))}
        {/* A house stands on each row's left end, over the lines: its roof, its room and its cellar. */}
        {zones && houseOf(block) && each(rows).map((top) => {
          const w = houseWidth(kindOf(block.props.kind));
          const tint = houseTintOf(block);
          return (
            <g key={top} className="house">
              <polygon className="roof" points={`0,${top + zones[1]} ${w / 2},${top + zones[0]} ${w},${top + zones[1]}`} fill={tint === "all" ? HOUSE.roof : "none"} strokeLinejoin="round" />
              <rect className="room" x={0} y={top + zones[1]} width={w} height={zones[2] - zones[1]} fill={tint ? HOUSE.room : "none"} strokeLinejoin="round" />
              <rect className="cellar" x={0} y={top + zones[2]} width={w} height={zones[3] - zones[2]} fill={tint === "all" ? HOUSE.cellar : "none"} strokeLinejoin="round" />
            </g>
          );
        })}
        {!at && each(cols + 1).map((x) => <line key={x} x1={x} x2={x} y2={rows * row} />)}
        {letters.map(([x, y, ch, o], i) => y < rows && (
          <text key={-i - 1} x={(x + 0.5) * row} y={(y + 0.5) * row} fontFamily="Andika" fontSize={size} textAnchor="middle" dominantBaseline="central" fill={colour.get(o) && karoLook !== "outline" ? colour.get(o) : mode ? (plain ? "currentColor" : "#aaaaaa") : karoLook === "grey" ? "#aaaaaa" : karoLook === "outline" ? "none" : "currentColor"} stroke={colour.get(o) && karoLook === "outline" ? colour.get(o) : karoLook === "outline" ? "currentColor" : "none"} strokeWidth={karoLook === "outline" ? size * 0.035 : undefined} opacity={karoFade && fadeAt(karoFade === "row" ? x : y, karoFade === "row" ? cols : rows)}>
            {ch}
          </text>
        ))}
        {/* The fold line between the words and the first empty column, and the lines between the empty columns:
            twice as thick as the rows' lines, so they show on Karo, where they lie on a line of the squares. */}
        {fold && (
          <>
            <line className="fold" x1={first} x2={first} y1={0} y2={rows * row} strokeWidth={0.4} strokeDasharray="2 1.5" />
            {Array.from({ length: folds - 1 }, (_, i) => (i + 2) * first).map((x) => (
              <line key={x} className="col" x1={x} x2={x} y1={0} y2={rows * row} strokeWidth={0.4} />
            ))}
            <text className="knick" x={first} y={-1} textAnchor="middle" fontFamily="Andika" fontSize={8 * PT} stroke="none" fill="#555555">
              knicken
            </text>
          </>
        )}
        {bowed}
        {on && !module && !failed && <g className="unsplit" />}
      </svg>
      {mode ? (
        <>
          {listed}
          {at && (block.props.syllables || block.props.tints) && <Bows block={block} base={FONTS[fontOf(block.props.font)][2]} breaks={breaks} syllables={block.props.syllables} tints={pairOf(block.props.tints)} tintsAcross={block.props.tintsAcross} />}
        </>
      ) : (
        <>
          {children ?? (at && text && <p className="written" data-trace={traceOf(block.props)} data-fade={fadeOf(block.props)} style={writtenStyle(block, k)}>{text}</p>)}
          {/* The editor's field holds the text as a value, which no bow can measure: a hidden copy of it does. */}
          {at && text && (block.props.syllables || block.props.tints) && (
            <>
              {/* With colours the copy shows and the field's letters go clear, as in a table's open cell, so the colours stay while typing. */}
              {children && <p className={classes("written", "copy", pairOf(block.props.tints) && "shown")} aria-hidden="true" data-trace={traceOf(block.props)} style={{ ...writtenStyle(block, k), visibility: pairOf(block.props.tints) ? undefined : "hidden" }}>{text}</p>}
              <Bows block={block} base={FONTS[fontOf(block.props.font)][2]} breaks={breaks} syllables={block.props.syllables} tints={pairOf(block.props.tints)} tintsAcross={block.props.tintsAcross} />
            </>
          )}
        </>
      )}
    </div>
  );
}
