"""Checks a sheet document against sheet.schema.json and says what to fix in plain words."""

import json
import logging
from pathlib import Path

from fastapi import HTTPException
from jsonschema import Draft7Validator

log = logging.getLogger(__name__)
SCHEMA = json.loads((Path(__file__).parent / "sheet.schema.json").read_text())
VALIDATOR = Draft7Validator(SCHEMA)
WORDS = {
    "string": "a string",
    "number": "a number",
    "integer": "a whole number",
    "boolean": "a yes or no",
    "array": "a list",
    "object": "an object",
    "null": "nothing",
}


def kind(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return {str: "string", list: "array", dict: "object"}[type(value)]


def where(path: list) -> str:
    text = ""
    for key in path:
        text += f"[{key}]" if isinstance(key, int) else f".{key}" if text else key
    return text or "doc"


def verdict(error) -> str:
    schema, got = error.schema, error.instance
    if error.validator in ("minimum", "maximum"):
        if "minimum" in schema and "maximum" in schema:
            return f"must be {schema['minimum']} to {schema['maximum']}, got {got}"
        if "minimum" in schema:
            return f"must be at least {schema['minimum']}, got {got}"
        return f"must be at most {schema['maximum']}, got {got}"
    if error.validator == "enum":
        options = ", ".join(f"'{option}'" for option in schema["enum"])
        return f"must be one of {options}, got '{got}'"
    if error.validator == "type":
        wanted = (
            [error.validator_value]
            if isinstance(error.validator_value, str)
            else error.validator_value
        )
        return f"must be {' or '.join(WORDS[w] for w in wanted)}, got {WORDS[kind(got)]}"
    return error.message


def items(error) -> list[tuple[list, str]]:
    """The path and the fix for each problem one error stands for."""
    path = list(error.absolute_path)
    if error.validator == "required":
        return [
            ([*path, name], "missing, add it")
            for name in error.validator_value
            if name not in error.instance
        ]
    if error.validator == "additionalProperties":
        known = error.schema.get("properties", {})
        return [
            ([*path, name], "unknown field, remove it")
            for name in error.instance
            if name not in known
        ]
    return [(path, verdict(error))]


def faults(doc: dict) -> list[tuple[list, str, bool]]:
    """Each fault's path, its text, and whether it breaks the sheet, ordered by path."""
    found = {}
    for error in VALIDATOR.iter_errors(doc):
        for path, text in items(error):
            key = tuple((0, k) if isinstance(k, int) else (1, k) for k in path)
            found.setdefault(f"{where(path)}: {text}", (key, path, breaks(error, path)))
    ordered = sorted(found.items(), key=lambda item: item[1][0])
    return [(path, text, broken) for text, (_, path, broken) in ordered]


def problems(doc: dict) -> list[str]:
    """Every fault in the doc against the whole schema, the first ten by path. None when right."""
    return [text for _, text, _ in faults(doc)][:10]


# What a block must have for the editor to open the sheet: the rest of it, the editor draws from
# its defaults where a value is wrong or missing, and saves back as it was.
SKELETON = {"id", "type", "x", "y", "w", "h", "props"}


def breaks(error, path: list) -> bool:
    """Whether the editor cannot open a sheet with this fault: the pages, their blocks, and each
    block's place, id and type must be there and of their type. A value it does not know, or
    out of range, it draws as the default; a block of a type it does not know as a plain one."""
    if error.validator not in ("type", "required"):
        return False
    shape = ["pages", int, "blocks", int]
    if len(path) > len(shape) + 1:
        return False
    for key, want in zip(path, shape, strict=False):
        if not isinstance(key, int) if want is int else key != want:
            return False
    return len(path) <= len(shape) or path[-1] in SKELETON


# What a block of a type must have for the page to draw it: a prop left out is filled with this.
NEEDED = {
    "text": {"text": ""},
    "shape": {"text": ""},
    "maths": {"exercises": []},
    "table": {"cells": [[""]], "cols": [1]},
}


def mended(doc: dict) -> dict:
    """The doc as the page draws it: a copy with each wrong prop of a block cut, and the props the
    page cannot draw without filled in. The stored doc keeps its wrong props. A doc with no fault,
    or one from before pages, comes back as it is."""
    found = faults(doc)
    if "pages" not in doc or not found:
        return doc
    # The props with a fault, by page, block and name.
    cut = {
        (path[1], path[3], path[5]) for path, _, _ in found if len(path) >= 6 and path[4] == "props"
    }
    mend = json.loads(json.dumps(doc))
    for i, page in enumerate(mend["pages"]):
        for j, block in enumerate(page.get("blocks", [])):
            props = block.get("props", {})
            for name in [name for (pi, pj, name) in cut if (pi, pj) == (i, j)]:
                props.pop(name, None)
            for name, value in NEEDED.get(block.get("type"), {}).items():
                props.setdefault(name, value)
    return mend


def as_pages(doc: dict) -> dict:
    """A sheet from before pages holds its blocks at the top; the editor reads them as one page."""
    if "pages" not in doc and isinstance(doc.get("blocks"), list):
        doc = {**doc, "pages": [{"blocks": doc["blocks"]}]}
        del doc["blocks"]
    return doc


def refuse_any_fault(doc: dict) -> None:
    """Refuses a doc with any fault of the whole schema, for a save that asks for it."""
    found = problems(as_pages(doc))
    if found:
        raise HTTPException(422, detail={"problems": found})


def check(doc: dict) -> None:
    """Refuses a doc the editor could not open, and names what to fix. Anything else it stores
    and logs: a sheet the editor opened saves back as it is, whatever an older build wrote."""
    doc = as_pages(doc)
    # JSON has no NaN: stored, it comes back as null, which no later save gets past.
    try:
        json.dumps(doc, allow_nan=False)
    except ValueError:
        raise HTTPException(
            422, detail={"problems": ["doc: holds NaN or Infinity, write a finite number"]}
        ) from None
    found = faults(doc)
    broken = [text for _, text, broke in found if broke][:10]
    if broken:
        raise HTTPException(422, detail={"problems": broken})
    if found:
        log.warning(
            "sheet saved with %d faults, such as %s", len(found), [t for _, t, _ in found[:3]]
        )
