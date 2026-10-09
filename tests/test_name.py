"""The product's name, Blattomat: in the browser, on every page, in the docs and in what is sent."""

import re
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import expect
from ui import STATIC

from blattwerk import auth, db
from blattwerk.app import app

REPO = Path(__file__).parent.parent
# Repo, package and host keep the old name. README and CLAUDE.md say so, once each.
KEPT = (
    "The repo, the Python package and the host `blattwerk.pgoell.com` "
    "still carry the old name `blattwerk`."
)
TEXTS = {".html", ".js", ".css", ".webmanifest", ".svg", ".txt", ".json"}


def test_title_and_home_screen_name(browser, server):
    page = browser.new_page()
    page.goto(server)
    expect(page).to_have_title("Blattomat")
    expect(page.locator("meta[name=apple-mobile-web-app-title]")).to_have_attribute(
        "content", "Blattomat"
    )
    manifest = page.request.get(f"{server}/manifest.webmanifest").json()
    assert manifest["name"] == manifest["short_name"] == "Blattomat"
    page.close()


def test_pages_say_blattomat(browser, server, editor):
    page = browser.new_page()
    page.goto(server)
    expect(page.locator(".auth .logo")).to_have_text("Blattomat")
    page.goto(f"{server}/einladung/{auth.new_link(db.open_db())}")
    expect(page.get_by_role("heading", name="Willkommen bei Blattomat")).to_be_visible()
    page.goto(f"{server}/ueber")
    expect(page.get_by_role("heading", name="Über Blattomat")).to_be_visible()
    page.close()

    page = editor()
    # The editor has its own header; the wordmark in it leads back to the list.
    mark = page.get_by_title("Meine Blätter").locator(".logo")
    expect(mark).to_be_visible()
    expect(mark).to_have_text("Blattomat")
    page.get_by_role("button", name="Rundgang").click()
    expect(page.locator(".tour h2")).to_have_text("Willkommen bei Blattomat")


def test_docs_name_the_product():
    named = [REPO / "README.md", REPO / ".claude/CLAUDE.md", REPO / "docs/spec-v0.md"]
    for file in named:
        assert "Blattomat" in file.read_text(), file
    for file in {*named, REPO / "NOTICE", *(REPO / "docs").rglob("*.md")}:
        assert "Blattwerk" not in file.read_text(), file
    for file in named[:2]:
        assert file.read_text().count(KEPT) == 1, file


def test_no_old_name_in_what_users_get():
    old = re.compile("blattwerk", re.IGNORECASE)
    for file in STATIC.rglob("*"):
        if file.suffix in TEXTS:
            assert not old.search(file.read_text()), file
    client = TestClient(app)
    for path in ("/", "/impressum", "/datenschutz", "/manifest.webmanifest"):
        assert not old.search(client.get(path).text), path
