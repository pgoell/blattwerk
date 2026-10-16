"""Previews: a PNG of one page of a sheet, as saved or as posted, printed by Chromium."""

import io
import threading
import time

import httpx
import pypdfium2
from fastapi.testclient import TestClient
from PIL import Image
from pixels import LIMITS, as_png, measures
from ui import MATHS, TEXT, block, maths, picture, sheet, upload, user

from blattwerk import db, pdf
from blattwerk.app import app

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def cookie(client):
    return {"Cookie": f"session={client.cookies['session']}"}


def image(data):
    return Image.open(io.BytesIO(data)).convert("RGB")


def has_red(data):
    return any(colour == (255, 0, 0) for _, colour in image(data).getcolors(maxcolors=2**24))


def magenta(picture):
    """How many pixels of a picture are the outline's magenta."""
    colours = picture.getcolors(maxcolors=2**24) or []
    return sum(n for n, (r, g, b) in colours if r > 200 and g < 80 and b > 200)


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


def test_preview_of_a_posted_doc_in_the_old_shape(server):
    # Before pages, a sheet held its blocks at the top (#543): one page.
    client = user()
    doc = {"blocks": [block("text", 15, 14, TEXT)]}
    url = f"{server}/api/preview.png"
    res = httpx.post(url, json={"doc": doc}, headers=cookie(client), timeout=60)
    assert res.status_code == 200
    assert 990 <= image(res.content).width <= 1010
    res = httpx.post(url, json={"doc": doc}, params={"page": 2}, headers=cookie(client))
    assert res.status_code == 404


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


def test_a_burst_past_the_queue_gets_503_at_once(monkeypatch):
    # Two run and two wait: a fifth does not take a server thread for the wait.
    client = user()
    mine = sheet(client, [])
    monkeypatch.setattr(pdf, "WAIT", 5)
    for _ in range(4):
        pdf.ROOM.acquire()
    try:
        start = time.monotonic()
        res = client.get(f"/api/sheets/{mine['id']}/preview.png")
        took = time.monotonic() - start
    finally:
        for _ in range(4):
            pdf.ROOM.release()
    assert res.status_code == 503
    assert res.headers["retry-after"] == "5"
    assert took < 1


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


def test_a_doc_the_page_cannot_draw_is_422_not_500(server, monkeypatch):
    monkeypatch.setattr(pdf, "DRAW", 3000)
    client = user()
    # A word for a number in a maths block's props: check() lets it by, the page cannot draw it.
    bad = block("maths", 40, 30, {**MATHS, "max": "x"})
    doc = {"pages": [{"blocks": [bad]}], "guides": {"x": [], "y": []}, "grid": 0}
    res = httpx.post(
        f"{server}/api/preview.png", json={"doc": doc}, headers=cookie(client), timeout=60
    )
    assert res.status_code == 422
    assert res.json()["detail"]["problems"][0].startswith("doc: the page could not be drawn: ")


def test_outlines_draw_each_block_box_and_id(server):
    client = user()
    mine = sheet(client, [block("text", 15, 14, TEXT)])
    url = f"{server}/api/sheets/{mine['id']}/preview.png"
    outlined = httpx.get(url, params={"outlines": True}, headers=cookie(client), timeout=60)
    plain = httpx.get(url, headers=cookie(client), timeout=60)
    assert outlined.status_code == plain.status_code == 200
    assert magenta(image(outlined.content)) > 0
    assert magenta(image(plain.content)) == 0


def test_outlines_name_each_block_by_its_id(server):
    client = user()
    url = f"{server}/api/preview.png"
    shots = []
    for name in ("a", "langer-name-eines-blocks"):
        doc = {"pages": [{"blocks": [{**block("text", 15, 14, TEXT), "id": name}]}]}
        res = httpx.post(url, json={"doc": doc}, params={"outlines": 1}, headers=cookie(client))
        assert res.status_code == 200
        shots.append(image(res.content))
    short, long = shots
    # The box: the block's left edge, 15 mm in, is magenta halfway down the block.
    x, y = int(15 * short.width / 210), int(22 * short.width / 210)
    assert magenta(short.crop((x - 1, y, x + 2, y + 1))) > 0
    # The id: the same box with a longer id carries far more magenta, in the label at its top left.
    assert magenta(long) > magenta(short) + 100


def test_outlines_never_reach_the_pdf(server):
    client = user()
    mine = sheet(client, [block("text", 15, 14, TEXT)])
    httpx.get(
        f"{server}/api/sheets/{mine['id']}/preview.png",
        params={"outlines": True},
        headers=cookie(client),
        timeout=60,
    )
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie(client), timeout=60)
    assert res.status_code == 200
    page = pypdfium2.PdfDocument(res.content)[0].render(scale=1.5).to_pil().convert("RGB")
    assert magenta(page) == 0


def test_png_matches_pdf_page_one(server):
    client = user()
    mine = sheet(
        client,
        [
            block("text", 15, 14, TEXT),
            block("maths", 40, 30, maths(client)),
            picture(upload(client)),
        ],
    )
    cookies = cookie(client)
    png = httpx.get(
        f"{server}/api/sheets/{mine['id']}/preview.png", headers=cookies, timeout=60
    ).content
    pdf_bytes = httpx.get(
        f"{server}/api/sheets/{mine['id']}/pdf", headers=cookies, timeout=60
    ).content
    # As screen_and_print does: the PDF drawn at twice the size and halved, against the screen.
    paper = pypdfium2.PdfDocument(pdf_bytes)[0]
    large = paper.render(scale=2 * image(png).width / paper.get_width()).to_pil()
    found, _ = measures(png, as_png(large.reduce(2)))
    print({name: round(value, 5) for name, (value, _) in found.items()})
    for name, (value, where) in found.items():
        assert value < LIMITS[name], f"{name} {value:.4f}{where}"
