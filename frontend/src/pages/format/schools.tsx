// Which school panel stands, and the change a block refuses once it would pass the paper.
import { useEffect, useState } from "react";
import { pastPaper } from "../../insert";
import { mathsHeight, overFoot, tall, type Block, type Box, type MathsProps } from "../../sheet";
import type { Owed } from "../../saves";
import type { Doc } from "../../sheet";
import Maths from "../Maths";
import Suchsel from "../Suchsel";
import Zahlenmauer from "../Zahlenmauer";
import Zahlenhaus from "../Zahlenhaus";
import Zahlenkette from "../Zahlenkette";
import Pfeilbild from "../Pfeilbild";
import Operatorfeld from "../Operatorfeld";
import Rechenrad from "../Rechenrad";
import Rechentabelle from "../Rechentabelle";
import MagischesQuadrat from "../MagischesQuadrat";
import Malquadrat from "../Malquadrat";
import Zerlegungsfeld from "../Zerlegungsfeld";
import Halbschriftlich from "../Halbschriftlich";
import Zehnerfeld from "../Zehnerfeld";
import Rechendreieck from "../Rechendreieck";
import Zahlenstrahl from "../Zahlenstrahl";
import Hunderterfeld from "../Hunderterfeld";
import Uhr from "../Uhr";
import Selbstkontrolle from "../Selbstkontrolle";

export function useSchools({
  sel, style, place, H,
}: {
  sel: Block[];
  style: (type: Block["type"], props: object, key?: string, only?: string[]) => void;
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
  H: number;
}) {
  // The generator's limits belong to one block.
  const maths = sel.length === 1 && sel[0].type === "maths" ? sel[0] : undefined;
  const suchsel = sel.length === 1 && sel[0].type === "suchsel" ? sel[0] : undefined;
  // A maths drawing that would grow past the paper's edge keeps its props, and the panel says why (#911).
  // The change refused, the block it was for, and that block's props and height at the refusal: the hint stays while the block is as it was (#911).
  const [denied, setDenied] = useState<{ id: string; props: object; from: string }>();
  useEffect(() => setDenied(undefined), [sel.map((b) => b.id).join()]);
  const sig = (b: Block) => JSON.stringify([b.props, b.y]);
  const picked = (id: string, props?: object) => {
    const b = sel.find((x) => x.id === id);
    return b && props ? ({ ...b, props: { ...b.props, ...props } } as Block) : b;
  };
  // `back` puts a number back that was stored before, with the height the block had then, so no check refuses it.
  // Returns false when the change is refused.
  const grows = (type: Block["type"], props: object, key?: string, back?: number): boolean => {
    if (back !== undefined) {
      const b = sel.find((x) => x.type === type)!;
      style(type, props, key);
      place([[b.id, tall(b, back)]], key);
      setDenied((d) => d && { ...d, from: sig(picked(d.id, props)!) });
      return true;
    }
    const off = sel.filter((b) => b.type === type).find((b) => pastPaper(b, { ...b, props: { ...b.props, ...props } } as Block, H));
    if (off) setDenied({ id: off.id, props, from: sig(off) });
    else {
      setDenied(undefined);
      style(type, props, key);
    }
    return !off;
  };
  const refusedBlock = denied && picked(denied.id);
  const paperHint = !!denied && !!refusedBlock && sig(refusedBlock) === denied.from && pastPaper(refusedBlock, { ...refusedBlock, props: { ...refusedBlock.props, ...denied.props } } as Block, H);
  const wall = sel.length === 1 && sel[0].type === "zahlenmauer" ? sel[0] : undefined;
  const haus = sel.length === 1 && sel[0].type === "zahlenhaus" ? sel[0] : undefined;
  const kette = sel.length === 1 && sel[0].type === "zahlenkette" ? sel[0] : undefined;
  const pfeil = sel.length === 1 && sel[0].type === "pfeilbild" ? sel[0] : undefined;
  const opfeld = sel.length === 1 && sel[0].type === "operatorfeld" ? sel[0] : undefined;
  const rad = sel.length === 1 && sel[0].type === "rechenrad" ? sel[0] : undefined;
  const rtab = sel.length === 1 && sel[0].type === "rechentabelle" ? sel[0] : undefined;
  const magisch = sel.length === 1 && sel[0].type === "magischesquadrat" ? sel[0] : undefined;
  const malq = sel.length === 1 && sel[0].type === "malquadrat" ? sel[0] : undefined;
  const zerl = sel.length === 1 && sel[0].type === "zerlegungsfeld" ? sel[0] : undefined;
  const halb = sel.length === 1 && sel[0].type === "halbschriftlich" ? sel[0] : undefined;
  const zehn = sel.length === 1 && sel[0].type === "zehnerfeld" ? sel[0] : undefined;
  const dreieck = sel.length === 1 && sel[0].type === "rechendreieck" ? sel[0] : undefined;
  const strahl = sel.length === 1 && sel[0].type === "zahlenstrahl" ? sel[0] : undefined;
  const feld = sel.length === 1 && sel[0].type === "hunderterfeld" ? sel[0] : undefined;
  const uhr = sel.length === 1 && sel[0].type === "uhr" ? sel[0] : undefined;
  const skb = sel.length === 1 && sel[0].type === "selbstkontrolle" ? sel[0] : undefined;
  // A maths block's height follows its exercises when they need more or less room than before. A change that would
  // push it past the page's foot is refused: the PDF would cut what hangs below.
  // `key` makes the style and the height one undo step.
  const calc = (props: MathsProps, key = "maths") => {
    if (overFoot(maths!, props, H)) return false;
    style("maths", props, key);
    if (mathsHeight(props) !== mathsHeight(maths!.props)) place([[maths!.id, tall(maths!, mathsHeight(props))]], key);
    return true;
  };
  return { paperHint, refusedType: refusedBlock?.type, maths, suchsel, wall, haus, kette, pfeil, opfeld, rad, rtab, magisch, malq, zerl, halb, zehn, dreieck, strahl, feld, uhr, skb, calc, grows };
}

export function SchoolPanels({
  maths, suchsel, wall, haus, kette, pfeil, opfeld, rad, rtab, magisch, malq, zerl, halb, zehn, dreieck, strahl, feld, uhr, skb, calc, grows, style, doc, words, owe, H,
}: ReturnType<typeof useSchools> & {
  style: (type: Block["type"], props: object, key?: string, only?: string[]) => void;
  doc: Doc;
  words: string[];
  owe: (entry: Owed) => void;
  H: number;
}) {
  return (
    <>
      {maths && <Maths key={maths.id} block={maths} apply={calc} foot={H} owe={owe} />}
      {suchsel && <Suchsel key={suchsel.id} block={suchsel} words={words} apply={(props, key) => style("suchsel", props, key)} />}
      {wall && <Zahlenmauer key={wall.id} block={wall} apply={(props, key) => grows("zahlenmauer", props, key)} />}
      {haus && <Zahlenhaus key={haus.id} block={haus} apply={(props, key) => grows("zahlenhaus", props, key)} />}
      {kette && <Zahlenkette key={kette.id} block={kette} apply={(props, key) => grows("zahlenkette", props, key)} />}
      {pfeil && <Pfeilbild key={pfeil.id} block={pfeil} apply={(props, key) => grows("pfeilbild", props, key)} />}
      {opfeld && <Operatorfeld key={opfeld.id} block={opfeld} apply={(props, key) => grows("operatorfeld", props, key)} />}
      {rad && <Rechenrad key={rad.id} block={rad} apply={(props, key) => grows("rechenrad", props, key)} />}
      {rtab && <Rechentabelle key={rtab.id} block={rtab} apply={(props, key) => grows("rechentabelle", props, key)} />}
      {magisch && <MagischesQuadrat key={magisch.id} block={magisch} apply={(props, key) => grows("magischesquadrat", props, key)} />}
      {malq && <Malquadrat key={malq.id} block={malq} apply={(props, key) => grows("malquadrat", props, key)} />}
      {zerl && <Zerlegungsfeld key={zerl.id} block={zerl} apply={(props, key) => grows("zerlegungsfeld", props, key)} />}
      {halb && <Halbschriftlich key={halb.id} block={halb} apply={(props, key) => grows("halbschriftlich", props, key)} />}
      {zehn && <Zehnerfeld key={zehn.id} block={zehn} apply={(props, key) => grows("zehnerfeld", props, key)} />}
      {dreieck && <Rechendreieck key={dreieck.id} block={dreieck} apply={(props, key) => grows("rechendreieck", props, key)} />}
      {strahl && <Zahlenstrahl key={strahl.id} block={strahl} apply={(props, key) => style("zahlenstrahl", props, key)} />}
      {feld && <Hunderterfeld key={feld.id} block={feld} apply={(props, key) => style("hunderterfeld", props, key)} />}
      {uhr && <Uhr key={uhr.id} block={uhr} apply={(props, key, back) => grows("uhr", props, key, back)} />}
      {skb && <Selbstkontrolle key={skb.id} block={skb} doc={doc} apply={(props, key) => style("selbstkontrolle", props, key)} />}
    </>
  );
}
