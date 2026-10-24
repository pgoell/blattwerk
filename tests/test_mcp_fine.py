"""The fine tools of the MCP server (frontend/mcp/tools.ts): blocks, pages, words, one write."""

import json

import pytest
from test_mcp import SCHEMA, start

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
        assert len(variants) == 27
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
