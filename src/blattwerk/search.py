"""Picture search through Pixabay.

Openclipart's public search answers with a web page, and its API wants an app token, so this asks
Pixabay alone. The browser is given no address of Pixabay's: the server asks, keeps the answer for
a day, as Pixabay requires, and copies a chosen picture into the teacher's uploads. Pixabay's
licence asks for no credit.
"""

import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from blattwerk import db, uploads
from blattwerk.auth import Teacher
from blattwerk.db import Con, Id

PIXABAY = "https://pixabay.com/api/"
SOURCE = "Pixabay"
LICENCE = "Pixabay-Lizenz"
DAY = 24 * 60 * 60
PER_PAGE = 20
LANG = "de"
# What Zeichnungen keeps. A photo copies badly in black and white, so it is off unless asked.
DRAWN = {"illustration", "vector"}
KEPT = DRAWN | {"photo"}
UNREACHABLE = "Die Bildsuche ist gerade nicht erreichbar."

router = APIRouter(prefix="/api")


def now() -> float:
    return time.time()


def key() -> str | None:
    found = os.environ.get("BLATTWERK_PIXABAY_KEY", "").strip()
    return found or None


def allowed(url: str) -> bool:
    """Whether the address is https on pixabay.com. A lookalike host is not."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    return parts.scheme == "https" and (host == "pixabay.com" or host.endswith(".pixabay.com"))


def fetch(url: str) -> tuple[int, bytes, str]:
    """The answer from a Pixabay address. A redirect that leaves Pixabay is refused."""
    # The address carries the key: it is never logged and never handed to the browser.
    if not allowed(url):
        raise HTTPException(502, UNREACHABLE)
    try:
        res = httpx.get(url, timeout=20, follow_redirects=True)
    except httpx.HTTPError:
        raise HTTPException(502, UNREACHABLE) from None
    if not allowed(str(res.url)):
        raise HTTPException(502, UNREACHABLE)
    if res.status_code != 200:
        raise HTTPException(502, UNREACHABLE)
    kind = res.headers.get("content-type", "application/octet-stream").split(";", 1)[0].strip()
    return res.status_code, res.content, kind


def whole(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0


def shape(raw: object, drawings: bool) -> dict | None:
    """One hit the server may keep, or none when the address or the type is not one we take."""
    if not isinstance(raw, dict) or type(raw.get("id")) is not int:
        return None
    kind = raw.get("type")
    if kind not in (DRAWN if drawings else KEPT):
        return None
    page = raw.get("pageURL")
    preview = raw.get("previewURL")
    download = raw.get("largeImageURL") or raw.get("webformatURL")
    author = raw.get("user")
    if not isinstance(page, str) or not allowed(page):
        return None
    if not isinstance(preview, str) or not allowed(preview):
        return None
    if not isinstance(download, str) or not allowed(download):
        return None
    if not isinstance(author, str) or not author.strip():
        return None
    width = whole(raw.get("imageWidth")) or whole(raw.get("webformatWidth"))
    height = whole(raw.get("imageHeight")) or whole(raw.get("webformatHeight"))
    return {
        "id": raw["id"],
        "preview": preview,
        "download": download,
        "source": SOURCE,
        "author": author,
        "licence": LICENCE,
        "page": page,
        "width": width,
        "height": height,
    }


def ask(term: str, drawings: bool) -> list[dict]:
    """Pixabay's hits for the term. Zeichnungen is two calls: image_type takes one value."""
    kinds = ("illustration", "vector") if drawings else ("all",)
    found: list[dict] = []
    seen: set[int] = set()
    for kind in kinds:
        query = urlencode(
            [
                ("key", key() or ""),
                ("q", term),
                ("lang", LANG),
                ("image_type", kind),
                ("safesearch", "true"),
                ("per_page", str(PER_PAGE)),
            ]
        )
        _status, body, _kind = fetch(f"{PIXABAY}?{query}")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(502, UNREACHABLE) from None
        if not isinstance(payload, dict):
            raise HTTPException(502, UNREACHABLE)
        for raw in payload.get("hits") or []:
            hit = shape(raw, drawings)
            if hit and hit["id"] not in seen:
                seen.add(hit["id"])
                found.append(hit)
    return found


def cache_name(term: str, drawings: bool) -> str:
    # The term stays as searched: two writings are two requests, and the key is not here.
    return f"{LANG}\n{int(drawings)}\n{term}"


def load(con: Con, name: str) -> list[dict] | None:
    row = con.execute("SELECT hits, until FROM picture_cache WHERE name = ?", (name,)).fetchone()
    if not row or row["until"] <= now():
        return None
    hits = json.loads(row["hits"])
    return hits if isinstance(hits, list) else None


def save(con: Con, name: str, hits: list[dict]) -> None:
    until = now() + DAY
    con.execute("DELETE FROM picture_cache WHERE until <= ?", (now(),))
    con.execute(
        "INSERT INTO picture_cache (name, hits, until) VALUES (?, ?, ?)"
        " ON CONFLICT(name) DO UPDATE SET hits = excluded.hits, until = excluded.until",
        (name, json.dumps(hits), until),
    )


def find(con: Con, hit_id: int) -> dict | None:
    rows = con.execute("SELECT hits, until FROM picture_cache").fetchall()
    for row in rows:
        if row["until"] <= now():
            continue
        for hit in json.loads(row["hits"]):
            if isinstance(hit, dict) and hit.get("id") == hit_id:
                return hit
    return None


def public(hit: dict) -> dict:
    """What the browser may see. The preview is our address, never Pixabay's."""
    return {
        "id": hit["id"],
        "preview": f"/api/picture-search/{hit['id']}/preview",
        "source": hit["source"],
        "author": hit["author"],
        "licence": hit["licence"],
        "page": hit["page"],
        "width": hit["width"],
        "height": hit["height"],
    }


@router.get("/picture-search")
async def find_pictures(user: Teacher, con: Con, q: str = "", drawings: bool = True) -> dict:
    """Hits for a term. The teacher is checked and not sent on: Pixabay sees the term only."""
    del user
    term = " ".join(q.split())
    if not term:
        return {"hits": []}
    if len(term) > 100:
        raise HTTPException(400, "Der Suchbegriff darf 100 Zeichen lang sein.")
    if key() is None:
        raise HTTPException(503, "Die Bildsuche ist nicht eingerichtet.")
    name = cache_name(term, drawings)
    hits = load(con, name)
    if hits is None:
        hits = await run_in_threadpool(ask, term, drawings)
        save(con, name, hits)
    return {"hits": [public(hit) for hit in hits]}


def kept(hit_id: int) -> tuple[Path, Path]:
    """The preview's file and the note of when it goes, under the data dir of this process."""
    folder = db.DATA_DIR / "picture-search"
    return folder / str(hit_id), folder / f"{hit_id}.json"


@router.get("/picture-search/{hit_id}/preview")
async def preview(hit_id: Id, user: Teacher, con: Con):
    """The small picture, fetched by the server and kept for a day."""
    del user
    hit = find(con, hit_id)
    if not hit:
        raise HTTPException(404)
    file, meta = kept(hit_id)
    fresh = False
    kind = ""
    if file.is_file() and meta.is_file():
        try:
            note = json.loads(meta.read_text(encoding="utf-8"))
            fresh = note.get("until", 0) > now()
            kind = note.get("type", "")
        except OSError, json.JSONDecodeError, AttributeError:
            fresh = False
    if not fresh or not isinstance(kind, str) or not kind.startswith("image/"):
        status, data, _kind = await run_in_threadpool(fetch, hit["preview"])
        if status != 200:
            raise HTTPException(502, UNREACHABLE)
        sniffed = uploads.kind(data)
        # An SVG would be a document. The preview is a picture the browser draws and nothing more.
        if sniffed is None or sniffed == "image/svg+xml":
            raise HTTPException(502, UNREACHABLE)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        meta.write_text(json.dumps({"until": now() + DAY, "type": sniffed}), encoding="utf-8")
        kind = sniffed
    else:
        data = file.read_bytes()
    return Response(content=data, media_type=kind, headers=dict(uploads.NOSNIFF))


@router.post("/picture-search/{hit_id}")
async def take(hit_id: Id, user: Teacher, con: Con) -> dict:
    """Copies one cached hit into the teacher's uploads. The id is ours, never an address."""
    hit = find(con, hit_id)
    if not hit:
        raise HTTPException(404)
    status, data, _kind = await run_in_threadpool(fetch, hit["download"])
    if status != 200:
        raise HTTPException(502, UNREACHABLE)
    data, type_ = await uploads.stored(data)
    upload_id = uploads.write_upload(
        con,
        user["id"],
        data,
        type_,
        {
            "source": hit["source"],
            "author": hit["author"],
            "licence": hit["licence"],
            "page": hit["page"],
        },
    )
    return {"id": upload_id}
