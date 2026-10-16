"""The fine MCP tools (#650) for eight block types: a block Claude adds is one a teacher adds."""

import json

import pytest
from playwright.sync_api import expect
from test_mcp import Mcp, printed, token_for
from ui import FIELD, png, saved, upload, user

from blattwerk import schema

KINDS = ["text", "shape", "ruling", "name", "points", "symbol", "table", "image"]
# The editor's insert buttons in the dock, by their labels.
LABELS = {
    "text": "Text",
    "shape": "Rechteck",
    "ruling": "Lineatur",
    "name": "Namenszeile",
    "points": "Punkte",
    "symbol": "Symbol",
    "table": "Tabelle",
}
# One real prop change per type: update_block stores it, and the schema still accepts the doc.
CHANGE = {
    "text": {"size": 18},
    "shape": {"fill": "#ffcc00"},
    "ruling": {"kind": "l4"},
    "name": {"fields": ["Name", "Datum", "Klasse"]},
    "points": {"max": 20},
    "symbol": {"code": "2605"},
    "table": {"align": "left"},
    "image": {"cut": [0.1, 0, 0, 0]},
}


def write(mcp, tool, **args):
    result = mcp.call(tool, **args)
    assert not result.get("isError"), result
    return json.loads(result["content"][0]["text"])


def stored_blocks(client, sheet_id):
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"]


def compare_with_editor(client, server, tmp_path, editor_block, kind, props):
    """Adds the block by MCP on a new sheet of the same teacher, and gives what the editor stored
    and what MCP stored: they must match."""
    mcp = Mcp(server, token_for(client), tmp_path)
    try:
        made = write(mcp, "create_sheet", title="Vergleich")
        write(
            mcp,
            "add_block",
            sheet_id=made["id"],
            version=made["version"],
            page=1,
            type=kind,
            props=props,
            x=15,
            y=20,
        )
        (mine,) = stored_blocks(client, made["id"])
    finally:
        mcp.stop()
    for key in ("type", "props", "w", "h", "z", "locked"):
        assert mine[key] == editor_block[key], key


@pytest.mark.parametrize("kind", KINDS)
def test_same_as_editor(kind, editor, server, tmp_path):
    client = user()
    page = editor(client=client)
    if kind == "image":
        page.locator("input[type=file]").set_input_files(
            {"name": "bild.png", "mimeType": "image/png", "buffer": png()}
        )
    else:
        page.locator(".dock, .insert").get_by_label(LABELS[kind], exact=True).click()
    expect(page.locator(".block[data-id]")).to_have_count(1)
    if kind == "text":
        # A new empty text opens for typing; one letter goes in, given to add_block too.
        expect(page.locator(FIELD)).to_be_focused()
        page.keyboard.type("A")
    (editor_block,) = saved(page, client)
    props = {"text": {"text": "A"}, "shape": {"kind": "rect"}, "image": {}}.get(kind, {})
    if kind == "image":
        props = {"upload": editor_block["props"]["upload"]}
    compare_with_editor(client, server, tmp_path, editor_block, kind, props)


@pytest.mark.parametrize("kind", KINDS)
def test_add_change_print(kind, server, tmp_path):
    client = user()
    mcp = Mcp(server, token_for(client), tmp_path)
    try:
        made = write(mcp, "create_sheet", title="Blatt")
        sheet_id = made["id"]
        props = {
            "shape": {"kind": "rect"},
            "image": {"upload": upload(client)},
        }.get(kind, {})
        added = write(
            mcp,
            "add_block",
            sheet_id=sheet_id,
            version=made["version"],
            page=1,
            type=kind,
            props=props,
            x=15,
            y=20,
        )
        block_id = added["block"]["id"]
        change = CHANGE[kind]
        key = next(iter(change))
        step = write(
            mcp,
            "update_block",
            sheet_id=sheet_id,
            version=added["version"],
            block_id=block_id,
            props=change,
        )
        (stored,) = stored_blocks(client, sheet_id)
        assert schema.problems(client.get(f"/api/sheets/{sheet_id}").json()["doc"]) == []
        assert stored["props"][key] == change[key]
        moved = write(
            mcp,
            "move_block",
            sheet_id=sheet_id,
            version=step["version"],
            block_id=block_id,
            x=30,
            y=40,
        )
        (stored,) = stored_blocks(client, sheet_id)
        assert schema.problems(client.get(f"/api/sheets/{sheet_id}").json()["doc"]) == []
        assert (stored["x"], stored["y"]) == (30, 40)
        assert printed(server, client, sheet_id) == 200
        write(mcp, "delete_block", sheet_id=sheet_id, version=moved["version"], block_id=block_id)
        assert stored_blocks(client, sheet_id) == []
    finally:
        mcp.stop()


def test_line_is_the_editors_linie(editor, server, tmp_path):
    client = user()
    page = editor(client=client)
    page.locator(".dock, .insert").get_by_label("Linie", exact=True).click()
    expect(page.locator(".block[data-id]")).to_have_count(1)
    (editor_block,) = saved(page, client)
    compare_with_editor(client, server, tmp_path, editor_block, "shape", {"kind": "line"})


def test_text_off_the_page_warns(server, tmp_path):
    client = user()
    mcp = Mcp(server, token_for(client), tmp_path)
    try:
        made = write(mcp, "create_sheet", title="Rand")
        added = write(
            mcp,
            "add_block",
            sheet_id=made["id"],
            version=made["version"],
            page=1,
            type="text",
            props={"text": "A"},
            x=250,
            y=20,
        )
        assert any("leaves the page" in said for said in added["warnings"]), added
        (stored,) = stored_blocks(client, made["id"])
        assert stored["x"] == 250
    finally:
        mcp.stop()
