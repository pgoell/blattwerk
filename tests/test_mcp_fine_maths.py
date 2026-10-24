"""Fine-grained MCP updates of a maths block: new exercises, a stretched height, and the foot.

The helpers live in test_mcp_fine.py.
"""

import json

from test_mcp import start
from test_mcp_fine import (
    doc_of,
    new_sheet,
    stored,
    stored_block,
    text_of,
)


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
