// What the format panel says when a block does not fit the page or lies over another.
import { MARGIN, boxed, lowest, rightmost, rowsNeeded, rowsOf, type Block, type Doc } from "../../sheet";

// The hints for a maths block that grows past the margin's foot or the paper's edge, by type: a name sentence, then the take-away.
const FOOT: Record<string, [string, string]> = {
  zahlenhaus: ["Das Zahlenhaus ragt unten über den Rand.", "Nimm weniger Häuser oder Stockwerke oder schiebe es nach oben."],
  zahlenkette: ["Die Zahlenkette ragt unten über den Rand.", "Nimm weniger Ketten oder Ringe oder schiebe sie nach oben."],
  pfeilbild: ["Das Pfeilbild ragt unten über den Rand.", "Nimm weniger Pfeilbilder oder Kästchen oder schiebe es nach oben."],
  operatorfeld: ["Das Operatorfeld ragt unten über den Rand.", "Nimm weniger Operatorfelder oder schiebe es nach oben."],
  rechenrad: ["Das Rechenrad ragt unten über den Rand.", "Nimm weniger Rechenräder oder Ringe oder schiebe es nach oben."],
  rechentabelle: ["Die Rechentabelle ragt unten über den Rand.", "Nimm weniger Tabellen oder Zeilen oder schiebe sie nach oben."],
  magischesquadrat: ["Das Magische Quadrat ragt unten über den Rand.", "Nimm weniger Quadrate oder schiebe es nach oben."],
  malquadrat: ["Das Malquadrat ragt unten über den Rand.", "Nimm weniger Malquadrate oder schiebe es nach oben."],
  zerlegungsfeld: ["Das Zerlegungsfeld ragt unten über den Rand.", "Nimm weniger Aufgaben oder schiebe es nach oben."],
  halbschriftlich: ["Der Block Halbschriftlich rechnen ragt unten über den Rand.", "Nimm weniger Aufgaben oder schiebe ihn nach oben."],
  zehnerfeld: ["Das Zehnerfeld ragt unten über den Rand.", "Nimm weniger Aufgaben oder schiebe es nach oben."],
  zahlenmauer: ["Die Zahlenmauer ragt unten über den Rand.", "Nimm weniger Mauern oder Grundsteine oder schiebe sie nach oben."],
  rechendreieck: ["Das Rechendreieck ragt unten über den Rand.", "Nimm weniger Dreiecke oder schiebe es nach oben."],
  uhr: ["Die Uhr ragt unten über den Rand.", "Nimm weniger Uhren oder schiebe sie nach oben."],
};

export function Notices({
  sel, doc, full, cramped, held, W, H, paper, refused,
}: {
  sel: Block[];
  doc: Doc;
  full: string[];
  cramped: string[];
  held: string[];
  W: number;
  H: number;
  paper: boolean;
  refused?: string;
}) {
  const rulings = sel.filter((b): b is Extract<Block, { type: "ruling" }> => b.type === "ruling");
  // A picked Lineatur that lies over a block with text, outside its group, covers that text: nothing moves, so the panel says so.
  const page = doc.pages.find((p) => p.blocks.some((b) => b.id === sel[0]?.id))?.blocks ?? [];
  const carries = (b: Block) => b.type === "table" || b.type === "maths" || b.type === "ruling" || !!boxed(b)?.text;
  const covers = rulings.some((r) =>
    page.some(
      (b) =>
        b.id !== r.id &&
        carries(b) &&
        !b.group?.some((g) => r.group?.includes(g)) &&
        r.x < b.x + b.w && b.x < r.x + r.w && r.y < b.y + b.h && b.y < r.y + r.h,
    ),
  );
  // A picked Zahlenmauer that grows over another block, outside its group, covers it: nothing moves, as for a
  // Lineatur. A shape without text does not count, being a frame or a mark.
  const wallCovers = sel.some(
    (z) =>
      z.type === "zahlenmauer" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );

  const houseCovers = sel.some(
    (z) =>
      z.type === "zahlenhaus" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );

  const ketteCovers = sel.some(
    (z) =>
      z.type === "zahlenkette" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );

  const pfeilCovers = sel.some(
    (z) =>
      z.type === "pfeilbild" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const radCovers = sel.some(
    (z) =>
      z.type === "rechenrad" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const tabelleCovers = sel.some(
    (z) =>
      z.type === "rechentabelle" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const magischCovers = sel.some(
    (z) =>
      z.type === "magischesquadrat" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const malqCovers = sel.some(
    (z) =>
      z.type === "malquadrat" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const zerlCovers = sel.some(
    (z) =>
      z.type === "zerlegungsfeld" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const halbCovers = sel.some(
    (z) =>
      z.type === "halbschriftlich" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const zehnCovers = sel.some(
    (z) =>
      z.type === "zehnerfeld" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const opfeldCovers = sel.some(
    (z) =>
      z.type === "operatorfeld" &&
      page.some(
        (b) =>
          b.id !== z.id &&
          !(b.type === "shape" && !boxed(b)?.text) &&
          !b.group?.some((g) => z.group?.includes(g)) &&
          z.x < b.x + b.w && b.x < z.x + z.w && z.y < b.y + b.h && b.y < z.y + z.h,
      ),
  );
  const paperHint = paper;
  const refusedBlock = refused ? { type: refused } : undefined;
  return (
    <>
      {/* A block that hangs over the foot is cut in the PDF: the panel says so first, whatever the block. */}
      {sel.some((b) => lowest(b) > H + 0.01) && (
        <p className="hint warn" role="status" data-foot="over">
          {sel.length > 1 ? "Die Auswahl ragt unten über die Seite hinaus." : "Der Block ragt unten über die Seite hinaus."} Was unter dem Rand steht, wird nicht gedruckt.
        </p>
      )}
      {/* A maths block past the margin's foot says so, where the PDF still prints it whole up to the paper's edge. */}
      {(() => {
        const first = sel.find((b) => FOOT[b.type] && lowest(b) > H - MARGIN + 0.01);
        return first && !sel.some((b) => lowest(b) > H + 0.01) ? (
          <p className="hint warn" role="status" data-foot="haus">
            {FOOT[first.type].join(" ")}
          </p>
        ) : null;
      })()}
      {paperHint && refusedBlock && (
        <p className="hint warn" role="status" data-foot="paper">
          Das passt nicht mehr auf die Seite und wurde nicht übernommen. {FOOT[refusedBlock.type][1]}
        </p>
      )}
      {/* A text that the foot stops from growing says that its last words are cut. */}
      {sel.some((b) => full.includes(b.id)) && (
        <p className="hint warn" role="status" data-foot="full">
          Der Text passt nicht mehr in den Block: er reicht bis an den unteren Rand der Seite. Was nicht hineinpasst, wird nicht gedruckt.
        </p>
      )}
      {/* A shape whose text does not fit where it stands says so, at any place on the page. */}
      {sel.some((b) => cramped.includes(b.id) && !full.includes(b.id)) && (
        <p className="hint warn" role="status" data-shape="full">
          Der Text passt nicht in die Form. Was nicht hineinpasst, wird nicht gedruckt.
        </p>
      )}
      {rulings.some((b) => rowsNeeded(b) > rowsOf(b)) && (
        <p className="hint warn" role="status" data-rows="short">
          Der Text braucht mehr Zeilen, als die Lineatur hat. Was nicht hineinpasst, wird nicht gedruckt.
        </p>
      )}
      {covers && (
        <p className="hint warn" role="status" data-cover="over">
          Die Lineatur liegt über einem anderen Block. Verschiebe ihn oder mache die Lineatur kleiner.
        </p>
      )}
      {wallCovers && (
        <p className="hint warn" role="status" data-cover="wall">
          Die Zahlenmauer liegt über einem anderen Block. Verschiebe ihn oder mache die Zahlenmauer kleiner.
        </p>
      )}
      {houseCovers && (
        <p className="hint warn" role="status" data-cover="haus">
          Das Zahlenhaus liegt über einem anderen Block. Verschiebe ihn oder mache das Zahlenhaus kleiner.
        </p>
      )}
      {ketteCovers && (
        <p className="hint warn" role="status" data-cover="kette">
          Die Zahlenkette liegt über einem anderen Block. Verschiebe ihn oder mache die Zahlenkette kleiner.
        </p>
      )}
      {pfeilCovers && (
        <p className="hint warn" role="status" data-cover="pfeil">
          Das Pfeilbild liegt über einem anderen Block. Verschiebe ihn oder mache das Pfeilbild kleiner.
        </p>
      )}
      {opfeldCovers && (
        <p className="hint warn" role="status" data-cover="operator">
          Das Operatorfeld liegt über einem anderen Block. Verschiebe ihn oder mache das Operatorfeld kleiner.
        </p>
      )}
      {radCovers && (
        <p className="hint warn" role="status" data-cover="rechenrad">
          Das Rechenrad liegt über einem anderen Block. Verschiebe ihn oder mache das Rechenrad kleiner.
        </p>
      )}
      {tabelleCovers && (
        <p className="hint warn" role="status" data-cover="rechentabelle">
          Die Rechentabelle liegt über einem anderen Block. Verschiebe ihn oder mache die Rechentabelle kleiner.
        </p>
      )}
      {malqCovers && (
        <p className="hint warn" role="status" data-cover="malquadrat">
          Das Malquadrat liegt über einem anderen Block. Verschiebe ihn oder mache das Malquadrat kleiner.
        </p>
      )}
      {zerlCovers && (
        <p className="hint warn" role="status" data-cover="zerlegungsfeld">
          Das Zerlegungsfeld liegt über einem anderen Block. Verschiebe ihn oder mache das Zerlegungsfeld kleiner.
        </p>
      )}
      {zehnCovers && (
        <p className="hint warn" role="status" data-cover="zehnerfeld">
          Das Zehnerfeld liegt über einem anderen Block. Verschiebe ihn oder mache das Zehnerfeld kleiner.
        </p>
      )}
      {halbCovers && (
        <p className="hint warn" role="status" data-cover="halbschriftlich">
          Der Block Halbschriftlich rechnen liegt über einem anderen Block. Verschiebe ihn oder mache ihn kleiner.
        </p>
      )}
      {magischCovers && (
        <p className="hint warn" role="status" data-cover="magischesquadrat">
          Das Magische Quadrat liegt über einem anderen Block. Verschiebe ihn oder mache das Magische Quadrat kleiner.
        </p>
      )}
      {/* A shape that a smaller size made, and whose text grew it back, says why it stays as tall as its text. */}
      {sel.some((b) => held.includes(b.id)) && (
        <p className="hint" role="status" data-held="text">
          Der Text braucht diese Höhe. Mit kleinerer Schrift oder kürzerem Text lässt sich die Form kleiner stellen.
        </p>
      )}
      {/* A table that a new column made wider than the page is cut too, at the right edge. */}
      {sel.some((b) => b.type === "table" && rightmost(b) > W + 0.01) && (
        <p className="hint warn" role="status" data-edge="over">
          Die Tabelle ragt rechts über die Seite hinaus. Was neben dem Rand steht, wird nicht gedruckt.
        </p>
      )}
    </>
  );
}
