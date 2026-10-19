"""The fine MCP tools for the eight generated blocks: a block Claude adds is one a teacher adds."""

import json

import pytest
from playwright.sync_api import expect
from test_mcp import Mcp, printed, token_for
from ui import insert, saved, user

from blattwerk import schema

# The editor's label for each block: the dock's button, or the "Mathe-Blöcke" menu's item.
LABEL = {
    "maths": "Rechnen",
    "suchsel": "Suchsel",
    "zahlenmauer": "Zahlenmauer",
    "zahlenhaus": "Zahlenhaus",
    "zahlenkette": "Zahlenkette",
    "pfeilbild": "Pfeilbild",
    "operatorfeld": "Operatorfeld",
    "rechenrad": "Rechenrad",
    "rechentabelle": "Rechentabelle",
    "magischesquadrat": "Magisches Quadrat",
    "malquadrat": "Malquadrat",
    "rechendreieck": "Rechendreieck",
    "zahlenstrahl": "Zahlenstrahl",
    "hunderterfeld": "Hunderterfeld",
    "uhr": "Uhr",
    "selbstkontrolle": "Selbstkontrolle",
}
DOCK = ("maths", "suchsel")
KINDS = list(LABEL)

# One prop change per type that changes the drawing, and whether the block must grow for it.
CHANGES = {
    "maths": ({"max": 100}, False),
    "suchsel": ({"words": ["HUND", "KATZE", "MAUS"]}, False),
    "zahlenmauer": ({"base": 4}, True),
    "zahlenhaus": ({"floors": 3}, False),
    "zahlenkette": ({"count": 6}, True),
    "pfeilbild": ({"count": 6}, True),
    "operatorfeld": ({"count": 6}, True),
    "rechenrad": ({"count": 6}, True),
    "rechentabelle": ({"count": 3}, True),
    "magischesquadrat": ({"count": 3}, True),
    "malquadrat": ({"count": 3}, True),
    "rechendreieck": ({"count": 6}, False),
    "zahlenstrahl": ({"end": 50}, False),
    "hunderterfeld": ({"look": "punkte"}, False),
    "uhr": ({"count": 8}, True),
    "selbstkontrolle": ({"form": "word", "word": "HUND"}, False),
}


def tool(mcp, name, **args):
    result = mcp.call(name, **args)
    assert not result.get("isError"), result
    return json.loads(result["content"][0]["text"])


def sheet_doc(client, sheet_id):
    """The stored doc, which must hold no schema problem."""
    doc = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    assert schema.problems(doc) == []
    return doc


def stored_block(client, sheet_id, block_id):
    doc = sheet_doc(client, sheet_id)
    (found,) = [b for b in doc["pages"][0]["blocks"] if b["id"] == block_id]
    return found


def new_sheet(mcp):
    sheet = tool(mcp, "create_sheet", title="Blatt")
    version = tool(mcp, "get_sheet", sheet_id=sheet["id"])["version"]
    return sheet["id"], version


@pytest.mark.parametrize("kind", KINDS)
def test_same_as_editor(editor, server, tmp_path, kind):
    client = user()
    page = editor(client=client)
    if kind in DOCK:
        page.locator(".dock, .insert").get_by_label(LABEL[kind], exact=True).click()
    else:
        insert(page, LABEL[kind])
    # Maths asks the server for its exercises first, so the block comes after the click.
    expect(page.locator(".block[data-id]")).to_have_count(1)
    (made,) = saved(page, client)
    assert made["type"] == kind
    mcp = Mcp(server, token_for(client), tmp_path)
    try:
        sheet_id, version = new_sheet(mcp)
        props = {"seed": made["props"]["seed"]}
        added = tool(
            mcp,
            "add_block",
            sheet_id=sheet_id,
            version=version,
            page=1,
            type=kind,
            props=props,
            x=40,
            y=60,
        )
        ours = stored_block(client, sheet_id, added["block"]["id"])
        assert ours["type"] == kind
        for key in ("props", "w", "h", "z", "locked"):
            assert ours[key] == made[key], key
    finally:
        mcp.stop()


@pytest.mark.parametrize("kind", KINDS)
def test_add_change_print(server, tmp_path, kind):
    client = user()
    change, grows = CHANGES[kind]
    mcp = Mcp(server, token_for(client), tmp_path)
    try:
        sheet_id, version = new_sheet(mcp)
        added = tool(
            mcp, "add_block", sheet_id=sheet_id, version=version, page=1, type=kind, x=15, y=20
        )
        block_id = added["block"]["id"]
        before = stored_block(client, sheet_id, block_id)
        assert before["h"] == added["block"]["h"]

        changed = tool(
            mcp,
            "update_block",
            sheet_id=sheet_id,
            version=added["version"],
            block_id=block_id,
            props=change,
        )
        after = stored_block(client, sheet_id, block_id)
        for key, value in change.items():
            assert after["props"][key] == value, key
        if grows:
            assert after["h"] > before["h"]
        assert changed["version"] > added["version"]

        moved = tool(
            mcp,
            "move_block",
            sheet_id=sheet_id,
            version=changed["version"],
            block_id=block_id,
            x=20,
            y=50,
        )
        placed = stored_block(client, sheet_id, block_id)
        assert (placed["x"], placed["y"]) == (20, 50)
        assert placed["props"] == after["props"]

        assert printed(server, client, sheet_id) == 200

        tool(mcp, "delete_block", sheet_id=sheet_id, version=moved["version"], block_id=block_id)
        assert sheet_doc(client, sheet_id)["pages"][0]["blocks"] == []
    finally:
        mcp.stop()


def test_selbstkontrolle_links_an_uhr(server, tmp_path):
    client = user()
    mcp = Mcp(server, token_for(client), tmp_path)
    try:
        sheet_id, version = new_sheet(mcp)
        uhr = tool(
            mcp, "add_block", sheet_id=sheet_id, version=version, page=1, type="uhr", x=15, y=20
        )
        selbst = tool(
            mcp,
            "add_block",
            sheet_id=sheet_id,
            version=uhr["version"],
            page=1,
            type="selbstkontrolle",
            x=15,
            y=120,
        )
        linked = tool(
            mcp,
            "update_block",
            sheet_id=sheet_id,
            version=selbst["version"],
            block_id=selbst["block"]["id"],
            props={"form": "sum", "links": [uhr["block"]["id"]]},
        )
        found = stored_block(client, sheet_id, selbst["block"]["id"])
        assert found["props"]["links"] == [uhr["block"]["id"]]
        assert printed(server, client, sheet_id) == 200
        assert linked["version"] > selbst["version"]
    finally:
        mcp.stop()


def test_suchsel_with_more_words_than_fit(server, tmp_path):
    client = user()
    mcp = Mcp(server, token_for(client), tmp_path)
    # Eleven letters each: none fits a ten by ten grid, so every word is too long for it.
    words = [f"WORT{n:03d}LANG" for n in range(30)]
    try:
        sheet_id, version = new_sheet(mcp)
        added = tool(
            mcp, "add_block", sheet_id=sheet_id, version=version, page=1, type="suchsel", x=15, y=20
        )
        block_id = added["block"]["id"]
        tool(
            mcp,
            "update_block",
            sheet_id=sheet_id,
            version=added["version"],
            block_id=block_id,
            props={"words": words},
        )
        found = stored_block(client, sheet_id, block_id)
        assert found["props"]["words"] == words
        assert printed(server, client, sheet_id) == 200
    finally:
        mcp.stop()
