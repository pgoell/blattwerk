// A bar button, and the name it keeps inside the window.
import type { ButtonHTMLAttributes, PointerEvent } from "react";
import type { LucideIcon } from "lucide-react";

// The name of a button at a row's end would poke out of the window, or of the panel that cuts it off:
// it shifts to stay 4 px inside.
export function holdName(e: PointerEvent<HTMLElement>, within?: Element) {
  const on = (e.target as Element).closest(".ib");
  if (!on) return;
  const name = getComputedStyle(on, "::after");
  // No name hangs there where the pointer is no mouse, and none on a button with its name beside it.
  if (name.position !== "absolute") return;
  const half = (parseFloat(name.width) + parseFloat(name.paddingLeft) + parseFloat(name.paddingRight)) / 2;
  const { left, width } = on.getBoundingClientRect();
  const middle = left + width / 2;
  // A panel shows what lies inside its border and its scrollbar.
  const from = within ? within.getBoundingClientRect().left + within.clientLeft : 0;
  const to = within ? from + within.clientWidth : innerWidth;
  const shift = Math.max(from + 4 + half - middle, 0) + Math.min(to - 4 - half - middle, 0);
  e.currentTarget.style.setProperty("--shift", `${shift}px`);
}

// A button that is its icon; the name shows when the pointer rests on it.
export function Tool({ icon: Icon, label, className = "", ...rest }: { icon: LucideIcon; label: string } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button aria-label={label} {...rest} className={`ib ${className}`}>
      <Icon size={16} aria-hidden />
    </button>
  );
}
