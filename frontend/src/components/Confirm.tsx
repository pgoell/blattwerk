// The app's own question before a step that takes something away: a modal dialog with the step's name on its
// button. Escape, "Abbrechen" and a click beside it leave everything as it is.
import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useBackdrop } from "./useBackdrop";

// `danger` marks a step that cannot be taken back.
type Props = { title: string; yes: string; danger?: boolean; children?: ReactNode; onYes: () => void; onClose: () => void };

export default function Confirm({ title, yes, danger, children, onYes, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  // What had the focus gets it back, as after a menu.
  useEffect(() => {
    const from = document.activeElement as HTMLElement | null;
    ref.current!.showModal();
    return () => from?.focus?.();
  }, []);
  const backdrop = useBackdrop(ref);
  // Under the body, not where it was asked: a panel's own colours do not reach it.
  return createPortal(
    <dialog ref={ref} className="ask confirm" aria-labelledby={id} onClose={onClose} {...backdrop}>
      <h1 id={id}>{title}</h1>
      {children}
      <div className="row">
        {/* The first in the dialog, so the focus starts on the way out. */}
        <button type="button" className="plain" onClick={() => ref.current?.close()}>
          Abbrechen
        </button>
        <button
          type="button"
          className={danger ? "danger" : "primary"}
          onClick={() => {
            ref.current?.close();
            onYes();
          }}
        >
          {yes}
        </button>
      </div>
    </dialog>,
    document.body,
  );
}
