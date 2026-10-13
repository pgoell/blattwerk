"""PDF: headless Chromium prints a sheet's render page, let in by a short-lived token."""

import hashlib
import hmac
import io
import json
import secrets
import sqlite3
import time
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from playwright.sync_api import sync_playwright
from pypdf import PdfWriter

from blattwerk import pictures, variants
from blattwerk.auth import User
from blattwerk.db import Con, Id
from blattwerk.sheets import find
from blattwerk.variants import LETTERS

# Seconds a token lasts: Chromium loads the page right after the token is made.
TTL = 60
# Made anew with each start: the token is made and checked in the same process.
SECRET = secrets.token_bytes(32)

router = APIRouter(prefix="/api")

# Chromium has no session cookie. It sends the token with every request it makes for the page.
Token = Annotated[str | None, Header(alias="X-Render-Token")]


def sign(sheet_id: int, expires: int) -> str:
    mac = hmac.new(SECRET, f"{sheet_id}.{expires}".encode(), hashlib.sha256).hexdigest()
    return f"{sheet_id}.{expires}.{mac}"


def new_token(sheet_id: int) -> str:
    return sign(sheet_id, int(time.time()) + TTL)


def opened(con: sqlite3.Connection, token: str | None) -> sqlite3.Row:
    """The sheet a token opens. A forged or old token is as good as none: 404."""
    token = token or ""
    try:
        sheet_id, expires, _ = token.split(".")
        good = int(expires) > time.time() and hmac.compare_digest(
            token.encode(), sign(int(sheet_id), int(expires)).encode()
        )
    except ValueError:
        good = False
    row = good and con.execute("SELECT * FROM sheets WHERE id = ?", (sheet_id,)).fetchone()
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
def variant(sheet_id: Id, letter: str, user: User, con: Con) -> dict:
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
    user: User,
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
