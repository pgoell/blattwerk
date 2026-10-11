"""Templates: a name and the sheet document to start from. Three are built in."""

import json
from itertools import count
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from blattwerk import pictures
from blattwerk.auth import User
from blattwerk.db import Con, Id

router = APIRouter(prefix="/api")


LINE = {"fill": "none", "stroke": "#222222", "strokeWidth": 0.5}
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


# Shared by all users. Their ids lie below zero and in no table, so no one can delete them.
BUILT_IN = [
    {
        "id": -1,
        "name": "Arbeitsblatt",
        "doc": doc(
            [
                block("name", 15, 15, 180, 10, {}),
                heading(32, "Überschrift"),
                shape("rounded", 15, 55, 180, 110),
                shape("rounded", 15, 172, 180, 110),
            ]
        ),
    },
    {"id": -2, "name": "Klassenarbeit", "doc": doc(*(test_page(n == 0) for n in range(3)))},
    {
        "id": -3,
        "name": "Beschriftungsblatt",
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
