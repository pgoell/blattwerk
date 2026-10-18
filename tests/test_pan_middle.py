"""The middle button pans the desk as Space and a drag do, and does nothing else (#163)."""

import pytest
from playwright.sync_api import expect
from test_zoom import HAND, PANNING, expect_scroll, fit, roomy, scroll, settled
from ui import FIELD, TEXT, at, box, centre, expect_picked, pick

# The middle button's events, first to hear of them; read after, whether the app cancelled each one.
WATCH = """() => {
    window.__seen = [];
    for (const type of ["pointerdown", "mousedown", "mouseup", "auxclick"]) {
        addEventListener(type, (e) => e.button === 1 && window.__seen.push(e), true);
    }
}
"""
# The pointer's press is not cancelled, only the mouse events that Chrome would act on.
SEEN = """window.__seen.filter((e) => e.type !== 'pointerdown')
    .map((e) => [e.type, e.defaultPrevented])"""


def middle(page, start, across, down):
    """Holds the middle button on the point and drags it, then lets go."""
    left, top = scroll(page)
    page.mouse.move(*start)
    page.mouse.down(button="middle")
    page.mouse.move(start[0] + across, start[1] + down, steps=5)
    page.mouse.up(button="middle")
    expect_scroll(page, left - across, top - down)


def on_desk(page, name):
    """Where the block lies on the desk's own scroll, so a pan leaves it where it was."""
    box_ = at(page, name).bounding_box()
    return page.locator(".desk").evaluate(
        "(el, b) => [b.x - el.getBoundingClientRect().left + el.scrollLeft,"
        " b.y - el.getBoundingClientRect().top + el.scrollTop]",
        box_,
    )


@pytest.mark.parametrize("zoom", ["roomy", "fitted"])
def test_middle_drag_moves_the_desk(editor, zoom):
    """A1, A6"""
    page = editor(box("a", "text", TEXT))
    if zoom == "roomy":
        roomy(page)
    else:
        fit(page).click()
    corner = page.locator(".desk").bounding_box()
    start = (corner["x"] + 10, corner["y"] + 10)
    if zoom == "fitted":
        # The desk may not scroll at this zoom: a drag then changes nothing and breaks nothing.
        page.mouse.move(*start)
        page.mouse.down(button="middle")
        page.mouse.move(start[0] + 60, start[1] + 40, steps=5)
        expect(page.locator("main.editor")).to_have_class(PANNING)
        page.mouse.up(button="middle")
        expect(page.locator("main.editor")).not_to_have_class(PANNING)
        expect(page.locator(".block.sel")).to_have_count(0)
        return
    page.mouse.move(*start)
    page.mouse.down(button="middle")
    page.mouse.move(start[0] + 100, start[1] + 60, steps=5)
    expect(page.locator("main.editor")).to_have_class(PANNING)
    page.mouse.up(button="middle")
    expect(page.locator("main.editor")).not_to_have_class(PANNING)
    settled(page)
    expect_picked(page)


def test_middle_drag_pans_while_space_holds_the_hand(editor):
    """#163: the hand lies over the desk while Space is down, and a middle drag still pans."""
    page = editor(box("a", "text", TEXT))
    roomy(page)
    corner = page.locator(".desk").bounding_box()
    start = (corner["x"] + 10, corner["y"] + 10)
    # A click on the empty desk first, so nothing else has the focus.
    page.mouse.click(*start)
    page.evaluate(WATCH)
    page.keyboard.down("Space")
    expect(page.locator(HAND)).to_have_count(1)
    middle(page, start, 100, 60)
    seen = page.evaluate(SEEN)
    page.keyboard.up("Space")
    assert seen and all(cancelled for _, cancelled in seen), seen
    expect(page.locator("main.editor")).not_to_have_class(PANNING)


def test_middle_drag_pans_on_an_unpicked_block(editor):
    """A2: an unpicked block takes the press, and neither moves nor gets picked."""
    page = editor(box("a", "text", TEXT))
    roomy(page)
    before = on_desk(page, "a")
    middle(page, centre(at(page, "a")), 100, 60)
    expect_picked(page)
    assert on_desk(page, "a") == pytest.approx(before, abs=1)


def test_middle_drag_pans_on_a_picked_block(editor):
    """A2: the frame over a picked block hears the press first, and the block does not move."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    roomy(page)
    expect_picked(page, "a")
    before = on_desk(page, "a")
    middle(page, centre(at(page, "a")), 100, 60)
    expect_picked(page, "a")
    assert on_desk(page, "a") == pytest.approx(before, abs=1)


def test_middle_drag_has_no_autoscroll(editor):
    """A3: the middle button's events are cancelled, and the desk stops where the drag ends."""
    page = editor(box("a", "text", TEXT))
    roomy(page)
    page.evaluate(WATCH)
    corner = page.locator(".desk").bounding_box()
    start = (corner["x"] + 10, corner["y"] + 10)
    left, top = scroll(page)
    middle(page, start, 100, 60)
    settled(page)
    expect_scroll(page, left - 100, top - 60)
    page.wait_for_timeout(300)
    assert scroll(page) == [left - 100, top - 60]
    seen = page.evaluate(SEEN)
    assert seen and all(cancelled for _, cancelled in seen), seen


def test_middle_click_does_nothing_else(editor):
    """A4: a middle click picks nothing and leaves an open text as it is."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("du")
    expect(page.locator(FIELD)).to_have_text("du")
    page.evaluate(WATCH)
    point = centre(page.locator(".desk"))
    page.mouse.move(*point)
    page.mouse.down(button="middle")
    page.mouse.up(button="middle")
    settled(page)
    expect(page.locator(FIELD)).to_have_text("du")
    seen = page.evaluate(SEEN)
    assert seen and all(cancelled for _, cancelled in seen), seen
    expect(page.locator("main.editor")).not_to_have_class(PANNING)


def test_middle_drag_while_typing_adds_no_undo_step(editor):
    """I1: a middle drag with a text open leaves it open, and the undo step stays the edit's."""
    page = editor(box("a", "text", TEXT))
    roomy(page)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("du")
    expect(page.locator(FIELD)).to_have_text("du")
    middle(page, centre(page.locator(".desk")), 80, 50)
    expect(page.locator(FIELD)).to_have_text("du")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Escape")
    expect(page.get_by_label("Rückgängig")).to_be_enabled()
    page.keyboard.press("Control+z")
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    expect(at(page, "a")).to_contain_text("Hallo")


def test_middle_drag_sets_panning_while_held(editor):
    """I2: the editor shows the grab cursor for the whole drag."""
    page = editor(box("a", "text", TEXT))
    roomy(page)
    main = page.locator("main.editor")
    corner = page.locator(".desk").bounding_box()
    page.mouse.move(corner["x"] + 10, corner["y"] + 10)
    page.mouse.down(button="middle")
    expect(main).to_have_class(PANNING)
    page.mouse.move(corner["x"] + 40, corner["y"] + 30, steps=5)
    expect(main).to_have_class(PANNING)
    page.mouse.up(button="middle")
    expect(main).not_to_have_class(PANNING)


def test_left_drag_still_moves_a_picked_block(editor):
    """A5: the left button moves the picked block, and a right press leaves the desk alone."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    roomy(page)
    left, top = scroll(page)
    before = on_desk(page, "a")
    point = centre(at(page, "a"))
    page.mouse.move(*point)
    page.mouse.down()
    page.mouse.move(point[0] + 60, point[1] + 30, steps=5)
    page.mouse.up()
    expect_picked(page, "a")
    assert on_desk(page, "a") != pytest.approx(before, abs=1)
    assert scroll(page) == [left, top]
