"""Deleting a page keeps the zoom and the page in use on screen, as in PowerPoint (issue 614)."""

from playwright.sync_api import expect
from test_clipboard import button
from test_pages import expect_in_use
from ui import TEXT, at, box, thumb


def two(editor):
    """Two pages with a heading each, "a" on the first and "b" on the second, the second Quer."""
    page = editor(box("a", "text", TEXT), pages=[{"blocks": [box("b", "text", TEXT)]}], theme="")
    quer(page, 1)
    return page


def quer(page, n):
    """Page n goes Quer alone, from the panel Ansicht."""
    thumb(page, n).click()
    page.get_by_role("tab", name="Ansicht").click()
    page.locator(".panel").get_by_role("button", name="Nur diese Seite").click()
    page.locator(".panel").get_by_role("button", name="Quer", exact=True).click()


def fit(page):
    """Ganze Seite on the page in use, and the zoom label's text."""
    page.get_by_label("Ganze Seite", exact=True).first.click()
    return page.locator("button.zoom").first.inner_text()


def seen(page, name):
    """The block lies whole inside the desk's visible rect."""
    desk, block = page.locator(".desk").bounding_box(), at(page, name).bounding_box()
    assert desk["y"] <= block["y"]
    assert block["y"] + block["height"] <= desk["y"] + desk["height"]
    assert desk["x"] <= block["x"]
    assert block["x"] + block["width"] <= desk["x"] + desk["width"]


def test_delete_on_a_quer_thumbnail_keeps_the_zoom_and_page_one_in_view(editor):
    page = two(editor)
    at(page, "a").click()
    zoom = fit(page)
    thumb(page, 1).focus()
    page.keyboard.press("Delete")
    expect(page.locator("button.zoom").first).to_have_text(zoom)
    expect_in_use(page, 0)
    seen(page, "a")


def test_seite_loeschen_keeps_the_zoom_and_page_one_in_view(editor):
    page = two(editor)
    at(page, "a").click()
    zoom = fit(page)
    thumb(page, 1).click()
    button(page, "Seite löschen").click()
    expect(page.locator("button.zoom").first).to_have_text(zoom)
    expect_in_use(page, 0)
    seen(page, "a")


def test_undo_after_the_delete_brings_the_quer_page_back_at_the_same_zoom(editor):
    page = two(editor)
    at(page, "a").click()
    zoom = fit(page)
    thumb(page, 1).focus()
    page.keyboard.press("Delete")
    expect(thumb(page, 1)).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(thumb(page, 1)).to_have_count(1)
    expect(page.locator("button.zoom").first).to_have_text(zoom)


def test_deleting_an_upright_page_beside_a_quer_one_keeps_the_zoom(editor):
    page = editor(
        box("a", "text", TEXT),
        pages=[{"blocks": [box("b", "text", TEXT)]}, {"blocks": [box("c", "text", TEXT)]}],
        theme="",
    )
    quer(page, 1)
    at(page, "a").click()
    zoom = fit(page)
    thumb(page, 2).focus()
    page.keyboard.press("Delete")
    expect(thumb(page, 2)).to_have_count(0)
    expect(page.locator("button.zoom").first).to_have_text(zoom)
    seen(page, "a")


def test_deleting_a_quer_page_first_with_the_second_in_use_keeps_it_in_view(editor):
    page = editor(box("a", "text", TEXT), pages=[{"blocks": [box("b", "text", TEXT)]}], theme="")
    quer(page, 0)
    thumb(page, 1).click()
    zoom = fit(page)
    thumb(page, 0).focus()
    page.keyboard.press("Delete")
    expect(page.locator("button.zoom").first).to_have_text(zoom)
    expect_in_use(page, 0)
    seen(page, "b")
