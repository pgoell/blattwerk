// A Lösungsfeld on the page: the blank always, the text or the picture only in the Lösungen.

import { useContext } from "react";
import { PT } from "../../height";
import { blankMm, sane, shown } from "../../loesungsfeld";
import { uploadAddress } from "../../uploadAddress";
import { Whole } from "../context";
import { HtmlInk } from "../places";
import type { LoesungsfeldBlock } from "../tasks";
import { symbol } from "../text";

export function Loesungsfeld({ block, k, solved }: { block: LoesungsfeldBlock; k: number; solved: boolean }) {
  const doc = useContext(Whole);
  const p = sane(block.props);
  const page = doc.pages.find((pg) => pg.blocks.some((b) => b.id === block.id));
  const peers = (page?.blocks ?? [block]).flatMap((b) => (b.type === "loesungsfeld" ? [sane(b.props)] : []));
  const face = shown(p, solved);
  const mm = blankMm(p, peers.length ? peers : [p]);
  return (
    <div className={`loesungsfeld${solved ? " solved" : ""}`} data-kind={p.kind} data-blank={p.blank} style={{ fontSize: p.size * PT * k }}>
      <span className={`blank ${p.blank}`} style={{ width: mm * k }}>
        {face.text !== undefined && (
          <span className="answer">
            <HtmlInk text={face.text} />
          </span>
        )}
        {face.code && <img className="answer" src={symbol(face.code)} alt="" draggable={false} />}
        {face.upload !== undefined && <img className="answer" src={uploadAddress(face.upload)} alt="" draggable={false} />}
      </span>
    </div>
  );
}
