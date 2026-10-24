"""Fine-grained MCP pictures: an upload of one's own, a picture of another teacher, and a preview.

The helpers live in test_mcp_fine.py.
"""

import base64
import io
import json

import pytest
from PIL import Image
from test_mcp import start
from test_mcp_fine import (
    doc_of,
    new_sheet,
    stored,
    stored_block,
    text_of,
)
from ui import png, upload, user


def test_image_from_own_upload(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        up = upload(client)
        added = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="image",
                    props={"upload": up},
                    x=10,
                    y=10,
                )
            )
        )
        props = stored(client, sheet_id)["pages"][0]["blocks"][0]["props"]
        assert props["upload"] == up
        assert props["cut"] == [0, 0, 0, 0]
        assert props["ratio"] > 0
        assert added["block"]["w"] == pytest.approx(round(min(100, 100 * props["ratio"]), 2))
        assert added["block"]["h"] == pytest.approx(
            round(added["block"]["w"] / props["ratio"], 2), abs=0.01
        )
    finally:
        mcp.stop()


def test_image_of_another_teacher_is_refused(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        other = upload(user())
        result = mcp.call(
            "add_block",
            sheet_id=sheet_id,
            version=version,
            page=1,
            type="image",
            props={"upload": other},
            x=10,
            y=10,
        )
        assert result.get("isError") is True
        assert f"No upload with id {other}." in text_of(result)
        assert stored(client, sheet_id) == doc_of()
    finally:
        mcp.stop()


def test_update_image_to_another_teachers_upload_is_refused(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        own = upload(client)
        added = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="image",
                    props={"upload": own},
                    x=10,
                    y=10,
                )
            )
        )
        block_id = added["block"]["id"]
        before = stored(client, sheet_id)
        other = upload(user())
        result = mcp.call(
            "update_block",
            sheet_id=sheet_id,
            version=added["version"],
            block_id=block_id,
            props={"upload": other},
        )
        assert result.get("isError") is True
        assert f"No upload with id {other}." in text_of(result)
        assert stored(client, sheet_id) == before
    finally:
        mcp.stop()


def jpeg(size, orientation=None):
    buf = io.BytesIO()
    if orientation is None:
        Image.new("RGB", size).save(buf, "JPEG")
    else:
        exif = Image.Exif()
        exif[0x0112] = orientation
        Image.new("RGB", size).save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def test_jpeg_turned_by_exif(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        turned = client.post(
            "/api/uploads", files={"file": ("p.jpg", jpeg((40, 20), 6), "image/jpeg")}
        ).json()["id"]
        plain = client.post(
            "/api/uploads", files={"file": ("q.jpg", jpeg((40, 20)), "image/jpeg")}
        ).json()["id"]
        first = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="image",
                    props={"upload": turned},
                    x=10,
                    y=10,
                )
            )
        )
        assert stored_block(client, sheet_id, first["block"]["id"])["props"]["ratio"] == 0.5
        second = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=first["version"],
                    page=1,
                    type="image",
                    props={"upload": plain},
                    x=10,
                    y=200,
                )
            )
        )
        assert stored_block(client, sheet_id, second["block"]["id"])["props"]["ratio"] == 2
    finally:
        mcp.stop()


SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
    '<rect width="200" height="100"/></svg>'
)
HOSTILE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" onload="alert(1)">'
    '<script>alert(1)</script><rect width="10" height="10"/></svg>'
)
REFUSED = (
    "The server does not take this picture: PNG, JPEG, WebP, GIF, "
    "or SVG with a viewBox (no entities)."
)


def encoded(data):
    return base64.b64encode(data).decode()


def test_upload_picture_svg_then_add_block(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        up = json.loads(text_of(mcp.call("upload_picture", svg=SVG)))
        assert up["ratio"] == 2
        mcp.call(
            "add_block",
            sheet_id=sheet_id,
            version=version,
            page=1,
            type="image",
            props={"upload": up["upload"]},
            x=10,
            y=10,
        )
        props = stored(client, sheet_id)["pages"][0]["blocks"][0]["props"]
        assert props["upload"] == up["upload"]
        assert props["ratio"] == 2
    finally:
        mcp.stop()


@pytest.mark.parametrize("format", ["PNG", "JPEG", "WEBP"])
def test_upload_picture_takes_png_jpeg_webp(server, tmp_path, format):
    client, mcp = start(server, tmp_path)
    try:
        buf = io.BytesIO()
        Image.new("RGB", (40, 20), (200, 30, 30)).save(buf, format)
        up = json.loads(text_of(mcp.call("upload_picture", data=encoded(buf.getvalue()))))
        assert client.get(f"/api/uploads/{up['upload']}").content == buf.getvalue()
        assert up["ratio"] == 2
    finally:
        mcp.stop()


def test_upload_picture_refuses_what_the_server_refuses(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        text_only = mcp.call("upload_picture", data=encoded(b"Hallo, kein Bild"))
        assert text_only.get("isError") is True
        assert REFUSED in text_of(text_only)
        neither = mcp.call("upload_picture")
        assert neither.get("isError") is True
        both = mcp.call("upload_picture", svg=SVG, data=encoded(png()))
        assert both.get("isError") is True
        spaced = mcp.call("upload_picture", data="iVBO Rw0K")
        assert spaced.get("isError") is True
        # Nothing was stored: the first upload of this teacher would have id 1.
        assert client.get("/api/uploads/1").status_code == 404
    finally:
        mcp.stop()


def test_upload_picture_cleans_a_hostile_svg(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        up = json.loads(text_of(mcp.call("upload_picture", svg=HOSTILE)))
        served = client.get(f"/api/uploads/{up['upload']}").content
        assert b"<script" not in served
        assert b"onload" not in served
        assert b"<rect" in served
    finally:
        mcp.stop()


def test_another_teacher_cannot_place_the_uploaded_picture(server, tmp_path):
    _alice, alice = start(server, tmp_path)
    _bob, bob = start(server, tmp_path)
    try:
        up = json.loads(text_of(alice.call("upload_picture", svg=SVG)))["upload"]
        sheet_id, version = new_sheet(bob, doc_of())
        result = bob.call(
            "add_block",
            sheet_id=sheet_id,
            version=version,
            page=1,
            type="image",
            props={"upload": up},
            x=10,
            y=10,
        )
        assert result.get("isError") is True
        assert f"No upload with id {up}." in text_of(result)
    finally:
        alice.stop()
        bob.stop()


def test_render_preview_shows_the_placed_svg(server, tmp_path):
    _client, mcp = start(server, tmp_path)
    try:
        square = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<rect width="10" height="10"/></svg>'
        )
        up = json.loads(text_of(mcp.call("upload_picture", svg=square)))["upload"]
        sheet_id, version = new_sheet(mcp, doc_of())
        mcp.call(
            "add_block",
            sheet_id=sheet_id,
            version=version,
            page=1,
            type="image",
            props={"upload": up},
            x=20,
            y=30,
            w=50,
            h=50,
        )
        shown = mcp.call("render_preview", sheet_id=sheet_id)
        raw = base64.b64decode(shown["content"][0]["data"])
        picture = Image.open(io.BytesIO(raw)).convert("L")
        per_mm = picture.width / 210
        # The square's middle is black; the page beside it is white.
        middle = picture.getpixel((int(45 * per_mm), int(55 * per_mm)))
        beside = picture.getpixel((int(150 * per_mm), int(250 * per_mm)))
        assert isinstance(middle, int) and middle < 60
        assert isinstance(beside, int) and beside > 240
    finally:
        mcp.stop()
