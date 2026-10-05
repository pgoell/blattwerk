"""Feedback from a logged-in user: text, voice notes and photos, saved to disk."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from starlette.datastructures import UploadFile

from blattwerk import db
from blattwerk.auth import User

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
async def submit(user: User, request: Request) -> dict[str, str]:
    form = await request.form()
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%f")
    # Under the user's folder, so deleting the account deletes the feedback.
    out = db.DATA_DIR / "users" / str(user["id"]) / "feedback" / stamp
    out.mkdir(parents=True)

    fields = {k: v for k, v in form.multi_items() if isinstance(v, str)}
    # One counter per field, so a send's files read audio-1, photo-1, photo-2.
    counts: dict[str, int] = {}
    for field, upload in form.multi_items():
        if not isinstance(upload, UploadFile) or field not in ("audio", "photo"):
            continue
        counts[field] = counts.get(field, 0) + 1
        ext = FILE_TYPES.get((upload.content_type or "").split(";")[0], "bin")
        (out / f"{field}-{counts[field]}.{ext}").write_bytes(await upload.read())

    (out / "feedback.json").write_text(
        json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"saved": stamp}
