"""The fields a name line shows: the teacher ticks them in the panel, and a hidden field is not drawn at all (issue #915)."""

from playwright.sync_api import expect
from ui import at, box, pick, saved, sheet, user

from blattwerk import pdf


def fields(page, name):
    return at(page, name).locator(".fields span")


def test_a_tick_hides_and_shows_a_field(editor):
    """A1: each field has a checkbox in the panel, unticking hides it on the line, ticking shows it again."""
    page = editor(box("n", "name", {}))
    pick(page, "n")
    datum = page.get_by_label("Datum", exact=True)
    expect(datum).to_be_checked()
    datum.uncheck()
    expect(fields(page, "n")).to_have_count(2)
    datum.check()
    expect(fields(page, "n")).to_have_count(3)


def test_the_fields_left_share_the_line(editor):
    """A2: with Name hidden the other two share the line's width equally, Name keeps its double width while shown."""
    page = editor(box("n", "name", {}))
    pick(page, "n")
    expect(fields(page, "n")).to_have_count(3)
    shown = [f.bounding_box()["width"] for f in fields(page, "n").all()]
    assert abs(shown[0] - 2 * shown[1]) <= 2, shown
    page.get_by_label("Name", exact=True).uncheck()
    expect(fields(page, "n")).to_have_count(2)
    left = [f.bounding_box()["width"] for f in fields(page, "n").all()]
    assert abs(left[0] - left[1]) <= 1, left


def test_an_old_line_shows_every_field(editor):
    """A3: a name line with no `hidden` shows all its fields, and every checkbox is ticked."""
    page = editor(box("n", "name", {}))
    pick(page, "n")
    expect(fields(page, "n")).to_have_count(3)
    for word in ["Name", "Datum", "Klasse"]:
        expect(page.get_by_label(word, exact=True)).to_be_checked()


def test_the_pdf_shows_the_fields_shown(browser, server):
    """A4: the PDF prints the fields the screen shows, and no others."""
    client = user()
    mine = sheet(client, [box("n", "name", {"hidden": [1]})])["id"]
    page = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    page.goto(f"{server}/druck/{mine}")
    page.wait_for_selector("body.ready", state="attached")
    expect(page.locator(".fields span")).to_have_count(2)
    expect(page.locator(".fields span")).to_have_text(["Name:", "Klasse:"])
    page.close()


def test_the_last_field_cannot_be_unticked(editor):
    """I6: with one field left shown, its checkbox is disabled."""
    page = editor(box("n", "name", {}))
    pick(page, "n")
    page.get_by_label("Datum", exact=True).uncheck()
    page.get_by_label("Name", exact=True).uncheck()
    expect(page.get_by_label("Klasse", exact=True)).to_be_disabled()
    expect(page.get_by_label("Klasse", exact=True)).to_be_checked()


def test_renaming_with_a_field_hidden_keeps_the_hidden_word(editor):
    """I7: only the shown fields get inputs, the hidden word stays, and an emptied word moves the hidden index."""
    client = user()
    page = editor(
        box("n", "name", {"fields": ["Name", "Datum", "Klasse"], "hidden": [1]}), client=client
    )
    at(page, "n").dblclick()
    expect(page.locator('.block.sel input[aria-label^="Feld"]')).to_have_count(2)
    page.get_by_label("Feld 1").fill("Vorname")
    page.keyboard.press("Enter")
    blocks = saved(page, client)
    assert blocks[0]["props"] == {"fields": ["Vorname", "Datum", "Klasse"], "hidden": [1]}
    # Emptying the first word drops its field: the hidden Datum moves from index 1 to index 0.
    at(page, "n").dblclick()
    page.get_by_label("Feld 1").fill("")
    page.keyboard.press("Enter")
    blocks = saved(page, client)
    assert blocks[0]["props"] == {"fields": ["Datum", "Klasse"], "hidden": [0]}


def test_a_tick_is_one_undo_step_and_sets_every_picked_line(editor):
    """I8: one tick is one undo step, and with two name lines picked the tick sets both."""
    page = editor(box("a", "name", {}), box("b", "name", {}, z=2))
    pick(page, "a", "b")
    page.get_by_label("Datum", exact=True).uncheck()
    expect(fields(page, "a")).to_have_count(2)
    expect(fields(page, "b")).to_have_count(2)
    page.keyboard.press("Control+z")
    expect(fields(page, "a")).to_have_count(3)
    expect(fields(page, "b")).to_have_count(3)
    page.keyboard.press("Control+y")
    expect(fields(page, "a")).to_have_count(2)
    expect(fields(page, "b")).to_have_count(2)
