"""The iPad held upright: the Format panel comes up from below and takes the desk's lower part, so the
desk scrolls the picked block, or the caret in the open text, into view above it (#265, #1187).

On its side the panel stands at the right, so nothing scrolls.
"""

import pytest
from playwright.sync_api import expect
from test_menu import HELD, props
from ui import FIELD, RECT, TEXT, at, bar, box, drawer, expect_lit, expect_picked, user

# Low on the page: in view in the whole desk, and under the panel once that is up.
LOW = {"y": 235, "h": 20}


def scroll(page):
    return page.locator(".desk").first.evaluate("el => el.scrollTop")


def desk_top(page):
    return page.locator(".desk").first.bounding_box()["y"]


def panel_top(page):
    return page.locator("aside.panel").bounding_box()["y"]


def span(page, names):
    """The top and bottom edges of the boxes of these blocks together, in the window."""
    boxes = [at(page, name).bounding_box() for name in names]
    return min(b["y"] for b in boxes), max(b["y"] + b["height"] for b in boxes)


def expect_above(page, names):
    """Waits until the blocks lie whole between the desk's top and the panel."""
    expect(page.locator("aside.panel")).to_be_visible()
    foot = panel_top(page)
    page.wait_for_function(
        """([names, foot]) => names.every((name) =>
            document.querySelector(`.block[data-id="${name}"]`).getBoundingClientRect().bottom <= foot)""",
        arg=[names, foot],
    )
    top, bottom = span(page, names)
    assert top >= desk_top(page) and bottom <= foot


@pytest.mark.parametrize("kind", HELD)
def test_a_picked_block_low_on_the_page_is_scrolled_into_view_above_the_panel(editor, kind):
    """A: the picked block, or group, lies above the Format panel, inside the desk."""
    client = user()
    if kind == "group":
        blocks = [
            box("a1", "shape", RECT, z=1, x=20, w=25, **LOW, group=["a"]),
            box("a2", "shape", RECT, z=1, x=45, w=25, **LOW, group=["a"]),
        ]
        names = ["a1", "a2"]
    else:
        blocks = [
            box("a", "shape" if kind == "line" else kind, props(client, kind), z=1, w=50, **LOW)
        ]
        names = ["a"]
    page = editor(*blocks, client=client, touch=True)
    at(page, names[0]).tap()
    expect_picked(page, *names)
    expect_above(page, names)
    assert scroll(page) > 0


def test_a_block_already_above_the_panel_does_not_move(editor):
    """B: a block in view above the panel stays put, and the desk does not scroll."""
    page = editor(box("a", "shape", RECT, z=1, x=20, y=20, w=40), touch=True)
    before = at(page, "a").bounding_box()
    at(page, "a").tap()
    expect_picked(page, "a")
    expect(page.locator("aside.panel")).to_be_visible()
    assert scroll(page) == 0
    assert at(page, "a").bounding_box() == before


def test_an_open_text_stays_above_the_panel_and_takes_typing(editor):
    """C: the open text lies above the panel, and typing still lands."""
    page = editor(box("a", "text", TEXT, z=1, w=50, **LOW), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    expect_above(page, ["a"])
    at(page, "a").tap()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.type("z")
    expect(page.locator(FIELD)).to_be_focused()
    expect(page.locator(FIELD)).to_contain_text("z")
    caret = page.evaluate("() => getSelection().getRangeAt(0).getBoundingClientRect().bottom")
    assert caret <= panel_top(page)


def test_two_picked_blocks_bring_the_first_into_view_above_the_panel(editor):
    """D: of two picked blocks the first one picked ends above the panel."""
    page = editor(
        box("a", "shape", RECT, z=1, x=20, w=30, **LOW),
        box("b", "shape", RECT, z=2, x=80, w=40, **LOW),
        touch=True,
    )
    at(page, "a").tap()
    page.keyboard.press("Control+a")
    expect_picked(page, "a", "b")
    expect_above(page, ["a", "b"])


def test_fertig_leaves_the_block_in_view(editor):
    """Implied 1: when the panel shuts, the block is still in the desk, which has its room back."""
    page = editor(box("a", "shape", RECT, z=1, w=50, **LOW), touch=True)
    at(page, "a").tap()
    expect_above(page, ["a"])
    page.locator("aside.panel").get_by_role("button", name="Fertig", exact=True).tap()
    expect(page.locator("aside.panel")).to_have_count(0)
    expect_picked(page, "a")
    top, bottom = span(page, ["a"])
    assert top >= desk_top(page) and bottom <= page.viewport_size["height"]


def test_the_scroll_makes_no_undo_step(editor):
    """Implied 2: scrolling the desk for the panel changes nothing, so Rückgängig stays disabled."""
    page = editor(box("a", "shape", RECT, z=1, w=50, **LOW), touch=True)
    at(page, "a").tap()
    expect_above(page, ["a"])
    assert scroll(page) > 0
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_nothing_picked_nothing_scrolls(editor):
    """Implied 7: with no block picked the bar's button opens the panel and the desk stays."""
    page = editor(box("a", "shape", RECT, z=1, w=50, **LOW), touch=True)
    drawer(page, "right")
    expect(page.locator("aside.panel")).to_be_visible()
    assert scroll(page) == 0
    # The same button sends it back.
    bar(page, "right").tap()
    expect_lit(bar(page, "right"), "false")
    expect(page.locator("aside.panel")).to_have_count(0)


def test_on_its_side_a_pick_scrolls_nothing(editor):
    """E: on its side the panel shows at the right and takes none of the desk, so nothing scrolls."""
    page = editor(box("a", "shape", RECT, z=1, x=150, y=20, w=50), touch="landscape")
    at(page, "a").tap()
    expect_picked(page, "a")
    assert scroll(page) == 0
    assert page.locator(".desk").first.evaluate("el => el.scrollLeft") == 0
