// A font menu in FONT_GROUPS' order, each font shown in its own face.
import { useEffect, useRef, useState } from "react";
import { FONT_GROUPS, FONTS, fontOf, type Font } from "../../sheet";

// A font menu in FONT_GROUPS' order, each font shown in its own face. The native select keeps the value and the keys;
// its list is ours, because macOS and iPadOS draw a native list in the system font.
const FONT_KEYS = FONT_GROUPS.flatMap(([, fonts]) => fonts) as readonly string[];
// The faces load when the pointer or the focus first comes to a font menu, so a name shows at once when its list
// opens. Not before: each face that comes measures the bows of every block anew. A face that fails shows its fallback.
let preloaded = false;
const preload = () => {
  if (preloaded) return;
  preloaded = true;
  for (const font of FONT_KEYS) document.fonts.load(`16px "${FONTS[font as Font][1]}"`).catch(() => {});
};
export function FontSelect({ label, value: stored, unknown, onChange }: { label: string; value: unknown; unknown?: string; onChange: (font: string) => void }) {
  // A font nobody knows shows as Druckschrift, the font it draws in.
  const value = fontOf(stored);
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const wrap = useRef<HTMLDivElement>(null);
  const select = useRef<HTMLSelectElement>(null);
  // Where the finger came down, to tell a tap from a swipe.
  const touch = useRef<{ x: number; y: number } | undefined>(undefined);
  // The faces load now, so a name shows at once when the list opens. A face that fails shows its fallback.
  // A press outside the select and the list shuts the list with no change, and goes on to the page, as a press beside
  // the browser's own list does. It is heard first, so a press that the desk keeps to itself shuts the list too.
  useEffect(() => {
    if (!open) return;
    const outside = (e: PointerEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    addEventListener("pointerdown", outside, true);
    return () => removeEventListener("pointerdown", outside, true);
  }, [open]);
  const show = () => {
    preload();
    setHi(Math.max(0, FONT_KEYS.indexOf(value)));
    setOpen(true);
  };
  const pick = (font: string) => {
    setOpen(false);
    select.current?.focus();
    if (font !== value) onChange(font);
  };
  const toggle = () => (open ? setOpen(false) : show());
  // The keys of the closed select step through the fonts; the keys of the open list move and pick.
  const key = (e: React.KeyboardEvent<HTMLSelectElement>) => {
    const step = e.key === "ArrowDown" ? 1 : e.key === "ArrowUp" ? -1 : 0;
    if (!open) {
      // Enter is not one of them: on a closed menu it gives the keys back to the sheet.
      if ([" ", "F4"].includes(e.key) || (e.altKey && e.key === "ArrowDown")) {
        // The panel's own keys stay out: the list keeps the keyup too.
        e.preventDefault();
        e.stopPropagation();
        show();
      } else if (step && !e.altKey) {
        e.preventDefault();
        const next = FONT_KEYS[Math.min(FONT_KEYS.length - 1, Math.max(0, FONT_KEYS.indexOf(value) + step))];
        if (next !== value) onChange(next);
      }
      return;
    }
    if (e.key === "Tab") {
      setOpen(false);
      return;
    }
    // Every other key is the list's: the sheet and the drawer do not hear of it.
    e.preventDefault();
    e.stopPropagation();
    if (step) {
      setHi((h) => Math.min(FONT_KEYS.length - 1, Math.max(0, h + step)));
    } else if (["Home", "PageUp"].includes(e.key)) {
      setHi(0);
    } else if (["End", "PageDown"].includes(e.key)) {
      setHi(FONT_KEYS.length - 1);
    } else if (e.key === "Enter" || e.key === " ") {
      pick(FONT_KEYS[hi]);
    } else if (e.key === "Escape") {
      // The drawer stays open.
      setOpen(false);
    } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
      // A letter moves the highlight to the next font whose name starts with it, wrapping round.
      const letter = e.key.toLocaleLowerCase("de");
      const after = [...FONT_KEYS.slice(hi + 1), ...FONT_KEYS.slice(0, hi + 1)];
      const next = after.find((font) => FONTS[font as Font][0].toLocaleLowerCase("de").startsWith(letter));
      if (next) setHi(FONT_KEYS.indexOf(next));
    }
  };
  return (
    <>
      <div className="fontsel" ref={wrap}>
        <select
          ref={select}
          aria-label={label}
          value={value}
          style={{ fontFamily: FONTS[value][1] }}
          onChange={(e) => onChange(e.target.value)}
          onMouseDown={(e) => {
            if (e.button !== 0) return;
            e.preventDefault();
            select.current?.focus();
            toggle();
          }}
          data-open={open || undefined}
          onTouchStart={(e) => {
            const t = e.touches[0];
            touch.current = { x: t.clientX, y: t.clientY };
          }}
          onTouchEnd={(e) => {
            // A finger that moved is a scroll of the drawer, and opens nothing.
            const t = e.changedTouches[0];
            const start = touch.current;
            if (!t || !start || Math.hypot(t.clientX - start.x, t.clientY - start.y) >= 10) return;
            e.preventDefault();
            select.current?.focus();
            toggle();
          }}
          onKeyDown={key}
          onPointerEnter={preload}
          onFocus={preload}
        >
          {FONT_GROUPS.map(([group, fonts]) => (
            <optgroup key={group} label={group}>
              {fonts.map((font) => (
                <option key={font} value={font} style={{ fontFamily: FONTS[font][1] }}>
                  {FONTS[font][0]}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        {open && (
          <div role="listbox" aria-label={`Liste: ${label}`} className="fontlist">
            {FONT_GROUPS.map(([group, fonts]) => (
              <div role="group" aria-label={group} key={group}>
                <div role="heading" aria-level={3} className="fontgroup">
                  {group}
                </div>
                {fonts.map((font) => (
                  <div
                    role="option"
                    key={font}
                    aria-selected={font === value}
                    className={FONT_KEYS[hi] === font ? "hi" : undefined}
                    style={{ fontFamily: `${FONTS[font][1]}, Andika, sans-serif` }}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => pick(font)}
                  >
                    {FONTS[font][0]}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
      {unknown && (
        <p className="hint">
          Die Schrift „{unknown}“ kennt Blattomat nicht: Der Block druckt in Druckschrift.
          <button onClick={() => onChange("andika")}>In Druckschrift setzen</button>
        </p>
      )}
    </>
  );
}

// The first font of the picked blocks that the app does not know, if one holds one.
export const unknownFont = (fonts: unknown[]) => fonts.find((f): f is string => typeof f === "string" && !Object.hasOwn(FONTS, f));
