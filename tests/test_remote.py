"""The remote MCP route /mcp: the bearer check, and the Node child that answers behind it (#654)."""

import json
import uuid

import httpx
from ui import user

from blattwerk import remote

SNAPSHOT = remote.ROOT / "tests/snapshots/mcp_tools.json"


def key_for(client):
    # A name of its own: one teacher's keys have different names.
    name = f"remote {uuid.uuid4().hex[:8]}"
    return client.post("/api/tokens", json={"name": name}).json()["token"]


def test_mcp_needs_token(server):
    response = httpx.post(f"{server}/mcp", json={}, timeout=30)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == (
        f'Bearer resource_metadata="{server}/.well-known/oauth-protected-resource/mcp"'
    )


def test_mcp_api_key_refused(server):
    key = key_for(user())
    response = httpx.post(
        f"{server}/mcp", json={}, headers={"Authorization": f"Bearer {key}"}, timeout=30
    )
    assert response.status_code == 401
    assert 'error="invalid_token"' in response.headers["www-authenticate"]


def test_child_lists_tools(server):
    key = key_for(user())
    port = remote.ensure()
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "authorization": f"Bearer {key}",
        "x-blattomat-api": server,
    }
    url = f"http://127.0.0.1:{port}/mcp"
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    assert httpx.post(url, json=initialize, headers=headers, timeout=30).status_code == 200
    listed = httpx.post(
        url, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=headers, timeout=30
    ).json()
    names = sorted(tool["name"] for tool in listed["result"]["tools"])
    assert names == sorted(tool["name"] for tool in json.loads(SNAPSHOT.read_text()))
    called = httpx.post(
        url,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_sheets", "arguments": {}},
        },
        headers=headers,
        timeout=30,
    ).json()
    assert not called["result"].get("isError")


def test_child_down(monkeypatch):
    monkeypatch.setenv("BLATTWERK_MCP_HTTP", "/nonexistent/http.mjs")
    monkeypatch.setattr(remote, "_child", None)
    monkeypatch.setattr(remote.auth, "token_user", lambda con, request, token: {"id": 1})
    client = user()
    response = client.post("/mcp", json={}, headers={"Authorization": "Bearer bo_1_secret"})
    assert response.status_code == 503
    assert client.get("/datenschutz").status_code == 200


def test_mcp_get_and_delete_answer_405_after_auth(server, monkeypatch):
    monkeypatch.setattr(remote.auth, "token_user", lambda con, request, token: {"id": 1})
    for method in ("GET", "DELETE"):
        response = httpx.request(
            method, f"{server}/mcp", headers={"Authorization": "Bearer bo_1_secret"}, timeout=30
        )
        assert response.status_code == 405
        assert response.headers["allow"] == "POST"
