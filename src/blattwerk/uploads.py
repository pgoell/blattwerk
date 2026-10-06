"""Uploads: the pictures of image blocks, kept per user on the data volume."""

import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from blattwerk import db
from blattwerk.auth import User
from blattwerk.db import Con

# What a browser draws and cannot run: no SVG.
TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 15 * 2**20

router = APIRouter(prefix="/api")


def path(user: sqlite3.Row, upload_id: int) -> Path:
    # Under the user's folder, so deleting the account deletes the pictures.
    return db.DATA_DIR / "users" / str(user["id"]) / "uploads" / str(upload_id)


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
    out = path(user, upload_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return {"id": upload_id}


@router.get("/uploads/{upload_id}")
def serve(upload_id: int, user: User, con: Con) -> FileResponse:
    row = con.execute(
        "SELECT type FROM uploads WHERE id = ? AND user_id = ?", (upload_id, user["id"])
    ).fetchone()
    # Someone else's picture is as missing as one that never was.
    if not row:
        raise HTTPException(404)
    # An upload never changes, so the browser may keep it.
    headers = {"Cache-Control": "private, max-age=31536000, immutable"}
    return FileResponse(path(user, upload_id), media_type=row["type"], headers=headers)
