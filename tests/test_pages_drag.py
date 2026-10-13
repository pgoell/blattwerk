"""The thumbnails in Blattform: the drag, its hint, and the panel that scrolls under a drag."""

import pytest
from playwright.sync_api import expect
from test_pages import DRAG, expect_in_use, expect_no_drag, expect_order, half, lift, pull
from ui import BROWSER, TEXT, box, centre, drawer, finger, thumb

NAMES = "abcdefghijklmnop"
# The panel that holds the thumbnails. A drag at its lower or upper edge scrolls it.
PANEL = "document.querySelector('aside.left')"
LAST = "document.querySelector('.pages [data-thumb=\"15\"]')"
FIRST = "document.querySelector('.pages [data-thumb=\"0\"]')"


def blatt(editor, names="abc"):
    """Blattform, the tab Vorlagen open, one block on each page named by `names`."""
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in names[1:]]
    page = editor(box(names[0], "text", TEXT), pages=rest)
    page.get_by_role("tab", name="Vorlagen").click()
    expect(thumb(page, 0)).to_be_visible()
    return page


def in_view(page, selector):
    """Whether the thumbnail lies inside the panel, in full."""
    return page.evaluate(
        f"""() => {{
            const p = {PANEL}.getBoundingClientRect();
            const t = {selector}.getBoundingClientRect();
            return t.top >= p.top && t.bottom <= p.bottom;
        }}"""
    )


def frames(page):
    """The panel's scrollTop after two frames: the same as now once the scroll has stopped."""
    return page.evaluate(
        "() => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame("
        f"() => ok({PANEL}.scrollTop))))"
    )


def bottom_edge(page):
    """A point 5 px above the panel's lower edge, in its middle."""
    box_ = page.locator("aside.left").bounding_box()
    return box_["x"] + box_["width"] / 2, box_["y"] + box_["height"] - 5


def top_edge(page):
    """A point 5 px below the panel's upper edge, in its middle."""
    box_ = page.locator("aside.left").bounding_box()
    return box_["x"] + box_["width"] / 2, box_["y"] + 5


def scrolled_down(page):
    """Waits until the panel has been scrolled and the last thumbnail is in view."""
    page.wait_for_function(f"{PANEL}.scrollTop > 0", timeout=5000)
    page.wait_for_function(
        f"() => {LAST}.getBoundingClientRect().bottom <= {PANEL}.getBoundingClientRect().bottom",
        timeout=5000,
    )


def test_a4_a_thumbnail_dragged_in_blattform_moves_its_page_to_the_drop(editor):
    """A4"""
    page = blatt(editor)
    pull(page, 0, 2, "right")
    expect_order(page, "bca")
    expect_no_drag(page)


def test_a5_a_thumbnail_dragged_with_the_tour_open_moves_its_page(editor):
    """A5"""
    page = blatt(editor)
    page.get_by_role("button", name="Rundgang", exact=True).click()
    expect(page.locator(".tour")).to_be_visible()
    pull(page, 0, 2, "right")
    expect_order(page, "bca")


def test_a6_a_line_marks_where_the_page_will_land_in_blattform(editor):
    """A6"""
    page = blatt(editor)
    lift(page, 0, 2, "right")
    expect(page.locator(".pages .mark")).to_have_count(1)
    expect(page.locator(".pages .mark")).to_have_attribute("data-to", "2")
    page.mouse.up()
    expect_no_drag(page)


def test_a7_undo_and_redo_take_a_move_in_blattform_as_one_step(editor):
    """A7"""
    page = blatt(editor)
    pull(page, 0, 2, "right")
    expect_order(page, "bca")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    page.keyboard.press("Control+y")
    expect_order(page, "bca")


def test_a8_ctrl_arrows_and_escape_on_a_thumbnail_in_blattform(editor):
    """A8"""
    page = blatt(editor)
    thumb(page, 0).focus()
    page.keyboard.press("Control+ArrowDown")
    expect_order(page, "bac")
    thumb(page, 1).focus()
    page.keyboard.press("Control+Shift+ArrowDown")
    expect_order(page, "bca")
    lift(page, 0, 2, "right")
    page.keyboard.press("Escape")
    expect_no_drag(page)
    page.mouse.up()
    expect_order(page, "bca")


def test_a9_a_thumbnail_shows_a_hand_and_a_closed_hand_in_a_drag(editor):
    """A9"""
    page = blatt(editor)
    expect(thumb(page, 0)).to_have_css("cursor", "grab")
    lift(page, 0, 2, "right")
    expect(thumb(page, 0)).to_have_css("cursor", "grabbing")
    # The button keeps the pointer while it is away from the thumbnail.
    page.mouse.move(700, 900, steps=5)
    expect(thumb(page, 0)).to_have_css("cursor", "grabbing")
    page.mouse.up()
    expect_no_drag(page)


def test_a9_the_tooltip_of_a_thumbnail_says_a_drag_moves_the_page(editor):
    """A9"""
    page = blatt(editor)
    expect(thumb(page, 0)).to_have_attribute("title", "Ziehen verschiebt die Seite")
    expect(thumb(page, 0)).to_contain_text("Seite 1")


def test_a9_the_tour_says_a_page_moves_by_dragging_its_thumbnail(editor):
    """A9"""
    page = blatt(editor)
    page.get_by_role("button", name="Rundgang", exact=True).click()
    tour = page.locator(".tour")
    # Some steps move on by themselves once a task is done, so each round reads the step first.
    for _ in range(15):
        if tour.locator("h2").text_content() == "Seiten und Vorlagen":
            break
        shown = tour.locator("small")
        before = shown.text_content()
        tour.locator(".primary").click()
        expect(shown).not_to_have_text(before)
    expect(tour.locator("h2")).to_have_text("Seiten und Vorlagen")
    expect(tour.locator("p")).to_contain_text("verschiebst du, indem du ihre Vorschau ziehst")


def test_i1_a_drag_resting_near_the_lower_edge_scrolls_the_panel_to_the_last_thumbnail(editor):
    """I1"""
    page = blatt(editor, NAMES)
    page.mouse.move(*centre(thumb(page, 0)))
    page.mouse.down()
    page.mouse.move(*bottom_edge(page), steps=10)
    scrolled_down(page)
    page.mouse.move(*half(page, 15, "right"), steps=5)
    page.mouse.up()
    expect_order(page, NAMES[1:] + "a")


def test_i1_a_drag_resting_near_the_upper_edge_scrolls_the_panel_to_the_top(editor):
    """I1"""
    page = blatt(editor, NAMES)
    page.evaluate(f"() => {{ {PANEL}.scrollTop = {PANEL}.scrollHeight; }}")
    page.mouse.move(*centre(thumb(page, 15)))
    page.mouse.down()
    page.mouse.move(*top_edge(page), steps=10)
    page.wait_for_function(
        f"() => {PANEL}.scrollTop < {PANEL}.scrollHeight - {PANEL}.clientHeight",
        timeout=5000,
    )
    page.wait_for_function(
        f"() => {FIRST}.getBoundingClientRect().top >= {PANEL}.getBoundingClientRect().top",
        timeout=5000,
    )
    page.mouse.move(*half(page, 0, "left"), steps=5)
    page.mouse.up()
    expect_order(page, "p" + NAMES[:15])


# Not strict: in CI's WebKit the panel does not scroll within 5 s in some shards (PR #510 one run
# of two, PR #513 three of three), and here 20 of 20 pass in WebKit and in Chromium, on master and
# on those branches.
@pytest.mark.xfail(
    BROWSER == "webkit", strict=False, reason="#512: the panel does not scroll in CI, now and then"
)
def test_i1_a_held_finger_near_the_lower_edge_scrolls_the_panel(editor):
    """I1"""
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in NAMES[1:]]
    page = editor(box("a", "text", TEXT), pages=rest, theme="", touch=True)
    drawer(page, "left")
    with finger(page, centre(thumb(page, 0))) as touch:
        # The hold is over once the thumbnail says so; the finger then moves on.
        expect(thumb(page, 0)).to_have_class(DRAG)
        touch("touchMove", bottom_edge(page))
        scrolled_down(page)
        touch("touchMove", half(page, 15, "right"))
    expect_order(page, NAMES[1:] + "a")
    expect_no_drag(page)


def test_i2_escape_in_a_drag_that_scrolled_the_panel_calls_it_off(editor):
    """I2"""
    page = blatt(editor, NAMES)
    page.mouse.move(*centre(thumb(page, 0)))
    page.mouse.down()
    page.mouse.move(*bottom_edge(page), steps=10)
    page.wait_for_function(f"{PANEL}.scrollTop > 0", timeout=5000)
    page.keyboard.press("Escape")
    expect_no_drag(page)
    stopped = frames(page)
    assert stopped < page.evaluate(f"{PANEL}.scrollHeight - {PANEL}.clientHeight")
    assert frames(page) == stopped
    page.mouse.up()
    expect_order(page, NAMES)
    expect_in_use(page, 0)
    page.keyboard.press("Control+z")
    expect_order(page, NAMES)


def test_i3_the_scroll_stops_when_the_pointer_leaves_the_edge_and_the_line_follows(editor):
    """I3"""
    page = blatt(editor, NAMES)
    page.mouse.move(*centre(thumb(page, 0)))
    page.mouse.down()
    page.mouse.move(*bottom_edge(page), steps=10)
    page.wait_for_function(f"{PANEL}.scrollTop > 0", timeout=5000)
    first_mark = page.locator(".pages .mark").get_attribute("data-to")
    # The line follows the thumbnails that scroll under the resting pointer.
    page.wait_for_function(
        f"() => document.querySelector('.pages .mark')?.dataset.to !== {first_mark!r}",
        timeout=5000,
    )
    box_ = page.locator("aside.left").bounding_box()
    page.mouse.move(box_["x"] + box_["width"] / 2, box_["y"] + box_["height"] / 2, steps=5)
    stopped = frames(page)
    assert frames(page) == stopped
    # It stopped on the way, not because the panel had come to its end.
    assert stopped < page.evaluate(f"{PANEL}.scrollHeight - {PANEL}.clientHeight")
    page.mouse.up()
    expect_no_drag(page)


def test_i4_the_moved_page_is_in_use_and_its_thumbnail_is_in_view_after_the_drop(editor):
    """I4"""
    page = blatt(editor, NAMES)
    page.mouse.move(*centre(thumb(page, 0)))
    page.mouse.down()
    page.mouse.move(*bottom_edge(page), steps=10)
    scrolled_down(page)
    page.mouse.move(*half(page, 15, "right"), steps=5)
    page.mouse.up()
    expect_order(page, NAMES[1:] + "a")
    expect_in_use(page, 15)
    assert in_view(page, LAST)
