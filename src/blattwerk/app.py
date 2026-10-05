"""Interview form and photo upload: answers, voice notes and photos, saved to disk."""

import json
import os
import secrets
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from starlette.datastructures import UploadFile

TOKEN = os.environ.get("BLATTWERK_TOKEN", "")
DATA_DIR = Path(os.environ.get("BLATTWERK_DATA_DIR", "data"))
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

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def check(token: str) -> None:
    # An empty TOKEN means no link opens the form.
    if not TOKEN or not secrets.compare_digest(token, TOKEN):
        raise HTTPException(404)


@app.get("/i/{token}", response_class=HTMLResponse)
def form(token: str) -> str:
    check(token)
    return files("blattwerk").joinpath("form.html").read_text(encoding="utf-8")


@app.get("/i/{token}/fotos", response_class=HTMLResponse)
def photos(token: str) -> str:
    check(token)
    return files("blattwerk").joinpath("photos.html").read_text(encoding="utf-8")


@app.post("/i/{token}")
@app.post("/i/{token}/fotos")
async def submit(token: str, request: Request) -> dict[str, str]:
    check(token)
    form = await request.form()
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%f")
    out = DATA_DIR / stamp
    out.mkdir(parents=True)

    answers = {k: v for k, v in form.multi_items() if isinstance(v, str)}
    # One counter per field, so a send's files read audio-1, photo-1, photo-2.
    counts: dict[str, int] = {}
    for field, upload in form.multi_items():
        if not isinstance(upload, UploadFile) or field not in ("audio", "photo"):
            continue
        counts[field] = counts.get(field, 0) + 1
        ext = FILE_TYPES.get((upload.content_type or "").split(";")[0], "bin")
        (out / f"{field}-{counts[field]}.{ext}").write_bytes(await upload.read())

    (out / "answers.json").write_text(
        json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"saved": stamp}
