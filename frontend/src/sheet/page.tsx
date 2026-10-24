// A page of the sheet: which block draws, and the paper around it.

import { GroundView } from "../ground";
import { PT } from "../height";
import { uploadAddress } from "../uploadAddress";
import { Halbschriftlich } from "./blocks/halbschriftlich";
import { Hunderterfeld } from "./blocks/hunderterfeld";
import { MagischesQuadrat } from "./blocks/magischesQuadrat";
import { Malquadrat } from "./blocks/malquadrat";
import { Operatorfeld } from "./blocks/operatorfeld";
import { Pfeilbild } from "./blocks/pfeilbild";
import { Rechendreieck } from "./blocks/rechendreieck";
import { Rechenrad } from "./blocks/rechenrad";
import { Rechentabelle } from "./blocks/rechentabelle";
import { Selbstkontrolle } from "./blocks/selbstkontrolle";
import { Suchsel } from "./blocks/suchsel";
import { Uhr } from "./blocks/uhr";
import { Zahlenhaus } from "./blocks/zahlenhaus";
import { Zahlenkette } from "./blocks/zahlenkette";
import { Zahlenmauer } from "./blocks/zahlenmauer";
import { Zahlenstrahl } from "./blocks/zahlenstrahl";
import { Zehnerfeld } from "./blocks/zehnerfeld";
import { Zerlegungsfeld } from "./blocks/zerlegungsfeld";
import { flipped, K, turned } from "./box";
import { Words, Whole } from "./context";
import { type Block, FIELDS, type Doc, sizeOf, read, wordsIn } from "./doc";
import { Frame, Line } from "./frame";
import { Lines } from "./lines";
import { textStyle, inset } from "./look";
import { Maths } from "./mathsView";
import { Count, numbers } from "./numbering";
import { NUMBER_EM, Numbers } from "./rich";
import { stepOf } from "./shape";
import { Table } from "./tableView";
import { isLine, symbol, boxed } from "./text";
import type { ReactNode, CSSProperties } from "react";

// What a block shows, at `k` pixels per mm. Sizes inside a block are in em of a font size set to the scale.
// `solved` fills in the answers of the maths exercises. `at` is the cell of a table that the editor's field is for.
export function Draw({ block, k, solved = false, at, reach, children }: { block: Block; k: number; solved?: boolean; at?: number; reach?: number; children?: ReactNode }) {
  if (block.type === "maths") return <Maths block={block} k={k} solved={solved} />;
  if (block.type === "suchsel") return <Suchsel block={block} k={k} solved={solved} />;
  if (block.type === "zahlenmauer") return <Zahlenmauer block={block} k={k} solved={solved} />;
  if (block.type === "zahlenhaus") return <Zahlenhaus block={block} k={k} solved={solved} />;
  if (block.type === "zahlenkette") return <Zahlenkette block={block} k={k} solved={solved} />;
  if (block.type === "pfeilbild") return <Pfeilbild block={block} k={k} solved={solved} />;
  if (block.type === "operatorfeld") return <Operatorfeld block={block} k={k} solved={solved} />;
  if (block.type === "rechenrad") return <Rechenrad block={block} solved={solved} />;
  if (block.type === "rechentabelle") return <Rechentabelle block={block} solved={solved} />;
  if (block.type === "magischesquadrat") return <MagischesQuadrat block={block} solved={solved} />;
  if (block.type === "malquadrat") return <Malquadrat block={block} solved={solved} />;
  if (block.type === "zerlegungsfeld") return <Zerlegungsfeld block={block} solved={solved} />;
  if (block.type === "halbschriftlich") return <Halbschriftlich block={block} solved={solved} />;
  if (block.type === "zehnerfeld") return <Zehnerfeld block={block} solved={solved} />;
  if (block.type === "rechendreieck") return <Rechendreieck block={block} k={k} solved={solved} />;
  if (block.type === "zahlenstrahl") return <Zahlenstrahl block={block} k={k} solved={solved} />;
  if (block.type === "hunderterfeld") return <Hunderterfeld block={block} k={k} solved={solved} />;
  if (block.type === "uhr") return <Uhr block={block} k={k} solved={solved} />;
  if (block.type === "selbstkontrolle") return <Selbstkontrolle block={block} k={k} solved={solved} />;
  if (block.type === "table") return <Table block={block} k={k} at={at} reach={reach} solved={solved}>{children}</Table>;
  if (block.type === "text" || (block.type === "shape" && !isLine(block))) return <Frame block={block} k={k} solved={solved}>{children}</Frame>;
  if (block.type === "shape") return <Line block={block} k={k} solved={solved} />;
  if (block.type === "ruling") return <Lines block={block} k={k}>{children}</Lines>;
  if (block.type === "symbol") return <img src={symbol(block.props.code)} alt="" draggable={false} style={flipped(block)} />;
  // While a name line is written in, `children` holds one field for each word, in the word's place of the line.
  if (block.type === "name") {
    const off = block.props.hidden ?? [];
    return (
      <div className="fields" style={{ fontSize: 12 * PT * k }}>
        {(block.props.fields ?? FIELDS).map((field, i) =>
          off.includes(i) ? null : (
            <span key={i} className={i === 0 ? "name" : undefined}>
              {field}:{(children as ReactNode[] | undefined)?.[i] ?? <i />}
            </span>
          ),
        )}
      </div>
    );
  }
  // The words' row is the box between its lines, in an even count of pixels: so they stand whole pixels below the
  // box's top. A part of a pixel Chromium rounds one way on a sharp screen and another in print.
  // While the score is written in, `children` is its field in place of the number.
  if (block.type === "points")
    return (
      <div className="points" style={{ fontSize: 12 * PT * k, lineHeight: `${2 * Math.round((block.h * k) / 2 - 1)}px` }}>
        {/* The word with its space as one piece of text, as before: the PDF sets each piece on its own. */}
        / {children ?? block.props.max}
        {block.props.max === 1 ? " Punkt" : " Punkte"}
      </div>
    );
  if (block.type === "image") {
    const [l, t, r, b] = block.props.cut;
    const [w, h] = [1 - l - r, 1 - t - b];
    // The picture clips itself at its cut. The box clips on whole pixels: alone it let a strip of the part that is
    // cut off, up to a pixel wide, show beyond the cut and print. A whole picture is left as it was.
    const clipPath = l || t || r || b ? `inset(${[t, r, b, l].map((share) => `${share * 100}%`).join(" ")})` : undefined;
    return (
      <div className="picture" style={flipped(block)}>
        <img
          src={uploadAddress(block.props.upload)}
          alt=""
          draggable={false}
          style={{ width: `${100 / w}%`, height: `${100 / h}%`, left: `${(-100 * l) / w}%`, top: `${(-100 * t) / h}%`, clipPath, opacity: block.props.opacity }}
        />
      </div>
    );
  }
  // A block of a type this script does not know: a newer Blattomat made it, and it stays as it is in the sheet.
  return <div className="unknown">Dieser Block braucht eine neuere Version von Blattomat.</div>;
}
// A block's numbering stands to the left of its box, so the box keeps its place and its snap lines. `n` is the
// number of a counted block; a symbol has none. Beside a text it starts as far down as the text's first line, and
// beside a line its middle is level with the line's start.
export function Mark({ block, k, n }: { block: Block; k: number; n?: number }) {
  if (!block.mark) return null;
  const style = textStyle(boxed(block) ?? { text: "", size: 14, align: "left" }, k);
  // The line numbers stand between the mark and the box: the mark moves left of their column.
  const column = block.type === "text" && stepOf(block.props.lines) > 0 ? `calc(.4em + ${(2 + 1.6 * NUMBER_EM * block.props.size * PT) * k}px)` : undefined;
  return (
    <b className="mark" style={{ ...style, textDecoration: "none", paddingTop: block.type === "text" ? inset(block.props, false)[0] * k : 0, paddingRight: column, translate: isLine(block) ? "0 -50%" : undefined }}>
      {n ? <Count mark={block.mark} n={n} /> : <img src={symbol(block.mark)} alt="" />}
    </b>
  );
}

// A sheet's page numbers: off unless `on` is true. A value nobody knows reads as the default.
export const pageNumbersOf = (doc: Doc) => {
  const p = doc.pageNumbers ?? {};
  return {
    on: p.on === true,
    at: (["bottom", "right", "outer", "top"] as const).find((at) => at === p.at) ?? "bottom",
    form: (["n", "seite", "of", "seiteVon"] as const).find((form) => form === p.form) ?? "n",
    notFirst: p.notFirst === true,
    black: p.black === true,
  };
};
// The text and place of a page's number, or nothing when the sheet shows none on that page. Pages count from 1.
export const folioOf = (doc: Doc, page: number) => {
  const f = pageNumbersOf(doc);
  if (!f.on || (f.notFirst && page === 0)) return undefined;
  const [w] = sizeOf(doc, page);
  const n = page + 1;
  const m = doc.pages.length;
  const text = { n: `${n}`, seite: `Seite ${n}`, of: `${n} / ${m}`, seiteVon: `Seite ${n} von ${m}` }[f.form];
  const pos: CSSProperties =
    f.at === "bottom" ? { left: 0, width: w * K, textAlign: "center", bottom: 6 * K }
    : f.at === "top" ? { right: 15 * K, top: 6 * K }
    : f.at === "outer" && n % 2 === 0 ? { left: 15 * K, bottom: 6 * K }
    : { right: 15 * K, bottom: 6 * K };
  return { text, pos, at: f.at, black: f.black };
};
// A page's number, the first child of its `.scaled` div, so the blocks draw over it.
export function PageNumber({ doc, page }: { doc: Doc; page: number }) {
  const f = folioOf(doc, page);
  return f ? (
    <span className="folio" aria-hidden style={{ ...f.pos, fontSize: 9 * PT * K, color: f.black ? "#000000" : "#707070" }}>
      {f.text}
    </span>
  ) : null;
}

// A page with nothing to take hold of, at `k` pixels per mm: page one drawn small in the list, every page at its
// true size in the PDF, where it needs no transform. The answer key says on each page that it is one; with the page
// number at the top right, it moves to the top left.
export function Paper({ doc, k, page = 0, solved = false, letter }: { doc: Doc; k: number; page?: number; solved?: boolean; letter?: string }) {
  const all = read(doc);
  const ns = numbers(all);
  const [w, h] = sizeOf(all, page);
  const moved = solved && folioOf(all, page)?.at === "top";
  return (
    <Words.Provider value={wordsIn(all)}>
    <Whole.Provider value={all}>
    <div className={w > h ? "paper wide" : "paper"} style={{ width: w * k, height: h * k }}>
      <div className="scaled" style={{ width: w * K, height: h * K, transform: k === K ? undefined : `scale(${k / K})` }}>
        {all.pages[page].ground && (
          <div className="ground-clip">
            <GroundView ground={all.pages[page].ground} w={w} h={h} k={K} />
          </div>
        )}
        <PageNumber doc={all} page={page} />
        {all.pages[page].blocks.map((b) => (
          <div key={b.id} className="block" data-block={b.id} style={{ left: b.x * K, top: b.y * K, width: b.w * K, height: b.h * K, zIndex: b.z, ...turned(b) }}>
            <Draw block={b} k={K} solved={solved} />
            {b.type === "text" && stepOf(b.props.lines) > 0 && <Numbers block={b} />}
            <Mark block={b} k={K} n={ns.get(b.id)} />
          </div>
        ))}
        {solved && <b className="key" style={{ top: 5 * K, ...(moved ? { left: 15 * K } : { right: 15 * K }), fontSize: 11 * PT * K }}>{letter ? `Lösungen ${letter}` : "Lösungen"}</b>}
        {letter && <b className="variant" style={{ position: "absolute", bottom: 5 * K, right: 8 * K, fontSize: 8 * PT * K }}>{letter}</b>}
      </div>
    </div>
    </Whole.Provider>
    </Words.Provider>
  );
}
