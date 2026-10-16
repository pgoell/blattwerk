"""The remote MCP route /mcp: checks the bearer token, then hands the request to a Node child.

The child (frontend/mcp/http.ts, or BLATTWERK_MCP_HTTP in the image) runs the same tools as stdio.
"""

import json
import os
import queue
import subprocess
import threading
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from blattwerk import auth
from blattwerk.db import Con

ROOT = Path(__file__).resolve().parents[2]
router = APIRouter()
_lock = threading.Lock()
_child: tuple[subprocess.Popen, int] | None = None


def challenge(request: Request, error: str | None = None) -> dict[str, str]:
    base = f"{request.url.scheme}://{request.url.netloc}"
    value = f'Bearer resource_metadata="{base}/.well-known/oauth-protected-resource/mcp"'
    if error:
        value += f', error="{error}"'
    return {"WWW-Authenticate": value}


def start() -> tuple[subprocess.Popen, int]:
    script = os.environ.get("BLATTWERK_MCP_HTTP") or str(ROOT / "frontend/mcp/http.ts")
    try:
        proc = subprocess.Popen(
            ["node", script], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
    except OSError as error:
        raise HTTPException(503) from error
    # The first line says the port. A thread reads it, so the wait can end.
    assert proc.stdout is not None
    out = proc.stdout
    first: queue.Queue[str] = queue.Queue()
    threading.Thread(target=lambda: first.put(out.readline()), daemon=True).start()
    try:
        return proc, json.loads(first.get(timeout=30))["port"]
    except (queue.Empty, ValueError, KeyError, TypeError) as error:
        proc.kill()
        raise HTTPException(503) from error


def ensure() -> int:
    """The port of the child, started now when none runs."""
    global _child
    with _lock:
        if _child is None or _child[0].poll() is not None:
            _child = start()
        return _child[1]


def stop() -> None:
    """Ends the child: its stdin closes, and it exits."""
    global _child
    with _lock:
        if _child is not None:
            assert _child[0].stdin is not None
            _child[0].stdin.close()
            _child[0].wait(timeout=10)
            _child = None


@router.api_route("/mcp", methods=["GET", "POST", "DELETE"])
async def mcp(request: Request, con: Con) -> Response:
    header = request.headers.get("authorization")
    if header is None:
        raise HTTPException(401, headers=challenge(request))
    scheme, _, token = header.partition(" ")
    # An API key is not a token for /mcp: only the tokens of the OAuth grants come through.
    if scheme.lower() != "bearer" or not token.startswith("bo_"):
        raise HTTPException(401, headers=challenge(request, "invalid_token"))
    try:
        auth.token_user(con, request, token)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        raise HTTPException(401, headers=challenge(request, "invalid_token")) from error
    if request.method != "POST":
        return Response(status_code=405, headers={"Allow": "POST"})
    port = await run_in_threadpool(ensure)
    forwarded = {
        "authorization": header,
        "x-blattomat-api": f"http://127.0.0.1:{request.scope['server'][1]}",
    }
    for name in ("content-type", "accept", "mcp-protocol-version"):
        if name in request.headers:
            forwarded[name] = request.headers[name]
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            answer = await client.post(
                f"http://127.0.0.1:{port}/mcp", content=await request.body(), headers=forwarded
            )
    except httpx.HTTPError as error:
        raise HTTPException(503) from error
    return Response(
        content=answer.content,
        status_code=answer.status_code,
        media_type=answer.headers.get("content-type"),
    )
