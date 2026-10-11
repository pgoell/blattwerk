"""Uploads: the pictures of image blocks, kept per user on the data volume."""

from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, UploadFile
from fastapi.responses import FileResponse

from blattwerk import pdf
from blattwerk.auth import User, current_user
from blattwerk.db import Con, Id
from blattwerk.pictures import path

MAX_BYTES = 15 * 2**20

router = APIRouter(prefix="/api")


def kind(data: bytes) -> str | None:
    """The type the first bytes show, for the four a browser draws and no others: no SVG, no PDF.

    What a file declares is no evidence: the type is the bytes', or the file is no picture.
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.post("/uploads")
async def upload(file: UploadFile, user: User, con: Con) -> dict:
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413)
    type_ = kind(data)
    if type_ is None:
        raise HTTPException(415)
    upload_id = con.execute(
        "INSERT INTO uploads (user_id, type) VALUES (?, ?)", (user["id"], type_)
    ).lastrowid
    assert upload_id is not None
    out = path(user["id"], upload_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return {"id": upload_id}


@router.get("/uploads/{upload_id}")
def serve(
    upload_id: Id,
    con: Con,
    session: Annotated[str | None, Cookie()] = None,
    token: pdf.Token = None,
) -> FileResponse:
    # Chromium, printing a sheet, stands for the sheet's owner, for that sheet's pictures alone.
    user_id = pdf.shows(con, token, upload_id) if token else current_user(con, session)["id"]
    row = con.execute(
        "SELECT type FROM uploads WHERE id = ? AND user_id = ?", (upload_id, user_id)
    ).fetchone()
    # Someone else's picture is as missing as one that never was, and so is a row whose file a
    # sweep deleted before it failed to delete the row.
    if not row or not path(user_id, upload_id).is_file():
        raise HTTPException(404)
    # An upload never changes, so the browser may keep it.
    headers = {"Cache-Control": "private, max-age=31536000, immutable"}
    return FileResponse(path(user_id, upload_id), media_type=row["type"], headers=headers)
