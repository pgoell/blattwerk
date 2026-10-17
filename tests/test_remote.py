"""The remote MCP route /mcp: the bearer check, and the Node child that answers behind it (#654)."""

import json
import socket
import time
import uuid

import httpx
from test_oauth import grant
from ui import user

from blattwerk import remote

SNAPSHOT = remote.ROOT / "tests/snapshots/mcp_tools.json"
SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
    '<rect width="200" height="100"/></svg>'
)


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


def test_child_survives_a_cut_request(server):
    port = remote.ensure()
    # A request whose body stops short: the client closes the socket with 990 bytes still to come.
    cut = socket.create_connection(("127.0.0.1", port), timeout=5)
    cut.sendall(
        b"POST /mcp HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\n"
        b"Content-Length: 1000\r\n\r\n0123456789"
    )
    cut.close()
    time.sleep(0.5)
    child = remote._child
    assert child is not None and child[0].poll() is None, "the child exited on a cut request"
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
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "authorization": "Bearer bt_test",
        "x-blattomat-api": server,
    }
    answer = httpx.post(
        f"http://127.0.0.1:{port}/mcp", json=initialize, headers=headers, timeout=30
    )
    assert answer.status_code == 200


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


def test_upload_picture_through_mcp_with_oauth(server):
    teacher = user()
    _client_id, token = grant(teacher)
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "authorization": f"Bearer {token['access_token']}",
    }
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
    assert (
        httpx.post(f"{server}/mcp", json=initialize, headers=headers, timeout=60).status_code == 200
    )
    call = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "upload_picture", "arguments": {"svg": SVG}},
    }
    answer = httpx.post(f"{server}/mcp", json=call, headers=headers, timeout=60).json()["result"]
    assert not answer.get("isError"), answer
    picture = json.loads(answer["content"][0]["text"])["upload"]
    assert teacher.get(f"/api/uploads/{picture}").status_code == 200
