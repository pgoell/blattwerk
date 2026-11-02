// Extra space between letters (Zeichenabstand). A share of the font size, not a length in mm.

import type { CSSProperties } from "react";
import { fontOf, type Font } from "./look";

// Absent, or anything but a number from above 0 to 1, draws as the font does. A larger number draws as 1.
export function trackingOf(p: { tracking?: unknown }): number {
  const n = typeof p.tracking === "number" && Number.isFinite(p.tracking) ? p.tracking : 0;
  return n > 0 ? Math.min(1, n) : 0;
}

// The scripts whose letters join. Spacing pulls those joins apart. Grundschrift does not join.
const CURSIVE: readonly Font[] = ["va", "sas", "la"];
export const cursive = (font: unknown) => CURSIVE.includes(fontOf(font));

// Puts the share on a text's style. Karo already spaces each letter into its square, and that stays.
export function withTracking(style: CSSProperties, tracking: unknown): CSSProperties {
  const n = trackingOf({ tracking });
  if (!(n > 0) || style.letterSpacing !== undefined) return style;
  return { ...style, letterSpacing: `${n}em` };
}
