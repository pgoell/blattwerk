"""Sheets: a title and the sheet document, saved per user."""

import json
import sqlite3
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from blattwerk.auth import User
from blattwerk.db import Con

router = APIRouter(prefix="/api")

Title = Annotated[str, Field(min_length=1, max_length=80)]


class Sheet(BaseModel):
    title: Title
    doc: dict


class Change(BaseModel):
    title: Title | None = None
    doc: dict | None = None
    # The version the document was based on. A rename brings neither.
    version: int | None = None

    @model_validator(mode="after")
    def doc_has_version(self) -> Change:
        if self.doc is not None and self.version is None:
            raise ValueError("a doc needs the version it was based on")
        return self


COLUMNS = "id, title, doc, version, updated"


def public(row: sqlite3.Row | None) -> dict:
    # Someone else's sheet is as missing as one that never was.
    if not row:
        raise HTTPException(404)
    return {**row, "doc": json.loads(row["doc"])}


@router.get("/sheets")
def sheets(user: User, con: Con) -> list[dict]:
    rows = con.execute(
        f"SELECT {COLUMNS} FROM sheets WHERE user_id = ? ORDER BY updated DESC, id DESC",
        (user["id"],),
    )
    return [public(row) for row in rows]


@router.post("/sheets")
def create(body: Sheet, user: User, con: Con) -> dict:
    return public(
        con.execute(
            f"INSERT INTO sheets (user_id, title, doc) VALUES (?, ?, ?) RETURNING {COLUMNS}",
            (user["id"], body.title, json.dumps(body.doc)),
        ).fetchone()
    )


def find(con: sqlite3.Connection, sheet_id: int, user: sqlite3.Row) -> dict:
    return public(
        con.execute(
            f"SELECT {COLUMNS} FROM sheets WHERE id = ? AND user_id = ?", (sheet_id, user["id"])
        ).fetchone()
    )


@router.get("/sheets/{sheet_id}")
def sheet(sheet_id: int, user: User, con: Con) -> dict:
    return find(con, sheet_id, user)


@router.patch("/sheets/{sheet_id}")
def save(sheet_id: int, body: Change, user: User, con: Con) -> dict:
    # Only a new document moves the version on, so a rename from the list neither needs one
    # nor gets in the way of an open editor's next save.
    doc = body.doc and json.dumps(body.doc)
    row = con.execute(
        "UPDATE sheets SET title = coalesce(?1, title), doc = coalesce(?2, doc),"
        " version = version + (?2 IS NOT NULL), updated = CURRENT_TIMESTAMP"
        " WHERE id = ?3 AND user_id = ?4 AND (?2 IS NULL OR version = ?5)"
        f" RETURNING {COLUMNS}",
        (body.title, doc, sheet_id, user["id"], body.version),
    ).fetchone()
    if not row:
        # The sheet is there, so it was saved from somewhere else in the meantime.
        find(con, sheet_id, user)
        raise HTTPException(409)
    return public(row)


@router.post("/sheets/{sheet_id}/duplicate")
def duplicate(sheet_id: int, user: User, con: Con) -> dict:
    # The copy's title stays within the 80 characters a save allows.
    return public(
        con.execute(
            "INSERT INTO sheets (user_id, title, doc)"
            " SELECT user_id, substr(title, 1, 72) || ' (Kopie)', doc FROM sheets"
            f" WHERE id = ? AND user_id = ? RETURNING {COLUMNS}",
            (sheet_id, user["id"]),
        ).fetchone()
    )


@router.delete("/sheets/{sheet_id}")
def delete(sheet_id: int, user: User, con: Con) -> dict:
    cur = con.execute("DELETE FROM sheets WHERE id = ? AND user_id = ?", (sheet_id, user["id"]))
    if not cur.rowcount:
        raise HTTPException(404)
    return {}
