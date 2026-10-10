"""Makes tests/corpus/ from a copy of the live database: every sheet and template, blanked.

    uv run python scripts/corpus.py copy.db tests/corpus/

The repo is public and the sheets are real teachers' work, so a string stays only where its key
is in ALLOW and its value fits the pattern there. Every other string is blanked: a letter turns
into x, a digit into 0, and the rest stays, so a text keeps its length and its line breaks.
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

COLOUR = r"#[0-9a-fA-F]{3,8}|none"
# A counting numbering as components/Numbering.tsx makes it, or a symbol's code as in symbols.ts.
MARK = r"[1a][.)o]?|\([1a]\)|[0-9A-F]{4,5}(-[0-9A-F]{4,5})*"
# The keys whose strings the editor picks from a fixed set or makes itself: see the types in
# frontend/src/sheet.tsx. `kind` is a shape's or a ruling's. An id is a UUID, or a built-in
# template's.
ALLOW = {
    "id": r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}|vorlage-[0-9]+",
    "type": "text|shape|ruling|name|points|symbol|image|maths|table",
    "kind": "rect|rounded|circle|triangle|star|bubble|line|arrow|double|l1|l2|l3|l4|lines|k5|k7",
    "align": "left|center|right",
    "valign": "top|middle|bottom",
    "font": "andika|grund|va|sas|la",
    "list": "bullet|number",
    "dash": "dashed|dotted",
    "from": "nw|ne|sw|se",
    "label": "show|key",
    "color": COLOUR,
    "fill": COLOUR,
    "stroke": COLOUR,
    "line": COLOUR,
    "mark": MARK,
    "numbering": MARK,
    "code": MARK,
    "op": r"[-+*/]",
    "ops": r"[-+*/]",
    "carry": "none|required|either",
    "format": "row|gap|written",
    "hide": "a|b",
}
ALLOW["group"] = ALLOW["id"]
# Where a sheet and where a template keeps its name.
TABLES = {"sheet": "title", "template": "name"}
LIVE = Path.home() / ".local" / "share"


def blanked(text: str) -> str:
    return "".join(
        ("X" if c.isupper() else "x") if c.isalpha() else "0" if c.isdigit() else c for c in text
    )


def kept(key: str, value: str) -> bool:
    return key in ALLOW and re.fullmatch(ALLOW[key], value) is not None


def blank(value, key: str = ""):
    """The value with every string blanked that ALLOW does not keep. A list's key is its items'.

    A picture keeps its place and its cut, and shows upload 0, which no one has.
    """
    if isinstance(value, str):
        return value if kept(key, value) else blanked(value)
    if isinstance(value, list):
        return [blank(item, key) for item in value]
    if isinstance(value, dict):
        made = {k: blank(v, k) for k, v in value.items()}
        if value.get("type") == "image" and isinstance(made.get("props"), dict):
            made["props"] = {k: v for k, v in made["props"].items() if k in ("ratio", "cut")}
            made["props"]["upload"] = 0
        return made
    return value


def strings(value, key: str = ""):
    """Every string in the value, with the key it stands under."""
    if isinstance(value, str):
        yield key, value
    for item in value if isinstance(value, list) else []:
        yield from strings(item, key)
    for k, v in value.items() if isinstance(value, dict) else []:
        yield from strings(v, k)


def rows(con: sqlite3.Connection):
    """Each sheet and template of the database: its file's name, the key of its name, the row."""
    for table, name in TABLES.items():
        found = con.execute(f"SELECT {name}, doc FROM {table}s ORDER BY id")
        for n, (text, doc) in enumerate(found, 1):
            yield f"{table}-{n}.json", name, text, json.loads(doc)


def main(source: str, target: str) -> None:
    path = Path(source).resolve()
    if any(path.is_relative_to(LIVE / name) for name in ("blattwerk", "blattwerk-canary")):
        sys.exit("Not the live data: copy the database elsewhere first.")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    folder = Path(target)
    folder.mkdir(parents=True, exist_ok=True)
    for file, name, text, doc in rows(con):
        made = {name: blanked(text), "doc": blank(doc)}
        (folder / file).write_text(json.dumps(made, indent=1, ensure_ascii=False) + "\n")
        print(file)


if __name__ == "__main__":
    main(*sys.argv[1:])
