"""Changes made with the session run out: a maths click and typed words are kept and saved after the
sign-in (issues #810 and #813). The session goes by `page.context.clear_cookies()`, the login by hand,
as in test_signed_out.py.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_saves import NOTICE, STATUS
from test_signed_out import WATCH, expect_login, expect_sheet, login
from ui import box, maths, pick, sheet

WAITS = "Die letzte Änderung an „m“ ist noch nicht gespeichert. Melde dich neu an, dann wird sie gespeichert."


def count_of(client, sheet_id):
    """The Aufgaben count of the maths block on the server's copy of the sheet."""
    doc = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    return doc["pages"][0]["blocks"][0]["props"]["count"]


def maths_sheet(window, server, count):
    """A sheet with one maths block of `count` Aufgaben, opened and picked. Gives the page, the client and the sheet id."""
    page, client = window()
    props = maths(client, format="row", ops=["+"], max=20, count=count)
    made = sheet(client, [box("m", "maths", props, y=20, h=60)], title="m")
    page.goto(f"{server}/blatt/{made['id']}")
    expect_sheet(page)
    pick(page, "m")
    return page, client, made["id"]


def test_a8_eine_aufgabe_weniger_after_the_session_ran_out_is_kept_and_saved_after_the_sign_in(
    window, server
):
    """A8: the login shows with the red bar, and after the sign-in the block has one task less, saved."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    page.evaluate(WATCH)
    page.context.clear_cookies()
    page.get_by_label("Eine Aufgabe weniger").click()
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    login(page, server, client)
    expect_sheet(page)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    # The redo comes after the login, from the server's maths, and its save follows it.
    for _ in range(50):
        if count_of(client, sheet_id) == 13:
            break
        page.wait_for_timeout(100)
    assert count_of(client, sheet_id) == 13
