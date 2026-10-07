import io
import re
import struct
import threading
import time
import zlib

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from pypdf import PdfReader

from blattwerk import auth, db, pdf
from blattwerk.app import STATIC, app

PASSWORD = "richtig-geheim"
MATHS = {"ops": ["+"], "max": 20, "count": 3, "seed": 7}
RED = b"\xff\x00\x00"


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    return tmp_path


def user(email):
    """A client logged in as a new user. https, or the Secure cookie is not sent back."""
    client = TestClient(app, base_url="https://testserver")
    body = {"token": auth.new_link(db.open_db()), "email": email, "password": PASSWORD}
    assert client.post("/api/signup", json=body).status_code == 200
    return client


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(colour=RED):
    """A picture a browser can draw: three by two pixels of one colour."""
    head = struct.pack(">IIBBBBB", 3, 2, 8, 2, 0, 0, 0)
    rows = zlib.compress((b"\x00" + colour * 3) * 2)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", rows) + chunk(b"IEND", b"")


def upload(client):
    return client.post("/api/uploads", files={"file": ("bild", png(), "image/png")}).json()["id"]


def block(kind, y, h, props):
    box = {"id": kind, "x": 15, "y": y, "w": 180, "h": h, "z": 1, "locked": False}
    return {**box, "type": kind, "props": props}


def picture(upload_id):
    return block("image", 150, 60, {"upload": upload_id, "ratio": 1.5, "cut": [0, 0, 0, 0]})


def sheet(client, *pages):
    doc = {"pages": [{"blocks": list(p)} for p in pages], "guides": {"x": [], "y": []}, "grid": 0}
    return client.post("/api/sheets", json={"title": "Plus bis 20", "doc": doc}).json()


def chromium(token):
    """As Chromium asks: no session, the token in a header."""
    return TestClient(app, base_url="https://testserver", headers={"X-Render-Token": token})


def test_token_opens_its_sheet_and_no_other():
    client = user("a@example.com")
    mine = sheet(client, [])
    other = sheet(client, [])
    token = pdf.new_token(mine["id"])
    assert chromium(token).get(f"/api/render/{mine['id']}").json() == mine["doc"]
    assert chromium(token).get(f"/api/render/{other['id']}").status_code == 404
    # The token is no session.
    assert chromium(token).get(f"/api/sheets/{mine['id']}").status_code == 401
    assert chromium(token).get("/api/sheets").status_code == 401


def test_bad_tokens_open_nothing(monkeypatch):
    client = user("a@example.com")
    first = sheet(client, [])["id"]
    other = sheet(client, [])["id"]
    url = f"/api/render/{first}"
    token = pdf.new_token(first)
    sheet_id, expires, mac = token.split(".")
    assert chromium(token).get(url).status_code == 200
    forged = [
        "",
        "1",
        "x.y.z",
        f"{sheet_id}.{expires}",
        f"{sheet_id}.{expires}.{'0' * len(mac)}",
        # A longer life, or another way to write the sheet, under the first token's signature.
        f"{sheet_id}.{int(expires) + 60}.{mac}",
        f"0{sheet_id}.{expires}.{mac}",
    ]
    for bad in forged:
        assert chromium(bad).get(url).status_code == 404, bad
    # Another sheet under the first token's signature.
    assert chromium(f"{other}.{expires}.{mac}").get(f"/api/render/{other}").status_code == 404
    # A token for a sheet since deleted.
    gone = pdf.new_token(other)
    assert chromium(gone).get(f"/api/render/{other}").status_code == 200
    client.delete(f"/api/sheets/{other}")
    assert chromium(gone).get(f"/api/render/{other}").status_code == 404
    # A token from before a restart.
    monkeypatch.setattr(pdf, "SECRET", b"another")
    assert chromium(token).get(url).status_code == 404


def test_old_token_opens_nothing(monkeypatch):
    client = user("a@example.com")
    shown = upload(client)
    mine = sheet(client, [picture(shown)])
    fresh = chromium(pdf.new_token(mine["id"]))
    assert fresh.get(f"/api/render/{mine['id']}").status_code == 200
    assert fresh.get(f"/api/uploads/{shown}").status_code == 200
    monkeypatch.setattr(pdf, "TTL", -1)
    old = chromium(pdf.new_token(mine["id"]))
    assert old.get(f"/api/render/{mine['id']}").status_code == 404
    assert old.get(f"/api/uploads/{shown}").status_code == 404


def test_token_opens_the_pictures_on_its_sheet_and_no_other():
    client = user("a@example.com")
    stranger = user("b@example.com")
    shown, unused, foreign = upload(client), upload(client), upload(stranger)
    # A sheet can name someone else's picture; that does not make it the sheet's.
    mine = sheet(client, [], [picture(shown), picture(foreign)])
    elsewhere = sheet(client, [picture(unused)])
    token = pdf.new_token(mine["id"])
    assert chromium(token).get(f"/api/uploads/{shown}").content == png()
    assert chromium(token).get(f"/api/uploads/{unused}").status_code == 404
    assert chromium(token).get(f"/api/uploads/{foreign}").status_code == 404
    assert chromium(token).get("/api/uploads/99").status_code == 404
    assert chromium(pdf.new_token(elsewhere["id"])).get(f"/api/uploads/{shown}").status_code == 404
    # A session does not make up for a bad token, and no token at all needs a session.
    assert client.get(f"/api/uploads/{shown}", headers={"X-Render-Token": "x"}).status_code == 404
    assert chromium("").get(f"/api/uploads/{shown}").status_code == 401


def test_pdf_of_someone_elses_sheet_is_missing():
    client = user("a@example.com")
    stranger = user("b@example.com")
    mine = sheet(client, [])
    assert stranger.get(f"/api/sheets/{mine['id']}/pdf").status_code == 404
    assert stranger.get(f"/api/sheets/{mine['id']}/pdf?solved=true").status_code == 404
    assert client.get("/api/sheets/99/pdf").status_code == 404
    # The render call knows no session, the owner's neither.
    assert stranger.get(f"/api/render/{mine['id']}").status_code == 404
    assert client.get(f"/api/render/{mine['id']}").status_code == 404
    assert TestClient(app).get(f"/api/sheets/{mine['id']}/pdf").status_code == 401
    assert TestClient(app).get(f"/api/render/{mine['id']}").status_code == 404


@pytest.fixture
def server():
    """The app on a real port, for Chromium to call as it does in production."""
    assert (STATIC / "index.html").is_file(), "build the frontend first: mise run build"
    server = uvicorn.Server(uvicorn.Config(app, port=0, log_level="warning"))
    thread = threading.Thread(target=server.run)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"
    server.should_exit = True
    thread.join()


def test_chromium_prints_the_sheet_and_its_answer_key(server):
    client = user("a@example.com")
    made = client.post("/api/maths", json=MATHS).json()
    maths = {**MATHS, **made, "format": "row", "columns": 3, "size": 14}
    text = {"text": "Rechne aus", "size": 24, "align": "center", "font": "grund"}
    mine = sheet(
        client,
        [block("text", 15, 14, text), block("maths", 40, 30, maths), picture(upload(client))],
        [block("name", 15, 10, {})],
    )
    # The session cookie is Secure and this server speaks http, so it goes by hand.
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    url = f"{server}/api/sheets/{mine['id']}/pdf"

    for solved in (False, True):
        res = httpx.get(url, params={"solved": solved}, headers=cookie, timeout=60)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        name = "Plus%20bis%2020%20L%C3%B6sungen.pdf" if solved else "Plus%20bis%2020.pdf"
        assert res.headers["content-disposition"] == f"attachment; filename*=UTF-8''{name}"
        pages = PdfReader(io.BytesIO(res.content)).pages
        # One page of A4 for each page of the sheet. A page's box is in points, 72 to the inch.
        sizes = [[round(float(n) / 72 * 25.4) for n in page.mediabox[2:]] for page in pages]
        assert sizes == [[210, 297]] * 2
        first, second = (" ".join(page.extract_text().split()) for page in pages)
        assert "Name:" in second
        assert len(pages[0].images) == 1
        # The sheet's own fonts are in the file, so they had loaded when the page was printed.
        fonts = set(re.findall(rb"/FontName /\w+\+(\w+)", res.content))
        assert fonts == {b"Andika", b"PlaywriteDEGrund"}
        # Only the answer key holds the answers, and it says so on each page.
        assert [("Lösungen" in page) for page in (first, second)] == [solved, solved]
        for e in made["exercises"]:
            assert (f"{e['a']} + {e['b']} = {e['result']}" in first) == solved


def test_chromium_prints_old_plain_text_and_rich_text(server):
    client = user("a@example.com")
    # A text as sheets saved before hold it, and one with paragraphs of its own beside the words.
    old = {"text": "Alter Text\nzweite Zeile", "size": 14, "align": "left"}
    rich = [
        {"runs": [{"text": "Lies "}, {"text": "genau", "bold": True, "color": "#c01c28"}]},
        {"runs": [{"text": "erstens", "italic": True}], "list": "number"},
        {"runs": [{"text": "tiefer", "underline": True}], "list": "number", "level": 1},
        {"runs": [{"text": "zweitens"}], "list": "number"},
        {"runs": []},
        {"runs": [{"text": "Punkt"}], "list": "bullet"},
    ]
    new = {**old, "text": "Lies genau\nerstens\ntiefer\nzweitens\n\nPunkt", "rich": rich}
    shape = {"kind": "rect", "fill": "none", "stroke": "#222222", "strokeWidth": 0.5}
    mine = sheet(
        client,
        [block("text", 15, 20, old), {**block("text", 40, 60, new), "id": "new"}],
        [block("shape", 15, 40, {**shape, "text": "Im Kasten", "rich": rich[:1]})],
    )
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    first, second = (
        " ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(res.content)).pages
    )
    assert "Alter Text zweite Zeile" in first
    # The numbers of a list are the page's own; each level counts for itself.
    assert "Lies genau 1. erstens 1. tiefer 2. zweitens • Punkt" in first
    # A shape draws its paragraphs, not the plain words beside them.
    assert "Lies genau" in second and "Im Kasten" not in second
    # The bold and the italic run bring their cuts of the font into the file.
    fonts = set(re.findall(rb"/FontName /\w+\+([\w-]+)", res.content))
    assert fonts == {b"Andika", b"Andika-Bold", b"Andika-Italic"}


def test_chromium_prints_each_page_upright_or_on_its_side(server):
    client = user("a@example.com")
    # The sheet lies on its side; the second page has a format of its own.
    pages = [{"blocks": []}, {"blocks": [], "landscape": False}, {"blocks": []}]
    doc = {"pages": pages, "guides": {"x": [], "y": []}, "grid": 0, "landscape": True}
    mine = client.post("/api/sheets", json={"title": "Quer", "doc": doc}).json()
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    pages = PdfReader(io.BytesIO(res.content)).pages
    sizes = [[round(float(n) / 72 * 25.4) for n in page.mediabox[2:]] for page in pages]
    assert sizes == [[297, 210], [210, 297], [297, 210]]


def test_chromium_prints_a_table(server):
    client = user("a@example.com")
    cells = [["H", "Z", "E"], ["3", "", "7"], ["Hundert\nund eins", "", ""]]
    props = {"cells": cells, "cols": [1, 2, 1], "size": 14, "align": "center", "line": "#222222"}
    mine = sheet(client, [block("table", 15, 40, {**props, "head": True})])
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    text = " ".join(PdfReader(io.BytesIO(res.content)).pages[0].extract_text().split())
    # Every cell's text is there, row by row; an empty cell prints nothing.
    assert text == "H Z E 3 7 Hundert und eins"
    # The head row brings the bold cut of the font into the file.
    fonts = set(re.findall(rb"/FontName /\w+\+([\w-]+)", res.content))
    assert fonts == {b"Andika", b"Andika-Bold"}
