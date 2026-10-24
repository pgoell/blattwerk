// The format panel's settings for the school blocks, and the numbering any block can have.
import Numbering from "../components/Numbering";
import { counts, ScoreInput, type Axis, type Block, type Box, type Doc, type List, type ListMode, type RulingBlock, type TableBlock } from "../sheet";
import type { Marks, Picked } from "./Field";
import type { Owed } from "../saves";
import type { Border } from "../borders";
import type { LineStyle, Pen } from "../edges";
import { Notices } from "./format/notices";
import { Place, Turns } from "./format/place";
import { RulingPanel } from "./format/ruling";
import { SchoolPanels, useSchools } from "./format/schools";
import { Symbols } from "./format/symbols";
import { TablePanel } from "./format/table";
import { TextPanel } from "./format/text";

export { adjustable, bounds, drawn, frameOf, has, hull, inked, mirrored, norm, outline, scaled, scaledGroup, sized, swung, unfit } from "../arrange";

type Props = {
  sel: Block[];
  // Keeps a maths change the session ran out on, for the editor to redo after the login (saves.ts `owe`).
  owe: (entry: Owed) => void;
  // Sets props on every selected block of one type.
  style: (type: Block["type"], props: object, key?: string, only?: string[]) => void;
  // Adds `by` to the score of each picked score box, each from its own number.
  bump: (by: number) => void;
  // Sets what a text and a shape share on every selected one of them.
  look: (props: object, key?: string) => void;
  // Sets the trace text's look on every picked block that carries text, in one step.
  traced: (props: object) => void;
  // Makes the picked texts and shapes take the sheet's Lernwörter as their text, or cut them loose with their words.
  link: (on: boolean) => void;
  // Sets props on the picked texts and shapes that take the Lernwörter, as `look` does for all of them.
  feed: (props: object, key?: string) => void;
  // Sets bold, italic, underline or colour on the words picked in the text being edited, or else as `look` does.
  paint: (props: Marks, key?: string) => void;
  // Mends a word's split on every block of the sheet, or with no counts takes the mend back to the module's own split.
  mendWord: (keys: string[], counts: number[] | undefined, id: string) => void;
  // Makes a list of the paragraphs the caret stands in, or else of all the selected texts.
  itemize: (kind: List) => void;
  // Makes the picked words, the cell being edited or else every selected text a gap, or takes the gap off.
  gap: (on: boolean) => void;
  // Makes every n-th word of every selected text a gap.
  every: (n: number) => void;
  // What is picked in the text being edited.
  part?: Picked;
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
  // Adds a row or a column to a table before the one at `i`, or takes the one at `i` away.
  rank: (b: TableBlock, axis: "row" | "col", i: number, add: boolean, after?: boolean) => void;
  // The cell of the table being edited, counted row by row.
  cell?: number;
  // The far corner of the cells picked with the open one, if any.
  reach?: number;
  // Makes the picked cells one cell, or brings the open merged cell back to single cells.
  merge: () => void;
  unmerge: () => void;
  // The height in mm of each row of the table being edited, as its grid lays them out.
  laid: number[];
  // The ids of the blocks whose text the page's foot cuts short.
  full: string[];
  // The ids of the shapes whose word does not print whole, wherever they stand.
  cramped: string[];
  // The ids of the picked shapes whose text grew them back after a smaller size from this panel.
  held: string[];
  // Tells the editor which blocks this panel resizes.
  onSize: (ids: string[]) => void;
  // Sets the width of the picked columns, or the height of the picked rows, in mm; or evens them out.
  sizeCells: (axis: "col" | "row", mm: number) => void;
  evenCells: (axis: "col" | "row") => void;
  // The line style and width of every picked table, or the one line of its `key` in a drag; Schneidelinien on or off.
  lines: (patch: { style?: LineStyle; width?: number }, key?: string) => void;
  cutting: (on: boolean) => void;
  // Draws the pen on the chosen borders of the table being edited.
  // Absent unless one table that is not locked is picked alone.
  border?: (which: Border, pen: Pen) => void;
  // Starts or ends crop mode; absent unless one picture that is not locked is selected.
  crop?: () => void;
  // The sheet's Lernwörter, and the mode each picked Lineatur takes them in: none cuts it loose with its words.
  words: string[];
  // Every Lineatur of the sheet: a picked one that a run-on Lineatur goes on from cuts off no word.
  lineaturen: RulingBlock[];
  list: (mode?: ListMode) => void;
  // Shows the list of the Lernwörter in the panel.
  toList: () => void;
  cropping: boolean;
  // Turns what is selected by so many degrees: a group picked whole as one, a loose block about its own centre.
  spin: (by: number) => void;
  // Mirrors what is selected across or down: a group picked whole as one, a loose block in itself.
  mirror: (axis: Axis) => void;
  // Whether the block is a thing by itself: loose, or picked out of its group.
  alone: (b: Block) => boolean;
  // Whether a new width sets the height to match, in the fields and on the handles.
  lock: boolean;
  setLock: (on: boolean) => void;
  // Where X and Y count from: the page's top left corner, or its centre. Kept by the editor, not in the sheet.
  from: "corner" | "centre";
  setFrom: (from: "corner" | "centre") => void;
  // The width and height in mm of the page in use.
  size: number[];
  // The whole sheet, for the maths blocks a Selbstkontrolle can check.
  doc: Doc;
  // Opens text help for the one selected text. Absent when that text cannot be helped.
  onHelp?: () => void;
};

export default function Format({ sel, style, bump, look, mendWord, traced, link, feed, paint, itemize, gap, every, part, place, rank, cell, reach, merge, unmerge, laid, full, cramped, held, onSize, sizeCells, evenCells, lines, cutting, border, crop, cropping, spin, mirror, alone, lock, setLock, from, setFrom, size: [W, H], doc, words, lineaturen, list, toList, owe, onHelp }: Props) {
  const schools = useSchools({ sel, style, place, H });
  const { mark } = sel[0];
  const number = (to?: string) => place(sel.map((b) => [b.id, { mark: to }]));
  const points = sel.find((b): b is Extract<Block, { type: "points" }> => b.type === "points");
  const sign = sel.find((b): b is Extract<Block, { type: "symbol" }> => b.type === "symbol");
  return (
    <>
      <Notices sel={sel} doc={doc} full={full} cramped={cramped} held={held} W={W} H={H} paper={schools.paperHint} refused={schools.refusedType} />
      <Place sel={sel} place={place} lock={lock} setLock={setLock} from={from} setFrom={setFrom} W={W} H={H} spin={spin} onSize={onSize} alone={alone} />
      <TextPanel sel={sel} part={part} look={look} style={style} paint={paint} itemize={itemize} traced={traced} link={link} feed={feed} gap={gap} every={every} cell={cell} mendWord={mendWord} doc={doc} words={words} toList={toList} onHelp={onHelp} />
      <RulingPanel sel={sel} style={style} place={place} words={words} lineaturen={lineaturen} list={list} toList={toList} part={part} look={look} mendWord={mendWord} doc={doc} traced={traced} W={W} H={H} />
      <TablePanel sel={sel} style={style} part={part} look={look} mendWord={mendWord} doc={doc} words={words} cell={cell} reach={reach} rank={rank} merge={merge} unmerge={unmerge} laid={laid} sizeCells={sizeCells} evenCells={evenCells} lines={lines} cutting={cutting} border={border} traced={traced} gap={gap} every={every} />
      <SchoolPanels {...schools} style={style} doc={doc} words={words} owe={owe} H={H} />
      {points && (
        <>
          <h2>Punkte</h2>
          <div className="seg">
            <ScoreInput max={points.props.max} change={(max) => style("points", { max })} steps={bump} />
          </div>
        </>
      )}
      {sign && (
        <>
          <h2>Symbol</h2>
          <Symbols value={sign.props.code} onPick={(code) => style("symbol", { code })} />
        </>
      )}
      {crop && (
        <>
          <h2>Bild</h2>
          <button className={cropping ? "wide on" : "wide"} aria-pressed={cropping} onClick={crop}>
            {cropping ? "Fertig" : "Zuschneiden"}
          </button>
        </>
      )}
      <Turns sel={sel} alone={alone} spin={spin} mirror={mirror} />
      <h2>Nummerierung</h2>
      <Numbering value={mark} onChange={number} symbol={() => number("2B50")} />
      {mark && !counts(mark) && <Symbols value={mark} onPick={number} />}
    </>
  );
}
