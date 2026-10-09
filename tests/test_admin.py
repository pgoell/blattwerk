import os
import shutil

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from ui import PASSWORD, user

from blattwerk import auth, db
from blattwerk.app import app

# The real one: a test that swaps `auth.shutil.rmtree` swaps it for the whole process.
RMTREE = shutil.rmtree


@pytest.fixture
def admin_page(browser, server):
    """Opens /admin for the given client and gives its page."""
    contexts = []

    def start(client):
        # The alert shows local time: Berlin is an hour ahead of the database's UTC in winter.
        context = browser.new_context(timezone_id="Europe/Berlin")
        contexts.append(context)
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        context.add_cookies(
            [{"name": "session", "value": client.cookies["session"], "url": server}]
        )
        page = context.new_page()
        page.goto(f"{server}/admin")
        return page

    yield start
    for context in contexts:
        context.close()


def admin():
    client = TestClient(app, base_url="https://testserver")
    token = auth.new_link(db.open_db(), admin=True)
    body = {"token": token, "email": "admin@example.com", "password": PASSWORD}
    assert client.post("/api/signup", json=body).status_code == 200
    return client


def stuck(path, onexc):
    """Stands in for `shutil.rmtree` on a folder that will not go."""
    onexc(os.rmdir, str(path), PermissionError(13, "Permission denied", str(path)))


@pytest.fixture
def leftover(monkeypatch):
    """A deleted account whose folder would not go. Gives the folder as the alert names it."""
    client = user("weg@example.com")
    client.post("/api/feedback", data={"text": "x"})
    name = f"users/{client.get('/api/me').json()['id']}"
    monkeypatch.setattr(auth, "DELETE_WAIT", 0)
    monkeypatch.setattr(auth.shutil, "rmtree", stuck)
    assert client.delete("/api/me").status_code == 200
    con = db.open_db()
    con.execute("UPDATE leftovers SET since = '2026-01-05 08:30:00'")
    con.close()
    return name


def test_admin_sees_the_folder_since_when_and_the_error(admin_page, leftover):
    page = admin_page(admin())
    alert = page.get_by_role("alert")
    expect(alert).to_contain_text(f"{leftover}, seit 05.01.2026, 09:30: PermissionError")
    expect(alert).to_contain_text(str(db.DATA_DIR / leftover))
    expect(alert).not_to_contain_text("weg@example.com")


def test_alert_goes_once_the_folder_is_removed_by_hand(admin_page, leftover):
    page = admin_page(admin())
    expect(page.get_by_role("alert")).to_be_visible()
    RMTREE(db.DATA_DIR / leftover)
    page.reload()
    # The accounts come with the same load as the alert would.
    expect(page.get_by_text("admin@example.com (Admin)")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)


def test_admin_with_no_left_over_folder_sees_no_alert(admin_page):
    page = admin_page(admin())
    expect(page.get_by_text("admin@example.com (Admin)")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)


def test_non_admin_sees_no_alert_and_no_admin_page(admin_page, leftover):
    page = admin_page(user())
    expect(page.get_by_role("heading", name="Seite nicht gefunden")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(page.get_by_text(leftover)).to_have_count(0)
