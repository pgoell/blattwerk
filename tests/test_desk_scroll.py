"""A block dragged near the edge of the desk scrolls the desk to the next page (#806).

The desk is the scrolling area that holds the pages. Held near its top or bottom edge, a block
drag scrolls it, faster nearer the edge, and the block follows the pointer. The drop lands on the
page under the pointer, and the whole drag with its scroll is one undo step.
"""

from playwright.sync_api import expect
from test_fix_blatt import pdf_pages
from ui import TEXT, at, box, doc, reload, user

DESK = ".desk"
PAGE = '.sheet[data-page="{}"]'


def sheets(editor):
    """A sheet of three pages, the text "a" on the first."""
    return editor(box("a", "text", TEXT), pages=[{"blocks": []}, {"blocks": []}])


def desk_scroll(page):
    return page.evaluate(f"() => document.querySelector('{DESK}').scrollTop")


def near_bottom(page):
    """A point 5 px above the desk's lower edge, in its middle."""
    b = page.locator(DESK).bounding_box()
    return b["x"] + b["width"] / 2, b["y"] + b["height"] - 5


def under(page, point):
    """The page number under a point of the screen."""
    return page.evaluate(
        "([x, y]) => +document.elementFromPoint(x, y).closest('.sheet').dataset.page",
        list(point),
    )


def test_a_block_resting_near_the_lower_edge_of_the_desk_keeps_scrolling_it(editor):
    page = sheets(editor)
    start = desk_scroll(page)
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    page.mouse.move(*near_bottom(page), steps=10)
    # The pointer rests: no further move, yet the desk scrolls on to the next page.
    page.wait_for_function(
        f"() => document.querySelector('{DESK}').scrollTop > {start + 300}", timeout=5000
    )
    page.mouse.up()


def test_a_block_follows_the_pointer_while_the_desk_scrolls(editor):
    page = sheets(editor)
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    page.mouse.move(*near_bottom(page), steps=10)
    page.wait_for_function(f"() => document.querySelector('{DESK}').scrollTop > 300", timeout=5000)
    _, y = near_bottom(page)
    # The block is drawn a frame or two after the desk moved: wait until it lies under the pointer.
    page.wait_for_function(
        """([y]) => {
            const r = document.querySelector('.block[data-id="a"]').getBoundingClientRect();
            return Math.abs(r.top + r.height / 2 - y) < 3;
        }""",
        arg=[y],
        timeout=5000,
    )
    page.mouse.up()


def test_the_drop_after_the_scroll_lands_on_the_page_under_the_pointer(editor):
    page = sheets(editor)
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    page.mouse.move(*near_bottom(page), steps=10)
    page.wait_for_function(f"() => document.querySelector('{DESK}').scrollTop > 300", timeout=5000)
    target = under(page, near_bottom(page))
    page.mouse.up()
    expect(page.locator(PAGE.format(target)).locator('.block[data-id="a"]')).to_have_count(1)
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(0)


def test_the_drag_with_its_scroll_is_one_undo_step(editor):
    page = sheets(editor)
    style = at(page, "a").get_attribute("style")
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    page.mouse.move(*near_bottom(page), steps=10)
    page.wait_for_function(f"() => document.querySelector('{DESK}').scrollTop > 300", timeout=5000)
    page.mouse.up()
    expect(page.locator(PAGE.format(1)).locator('.block[data-id="a"]')).to_have_count(1)
    page.keyboard.press("Control+z")
    # Undo shows page 1 again: the block is back there, where it was, in one step.
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    expect(at(page, "a")).to_have_attribute("style", style)


def frames(page, n):
    """Waits n frames of the page."""
    page.evaluate(
        f"() => new Promise((done) => {{ let n = {n}; const f = () => (--n ? requestAnimationFrame(f) : done()); requestAnimationFrame(f); }})"
    )


def test_a_drag_held_still_after_the_scroll_keeps_its_page_until_the_drop(editor):
    """#805 with #806: page 1 scrolled out of view under a drag, the pointer back in the middle and
    held there: the page in use does not change under the drag, the block drops on the page under
    the pointer, and one undo puts it back on page 1."""
    page = sheets(editor)
    style = at(page, "a").get_attribute("style")
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    page.mouse.move(*near_bottom(page), steps=10)
    page.wait_for_function(
        """() => document.querySelector('.sheet[data-page="0"]').getBoundingClientRect().bottom
            < document.querySelector('.desk').getBoundingClientRect().top"""
    )
    b = page.locator(DESK).bounding_box()
    middle = (b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    page.mouse.move(*middle, steps=5)
    frames(page, 30)
    page.mouse.move(middle[0] + 3, middle[1] + 3)
    target = under(page, middle)
    page.mouse.up()
    assert target > 0
    expect(page.locator(PAGE.format(target)).locator('.block[data-id="a"]')).to_have_count(1)
    page.keyboard.press("Control+z")
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    expect(at(page, "a")).to_have_attribute("style", style)


def test_escape_calls_off_a_drag_that_scrolled_the_desk(editor):
    """Escape during the scroll: the block is back on page 1 where it was, and the drag left no
    step to take back."""
    page = sheets(editor)
    style = at(page, "a").get_attribute("style")
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    page.mouse.move(*near_bottom(page), steps=10)
    page.wait_for_function(f"() => document.querySelector('{DESK}').scrollTop > 300")
    page.keyboard.press("Escape")
    page.mouse.up()
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    expect(at(page, "a")).to_have_attribute("style", style)
    # Nothing is left to take back.
    page.keyboard.press("Control+z")
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    expect(at(page, "a")).to_have_attribute("style", style)


def test_a_block_moved_to_another_page_saves_reopens_and_prints_there(editor, server):
    """The save path of the move: the text dragged from page 1 to page 2 is saved on page 2 with its
    words and size, is there after a reload, prints on PDF page 2 and not on page 1, and one undo
    saves it back on page 1."""
    client = user()
    words = {**TEXT, "text": "Wanderwort"}
    page = editor(box("a", "text", words), pages=[{"blocks": []}, {"blocks": []}], client=client)
    before = doc(page, client)["pages"][0]["blocks"][0]
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    page.mouse.move(*near_bottom(page), steps=10)
    page.wait_for_function(
        """() => document.querySelector('.sheet[data-page="1"]').getBoundingClientRect().top
            < document.querySelector('.desk').getBoundingClientRect().top + 200"""
    )
    b = page.locator(DESK).bounding_box()
    page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=5)
    target = under(page, (b["x"] + b["width"] / 2, b["y"] + b["height"] / 2))
    page.mouse.up()
    assert target == 1
    expect(page.locator(PAGE.format(1)).locator('.block[data-id="a"]')).to_have_count(1)
    moved = doc(page, client)
    assert [len(p["blocks"]) for p in moved["pages"]] == [0, 1, 0]
    after = moved["pages"][1]["blocks"][0]
    assert (after["props"], after["w"], after["h"], after["type"]) == (
        before["props"],
        before["w"],
        before["h"],
        before["type"],
    )
    assert 0 <= after["y"] <= 297 - after["h"]
    # One undo saves it back on page 1, as it was; redo moves it again.
    page.keyboard.press("Control+z")
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    assert doc(page, client)["pages"][0]["blocks"] == [before]
    page.keyboard.press("Control+y")
    expect(page.locator(PAGE.format(1)).locator('.block[data-id="a"]')).to_have_count(1)
    assert doc(page, client)["pages"][1]["blocks"] == [after]
    reload(page, page.url)
    expect(page.locator(PAGE.format(1)).locator('.block[data-id="a"]')).to_have_text("Wanderwort")
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(0)
    printed = pdf_pages(server, client, page.url.rsplit("/", 1)[1])
    assert "Wanderwort" not in printed[0]
    assert "Wanderwort" in printed[1]


def test_away_from_the_edges_a_drag_does_not_scroll_the_desk(editor):
    page = sheets(editor)
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    b = page.locator(DESK).bounding_box()
    page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=10)
    # Twenty frames, in which a scroll at the edge would have gone 240 px.
    frames(page, 20)
    assert desk_scroll(page) == 0
    page.mouse.up()
