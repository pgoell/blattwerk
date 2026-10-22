"""Picture search: Pixabay through the server, a copy in the teacher's uploads, the licence note.

Openclipart's public `/search/json/` answers with a web page, and its API wants an app token, so
these tests ask Pixabay alone. The browser is given no address of Pixabay's.
"""

import json
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from test_feed_print import pdf_text, printed, sheet_id
from ui import png, user

from blattwerk.app import app
from blattwerk.db import open_db

PNG = png()
DAY = 24 * 60 * 60


def hit(id_, kind, **more):
    body = {
        "id": id_,
        "pageURL": f"https://pixabay.com/photos/{id_}/",
        "type": kind,
        "previewURL": f"https://cdn.pixabay.com/photo/{id_}_150.jpg",
        "largeImageURL": f"https://pixabay.com/get/{id_}_1280.jpg",
        "imageWidth": 640,
        "imageHeight": 480,
        "user": "Josch13",
    }
    body.update(more)
    return body


ILLUSTRATION = hit(195893, "illustration")
PHOTO = hit(2, "photo", user="Ada")
VECTOR = hit(7, "vector", user="Ada")
EVIL = hit(
    8,
    "illustration",
    largeImageURL="https://evil.example/a.png",
    previewURL="https://evil.example/b.png",
)


def install(monkeypatch, extra=None):
    """A Pixabay that answers from `extra`, keyed by a piece of the URL, and a clock the test owns."""
    from blattwerk import search

    monkeypatch.setenv("BLATTWERK_PIXABAY_KEY", "test-key")
    clock = {"t": 1_000_000.0}
    monkeypatch.setattr(search, "now", lambda: clock["t"])
    bodies = {
        "image_type=illustration": {"hits": [ILLUSTRATION, PHOTO, EVIL]},
        "image_type=vector": {"hits": [VECTOR, ILLUSTRATION]},
        "image_type=all": {"hits": [PHOTO, ILLUSTRATION, VECTOR]},
        "cdn.pixabay.com": PNG,
        "pixabay.com/get/": PNG,
    }
    if extra:
        bodies.update(extra)
    calls = []

    def fetch(url):
        calls.append(url)
        for part, body in bodies.items():
            if part in url:
                if isinstance(body, bytes):
                    return 200, body, "image/png"
                return 200, json.dumps(body).encode(), "application/json"
        return 404, b"missing", "text/plain"

    monkeypatch.setattr(search, "fetch", fetch)
    return calls, clock


def asked(calls, image_type):
    return [url for url in calls if f"image_type={image_type}" in url]


def test_logged_out_search_is_refused():
    client = TestClient(app, base_url="https://testserver")
    assert client.get("/api/picture-search", params={"q": "Hund"}).status_code == 401
    assert client.get("/api/picture-search/1/preview").status_code == 401
    assert client.post("/api/picture-search/1").status_code == 401
    assert client.get("/api/picture-notes").status_code == 401


def test_search_without_a_key_does_not_call_pixabay(monkeypatch):
    from blattwerk import search

    monkeypatch.delenv("BLATTWERK_PIXABAY_KEY", raising=False)
    calls = []
    monkeypatch.setattr(search, "fetch", lambda url: calls.append(url))
    res = user("a@example.com").get("/api/picture-search", params={"q": "Hund"})
    assert res.status_code == 503
    assert res.json()["detail"] == "Die Bildsuche ist nicht eingerichtet."
    assert calls == []


def test_an_empty_search_asks_nothing(monkeypatch):
    calls, _ = install(monkeypatch)
    res = user("a@example.com").get("/api/picture-search", params={"q": "  "})
    assert res.status_code == 200
    assert res.json() == {"hits": []}
    assert calls == []


def test_search_asks_pixabay_for_drawings_and_hides_its_address(monkeypatch):
    """Zeichnungen is the default: illustration and vector, photos dropped, no CDN address."""
    calls, _ = install(monkeypatch)
    client = user("sucherin@example.com")
    res = client.get("/api/picture-search", params={"q": "Hund"})
    assert res.status_code == 200
    assert "test-key" not in res.text
    body = res.json()
    ids = [hit["id"] for hit in body["hits"]]
    assert ids == [195893, 7]
    assert 2 not in ids and 8 not in ids
    one = body["hits"][0]
    assert one == {
        "id": 195893,
        "preview": "/api/picture-search/195893/preview",
        "source": "Pixabay",
        "author": "Josch13",
        "licence": "Pixabay-Lizenz",
        "page": "https://pixabay.com/photos/195893/",
        "width": 640,
        "height": 480,
    }
    assert one["preview"].startswith("/api/")
    assert "cdn.pixabay.com" not in res.text
    assert len(asked(calls, "illustration")) == 1
    assert len(asked(calls, "vector")) == 1
    assert asked(calls, "all") == []
    for url in calls:
        query = parse_qs(urlsplit(url).query)
        assert query["q"] == ["Hund"]
        assert query["lang"] == ["de"]
        assert query["safesearch"] == ["true"]
        assert query["per_page"] == ["20"]
        assert "sucherin@example.com" not in url
        assert set(query) <= {"key", "q", "lang", "image_type", "safesearch", "per_page"}


def test_search_without_drawings_asks_once_for_every_type(monkeypatch):
    calls, _ = install(monkeypatch)
    res = user("a@example.com").get("/api/picture-search", params={"q": "Hund", "drawings": False})
    assert res.status_code == 200
    assert [hit["id"] for hit in res.json()["hits"]] == [2, 195893, 7]
    assert len(asked(calls, "all")) == 1
    assert asked(calls, "illustration") == []


def test_the_same_search_is_not_asked_again_for_a_day(monkeypatch):
    calls, clock = install(monkeypatch)
    client = user("a@example.com")
    assert client.get("/api/picture-search", params={"q": "Hund"}).status_code == 200
    first = len(calls)
    assert first == 2
    clock["t"] += DAY - 1
    assert client.get("/api/picture-search", params={"q": "Hund"}).status_code == 200
    assert len(calls) == first
    clock["t"] += 2
    assert client.get("/api/picture-search", params={"q": "Hund"}).status_code == 200
    assert len(calls) == first + 2


def test_a_preview_is_fetched_by_the_server(monkeypatch):
    calls, _ = install(monkeypatch)
    client = user("a@example.com")
    assert client.get("/api/picture-search", params={"q": "Hund"}).status_code == 200
    res = client.get("/api/picture-search/195893/preview")
    assert res.status_code == 200
    assert res.content == PNG
    assert res.headers["content-type"].startswith("image/png")
    assert any("cdn.pixabay.com/photo/195893" in url for url in calls)
    assert client.get("/api/picture-search/404/preview").status_code == 404


def test_a_hit_is_copied_into_the_teachers_uploads(monkeypatch):
    install(monkeypatch)
    client = user("a@example.com")
    other = user("b@example.com")
    assert client.get("/api/picture-search", params={"q": "Hund"}).status_code == 200
    made = client.post("/api/picture-search/195893")
    assert made.status_code == 200
    upload_id = made.json()["id"]
    assert client.get(f"/api/uploads/{upload_id}").content == PNG
    row = (
        open_db()
        .execute("SELECT source, author, licence, page FROM uploads WHERE id = ?", (upload_id,))
        .fetchone()
    )
    assert tuple(row) == (
        "Pixabay",
        "Josch13",
        "Pixabay-Lizenz",
        "https://pixabay.com/photos/195893/",
    )
    notes = client.get("/api/picture-notes", params={"ids": str(upload_id)}).json()
    assert notes == [
        {
            "id": upload_id,
            "source": "Pixabay",
            "author": "Josch13",
            "licence": "Pixabay-Lizenz",
            "page": "https://pixabay.com/photos/195893/",
        }
    ]
    assert other.get(f"/api/uploads/{upload_id}").status_code == 404
    assert other.get("/api/picture-notes", params={"ids": str(upload_id)}).json() == []


def test_an_unknown_hit_is_not_fetched(monkeypatch):
    calls, _ = install(monkeypatch)
    client = user("a@example.com")
    assert client.get("/api/picture-search", params={"q": "Hund"}).status_code == 200
    before = len(calls)
    assert client.post("/api/picture-search/999").status_code == 404
    assert len(calls) == before


def test_a_download_from_another_host_is_not_stored(monkeypatch):
    calls, _ = install(monkeypatch)
    client = user("a@example.com")
    res = client.get("/api/picture-search", params={"q": "Hund"})
    assert all(hit["id"] != 8 for hit in res.json()["hits"])
    assert not any("evil.example" in url for url in calls)
    assert client.post("/api/picture-search/8").status_code == 404


def test_webformat_is_used_when_pixabay_gives_no_large_image(monkeypatch):
    small = hit(
        9, "illustration", largeImageURL=None, webformatURL="https://pixabay.com/get/9_640.jpg"
    )
    del small["largeImageURL"]
    calls, _ = install(
        monkeypatch,
        {"image_type=illustration": {"hits": [small]}, "image_type=vector": {"hits": []}},
    )
    client = user("a@example.com")
    assert client.get("/api/picture-search", params={"q": "Hund"}).status_code == 200
    assert client.post("/api/picture-search/9").status_code == 200
    assert any("pixabay.com/get/9_640.jpg" in url for url in calls)


def test_a_redirect_off_pixabay_is_refused(monkeypatch):
    from blattwerk import search

    class Answer:
        status_code = 200
        content = b"x"
        url = "https://evil.example/a.png"

        def __init__(self) -> None:
            self.headers = {"content-type": "image/png"}

    monkeypatch.setattr(search.httpx, "get", lambda *args, **kwargs: Answer())
    with pytest.raises(HTTPException) as caught:
        search.fetch("https://cdn.pixabay.com/photo/1.jpg")
    assert caught.value.status_code == 502


def test_only_pixabay_hosts_are_fetched():
    from blattwerk import search

    assert search.allowed("https://pixabay.com/api/")
    assert search.allowed("https://cdn.pixabay.com/photo/1.jpg")
    assert not search.allowed("http://cdn.pixabay.com/photo/1.jpg")
    assert not search.allowed("https://evil.example/a.png")
    assert not search.allowed("https://pixabay.com.evil.example/a.png")
    assert not search.allowed("https://notpixabay.com/a.png")


def test_a_found_picture_lands_with_its_licence_undo_and_the_print(
    monkeypatch, editor, browser, server
):
    """The picker asks the server, the block undoes, and the print shows the credit once it is on."""
    client = user("sucherin@example.com")
    page = editor(client=client)
    talked = []
    page.on("request", lambda request: talked.append(request.url))
    page.get_by_label("Bild", exact=True).click()
    dialog = page.locator("dialog.pictures")
    expect(dialog).to_be_visible()
    install(monkeypatch)
    expect(dialog.get_by_role("checkbox", name="Zeichnungen")).to_be_checked()
    dialog.get_by_label("Suchbegriff").fill("Hund")
    dialog.get_by_role("button", name="Suchen").click()
    hit_button = dialog.get_by_role("button", name="Josch13")
    expect(hit_button).to_be_visible()
    expect(hit_button).to_contain_text("Pixabay-Lizenz")
    src = hit_button.locator("img").get_attribute("src")
    assert src is not None and src.startswith("/api/picture-search/") and "pixabay" not in src
    hit_button.click()
    expect(page.locator(".block .picture img")).to_have_count(1)
    expect(page.locator(".panel")).to_contain_text("Josch13")
    expect(page.locator(".panel")).to_contain_text("Pixabay-Lizenz")
    expect(page.locator(".credits")).to_have_count(0)
    page.get_by_label("Rückgängig", exact=True).click()
    expect(page.locator(".block .picture img")).to_have_count(0)
    page.get_by_label("Wiederholen", exact=True).click()
    expect(page.locator(".block .picture img")).to_have_count(1)
    page.get_by_role("tab", name="Ansicht").click()
    page.get_by_role("group", name="Bildnachweise").get_by_role("button", name="An").click()
    expect(page.locator(".sheet.on .credits")).to_contain_text("Josch13")
    expect(page.locator(".sheet.on .credits")).to_contain_text("Pixabay-Lizenz")
    assert doc_credits(page, client) is True
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    expect(paper.locator(".credits")).to_contain_text("Josch13")
    expect(paper.locator(".credits")).to_contain_text("https://pixabay.com/photos/195893/")
    paper.context.close()
    text = pdf_text(server, client, mine)
    assert "Josch13" in text
    assert "Pixabay-Lizenz" in text
    assert not any("pixabay.com" in url for url in talked)


def doc_credits(page, client):
    from ui import doc

    return doc(page, client).get("credits")
