"""Ganze Seite stays whole when the window changes size, until a zoom by hand ends the fit."""

import pytest
from playwright.sync_api import expect
from test_pages import expect_in_use
from test_zoom import (
    INSIDE,
    PLACE,
    RECT,
    TEXT,
    expect_percent,
    expect_width,
    fit,
    percent,
    wheel,
    width,
)
from ui import FIELD, at, box, pick, thumb

# The page n, of w by h mm, lies whole in the desk and as large as the desk's padding lets it.
WHOLE = (
    """([n, w, h]) => {
    const d = document.querySelector('.desk');
    const s = document.querySelector(`.sheet[data-page="${n}"]`).getBoundingClientRect();
    const k = Math.min((d.clientWidth - 64) / w, (d.clientHeight - 120) / h);
    return Math.abs(s.width - w * k) < 3 && Math.abs(s.height - h * k) < 3 && ("""
    + INSIDE
    + ")(n);\n}"
)


def expect_whole(page, n, w, h):
    """Waits until page n is whole in the desk at the size a fresh Ganze Seite gives."""
    page.wait_for_function(WHOLE, arg=[n, w, h], timeout=5000)


def desk_width(page):
    return page.locator(".desk").evaluate("el => el.clientWidth")


@pytest.mark.parametrize(
    "size", [(1400, 650), (1150, 1000), (1800, 1100)], ids=["lower", "narrower", "larger"]
)
def test_the_fit_follows_a_window_change(editor, size):
    """Lower, narrower and larger: the page stays whole, as large as a fresh fit."""
    page = editor(box("a", "text", TEXT))
    fit(page).click()
    expect_whole(page, 0, 210, 297)
    page.set_viewport_size({"width": size[0], "height": size[1]})
    expect_whole(page, 0, 210, 297)
    refit = width(page)
    fit(page).click()
    expect_width(page, refit)


def lower(page):
    """The window gets lower, the width as it was: only the desk's height changes."""
    before = page.locator(".desk").evaluate("el => el.clientHeight")
    page.set_viewport_size({"width": 1400, "height": 650})
    page.wait_for_function("(h) => document.querySelector('.desk').clientHeight !== h", arg=before)
    # The observer and its effect run a few frames later: a fit follows by then.
    page.evaluate(
        "() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame("
        "() => setTimeout(done, 100))))"
    )


def test_without_a_zoom_by_hand_a_lower_window_shrinks_the_fit(editor):
    """Sanity for the next test: the fit alone follows the desk's height."""
    page = editor(box("a", "text", TEXT))
    fit(page).click()
    expect_whole(page, 0, 210, 297)
    tall = width(page)
    lower(page)
    expect_whole(page, 0, 210, 297)
    assert width(page) < tall - 20


@pytest.mark.parametrize(
    "by_hand", ["Größer", "Kleiner", "wheel"], ids=["bigger", "smaller", "wheel"]
)
def test_a_zoom_by_hand_ends_the_fit_for_a_lower_window(editor, by_hand):
    """After Ganze Seite and a zoom by hand, a lower window leaves the page as large as it was."""
    page = editor(box("a", "text", TEXT))
    fit(page).click()
    expect_whole(page, 0, 210, 297)
    shown = width(page)
    if by_hand == "wheel":
        wheel(page, -100)
    else:
        page.get_by_label(by_hand, exact=True).first.click()
    page.wait_for_function(
        "(w) => Math.abs(document.querySelector('.sheet.on').getBoundingClientRect().width"
        " - w) > 2",
        arg=shown,
    )
    zoomed, percent_before = width(page), percent(page)
    lower(page)
    assert width(page) == pytest.approx(zoomed, abs=1)
    assert percent(page) == percent_before


def test_the_fit_follows_the_panel_beside_the_desk(editor):
    """The panel opens beside the desk and the page stays whole, then closes and it stays whole."""
    page = editor(box("a", "shape", RECT, **PLACE))
    fit(page).click()
    expect_whole(page, 0, 210, 297)
    panel = page.get_by_label("Format und Ansicht", exact=True).first
    shut = desk_width(page)
    pick(page, "a")
    panel.click()
    page.wait_for_function(
        "(w) => Math.abs(document.querySelector('.desk').clientWidth - w) > 20", arg=shut
    )
    expect_whole(page, 0, 210, 297)
    panel.click()
    page.wait_for_function(
        "(w) => Math.abs(document.querySelector('.desk').clientWidth - w) < 2", arg=shut
    )
    expect_whole(page, 0, 210, 297)


def test_the_fit_keeps_the_page_in_use(editor):
    """The second page is in use: the fit and a window change keep it, not another page."""
    rest = [{"blocks": [box("b", "text", TEXT)]}, {"blocks": [box("c", "text", TEXT)]}]
    page = editor(box("a", "text", TEXT), pages=rest, theme="")
    thumb(page, 1).click()
    expect_in_use(page, 1)
    fit(page).click()
    expect_whole(page, 1, 210, 297)
    page.set_viewport_size({"width": 1000, "height": 650})
    expect_whole(page, 1, 210, 297)
    expect_in_use(page, 1)


def test_the_fit_makes_no_undo_step(editor):
    """The refit leaves the sheet and the undo button as they were."""
    page = editor(box("a", "shape", RECT, **PLACE))
    fit(page).click()
    expect_whole(page, 0, 210, 297)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    page.set_viewport_size({"width": 1400, "height": 650})
    expect_whole(page, 0, 210, 297)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_a_window_change_keeps_a_text_open(editor):
    """A teacher types while the window changes: the text stays open and takes the letters."""
    page = editor(box("a", "text", TEXT))
    fit(page).click()
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("du")
    page.set_viewport_size({"width": 1000, "height": 650})
    expect_whole(page, 0, 210, 297)
    page.keyboard.type("ch")
    expect(page.locator(FIELD)).to_have_text("duch")
    expect(at(page, "a")).to_be_visible()


def test_the_fit_settles_through_several_window_changes(editor):
    """Lower, narrower, larger and back: each change ends whole, and the sizes do not drift."""
    page = editor(box("a", "text", TEXT))
    fit(page).click()
    first = width(page)
    for size in [(1400, 650), (900, 1000), (1800, 1100), (1400, 1000)]:
        page.set_viewport_size({"width": size[0], "height": size[1]})
        expect_whole(page, 0, 210, 297)
    assert width(page) == pytest.approx(first, abs=1)
    expect_percent(page)
