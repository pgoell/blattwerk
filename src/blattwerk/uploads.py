"""Uploads: the pictures of image blocks, kept per user on the data volume."""

import json
import threading
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from blattwerk import pdf, pictures, svg
from blattwerk.auth import Teacher, current_teacher
from blattwerk.db import Con, Id
from blattwerk.pictures import path

MAX_BYTES = 15 * 2**20
# Parsing an SVG takes about 60 times its bytes in memory, so an SVG has a lower limit.
MAX_SVG_BYTES = 2 * 2**20
# And so no more than two are parsed at once, whatever the threads.
PARSING = threading.BoundedSemaphore(2)
NOSNIFF = {"X-Content-Type-Options": "nosniff"}
# An SVG opened in a tab runs nothing and loads nothing.
SVG_CSP = {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"}

router = APIRouter(prefix="/api")


def kind(data: bytes) -> str | None:
    """The type the first bytes show: the four a browser draws, and SVG, which is cleaned first.

    What a file declares is no evidence: the type is the bytes', or the file is no picture.
    No PDF.
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.removeprefix(b"\xef\xbb\xbf").lstrip().startswith((b"<svg", b"<?xml", b"<!--")):
        return "image/svg+xml"
    return None


def parsed(data: bytes) -> bytes | None:
    with PARSING:
        return svg.clean(data)


async def stored(data: bytes) -> tuple[bytes, str]:
    """The bytes to keep and their type. A file that is no picture is refused."""
    if len(data) > MAX_BYTES:
        raise HTTPException(413)
    type_ = kind(data)
    if type_ is None:
        raise HTTPException(415)
    if type_ == "image/svg+xml":
        if len(data) > MAX_SVG_BYTES:
            raise HTTPException(413)
        # Cleaning parses the SVG, which takes time, so it leaves the event loop.
        cleaned = await run_in_threadpool(parsed, data)
        if cleaned is None:
            raise HTTPException(415)
        if len(cleaned) > MAX_BYTES:
            raise HTTPException(413)
        data = cleaned
    return data, type_


def write_upload(
    con: Con, user_id: int, data: bytes, type_: str, credit: dict | None = None
) -> int:
    """Stores one picture. `credit` is the source of a found picture; an upload has none."""
    credit = credit or {}
    upload_id = con.execute(
        "INSERT INTO uploads (user_id, type, source, author, licence, page)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            type_,
            credit.get("source"),
            credit.get("author"),
            credit.get("licence"),
            credit.get("page"),
        ),
    ).lastrowid
    assert upload_id is not None
    out = path(user_id, upload_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return upload_id


@router.post("/uploads")
async def upload(file: UploadFile, user: Teacher, con: Con) -> dict:
    data, type_ = await stored(await file.read(MAX_BYTES + 1))
    return {"id": write_upload(con, user["id"], data, type_)}


@router.get("/uploads/{upload_id}")
def serve(
    upload_id: Id,
    request: Request,
    con: Con,
    session: Annotated[str | None, Cookie()] = None,
    token: pdf.Token = None,
) -> FileResponse:
    # Chromium, printing a sheet, stands for the sheet's owner, for that sheet's pictures alone.
    user_id = (
        pdf.shows(con, token, upload_id) if token else current_teacher(request, con, session)["id"]
    )
    row = con.execute(
        "SELECT type FROM uploads WHERE id = ? AND user_id = ?", (upload_id, user_id)
    ).fetchone()
    # Someone else's picture is as missing as one that never was, and so is a row whose file a
    # sweep deleted before it failed to delete the row.
    if not row or not path(user_id, upload_id).is_file():
        raise HTTPException(404, headers=NOSNIFF)
    # An upload never changes, so the browser may keep it.
    headers = {"Cache-Control": "private, max-age=31536000, immutable", **NOSNIFF}
    if row["type"] == "image/svg+xml":
        headers |= SVG_CSP
    return FileResponse(path(user_id, upload_id), media_type=row["type"], headers=headers)


def chosen_ids(raw: str) -> list[int]:
    """Up to 200 ids from a comma list. Anything else is left out."""
    chosen = []
    for part in raw.split(","):
        part = part.strip()
        if not part.isdigit():
            continue
        number = int(part)
        if number >= 2**63:
            continue
        chosen.append(number)
        if len(chosen) == 200:
            break
    return chosen


def notes_for(con: Con, user_id: int, ids: list[int]) -> list[dict]:
    """The licence notes of this teacher's pictures, in the order asked, with a source only."""
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    rows = con.execute(
        "SELECT id, source, author, licence, page FROM uploads"
        f" WHERE user_id = ? AND source IS NOT NULL AND id IN ({marks})",
        (user_id, *ids),
    ).fetchall()
    by = {row["id"]: row for row in rows}
    return [
        {
            "id": i,
            "source": by[i]["source"] or "",
            "author": by[i]["author"] or "",
            "licence": by[i]["licence"] or "",
            "page": by[i]["page"] or "",
        }
        for i in ids
        if i in by
    ]


@router.get("/picture-notes")
def picture_notes(
    request: Request,
    con: Con,
    ids: str = "",
    session: Annotated[str | None, Cookie()] = None,
    token: pdf.Token = None,
) -> list[dict]:
    """Licence notes for picture ids. A render token sees only the pictures on its sheet."""
    chosen = chosen_ids(ids)
    if token:
        row = pdf.opened(con, token)
        held = row["doc"]
        doc = json.loads(held) if isinstance(held, str) else held
        shown = pictures.shown(doc if isinstance(doc, dict) else {})
        return notes_for(con, row["user_id"], [i for i in chosen if i in shown])
    user = current_teacher(request, con, session)
    return notes_for(con, user["id"], chosen)
