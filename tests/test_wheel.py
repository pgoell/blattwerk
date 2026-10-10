"""Ctrl and the wheel beside the desk: never the browser's zoom, over the thumbnails their size."""

import pytest
from playwright.sync_api import expect
from test_zoom import WATCH, expect_width, kept, settled, wheel, width
from ui import TEXT, at, box, centre, pick

WINDOW = "[innerWidth, innerHeight, devicePixelRatio, visualViewport.scale]"
PAPER = '.pages [data-thumb="0"] .paper'
THUMB = f"(w) => Math.abs(document.querySelector('{PAPER}').getBoundingClientRect().width - w) < 1"
# Where the wheel turns beside the desk and the thumbnails: the panel Seiten below them, the
# format panel, and the bar.
BESIDE = {"seiten": ".left .foot", "format": ".panel", "bar": "header .top"}


def opened(editor, pages=1):
    """The editor with the panel Seiten open, its block selected, and the wheel watched."""
    rest = [{"blocks": []} for _ in range(pages - 1)]
    page = editor(box("a", "text", TEXT), pages=rest, theme="")
    pick(page, "a")
    page.evaluate(WATCH)
    return page


def thumb(page):
    """The width on the screen of the first thumbnail's page, in px."""
    return page.locator(PAPER).evaluate("el => el.getBoundingClientRect().width")


def expect_thumb(page, wide):
    """Waits until the first thumbnail's page is this wide."""
    page.wait_for_function(THUMB, arg=wide)


def look(page):
    """What a wheel beside the desk must leave alone: the window, the page, the thumbnails, and
    how far the desk and the panels are scrolled."""
    scrolled = "[...document.querySelectorAll('.desk, .left, .panel')].map((el) => el.scrollTop)"
    return page.evaluate(f"[{WINDOW}, {scrolled}]"), round(width(page)), round(thumb(page))


def expect_unchanged(page):
    """Nothing is on its way to the server and nothing can be undone."""
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    assert page.locator("header [role=status]").inner_text() == "Gespeichert"
    expect(at(page, "a")).to_have_class("block sel")


# Asked #162, A3, and implied I6


@pytest.mark.parametrize("where", BESIDE)
@pytest.mark.parametrize("delta", [-100, 100, -3])
def test_ctrl_wheel_beside_the_desk_is_kept_from_the_browser_and_does_nothing(editor, where, delta):
    page = opened(editor)
    was = look(page)
    wheel(page, delta, centre(page.locator(BESIDE[where])))
    assert kept(page) is True
    settled(page)
    assert look(page) == was
    expect_unchanged(page)


# Asked #162, A4


def test_ctrl_wheel_over_the_thumbnails_makes_them_larger_and_smaller(editor):
    page = opened(editor)
    was = look(page)
    over = centre(page.locator(PAPER))
    assert thumb(page) == pytest.approx(97, abs=0.5)
    for delta, wide in ((-100, 97 * 1.25), (-100, 97 * 1.25**2), (100, 97 * 1.25), (100, 97)):
        wheel(page, delta, over)
        assert kept(page) is True
        expect_thumb(page, wide)
    wheel(page, 100, over)
    assert kept(page) is True
    expect_thumb(page, 97 / 1.25)
    # The page on the desk and the window stay as they were, and so does the sheet.
    wheel(page, -100, over)
    expect_thumb(page, 97)
    assert look(page) == was
    expect_unchanged(page)


def test_thumbnails_made_smaller_and_larger_again_stand_two_in_a_row_as_before(editor):
    page = opened(editor, pages=2)
    tops = "[...document.querySelectorAll('.pages [data-thumb]')].map((el) => el.offsetTop)"
    was = page.evaluate(tops)
    assert was[0] == was[1]
    over = centre(page.locator(PAPER))
    wheel(page, 100, over)
    expect_thumb(page, 97 / 1.25)
    wheel(page, -100, over)
    expect_thumb(page, 97)
    assert page.evaluate(tops) == was


def test_a_pinch_over_the_thumbnails_sizes_them_smoothly(editor):
    page = opened(editor)
    over = centre(page.locator(PAPER))
    # A trackpad sends many small turns of the wheel with Ctrl.
    for n in range(1, 6):
        wheel(page, -10, over)
        assert kept(page) is True
        expect_thumb(page, 97 * 1.25 ** (n / 10))


def test_the_thumbnail_drawn_larger_is_the_whole_page(editor):
    page = opened(editor)
    wheel(page, -100, centre(page.locator(PAPER)))
    expect_thumb(page, 97 * 1.25)
    paper = page.locator(PAPER).bounding_box()
    assert paper["height"] == pytest.approx(paper["width"] * 297 / 210, abs=1)
    # The block is drawn on it at the thumbnail's scale: 180 mm of the page's 210.
    drawn = page.locator(f"{PAPER} .block").bounding_box()
    assert drawn["width"] == pytest.approx(paper["width"] * 180 / 210, abs=1)
    # The button for a new page is as wide as a thumbnail.
    assert page.locator(".pages i").bounding_box()["width"] == pytest.approx(paper["width"], abs=1)


# Implied #162, I7


def test_ctrl_wheel_over_the_desk_still_zooms_the_page(editor):
    page = opened(editor)
    wide, small = width(page), thumb(page)
    wheel(page, -100)
    assert kept(page) is True
    expect_width(page, wide * 1.25)
    assert thumb(page) == pytest.approx(small, abs=0.5)


@pytest.mark.parametrize("panel", [".left", ".panel"])
def test_the_wheel_alone_scrolls_a_panel(editor, panel):
    page = opened(editor, pages=12)
    was = look(page)
    over = ".pages" if panel == ".left" else panel
    wheel(page, 300, centre(page.locator(over)), ctrl=False)
    assert kept(page) is False
    page.wait_for_function(f"document.querySelector('{panel}').scrollTop > 0")
    wheel(page, -300, ctrl=False, point=centre(page.locator(over)))
    assert kept(page) is False
    page.wait_for_function(f"document.querySelector('{panel}').scrollTop === 0")
    assert look(page) == was


# Implied #162, I8


def test_the_thumbnails_have_a_smallest_and_a_largest_size(editor):
    page = opened(editor, pages=3)
    over = ".pages"
    for delta, limit, across in ((-100, 200, 1), (100, 60, 3)):
        for _ in range(8):
            wheel(page, delta, centre(page.locator(over)))
            assert kept(page) is True
        expect_thumb(page, limit)
        # At the limit the wheel is still not the browser's, and nothing moves.
        wheel(page, delta, centre(page.locator(over)))
        assert kept(page) is True
        settled(page)
        assert thumb(page) == pytest.approx(limit, abs=0.5)
        # The thumbnails stand in rows that fit the panel: it never scrolls sideways.
        tops = page.eval_on_selector_all(
            ".pages [data-thumb]", "els => els.map((el) => el.getBoundingClientRect().top)"
        )
        assert len([top for top in tops if top == tops[0]]) == across
        assert page.locator(".left").evaluate("el => el.scrollWidth <= el.clientWidth")
    # One step back from the smallest: the limit is no trap.
    wheel(page, -100, centre(page.locator(over)))
    expect_thumb(page, 60 * 1.25)
