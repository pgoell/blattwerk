"""The Blattomat MCP server (frontend/mcp/stdio.ts), spoken to over stdio as Claude Code does."""

import base64
import json
import os
import re
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator
from ui import user

ROOT = Path(__file__).parent.parent
SCHEMA = json.loads((ROOT / "src/blattwerk/sheet.schema.json").read_text())


class Mcp:
    def __init__(self, server, token, tmp_path, url=None, tag=""):
        self.err = tmp_path / f"stderr{tag}.txt"
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
        self.init = self.request(
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
                "add_block",
                "update_block",
                "move_block",
                "delete_block",
                "add_page",
                "set_page",
                "set_words",
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


def test_every_tool_schema_is_valid_2020_12(server, tmp_path):
    # Claude Code drops a tool whose schema is not draft 2020-12: the generated schema is draft 7,
    # whose fixed-length lists (`items` as a list) 2020-12 writes as `prefixItems`.
    _, mcp = start(server, tmp_path)
    try:
        for tool in mcp.tools():
            Draft202012Validator.check_schema(tool["inputSchema"])
            # Each `$ref` points at a definition the tool's schema holds: a dangling one makes
            # Claude send the doc as a string.
            schema = tool["inputSchema"]
            for ref in set(re.findall(r'"\$ref": "#/definitions/([^"]+)"', json.dumps(schema))):
                assert ref in schema["definitions"], f"{tool['name']}: no definition {ref}"
        replace = next(t for t in mcp.tools() if t["name"] == "replace_doc")
        doc = {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}
        Draft202012Validator(replace["inputSchema"]).validate(
            {"sheet_id": 1, "version": 1, "doc": doc}
        )
        assert not Draft202012Validator(replace["inputSchema"]).is_valid(
            {"sheet_id": 1, "version": 1, "doc": json.dumps(doc)}
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
        # An id goes into the URL: one that is no whole number never reaches another route.
        result = mcp.call("get_sheet", sheet_id="1/../../templates")
        assert result["isError"] and "whole number" in result["content"][0]["text"]
    finally:
        mcp.stop()


def block(id, kind, props, y, h):
    return {
        "type": kind,
        "id": id,
        "x": 15,
        "y": y,
        "w": 180,
        "h": h,
        "z": 1,
        "locked": False,
        "props": props,
    }


def doc_of(*blocks):
    return {"pages": [{"blocks": list(blocks)}], "guides": {"x": [], "y": []}, "grid": 0}


TEXT = {"text": "Name:", "size": 14, "align": "left"}
RULING = {"kind": "l4", "color": "#222222"}


def maths(id, y, count=12, columns=4):
    props = {"ops": ["+", "-"], "max": 20, "count": count, "columns": columns, "size": 14}
    return block(id, "maths", props, y, 10)


def new_sheet(mcp):
    return json.loads(mcp.call("create_sheet", title="Blatt")["content"][0]["text"])


def stored(client, sheet_id):
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]


def test_replace_doc_takes_the_three_types(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet = new_sheet(mcp)
        doc = doc_of(
            block("t", "text", TEXT, 20, 10), maths("m", 40), block("r", "ruling", RULING, 60, 10)
        )
        result = mcp.call("replace_doc", sheet_id=sheet["id"], version=sheet["version"], doc=doc)
        assert not result.get("isError"), result
        kinds = [b["type"] for b in stored(client, sheet["id"])["pages"][0]["blocks"]]
        assert kinds == ["text", "maths", "ruling"]
    finally:
        mcp.stop()


def test_replace_doc_names_path_and_fix(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet = new_sheet(mcp)
        before = stored(client, sheet["id"])
        doc = doc_of(maths("m", 20, columns=7))
        result = mcp.call("replace_doc", sheet_id=sheet["id"], version=sheet["version"], doc=doc)
        text = result["content"][0]["text"]
        assert result["isError"]
        assert "props.columns" in text and "must be 1 to 6" in text
        assert stored(client, sheet["id"]) == before
    finally:
        mcp.stop()


def test_maths_gets_exercises_from_the_api(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet = new_sheet(mcp)
        doc = doc_of(maths("m", 20, count=12))
        result = mcp.call("replace_doc", sheet_id=sheet["id"], version=sheet["version"], doc=doc)
        assert not result.get("isError"), result
        (saved,) = stored(client, sheet["id"])["pages"][0]["blocks"]
        assert len(saved["props"]["exercises"]) == 12
        assert saved["h"] >= 10
    finally:
        mcp.stop()


def test_maths_keeps_its_own_exercises(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet = new_sheet(mcp)
        first = mcp.call(
            "replace_doc",
            sheet_id=sheet["id"],
            version=sheet["version"],
            doc=doc_of(maths("m", 20)),
        )
        assert not first.get("isError"), first
        once = stored(client, sheet["id"])
        version = client.get(f"/api/sheets/{sheet['id']}").json()["version"]
        result = mcp.call("replace_doc", sheet_id=sheet["id"], version=version, doc=once)
        assert not result.get("isError"), result
        twice = stored(client, sheet["id"])
        assert (
            twice["pages"][0]["blocks"][0]["props"]["exercises"]
            == (once["pages"][0]["blocks"][0]["props"]["exercises"])
        )
    finally:
        mcp.stop()


def test_409_retries_once(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet = new_sheet(mcp)
        got = json.loads(mcp.call("get_sheet", sheet_id=sheet["id"])["content"][0]["text"])
        bumped = client.patch(
            f"/api/sheets/{sheet['id']}", json={"doc": got["doc"], "version": got["version"]}
        )
        assert bumped.status_code == 200, bumped.text
        result = mcp.call(
            "replace_doc",
            sheet_id=sheet["id"],
            version=got["version"],
            doc=doc_of(block("t", "text", TEXT, 20, 10)),
        )
        assert not result.get("isError"), result
        assert stored(client, sheet["id"])["pages"][0]["blocks"][0]["type"] == "text"
    finally:
        mcp.stop()


def test_409_after_a_teachers_edit_tells_claude(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet = new_sheet(mcp)
        got = json.loads(mcp.call("get_sheet", sheet_id=sheet["id"])["content"][0]["text"])
        teacher = doc_of(block("t", "text", TEXT, 20, 10))
        bumped = client.patch(
            f"/api/sheets/{sheet['id']}", json={"doc": teacher, "version": got["version"]}
        )
        assert bumped.status_code == 200, bumped.text
        result = mcp.call("replace_doc", sheet_id=sheet["id"], version=got["version"], doc=doc_of())
        assert result["isError"]
        said = result["content"][0]["text"]
        assert "teacher changed" in said
        # The new version, and where Claude reads the teacher's doc to build its change on.
        assert f"it is now {bumped.json()['version']}" in said
        assert "get_sheet" in said
        assert stored(client, sheet["id"]) == teacher
    finally:
        mcp.stop()


def test_render_preview_gives_a_png(server, tmp_path):
    client, mcp = start(server, tmp_path)
    try:
        sheet = new_sheet(mcp)
        image = mcp.call("render_preview", sheet_id=sheet["id"])
        assert image["content"][0]["type"] == "image"
        assert image["content"][0]["mimeType"] == "image/png"
        assert base64.b64decode(image["content"][0]["data"])[:4] == b"\x89PNG"
        far = mcp.call("render_preview", sheet_id=sheet["id"], page=5)
        assert far["isError"] and "1" in far["content"][0]["text"]
        assert client
    finally:
        mcp.stop()


def test_token_never_shows(server, tmp_path):
    client = user()
    token = token_for(client)
    good = Mcp(server, token, tmp_path, tag="good")
    bad = Mcp(server, "bt_1_wrong", tmp_path, tag="bad")
    down = Mcp(server, token, tmp_path, url="http://127.0.0.1:9", tag="down")
    try:
        sheet = new_sheet(good)
        good.call("get_sheet", sheet_id=sheet["id"])
        # A title that holds the token, so an answer does carry it: the server hides it.
        client.post("/api/sheets", json={"title": token[:80], "doc": stored(client, sheet["id"])})
        listed = good.call("list_sheets")["content"][0]["text"]
        assert "***" in listed
        assert bad.call("get_sheet", sheet_id=sheet["id"])["isError"]
        assert down.call("list_sheets")["isError"]
        outs = good.out + bad.out + down.out
        for mcp in (good, bad, down):
            mcp.stop()
        for line in outs:
            assert token not in line
        # The refused token is the one the bad server holds: it does not show either.
        assert not any("bt_1_wrong" in line for line in bad.out)
        for name in ("stderrgood.txt", "stderrbad.txt", "stderrdown.txt"):
            assert token not in (tmp_path / name).read_text()
    finally:
        for mcp in (good, bad, down):
            mcp.stop()


def test_instructions_name_the_three_types(server, tmp_path):
    _, mcp = start(server, tmp_path)
    try:
        instructions = mcp.init["instructions"]
        for word in ("text", "maths", "ruling"):
            assert word in instructions
    finally:
        mcp.stop()
