"""A block from the server that comes back while the mouse holds another one."""

import pytest
from playwright.sync_api import expect
from test_clipboard import button
from test_escape import hold, opened
from test_pages import PICKED, PICKER
from ui import at

# What asks the server for a block, and the request that waits.
SOURCES = {
    "maths": ("**/api/maths", lambda page: button(page, "Rechnen").click()),
    "picture": ("**/api/uploads", lambda page: page.locator(PICKER).set_input_files(PICKED)),
}
WAYS = ("move", "resize", "turn")
STYLE = "document.querySelector('.sheet [data-id=a]').style.cssText"


def spot(page):
    """Where the text "a" lies, how large it is and how it is turned."""
    return page.evaluate(STYLE)


def expect_spot(page, was, same=True):
    page.wait_for_function(f"([was, same]) => ({STYLE} === was) === same", arg=[was, same])


def blocks(page):
    return page.locator(".sheet .block[data-id]")


def asked(editor, what):
    """The editor with the text "a" selected and a block asked for. Gives the way to let it come."""
    page = opened(editor, "text")
    url, ask = SOURCES[what]
    waiting = []
    page.route(url, lambda route: waiting.append(route))
    with page.expect_request(url):
        ask(page)

    def come():
        # While the mouse is down nothing on the page shows that the answer is here, so its end on
        # the line tells. The moves that follow give the editor the time to read it.
        with page.expect_response(url) as answer:
            waiting.pop().continue_()
        answer.value.finished()

    return page, come


def dragged(editor, what, way):
    """Lets the block come back in the middle of a drag of "a", with the mouse still down.

    Gives the page, how "a" lay before the drag and how it lies now.
    """
    page, come = asked(editor, what)
    was = spot(page)
    on = hold(page, way, "text", False)
    expect_spot(page, was, same=False)
    mid = spot(page)
    come()
    page.mouse.move(*on, steps=5)
    expect_spot(page, mid, same=False)
    return page, was, spot(page)


def expect_landed(page):
    """Waits until the one new block is there, and selected alone."""
    expect(blocks(page)).to_have_count(2)
    expect(page.locator(".block.sel")).to_have_count(1)
    expect(at(page, "a")).not_to_have_class("block sel")


@pytest.mark.parametrize("way", WAYS)
@pytest.mark.parametrize("what", SOURCES)
def test_a_block_that_comes_back_during_a_drag_does_not_end_it(editor, what, way):
    """#201"""
    page, _, end = dragged(editor, what, way)
    # The new block waits for the mouse to come up.
    expect(blocks(page)).to_have_count(1)
    page.mouse.up()
    expect_landed(page)
    assert spot(page) == end


@pytest.mark.parametrize("way", WAYS)
def test_the_drag_and_the_block_that_came_back_in_it_are_two_undo_steps(editor, way):
    """#201"""
    page, was, end = dragged(editor, "maths", way)
    page.mouse.up()
    expect_landed(page)
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(1)
    assert spot(page) == end
    page.keyboard.press("Control+z")
    expect_spot(page, was)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    page.keyboard.press("Control+y")
    expect_spot(page, end)
    expect(blocks(page)).to_have_count(1)
    page.keyboard.press("Control+y")
    expect(blocks(page)).to_have_count(2)
    assert spot(page) == end


@pytest.mark.parametrize("way", WAYS)
@pytest.mark.parametrize("first", ["answer", "escape"])
@pytest.mark.parametrize("what", SOURCES)
def test_escape_calls_the_whole_drag_off_and_the_block_lands_once(editor, what, first, way):
    """#201: with the answer before Escape, or after it while the mouse is still down."""
    if first == "answer":
        page, was, _ = dragged(editor, what, way)
        page.keyboard.press("Escape")
    else:
        page, come = asked(editor, what)
        was = spot(page)
        hold(page, way, "text", False)
        expect_spot(page, was, same=False)
        page.keyboard.press("Escape")
        come()
    expect_spot(page, was)
    x, y = page.viewport_size["width"] / 2, page.viewport_size["height"] / 2
    page.mouse.move(x, y, steps=5)
    assert spot(page) == was
    expect(blocks(page)).to_have_count(1)
    page.mouse.up()
    expect_landed(page)
    assert spot(page) == was
    # The next press and release bring no second one, and the new block is the only undo step.
    page.mouse.click(x, y)
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(1)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    assert spot(page) == was
