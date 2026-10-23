"""Uploads: the pictures of image blocks, kept per user on the data volume."""

import threading
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from blattwerk import folder, pdf, svg
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


@router.post("/uploads")
async def upload(file: UploadFile, user: Teacher, con: Con) -> dict:
    data = await file.read(MAX_BYTES + 1)
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
    upload_id = con.execute(
        "INSERT INTO uploads (user_id, type) VALUES (?, ?)", (user["id"], type_)
    ).lastrowid
    assert upload_id is not None
    out = path(user["id"], upload_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return {"id": upload_id}


def response(file: Path, type_: str) -> FileResponse:
    # An upload never changes, so the browser may keep it. A folder copy is the same bytes.
    headers = {"Cache-Control": "private, max-age=31536000, immutable", **NOSNIFF}
    if type_ == "image/svg+xml":
        headers |= SVG_CSP
    return FileResponse(file, media_type=type_, headers=headers)


@router.get("/uploads/{upload_id}")
def serve(
    upload_id: Id,
    request: Request,
    con: Con,
    session: Annotated[str | None, Cookie()] = None,
    token: pdf.Token = None,
) -> FileResponse:
    # Chromium, printing a sheet, stands for the sheet's owner, for that sheet's pictures alone.
    if token:
        user_id = pdf.shows(con, token, upload_id)
        row = con.execute(
            "SELECT type FROM uploads WHERE id = ? AND user_id = ?", (upload_id, user_id)
        ).fetchone()
        own = path(user_id, upload_id)
        if not row or not own.is_file():
            raise HTTPException(404, headers=NOSNIFF)
        return response(own, row["type"])
    user_id = current_teacher(request, con, session)["id"]
    row = con.execute(
        "SELECT type FROM uploads WHERE id = ? AND user_id = ?", (upload_id, user_id)
    ).fetchone()
    own = path(user_id, upload_id)
    if row and own.is_file():
        return response(own, row["type"])
    # A folder copy, for a teacher at that school, once the author's file is gone.
    copied = folder.served_copy(con, user_id, upload_id)
    if copied:
        return response(*copied)
    # Someone else's picture is as missing as one that never was.
    raise HTTPException(404, headers=NOSNIFF)
