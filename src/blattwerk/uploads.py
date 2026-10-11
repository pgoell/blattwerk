"""Uploads: the pictures of image blocks, kept per user on the data volume."""

from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, UploadFile
from fastapi.responses import FileResponse

from blattwerk import pdf
from blattwerk.auth import User, current_user
from blattwerk.db import Con, Id
from blattwerk.pictures import path

# What a browser draws and cannot run: no SVG.
TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 15 * 2**20

router = APIRouter(prefix="/api")


@router.post("/uploads")
async def upload(file: UploadFile, user: User, con: Con) -> dict:
    if file.content_type not in TYPES:
        raise HTTPException(415)
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413)
    upload_id = con.execute(
        "INSERT INTO uploads (user_id, type) VALUES (?, ?)", (user["id"], file.content_type)
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
