import { useRef, type RefObject } from "react";

type At = { target: EventTarget | null; clientX: number; clientY: number };

// A point beside the dialog's box: the dialog is the target, and the point lies outside its box.
export function beside(dialog: HTMLDialogElement, e: At) {
  const box = dialog.getBoundingClientRect();
  return e.target === dialog && (e.clientX < box.left || e.clientX > box.right || e.clientY < box.top || e.clientY > box.bottom);
}

// A click on the backdrop shuts the dialog, when the press began there too: a drag that ends outside does not.
// `shut` takes the same path as Escape, so the focus goes back.
export function useBackdrop(ref: RefObject<HTMLDialogElement | null>, shut = () => ref.current?.close(), busy = false) {
  const pressed = useRef(false);
  return {
    onPointerDown: (e: At & { currentTarget: HTMLDialogElement }) => {
      pressed.current = beside(e.currentTarget, e);
    },
    onClick: (e: At & { currentTarget: HTMLDialogElement }) => {
      if (pressed.current && !busy && beside(e.currentTarget, e)) shut();
    },
  };
}
