// Draws the place colours inside a maths block. A text block never provides them, so its digits stay black.

import { createContext, useContext, type ReactNode } from "react";
import { placeColors, runs, type PlaceColors, type Run } from "../places";
import { Whole } from "./context";

const Ink = createContext<PlaceColors | null>(null);

// The sheet's place colours, around one maths block. Off, or on a block that is not maths, there are none.
export function PlaceScope({ children }: { children: ReactNode }) {
  const colors = placeColors(useContext(Whole));
  return <Ink.Provider value={colors}>{children}</Ink.Provider>;
}

export const usePlaces = () => useContext(Ink);

function partsOf(text: string, colors: PlaceColors | null): Run[] | null {
  const parts = runs(text, colors);
  return parts.some((part) => part.place) ? parts : null;
}

// The text, with each digit of a whole number in its place colour. Without the colours, the text itself.
export function HtmlInk({ text }: { text: string | number }) {
  const parts = partsOf(String(text), usePlaces());
  if (!parts) return <>{text}</>;
  return (
    <>
      {parts.map((part, i) =>
        part.place ? (
          <span key={i} data-place={part.place} style={{ color: part.color }}>{part.text}</span>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </>
  );
}

// The same, as tspans of an svg text. `xs` is one position per character, for a number set one digit to a square.
export function SvgInk({ text, xs }: { text: string | number; xs?: number[] }) {
  const raw = String(text);
  const parts = partsOf(raw, usePlaces());
  if (!parts) return <>{raw}</>;
  if (!xs) {
    return (
      <>
        {parts.map((part, i) => (
          <tspan key={i} data-place={part.place} style={part.color ? { fill: part.color } : undefined}>{part.text}</tspan>
        ))}
      </>
    );
  }
  const glyphs = parts.flatMap((part) => [...part.text].map((ch) => ({ ch, place: part.place, color: part.color })));
  return (
    <>
      {glyphs.map((glyph, i) => (
        <tspan key={i} x={xs[i]} data-place={glyph.place} style={glyph.color ? { fill: glyph.color } : undefined}>{glyph.ch}</tspan>
      ))}
    </>
  );
}
