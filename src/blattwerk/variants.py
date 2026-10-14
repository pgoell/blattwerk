"""Variants: the sheet with other tasks, from the stored seeds and a letter. Nothing is stored.

A written variant that needs more room than the stored block takes a later try of its seed.
"""

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


def room(exercises: list) -> tuple[int, int]:
    """The most rows and columns of the written grids of some exercises."""
    grids = [e.get("grid") if isinstance(e, dict) else None for e in exercises]
    grids = [g for g in grids if isinstance(g, dict)]
    rows = [g["rows"] for g in grids if whole(g.get("rows"))]
    cols = [g["cols"] for g in grids if whole(g.get("cols"))]
    return max(rows, default=0), max(cols, default=0)


def fits(made: list, stored) -> bool:
    """Whether the variant's tasks fill the stored block: as many, and no bigger grids."""
    if not isinstance(stored, list):
        return True
    if len(made) < len(stored):
        return False
    if not all(isinstance(e, dict) for e in stored):
        return True
    return all(a <= b for a, b in zip(room(made), room(stored), strict=True))


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
                made = None
                # Try 0 is the plain variant; later tries only when the grid does not fit the block.
                for k in range(100):
                    new = derived(props["seed"], letter if k == 0 else f"{letter}{k}")
                    try:
                        made = generate(Settings.model_validate({**props, "seed": new}))
                    except ValidationError:
                        made = None
                        break
                    if fits(made["exercises"], stored):
                        break
                    few = isinstance(stored, list) and len(made["exercises"]) < len(stored)
                    made = None
                    # Too few tasks is the limits' doing, and no other seed mends that.
                    if few:
                        break
                if made is None:
                    short.append({"page": n, "id": block.get("id"), "type": "maths"})
                    continue
                props["seed"] = new
                props["exercises"] = made["exercises"]
                props["loosen"] = made["loosen"]
            elif kind in ("suchsel", "zahlenmauer") and whole(props.get("seed")):
                props["seed"] = derived(props["seed"], letter)
            elif kind in ("text", "shape"):
                for key in ("mix", "bank", "holeSeed"):
                    if whole(props.get(key)):
                        props[key] = derived(props[key], letter)
            elif kind == "table" and whole(props.get("bank")):
                props["bank"] = derived(props["bank"], letter)
    return doc, short
