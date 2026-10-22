"""A share link: one frozen preview of a sheet, and a copy into another account.

The link shows the sheet as it was when the link was made or last renewed, not the live sheet.
Switching it off, or deleting the sheet or the account, kills the link. The copy is a new sheet
in the receiver's account. Its pictures are new files: an upload belongs to one account, and a
later edit of either sheet never touches the other.
"""

import json
import re
import secrets
import sqlite3
from contextlib import suppress
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from blattwerk import pictures
from blattwerk.auth import Teacher
from blattwerk.db import Con, Id
from blattwerk.schema import check
from blattwerk.sheets import COLUMNS, find, public
from blattwerk.uploads import NOSNIFF, SVG_CSP

router = APIRouter(prefix="/api")

# token_urlsafe(32) is 43 characters. Anything else is not a link this app made.
TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
# What a visitor's copy is called. The sheet's title fills the rest of the 80 characters.
PREFIX = "Kopie von "
# A preview is not a catalogue, and a renewed link keeps its address, so nothing may cache it.
GONE = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"}


def missing_link() -> HTTPException:
    return HTTPException(404, headers=GONE)


def by_token(con: sqlite3.Connection, token: str) -> sqlite3.Row:
    if not TOKEN.fullmatch(token):
        raise missing_link()
    row = con.execute("SELECT * FROM shares WHERE token = ?", (token,)).fetchone()
    if not row:
        raise missing_link()
    return row


def of_sheet(con: sqlite3.Connection, sheet_id: int, user_id: int) -> sqlite3.Row | None:
    return con.execute(
        "SELECT * FROM shares WHERE sheet_id = ? AND user_id = ?", (sheet_id, user_id)
    ).fetchone()


def state(row: sqlite3.Row | None) -> dict:
    if not row:
        return {"on": False}
    return {"on": True, "token": row["token"], "updated": row["updated"]}


def retarget(doc: dict, mapping: dict[int, int]) -> dict:
    """The document with each shown picture pointed at the receiver's new upload."""
    pages = doc.get("pages")
    if not isinstance(pages, list):
        return doc
    for page in pages:
        if not isinstance(page, dict):
            continue
        blocks = page.get("blocks")
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


def picture_bytes(
    con: sqlite3.Connection, owner_id: int, doc: dict
) -> dict[int, tuple[str, bytes]]:
    """The snapshot's pictures, read before any row of the copy is written."""
    blobs = {}
    for upload_id in pictures.shown(doc):
        row = con.execute(
            "SELECT type FROM uploads WHERE id = ? AND user_id = ?", (upload_id, owner_id)
        ).fetchone()
        file = pictures.path(owner_id, upload_id)
        # A snapshot whose file is gone cannot be copied whole, so it is not copied at all.
        if not row or not file.is_file():
            raise missing_link()
        blobs[upload_id] = (row["type"], file.read_bytes())
    return blobs


@router.get("/sheets/{sheet_id}/share")
def share(sheet_id: Id, user: Teacher, con: Con) -> dict:
    find(con, sheet_id, user)
    return state(of_sheet(con, sheet_id, user["id"]))


@router.post("/sheets/{sheet_id}/share")
def turn_on(sheet_id: Id, user: Teacher, con: Con) -> dict:
    """Makes the link, or returns the one already on. A second press does not renew it."""
    sheet = find(con, sheet_id, user)
    row = of_sheet(con, sheet_id, user["id"])
    if row:
        return state(row)
    token = secrets.token_urlsafe(32)
    try:
        con.execute(
            "INSERT INTO shares (token, sheet_id, user_id, title, doc) VALUES (?, ?, ?, ?, ?)",
            (token, sheet_id, user["id"], sheet["title"], json.dumps(sheet["doc"])),
        )
    except sqlite3.IntegrityError:
        # The sheet took a link between the look and the insert.
        row = of_sheet(con, sheet_id, user["id"])
        if not row:
            raise
        return state(row)
    return state(of_sheet(con, sheet_id, user["id"]))


@router.post("/sheets/{sheet_id}/share/renew")
def renew(sheet_id: Id, user: Teacher, con: Con) -> dict:
    """Points the same link at the sheet as it is saved now."""
    sheet = find(con, sheet_id, user)
    row = of_sheet(con, sheet_id, user["id"])
    if not row:
        raise HTTPException(404)
    pictures.touch(user["id"], json.loads(row["doc"]))
    pictures.touch(user["id"], sheet["doc"])
    con.execute(
        "UPDATE shares SET title = ?, doc = ?, updated = CURRENT_TIMESTAMP WHERE token = ?",
        (sheet["title"], json.dumps(sheet["doc"]), row["token"]),
    )
    pictures.sweep(con, user["id"])
    return state(of_sheet(con, sheet_id, user["id"]))


@router.delete("/sheets/{sheet_id}/share")
def turn_off(sheet_id: Id, user: Teacher, con: Con) -> dict:
    find(con, sheet_id, user)
    row = of_sheet(con, sheet_id, user["id"])
    if row:
        # The 30 days of a picture the sheet no longer shows start as the link lets it go.
        pictures.touch(user["id"], json.loads(row["doc"]))
        con.execute("DELETE FROM shares WHERE token = ?", (row["token"],))
        pictures.sweep(con, user["id"])
    return {"on": False}


@router.get("/shares/{token}")
def preview(token: str, response: Response, con: Con) -> dict:
    row = by_token(con, token)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Cache-Control"] = "no-store"
    # The title and the document only. Nothing here names the account the sheet belongs to.
    return {"title": row["title"], "doc": json.loads(row["doc"])}


@router.get("/shares/{token}/uploads/{upload_id}")
def preview_picture(token: str, upload_id: Id, con: Con) -> FileResponse:
    row = by_token(con, token)
    # Only a picture the snapshot shows. The owner's other uploads stay theirs.
    if upload_id not in pictures.shown(json.loads(row["doc"])):
        raise HTTPException(404, headers={**NOSNIFF, **GONE})
    stored = con.execute(
        "SELECT type FROM uploads WHERE id = ? AND user_id = ?", (upload_id, row["user_id"])
    ).fetchone()
    file = pictures.path(row["user_id"], upload_id)
    if not stored or not file.is_file():
        raise HTTPException(404, headers={**NOSNIFF, **GONE})
    # A picture file never changes, so the browser may keep it. no-store stays on the preview JSON,
    # whose address does not change when the owner renews the link.
    headers = {
        "Cache-Control": "private, max-age=31536000, immutable",
        "X-Robots-Tag": "noindex, nofollow",
        **NOSNIFF,
    }
    if stored["type"] == "image/svg+xml":
        headers |= SVG_CSP
    return FileResponse(file, media_type=stored["type"], headers=headers)


@router.post("/shares/{token}/copy")
def copy(token: str, user: Teacher, con: Con) -> dict:
    row = by_token(con, token)
    doc = json.loads(row["doc"])
    blobs = picture_bytes(con, row["user_id"], doc)
    # The new upload rows, their files and the new sheet land together, or not at all.
    written: list[Path] = []
    con.execute("BEGIN IMMEDIATE")
    try:
        mapping = {}
        for upload_id, (type_, data) in blobs.items():
            new_id = con.execute(
                "INSERT INTO uploads (user_id, type) VALUES (?, ?)", (user["id"], type_)
            ).lastrowid
            assert new_id is not None
            out = pictures.path(user["id"], new_id)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            written.append(out)
            mapping[upload_id] = new_id
        doc = retarget(doc, mapping)
        check(doc)
        made = con.execute(
            f"INSERT INTO sheets (user_id, title, doc) VALUES (?, ?, ?) RETURNING {COLUMNS}",
            (user["id"], (PREFIX + row["title"])[:80], json.dumps(doc)),
        ).fetchone()
        con.execute("COMMIT")
    except BaseException:
        with suppress(sqlite3.Error):
            con.execute("ROLLBACK")
        for out in written:
            out.unlink(missing_ok=True)
        raise
    pictures.touch(user["id"], doc)
    return public(made, user)
