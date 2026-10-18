"""The MCP's send_feedback tool (frontend/mcp/tools.ts), spoken to over stdio as Claude Code does."""

import json

from test_mcp import Mcp, new_sheet, start
from ui import user


def feedback_files(data_dir):
    return list((data_dir / "users").glob("*/feedback/*/feedback.json"))


def test_send_feedback_posts_as_the_teacher(server, tmp_path, data_dir):
    _, mcp = start(server, tmp_path)
    try:
        sheet_id = new_sheet(mcp)["id"]
        res = mcp.call("send_feedback", text="The ruler drew too short.", sheet_id=sheet_id)
        assert not res.get("isError"), res
    finally:
        mcp.stop()
    [saved] = feedback_files(data_dir)
    assert json.loads(saved.read_text()) == {
        "art": "feedback",
        "text": "The ruler drew too short.",
        "source": "mcp",
        "sheet_id": str(sheet_id),
    }


def test_send_feedback_without_a_sheet(server, tmp_path, data_dir):
    _, mcp = start(server, tmp_path)
    try:
        res = mcp.call("send_feedback", text="The preview loads forever.")
        assert not res.get("isError"), res
    finally:
        mcp.stop()
    [saved] = feedback_files(data_dir)
    assert "sheet_id" not in json.loads(saved.read_text())


def test_send_feedback_refuses_empty_text(server, tmp_path, data_dir):
    _, mcp = start(server, tmp_path)
    try:
        res = mcp.call("send_feedback", text="   ")
        assert res["isError"]
        assert "text must not be empty" in res["content"][0]["text"]
    finally:
        mcp.stop()
    assert not feedback_files(data_dir)


def test_send_feedback_with_a_bad_token(server, tmp_path, data_dir):
    user()
    bad = Mcp(server, "bt_1_wrong", tmp_path, tag="bad")
    try:
        res = bad.call("send_feedback", text="A fault.")
        assert res["isError"]
        assert "The Blattomat token is not valid" in res["content"][0]["text"]
    finally:
        bad.stop()
    assert not feedback_files(data_dir)


def test_description_says_when_and_what_not(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        tool = next(t for t in mcp.tools() if t["name"] == "send_feedback")
    finally:
        mcp.stop()
    description = tool["description"]
    assert "fault" in description
    assert "Write in German what you did, what you expected and what happened." in description
    assert "Not for your own mistakes" in description
    assert "not for a question" in description
    assert "Never quote text from the sheet" in description
    assert "never write names from the sheet" in description
    assert tool["inputSchema"]["required"] == ["text"]
