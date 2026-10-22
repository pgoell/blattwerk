"""The school folder: one copy of a sheet, for the teachers who have a seat at that school.

Putting a sheet in stores a copy. The teacher's own sheet is left alone, and a copy taken out
is a new sheet with no tie back. The name kept is the part of the address before @, because an
account has no name of its own. Pictures are copied with the sheet, so they outlive the file
they came from.
"""

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from blattwerk import pictures, sheets
from blattwerk.auth import Admin, Email, Teacher
from blattwerk.db import DATA_DIR, Con, Id, Whole

router = APIRouter(prefix="/api")

Label = Annotated[str, Field(max_length=40)]
Sort = Literal["name", "date", "label"]


def strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


class PutIn(BaseModel):
    sheet_id: Whole
    label: Label = ""

    @field_validator("label", mode="before")
    @classmethod
    def stripped(cls, value: object) -> object:
        return strip_text(value)


class Replace(BaseModel):
    sheet_id: Whole


class Relabel(BaseModel):
    label: Label

    @field_validator("label", mode="before")
    @classmethod
    def stripped(cls, value: object) -> object:
        return strip_text(value)


class SchoolName(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=80)]

    @field_validator("name", mode="before")
    @classmethod
    def stripped(cls, value: object) -> object:
        return strip_text(value)


class NewSeat(BaseModel):
    email: Email
    admin: bool = False


def mailbox_name(email: str) -> str:
    """The part before @. Kept as it was on the day the sheet went in."""
    name, _, _rest = email.partition("@")
    return name or email


def copy_title(title: str) -> str:
    """The name a copy out carries, within the 80 characters a sheet allows."""
    return f"Kopie von {title}"[:80]


def entry_dir(school_id: int, entry_id: int) -> Path:
    return DATA_DIR / "schools" / str(school_id) / str(entry_id)


def picture_path(school_id: int, entry_id: int, upload_id: int) -> Path:
    return entry_dir(school_id, entry_id) / str(upload_id)


def school_of(con: sqlite3.Connection, user: sqlite3.Row) -> sqlite3.Row:
    row = con.execute(
        "SELECT seats.school_id AS id, seats.admin, schools.name FROM seats"
        " JOIN schools ON schools.id = seats.school_id WHERE seats.user_id = ?",
        (user["id"],),
    ).fetchone()
    # No seat: the folder does not exist for this teacher.
    if row is None:
        raise HTTPException(404)
    return row


def school_public(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "admin": bool(row["admin"])}


def public_entry(row: sqlite3.Row, user_id: int) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "label": row["label"],
        "author_name": row["author_name"],
        "author_id": row["author_id"],
        "mine": row["author_id"] == user_id,
        "created": row["created"],
        "updated": row["updated"],
        "doc": json.loads(row["doc"]),
    }


def entry_of(
    con: sqlite3.Connection, entry_id: int, user: sqlite3.Row
) -> tuple[sqlite3.Row, sqlite3.Row]:
    seat = school_of(con, user)
    row = con.execute(
        "SELECT * FROM folder_sheets WHERE id = ? AND school_id = ?",
        (entry_id, seat["id"]),
    ).fetchone()
    # Another school's sheet is as missing as one that never was.
    if row is None:
        raise HTTPException(404)
    return seat, row


def may_change(seat: sqlite3.Row, row: sqlite3.Row, user: sqlite3.Row) -> bool:
    return bool(seat["admin"]) or row["author_id"] == user["id"]


def load_entry(entry_id: Id, user: Teacher, con: Con) -> tuple[sqlite3.Row, sqlite3.Row]:
    """404 before the body is read, so a bad body does not tell a stranger the sheet is there."""
    return entry_of(con, entry_id, user)


Entry = Annotated[tuple[sqlite3.Row, sqlite3.Row], Depends(load_entry)]


def listed(rows: list[sqlite3.Row], user_id: int, sort: str, q: str) -> list[dict]:
    needle = q.casefold().strip()
    found = []
    for row in rows:
        title = row["title"].casefold()
        label = row["label"].casefold()
        if needle and needle not in title and needle not in label:
            continue
        found.append(public_entry(row, user_id))
    if sort == "name":
        found.sort(key=lambda item: (item["title"].casefold(), item["id"]))
    elif sort == "label":
        found.sort(
            key=lambda item: (item["label"].casefold(), item["title"].casefold(), item["id"])
        )
    else:
        found.sort(key=lambda item: (item["updated"], item["id"]), reverse=True)
    return found


def retarget(doc: dict, mapping: dict[int, int]) -> dict:
    doc = json.loads(json.dumps(doc))
    pages = doc.get("pages", [doc])
    if not isinstance(pages, list):
        return doc
    for page in pages:
        blocks = page.get("blocks") if isinstance(page, dict) else None
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict) or block.get("type") != "image":
                continue
            props = block.get("props")
            if not isinstance(props, dict):
                continue
            upload = props.get("upload")
            if isinstance(upload, int) and upload in mapping:
                props["upload"] = mapping[upload]
    return doc


def take_pictures(
    con: sqlite3.Connection, user_id: int, doc: dict, school_id: int, entry_id: int
) -> None:
    """Copies the pictures next to the entry, and drops the ones the document no longer shows."""
    shown = pictures.shown(doc)
    old = con.execute(
        "SELECT upload_id FROM folder_files WHERE entry_id = ?", (entry_id,)
    ).fetchall()
    for upload_id in shown:
        row = con.execute(
            "SELECT type FROM uploads WHERE id = ? AND user_id = ?",
            (upload_id, user_id),
        ).fetchone()
        src = pictures.path(user_id, upload_id)
        if row is None or not src.is_file():
            continue
        dest = picture_path(school_id, entry_id, upload_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        con.execute(
            "INSERT INTO folder_files (entry_id, upload_id, type) VALUES (?, ?, ?)"
            " ON CONFLICT (entry_id, upload_id) DO UPDATE SET type = excluded.type",
            (entry_id, upload_id, row["type"]),
        )
    for old_row in old:
        upload_id = old_row["upload_id"]
        if upload_id in shown:
            continue
        con.execute(
            "DELETE FROM folder_files WHERE entry_id = ? AND upload_id = ?",
            (entry_id, upload_id),
        )
        picture_path(school_id, entry_id, upload_id).unlink(missing_ok=True)


def give_pictures(
    con: sqlite3.Connection, user_id: int, school_id: int, entry_id: int, doc: dict
) -> dict:
    """Copies each folder picture into the teacher's uploads and points the document at them."""
    mapping: dict[int, int] = {}
    for upload_id in pictures.shown(doc):
        row = con.execute(
            "SELECT type FROM folder_files WHERE entry_id = ? AND upload_id = ?",
            (entry_id, upload_id),
        ).fetchone()
        src = picture_path(school_id, entry_id, upload_id)
        if row is None or not src.is_file():
            continue
        new_id = con.execute(
            "INSERT INTO uploads (user_id, type) VALUES (?, ?)",
            (user_id, row["type"]),
        ).lastrowid
        assert new_id is not None
        dest = pictures.path(user_id, new_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        mapping[upload_id] = new_id
    return retarget(doc, mapping)


def served_copy(con: sqlite3.Connection, user_id: int, upload_id: int) -> tuple[Path, str] | None:
    """The folder's copy of a picture, when the teacher has a seat at that school."""
    row = con.execute(
        "SELECT folder_sheets.school_id, folder_files.entry_id, folder_files.type"
        " FROM folder_files"
        " JOIN folder_sheets ON folder_sheets.id = folder_files.entry_id"
        " JOIN seats ON seats.school_id = folder_sheets.school_id"
        " WHERE folder_files.upload_id = ? AND seats.user_id = ?",
        (upload_id, user_id),
    ).fetchone()
    if row is None:
        return None
    file = picture_path(row["school_id"], row["entry_id"], upload_id)
    if not file.is_file():
        return None
    return file, row["type"]


def drop_entry_files(school_id: int, entry_id: int) -> None:
    shutil.rmtree(entry_dir(school_id, entry_id), ignore_errors=True)


@router.get("/folder")
def folder_list(
    user: Teacher,
    con: Con,
    sort: Sort = "date",
    q: Annotated[str, Query(max_length=80)] = "",
) -> dict:
    seat = school_of(con, user)
    rows = con.execute("SELECT * FROM folder_sheets WHERE school_id = ?", (seat["id"],)).fetchall()
    return {"school": school_public(seat), "sheets": listed(rows, user["id"], sort, q)}


@router.post("/folder")
def put_in(body: PutIn, user: Teacher, con: Con) -> dict:
    seat = school_of(con, user)
    own = sheets.find(con, body.sheet_id, user)
    row = con.execute(
        "INSERT INTO folder_sheets (school_id, author_id, author_name, title, label, doc)"
        " VALUES (?, ?, ?, ?, ?, ?) RETURNING *",
        (
            seat["id"],
            user["id"],
            mailbox_name(user["email"]),
            own["title"],
            body.label,
            json.dumps(own["doc"]),
        ),
    ).fetchone()
    assert row is not None
    take_pictures(con, user["id"], own["doc"], seat["id"], row["id"])
    return {"school": school_public(seat), "sheet": public_entry(row, user["id"])}


@router.get("/folder/{entry_id}")
def one(entry_id: Id, user: Teacher, con: Con) -> dict:
    seat, row = entry_of(con, entry_id, user)
    return {"school": school_public(seat), "sheet": public_entry(row, user["id"])}


@router.patch("/folder/{entry_id}")
def relabel(body: Relabel, user: Teacher, con: Con, found: Entry) -> dict:
    seat, row = found
    if not may_change(seat, row, user):
        raise HTTPException(404)
    updated = con.execute(
        "UPDATE folder_sheets SET label = ? WHERE id = ? RETURNING *",
        (body.label, row["id"]),
    ).fetchone()
    assert updated is not None
    return {"school": school_public(seat), "sheet": public_entry(updated, user["id"])}


@router.post("/folder/{entry_id}/replace")
def replace(body: Replace, user: Teacher, con: Con, found: Entry) -> dict:
    seat, row = found
    if not may_change(seat, row, user):
        raise HTTPException(404)
    own = sheets.find(con, body.sheet_id, user)
    updated = con.execute(
        "UPDATE folder_sheets SET title = ?, doc = ?, updated = CURRENT_TIMESTAMP"
        " WHERE id = ? RETURNING *",
        (own["title"], json.dumps(own["doc"]), row["id"]),
    ).fetchone()
    assert updated is not None
    take_pictures(con, user["id"], own["doc"], seat["id"], row["id"])
    return {"school": school_public(seat), "sheet": public_entry(updated, user["id"])}


@router.post("/folder/{entry_id}/copy")
def copy_out(entry_id: Id, user: Teacher, con: Con) -> dict:
    seat, row = entry_of(con, entry_id, user)
    doc = give_pictures(con, user["id"], seat["id"], row["id"], json.loads(row["doc"]))
    return sheets.create(sheets.Sheet(title=copy_title(row["title"]), doc=doc), user, con)


@router.delete("/folder/{entry_id}")
def delete_entry(entry_id: Id, user: Teacher, con: Con) -> dict:
    seat, row = entry_of(con, entry_id, user)
    if not may_change(seat, row, user):
        raise HTTPException(404)
    con.execute("DELETE FROM folder_sheets WHERE id = ?", (row["id"],))
    drop_entry_files(seat["id"], row["id"])
    return {}


@router.get("/admin/schools")
def schools(admin: Admin, con: Con) -> list[dict]:
    rows = con.execute("SELECT id, name FROM schools ORDER BY id").fetchall()
    out = []
    for row in rows:
        seats = con.execute(
            "SELECT users.id AS user_id, users.email, seats.admin FROM seats"
            " JOIN users ON users.id = seats.user_id WHERE seats.school_id = ?"
            " ORDER BY users.email",
            (row["id"],),
        ).fetchall()
        out.append(
            {
                "id": row["id"],
                "name": row["name"],
                "seats": [
                    {
                        "user_id": seat["user_id"],
                        "email": seat["email"],
                        "admin": bool(seat["admin"]),
                    }
                    for seat in seats
                ],
            }
        )
    return out


@router.post("/admin/schools")
def create_school(body: SchoolName, admin: Admin, con: Con) -> dict:
    row = con.execute(
        "INSERT INTO schools (name) VALUES (?) RETURNING id, name", (body.name,)
    ).fetchone()
    assert row is not None
    return {"id": row["id"], "name": row["name"], "seats": []}


@router.post("/admin/schools/{school_id}/seats")
def give_seat(school_id: Id, body: NewSeat, admin: Admin, con: Con) -> dict:
    if not con.execute("SELECT 1 FROM schools WHERE id = ?", (school_id,)).fetchone():
        raise HTTPException(404)
    person = con.execute(
        "SELECT id, email FROM users WHERE email = ?", (body.email.lower(),)
    ).fetchone()
    if person is None:
        raise HTTPException(404)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT INTO seats (user_id, school_id, admin) VALUES (?, ?, ?)",
            (person["id"], school_id, int(body.admin)),
        )
        con.execute("COMMIT")
    except sqlite3.IntegrityError:
        con.execute("ROLLBACK")
        raise HTTPException(409) from None
    return {"user_id": person["id"], "email": person["email"], "admin": body.admin}


@router.delete("/admin/schools/{school_id}/seats/{user_id}")
def take_seat(school_id: Id, user_id: Id, admin: Admin, con: Con) -> dict:
    cur = con.execute("DELETE FROM seats WHERE school_id = ? AND user_id = ?", (school_id, user_id))
    if not cur.rowcount:
        raise HTTPException(404)
    return {}
