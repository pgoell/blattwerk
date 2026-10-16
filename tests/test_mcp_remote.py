"""The remote connector at /mcp, driven end to end by the MCP SDK's client, as Claude does it."""

import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import httpx2
from mcp.client.auth import AuthorizationCodeResult, OAuthClientProvider
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from ui import user

from blattwerk import db

TOOLS = json.loads((Path(__file__).parent / "snapshots/mcp_tools.json").read_text())
REDIRECT = "http://localhost:3118/callback"


class Memory:
    def __init__(self):
        self.tokens: OAuthToken | None = None
        self.client: OAuthClientInformationFull | None = None

    async def get_tokens(self):
        return self.tokens

    async def set_tokens(self, tokens):
        self.tokens = tokens

    async def get_client_info(self):
        return self.client

    async def set_client_info(self, client_info):
        self.client = client_info


def connector(server, session, storage, seen):
    """The SDK's OAuth client. The teacher's browser is a cookie that says yes."""
    cookie = {"cookie": f"session={session}"}
    got = {}

    async def redirect_handler(url):
        params = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        seen.append(params)
        async with httpx.AsyncClient() as http:
            ask = await http.get(f"{server}/api/oauth/authorize", params=params, headers=cookie)
            assert ask.status_code == 200, ask.text
            assert ask.json()["client_name"] == "Testprogramm"
            yes = await http.post(
                f"{server}/api/oauth/consent", json={**params, "approve": True}, headers=cookie
            )
            assert yes.status_code == 200, yes.text
        back = parse_qs(urlsplit(yes.json()["redirect"]).query)
        got.update(code=back["code"][0], state=back["state"][0])

    async def callback_handler():
        return AuthorizationCodeResult(code=got["code"], state=got["state"])

    return OAuthClientProvider(
        server_url=f"{server}/mcp",
        client_metadata=OAuthClientMetadata(
            client_name="Testprogramm",
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none",
        ),
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )


async def talk(server, provider, *calls):
    """One connection to /mcp: the tool names, then each call's result."""
    async with (
        httpx2.AsyncClient(auth=provider) as http,
        streamable_http_client(f"{server}/mcp", http_client=http) as (read, write),
        ClientSession(read, write) as mcp,
    ):
        await mcp.initialize()
        names = [tool.name for tool in (await mcp.list_tools()).tools]
        results = [await mcp.call_tool(name, args) for name, args in calls]
    return names, results


def test_remote_flow(server):
    teacher = user()
    session = teacher.cookies["session"]
    storage, seen = Memory(), []
    provider = connector(server, session, storage, seen)

    names, [made] = asyncio.run(talk(server, provider, ("create_sheet", {"title": "Von Claude"})))
    # The same tools as the extension, from the same code.
    assert sorted(names) == sorted(tool["name"] for tool in TOOLS)
    assert not made.is_error, made
    # The sheet lies in the teacher's own account.
    assert "Von Claude" in [s["title"] for s in teacher.get("/api/sheets").json()]
    # One sign-in, with S256 and this server as the audience.
    assert len(seen) == 1
    assert seen[0]["code_challenge_method"] == "S256"
    assert seen[0]["resource"] == f"{server}/mcp"
    assert storage.client is not None
    assert storage.tokens is not None
    first = storage.tokens

    # The access token runs out: the client refreshes, and the old refresh token is dead.
    con = db.open_db()
    con.execute("UPDATE oauth_grants SET access_expires = datetime('now', '-1 seconds')")
    # This SDK refreshes by its own clock (Claude also on a 401), so its clock runs out too.
    provider.context.token_expiry_time = 1
    names, [listed] = asyncio.run(talk(server, provider, ("list_sheets", {})))
    assert not listed.is_error, listed
    assert "Von Claude" in str(listed.content)
    assert len(seen) == 1, "a refresh, not a new sign-in"
    assert storage.tokens.access_token != first.access_token
    assert storage.tokens.refresh_token != first.refresh_token
    old = httpx.post(
        f"{server}/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": first.refresh_token,
            "client_id": storage.client.client_id,
        },
    )
    assert old.status_code == 400
    assert old.json()["error"] == "invalid_grant"

    # Revoked, the token no longer opens /mcp.
    token = storage.tokens.access_token
    assert httpx.post(f"{server}/oauth/revoke", data={"token": token}).status_code == 200
    gone = httpx.post(
        f"{server}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={
            "authorization": f"Bearer {token}",
            "accept": "application/json, text/event-stream",
        },
    )
    assert gone.status_code == 401
    assert 'error="invalid_token"' in gone.headers["www-authenticate"]
    assert teacher.get("/api/connections").json() == []


def test_remote_expired_token(server):
    teacher = user()
    storage = Memory()
    asyncio.run(talk(server, connector(server, teacher.cookies["session"], storage, [])))
    assert storage.tokens is not None
    con = db.open_db()
    con.execute("UPDATE oauth_grants SET access_expires = datetime('now', '-1 seconds')")
    before = con.execute("SELECT count(*) FROM attempts").fetchone()[0]
    late = httpx.post(
        f"{server}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={
            "authorization": f"Bearer {storage.tokens.access_token}",
            "accept": "application/json, text/event-stream",
        },
    )
    assert late.status_code == 401
    assert (
        f'resource_metadata="{server}/.well-known/oauth-protected-resource/mcp"'
        in (late.headers["www-authenticate"])
    )
    # A token that ran out is no guess: it does not count against the address.
    assert con.execute("SELECT count(*) FROM attempts").fetchone()[0] == before


def test_remote_shared_address_locks_out_no_good_token(server):
    """Teachers behind one address (Anthropic's): run-out or wrong tokens never block a good one."""
    late, good = Memory(), Memory()
    asyncio.run(talk(server, connector(server, user().cookies["session"], late, [])))
    asyncio.run(talk(server, connector(server, user().cookies["session"], good, [])))
    assert late.tokens is not None
    assert good.tokens is not None
    con = db.open_db()
    con.execute(
        "UPDATE oauth_grants SET access_expires = datetime('now', '-1 seconds') WHERE id = ?",
        (int(late.tokens.access_token.split("_")[1]),),
    )

    def ask(token):
        return httpx.post(
            f"{server}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={
                "authorization": f"Bearer {token}",
                "accept": "application/json, text/event-stream",
                "mcp-protocol-version": "2025-06-18",
            },
        ).status_code

    # A run-out token is no guess: as often as the client likes, a 401 that makes it refresh.
    assert [ask(late.tokens.access_token) for _ in range(15)] == [401] * 15
    # Wrong tokens from the address count, and past the limit they get 429 ...
    assert [ask("bo_1_wrong") for _ in range(11)][-1] == 429
    # ... while the other teacher's good token from the same address goes through.
    assert ask(good.tokens.access_token) == 200


def test_remote_foreign_sheet(server):
    owner, other = user(), user()
    sheet = owner.post(
        "/api/sheets", json={"title": "Fremd", "doc": {"pages": [{"blocks": []}]}}
    ).json()
    storage = Memory()
    _, [read] = asyncio.run(
        talk(
            server,
            connector(server, other.cookies["session"], storage, []),
            ("get_sheet", {"sheet_id": sheet["id"]}),
        )
    )
    assert read.is_error
    assert "Fremd" not in str(read.content)
