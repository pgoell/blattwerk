"""A save the server refuses with 422 (issue #647) is said so on the page, and the change is kept.

The sheet holds a text block with a field the schema does not know, `bogus`. The editor keeps that
field, so each save carries it, and the server turns the save down and names the field. Until the
teacher removes the block, nothing is saved and the change stays in the browser's store.
"""

import json

from playwright.sync_api import expect
from test_saves import record
from test_stale import STATUS
from ui import TEXT, at, box, pick, reload, unpick, user

from blattwerk import db

ALERT = "[role=alert]"
LEFT = "el => getComputedStyle(el).left"
# Longer than the 1.1 s from a change to its save, and the 2 s of a retry after a failure.
INTERVAL = 2500


def stored(sheet_id):
    """The sheet's document as the server holds it."""
    con = db.open_db()
    return json.loads(con.execute("SELECT doc FROM sheets WHERE id = ?", (sheet_id,)).fetchone()[0])


def seed_bogus(sheet_id):
    """Writes the unknown field into the stored text block, as an older build saved it."""
    doc = stored(sheet_id)
    doc["pages"][0]["blocks"][0]["props"]["bogus"] = 1
    con = db.open_db()
    con.execute("UPDATE sheets SET doc = ? WHERE id = ?", (json.dumps(doc), sheet_id))


def open_bad(editor):
    """The editor on the sheet with the bad field, its block picked and moved one step."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    sheet_id = int(page.url.rsplit("/", 1)[1])
    seed_bogus(sheet_id)
    reload(page, page.url)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    return page, sheet_id


def test_a_refused_save_names_the_field_and_keeps_the_change(editor):
    page, sheet_id = open_bad(editor)
    held = stored(sheet_id)
    patches = []
    page.on("request", lambda r: patches.append(r) if r.method == "PATCH" else None)

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    moved = at(page, "a").evaluate(LEFT)

    expect(page.locator(ALERT)).to_contain_text(
        "Nicht gespeichert: Das Blatt passt nicht zum Format."
    )
    expect(page.locator(ALERT)).to_contain_text("bogus")
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    expect(at(page, "a")).to_have_css("left", moved)
    assert record(page, sheet_id)["doc"]["pages"][0]["blocks"][0]["props"]["bogus"] == 1
    assert stored(sheet_id) == held

    # One refused save, and no retry while the document is the same.
    refused = len(patches)
    assert refused == 1
    page.wait_for_timeout(INTERVAL)
    assert len(patches) == refused

    address = page.url
    reload(page, address)
    expect(page.locator(ALERT)).to_contain_text("bogus")
    expect(at(page, "a")).to_have_css("left", moved)


def test_removing_the_block_with_the_bad_field_saves_and_clears_the_alert(editor):
    page, _ = open_bad(editor)
    expect(page.locator(ALERT)).to_have_count(0)

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(ALERT)).to_contain_text("bogus")

    unpick(page)
    pick(page, "a")
    page.keyboard.press("Delete")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)


def test_undo_back_to_the_stored_sheet_keeps_the_change_for_redo(editor):
    page, sheet_id = open_bad(editor)
    start = at(page, "a").evaluate(LEFT)

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    moved = at(page, "a").evaluate(LEFT)
    expect(page.locator(ALERT)).to_contain_text("bogus")

    # Undo puts the block back where the stored sheet has it: nothing is unsaved, nothing is lost.
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", start)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)

    # Redo brings the change back, and the refusal with it.
    page.keyboard.press("Control+y")
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(ALERT)).to_contain_text("bogus")
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    # The browser's store has the change within a second, so it is awaited, not read at once.
    page.wait_for_function("id => localStorage.getItem('unsaved:' + id) !== null", arg=sheet_id)
    kept = record(page, sheet_id)["doc"]["pages"][0]["blocks"][0]
    assert kept["props"]["bogus"] == 1
    assert kept["x"] != stored(sheet_id)["pages"][0]["blocks"][0]["x"]
