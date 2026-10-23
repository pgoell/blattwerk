"""A page ground: a JPEG, a PNG, or one page of a PDF, stored as an upload."""

import io
import os
import time
from typing import cast

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, EncodedStreamObject
from ui import png, user

from blattwerk import db, pictures
from blattwerk.app import app
from blattwerk.grounds import MAX_GROUND_BYTES, MAX_GROUND_PAGES, TOO_BIG, TOO_MANY

PASSWORD = "richtig-geheim"


def pdf_of(*sizes):
    """A PDF with one page per (width, height) in points. The first page is filled red."""
    writer = PdfWriter()
    for i, (width, height) in enumerate(sizes):
        page = writer.add_blank_page(width=width, height=height)
        if i == 0:
            stream = DecodedStreamObject()
            stream.set_data(b"1 0 0 rg\n0 0 595 842 re\nf\n")
            page.replace_contents(cast(EncodedStreamObject, stream))
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def jpeg(colour=(255, 0, 0), size=(40, 20)):
    out = io.BytesIO()
    Image.new("RGB", size, colour).save(out, format="JPEG", quality=90)
    return out.getvalue()


def send(client, data, name="blatt.pdf", kind="application/pdf", which=None):
    files = {"file": (name, data, kind)}
    if which is not None:
        files["which"] = (None, which)
    return client.post("/api/grounds", files=files)


def test_logged_out_gets_401():
    client = TestClient(app, base_url="https://testserver")
    assert send(client, pdf_of((595.28, 841.89))).status_code == 401


def test_a_pdf_page_becomes_a_jpeg_at_300_dpi_on_a4(data_dir):
    client = user("a@example.com")
    res = send(client, pdf_of((595.28, 841.89)))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["pages"] == 1
    assert body["page_limit"] == MAX_GROUND_PAGES
    assert body["bytes"] == MAX_GROUND_BYTES
    made = body["made"]
    assert len(made) == 1
    assert made[0]["page"] == 1
    # 210 mm and 297 mm at 300 dpi. PDFium rounds the page box, so a pixel either way.
    assert abs(made[0]["width"] - round(210 / 25.4 * 300)) <= 2
    assert abs(made[0]["height"] - round(297 / 25.4 * 300)) <= 2
    upload_id = made[0]["id"]
    got = client.get(f"/api/uploads/{upload_id}")
    assert got.status_code == 200
    assert got.headers["content-type"] == "image/jpeg"
    image = Image.open(io.BytesIO(got.content))
    assert image.size == (made[0]["width"], made[0]["height"])
    # The red fill of the PDF page survives the render.
    pixel = image.convert("RGB").getpixel((image.width // 2, image.height // 2))
    assert isinstance(pixel, tuple) and pixel[0] > 200
    assert (data_dir / "users" / "1" / "uploads" / str(upload_id)).is_file()


def test_one_page_of_a_pdf_is_the_only_upload(data_dir):
    client = user("a@example.com")
    data = pdf_of((595.28, 841.89), (420, 595))
    probe = send(client, data, which="")
    assert probe.status_code == 200
    assert probe.json()["pages"] == 2
    assert probe.json()["made"] == []
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0
    res = send(client, data, which="2")
    assert res.status_code == 200
    made = res.json()["made"]
    assert [item["page"] for item in made] == [2]
    # The second page is the smaller one, so its picture is the smaller one.
    assert made[0]["width"] < round(210 / 25.4 * 300) - 50
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 1


def test_every_page_of_a_pdf_is_an_upload():
    client = user("a@example.com")
    res = send(client, pdf_of((595.28, 841.89), (595.28, 841.89)), which="all")
    assert res.status_code == 200
    made = res.json()["made"]
    assert [item["page"] for item in made] == [1, 2]
    assert made[0]["id"] != made[1]["id"]
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 2


def test_a_jpeg_and_a_png_are_stored_as_themselves():
    client = user("a@example.com")
    data = jpeg()
    res = send(client, data, name="foto.jpg", kind="image/jpeg")
    assert res.status_code == 200
    made = res.json()["made"][0]
    assert made["width"] == 40 and made["height"] == 20
    assert client.get(f"/api/uploads/{made['id']}").content == data
    png_res = send(client, png(), name="foto.png", kind="image/png")
    assert png_res.status_code == 200
    stored = client.get(f"/api/uploads/{png_res.json()['made'][0]['id']}")
    assert stored.headers["content-type"] == "image/png"
    assert stored.content == png()


def test_a_file_over_the_limit_is_refused_with_a_message():
    client = user("a@example.com")
    res = send(client, b"%PDF" + b"x" * MAX_GROUND_BYTES)
    assert res.status_code == 413
    assert res.json()["detail"] == TOO_BIG
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0


def test_a_pdf_with_too_many_pages_is_refused_with_a_message():
    client = user("a@example.com")
    res = send(client, pdf_of(*[(200, 200)] * (MAX_GROUND_PAGES + 1)))
    assert res.status_code == 422
    assert res.json()["detail"] == TOO_MANY
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0


@pytest.mark.parametrize(
    "data, kind, name",
    [
        (b"GIF89a", "image/gif", "a.gif"),
        (b"<svg></svg>", "image/svg+xml", "a.svg"),
        (b"not a picture", "text/plain", "a.txt"),
    ],
)
def test_other_files_are_refused_with_a_message(data, kind, name):
    client = user("a@example.com")
    res = send(client, data, name=name, kind=kind)
    assert res.status_code == 415
    assert "JPEG" in res.json()["detail"] and "PDF" in res.json()["detail"]
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0


def test_a_page_the_pdf_has_not_is_refused():
    client = user("a@example.com")
    res = send(client, pdf_of((200, 200)), which="4")
    assert res.status_code == 422
    assert "4" in res.json()["detail"]
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0


def test_a_ground_counts_as_shown_and_is_kept():
    assert pictures.shown(
        {"pages": [{"blocks": [], "ground": {"upload": 7, "ratio": 1, "cut": [0, 0, 0, 0]}}]}
    ) == {7}
    client = user("a@example.com")
    upload_id = send(client, jpeg(), name="foto.jpg", kind="image/jpeg").json()["made"][0]["id"]
    doc = {
        "pages": [
            {
                "blocks": [],
                "ground": {"upload": upload_id, "ratio": 2, "cut": [0, 0, 0, 0]},
            }
        ],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    made = client.post("/api/sheets", json={"title": "Grund", "doc": doc})
    assert made.status_code == 200
    then = time.time() - (pictures.KEEP_DAYS + 1) * 86400
    os.utime(pictures.path(1, upload_id), (then, then))
    other = {
        "pages": [{"blocks": []}],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    assert client.post("/api/sheets", json={"title": "Leer", "doc": other}).status_code == 200
    assert pictures.path(1, upload_id).is_file()
    assert client.get(f"/api/uploads/{upload_id}").content == jpeg()


def test_a_ground_opacity_past_1_is_refused():
    client = user("a@example.com")
    upload_id = send(client, jpeg(), name="foto.jpg", kind="image/jpeg").json()["made"][0]["id"]
    doc = {
        "pages": [
            {
                "blocks": [],
                "ground": {"upload": upload_id, "ratio": 2, "cut": [0, 0, 0, 0], "opacity": 2},
            }
        ],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    # A strict save refuses a fade outside 0 to 1. The editor's own save logs it and keeps the sheet.
    res = client.post("/api/sheets?strict=true", json={"title": "Grund", "doc": doc})
    assert res.status_code == 422
    assert any("opacity" in problem for problem in res.json()["detail"]["problems"])
