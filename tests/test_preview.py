"""Previews: a PNG of one page of a sheet, as saved or as posted, printed by Chromium."""

import io
import threading

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from ui import MATHS, TEXT, block, picture, sheet, upload, user

from blattwerk import db, pdf
from blattwerk.app import app

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def cookie(client):
    return {"Cookie": f"session={client.cookies['session']}"}


def image(data):
    return Image.open(io.BytesIO(data)).convert("RGB")


def has_red(data):
    return any(colour == (255, 0, 0) for _, colour in image(data).getcolors(maxcolors=2**24))


def rows():
    """The row count of every table in the database."""
    con = db.open_db()
    names = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    return {name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in names}


def test_preview_of_a_saved_sheet(server):
    client = user()
    mine = sheet(client, [block("text", 15, 14, TEXT)])
    res = httpx.get(
        f"{server}/api/sheets/{mine['id']}/preview.png", headers=cookie(client), timeout=60
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content.startswith(PNG_SIGNATURE)
    assert 990 <= image(res.content).width <= 1010


def test_preview_of_a_posted_doc(server):
    client = user()
    doc = sheet(client, [block("text", 15, 14, TEXT)])["doc"]
    before = rows()
    res = httpx.post(
        f"{server}/api/preview.png", json={"doc": doc}, headers=cookie(client), timeout=60
    )
    assert res.status_code == 200
    assert res.content.startswith(PNG_SIGNATURE)
    # Nothing is written: not a sheet, a picture or a word.
    assert rows() == before


def test_preview_of_a_posted_doc_shows_its_own_picture_and_no_other(server):
    client = user()
    stranger = user()
    shown, foreign = upload(client), upload(stranger)

    def posted(upload_id):
        doc = {"pages": [{"blocks": [picture(upload_id)]}], "guides": {"x": [], "y": []}, "grid": 0}
        res = httpx.post(
            f"{server}/api/preview.png", json={"doc": doc}, headers=cookie(client), timeout=60
        )
        assert res.status_code == 200
        return res.content

    assert has_red(posted(shown))
    assert not has_red(posted(foreign))


def test_preview_of_a_landscape_page_is_about_1000_wide(server):
    client = user()
    doc = {
        "pages": [{"blocks": [block("text", 15, 14, TEXT)], "landscape": True}],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    res = httpx.post(
        f"{server}/api/preview.png", json={"doc": doc}, headers=cookie(client), timeout=60
    )
    assert res.status_code == 200
    assert 990 <= image(res.content).width <= 1010


def test_preview_of_a_foreign_sheet_is_missing():
    client = user()
    stranger = user()
    mine = sheet(client, [])
    assert stranger.get(f"/api/sheets/{mine['id']}/preview.png").status_code == 404


def test_preview_needs_a_login():
    client = user()
    mine = sheet(client, [])
    anon = TestClient(app, base_url="https://testserver")
    assert anon.get(f"/api/sheets/{mine['id']}/preview.png").status_code == 401
    assert anon.post("/api/preview.png", json={"doc": mine["doc"]}).status_code == 401


def test_preview_of_a_bad_page(server):
    client = user()
    mine = sheet(client, [block("text", 15, 14, TEXT)])
    url = f"/api/sheets/{mine['id']}/preview.png"
    assert client.get(url, params={"page": 0}).status_code == 422
    assert client.get(url, params={"page": "x"}).status_code == 422
    res = client.get(url, params={"page": 2})
    assert res.status_code == 404
    assert res.json()["detail"] == "page 2: the sheet has 1 pages"


def test_posted_doc_is_checked_and_names_the_path():
    client = user()
    # A place that is no number: the editor could not open this sheet, so the check refuses it.
    bad = {**block("maths", 40, 30, MATHS), "y": "high"}
    doc = {"pages": [{"blocks": [bad]}], "guides": {"x": [], "y": []}, "grid": 0}
    res = client.post("/api/preview.png", json={"doc": doc})
    assert res.status_code == 422
    assert any("pages[0].blocks[0]" in text for text in res.json()["detail"]["problems"])


def test_a_burst_waits_then_gets_503(monkeypatch):
    client = user()
    mine = sheet(client, [])
    monkeypatch.setattr(pdf, "WAIT", 1)
    pdf.SLOTS.acquire()
    pdf.SLOTS.acquire()
    try:
        res = client.get(f"/api/sheets/{mine['id']}/preview.png")
    finally:
        pdf.SLOTS.release()
        pdf.SLOTS.release()
    assert res.status_code == 503
    assert res.headers["retry-after"] == "5"


def test_a_burst_waiter_gets_its_png_when_a_slot_frees(server):
    client = user()
    mine = sheet(client, [block("text", 15, 14, TEXT)])
    pdf.SLOTS.acquire()
    pdf.SLOTS.acquire()
    # One slot frees while the request waits; the test keeps the other.
    timer = threading.Timer(0.5, pdf.SLOTS.release)
    timer.start()
    try:
        res = httpx.get(
            f"{server}/api/sheets/{mine['id']}/preview.png", headers=cookie(client), timeout=60
        )
    finally:
        timer.join()
        pdf.SLOTS.release()
    assert res.status_code == 200
    assert res.content.startswith(PNG_SIGNATURE)
