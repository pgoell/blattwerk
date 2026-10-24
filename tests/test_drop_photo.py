"""A photo dropped on the feedback form, not on the sheet.

The drop helpers live in test_drop.py."""

from playwright.sync_api import expect
from test_drop import (
    EFFECT,
    KEPT,
    PDF,
    PNG,
    field,
    landed,
    new,
    photos,
    sent,
    spot,
)
from ui import (
    TEXT,
    box,
    centre,
    drop,
    png,
    saved,
    user,
)


def test_a_photo_dropped_on_the_feedback_photo_field_lands_there(editor):
    page = editor(box("a", "text", TEXT))
    point = field(page)
    assert page.evaluate(EFFECT, point) == "copy"
    drop(page, *point, PNG)
    photos(page, 1)
    expect(page.locator("dialog.feedback figcaption")).to_have_text("Bild 1")


def test_a_drop_on_the_photo_field_adds_nothing_to_the_sheet(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    url = page.url
    point = field(page)
    assert drop(page, *point, PNG) == KEPT
    photos(page, 1)
    page.keyboard.press("Escape")
    expect(page.locator("dialog")).to_have_count(0)
    # A picture of the first drop would be on the sheet by the time the second one's is.
    drop(page, *spot(page, 105, 150), PNG)
    landed(page, 2)
    assert [b["type"] for b in new(saved(page, client), "a")] == ["image"]
    assert page.url == url


def test_several_photos_in_one_drop_on_the_photo_field(editor):
    page = editor(box("a", "text", TEXT))
    files = [(f"{n}.png", "image/png", png(bytes([n, 0, 0]))) for n in range(3)]
    drop(page, *field(page), *files)
    photos(page, 3)
    expect(page.locator("dialog.feedback figcaption")).to_have_text(["Bild 1", "Bild 2", "Bild 3"])


def test_the_photo_field_refuses_a_file_that_is_no_picture(editor):
    page = editor(box("a", "text", TEXT))
    url = page.url
    point = field(page)
    assert drop(page, *point, PDF) == KEPT
    # The PDF of the first drop would be there by the time the second one's picture is.
    assert drop(page, *point, PDF, PNG) == KEPT
    photos(page, 1)
    assert page.url == url


def test_a_drop_beside_the_photo_field_adds_nothing_anywhere(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    url = page.url
    point = field(page)
    beside = centre(page.locator("dialog.feedback h1"))
    assert page.evaluate(EFFECT, beside) == "none"
    assert drop(page, *beside, PNG) == KEPT
    # A photo of the first drop would be there by the time the second one's is.
    drop(page, *point, PNG)
    photos(page, 1)
    page.keyboard.press("Escape")
    expect(page.locator("dialog")).to_have_count(0)
    assert [b["id"] for b in saved(page, client)] == ["a"]
    assert page.url == url


def test_a_dropped_photo_goes_out_with_the_feedback(editor, data_dir):
    page = editor(box("a", "text", TEXT))
    drop(page, *field(page), PNG)
    photos(page, 1)
    page.get_by_role("button", name="Abschicken").click()
    expect(page.locator("dialog.feedback .status")).to_have_text("Danke! Ist angekommen.")
    assert [name.split(".")[0] for name in sent(data_dir)] == ["photo-1"]
    photos(page, 0)


def test_entfernen_takes_a_dropped_photo_away(editor, data_dir):
    page = editor(box("a", "text", TEXT))
    point = field(page)
    drop(page, *point, PNG, PNG)
    photos(page, 2)
    page.get_by_label("Bild 1 entfernen").click()
    photos(page, 1)
    page.get_by_role("button", name="Abschicken").click()
    expect(page.locator("dialog.feedback .status")).to_have_text("Danke! Ist angekommen.")
    assert [name.split(".")[0] for name in sent(data_dir)] == ["photo-1"]


def test_a_photo_dropped_on_the_photo_page_lands_there(editor, server):
    """No editor is there to keep a dropped file from the browser: the field does it alone."""
    page = editor(box("a", "text", TEXT))
    page.goto(f"{server}/feedback/fotos")
    point = centre(page.locator(".pick"))
    assert page.evaluate(EFFECT, point) == "copy"
    assert drop(page, *point, PDF, PNG) == KEPT
    photos(page, 1)
    assert page.url == f"{server}/feedback/fotos"
