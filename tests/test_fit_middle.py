"""Ganze Seite keeps a page in use whole in view (issue 629); the page keys work after it (632)."""

from test_pages import expect_in_use, three
from test_zoom import fit
from ui import TEXT, box, expect_picked, pick, thumb

INSIDE_BOXES = """(n) => {
    const d = document.querySelector('.desk').getBoundingClientRect();
    const s = document.querySelector(`.sheet[data-page="${n}"]`).getBoundingClientRect();
    return s.width > 0 && s.top >= d.top && s.bottom <= d.bottom
        && s.left >= d.left && s.right <= d.right;
}"""


def expect_whole_in_view(page, n):
    """Waits until page n's box lies wholly inside the desk's box, as the eye sees it."""
    page.wait_for_function(INSIDE_BOXES, arg=n, timeout=5000)


def window(page, width, height):
    page.set_viewport_size({"width": width, "height": height})


def open_in_use(page, n):
    """Puts page n in use by its thumbnail, then fits it with Ganze Seite."""
    thumb(page, n).click()
    expect_in_use(page, n)
    fit(page).click()


def test_a_middle_page_stays_whole_when_the_window_gets_lower(editor):
    """629: page 2 in use, fitted; a lower window keeps the whole page 2 in the desk."""
    page = three(editor)
    window(page, 1280, 1024)
    open_in_use(page, 1)
    expect_whole_in_view(page, 1)
    window(page, 1280, 800)
    expect_whole_in_view(page, 1)
    expect_in_use(page, 1)


def test_a_middle_page_stays_whole_when_the_window_is_back(editor):
    """629: after the lower window, the taller one brings page 2 back whole, not page 1 or 3."""
    page = three(editor)
    window(page, 1280, 1024)
    open_in_use(page, 1)
    window(page, 1280, 800)
    expect_whole_in_view(page, 1)
    window(page, 1280, 1024)
    expect_whole_in_view(page, 1)
    expect_in_use(page, 1)


def test_a_middle_page_stays_whole_when_the_panel_hides_and_shows(editor):
    """629: the right panel shut and open again, page 2 stays whole in the desk each time."""
    page = three(editor)
    window(page, 1280, 1024)
    open_in_use(page, 1)
    expect_whole_in_view(page, 1)
    panel = page.get_by_label("Format und Ansicht", exact=True).first
    shut = page.locator(".desk").evaluate("el => el.clientWidth")
    panel.click()
    page.wait_for_function(
        "(w) => Math.abs(document.querySelector('.desk').clientWidth - w) > 20", arg=shut
    )
    expect_whole_in_view(page, 1)
    panel.click()
    page.wait_for_function(
        "(w) => Math.abs(document.querySelector('.desk').clientWidth - w) < 2", arg=shut
    )
    expect_whole_in_view(page, 1)
    expect_in_use(page, 1)


def test_the_last_page_stays_whole_when_the_window_gets_lower(editor):
    """629: page 3, the last, fitted; a lower window keeps it whole in the desk."""
    page = three(editor)
    window(page, 1280, 1024)
    open_in_use(page, 2)
    expect_whole_in_view(page, 2)
    window(page, 1280, 800)
    expect_whole_in_view(page, 2)
    expect_in_use(page, 2)


def test_ganze_seite_from_the_zoom_list_keeps_a_middle_page_whole(editor):
    """629 beyond the brief: the list's entry fits page 2 too, and a lower window keeps it whole."""
    page = three(editor)
    window(page, 1280, 1024)
    thumb(page, 1).click()
    expect_in_use(page, 1)
    page.locator("button.zoom").first.click()
    page.get_by_role("menuitem", name="Ganze Seite").click()
    expect_whole_in_view(page, 1)
    window(page, 1280, 800)
    expect_whole_in_view(page, 1)
    expect_in_use(page, 1)


def test_page_down_and_end_work_right_after_ganze_seite(editor):
    """632: with the focus on the button, PageDown shows page 2 and End the last page."""
    page = three(editor)
    fit(page).click()
    page.keyboard.press("PageDown")
    expect_in_use(page, 1)
    page.keyboard.press("End")
    expect_in_use(page, 2)


def desk_top(page):
    return page.evaluate("document.querySelector('.desk').scrollTop")


def test_page_down_works_after_ganze_seite_with_a_block_picked(editor):
    """Review of #638: with a block picked, PageDown after Ganze Seite still scrolls the desk."""
    page = three(editor)
    pick(page, "a")
    fit(page).click()
    was = desk_top(page)
    page.keyboard.press("PageDown")
    page.wait_for_function("(was) => document.querySelector('.desk').scrollTop > was + 50", arg=was)
    expect_picked(page, "a")


def test_the_page_keys_on_a_thumbnail_page_the_strip_not_the_desk(editor):
    """Review of #638: on a thumbnail, PageDown scrolls the long strip and leaves the desk."""
    page = editor(
        box("a", "text", TEXT),
        pages=[{"blocks": [box(f"p{n}", "text", TEXT)]} for n in range(14)],
        theme="",
    )
    window(page, 1280, 700)
    thumb(page, 0).click()
    was = desk_top(page)
    page.keyboard.press("PageDown")
    page.wait_for_function(
        "() => document.querySelector('.pages').closest('aside, .left').scrollTop > 0"
    )
    assert desk_top(page) == was


def test_page_up_and_home_work_right_after_ganze_seite_from_the_zoom_list(editor):
    """632: Ganze Seite picked in the zoom list, then PageUp shows page 2 and Home page 1."""
    page = three(editor)
    thumb(page, 2).click()
    expect_in_use(page, 2)
    page.locator("button.zoom").first.click()
    page.get_by_role("menuitem", name="Ganze Seite").click()
    page.keyboard.press("PageUp")
    expect_in_use(page, 1)
    page.keyboard.press("Home")
    expect_in_use(page, 0)
