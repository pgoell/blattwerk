import pytest
from playwright.sync_api import expect, sync_playwright
from ui import serving, sheet, user

from blattwerk import db

expect.set_options(timeout=2000)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def server():
    """The app on a real port, for Chromium to call as it does in production."""
    with serving() as url:
        yield url


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def editor(browser, server):
    """Opens the editor on a sheet of the given blocks, as a new user, and gives its page."""
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    # The tour would open on the first visit and lie over the sheet.
    context.add_init_script("localStorage.setItem('tour', '1')")

    def start(*blocks, client=None, more=()):
        """`more` holds the blocks of a second page."""
        client = client or user()
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        context.add_cookies(
            [{"name": "session", "value": client.cookies["session"], "url": server}]
        )
        page = context.new_page()
        page.goto(f"{server}/blatt/{sheet(client, blocks, *([more] if more else []))['id']}")
        # The editor listens for keys once the sheet has loaded.
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
        expect(page.locator(".block")).to_have_count(len(blocks) + len(more))
        return page

    yield start
    # Before the server stops: leaving the editor saves.
    context.close()
