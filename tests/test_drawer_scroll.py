"""The iPad held upright: an open Format drawer lies over the sheet's right end, so the desk
scrolls the picked block, or the caret in the open text, clear of it, as PowerPoint does (#265).

On its side the panel already shows, so nothing scrolls.
"""

import pytest
from playwright.sync_api import expect
from test_menu import HELD, props
from ui import FIELD, RECT, TEXT, at, bar, box, drawer, expect_picked, tool, user


def expect_wide(page):
    """Waits until the sheet has the window's width, less the desk's edges."""
    expect(page.locator("aside.left, aside.panel")).to_have_count(0)
    page.wait_for_function("document.querySelector('.sheet').getBoundingClientRect().width >= 700")


def scroll(page):
    return page.locator(".desk").first.evaluate("el => el.scrollLeft")


def desk_left(page):
    return page.locator(".desk").first.bounding_box()["x"]


def panel_left(page):
    return page.locator("aside.panel").bounding_box()["x"]


def span(page, names):
    """The left and right edges of the boxes of these blocks together, in the window."""
    boxes = [at(page, name).bounding_box() for name in names]
    return min(b["x"] for b in boxes), max(b["x"] + b["width"] for b in boxes)


def caret_right(page):
    return page.evaluate("() => getSelection().getRangeAt(0).getBoundingClientRect().right")


@pytest.mark.parametrize("kind", HELD)
def test_a_picked_block_at_the_right_end_is_scrolled_clear_of_the_drawer(editor, kind):
    """A: the picked block, or group, lies left of the Format drawer, inside the desk."""
    client = user()
    if kind == "group":
        blocks = [
            box("a1", "shape", RECT, z=1, x=150, w=25, group=["a"]),
            box("a2", "shape", RECT, z=1, x=175, w=25, group=["a"]),
        ]
        names = ["a1", "a2"]
    else:
        blocks = [
            box("a", "shape" if kind == "line" else kind, props(client, kind), z=1, x=150, w=50)
        ]
        names = ["a"]
    page = editor(*blocks, client=client, touch=True)
    expect_wide(page)
    at(page, names[0]).tap()
    expect_picked(page, *names)
    drawer(page, "right")
    # The layout effect scrolls before the drawer's first paint, so the block lies clear at once.
    assert span(page, names)[1] <= panel_left(page)
    assert span(page, names)[0] >= desk_left(page)
    assert scroll(page) > 0


def test_a_block_already_clear_of_the_drawer_does_not_move(editor):
    """B: a block in view beside the drawer stays put, and the desk does not scroll."""
    page = editor(box("a", "shape", RECT, z=1, x=20, w=40), touch=True)
    expect_wide(page)
    at(page, "a").tap()
    expect_picked(page, "a")
    before = at(page, "a").bounding_box()
    drawer(page, "right")
    assert scroll(page) == 0
    assert at(page, "a").bounding_box() == before


def test_an_open_text_keeps_its_caret_clear_of_the_drawer_and_takes_typing(editor):
    """C: the caret at the end of an open text lies left of the drawer, and typing still lands."""
    page = editor(box("a", "text", TEXT, z=1, x=150, w=50), touch=True)
    expect_wide(page)
    at(page, "a").tap()
    expect_picked(page, "a")
    at(page, "a").tap()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    drawer(page, "right")
    assert caret_right(page) <= panel_left(page)
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("z")
    expect(page.locator(FIELD)).to_be_focused()
    expect(page.locator(FIELD)).to_contain_text("z")


def test_two_picked_blocks_both_end_in_view_beside_the_drawer(editor):
    """D: two picked blocks, one under the drawer, both end left of it, inside the desk."""
    page = editor(
        box("a", "shape", RECT, z=1, x=100, w=30),
        box("b", "shape", RECT, z=2, x=150, w=40),
        touch=True,
    )
    expect_wide(page)
    at(page, "a").tap()
    page.keyboard.press("Control+a")
    expect_picked(page, "a", "b")
    drawer(page, "right")
    page.wait_for_function("document.querySelector('.desk').scrollLeft > 0")
    left, right = span(page, ["a", "b"])
    assert left >= desk_left(page)
    assert right <= panel_left(page)


def test_shutting_the_drawer_takes_the_scroll_back(editor):
    """Implied 1: when the drawer shuts, the desk scrolls back to 0 and the sheet is as it was."""
    page = editor(box("a", "shape", RECT, z=1, x=150, w=50), touch=True)
    expect_wide(page)
    sheet = page.locator(".sheet").first
    before = sheet.bounding_box()
    at(page, "a").tap()
    expect_picked(page, "a")
    drawer(page, "right")
    assert scroll(page) > 0
    bar(page, "right").tap()
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "false")
    page.wait_for_function("document.querySelector('.desk').scrollLeft === 0")
    assert sheet.bounding_box() == before


def test_the_scroll_makes_no_undo_step(editor):
    """Implied 2: scrolling the desk for a drawer changes nothing, so Rückgängig stays disabled."""
    page = editor(box("a", "shape", RECT, z=1, x=150, w=50), touch=True)
    expect_wide(page)
    at(page, "a").tap()
    expect_picked(page, "a")
    drawer(page, "right")
    assert scroll(page) > 0
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_nothing_picked_nothing_scrolls(editor):
    """Implied 7: with no block picked the drawer opens and the desk stays where it is."""
    page = editor(box("a", "shape", RECT, z=1, x=150, w=50), touch=True)
    expect_wide(page)
    drawer(page, "right")
    assert scroll(page) == 0


def test_on_its_side_opening_the_drawer_scrolls_nothing(editor):
    """E: on its side the panel shows and no drawer lies over the sheet, so nothing scrolls."""
    page = editor(box("a", "shape", RECT, z=1, x=150, w=50), touch="landscape")
    at(page, "a").tap()
    expect_picked(page, "a")
    bar(page, "right").tap()
    bar(page, "right").tap()
    assert scroll(page) == 0


def test_shutting_the_drawer_gives_back_a_zoomed_desk_its_scroll(editor):
    """Shutting the drawer returns the desk to the scroll it had before the drawer moved it."""
    # Clear of the sheet's right end, so the scroll the drawer adds lies inside the desk's reach.
    page = editor(box("a", "shape", RECT, z=1, x=120, w=50), touch=True)
    expect_wide(page)
    for _ in range(3):
        tool(page, "Größer").tap()
    at(page, "a").tap()
    expect_picked(page, "a")
    # The block's left edge to 300 px: its right edge then lies under the drawer.
    page.evaluate(
        "(by) => { document.querySelector('.desk').scrollLeft += by; }",
        at(page, "a").bounding_box()["x"] - 300,
    )
    before = scroll(page)
    assert before > 0
    drawer(page, "right")
    assert scroll(page) > before
    bar(page, "right").tap()
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "false")
    assert scroll(page) == before
