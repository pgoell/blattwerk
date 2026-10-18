"""Feedback from a logged-in user or the MCP: text, voice notes, photos and the screen, saved."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from starlette.datastructures import UploadFile

from blattwerk import auth, db
from blattwerk.auth import Teacher

FILE_TYPES = {
    "audio/webm": "webm",
    "audio/mp4": "m4a",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/webp": "webp",
}

router = APIRouter(prefix="/api")


@router.post("/feedback")
async def submit(user: Teacher, con: db.Con, request: Request) -> dict[str, str]:
    # A program (the MCP) may send in a loop: 10 sends per 15 minutes, then 429.
    if "authorization" in request.headers:
        auth.limit(con, f"feedback:{user['id']}")
    form = await request.form()
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%f")
    # Under the user's folder, so deleting the account deletes the feedback.
    out = db.DATA_DIR / "users" / str(user["id"]) / "feedback" / stamp
    out.mkdir(parents=True)

    fields = {k: v for k, v in form.multi_items() if isinstance(v, str)}
    # Only a send with an API token (the MCP) may say where it came from: the app's has no source.
    if "authorization" not in request.headers:
        fields.pop("source", None)
    # One counter per field, so a send's files read audio-1, photo-1, photo-2.
    counts: dict[str, int] = {}
    for field, upload in form.multi_items():
        if not isinstance(upload, UploadFile) or field not in ("audio", "photo", "screenshot"):
            continue
        counts[field] = counts.get(field, 0) + 1
        ext = FILE_TYPES.get((upload.content_type or "").split(";")[0], "bin")
        (out / f"{field}-{counts[field]}.{ext}").write_bytes(await upload.read())

    (out / "feedback.json").write_text(
        json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"saved": stamp}
