"""Variants: the sheet with other tasks, from the stored seeds and a letter. Nothing is stored."""

import copy
import zlib

from pydantic import ValidationError

from blattwerk.maths import Settings, generate

LETTERS = "ABCD"


def derived(seed: int, letter: str) -> int:
    """The seed of a variant: from the stored seed and the letter, the same on every run."""
    return zlib.crc32(f"{seed}:{letter}".encode()) % 2147483647 + 1


def whole(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def vary(doc: dict, letter: str) -> tuple[dict, list[dict]]:
    """The document as variant `letter` prints it, and the blocks that variant cannot fill."""
    if letter == "A":
        return doc, []
    doc = copy.deepcopy(doc)
    short = []
    # A client wrote the document, so any part may be missing or of another kind.
    pages = doc.get("pages", [doc])
    for n, page in enumerate(pages if isinstance(pages, list) else [], start=1):
        blocks = page.get("blocks") if isinstance(page, dict) else None
        for block in blocks if isinstance(blocks, list) else []:
            props = block.get("props") if isinstance(block, dict) else None
            if not isinstance(props, dict):
                continue
            kind = block.get("type")
            if kind == "maths" and whole(props.get("seed")):
                stored = props.get("exercises")
                new = derived(props["seed"], letter)
                try:
                    made = generate(Settings.model_validate({**props, "seed": new}))
                except ValidationError:
                    made = None
                if made is None or (
                    isinstance(stored, list) and len(made["exercises"]) < len(stored)
                ):
                    short.append({"page": n, "id": block.get("id"), "type": "maths"})
                    continue
                props["seed"] = new
                props["exercises"] = made["exercises"]
                props["loosen"] = made["loosen"]
            elif kind == "suchsel" and whole(props.get("seed")):
                props["seed"] = derived(props["seed"], letter)
            elif kind in ("text", "shape"):
                for key in ("mix", "bank", "holeSeed"):
                    if whole(props.get(key)):
                        props[key] = derived(props[key], letter)
            elif kind == "table" and whole(props.get("bank")):
                props["bank"] = derived(props["bank"], letter)
    return doc, short
