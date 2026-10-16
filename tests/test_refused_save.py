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

BAD = {**TEXT, "bogus": 1}
ALERT = "[role=alert]"


def stored(sheet_id):
    """The sheet's document as the server holds it."""
    con = db.open_db()
    return json.loads(con.execute("SELECT doc FROM sheets WHERE id = ?", (sheet_id,)).fetchone()[0])


def test_a_refused_save_names_the_field_and_keeps_the_change(editor):
    client = user()
    page = editor(box("a", "text", BAD), client=client)
    sheet_id = int(page.url.rsplit("/", 1)[1])
    held = stored(sheet_id)

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    moved = at(page, "a").evaluate("el => getComputedStyle(el).left")

    expect(page.locator(ALERT)).to_contain_text(
        "Nicht gespeichert: Das Blatt passt nicht zum Format."
    )
    expect(page.locator(ALERT)).to_contain_text("bogus")
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    expect(at(page, "a")).to_have_css("left", moved)
    assert record(page, sheet_id)["doc"]["pages"][0]["blocks"][0]["props"]["bogus"] == 1
    assert stored(sheet_id) == held

    address = page.url
    reload(page, address)
    expect(page.locator(ALERT)).to_contain_text("bogus")
    expect(at(page, "a")).to_have_css("left", moved)


def test_removing_the_block_with_the_bad_field_saves_and_clears_the_alert(editor):
    client = user()
    page = editor(box("a", "text", BAD), client=client)
    expect(page.locator(ALERT)).to_have_count(0)

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(ALERT)).to_contain_text("bogus")

    unpick(page)
    pick(page, "a")
    page.keyboard.press("Delete")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)
