"""Eine Aufgabe weniger keeps the other exercises (issue #903); an overtaken click is not redone (issue #902).

The docstrings name the case each test proves. The session goes by `page.context.clear_cookies()`, the
login by hand, as in test_signed_out_input.py.
"""

# The fixture `window` is imported, and each test names one as its argument.
# ruff: noqa: F811

import time

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_saves import NOTICE
from test_signed_out import expect_login, expect_sheet, login
from ui import box, maths, pick, sheet, user

WAITS_NOTICE = "Die letzte Änderung an „m“ ist noch nicht gespeichert. Melde dich neu an, dann wird sie gespeichert."


def block_of(client, sheet_id):
    """The maths block's props on the server's copy of the sheet."""
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"][0]["props"]


def exercises_of(client, sheet_id):
    return block_of(client, sheet_id)["exercises"]


def wait_for(check):
    """Polls the check until it holds, for up to 5 s: the editor saves a change 1.1 s after it."""
    for _ in range(50):
        if check():
            return
        time.sleep(0.1)


def test_903_eine_aufgabe_weniger_drops_the_last_exercise_and_keeps_the_others(editor):
    """#903: "Eine Aufgabe weniger" drops the last exercise; the others stay as they were, in order."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=8, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    old = exercises_of(client, sheet_id)
    assert len(old) == 8
    pick(page, "m")
    page.get_by_label("Eine Aufgabe weniger").click()
    wait_for(lambda: block_of(client, sheet_id)["count"] == 7)
    assert exercises_of(client, sheet_id) == old[:-1]


def test_903_two_quick_weniger_clicks_drop_the_last_two_in_order(editor):
    """#903: two quick "weniger" clicks, the first answer held: the last two go, the others stay in order."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=8, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    old = exercises_of(client, sheet_id)
    held = []

    def hold(route):
        # The first answer waits until the second click is sent; then both go on.
        if held:
            held.pop().continue_()
            route.continue_()
        else:
            held.append(route)

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe weniger").click()
    page.get_by_label("Eine Aufgabe weniger").click()
    wait_for(lambda: block_of(client, sheet_id)["count"] == 6)
    assert exercises_of(client, sheet_id) == old[:-2]


def test_903_one_undo_brings_the_dropped_exercise_back(editor):
    """#903: Ctrl+Z after "Eine Aufgabe weniger" brings the exercises back as they were."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=8, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    old = exercises_of(client, sheet_id)
    pick(page, "m")
    page.get_by_label("Eine Aufgabe weniger").click()
    wait_for(lambda: block_of(client, sheet_id)["count"] == 7)
    pick(page, "m")
    page.keyboard.press("Control+z")
    wait_for(lambda: block_of(client, sheet_id)["count"] == 8)
    assert exercises_of(client, sheet_id) == old


def maths_sheet(window, server, count):
    """A sheet with one maths block of `count` Aufgaben, opened and picked. Gives the page, the client and the sheet id."""
    page, client = window()
    props = maths(client, format="row", ops=["+"], max=20, count=count)
    made = sheet(client, [box("m", "maths", props, y=20, h=60)], title="m")
    page.goto(f"{server}/blatt/{made['id']}")
    expect_sheet(page)
    pick(page, "m")
    return page, client, made["id"]


def test_903_weniger_after_the_session_ran_out_keeps_the_others_after_the_login(window, server):
    """#903: "Eine Aufgabe weniger" with the session run out: after the sign-in the other exercises stay."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    old = exercises_of(client, sheet_id)
    page.context.clear_cookies()
    page.get_by_label("Eine Aufgabe weniger").click()
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS_NOTICE)
    login(page, server, client)
    expect_sheet(page)
    wait_for(lambda: block_of(client, sheet_id)["count"] == 13)
    assert exercises_of(client, sheet_id) == old[:-1]


def test_902_an_overtaken_click_that_meets_a_run_out_session_is_not_redone_after_the_login(
    window, server
):
    """#902: "mehr" fails, "weniger" lands, then the retry of "mehr" meets a run-out session: the count stays at weniger."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    page.route("**/api/maths", lambda route: route.abort())
    page.get_by_label("Eine Aufgabe mehr").click()
    again = page.get_by_role("button", name="Erneut versuchen")
    expect(again).to_be_visible()
    page.unroute("**/api/maths")
    calls = []

    def answer(route):
        # The first request, "weniger", lands; the retry of "mehr" finds the session run out.
        calls.append(1)
        if len(calls) == 1:
            route.continue_()
        else:
            route.fulfill(status=401, body="{}")

    page.route("**/api/maths", answer)
    page.get_by_label("Eine Aufgabe weniger").click()
    wait_for(lambda: block_of(client, sheet_id)["count"] == 13)
    again.click()
    expect_login(page, address)
    login(page, server, client)
    expect_sheet(page)
    page.wait_for_timeout(1500)
    assert block_of(client, sheet_id)["count"] == 13
