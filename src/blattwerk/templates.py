"""Templates: a name and the sheet document to start from. Three are built in."""

import json
from itertools import count
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from blattwerk import pictures
from blattwerk.auth import User
from blattwerk.db import Con, Id
from blattwerk.maths import Settings, generate

router = APIRouter(prefix="/api")


LINE = {"fill": "none", "stroke": "#222222", "strokeWidth": 0.5}
MM_PER_PT = 25.4 / 72
KARO = 5
ids = count(1)


def block(type: str, x: float, y: float, w: float, h: float, props: dict, mark: str = "") -> dict:
    n = next(ids)
    box = {"id": f"vorlage-{n}", "x": x, "y": y, "w": w, "h": h, "z": n, "locked": False}
    return {**box, "type": type, "props": props, **({"mark": mark} if mark else {})}


def heading(y: float, text: str) -> dict:
    return block(
        "text", 15, y, 180, 14, {"text": text, "size": 24, "align": "center", "bold": True}
    )


def shape(kind: str, x: float, y: float, w: float, h: float, **props: str) -> dict:
    return block("shape", x, y, w, h, {"kind": kind, **LINE, **props})


def doc(*pages: list[dict]) -> dict:
    return {
        "pages": [{"blocks": blocks} for blocks in pages],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }


def test_page(first: bool) -> list[dict]:
    """A page of the Klassenarbeit: the name, the points total and two tasks with their points."""
    top = 55 if first else 35
    return [
        block("name", 15, 15, 135, 10, {}),
        block("points", 155, 14, 40, 12, {"max": 60}),
        *([heading(32, "Klassenarbeit")] if first else []),
        *(
            part
            for y in (top, top + (282 - top) / 2)
            for part in (
                block(
                    "text", 25, y, 125, 12, {"text": "Aufgabe", "size": 14, "align": "left"}, "1."
                ),
                block("points", 155, y, 40, 12, {"max": 10}),
            )
        ),
    ]


def maths_height(props: dict) -> float:
    """The height the editor gives a maths block with these exercises (mathsHeight in sheet.tsx)."""
    lines = -(-len(props["exercises"]) // props["columns"])
    if props["format"] == "written":
        rows = max(e.get("grid", {}).get("rows", 0) for e in props["exercises"])
        return max(10, round(lines * (rows + 1) * KARO))
    return max(10, round(lines * props["size"] * MM_PER_PT * 2.4))


def maths_block(y: float, limits: dict) -> dict:
    """A maths block at height y, with exercises made from the limits, with a fixed seed."""
    props = {**limits, **generate(Settings.model_validate(limits)), "columns": 3, "size": 14}
    return block("maths", 15, y, 180, maths_height(props), props)


def maths_page(title: str, *blocks: dict) -> list[dict]:
    return [block("name", 15, 15, 180, 10, {}), heading(32, title), *blocks]


def ruled_page(title: str, props: dict) -> list[dict]:
    return [
        block("name", 15, 15, 180, 10, {}),
        heading(32, title),
        block("ruling", 15, 55, 180, 200, props),
    ]


# Shared by all users. Their ids lie below zero and in no table, so no one can delete them.
BUILT_IN = [
    {
        "id": -1,
        "name": "Arbeitsblatt",
        "group": "Allgemein",
        "doc": doc(
            [
                block("name", 15, 15, 180, 10, {}),
                heading(32, "Überschrift"),
                shape("rounded", 15, 55, 180, 110),
                shape("rounded", 15, 172, 180, 110),
            ]
        ),
    },
    {
        "id": -2,
        "name": "Klassenarbeit",
        "group": "Organisation",
        "doc": doc(*(test_page(n == 0) for n in range(3))),
    },
    {
        "id": -3,
        "name": "Beschriftungsblatt",
        "group": "Allgemein",
        "doc": doc(
            [
                heading(15, "Überschrift"),
                # Where the picture goes. A label is a line to write on and an arrow to the picture.
                shape("rect", 50, 40, 110, 150),
                *(
                    part
                    for y in (70, 115, 160)
                    for part in (
                        shape("line", 15, y, 30, 0),
                        shape("arrow", 45, y, 25, 0),
                        shape("arrow", 140, y, 25, 0, **{"from": "ne"}),
                        shape("line", 165, y, 30, 0),
                    )
                ),
            ]
        ),
    },
    {
        "id": -4,
        "name": "Wochenplan",
        "group": "Organisation",
        "doc": doc(
            [
                block("name", 15, 15, 180, 10, {}),
                heading(32, "Wochenplan"),
                block(
                    "table",
                    15,
                    55,
                    180,
                    140,
                    {
                        "cells": [
                            ["", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"],
                            *(
                                [subject, "", "", "", "", ""]
                                for subject in (
                                    "Deutsch",
                                    "Mathe",
                                    "Sachunterricht",
                                    "Englisch",
                                    "Kunst",
                                    "Sport",
                                )
                            ),
                        ],
                        "cols": [1.6, 1, 1, 1, 1, 1],
                        "size": 14,
                        "align": "center",
                        "line": "#222222",
                        "head": True,
                    },
                ),
            ]
        ),
    },
    {
        "id": -5,
        "name": "Elternbrief",
        "group": "Organisation",
        "doc": doc(
            [
                block("name", 15, 15, 180, 10, {}),
                heading(30, "Grundschule am Wald"),
                block(
                    "text",
                    15,
                    55,
                    180,
                    8,
                    {"text": "Datum: ______________", "size": 12, "align": "right"},
                ),
                block(
                    "text",
                    15,
                    70,
                    180,
                    90,
                    {
                        "text": "Liebe Eltern, bitte lesen Sie diesen Brief und unterschreiben "
                        "Sie den Abschnitt unten. Geben Sie ihn bis Freitag in der Klasse ab. "
                        "Vielen Dank! Ihre Klassenlehrerin",
                        "size": 12,
                        "align": "left",
                    },
                ),
                shape("line", 15, 185, 180, 0, dash="dashed"),
                block("symbol", 15, 179, 12, 12, {"code": "2702"}),
                block(
                    "text",
                    15,
                    195,
                    180,
                    10,
                    {"text": "Ich habe den Elternbrief gelesen.", "size": 12, "align": "left"},
                ),
                block(
                    "text", 15, 232, 90, 8, {"text": "Name des Kindes", "size": 12, "align": "left"}
                ),
                shape("line", 15, 246, 90, 0),
                block(
                    "text", 115, 232, 80, 8, {"text": "Unterschrift", "size": 12, "align": "left"}
                ),
                shape("line", 115, 246, 80, 0),
            ]
        ),
    },
    {
        "id": -6,
        "name": "Rechenblatt Klasse 1",
        "group": "Mathe",
        "doc": doc(
            maths_page(
                "Rechenblatt Klasse 1",
                maths_block(
                    55,
                    {
                        "ops": ["+", "-"],
                        "max": 20,
                        "carry": "either",
                        "rest": False,
                        "format": "row",
                        "count": 12,
                        "seed": 101,
                    },
                ),
                block(
                    "zahlenmauer",
                    15,
                    110,
                    180,
                    60,
                    {
                        "base": 3,
                        "count": 4,
                        "columns": 2,
                        "max": 20,
                        "op": "+",
                        "given": "base",
                        "empty": False,
                        "seed": 111,
                    },
                ),
                block(
                    "rechendreieck",
                    15,
                    180,
                    180,
                    50,
                    {
                        "count": 4,
                        "columns": 4,
                        "max": 20,
                        "given": "inner",
                        "empty": False,
                        "seed": 121,
                    },
                ),
            )
        ),
    },
    {
        "id": -7,
        "name": "Rechenblatt Klasse 2",
        "group": "Mathe",
        "doc": doc(
            maths_page(
                "Rechenblatt Klasse 2",
                maths_block(
                    55,
                    {
                        "ops": ["+", "-"],
                        "max": 100,
                        "carry": "either",
                        "rest": False,
                        "format": "row",
                        "count": 12,
                        "seed": 102,
                    },
                ),
                maths_block(
                    110,
                    {
                        "ops": ["*"],
                        "max": 100,
                        "small": True,
                        "carry": "either",
                        "rest": False,
                        "format": "row",
                        "count": 12,
                        "seed": 122,
                    },
                ),
                block(
                    "zahlenmauer",
                    15,
                    165,
                    180,
                    60,
                    {
                        "base": 3,
                        "count": 4,
                        "columns": 2,
                        "max": 100,
                        "op": "+",
                        "given": "base",
                        "empty": False,
                        "seed": 112,
                    },
                ),
            )
        ),
    },
    {
        "id": -8,
        "name": "Rechenblatt Klasse 3",
        "group": "Mathe",
        "doc": doc(
            maths_page(
                "Rechenblatt Klasse 3",
                maths_block(
                    55,
                    {
                        "ops": ["+", "-"],
                        "max": 1000,
                        "carry": "either",
                        "rest": False,
                        "format": "row",
                        "count": 12,
                        "seed": 103,
                    },
                ),
                block(
                    "zahlenmauer",
                    15,
                    110,
                    180,
                    60,
                    {
                        "base": 3,
                        "count": 4,
                        "columns": 2,
                        "max": 1000,
                        "op": "+",
                        "given": "base",
                        "empty": False,
                        "seed": 113,
                    },
                ),
                block(
                    "zahlenstrahl",
                    15,
                    180,
                    180,
                    40,
                    {
                        "start": 0,
                        "end": 1000,
                        "minor": 10,
                        "major": 100,
                        "labels": "major",
                        "size": 12,
                        "seed": 123,
                    },
                ),
            )
        ),
    },
    {
        "id": -9,
        "name": "Rechenblatt Klasse 4",
        "group": "Mathe",
        "doc": doc(
            maths_page(
                "Rechenblatt Klasse 4",
                maths_block(
                    55,
                    {
                        "ops": ["+", "-"],
                        "max": 10000,
                        "carry": "either",
                        "rest": False,
                        "format": "written",
                        "count": 9,
                        "seed": 104,
                    },
                ),
                maths_block(
                    150,
                    {
                        "ops": ["*"],
                        "max": 10000,
                        "carry": "either",
                        "rest": False,
                        "format": "written",
                        "count": 6,
                        "seed": 124,
                    },
                ),
            )
        ),
    },
    {
        "id": -10,
        "name": "Schreibblatt Lineatur 1",
        "group": "Deutsch",
        "doc": doc(
            ruled_page(
                "Schreibblatt",
                {"kind": "l1", "color": "#555555", "text": "Mama Papa Maus Hund", "trace": True},
            )
        ),
    },
    {
        "id": -11,
        "name": "Schreibblatt Lineatur 2",
        "group": "Deutsch",
        "doc": doc(
            ruled_page(
                "Schreibblatt",
                {"kind": "l2", "color": "#555555", "text": "Mama Papa Maus Hund", "trace": True},
            )
        ),
    },
    {
        "id": -12,
        "name": "Lernwörter",
        "group": "Deutsch",
        "doc": doc(
            [
                block("name", 15, 15, 180, 10, {}),
                heading(32, "Lernwörter"),
                # Six words, one row of Lineatur 1 (20 mm) each.
                block(
                    "ruling", 15, 55, 180, 120, {"kind": "l1", "color": "#555555", "list": "copy"}
                ),
            ]
        ),
    },
    {
        "id": -13,
        "name": "Klassenarbeit Deckblatt",
        "group": "Organisation",
        "doc": doc(
            [
                block("name", 15, 15, 180, 10, {}),
                heading(32, "Klassenarbeit"),
                block(
                    "text",
                    15,
                    50,
                    180,
                    10,
                    {
                        "text": "Fach: ____________   Datum: ____________",
                        "size": 14,
                        "align": "left",
                    },
                ),
                block(
                    "table",
                    15,
                    70,
                    180,
                    36,
                    {
                        "cells": [
                            ["Aufgabe", "1", "2", "3", "4", "5", "Gesamt"],
                            ["Punkte", "", "", "", "", "", ""],
                            ["erreicht", "", "", "", "", "", ""],
                        ],
                        "cols": [2, 1, 1, 1, 1, 1, 1.5],
                        "size": 14,
                        "align": "center",
                        "line": "#222222",
                        "head": True,
                    },
                ),
                block("text", 15, 130, 20, 10, {"text": "Note:", "size": 14, "align": "left"}),
                shape("line", 35, 140, 60, 0),
                block(
                    "text", 105, 130, 35, 10, {"text": "Unterschrift:", "size": 14, "align": "left"}
                ),
                shape("line", 140, 140, 55, 0),
            ]
        ),
    },
]


class Template(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=80)]
    doc: dict


@router.get("/templates")
def templates(user: User, con: Con) -> list[dict]:
    rows = con.execute(
        "SELECT id, name, doc FROM templates WHERE user_id = ? ORDER BY name", (user["id"],)
    )
    return BUILT_IN + [
        {"id": r["id"], "name": r["name"], "doc": json.loads(r["doc"])} for r in rows
    ]


@router.post("/templates")
def save(body: Template, user: User, con: Con) -> dict:
    pictures.touch(user["id"], body.doc)
    cur = con.execute(
        "INSERT INTO templates (user_id, name, doc) VALUES (?, ?, ?)",
        (user["id"], body.name, json.dumps(body.doc)),
    )
    return {"id": cur.lastrowid, "name": body.name, "doc": body.doc}


@router.delete("/templates/{template_id}")
def delete(template_id: Id, user: User, con: Con) -> dict:
    mine = (template_id, user["id"])
    row = con.execute("SELECT doc FROM templates WHERE id = ? AND user_id = ?", mine).fetchone()
    # Someone else's template is as missing as one that never was.
    if not row:
        raise HTTPException(404)
    # A picture's 30 days count from the delete that takes it away.
    pictures.touch(user["id"], json.loads(row["doc"]))
    con.execute("DELETE FROM templates WHERE id = ? AND user_id = ?", mine)
    pictures.sweep(con, user["id"])
    return {}
