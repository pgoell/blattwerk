"""Text help sends only the selected text, and only when Pascal has set an address.

The button, the preview and the page copies are in the browser tests below. The model is not
here: a local stub answers, and with no address the route refuses.
"""

import io
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

import httpx
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import TEXT, at, box, maths, pick, user

from blattwerk.app import app

NOTE = "Ein Modell hat diesen Text geschrieben. Lies ihn, bevor du ihn druckst."
OLD = "Der Hund ist gross."
SECRET = "Geheimnis der Klasse"
SIMPLER = "Der Hund ist klein."


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        cast("Provider", self.server).calls.append(
            ({k.lower(): v for k, v in self.headers.items()}, raw)
        )
        body = json.loads(raw)
        if body.get("kind") == "levels":
            out = {"texts": ["Niveau eins", "Niveau zwei", "Niveau drei"], "model": "stub"}
        else:
            out = {"text": SIMPLER, "model": "stub"}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


class Provider(ThreadingHTTPServer):
    calls: list[tuple[dict[str, str], bytes]]

    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.calls = []


def start_provider():
    server = Provider()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def logged_in(email="lehrerin@example.com"):
    return user(email)


def test_help_is_missing_until_a_provider_is_set(monkeypatch):
    monkeypatch.delenv("BLATTWERK_TEXT_HELP_URL", raising=False)
    client = logged_in()
    res = client.post("/api/text/help", json={"text": OLD, "kind": "simpler"})
    assert res.status_code == 503
    assert res.json()["detail"] == "Die Texthilfe ist nicht eingerichtet."


def test_logged_out_cannot_ask():
    client = TestClient(app, base_url="https://testserver")
    res = client.post("/api/text/help", json={"text": OLD, "kind": "simpler"})
    assert res.status_code == 401


def test_a_file_address_is_not_opened(monkeypatch):
    monkeypatch.setenv("BLATTWERK_TEXT_HELP_URL", "file:///etc/passwd")
    client = logged_in()
    res = client.post("/api/text/help", json={"text": OLD, "kind": "simpler"})
    assert res.status_code == 503
    assert res.json()["detail"] == "Die Texthilfe ist nicht eingerichtet."


def test_an_extra_field_is_refused_and_not_forwarded(monkeypatch):
    server, thread = start_provider()
    monkeypatch.setenv("BLATTWERK_TEXT_HELP_URL", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        client = logged_in()
        res = client.post(
            "/api/text/help",
            json={"text": OLD, "kind": "simpler", "email": "lehrerin@example.com"},
        )
        assert res.status_code == 422
        assert server.calls == []
    finally:
        server.shutdown()
        thread.join()


def test_the_provider_is_sent_only_the_text_and_the_kind(monkeypatch):
    server, thread = start_provider()
    monkeypatch.setenv("BLATTWERK_TEXT_HELP_URL", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        client = logged_in("lehrerin@example.com")
        res = client.post("/api/text/help", json={"text": OLD, "kind": "shorter"})
        assert res.status_code == 200
        assert res.json() == {"text": SIMPLER}
        headers, raw = server.calls[0]
        assert json.loads(raw) == {"text": OLD, "kind": "shorter"}
        assert "cookie" not in headers
        assert "authorization" not in headers
        sent = raw.decode()
        assert "lehrerin@example.com" not in sent
        assert SECRET not in sent
        assert "model" not in res.json()
    finally:
        server.shutdown()
        thread.join()


def test_three_levels_come_back_as_three_texts(monkeypatch):
    server, thread = start_provider()
    monkeypatch.setenv("BLATTWERK_TEXT_HELP_URL", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        client = logged_in()
        res = client.post("/api/text/help", json={"text": OLD, "kind": "levels"})
        assert res.status_code == 200
        assert res.json() == {"texts": ["Niveau eins", "Niveau zwei", "Niveau drei"]}
        assert json.loads(server.calls[0][1]) == {"text": OLD, "kind": "levels"}
    finally:
        server.shutdown()
        thread.join()


def test_a_provider_that_does_not_answer_says_so(monkeypatch):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    monkeypatch.setenv("BLATTWERK_TEXT_HELP_URL", f"http://127.0.0.1:{port}")
    client = logged_in()
    res = client.post("/api/text/help", json={"text": OLD, "kind": "simpler"})
    assert res.status_code == 502
    assert res.json()["detail"] == "Die Texthilfe hat nicht geantwortet."


def test_maths_does_not_call_the_text_provider(monkeypatch):
    server, thread = start_provider()
    monkeypatch.setenv("BLATTWERK_TEXT_HELP_URL", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        client = logged_in()
        res = client.post("/api/maths", json={"ops": ["+"], "max": 20, "count": 3, "seed": 7})
        assert res.status_code == 200
        assert len(res.json()["exercises"]) == 3
        assert server.calls == []
    finally:
        server.shutdown()
        thread.join()


def test_simpler_stays_off_the_sheet_until_she_takes_it_and_undo_is_one_step(
    editor, server, monkeypatch
):
    provider, thread = start_provider()
    monkeypatch.setenv("BLATTWERK_TEXT_HELP_URL", f"http://127.0.0.1:{provider.server_address[1]}")
    try:
        client = logged_in("lehrerin@example.com")
        page = editor(
            box("a", "text", {**TEXT, "text": OLD}),
            box("b", "text", {**TEXT, "text": SECRET}, z=2),
            client=client,
        )
        pick(page, "a")
        page.get_by_role("button", name="Text anpassen", exact=True).click()
        dialog = page.locator("dialog.texthelp")
        dialog.get_by_role("button", name="Einfacher", exact=True).click()
        expect(dialog.get_by_role("heading", name="Bisher")).to_be_visible()
        expect(dialog.get_by_role("heading", name="Neu")).to_be_visible()
        expect(dialog.get_by_text(OLD)).to_be_visible()
        expect(dialog.get_by_text(SIMPLER)).to_be_visible()
        expect(dialog.get_by_text(NOTE)).to_be_visible()
        expect(at(page, "a").get_by_text(OLD)).to_be_visible()
        expect(at(page, "a").get_by_text(SIMPLER)).to_have_count(0)
        expect(at(page, "b").get_by_text(SECRET)).to_be_visible()
        headers, raw = provider.calls[0]
        assert json.loads(raw) == {"text": OLD, "kind": "simpler"}
        assert "cookie" not in headers
        assert "authorization" not in headers
        assert "lehrerin@example.com" not in raw.decode()
        assert SECRET not in raw.decode()
        assert len(provider.calls) == 1

        dialog.get_by_role("button", name="Verwerfen", exact=True).click()
        expect(dialog).to_have_count(0)
        expect(at(page, "a").get_by_text(OLD)).to_be_visible()
        expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()

        page.get_by_role("button", name="Text anpassen", exact=True).click()
        dialog = page.locator("dialog.texthelp")
        dialog.get_by_role("button", name="Einfacher", exact=True).click()
        expect(dialog.get_by_text(SIMPLER)).to_be_visible()
        dialog.get_by_role("button", name="Bearbeiten", exact=True).click()
        dialog.locator("textarea").fill("Der Hund ist klein und ruhig.")
        dialog.get_by_role("button", name="Übernehmen", exact=True).click()
        expect(dialog).to_have_count(0)
        expect(at(page, "a").get_by_text("Der Hund ist klein und ruhig.")).to_be_visible()
        expect(at(page, "b").get_by_text(SECRET)).to_be_visible()

        page.get_by_label("Rückgängig", exact=True).click()
        expect(at(page, "a").get_by_text(OLD)).to_be_visible()
        expect(at(page, "a").get_by_text("ruhig")).to_have_count(0)
        page.get_by_label("Wiederholen", exact=True).click()
        expect(at(page, "a").get_by_text("Der Hund ist klein und ruhig.")).to_be_visible()

        expect(page.locator("header [role=status]")).to_have_text("Gespeichert")
        sheet_id = page.url.rstrip("/").split("/")[-1]
        res = httpx.get(
            f"{server}/api/sheets/{sheet_id}/pdf",
            headers={"cookie": f"session={client.cookies['session']}"},
            timeout=60,
        )
        assert res.status_code == 200
        printed = " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(res.content)).pages)
        assert "ruhig" in printed
        assert "gross" not in printed
    finally:
        provider.shutdown()
        thread.join()


def test_three_levels_copy_the_page_with_the_symbol_she_picks_and_one_undo(editor, monkeypatch):
    provider, thread = start_provider()
    monkeypatch.setenv("BLATTWERK_TEXT_HELP_URL", f"http://127.0.0.1:{provider.server_address[1]}")
    try:
        page = editor(box("a", "text", {**TEXT, "text": OLD}), client=logged_in())
        pick(page, "a")
        page.get_by_role("button", name="Text anpassen", exact=True).click()
        dialog = page.locator("dialog.texthelp")
        dialog.get_by_role("button", name="In drei Niveaus", exact=True).click()
        expect(dialog.get_by_text("Niveau eins")).to_be_visible()
        expect(dialog.get_by_text("Niveau zwei")).to_be_visible()
        expect(dialog.get_by_text("Niveau drei")).to_be_visible()
        expect(dialog.get_by_text(NOTE)).to_be_visible()
        expect(at(page, "a").get_by_text(OLD)).to_be_visible()
        expect(page.locator(".desk .sheet")).to_have_count(1)
        assert json.loads(provider.calls[0][1]) == {"text": OLD, "kind": "levels"}

        dialog.get_by_label("Zeichen").select_option("270F")
        dialog.get_by_role("button", name="Übernehmen", exact=True).click()
        expect(dialog).to_have_count(0)
        sheets = page.locator(".desk .sheet")
        expect(sheets).to_have_count(4)
        expect(page.locator(".desk .sheet.on").get_by_text("Niveau eins")).to_be_visible()
        expect(page.locator(".desk .sheet.on img[src='/openmoji/270F.svg']")).to_have_count(1)
        expect(sheets.nth(2).get_by_text("Niveau zwei")).to_be_visible()
        expect(sheets.nth(2).locator("img[src='/openmoji/270F.svg']")).to_have_count(2)
        expect(sheets.nth(3).get_by_text("Niveau drei")).to_be_visible()
        expect(sheets.nth(3).locator("img[src='/openmoji/270F.svg']")).to_have_count(3)
        expect(at(page, "a").get_by_text(OLD)).to_be_visible()
        expect(sheets.nth(0).locator("img[src='/openmoji/270F.svg']")).to_have_count(0)

        page.get_by_label("Rückgängig", exact=True).click()
        expect(page.locator(".desk .sheet")).to_have_count(1)
        expect(at(page, "a").get_by_text(OLD)).to_be_visible()
        expect(page.locator(".desk img[src='/openmoji/270F.svg']")).to_have_count(0)
    finally:
        provider.shutdown()
        thread.join()


def test_a_maths_block_has_no_text_help(editor):
    client = logged_in()
    page = editor(box("m", "maths", maths(client)), client=client)
    pick(page, "m")
    expect(page.get_by_role("button", name="Text anpassen", exact=True)).to_have_count(0)
