"""OAuth 2.1 for the remote MCP: a program asks, the teacher says yes, the program gets tokens."""

import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from typing import Annotated
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from blattwerk import auth, db
from blattwerk.db import Con, Id

CODE_SECONDS = 300
ACCESS_SECONDS = 3600
REFRESH_DAYS = 90
# The unreserved characters of RFC 7636: a PKCE challenge or verifier is 43 to 128 of them.
PKCE = re.compile(r"[A-Za-z0-9\-._~]{43,128}")
LOOPBACK = ("localhost", "127.0.0.1")
DEFAULT_NAME = "Unbekanntes Programm"
REGISTER_TRIES = 100

router = APIRouter()


def origin(request: Request) -> str:
    # Behind the proxy the scheme comes from the forwarded headers (uvicorn --proxy-headers).
    return f"{request.url.scheme}://{request.url.netloc}"


def answer(content: dict, status: int = 200) -> JSONResponse:
    # Tokens and errors must not sit in a cache.
    return JSONResponse(content, status, headers={"Cache-Control": "no-store"})


def refuse(error: str, text: str) -> JSONResponse:
    return answer({"error": error, "error_description": text}, 400)


def good_redirect(uri: str) -> bool:
    # https anywhere, or plain http only on this machine: a native program listens there.
    try:
        parts = urlsplit(uri)
        # Reading the port raises when it is not a number in range.
        port_ok = parts.port is None or 0 <= parts.port <= 65535
    except ValueError:
        return False
    if not port_ok or parts.fragment or not parts.hostname:
        return False
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in LOOPBACK)


def redirect_to(uri: str, **params: str | None) -> str:
    params = {key: value for key, value in params.items() if value is not None}
    return uri + ("&" if "?" in uri else "?") + urlencode(params)


def checked(con: sqlite3.Connection, base: str, asked: dict) -> sqlite3.Row:
    """The client of a request. A bad request is a 400 page, never a redirect.

    Used by the page that asks and by the teacher's yes, so both judge a request the same way.
    """
    client = con.execute(
        "SELECT * FROM oauth_clients WHERE id = ?", (str(asked.get("client_id", "")),)
    ).fetchone()
    # Never send anyone to an address the client did not register: that would be an open redirect.
    if not client or asked.get("redirect_uri") not in json.loads(client["redirect_uris"]):
        raise HTTPException(400, "Das Programm ist nicht bekannt oder seine Adresse stimmt nicht.")
    # A redirect with an error would send the page on with no click, so these are 400 too.
    if (
        asked.get("response_type") != "code"
        or not PKCE.fullmatch(str(asked.get("code_challenge", "")))
        or asked.get("code_challenge_method") != "S256"
    ):
        raise HTTPException(400, "Die Anfrage ist nicht gültig: nur Code mit S256.")
    if asked.get("resource") not in (None, "", base + "/mcp"):
        raise HTTPException(400, "Die Anfrage gilt für ein anderes Ziel als Blattomat.")
    return client


def issue(con: sqlite3.Connection, grant_id: int, refresh_was: str | None = None) -> dict | None:
    """New tokens for a grant. A refresh passes the refresh hash it read: if another refresh
    rotated it since, nothing changes and the answer is None.
    """
    # The grant id is part of each token, so the id comes first and the tokens after it.
    access = f"bo_{grant_id}_{secrets.token_urlsafe(32)}"
    refresh = f"br_{grant_id}_{secrets.token_urlsafe(32)}"
    cur = con.execute(
        "UPDATE oauth_grants SET access_hash = ?, access_expires = datetime('now', ?),"
        " refresh_hash = ?, refresh_expires = datetime('now', ?)"
        " WHERE id = ? AND (? IS NULL OR refresh_hash = ?)",
        (
            auth.digest(access),
            f"+{ACCESS_SECONDS} seconds",
            auth.digest(refresh),
            f"+{REFRESH_DAYS} days",
            grant_id,
            refresh_was,
            refresh_was,
        ),
    )
    if not cur.rowcount:
        return None
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": ACCESS_SECONDS,
        "refresh_token": refresh,
    }


def grant_id_of(token: str) -> int | None:
    # A token starts with its kind and its grant id: bo_<id>_<secret> or br_<id>_<secret>.
    parts = token.split("_", 2)
    if len(parts) != 3 or parts[0] not in ("bo", "br") or not db.ID.fullmatch(parts[1]):
        return None
    return int(parts[1]) if int(parts[1]) < 2**63 else None


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/mcp")
def protected_resource(request: Request) -> dict:
    base = origin(request)
    return {
        "resource": base + "/mcp",
        "authorization_servers": [base],
        "bearer_methods_supported": ["header"],
        "resource_name": "Blattomat",
    }


@router.get("/.well-known/oauth-authorization-server")
def authorization_server(request: Request) -> dict:
    base = origin(request)
    return {
        "issuer": base,
        "authorization_endpoint": base + "/oauth/authorize",
        "token_endpoint": base + "/oauth/token",
        "registration_endpoint": base + "/oauth/register",
        "revocation_endpoint": base + "/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
    }


@router.post("/oauth/register", status_code=201)
def register(body: dict, request: Request, con: Con) -> JSONResponse:
    # Many teachers' programs share Anthropic's few addresses, so the tries are generous.
    auth.limit(con, f"register:{request.client.host if request.client else ''}", REGISTER_TRIES)
    # Clients nobody connected, from a day or more ago, go: the table stays small.
    con.execute(
        "DELETE FROM oauth_clients WHERE created <= datetime('now', '-1 days')"
        " AND id NOT IN (SELECT client_id FROM oauth_grants)"
    )
    con.execute("DELETE FROM oauth_codes WHERE expires <= datetime('now')")
    uris = body.get("redirect_uris")
    if not isinstance(uris, list) or not 1 <= len(uris) <= 5:
        return refuse("invalid_client_metadata", "redirect_uris needs 1 to 5 addresses")
    if not all(isinstance(uri, str) and len(uri) <= 2000 for uri in uris):
        return refuse("invalid_client_metadata", "each redirect URI is text of at most 2000")
    if not all(good_redirect(uri) for uri in uris):
        return refuse("invalid_redirect_uri", "use https, or http on localhost or 127.0.0.1")
    if body.get("token_endpoint_auth_method", "none") != "none":
        return refuse("invalid_client_metadata", "the client has no secret: use none")
    name = body.get("client_name") or DEFAULT_NAME
    if not isinstance(name, str):
        return refuse("invalid_client_metadata", "client_name is text")
    name = name.strip()[:100] or DEFAULT_NAME
    client_id = secrets.token_urlsafe(16)
    con.execute(
        "INSERT INTO oauth_clients (id, name, redirect_uris) VALUES (?, ?, ?)",
        (client_id, name, json.dumps(uris)),
    )
    return JSONResponse(
        {
            "client_id": client_id,
            "client_name": name,
            "redirect_uris": uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_id_issued_at": int(time.time()),
        },
        201,
    )


@router.get("/api/oauth/authorize")
def authorize(request: Request, user: auth.User, con: Con) -> dict:
    # The page the teacher sees: who asks, and where the answer goes.
    asked = dict(request.query_params)
    client = checked(con, origin(request), asked)
    uri = asked["redirect_uri"]
    host = urlsplit(uri).hostname
    return {"client_name": client["name"], "redirect_host": host, "loopback": host in LOOPBACK}


@router.post("/api/oauth/consent")
def consent(body: dict, request: Request, user: auth.User, con: Con) -> dict:
    client = checked(con, origin(request), body)
    uri = body["redirect_uri"]
    state = body.get("state")
    if body.get("approve") is not True:
        return {"redirect": redirect_to(uri, error="access_denied", state=state)}
    code = secrets.token_urlsafe(32)
    # Only the hash is kept, so a leaked database gives no code to use.
    con.execute(
        "INSERT INTO oauth_codes (hash, client_id, user_id, redirect_uri, challenge, resource,"
        " expires) VALUES (?, ?, ?, ?, ?, ?, datetime('now', ?))",
        (
            auth.digest(code),
            client["id"],
            user["id"],
            uri,
            body["code_challenge"],
            origin(request) + "/mcp",
            f"+{CODE_SECONDS} seconds",
        ),
    )
    return {"redirect": redirect_to(uri, code=code, state=state)}


@router.post("/oauth/token")
def token(
    request: Request,
    con: Con,
    grant_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()] = "",
    code: Annotated[str, Form()] = "",
    redirect_uri: Annotated[str, Form()] = "",
    code_verifier: Annotated[str, Form()] = "",
    refresh_token: Annotated[str, Form()] = "",
    resource: Annotated[str, Form()] = "",
) -> JSONResponse:
    now = con.execute("SELECT datetime('now')").fetchone()[0]
    if grant_type == "authorization_code":
        # A code works once: taking it deletes it.
        row = con.execute(
            "DELETE FROM oauth_codes WHERE hash = ? RETURNING *", (auth.digest(code),)
        ).fetchone()
        if row is None:
            # A code used twice means someone has it: what it made is revoked too.
            con.execute("DELETE FROM oauth_grants WHERE code = ?", (auth.digest(code),))
            return refuse("invalid_grant", "the code is used or unknown")
        if (
            row["expires"] <= now
            or row["client_id"] != client_id
            or row["redirect_uri"] != redirect_uri
        ):
            return refuse("invalid_grant", "the code is expired or was asked for elsewhere")
        if not PKCE.fullmatch(code_verifier):
            return refuse("invalid_grant", "the code_verifier does not match")
        sent = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        if not hmac.compare_digest(sent.rstrip(b"=").decode(), row["challenge"]):
            return refuse("invalid_grant", "the code_verifier does not match")
        if resource and resource != row["resource"]:
            return answer({"error": "invalid_target"}, 400)
        grant_id = con.execute(
            "INSERT INTO oauth_grants (user_id, client_id, code, access_hash, access_expires,"
            " refresh_hash, refresh_expires, resource) VALUES (?, ?, ?, '', '', '', '', ?)"
            " RETURNING id",
            (row["user_id"], row["client_id"], row["hash"], row["resource"]),
        ).fetchone()[0]
        # A new grant has no refresh hash to compare, so the rotation always applies here.
        return answer(issue(con, grant_id) or {})
    if grant_type == "refresh_token":
        grant_id = grant_id_of(refresh_token)
        row = None
        if grant_id is not None and refresh_token.startswith("br_"):
            row = con.execute("SELECT * FROM oauth_grants WHERE id = ?", (grant_id,)).fetchone()
        if (
            row is None
            or not hmac.compare_digest(row["refresh_hash"], auth.digest(refresh_token))
            or row["refresh_expires"] <= now
            or row["client_id"] != client_id
        ):
            return refuse("invalid_grant", "the refresh token is unknown, expired or used")
        if resource and resource != row["resource"]:
            return answer({"error": "invalid_target"}, 400)
        tokens = issue(con, row["id"], row["refresh_hash"])
        if tokens is None:
            return refuse("invalid_grant", "the refresh token is unknown, expired or used")
        return answer(tokens)
    return refuse("unsupported_grant_type", "use authorization_code or refresh_token")


@router.post("/oauth/revoke")
def revoke(con: Con, token: Annotated[str, Form()]) -> JSONResponse:
    # RFC 7009: the answer is the same whether the token was ours or not.
    grant_id = grant_id_of(token)
    if grant_id is not None:
        column = "access_hash" if token.startswith("bo_") else "refresh_hash"
        con.execute(
            f"DELETE FROM oauth_grants WHERE id = ? AND {column} = ?",
            (grant_id, auth.digest(token)),
        )
    return answer({})


@router.get("/api/connections")
def connections(user: auth.User, con: Con) -> list[dict]:
    rows = con.execute(
        "SELECT oauth_grants.id, oauth_clients.name, oauth_grants.created, oauth_grants.last_used"
        " FROM oauth_grants JOIN oauth_clients ON oauth_clients.id = oauth_grants.client_id"
        " WHERE oauth_grants.user_id = ? ORDER BY oauth_grants.created DESC, oauth_grants.id DESC",
        (user["id"],),
    ).fetchall()
    return [dict(row) for row in rows]


@router.delete("/api/connections/{connection_id}")
def disconnect(connection_id: Id, user: auth.User, con: Con) -> dict:
    cur = con.execute(
        "DELETE FROM oauth_grants WHERE id = ? AND user_id = ?", (connection_id, user["id"])
    )
    if not cur.rowcount:
        raise HTTPException(404)
    return {}
