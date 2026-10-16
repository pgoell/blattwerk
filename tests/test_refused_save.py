"""A save the server refuses with 422 (issue #647) is said so on the page, and the change is kept.

The server lets an unknown field pass: a text block with `bogus` in its props is saved as it is. It
refuses only a broken skeleton, such as a block whose x is not a number. The refusals here come from
a request the test rewrites on its way out, with `x` set to "abc"; the server then names that field.
"""

import json

from playwright.sync_api import expect
from test_saves import record
from test_stale import STATUS
from ui import TEXT, at, box, pick, unpick, user

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


def break_x(page, url, method="PATCH"):
    """Rewrites each save's block x to "abc" on its way to the server, which then refuses it."""

    def rewrite(route):
        body = json.loads(route.request.post_data or "{}") if route.request.method == method else {}
        if "doc" not in body:
            return route.continue_()
        body["doc"]["pages"][0]["blocks"][0]["x"] = "abc"
        route.continue_(post_data=json.dumps(body))

    page.route(url, rewrite)


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
    break_x(page, f"**/api/sheets/{sheet_id}")
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
    break_x(page, f"**/api/sheets/{sheet_id}")

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")

    page.unroute(f"**/api/sheets/{sheet_id}")
    page.keyboard.press("Delete")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)


def test_undo_back_to_the_stored_sheet_keeps_the_change_for_redo(editor):
    page, sheet_id = open_sheet(editor)
    break_x(page, f"**/api/sheets/{sheet_id}")
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


def stored_title(sheet_id):
    """The sheet's title as the server holds it."""
    con = db.open_db()
    return con.execute("SELECT title FROM sheets WHERE id = ?", (sheet_id,)).fetchone()[0]


def test_a_renamed_title_still_goes_while_the_doc_is_refused(editor):
    page, sheet_id = open_sheet(editor)
    break_x(page, f"**/api/sheets/{sheet_id}")
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")

    with page.expect_response(lambda r: r.request.method == "PATCH") as sent:
        page.get_by_label("Titel").fill("Neuer Titel")
    sent.value.finished()

    assert stored_title(sheet_id) == "Neuer Titel"
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")


def test_a_refused_sheet_off_screen_says_it_is_not_saved_and_why(editor):
    page, sheet_id = open_sheet(editor)
    break_x(page, f"**/api/sheets/{sheet_id}")
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")

    page.goto(page.url.split("/blatt/")[0] + "/")
    notice = page.locator(".notice")
    expect(notice).to_contain_text("ist nicht gespeichert: das Blatt passt nicht zum Format.")
    expect(notice).not_to_contain_text("versucht es weiter")


def test_keeping_a_refused_sheet_as_new_names_the_problem(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    sheet_id = int(page.url.rsplit("/", 1)[1])
    assert client.delete(f"/api/sheets/{sheet_id}").status_code == 200

    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.get_by_role("alert")).to_contain_text("auf einem anderen Gerät gelöscht")

    break_x(page, "**/api/sheets", method="POST")
    page.get_by_role("button", name="Als neues Blatt behalten").click()
    expect(page.get_by_role("alert")).to_contain_text("pages[0].blocks[0].x")
    expect(page.get_by_role("alert")).not_to_contain_text("Prüfe deine Verbindung")


def test_a_failed_rename_of_a_refused_sheet_is_tried_again(editor):
    page, sheet_id = open_sheet(editor)
    failed = []

    def rewrite(route):
        # The first rename fails with 500. The doc's save is refused as before; the rest goes on.
        body = (
            json.loads(route.request.post_data or "{}") if route.request.method == "PATCH" else {}
        )
        if "doc" in body:
            body["doc"]["pages"][0]["blocks"][0]["x"] = "abc"
            return route.continue_(post_data=json.dumps(body))
        if "title" in body and not failed:
            failed.append(body)
            return route.fulfill(status=500, body="{}")
        route.continue_()

    page.route(f"**/api/sheets/{sheet_id}", rewrite)
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")

    # The rename fails once, then is sent again on its own, and reaches the server.
    with page.expect_response(lambda r: r.request.method == "PATCH" and r.status == 200) as sent:
        page.get_by_label("Titel").fill("Neuer Titel")
    sent.value.finished()
    assert len(failed) == 1
    assert stored_title(sheet_id) == "Neuer Titel"
    expect(page.locator(ALERT)).to_contain_text("pages[0].blocks[0].x")

    # The teacher fixes the doc: the next change saves, the alert goes, and the server holds it.
    page.unroute(f"**/api/sheets/{sheet_id}")
    # The title field has the focus: the block is picked again, so the arrow moves it.
    unpick(page)
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(ALERT)).to_have_count(0)
    assert stored(sheet_id)["pages"][0]["blocks"][0]["x"] not in (15, "abc")
    assert stored_title(sheet_id) == "Neuer Titel"
