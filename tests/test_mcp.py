"""The Blattomat MCP server (frontend/mcp/stdio.ts), spoken to over stdio as Claude Code does."""

import json
import os
import subprocess
from pathlib import Path

from ui import user

ROOT = Path(__file__).parent.parent
SCHEMA = json.loads((ROOT / "src/blattwerk/sheet.schema.json").read_text())


class Mcp:
    def __init__(self, server, token, tmp_path, url=None):
        self.err = tmp_path / "stderr.txt"
        self.proc = subprocess.Popen(
            ["node", "frontend/mcp/stdio.ts"],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.err.open("w"),
            env={**os.environ, "BLATTWERK_URL": url or server, "BLATTWERK_TOKEN": token},
        )
        self.out = []
        self.next_id = 1
        self.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        )
        self.notify("notifications/initialized")

    def _send(self, message):
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(message) + "\n").encode())
        self.proc.stdin.flush()

    def notify(self, method):
        self._send({"jsonrpc": "2.0", "method": method})

    def request(self, method, params=None):
        ident = self.next_id
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}})
        while True:
            assert self.proc.stdout is not None
            line = self.proc.stdout.readline().decode()
            assert line, f"server ended; stderr: {self.err.read_text()}"
            self.out.append(line)
            message = json.loads(line)
            if message.get("id") == ident:
                assert "error" not in message, message
                return message["result"]

    def tools(self):
        return self.request("tools/list")["tools"]

    def call(self, name, **args):
        return self.request("tools/call", {"name": name, "arguments": args})

    def stop(self):
        self.proc.kill()
        self.proc.wait()


def token_for(client):
    return client.post("/api/tokens", json={"name": "mcp"}).json()["token"]


def start(server, tmp_path):
    client = user()
    mcp = Mcp(server, token_for(client), tmp_path)
    return client, mcp


def test_answers_initialize_and_tools_list(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        assert isinstance(mcp.tools(), list)
    finally:
        mcp.stop()


def test_lists_the_seven_tools(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        names = sorted(t["name"] for t in mcp.tools())
        assert names == sorted(
            [
                "list_sheets",
                "get_sheet",
                "create_sheet",
                "rename_sheet",
                "duplicate_sheet",
                "replace_doc",
                "render_preview",
            ]
        )
    finally:
        mcp.stop()


def test_doc_schema_is_the_generated_one(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        replace = next(t for t in mcp.tools() if t["name"] == "replace_doc")
        assert (
            replace["inputSchema"]["definitions"]["TextProps"] == SCHEMA["definitions"]["TextProps"]
        )
    finally:
        mcp.stop()


def test_create_rename_duplicate_list_get(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        made = json.loads(mcp.call("create_sheet", title="Plus")["content"][0]["text"])
        sheet_id = made["id"]
        assert made["doc"]["pages"]
        mcp.call("rename_sheet", sheet_id=sheet_id, title="Minus")
        copy = json.loads(mcp.call("duplicate_sheet", sheet_id=sheet_id)["content"][0]["text"])
        assert copy["id"] != sheet_id
        listed = json.loads(mcp.call("list_sheets")["content"][0]["text"])
        assert {s["id"]: s["title"] for s in listed}[sheet_id] == "Minus"
        assert "doc" not in listed[0]
        got = json.loads(mcp.call("get_sheet", sheet_id=sheet_id)["content"][0]["text"])
        assert got["title"] == "Minus"
        foreign = (
            user().post("/api/sheets", json={"title": "Fremd", "doc": made["doc"]}).json()["id"]
        )
        result = mcp.call("get_sheet", sheet_id=foreign)
        assert result["isError"] and "No sheet with id" in result["content"][0]["text"]
    finally:
        mcp.stop()
