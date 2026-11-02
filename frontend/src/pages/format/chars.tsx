// The symbol menu in the Schrift section: a fixed set, any Unicode code, and the last ones used.
import { useState } from "react";
import { CHARS, fromCode, remembered, RECENT } from "../../chars";

const KEY = "sonderzeichen";

// What this browser last inserted, newest first. A broken store is an empty list.
function load(): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    if (!Array.isArray(raw)) return [];
    return raw.filter((c): c is string => typeof c === "string" && [...c].length === 1).slice(0, RECENT);
  } catch {
    return [];
  }
}

// `family` is the face the picked text draws in, so a symbol shows as it will on the sheet.
export function Chars({ family, onInsert }: { family: string; onInsert: (ch: string) => void }) {
  const [open, setOpen] = useState(false);
  const [recent, setRecent] = useState(load);
  const [code, setCode] = useState("");
  const glyph = fromCode(code);
  const face = { fontFamily: family };
  const pick = (ch: string) => {
    const next = remembered(recent, ch);
    setRecent(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      // The list still shows for this visit.
    }
    onInsert(ch);
  };
  return (
    <>
      <button type="button" aria-expanded={open} onClick={() => setOpen((now) => !now)}>
        Sonderzeichen
      </button>
      {open && (
        <>
          {recent.length > 0 && (
            <div className="chars" role="group" aria-label="Zuletzt">
              {recent.map((ch) => (
                <button key={ch} type="button" style={face} onClick={() => pick(ch)}>
                  {ch}
                </button>
              ))}
            </div>
          )}
          <div className="chars" role="group" aria-label="Zeichen">
            {CHARS.map(([ch, name]) => (
              <button key={ch} type="button" aria-label={name} title={name} style={face} onClick={() => pick(ch)}>
                {ch}
              </button>
            ))}
          </div>
          <label>
            Unicode
            <input
              aria-label="Unicode"
              placeholder="U+00B7"
              maxLength={8}
              autoComplete="off"
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={(e) => {
                if (e.key !== "Enter" || !glyph) return;
                e.preventDefault();
                pick(glyph);
              }}
            />
          </label>
          <div className="seg">
            <output className="glyph" aria-label="Vorschau" style={face}>{glyph ?? ""}</output>
            <button type="button" aria-label="Zeichen einfügen" disabled={!glyph} onClick={() => glyph && pick(glyph)}>
              Einfügen
            </button>
          </div>
        </>
      )}
    </>
  );
}
