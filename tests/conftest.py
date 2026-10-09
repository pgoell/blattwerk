import json
import os

import pytest
from argon2 import PasswordHasher
from playwright.sync_api import expect, sync_playwright
from ui import serving, sheet, user

from blattwerk import auth, db

expect.set_options(timeout=2000)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    """With SHARD=i/n, keeps every n-th test from the i-th on: CI runs the shards side by side.

    By place in the collection, so the slow files spread over all shards. Each xdist worker
    collects the same list and reads the same variable, so all agree.
    """
    shard = os.environ.get("SHARD")
    if not shard:
        return
    i, n = map(int, shard.split("/"))
    assert 1 <= i <= n, f"SHARD={shard}: want i/n with 1 <= i <= n"
    config.hook.pytest_deselected(items=[t for k, t in enumerate(items) if k % n != i - 1])
    items[:] = items[i - 1 :: n]


@pytest.fixture(scope="session", autouse=True)
def cheap(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        # The real hash takes 64 MiB and a fifth of a second, and every test signs a user up.
        patch.setattr(auth, "hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
        # Between two tests too, no request may reach the data folder of the checkout.
        patch.setattr(db, "DATA_DIR", tmp_path_factory.mktemp("between"))
        yield


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture(scope="session")
def server():
    """The app on a real port, for Chromium to call as it does in production.

    One for the whole run: the app looks up the data folder with each request, so each test still
    has its own.
    """
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
    contexts = []

    def start(*blocks, client=None, more=(), pages=(), theme=None, touch=False):
        """`more` holds the blocks of a second page. With `touch` the window takes fingers too.

        `pages` holds the pages after the first, each a whole page: its blocks and, where it has
        them, its own guides, grid and landscape. `theme` is the one picked on the account page:
        "" opens the panel Seiten, none is Blattform, which starts with that panel shut.
        """
        context = browser.new_context(viewport={"width": 1400, "height": 1000}, has_touch=touch)
        contexts.append(context)
        # A copy stamps the system clipboard and a paste reads it; headless Chromium asks no one.
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        # The tour would open on the first visit and lie over the sheet.
        context.add_init_script("localStorage.setItem('tour', '1')")
        if theme is not None:
            context.add_init_script(f"localStorage.setItem('theme', {json.dumps(theme)})")
        client = client or user()
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        context.add_cookies(
            [{"name": "session", "value": client.cookies["session"], "url": server}]
        )
        page = context.new_page()
        rest = [*([more] if more else []), *pages]
        page.goto(f"{server}/blatt/{sheet(client, blocks, *rest)['id']}")
        # The editor listens for keys once the sheet has loaded.
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
        # A thumbnail draws blocks too, with no name.
        count = len(blocks) + len(more) + sum(len(p["blocks"]) for p in pages)
        expect(page.locator(".block[data-id]")).to_have_count(count)
        return page

    yield start
    # Leaving the editor saves. A save that comes in late finds no such session in the next
    # test's data and changes nothing.
    for context in contexts:
        context.close()
