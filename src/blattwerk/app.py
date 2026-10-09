"""Blattomat: the API, the legal pages and the built frontend."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from blattwerk import auth, feedback, maths, pdf, sheets, templates, uploads

# `npm run build` in frontend/ writes here.
STATIC = Path(__file__).parent / "static"

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        # Opens the database, so the start makes a new file's tables and a request need not.
        auth.retry_leftovers()
    except Exception:
        # A busy database or a full disk must not keep the app down: the next start tries again.
        log.exception("Could not retry the left over folders")
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.include_router(auth.router)
app.include_router(feedback.router)
app.include_router(maths.router)
app.include_router(pdf.router)
app.include_router(sheets.router)
app.include_router(templates.router)
app.include_router(uploads.router)


@app.get("/impressum", response_class=HTMLResponse)
def impressum() -> str:
    return files("blattwerk").joinpath("impressum.html").read_text(encoding="utf-8")


@app.get("/datenschutz", response_class=HTMLResponse)
def datenschutz() -> str:
    return files("blattwerk").joinpath("datenschutz.html").read_text(encoding="utf-8")


@app.get("/{path:path}")
def frontend(path: str) -> FileResponse:
    # The frontend routes in the browser, so any path that is not a file gets the app.
    if path.startswith("api/"):
        raise HTTPException(404)
    file = (STATIC / path).resolve()
    if not file.is_file() or not file.is_relative_to(STATIC):
        file = STATIC / "index.html"
    if not file.is_file():
        raise HTTPException(404)
    return FileResponse(file)
