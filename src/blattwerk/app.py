"""Blattomat: the API, the legal pages and the built frontend."""

import json
import logging
import os
import zipfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.resources import files
from pathlib import Path

import markdown
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from blattwerk import (
    auth,
    feedback,
    maths,
    oauth,
    pdf,
    remote,
    sheets,
    templates,
    texthelp,
    uploads,
)

# `npm run build` in frontend/ writes here.
STATIC = Path(__file__).parent / "static"

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    try:
        # Opens the database, so the start makes a new file's tables and a request need not.
        auth.retry_leftovers()
    except Exception:
        # A busy database or a full disk must not keep the app down: the next start tries again.
        log.exception("Could not retry the left over folders")
    yield
    remote.stop()


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.include_router(auth.router)
app.include_router(feedback.router)
app.include_router(maths.router)
app.include_router(oauth.router)
app.include_router(pdf.router)
app.include_router(remote.router)
app.include_router(sheets.router)
app.include_router(templates.router)
app.include_router(texthelp.router)
app.include_router(uploads.router)


@app.get("/impressum", response_class=HTMLResponse)
def impressum() -> str:
    return files("blattwerk").joinpath("impressum.html").read_text(encoding="utf-8")


@app.get("/datenschutz", response_class=HTMLResponse)
def datenschutz() -> str:
    return files("blattwerk").joinpath("datenschutz.html").read_text(encoding="utf-8")


ANLEITUNG_HEAD = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dein erstes Blatt mit Claude: Blattomat</title>
<style>
  :root {
    --bg: #f6f2e9; --ink: #1d2721; --muted: #667066; --accent: #2f6f4f;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #171a17; --ink: #ebe8df; --muted: #a2a79d; --accent: #7cc79a; }
  }
  body {
    margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.6 system-ui, sans-serif;
  }
  main { max-width: 680px; margin: 0 auto; padding: 24px 16px 64px; }
  h1 { font-size: 1.6rem; }
  h2 { font-size: 1.15rem; margin-top: 2em; }
  a { color: var(--accent); }
  code { font-size: 0.95em; }
</style>
</head>
<body>
<main>
  <p><a href="/">← Blattomat</a></p>
"""


@app.get("/anleitung/claude", response_class=HTMLResponse)
def anleitung_claude() -> str:
    # Read per request, so BLATTWERK_DOCS can point elsewhere in a test.
    docs = remote.ROOT / "docs" / "okf"
    if "BLATTWERK_DOCS" in os.environ:
        docs = Path(os.environ["BLATTWERK_DOCS"])
    text = (docs / "tutorials" / "dein-erstes-blatt-mit-claude.md").read_text(encoding="utf-8")
    # Strip the YAML frontmatter, the block between the first two `---` lines.
    # sane_lists keeps a list's first number: Schritt 3 goes on at 4 after its paragraph.
    body = markdown.markdown(text.split("---", 2)[2], extensions=["sane_lists"])
    return ANLEITUNG_HEAD + body + "</main>\n</body>\n</html>\n"


@app.get("/api/mcpb/version")
def mcpb_version() -> dict[str, str]:
    # The version the Claude Desktop extension was built with: an old copy asks to be reloaded.
    file = STATIC / "blattomat.mcpb"
    if not file.is_file():
        raise HTTPException(404)
    try:
        with zipfile.ZipFile(file) as z:
            version = json.loads(z.read("manifest.json"))["version"]
            return {"version": version, "fingerprint": z.read("fingerprint.txt").decode()}
    except KeyError, zipfile.BadZipFile:
        # A bundle from before the fingerprint, or a broken one: the extension then says nothing.
        raise HTTPException(404) from None


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
    # The Claude Desktop extension, a zip that mimetypes does not know: a file to save, not text.
    if file.suffix == ".mcpb":
        return FileResponse(file, media_type="application/octet-stream")
    return FileResponse(file)
