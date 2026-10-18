"""Eine Aufgabe weniger keeps the other exercises (issue #903); an overtaken click is not redone (issue #902).

The docstrings name the case each test proves. The session goes by `page.context.clear_cookies()`, the
login by hand, as in test_signed_out_input.py. Plus and minus up to 100: for those the server draws a new
set for every count, so a test that keeps the old exercises fails where the block takes the server's.
"""

# The fixture `window` is imported, and each test names one as its argument.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_saves import NOTICE
from test_signed_out import expect_login, expect_sheet, login
from ui import box, maths, pick, sheet, user

WAITS_NOTICE = "Die letzte Änderung an „m“ ist noch nicht gespeichert. Melde dich neu an, dann wird sie gespeichert."
LIMITS = {"ops": ["+", "-"], "max": 100, "format": "row"}
TASKS = '.block[data-id="m"] .maths > div'


def block_of(client, sheet_id):
    """The maths block's props on the server's copy of the sheet."""
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"][0]["props"]


def pairs(exercises):
    return [(e["op"], e["a"], e["b"]) for e in exercises]


def wait_saved(page, client, sheet_id, check):
    """Waits up to 5 s for the server's copy to pass the check: the editor saves a change 1.1 s after it, 2 s for a teacher."""
    for _ in range(50):
        if check(block_of(client, sheet_id)):
            break
        page.wait_for_timeout(100)
    return block_of(client, sheet_id)


def fewer_sheet(editor, count=8, **more):
    client = user()
    limits = {**LIMITS, **more}
    page = editor(
        box("m", "maths", maths(client, count=count, columns=3, size=14, **limits), y=20, h=60),
        client=client,
    )
    sheet_id = page.url.rsplit("/", 1)[1]
    pick(page, "m")
    return page, client, sheet_id, block_of(client, sheet_id)["exercises"]


def test_903_eine_aufgabe_weniger_drops_the_last_exercise_and_keeps_the_others(editor):
    """#903: "Eine Aufgabe weniger" drops the last exercise; the others stay as they were, in order."""
    page, client, sheet_id, old = fewer_sheet(editor)
    assert len(old) == 8
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(page.locator(TASKS)).to_have_count(7)
    got = wait_saved(page, client, sheet_id, lambda p: p["count"] == 7)
    assert pairs(got["exercises"]) == pairs(old[:-1])


def test_903_weniger_on_families_drops_the_last_family_whole(editor):
    """#903, review: with Tauschaufgaben the count is that of the families. "weniger" drops the last
    family whole, its two exercises, and keeps the others as they were."""
    page, client, sheet_id, old = fewer_sheet(editor, count=5, ops=["+"], family="swap")
    assert len(old) == 10
    page.get_by_label("Eine Aufgabe weniger").click()
    got = wait_saved(page, client, sheet_id, lambda p: p["count"] == 4)
    assert pairs(got["exercises"]) == pairs(old[:-2])
    assert {e["family"] for e in got["exercises"]} == {0, 1, 2, 3}


def test_903_two_quick_weniger_clicks_drop_the_last_two_in_order(editor):
    """#903: two quick "weniger" clicks, the first answer held: the last two go, the others stay in order."""
    page, client, sheet_id, old = fewer_sheet(editor)
    held = []

    def hold(route):
        # The first answer waits until the second click is sent; then both go on.
        if held:
            held.pop().continue_()
            route.continue_()
        else:
            held.append(route)

    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe weniger").click()
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(page.locator(TASKS)).to_have_count(6)
    got = wait_saved(page, client, sheet_id, lambda p: p["count"] == 6)
    assert pairs(got["exercises"]) == pairs(old[:-2])


def test_903_one_undo_brings_the_dropped_exercise_back(editor):
    """#903: Ctrl+Z after "Eine Aufgabe weniger" brings the exercises back as they were."""
    page, client, sheet_id, old = fewer_sheet(editor)
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(page.locator(TASKS)).to_have_count(7)
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(page.locator(TASKS)).to_have_count(8)
    got = wait_saved(page, client, sheet_id, lambda p: p["count"] == 8)
    assert pairs(got["exercises"]) == pairs(old)


def test_906_one_more_keeps_the_exercises_and_adds_one(editor):
    """#906: "Eine Aufgabe mehr" keeps the eight exercises as they were, in order, and adds one at the end."""
    page, client, sheet_id, old = fewer_sheet(editor)
    assert len(old) == 8
    page.get_by_label("Eine Aufgabe mehr").click()
    expect(page.locator(TASKS)).to_have_count(9)
    got = wait_saved(page, client, sheet_id, lambda p: p["count"] == 9)
    assert pairs(got["exercises"][:8]) == pairs(old)
    assert len(got["exercises"]) == 9


def test_906_one_more_with_families_keeps_the_families_and_adds_one(editor):
    """#906, families: with Tauschaufgaben "mehr" keeps the five families as they were and adds one family whole."""
    page, client, sheet_id, old = fewer_sheet(editor, count=5, ops=["+"], family="swap")
    assert len(old) == 10
    page.get_by_label("Eine Aufgabe mehr").click()
    got = wait_saved(page, client, sheet_id, lambda p: p["count"] == 6)
    assert pairs(got["exercises"][:10]) == pairs(old)
    assert len(got["exercises"]) == 12
    assert {e["family"] for e in got["exercises"]} == {0, 1, 2, 3, 4, 5}


def maths_sheet(window, server, count):
    """A sheet with one maths block of `count` Aufgaben, opened and picked. Gives the page, the client and the sheet id."""
    page, client = window()
    made = sheet(
        client, [box("m", "maths", maths(client, count=count, **LIMITS), y=20, h=60)], title="m"
    )
    page.goto(f"{server}/blatt/{made['id']}")
    expect_sheet(page)
    pick(page, "m")
    return page, client, made["id"]


def test_903_weniger_after_the_session_ran_out_keeps_the_others_after_the_login(window, server):
    """#903: "Eine Aufgabe weniger" with the session run out: after the sign-in the other exercises stay."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    old = block_of(client, sheet_id)["exercises"]
    page.context.clear_cookies()
    page.get_by_label("Eine Aufgabe weniger").click()
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS_NOTICE)
    login(page, server, client)
    expect_sheet(page)
    got = wait_saved(page, client, sheet_id, lambda p: p["count"] == 13)
    assert pairs(got["exercises"]) == pairs(old[:-1])


def test_902_an_overtaken_click_that_meets_a_run_out_session_is_not_redone_after_the_login(
    window, server
):
    """#902: "mehr" fails; its retry is on its way when "weniger" lands, then the retry meets a run out
    session. The retry is owed to nobody: after the sign-in the count stays at the "weniger" value."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    page.route("**/api/maths", lambda route: route.abort())
    page.get_by_label("Eine Aufgabe mehr").click()
    again = page.get_by_role("button", name="Erneut versuchen")
    expect(again).to_be_visible()
    page.unroute("**/api/maths")
    held = []
    page.route("**/api/maths", lambda route: held.append(route) if not held else route.continue_())
    again.click()
    with page.expect_response(lambda r: r.url.endswith("/api/maths")):
        page.get_by_label("Eine Aufgabe weniger").click()
    # "weniger" counts from the 15 the panel shows for the failed "mehr": the block stays at 14.
    expect(page.get_by_text("Die Aufgaben konnten nicht erzeugt werden.")).to_have_count(0)
    expect(page.locator(TASKS)).to_have_count(14)
    page.context.clear_cookies()
    held.pop().fulfill(status=401, body="{}")
    expect_login(page, address)
    # The browser's record of owed clicks holds none: the overtaken click is not redone.
    assert page.evaluate(f"() => localStorage.getItem('owed:{sheet_id}')") is None
    login(page, server, client)
    expect_sheet(page)
    expect(page.locator(TASKS)).to_have_count(14)
    assert block_of(client, sheet_id)["count"] == 14
