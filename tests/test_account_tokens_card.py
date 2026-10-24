"""The Konto card for Claude: the extension, the install steps, and the page they open.

The account fixture and the helpers live in test_account_tokens.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import json
import shutil
import zipfile

import httpx
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from test_account_tokens import (
    DOCS,
    account,  # noqa: F401
    make,
)
from ui import user

from blattwerk.app import app


def test_the_extension_downloads_beside_the_key(account, server, tmp_path):
    """The card of the keys offers the Claude Desktop extension, served by the app as a file."""
    page = account(user())
    card = page.locator(".card").filter(has_text="Zugang für Claude")
    with page.expect_download() as download:
        card.get_by_role("link", name="Erweiterung für Claude Desktop herunterladen").click()
    assert download.value.suggested_filename == "blattomat.mcpb"
    path = tmp_path / "blattomat.mcpb"
    download.value.save_as(path)
    with zipfile.ZipFile(path) as bundle:
        assert json.loads(bundle.read("manifest.json"))["name"] == "blattomat"
    answer = httpx.get(f"{server}/blattomat.mcpb")
    assert answer.headers["content-type"] == "application/octet-stream"


def test_the_card_says_what_claude_is_does_sees_and_how_to_stop(account):
    page = account(user())
    card = page.locator(".card").filter(has_text="Zugang für Claude")
    for words in (
        "KI-Assistent",
        "Anthropic",
        "USA",
        "anlegen und ändern",
        "Titel",
        "Inhalte",
        "Lernwörter",
        "Bilder der Seiten",
        "entfern die Erweiterung",
        "Widerrufen",
    ):
        expect(card).to_contain_text(words)


def test_the_install_steps_open_from_the_card_in_a_new_tab(account):
    page = account(user())
    make(page, "Claude Desktop")
    with page.context.expect_page() as new:
        page.get_by_role("link", name="So installierst du die Erweiterung").click()
    tab = new.value
    tab.wait_for_load_state()
    expect(tab.get_by_role("heading", name="Dein erstes Blatt mit Claude")).to_be_visible()
    expect(tab.locator("body")).to_contain_text("Schritt 3: Die Erweiterung installieren")
    expect(tab.locator("body")).to_contain_text("blattomat.mcpb")
    expect(page.get_by_test_id("new-token")).to_be_visible()


def test_datenschutz_section_9_opens_from_the_card(account):
    page = account(user())
    make(page, "Claude Desktop")
    with page.context.expect_page() as new:
        page.get_by_role("link", name="Was an Anthropic geht: Datenschutz, Abschnitt 9").click()
    tab = new.value
    tab.wait_for_load_state()
    assert tab.url.endswith("/datenschutz#claude")
    section = tab.locator("#claude")
    expect(section).to_have_text("9. Claude (freiwillig)")
    expect(section).to_be_in_viewport()
    expect(page.get_by_test_id("new-token")).to_be_visible()


def test_the_install_page_opens_without_a_login_and_numbers_its_steps():
    response = TestClient(app).get("/anleitung/claude")
    assert response.status_code == 200
    html = response.text
    assert "viewport" in html
    assert "prefers-color-scheme: dark" in html
    assert "← Blattomat" in html
    # Schritt 3 has a paragraph between steps 3 and 4, so its list starts at 4.
    before_key_step = html[: html.index("API-Schlüssel")]
    assert before_key_step.rsplit("<ol", 1)[1].startswith(' start="4">')


def test_the_install_page_reads_the_docs_folder_from_the_env(tmp_path, monkeypatch):
    docs = tmp_path / "okf"
    shutil.copytree(DOCS, docs)
    tutorial = docs / "tutorials" / "dein-erstes-blatt-mit-claude.md"
    text = tutorial.read_text(encoding="utf-8")
    changed = text.replace("# Dein erstes Blatt mit Claude", "# Ein anderes Blatt", 1)
    tutorial.write_text(changed, encoding="utf-8")
    monkeypatch.setenv("BLATTWERK_DOCS", str(docs))
    assert "<h1>Ein anderes Blatt</h1>" in TestClient(app).get("/anleitung/claude").text
