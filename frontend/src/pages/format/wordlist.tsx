// The field of the sheet's Lernwörter, as every block that shows them has it in its panel.
import { useEffect, useRef, type RefObject } from "react";
import type { Doc } from "../../sheet";
import { pasted } from "../../words";

// What a panel needs to show and change the sheet's list: `write` takes the field's whole text, a word to a line, and
// `crowded` is how many words the fullest Lineatur of the sheet cannot show. While `aim` is set the field takes the
// focus as it appears, once.
export type Listing = { write: (value: string) => void; crowded: number; aim: RefObject<boolean> };

// The sheet has one list, so each block that shows it has the same field: a word typed here reaches all of them.
// `short` is how many words the picked Lineatur cannot show; without it the sheet's fullest Lineatur is said.
export function WordList({ doc, listing, short = 0 }: { doc: Doc; listing: Listing; short?: number }) {
  const field = useRef<HTMLTextAreaElement>(null);
  // The caret goes behind a paste once the paste is drawn, as React sets the value only then.
  const caretAt = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (caretAt.current === undefined) return;
    field.current?.setSelectionRange(caretAt.current, caretAt.current);
    caretAt.current = undefined;
  });
  useEffect(() => {
    if (!listing.aim.current) return;
    listing.aim.current = false;
    field.current?.focus();
  });
  return (
    <>
      <textarea
        aria-label="Lernwörter"
        className="wordlist"
        rows={8}
        // The browser's check knows no German on most machines and marks every word (#580).
        spellCheck={false}
        placeholder="Ein Wort pro Zeile"
        ref={field}
        value={Array.isArray(doc.words) ? doc.words.filter((w) => typeof w === "string").join("\n") : ""}
        onChange={(e) => listing.write(e.target.value)}
        // A paste brings its words one to a line, in place of what is picked in the field.
        onPaste={(e) => {
          e.preventDefault();
          const el = e.currentTarget;
          const [from, to] = [el.selectionStart, el.selectionEnd];
          const got = pasted(e.clipboardData.getData("text/plain"));
          // A paste that holds no word changes nothing.
          if (!got.length) return;
          const [before, after] = [el.value.slice(0, from), el.value.slice(to)];
          // The pasted words keep to lines of their own: a word before or behind them is not joined to one.
          const words = (/[^\n]$/.test(before) ? "\n" : "") + got.join("\n") + (/^[^\n]/.test(after) ? "\n" : "");
          caretAt.current = from + words.length;
          listing.write(before + words + after);
        }}
      />
      <p className="hint">Ein Wort pro Zeile. Die Liste gilt für das ganze Blatt.</p>
      {short > 0 ? (
        <p className="hint" role="status">
          {short === 1 ? "1 Wort passt nicht in die Zeilen." : `${short} Wörter passen nicht in die Zeilen.`}
        </p>
      ) : (
        listing.crowded > 0 && (
          <p className="hint" role="status">
            {listing.crowded === 1 ? "In einer Lineatur passt 1 Wort nicht in die Zeilen." : `In einer Lineatur passen ${listing.crowded} Wörter nicht in die Zeilen.`}
          </p>
        )
      )}
    </>
  );
}
