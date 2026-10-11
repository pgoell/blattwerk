"""A form sent with no connection, or to a server at fault, says so, keeps what was entered and
goes with the next press: the login, the invitation, the new password, the feedback, the photos.

The cookie of a login is Secure and this server speaks http, so no test here looks past the
server's answer for it.

The docstrings name the lines of the checklist.
"""

# The fixture `window` is imported, and each test names it as its argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_offline_editor import HOW, WHY, broken
from test_signed_out import TYPED, photographed, written
from ui import PASSWORD

from blattwerk import auth, db

NEW = "neu-und-geheim"


def press(page, name, path, server):
    """Presses the form's button. Gives the status of the server's answer."""
    with page.expect_response(f"{server}/api{path}") as got:
        page.get_by_role("button", name=name, exact=True).click()
    return got.value.status


@pytest.mark.parametrize("how", HOW)
def test_a_login_that_reaches_no_server_blames_no_password_and_works_with_the_next_press(
    window, server, how
):
    """A22"""
    page, client = window(signed=False)
    email = client.get("/api/me").json()["email"]
    page.goto(server)
    page.get_by_label("E-Mail").fill(email)
    page.get_by_label("Passwort").fill(PASSWORD)
    mend = broken(page, how, "/login$")
    page.get_by_role("button", name="Anmelden").click()
    said = page.get_by_role("status")
    expect(said).to_have_text(f"Die Anmeldung hat nicht geklappt. {WHY[how]}")
    expect(page.get_by_label("E-Mail")).to_have_value(email)
    expect(page.get_by_label("Passwort")).to_have_value(PASSWORD)
    mend()
    assert press(page, "Anmelden", "/login", server) == 200
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible()


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("invite", [True, False], ids=["invitation", "new password"])
def test_a_link_that_reaches_no_server_is_not_called_dead_and_works_with_the_next_press(
    window, server, how, invite
):
    """A22"""
    page, client = window(signed=False)
    me = client.get("/api/me").json()
    token = auth.new_link(db.open_db(), None if invite else me["id"])
    page.goto(f"{server}/{'einladung' if invite else 'passwort'}/{token}")
    if invite:
        page.get_by_label("E-Mail").fill("neu@example.com")
    page.get_by_label("Passwort").fill(NEW)
    name, path, what = (
        ("Konto anlegen", "/signup", "Das Konto konnte nicht angelegt werden.")
        if invite
        else ("Speichern", "/reset", "Das Passwort konnte nicht gespeichert werden.")
    )
    mend = broken(page, how, f"{path}$")
    page.get_by_role("button", name=name, exact=True).click()
    expect(page.get_by_role("status")).to_have_text(f"{what} {WHY[how]}")
    if invite:
        expect(page.get_by_label("E-Mail")).to_have_value("neu@example.com")
    expect(page.get_by_label("Passwort")).to_have_value(NEW)
    mend()
    assert press(page, name, path, server) == 200
    expect(page).to_have_url(f"{server}/")


def test_a_dead_link_is_still_called_dead(window, server):
    """A22: the words of the form's own refusals stay."""
    page, _ = window(signed=False)
    page.goto(f"{server}/passwort/nichts")
    page.get_by_label("Passwort").fill(NEW)
    assert press(page, "Speichern", "/reset", server) == 404
    expect(page.get_by_role("status")).to_have_text(
        "Der Link gilt nicht mehr. Bitte frag nach einem neuen."
    )


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("form", ["feedback", "photos"])
def test_feedback_that_reaches_no_server_says_so_stays_and_goes_with_the_next_press(
    window, server, data_dir, how, form
):
    """A24"""
    page, _ = window()
    if form == "feedback":
        page.goto(server)
        expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible(timeout=10000)
        written(page)
        within, text = page.locator("dialog.feedback"), page.locator("dialog.feedback textarea")
        what, thanks = "Dein Feedback ist", "Danke! Ist angekommen."
    else:
        page.goto(f"{server}/feedback/fotos")
        photographed(page)
        within, text = page.locator("main"), page.get_by_label("Was gefällt dir daran?")
        what = "Die Fotos sind"
        thanks = "Danke! Ist angekommen. Du kannst gleich das nächste schicken."
    send = within.get_by_role("button", name="Abschicken")
    said = within.get_by_role("status")
    mend = broken(page, how, "/feedback$")
    send.click()
    expect(said).to_have_text(f"Das hat nicht geklappt. {what} noch da, versuch es gleich nochmal.")
    expect(text).to_have_value(TYPED)
    expect(within.locator("figure img")).to_have_count(1)
    mend()
    with page.expect_response(f"{server}/api/feedback") as got:
        send.click()
    assert got.value.status == 200
    expect(said).to_have_text(thanks, timeout=5000)
    assert len(list(data_dir.glob("users/*/feedback/*"))) == 1
