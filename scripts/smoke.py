"""One walk through the app, to tell a live app from a dead one.

    SMOKE_INVITE=<token> python - <url> < scripts/smoke.py
    python - --read-only <url> < scripts/smoke.py

Runs in the app's container with the image's own python, fed on stdin, so it is one file. The
read-only half is three GETs and one look into the database for a user, and writes nothing. The
full run signs a smoke user up with the invite, types into a sheet, saves, reloads and prints the
PDF: only ever on a copy of the data.
The job log is public, so the output names the steps and nothing else.
"""

import argparse
import io
import json
import os
import re
import secrets
import sqlite3
import sys
import urllib.error
import urllib.request
from http.cookies import SimpleCookie
from typing import Never
from urllib.parse import urljoin

# Milliseconds a wait in the browser may take.
WAIT = 30_000
JS = {"text/javascript", "application/javascript"}
NO_USER = (
    "the database the app reads has no user: the container's volume may point at the wrong "
    "folder. On a new machine make the admin with `python -m blattwerk invite --admin`, then rerun"
)

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("--read-only", action="store_true")
args = parser.parse_args()

step = "start"


def fail(reason: str) -> Never:
    print(f"smoke failed: {step}: {reason}", file=sys.stderr)
    sys.exit(1)


def passed(name: str) -> None:
    """Prints the step that is over and names the next one."""
    global step
    print(step, flush=True)
    step = name


def call(path: str, body: dict | None = None, cookie: str = "") -> tuple[str, bytes, str]:
    """Asks the app and wants a 200. Gives the content type, the body and the session cookie."""
    status, kind, data, session = ask(path, body, cookie)
    if status != 200:
        fail(f"status {status}")
    return kind, data, session


def ask(path: str, body: dict | None = None, cookie: str = "") -> tuple[int, str, bytes, str]:
    headers = {"Cookie": f"session={cookie}"} if cookie else {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(urljoin(args.url, path), data, headers)
    try:
        response = urllib.request.urlopen(request, timeout=30)
        status = response.status
    except urllib.error.HTTPError as error:
        # An answer like any other: the caller says which status it wants.
        response = error
        status = error.code
    with response:
        session = SimpleCookie(response.headers.get("Set-Cookie", "")).get("session")
        kind = response.headers.get_content_type()
        return status, kind, response.read(), session.value if session else ""


def read_only() -> None:
    global step
    step = "page"
    kind, html, _ = call("/")
    if kind != "text/html":
        fail(f"content type {kind}")
    passed("bundle")
    script = re.search(rb'<script[^>]*\ssrc="([^"]+)"', html)
    if not script:
        fail("no script in the page")
    # The app answers a missing file with the page itself: 200 and text/html.
    kind, _, _ = call(script[1].decode())
    if kind not in JS:
        fail(f"content type {kind}")
    passed("database")
    # The app looks the session up before it says 401, so a 401 is a database that opens.
    status = ask("/api/me")[0]
    if status != 401:
        fail(f"status {status}")


def users() -> None:
    """Reads the database itself: the app makes a missing one anew, and that one answers 401 too."""
    folder = os.environ.get("BLATTWERK_DATA_DIR")
    if not folder:
        fail("BLATTWERK_DATA_DIR is not set")
    # mode=ro: opens no file that is not there, and writes nothing.
    con = sqlite3.connect(f"file:{folder}/blattwerk.db?mode=ro", uri=True, timeout=5)
    try:
        count = con.execute("SELECT count(*) FROM users").fetchone()[0]
    finally:
        con.close()
    if not count:
        fail(NO_USER)


def full(token: str) -> None:
    # Here, not at the top: the read-only half gets by with the standard library.
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader

    email = f"smoke-{secrets.token_hex(8)}@smoke.invalid"
    password = secrets.token_urlsafe(24)
    word = f"smoke{secrets.token_hex(6)}"
    call("/api/signup", {"token": token, "email": email, "password": password})
    passed("login")
    session = call("/api/login", {"email": email, "password": password})[2]
    if not session:
        fail("no session cookie")
    passed("sheet")
    box = {"id": "a", "x": 15, "y": 50, "w": 180, "h": 20, "z": 1, "locked": False}
    block = {**box, "type": "text", "props": {"text": "Probe", "size": 14, "align": "left"}}
    doc = {"pages": [{"blocks": [block]}], "guides": {"x": [], "y": []}, "grid": 0}
    sheet = json.loads(call("/api/sheets", {"title": "Probe", "doc": doc}, session)[1])["id"]
    passed("editor")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(timeout=WAIT)
        context = browser.new_context(viewport={"width": 1400, "height": 1000})
        context.set_default_timeout(WAIT)
        # The tour would open on the first visit and lie over the sheet.
        context.add_init_script("localStorage.setItem('tour', '1')")
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        context.add_cookies([{"name": "session", "value": session, "url": args.url}])
        page = context.new_page()
        ready = page.locator('main.editor[data-ready="1"]')
        page.goto(urljoin(args.url, f"/blatt/{sheet}"))
        ready.wait_for()
        passed("save")
        # The editor saves two seconds after the last change. On a slow machine a save may go
        # out in the middle of the word, so the one to wait for is the one that holds all of it.
        with page.expect_response(lambda r: r.ok and word in (r.request.post_data or "")):
            page.locator('.block[data-id="a"]').click()
            page.keyboard.press("Enter")
            page.keyboard.type(word)
        stored = json.loads(call(f"/api/sheets/{sheet}", cookie=session)[1])["doc"]
        if word not in json.dumps(stored):
            fail("the stored sheet lacks the typed text")
        passed("reload")
        page.reload()
        ready.wait_for()
        page.locator('.block[data-id="a"]', has_text=word).wait_for()
        browser.close()
    passed("pdf")
    kind, data, _ = call(f"/api/sheets/{sheet}/pdf", cookie=session)
    if kind != "application/pdf":
        fail(f"content type {kind}")
    pages = len(PdfReader(io.BytesIO(data)).pages)
    if pages != 1:
        fail(f"{pages} pages")


try:
    token = os.environ.get("SMOKE_INVITE", "").rsplit("/", 1)[-1]
    if not args.read_only and not token:
        # Before the first request, so a run that cannot finish writes nothing.
        step = "invite"
        fail("SMOKE_INVITE is not set")
    read_only()
    if args.read_only:
        passed("users")
        users()
    else:
        passed("signup")
        full(token)
    passed("end")
except Exception as error:
    # The class and no more: a message may hold an address, a token or the sheet's text.
    fail(type(error).__name__)
print("smoke ok")
