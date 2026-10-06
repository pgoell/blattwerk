"""Templates a user saved: a name and the sheet document to start from."""

import json
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from blattwerk.auth import User
from blattwerk.db import Con

router = APIRouter(prefix="/api")


class Template(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=80)]
    doc: dict


@router.get("/templates")
def templates(user: User, con: Con) -> list[dict]:
    rows = con.execute(
        "SELECT id, name, doc FROM templates WHERE user_id = ? ORDER BY name", (user["id"],)
    )
    return [{"id": r["id"], "name": r["name"], "doc": json.loads(r["doc"])} for r in rows]


@router.post("/templates")
def save(body: Template, user: User, con: Con) -> dict:
    cur = con.execute(
        "INSERT INTO templates (user_id, name, doc) VALUES (?, ?, ?)",
        (user["id"], body.name, json.dumps(body.doc)),
    )
    return {"id": cur.lastrowid, "name": body.name, "doc": body.doc}


@router.delete("/templates/{template_id}")
def delete(template_id: int, user: User, con: Con) -> dict:
    cur = con.execute(
        "DELETE FROM templates WHERE id = ? AND user_id = ?", (template_id, user["id"])
    )
    # Someone else's template is as missing as one that never was.
    if not cur.rowcount:
        raise HTTPException(404)
    return {}
