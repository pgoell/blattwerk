// The one control for a setting that is on or off: its name on the left, a slider on the right.
import type { ReactNode } from "react";

// The whole row is the button, so a press on the name switches too, Space switches it from the keys, and a press
// with the mouse leaves the focus where it was, as every button of the format panel does. `name` is what a screen
// reader says where the visible words are not enough, or not plain text.
export function Switch({ label, on, onChange, disabled, name, className }: { label: ReactNode; on: boolean | undefined; onChange: (on: boolean) => void; disabled?: boolean; name?: string; className?: string }) {
  return (
    <button
      type="button"
      role="switch"
      className={className ? `sw ${className}` : "sw"}
      aria-checked={!!on}
      aria-label={name ?? (typeof label === "string" ? label : undefined)}
      disabled={disabled}
      onClick={() => onChange(!on)}
    >
      <span>{label}</span>
      <i aria-hidden />
    </button>
  );
}
