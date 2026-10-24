"""A picture or a PDF that finds the session gone, and whose change is kept.

The helpers live in test_signed_out.py.
"""

# The fixture is imported, and each test names it as its argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_loading import READY, window  # noqa: F401
from test_saves import LEFT, NOTICE, answer, nudge, record, run, start, unsaved, x_of  # noqa: F401
from test_signed_out import (
    expect_login,
    expect_sheet,
    gone,
    login,
)
from test_stale import FRAMES, GO, STATUS, TURNS, named
from ui import at, drop, png, user

WAITS = unsaved("a", "Melde dich neu an, dann wird sie gespeichert.")


def back(run, moved, saved=True):
    """After the login A shows as it was left, and the change is saved."""
    page = run.page
    page.clock.resume()
    login(page, run.server, run.client)
    expect_sheet(page)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert x_of(run, "a") == (16 if saved else 15)
    assert record(page, run.ids["a"]) is None


@pytest.mark.parametrize("how", ["drop", "button"])
def test_a_picture_that_finds_the_session_gone_brings_the_login_and_the_change_is_saved_after_it(
    run, how
):
    """A8: no dialog says that the picture could not be uploaded."""
    moved, asked = gone(run)
    page = run.page
    address = f"{run.server}/blatt/{run.ids['a']}"
    with page.expect_response(f"{run.server}/api/uploads") as got:
        if how == "drop":
            held = page.locator('.sheet[data-page="0"]').bounding_box()
            point = held["x"] + held["width"] / 2, held["y"] + held["height"] / 2
            drop(page, *point, ("bild.png", "image/png", png()))
        else:
            file = {"name": "bild.png", "mimeType": "image/png", "buffer": png()}
            page.locator("input[type=file]").set_input_files(file)
    assert got.value.status == 401
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16
    back(run, moved)
    assert asked == []


@pytest.mark.parametrize("change", [True, False], ids=["unsaved", "saved"])
def test_a_pdf_that_finds_the_session_gone_brings_the_login_and_stays_in_the_app(run, change):
    """A9: nothing goes to the PDF's address, and an unsaved change is saved after the login."""
    moved, asked = gone(run, change)
    page = run.page
    address = f"{run.server}/blatt/{run.ids['a']}"
    left = []
    page.on("request", lambda r: "/pdf" in r.url and left.append(r.url))
    page.on("download", lambda download: left.append(download))
    page.on("framenavigated", lambda frame: left.append(frame.url))
    with page.expect_response(f"{run.server}/api/me") as got:
        page.get_by_role("button", name="PDF", exact=True).click()
    assert got.value.status == 401
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text([WAITS] if change else [])
    page.evaluate(TURNS)
    assert left == []
    back(run, moved, saved=change)
    assert left == []
    assert asked == []


def test_one_teachers_kept_change_never_goes_to_the_teacher_who_signs_in_at_that_login(run):
    """A10: B signs in at the login A's save brought, on A's sheet. B sees and saves nothing of
    A's, and A gets the change back."""
    moved, _ = gone(run)
    page, gate, a = run.page, run.gates["a"], run.ids["a"]
    address = f"{run.server}/blatt/{a}"
    with page.expect_response(gate.answers("PATCH")) as turned_down:
        page.clock.run_for(2000)
    assert turned_down.value.status == 401
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    kept = record(page, a)
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    page.clock.resume()
    other = user()
    d = named(other, "d")
    asked = []
    page.on("request", lambda r: r.url.endswith(f"/api/sheets/{a}") and asked.append(r.method))
    login(page, run.server, other)
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()

    def untouched():
        expect(page.locator(".notice, .clash")).to_have_count(0)
        page.evaluate(FRAMES)
        # The address asks for the sheet once, and is told that it is not there. No save goes.
        assert asked == ["GET"]
        assert len(run.sent) == 1
        assert record(page, a) == kept
        assert x_of(run, "a") == 15

    untouched()
    # A sheet of B's own shows as B left it.
    page.evaluate(GO, f"/blatt/{d}")
    expect_sheet(page)
    expect(at(page, "d")).to_contain_text("Blatt D")
    expect(at(page, "a")).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    untouched()
    # B's session runs out, and A signs in on A's sheet.
    page.context.clear_cookies()
    page.evaluate(GO, address)
    expect_login(page, address)
    back(run, moved)
