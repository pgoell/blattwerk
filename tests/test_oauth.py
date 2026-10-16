"""The OAuth authorization server for the remote MCP: metadata, clients, codes, tokens."""

import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from ui import sheet, user

from blattwerk import auth, db
from blattwerk.app import app

BASE = "https://testserver"
RESOURCE = BASE + "/mcp"
REDIRECT = "https://claude.example/cb"


def anon():
    return TestClient(app, base_url=BASE)


def bearer(token):
    return TestClient(app, base_url=BASE, headers={"Authorization": f"Bearer {token}"})


def pkce():
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).decode().rstrip("=")


def register(redirect=REDIRECT, name="Claude Desktop"):
    res = anon().post("/oauth/register", json={"redirect_uris": [redirect], "client_name": name})
    assert res.status_code == 201
    return res.json()["client_id"]


def params_for(client_id, challenge, redirect=REDIRECT, **extra):
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "xyz",
    }
    return {**params, **extra}


def consent(teacher, params, approve=True):
    return teacher.post("/api/oauth/consent", json={**params, "approve": approve})


def query_of(redirect):
    return parse_qs(urlsplit(redirect).query)


def approve_code(teacher, client_id, challenge, **extra):
    res = consent(teacher, params_for(client_id, challenge, **extra))
    assert res.status_code == 200
    return query_of(res.json()["redirect"])["code"][0]


def exchange(code, client_id, verifier, redirect=REDIRECT):
    return anon().post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )


def refresh(token, client_id):
    return anon().post(
        "/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": token, "client_id": client_id},
    )


def grant(teacher):
    """Connects one program with the teacher's yes. Gives its client id and the token answer."""
    client_id = register()
    verifier, challenge = pkce()
    code = approve_code(teacher, client_id, challenge)
    res = exchange(code, client_id, verifier)
    assert res.status_code == 200
    return client_id, res.json()


def test_metadata():
    resource = {
        "resource": RESOURCE,
        "authorization_servers": [BASE],
        "bearer_methods_supported": ["header"],
        "resource_name": "Blattomat",
    }
    client = anon()
    assert client.get("/.well-known/oauth-protected-resource").json() == resource
    assert client.get("/.well-known/oauth-protected-resource/mcp").json() == resource
    server = client.get("/.well-known/oauth-authorization-server").json()
    assert server == {
        "issuer": BASE,
        "authorization_endpoint": BASE + "/oauth/authorize",
        "token_endpoint": BASE + "/oauth/token",
        "registration_endpoint": BASE + "/oauth/register",
        "revocation_endpoint": BASE + "/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
    }


def test_register():
    client = anon()
    res = client.post(
        "/oauth/register", json={"redirect_uris": [REDIRECT], "client_name": "  Claude  "}
    )
    assert res.status_code == 201
    body = res.json()
    assert set(body) == {
        "client_id",
        "client_name",
        "redirect_uris",
        "token_endpoint_auth_method",
        "grant_types",
        "response_types",
        "client_id_issued_at",
    }
    assert body["client_name"] == "Claude"
    assert body["redirect_uris"] == [REDIRECT]
    assert body["token_endpoint_auth_method"] == "none"
    assert body["grant_types"] == ["authorization_code", "refresh_token"]
    assert body["response_types"] == ["code"]
    assert isinstance(body["client_id_issued_at"], int)

    evil = client.post("/oauth/register", json={"redirect_uris": ["http://evil.example/cb"]})
    assert evil.status_code == 400
    assert evil.json()["error"] == "invalid_redirect_uri"

    secret = client.post(
        "/oauth/register",
        json={"redirect_uris": [REDIRECT], "token_endpoint_auth_method": "client_secret_basic"},
    )
    assert secret.status_code == 400

    # Ten registrations from one address in a window; the eleventh is refused.
    # The three above count too: 1 good, 1 bad redirect, 1 bad method.
    for _ in range(7):
        assert client.post("/oauth/register", json={"redirect_uris": [REDIRECT]}).status_code == 201
    assert client.post("/oauth/register", json={"redirect_uris": [REDIRECT]}).status_code == 429


def test_code_flow():
    teacher = user()
    client_id = register()
    verifier, challenge = pkce()
    params = params_for(client_id, challenge)
    shown = teacher.get("/api/oauth/authorize", params=params)
    assert shown.status_code == 200
    assert shown.json() == {
        "client_name": "Claude Desktop",
        "redirect_host": "claude.example",
        "loopback": False,
    }
    res = consent(teacher, params)
    assert res.status_code == 200
    query = query_of(res.json()["redirect"])
    assert query["state"] == ["xyz"]
    assert "iss" not in query

    token = exchange(query["code"][0], client_id, verifier)
    assert token.status_code == 200
    assert token.headers["cache-control"] == "no-store"
    body = token.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert bearer(body["access_token"]).get("/api/sheets").status_code == 200


def test_wrong_verifier():
    teacher = user()
    client_id = register()
    _, challenge = pkce()
    code = approve_code(teacher, client_id, challenge)
    res = exchange(code, client_id, "x" * 50)
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_grant"


def test_reused_code():
    teacher = user()
    client_id = register()
    verifier, challenge = pkce()
    code = approve_code(teacher, client_id, challenge)
    first = exchange(code, client_id, verifier)
    assert first.status_code == 200
    access = first.json()["access_token"]
    second = exchange(code, client_id, verifier)
    assert second.status_code == 400
    assert second.json()["error"] == "invalid_grant"
    assert bearer(access).get("/api/sheets").status_code == 401


def test_foreign_redirect():
    teacher = user()
    client_id = register()
    _, challenge = pkce()
    params = params_for(client_id, challenge, redirect="https://evil.example/cb")
    res = teacher.get("/api/oauth/authorize", params=params)
    assert res.status_code == 400
    assert "redirect" not in res.json()
    res = consent(teacher, params)
    assert res.status_code == 400
    assert "redirect" not in res.json()


def test_plain_method():
    teacher = user()
    client_id = register()
    _, challenge = pkce()
    params = params_for(client_id, challenge, code_challenge_method="plain")
    res = teacher.get("/api/oauth/authorize", params=params)
    assert res.status_code == 200
    query = query_of(res.json()["redirect"])
    assert query["error"] == ["invalid_request"]
    assert query["state"] == ["xyz"]
    res = consent(teacher, params)
    assert query_of(res.json()["redirect"])["error"] == ["invalid_request"]


def test_wrong_resource():
    teacher = user()
    client_id = register()
    _, challenge = pkce()
    params = params_for(client_id, challenge, resource="https://other.example/mcp")
    res = teacher.get("/api/oauth/authorize", params=params)
    assert res.status_code == 200
    assert query_of(res.json()["redirect"])["error"] == ["invalid_target"]


def test_deny():
    teacher = user()
    client_id = register()
    _, challenge = pkce()
    res = consent(teacher, params_for(client_id, challenge), approve=False)
    assert res.status_code == 200
    query = query_of(res.json()["redirect"])
    assert query["error"] == ["access_denied"]
    assert query["state"] == ["xyz"]
    assert "code" not in query


def test_expired_code():
    teacher = user()
    client_id = register()
    verifier, challenge = pkce()
    code = approve_code(teacher, client_id, challenge)
    db.open_db().execute("UPDATE oauth_codes SET expires = datetime('now', '-1 seconds')")
    res = exchange(code, client_id, verifier)
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_grant"


def test_expired_access():
    teacher = user()
    client_id, tokens = grant(teacher)
    con = db.open_db()
    con.execute("UPDATE oauth_grants SET access_expires = datetime('now', '-1 seconds')")
    attempts = con.execute("SELECT count(*) FROM attempts").fetchone()[0]
    assert bearer(tokens["access_token"]).get("/api/sheets").status_code == 401
    # An expired token is not a guess, so it is not counted as a bad try.
    assert con.execute("SELECT count(*) FROM attempts").fetchone()[0] == attempts
    renewed = refresh(tokens["refresh_token"], client_id)
    assert renewed.status_code == 200
    assert bearer(renewed.json()["access_token"]).get("/api/sheets").status_code == 200


def test_refresh_rotates():
    teacher = user()
    client_id, tokens = grant(teacher)
    renewed = refresh(tokens["refresh_token"], client_id)
    assert renewed.status_code == 200
    new = renewed.json()
    old_again = refresh(tokens["refresh_token"], client_id)
    assert old_again.status_code == 400
    assert old_again.json()["error"] == "invalid_grant"
    assert bearer(tokens["access_token"]).get("/api/sheets").status_code == 401
    assert bearer(new["access_token"]).get("/api/sheets").status_code == 200


def test_revoke():
    teacher = user()
    client_id, tokens = grant(teacher)
    res = anon().post("/oauth/revoke", data={"token": tokens["access_token"]})
    assert res.status_code == 200
    assert res.json() == {}
    assert bearer(tokens["access_token"]).get("/api/sheets").status_code == 401
    assert refresh(tokens["refresh_token"], client_id).status_code == 400


def test_foreign_sheet():
    teacher_a = user()
    _, tokens = grant(teacher_a)
    teacher_b = user()
    made = sheet(teacher_b, title="Geheim")
    api = bearer(tokens["access_token"])
    assert api.get(f"/api/sheets/{made['id']}").status_code == 404
    assert made["id"] not in [s["id"] for s in api.get("/api/sheets").json()]


def test_bad_token_counts():
    user()
    bad = bearer("bo_1_wrong")
    for _ in range(10):
        assert bad.get("/api/sheets").status_code == 401
    assert bad.get("/api/sheets").status_code == 429


def test_only_hashes():
    teacher = user()
    client_id = register()
    verifier, challenge = pkce()
    code = approve_code(teacher, client_id, challenge)
    tokens = exchange(code, client_id, verifier).json()
    clear = [code, tokens["access_token"], tokens["refresh_token"]]
    con = db.open_db()
    for table in ("oauth_codes", "oauth_grants"):
        for row in con.execute(f"SELECT * FROM {table}").fetchall():
            for value in tuple(row):
                for secret in clear:
                    assert secret not in str(value)


def test_reset_revokes():
    teacher = user()
    client_id, tokens = grant(teacher)
    user_id = teacher.get("/api/me").json()["id"]
    link = auth.new_link(db.open_db(), user_id)
    res = teacher.post("/api/reset", json={"token": link, "password": "neues-geheim"})
    assert res.status_code == 200
    assert bearer(tokens["access_token"]).get("/api/sheets").status_code == 401
    assert refresh(tokens["refresh_token"], client_id).json()["error"] == "invalid_grant"


def test_connections():
    teacher = user()
    _, tokens = grant(teacher)
    other = user()
    _, other_tokens = grant(other)

    listed = teacher.get("/api/connections").json()
    assert len(listed) == 1
    assert set(listed[0]) == {"id", "name", "created", "last_used"}
    assert listed[0]["name"] == "Claude Desktop"
    assert bearer(tokens["access_token"]).get("/api/connections").status_code == 401

    other_id = other.get("/api/connections").json()[0]["id"]
    assert teacher.delete(f"/api/connections/{other_id}").status_code == 404

    assert teacher.delete(f"/api/connections/{listed[0]['id']}").status_code == 200
    assert teacher.get("/api/connections").json() == []
    assert bearer(tokens["access_token"]).get("/api/sheets").status_code == 401
    assert bearer(other_tokens["access_token"]).get("/api/sheets").status_code == 200
