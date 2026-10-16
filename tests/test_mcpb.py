"""The Claude Desktop extension (static/blattomat.mcpb): unpacked, run from its manifest."""

import json
import os
import subprocess
import uuid
import zipfile
from pathlib import Path

from ui import user

ROOT = Path(__file__).parent.parent
BUNDLE = ROOT / "src/blattwerk/static/blattomat.mcpb"
DOCS = ROOT / "docs/okf"


def unpack(tmp_path):
    folder = tmp_path / "bundle"
    with zipfile.ZipFile(BUNDLE) as z:
        z.extractall(folder)
    return folder, json.loads((folder / "manifest.json").read_text())


def snapshot(*folders):
    return sorted(
        (str(Path(root) / name))
        for folder in folders
        for root, _, names in os.walk(folder)
        for name in names
    )


class Bundle:
    """The server as Claude Desktop starts it: the manifest's command and env, empty folders."""

    def __init__(self, folder, manifest, tmp_path, key, url, tag=""):
        self.cwd = tmp_path / f"cwd{tag}"
        self.home = tmp_path / f"home{tag}"
        self.cwd.mkdir()
        self.home.mkdir()
        self.err = tmp_path / f"stderr{tag}.txt"
        config = manifest["server"]["mcp_config"]

        def fill(text):
            return (
                text.replace("${__dirname}", str(folder))
                .replace("${user_config.api_key}", key)
                .replace("${user_config.url}", url)
            )

        env = {k: fill(v) for k, v in config["env"].items()}
        self.proc = subprocess.Popen(
            [config["command"], *map(fill, config["args"])],
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.err.open("w"),
            env={"PATH": os.environ["PATH"], "HOME": str(self.home), **env},
        )
        self.out = []
        self.next_id = 1

    def _send(self, message):
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(message) + "\n").encode())
        self.proc.stdin.flush()

    def reply(self, method, params=None):
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
                return message

    def start(self):
        result = self.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        )
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def request(self, method, params=None):
        message = self.reply(method, params)
        assert "error" not in message, message
        return message["result"]

    def call(self, name, **args):
        return self.request("tools/call", {"name": name, "arguments": args})

    def stop(self):
        self.proc.kill()
        self.proc.wait()


def token_for(client):
    return client.post("/api/tokens", json={"name": f"mcpb {uuid.uuid4().hex[:8]}"}).json()["token"]


def test_manifest(tmp_path):
    _, manifest = unpack(tmp_path)
    assert manifest["manifest_version"] == "0.3"
    assert manifest["server"]["type"] == "node"
    config = manifest["user_config"]
    assert config["api_key"]["type"] == "string"
    assert config["api_key"]["sensitive"] is True
    assert config["api_key"]["required"] is True
    assert config["url"]["type"] == "string"
    assert config["url"]["default"] == "https://blattwerk.pgoell.com"
    assert "darwin" in manifest["compatibility"]["platforms"]
    assert "win32" in manifest["compatibility"]["platforms"]
    assert manifest["compatibility"]["runtimes"]["node"] == ">=18.0.0"
    # Node before 22 reads a .js file as CommonJS; the bundle is a module and says so by name.
    entry = manifest["server"]["entry_point"]
    assert entry.endswith(".mjs")
    assert manifest["server"]["mcp_config"]["args"] == ["${__dirname}/" + entry]


def test_the_unpacked_bundle_makes_a_sheet(server, tmp_path):
    folder, manifest = unpack(tmp_path)
    client = user()
    mcp = Bundle(folder, manifest, tmp_path, token_for(client), server)
    try:
        mcp.start()
        names = {t["name"] for t in mcp.request("tools/list")["tools"]}
        assert "create_sheet" in names
        made = json.loads(mcp.call("create_sheet", title="Bundle")["content"][0]["text"])
        assert client.get(f"/api/sheets/{made['id']}").json()["title"] == "Bundle"
        resources = mcp.request("resources/list")["resources"]
        assert "blattomat://okf/index.md" in {r["uri"] for r in resources}
        contents = mcp.request("resources/read", {"uri": "blattomat://okf/index.md"})["contents"]
        assert contents[0]["text"] == (DOCS / "index.md").read_text()
    finally:
        mcp.stop()


def test_the_key_never_shows(server, tmp_path):
    folder, manifest = unpack(tmp_path)
    key = token_for(user())
    wrong = "bt_9_" + uuid.uuid4().hex
    cases = {
        "a": (wrong, server),
        "b": (key, "http://127.0.0.1:9"),
    }
    for tag, (token, url) in cases.items():
        before = snapshot(folder, tmp_path / f"cwd-{tag}", tmp_path / f"home-{tag}")
        mcp = Bundle(folder, manifest, tmp_path, token, url, tag=f"-{tag}")
        try:
            mcp.start()
            result = mcp.call("list_sheets")
            assert result["isError"]
            assert token not in json.dumps(result)
        finally:
            mcp.stop()
        for line in mcp.out:
            assert token not in line
        assert token not in mcp.err.read_text()
        assert snapshot(folder, tmp_path / f"cwd-{tag}", tmp_path / f"home-{tag}") == before

    # (c): the key is good, the API answers with an error body.
    client = user()
    real = token_for(client)
    before = snapshot(folder, tmp_path / "cwd-c", tmp_path / "home-c")
    mcp = Bundle(folder, manifest, tmp_path, real, server, tag="-c")
    try:
        mcp.start()
        made = json.loads(mcp.call("create_sheet", title="Fehler")["content"][0]["text"])
        props = {"ops": ["+"], "max": 20, "count": 12, "columns": 7, "size": 14}
        block = {"type": "maths", "id": "m", "x": 15, "y": 20, "w": 180, "h": 10, "z": 1}
        bad = {
            "pages": [{"blocks": [{**block, "locked": False, "props": props}]}],
            "guides": {"x": [], "y": []},
            "grid": 0,
        }
        result = mcp.call("replace_doc", sheet_id=made["id"], version=made["version"], doc=bad)
        assert result["isError"]
        assert real not in json.dumps(result)
    finally:
        mcp.stop()
    for line in mcp.out:
        assert real not in line
    assert real not in mcp.err.read_text()
    assert snapshot(folder, tmp_path / "cwd-c", tmp_path / "home-c") == before


def test_an_empty_key_says_so(tmp_path):
    folder, manifest = unpack(tmp_path)
    mcp = Bundle(folder, manifest, tmp_path, "", "http://127.0.0.1:9", tag="-empty")
    try:
        assert mcp.proc.wait(timeout=30) == 1
    finally:
        mcp.stop()
    text = mcp.err.read_text()
    assert "BLATTWERK_TOKEN" in text
    assert "API key" in text
    # A message, not a crash: Node prints a stack's "    at " lines when it throws.
    assert "    at " not in text


def test_the_url_may_end_in_api(server, tmp_path):
    folder, manifest = unpack(tmp_path)
    client = user()
    mcp = Bundle(folder, manifest, tmp_path, token_for(client), server + "/api/", tag="-api")
    try:
        mcp.start()
        result = mcp.call("list_sheets")
        assert not result.get("isError"), result
    finally:
        mcp.stop()
