"""A save the server refuses with 422 (issue #647) is said so on the page, and the change is kept.

The server lets an unknown field pass: a text block with `bogus` in its props is saved as it is. It
refuses only a broken skeleton, such as a block whose x is not a number. The refusals here come from
a request the test rewrites on its way out, with `x` set to "abc"; the server then names that field.
"""

import json

from playwright.sync_api import expect
from test_saves import record
from test_stale import STATUS
from ui import TEXT, at, box, pick, user

from blattwerk import db

ALERT = "[role=alert]"
LEFT = "el => getComputedStyle(el).left"
# Longer than the 1.1 s from a change to its save, and the 2 s of a retry after a failure.
INTERVAL = 2500


def stored(sheet_id):
    """The sheet's document as the server holds it."""
    con = db.open_db()
    return json.loads(con.execute("SELECT doc FROM sheets WHERE id = ?", (sheet_id,)).fetchone()[0])


def open_sheet(editor, props=TEXT):
    """The editor on a sheet of one text block, and the sheet's id."""
    client = user()
    page = editor(box("a", "text", props), client=client)
    return page, int(page.url.rsplit("/", 1)[1])


def break_x(page, sheet_id):
    """Rewrites each save's block x to "abc" on its way to the server, which then refuses it."""

    def rewrite(route):
        if route.request.method != "PATCH":
            return route.continue_()
        body = json.loads(route.request.post_data)
        body["doc"]["pages"][0]["blocks"][0]["x"] = "abc"
        route.continue_(post_data=json.dumps(body))

    page.route(f"**/api/sheets/{sheet_id}", rewrite)


def test_a_field_the_schema_does_not_know_saves_and_stays(editor):
    page, sheet_id = open_sheet(editor, {**TEXT, "bogus": 1})

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)

    kept = stored(sheet_id)["pages"][0]["blocks"][0]
    assert kept["props"]["bogus"] == 1
    assert kept["x"] != 15


def test_a_refused_save_names_the_field_and_keeps_the_change(editor):
    page, sheet_id = open_sheet(editor)
    break_x(page, sheet_id)
    patches = []
    page.on("request", lambda r: patches.append(r) if r.method == "PATCH" else None)

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    moved = at(page, "a").evaluate(LEFT)

    expect(page.locator(ALERT)).to_contain_text("Nicht gespeichert")
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    expect(at(page, "a")).to_have_css("left", moved)
    assert record(page, sheet_id)["doc"]["pages"][0]["blocks"][0]["x"] != 15
    assert stored(sheet_id)["pages"][0]["blocks"][0]["x"] == 15

    # One refused save, and no retry while the document is the same.
    refused = len(patches)
    assert refused == 1
    page.wait_for_timeout(INTERVAL)
    assert len(patches) == refused

    # A change the server takes once the route is gone: the alert goes, and the change is kept.
    page.unroute(f"**/api/sheets/{sheet_id}")
    page.keyboard.press("ArrowRight")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)
    assert stored(sheet_id)["pages"][0]["blocks"][0]["x"] not in (15, "abc")


def test_removing_the_block_with_the_bad_field_saves_and_clears_the_alert(editor):
    page, sheet_id = open_sheet(editor)
    break_x(page, sheet_id)

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")

    page.unroute(f"**/api/sheets/{sheet_id}")
    page.keyboard.press("Delete")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)


def test_undo_back_to_the_stored_sheet_keeps_the_change_for_redo(editor):
    page, sheet_id = open_sheet(editor)
    break_x(page, sheet_id)
    start = at(page, "a").evaluate(LEFT)

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    moved = at(page, "a").evaluate(LEFT)
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")

    # Undo puts the block back where the stored sheet has it: nothing is unsaved, nothing is lost.
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", start)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)

    # Redo brings the change back, and the refusal with it.
    page.keyboard.press("Control+y")
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    # The browser's store has the change within a second, so it is awaited, not read at once.
    page.wait_for_function("id => localStorage.getItem('unsaved:' + id) !== null", arg=sheet_id)
    assert record(page, sheet_id)["doc"]["pages"][0]["blocks"][0]["x"] != 15
    assert stored(sheet_id)["pages"][0]["blocks"][0]["x"] == 15
