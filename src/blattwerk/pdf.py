"""PDF: headless Chromium prints a sheet's render page, let in by a short-lived token."""

import hashlib
import hmac
import io
import json
import secrets
import sqlite3
import threading
import time
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright
from pydantic import BaseModel
from pypdf import PdfWriter

from blattwerk import pictures, variants
from blattwerk.auth import Teacher
from blattwerk.db import Con, Id
from blattwerk.schema import check
from blattwerk.sheets import find
from blattwerk.variants import LETTERS

# Seconds a token lasts: Chromium loads the page right after the token is made.
TTL = 60
# Made anew with each start: the token is made and checked in the same process.
SECRET = secrets.token_bytes(32)
# Docs posted for a preview, while Chromium prints them. Keys start with "p", sheet ids are digits.
POSTED: dict[str, dict] = {}
# Each preview is a Chromium: two at once, and a burst waits WAIT seconds for a turn, then gets 503.
SLOTS = threading.BoundedSemaphore(2)
WAIT = 10
# A preview holds one of the server's threads while it runs or waits, and Chromium's own requests
# for the page need others: so two may wait beside the two that run, and the rest get 503 at once.
ROOM = threading.BoundedSemaphore(4)
# Milliseconds a preview's page may take to draw before the doc is refused as one no page can draw.
DRAW = 15000
# Drawn on a preview only: each block's box in magenta, with its id. The PDF never gets them.
OUTLINES = """
.print .block { outline: 1px solid magenta; outline-offset: -1px; }
.print .block::before { content: attr(data-block); position: absolute; top: 0; left: 0;
  font: bold 11px sans-serif; color: magenta; background: white; }
"""

router = APIRouter(prefix="/api")

# Chromium has no session cookie. It sends the token with every request it makes for the page.
Token = Annotated[str | None, Header(alias="X-Render-Token")]


def sign(name: str, expires: int) -> str:
    mac = hmac.new(SECRET, f"{name}.{expires}".encode(), hashlib.sha256).hexdigest()
    return f"{name}.{expires}.{mac}"


def new_token(name: int | str) -> str:
    """A token for a sheet's id, or for a posted doc's key."""
    return sign(str(name), int(time.time()) + TTL)


def opened(con: sqlite3.Connection, token: str | None) -> sqlite3.Row | dict:
    """The sheet, or posted doc, a token opens. A forged or old token is as good as none: 404."""
    token = token or ""
    try:
        name, expires, _ = token.split(".")
        good = int(expires) > time.time() and hmac.compare_digest(
            token.encode(), sign(name, int(expires)).encode()
        )
    except ValueError:
        good = False
    if not good:
        raise HTTPException(404)
    if name.startswith("p"):
        row = POSTED.get(name)
    else:
        row = con.execute("SELECT * FROM sheets WHERE id = ?", (name,)).fetchone()
    if not row:
        raise HTTPException(404)
    return row


def shows(con: sqlite3.Connection, token: str | None, upload_id: int) -> int:
    """The owner of the sheet a token opens, if that sheet shows the picture."""
    row = opened(con, token)
    if upload_id not in pictures.shown(json.loads(row["doc"])):
        raise HTTPException(404)
    return row["user_id"]


@router.get("/render/{sheet_id}")
def render(
    sheet_id: Id,
    con: Con,
    token: Token = None,
    variante: Literal["A", "B", "C", "D"] | None = None,
) -> dict:
    row = opened(con, token)
    if row["id"] != sheet_id:
        raise HTTPException(404)
    if variante:
        return variants.vary(json.loads(row["doc"]), variante)[0]
    return json.loads(row["doc"])


@router.get("/sheets/{sheet_id}/variante/{letter}")
def variant(sheet_id: Id, letter: str, user: Teacher, con: Con) -> dict:
    # The sheet first: a stranger gets 404 whatever the letter, as for every call for an item.
    sheet = find(con, sheet_id, user)
    if letter not in list(LETTERS):
        raise HTTPException(404)
    doc, short = variants.vary(sheet["doc"], letter)
    return {"doc": doc, "short": short}


@router.get("/sheets/{sheet_id}/pdf")
def pdf(
    sheet_id: Id,
    request: Request,
    user: Teacher,
    con: Con,
    solved: bool = False,
    varianten: Annotated[int, Query(ge=1, le=4)] = 1,
    buchstaben: bool = True,
) -> Response:
    sheet = find(con, sheet_id, user)
    # Chromium calls this same server, on the port the request came in by.
    url = f"http://127.0.0.1:{request.scope['server'][1]}/druck/{sheet_id}"
    if varianten == 1:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(extra_http_headers={"X-Render-Token": new_token(sheet_id)})
            page.goto(url + ("?loesungen" if solved else ""))
            # The page says when its fonts and pictures have loaded.
            page.wait_for_selector("body.ready", state="attached")
            # A4 with no margin of the printer's: the sheet's own margins are the page's. The
            # stylesheet says which pages lie on their side.
            data = page.pdf(prefer_css_page_size=True, print_background=True)
            browser.close()
        # Chromium names itself as the file's maker, and has no setting for that. The title is the
        # page's own.
        writer = PdfWriter(clone_from=io.BytesIO(data))
    else:
        short = [
            {**entry, "letter": letter}
            for letter in LETTERS[:varianten]
            for entry in variants.vary(sheet["doc"], letter)[1]
        ]
        if short:
            raise HTTPException(409, detail={"short": short})
        writer = PdfWriter()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for letter in LETTERS[:varianten]:
                # A fresh page and token for each variant: the old `body.ready` is never seen.
                query = []
                if letter != "A":
                    query.append(f"variante={letter}")
                if buchstaben or solved:
                    query.append(f"buchstabe={letter}")
                if solved:
                    query.append("loesungen")
                page = browser.new_page(extra_http_headers={"X-Render-Token": new_token(sheet_id)})
                page.goto(url + ("?" + "&".join(query) if query else ""))
                page.wait_for_selector("body.ready", state="attached")
                data = page.pdf(prefer_css_page_size=True, print_background=True)
                page.close()
                writer.append(io.BytesIO(data))
            browser.close()
    writer.add_metadata({"/Creator": "Blattomat", "/Producer": "Blattomat"})
    out = io.BytesIO()
    writer.write(out)
    name = quote(sheet["title"] + (" Lösungen" if solved else "") + ".pdf")
    return Response(
        out.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"},
    )


class Posted(BaseModel):
    doc: dict


def snap(
    request: Request, token: str, sheet_id: int, doc: dict, page: int, outlines: bool
) -> bytes:
    """One page of a doc as a PNG about 1000 px wide: Chromium prints the page, shot alone."""
    # A sheet from before pages holds its blocks at the top: one page.
    pages = doc.get("pages", [doc])
    if page > len(pages):
        raise HTTPException(404, detail=f"page {page}: the sheet has {len(pages)} pages")
    landscape = pages[page - 1].get("landscape", doc.get("landscape"))
    # A4 is 210 mm wide, or 297 mm lying on its side; 96 px to the inch.
    scale = 1000 / ((297 if landscape else 210) * 96 / 25.4)
    url = f"http://127.0.0.1:{request.scope['server'][1]}/druck/{sheet_id}"
    if not ROOM.acquire(blocking=False):
        raise HTTPException(503, headers={"Retry-After": "5"})
    try:
        return shoot(url, token, scale, page, outlines)
    finally:
        ROOM.release()


def shoot(url: str, token: str, scale: float, page: int, outlines: bool) -> bytes:
    if not SLOTS.acquire(timeout=WAIT):
        raise HTTPException(503, headers={"Retry-After": "5"})
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                context = browser.new_context(
                    viewport={"width": 1400, "height": 1400},
                    device_scale_factor=scale,
                    extra_http_headers={"X-Render-Token": token},
                )
                tab = context.new_page()
                errors: list[str] = []
                tab.on("pageerror", lambda error: errors.append(error.message))
                tab.emulate_media(media="print")
                tab.goto(url)
                try:
                    tab.wait_for_selector("body.ready", state="attached", timeout=DRAW)
                except PlaywrightTimeout:
                    why = errors[0] if errors else "it did not finish"
                    raise HTTPException(
                        422, detail={"problems": [f"doc: the page could not be drawn: {why}"]}
                    ) from None
                if outlines:
                    tab.add_style_tag(content=OUTLINES)
                return tab.locator(".print .paper").nth(page - 1).screenshot()
            finally:
                browser.close()
    finally:
        SLOTS.release()


@router.get("/sheets/{sheet_id}/preview.png")
def sheet_preview(
    sheet_id: Id,
    request: Request,
    user: Teacher,
    con: Con,
    page: Annotated[int, Query(ge=1)] = 1,
    outlines: bool = False,
) -> Response:
    sheet = find(con, sheet_id, user)
    png = snap(request, new_token(sheet_id), sheet_id, sheet["doc"], page, outlines)
    return Response(png, media_type="image/png")


@router.post("/preview.png")
def posted_preview(
    body: Posted,
    request: Request,
    user: Teacher,
    page: Annotated[int, Query(ge=1)] = 1,
    outlines: bool = False,
) -> Response:
    check(body.doc)
    # Held in memory for the print alone: the doc is never written to the database.
    key = "p" + secrets.token_urlsafe(16)
    POSTED[key] = {"id": 0, "user_id": user["id"], "doc": json.dumps(body.doc)}
    try:
        png = snap(request, new_token(key), 0, body.doc, page, outlines)
    finally:
        POSTED.pop(key, None)
    return Response(png, media_type="image/png")
