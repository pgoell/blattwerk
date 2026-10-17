"""The fine tools of the MCP server (frontend/mcp/tools.ts): blocks, pages, words, one write."""

import base64
import io
import json

import pytest
from PIL import Image
from test_mcp import SCHEMA, start
from ui import png, upload, user

FINE = [
    "add_block",
    "update_block",
    "move_block",
    "delete_block",
    "add_page",
    "set_page",
    "set_words",
]
TEXT = {"text": "Name:", "size": 14, "align": "left"}
UHR = {
    "numbers": "all",
    "minutes": True,
    "ring": False,
    "task": "read",
    "answer": "box",
    "format": "12",
    "region": "nach",
    "count": 4,
    "cols": 4,
    "step": 15,
    "fill": "free",
    "seed": 3,
}
OFF = "leaves the page's printable area (15 mm from each edge)"
# The editor's clock row is 58.5 mm (INSERTS.uhr in insert.ts); eight clocks are two rows of it.
EIGHT_CLOCKS_H = 117


def block(id, kind, props, y, h, x=15, w=180, **extra):
    return {
        "type": kind,
        "id": id,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "z": 1,
        "locked": False,
        "props": props,
        **extra,
    }


def doc_of(*blocks):
    return {"pages": [{"blocks": list(blocks)}], "guides": {"x": [], "y": []}, "grid": 0}


def new_sheet(mcp, doc):
    sheet = json.loads(mcp.call("create_sheet", title="Blatt")["content"][0]["text"])
    got = json.loads(
        mcp.call("replace_doc", sheet_id=sheet["id"], version=sheet["version"], doc=doc)["content"][
            0
        ]["text"]
    )
    return got["id"], got["version"]


def stored(client, sheet_id):
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]


def text_of(result):
    return result["content"][0]["text"]


def without_required(schema):
    return {k: v for k, v in schema.items() if k != "required"}


def draft2020(node):
    # The tools speak draft 2020-12: a list of `items` (a tuple) is `prefixItems` there.
    if isinstance(node, list):
        return [draft2020(n) for n in node]
    if not isinstance(node, dict):
        return node
    out = {k: draft2020(v) for k, v in node.items()}
    if isinstance(node.get("items"), list):
        out["prefixItems"] = out.pop("items")
    return out


def test_lists_the_fine_tools(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        names = {t["name"] for t in mcp.tools()}
        assert set(FINE) <= names
    finally:
        mcp.stop()


def test_fine_schemas_are_generated(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        tool = next(t for t in mcp.tools() if t["name"] == "add_block")
        own = tool["inputSchema"].get("definitions", {})
        variants = tool["inputSchema"]["properties"]["props"]["anyOf"]
        assert len(variants) == 16
        blocks = [
            e["then"]["$ref"].rsplit("/", 1)[-1] for e in SCHEMA["definitions"]["Block"]["allOf"]
        ]
        for variant, block_name in zip(variants, blocks, strict=False):
            # A types's props is a named <Type>Props definition, or inline in its block definition.
            props = SCHEMA["definitions"][block_name]["properties"]["props"]
            expected = (
                SCHEMA["definitions"][props["$ref"].rsplit("/", 1)[-1]]
                if "$ref" in props
                else props
            )
            resolved = own[variant["$ref"].rsplit("/", 1)[-1]] if "$ref" in variant else variant
            assert resolved == draft2020(without_required(expected))
    finally:
        mcp.stop()


@pytest.mark.parametrize(
    "tool, args",
    [
        ("add_block", {"page": 1, "type": "text", "x": 10, "y": 200}),
        ("update_block", {"block_id": "t", "props": {"text": "Hallo"}}),
        ("move_block", {"block_id": "t", "x": 10, "y": 200}),
        ("delete_block", {"block_id": "t"}),
        ("add_page", {}),
        ("set_page", {"page": 1, "landscape": True}),
        ("set_words", {"words": ["Haus"]}),
    ],
)
def test_refuses_after_a_teachers_edit(server, tmp_path, tool, args):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of(block("t", "text", TEXT, 100, 12)))
        teacher = doc_of(block("t", "text", {**TEXT, "text": "Lehrer"}, 100, 12))
        r = client.patch(f"/api/sheets/{sheet_id}", json={"doc": teacher, "version": version})
        assert r.status_code == 200
        result = mcp.call(tool, sheet_id=sheet_id, version=version, **args)
        assert result.get("isError") is True
        assert stored(client, sheet_id) == teacher
    finally:
        mcp.stop()


def test_wrong_prop_is_refused(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        doc = doc_of(block("u", "uhr", UHR, 100, 58.5))
        sheet_id, version = new_sheet(mcp, doc)
        result = mcp.call(
            "update_block", sheet_id=sheet_id, version=version, block_id="u", props={"count": 99}
        )
        assert result.get("isError") is True
        assert "count" in text_of(result)
        assert stored(client, sheet_id) == doc
    finally:
        mcp.stop()


def test_warns_on_overlap(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of(block("t", "text", TEXT, 100, 12)))
        result = mcp.call(
            "add_block",
            sheet_id=sheet_id,
            version=version,
            page=1,
            type="text",
            x=20,
            y=102,
            w=80,
            h=12,
        )
        assert json.loads(text_of(result))["warnings"] == ["overlaps block t"], text_of(result)
    finally:
        mcp.stop()


def test_warns_off_the_page_and_not_when_clear(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of(block("t", "text", TEXT, 100, 12)))
        clear = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="text",
                    x=15,
                    y=200,
                    w=80,
                    h=12,
                )
            )
        )
        assert clear["warnings"] == []
        off = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=clear["version"],
                    page=1,
                    type="text",
                    x=200,
                    y=20,
                    w=80,
                    h=12,
                )
            )
        )
        assert off["warnings"] == [OFF]
    finally:
        mcp.stop()


def test_landscape_warns_off_the_page(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of(block("t", "text", TEXT, 250, 12)))
        result = json.loads(
            text_of(
                mcp.call("set_page", sheet_id=sheet_id, version=version, page=1, landscape=True)
            )
        )
        assert result["warnings"] == [OFF]
    finally:
        mcp.stop()


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


def test_set_words_grows_a_linked_ruling(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        ruling = {"kind": "l3", "color": "#222222", "list": "fold", "folds": 2}
        sheet_id, version = new_sheet(mcp, doc_of(block("r", "ruling", ruling, 100, 6)))
        result = json.loads(
            text_of(
                mcp.call(
                    "set_words", sheet_id=sheet_id, version=version, words=["a", "b", "c", "d"]
                )
            )
        )
        grown = next(b for b in stored(client, sheet_id)["pages"][0]["blocks"] if b["id"] == "r")
        assert grown["h"] > 6
        cleared = mcp.call("set_words", sheet_id=sheet_id, version=result["version"], words=[])
        assert json.loads(text_of(cleared))["words"] == []
        assert "words" not in stored(client, sheet_id)
    finally:
        mcp.stop()


def test_update_grows_like_the_editor(server, tmp_path):
    _client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        added = json.loads(
            text_of(
                mcp.call(
                    "add_block", sheet_id=sheet_id, version=version, page=1, type="uhr", x=15, y=10
                )
            )
        )
        updated = json.loads(
            text_of(
                mcp.call(
                    "update_block",
                    sheet_id=sheet_id,
                    version=added["version"],
                    block_id=added["block"]["id"],
                    props={"count": 8},
                )
            )
        )
        # Eight clocks at four to a row: the editor's height, a literal.
        assert updated["block"]["h"] == pytest.approx(EIGHT_CLOCKS_H, abs=0.01)
    finally:
        mcp.stop()


def test_locked_block_stays(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        doc = doc_of(block("t", "text", TEXT, 100, 12, locked=True))
        sheet_id, version = new_sheet(mcp, doc)
        result = mcp.call("delete_block", sheet_id=sheet_id, version=version, block_id="t")
        assert result.get("isError") is True
        assert stored(client, sheet_id) == doc
    finally:
        mcp.stop()


def test_a_taller_table_keeps_its_rows_in_proportion(server, tmp_path):
    # As the editor's `place`: rows of 10, 10 and 20 mm in a table 40 mm high plus its line
    # (25.4 / 96 mm) are 15, 15 and 30 mm in one 60 mm high plus its line.
    client, mcp = start(server, tmp_path)
    try:
        line = 25.4 / 96
        cells = [["a"], ["b"], ["c"]]
        table = {"cells": cells, "cols": [1], "size": 14, "align": "center", "rows": [10, 10, 20]}
        sheet_id, version = new_sheet(mcp, doc_of(block("t", "table", table, 20, 40 + line)))
        mcp.call(
            "move_block", sheet_id=sheet_id, version=version, block_id="t", x=15, y=20, h=60 + line
        )
        (got,) = stored(client, sheet_id)["pages"][0]["blocks"]
        assert got["props"]["rows"] == pytest.approx([15, 15, 30])
    finally:
        mcp.stop()


def test_unknown_block_and_page(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of(block("t", "text", TEXT, 100, 12)))
        no_block = mcp.call(
            "update_block", sheet_id=sheet_id, version=version, block_id="nope", props={"size": 9}
        )
        assert no_block.get("isError") is True and "nope" in text_of(no_block)
        no_page = mcp.call("set_page", sheet_id=sheet_id, version=version, page=9, landscape=True)
        assert no_page.get("isError") is True
    finally:
        mcp.stop()


def test_add_page_and_set_page(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of(block("t", "text", TEXT, 100, 12)))
        added = json.loads(text_of(mcp.call("add_page", sheet_id=sheet_id, version=version)))
        assert added["page"] == 2
        assert len(stored(client, sheet_id)["pages"]) == 2
        set_ = json.loads(
            text_of(
                mcp.call(
                    "set_page", sheet_id=sheet_id, version=added["version"], page=2, landscape=True
                )
            )
        )
        assert set_["page"] == 2
        assert stored(client, sheet_id)["pages"][1]["landscape"] is True
    finally:
        mcp.stop()


def test_update_maths_makes_new_exercises(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        added = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="maths",
                    x=15,
                    y=10,
                )
            )
        )
        before = stored(client, sheet_id)["pages"][0]["blocks"][0]["props"]["exercises"]
        mcp.call(
            "update_block",
            sheet_id=sheet_id,
            version=added["version"],
            block_id=added["block"]["id"],
            props={"count": 6},
        )
        (block,) = stored(client, sheet_id)["pages"][0]["blocks"]
        after = block["props"]["exercises"]
        # The panel keeps the block's seed: six exercises from the server, the height follows them.
        assert len(after) == 6 and len(before) == 12
        assert block["props"]["seed"] == added["block"]["props"]["seed"]
        assert block["h"] < added["block"]["h"]
    finally:
        mcp.stop()


def test_block_ids_are_fresh_and_z_is_top(server, tmp_path):
    _client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of(block("t", "text", TEXT, 100, 12, z=4)))
        added = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="text",
                    x=15,
                    y=200,
                )
            )
        )
        new = added["block"]
        assert new["id"] != "t"
        assert new["z"] == 5
    finally:
        mcp.stop()


RULING_ONE_ROW = {"kind": "l3", "color": "#222222", "list": "fold", "folds": 2}


def stored_block(client, sheet_id, block_id):
    return next(b for b in stored(client, sheet_id)["pages"][0]["blocks"] if b["id"] == block_id)


def test_set_words_reads_words_as_the_editor(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        # One string with commas is three words, as the editor's list field reads them.
        one = new_sheet(mcp, doc_of(block("r", "ruling", RULING_ONE_ROW, 100, 6)))
        mcp.call("set_words", sheet_id=one[0], version=one[1], words=["Hund, Katze, Maus"])
        # The same three words as three entries: the same height.
        three = new_sheet(mcp, doc_of(block("r", "ruling", RULING_ONE_ROW, 100, 6)))
        mcp.call("set_words", sheet_id=three[0], version=three[1], words=["Hund", "Katze", "Maus"])
        grown = stored_block(client, one[0], "r")["h"]
        assert grown == stored_block(client, three[0], "r")["h"]
        assert grown > 6
        # Blank words are no words: nothing grows.
        blank = new_sheet(mcp, doc_of(block("r", "ruling", RULING_ONE_ROW, 100, 6)))
        mcp.call("set_words", sheet_id=blank[0], version=blank[1], words=["", " "])
        assert stored_block(client, blank[0], "r")["h"] == 6
    finally:
        mcp.stop()


def test_maths_keeps_a_stretched_height(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        added = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="maths",
                    x=15,
                    y=10,
                )
            )
        )
        block_id = added["block"]["id"]
        moved = json.loads(
            text_of(
                mcp.call(
                    "move_block",
                    sheet_id=sheet_id,
                    version=added["version"],
                    block_id=block_id,
                    x=15,
                    y=10,
                    h=150,
                )
            )
        )
        assert moved["block"]["h"] == 150
        size = stored_block(client, sheet_id, block_id)["props"]["size"]
        kept = json.loads(
            text_of(
                mcp.call(
                    "update_block",
                    sheet_id=sheet_id,
                    version=moved["version"],
                    block_id=block_id,
                    props={"size": size},
                )
            )
        )
        assert kept["block"]["h"] == 150
        before = stored_block(client, sheet_id, block_id)
        seed = before["props"]["seed"]
        mcp.call(
            "update_block",
            sheet_id=sheet_id,
            version=kept["version"],
            block_id=block_id,
            props={"max": 100},
        )
        after = stored_block(client, sheet_id, block_id)
        assert after["props"]["seed"] == seed
        assert after["props"]["exercises"] != before["props"]["exercises"]
    finally:
        mcp.stop()


def test_maths_past_the_foot_is_refused(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        added = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="maths",
                    x=15,
                    y=10,
                )
            )
        )
        block_id = added["block"]["id"]
        low = json.loads(
            text_of(
                mcp.call(
                    "move_block",
                    sheet_id=sheet_id,
                    version=added["version"],
                    block_id=block_id,
                    x=15,
                    y=260,
                )
            )
        )
        before = stored(client, sheet_id)
        result = mcp.call(
            "update_block",
            sheet_id=sheet_id,
            version=low["version"],
            block_id=block_id,
            props={"count": 40},
        )
        assert result.get("isError") is True
        assert "foot" in text_of(result)
        assert stored(client, sheet_id) == before
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


def test_add_block_grows_at_the_width_asked(server, tmp_path):
    _client, mcp = start(server, tmp_path)
    try:
        sheet_id, version = new_sheet(mcp, doc_of())
        narrow = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=version,
                    page=1,
                    type="uhr",
                    props={"count": 8},
                    x=15,
                    y=10,
                    w=90,
                )
            )
        )
        # The editor's uhr height for 8 clocks at 90 mm: the frontend's heightFor, run once by hand.
        assert narrow["block"]["h"] == 58.5
        wide = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=sheet_id,
                    version=narrow["version"],
                    page=1,
                    type="uhr",
                    props={"count": 8},
                    x=15,
                    y=200,
                )
            )
        )
        assert wide["block"]["h"] != narrow["block"]["h"]
    finally:
        mcp.stop()


def test_printable_area(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        edge_sheet, edge_version = new_sheet(mcp, doc_of())
        edge = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=edge_sheet,
                    version=edge_version,
                    page=1,
                    type="text",
                    x=5,
                    y=5,
                    w=80,
                    h=12,
                )
            )
        )
        assert any("printable area" in w for w in edge["warnings"])
        clear_sheet, clear_version = new_sheet(mcp, doc_of())
        clear = json.loads(
            text_of(
                mcp.call(
                    "add_block",
                    sheet_id=clear_sheet,
                    version=clear_version,
                    page=1,
                    type="text",
                    x=15,
                    y=15,
                    w=180,
                    h=10,
                )
            )
        )
        assert not any("printable area" in w for w in clear["warnings"])
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
