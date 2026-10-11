"""An id no row can have is as missing as any other (issue #339): SQLite's whole numbers have 64
bits, and a larger id in an address answered 500. Now it answers 404, and the page says `Blatt
nicht gefunden`.

The docstrings name the lines of the checklist.
"""

# The fixture `window` is imported, and the test names it as its argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_admin import admin
from test_load_fails import FAILED
from test_loading import window  # noqa: F401
from ui import sheet, user

LARGE = 99999999999999999999999
# The first number on either side that SQLite cannot hold.
ABOVE = 2**63
BELOW = -(2**63) - 1

ROUTES = {
    "save": ("PATCH", "/api/sheets/{}"),
    "duplicate": ("POST", "/api/sheets/{}/duplicate"),
    "delete": ("DELETE", "/api/sheets/{}"),
    "pdf": ("GET", "/api/sheets/{}/pdf"),
    "render": ("GET", "/api/render/{}"),
    "upload": ("GET", "/api/uploads/{}"),
    "template": ("DELETE", "/api/templates/{}"),
    "reset": ("POST", "/api/admin/users/{}/reset"),
}


def ask(client, method, path, sheet_id):
    """Asks the route for the id. A save brings a title, so only the id can be at fault."""
    body = {"title": "Neu"} if method == "PATCH" else None
    return client.request(method, path.format(sheet_id), json=body)


def test_a_sheet_id_too_large_answers_404():
    """A11: `GET /api/sheets/<id too large>` answers 404."""
    client = user()
    assert client.get(f"/api/sheets/{LARGE}").status_code == 404
    assert client.get(f"/api/sheets/{ABOVE}").status_code == 404


def test_the_page_of_a_sheet_id_too_large_says_that_the_sheet_is_not_there(window, server):
    """A11: signed in, `/blatt/<id too large>` says `Blatt nicht gefunden`, not that the sheet
    could not be loaded."""
    page, _ = window()
    page.goto(f"{server}/blatt/{LARGE}")
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
    expect(page.get_by_role("heading", name=FAILED)).to_have_count(0)
    expect(page.locator("main.editor")).to_have_count(0)


@pytest.mark.parametrize(("method", "path"), ROUTES.values(), ids=ROUTES)
def test_every_other_route_answers_404_for_an_id_too_large(method, path):
    """A12: every other route that takes an id answers 404 for one too large, not 500.

    Backend only, no browser: the page asks none of these for an id it did not get from the
    server."""
    client = admin() if "admin" in path else user()
    assert ask(client, method, path, LARGE).status_code == 404
    assert ask(client, method, path, ABOVE).status_code == 404


@pytest.mark.parametrize(("method", "path"), ROUTES.values(), ids=ROUTES)
def test_an_id_too_large_below_zero_answers_404(method, path):
    """I7: a negative id too large is as missing, on every route."""
    client = admin() if "admin" in path else user()
    assert client.get(f"/api/sheets/{BELOW}").status_code == 404
    assert ask(client, method, path, BELOW).status_code == 404
    assert ask(client, method, path, -LARGE).status_code == 404


@pytest.mark.parametrize(("method", "path"), ROUTES.values(), ids=ROUTES)
def test_an_id_that_is_no_number_stays_422(method, path):
    """I7: an id that is no number answers 422 as before."""
    client = admin() if "admin" in path else user()
    assert client.get("/api/sheets/abc").status_code == 422
    assert ask(client, method, path, "abc").status_code == 422
    assert ask(client, method, path, "1.5").status_code == 422


def test_the_largest_id_sqlite_holds_is_looked_up():
    """I7: the bound lies where SQLite's does. The last id on either side is asked for and
    missing, and a sheet's own id still finds it."""
    client = user()
    made = sheet(client)
    assert client.get(f"/api/sheets/{made['id']}").json() == made
    assert client.get(f"/api/sheets/{ABOVE - 1}").status_code == 404
    assert client.get(f"/api/sheets/{BELOW + 1}").status_code == 404


@pytest.mark.parametrize("version", [LARGE, ABOVE, BELOW], ids=["large", "above", "below"])
def test_a_version_too_large_in_a_save_answers_422(version):
    """I7: a huge `version` in a save's body answers 422, not 500, and the sheet stays."""
    client = user()
    made = sheet(client)
    body = {"doc": made["doc"], "version": version}
    assert client.patch(f"/api/sheets/{made['id']}", json=body).status_code == 422
    assert client.get(f"/api/sheets/{made['id']}").json() == made


def test_a_version_that_is_not_the_sheets_still_answers_409():
    """I7: a version SQLite holds but the sheet does not have is a save from elsewhere, as
    before."""
    client = user()
    made = sheet(client)
    body = {"doc": made["doc"], "version": ABOVE - 1}
    assert client.patch(f"/api/sheets/{made['id']}", json=body).status_code == 409
