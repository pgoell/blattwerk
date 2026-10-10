"""A click on the handle that turns is a click on the block under it, in Chromium on the built
frontend."""

import pytest
from playwright.sync_api import expect
from ui import (
    RECT,
    RULING,
    TEXT,
    angle,
    arc,
    at,
    box,
    centre,
    drag,
    expect_picked,
    maths,
    picture,
    upload,
    user,
)

# Moveable's handle above the selection, the one that turns it.
HANDLE = ".moveable-rotation-control"
# Every type of block that has the handle.
KINDS = ["text", "shape", "picture", "symbol", "ruling", "maths", "points", "group"]
# A block 60 by 20 mm in the middle of the page, with room to turn in.
PLACE = {"x": 75, "y": 80, "w": 60, "h": 20}
# How far a hand moves the mouse between the press and the lift of a click, in px.
WOBBLES = [(0, 0), (1, 1), (-2, 1)]


def under(editor, kind, *above):
    """The editor on a block of the kind, "a", picked, and the blocks `above`.

    A group is "a" and "b".
    """
    client = user()
    if kind == "group":
        mate = {**PLACE, "x": 110, "w": 25}
        blocks = [
            box("a", "shape", RECT, **{**PLACE, "w": 25}, group=["g"]),
            box("b", "shape", RECT, **mate, group=["g"]),
        ]
    elif kind == "picture":
        blocks = [{**picture(upload(client)), "id": "a", **PLACE}]
    elif kind == "maths":
        blocks = [box("a", "maths", maths(client), **PLACE)]
    else:
        props = {
            "text": TEXT,
            "shape": RECT,
            "symbol": {"code": "2B50"},
            "ruling": RULING,
            "points": {"max": 10},
        }
        blocks = [box("a", kind, props[kind], **PLACE)]
    page = editor(*blocks, *above, client=client)
    at(page, "a").click()
    expect_picked(page, *names(kind))
    return page


def names(kind):
    return ["a", "b"] if kind == "group" else ["a"]


def heading(**more):
    """A text across the page above the block, "top": the handle stands on it."""
    return box("top", "text", TEXT, z=5, x=15, y=50, w=180, h=25, **more)


def handle(page, over=None):
    """Where the handle stands: on the block `over`, or on the empty paper."""
    x, y = centre(page.locator(HANDLE))
    found = "document.elementsFromPoint(x, y).find((el) => el.matches('.block'))?.dataset.id"
    assert page.evaluate(f"([x, y]) => {found}", [x, y]) == over
    return x, y


def click(page, spot, by=(0, 0), keys=()):
    """A click of the mouse that moves by so much between the press and the lift."""
    drag(page, spot, (spot[0] + by[0], spot[1] + by[1]), keys=keys)


def expect_no_step(page):
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_a_click_on_a_heading_under_the_handle_picks_it(editor):
    page = editor()
    page.set_viewport_size({"width": 1280, "height": 1024})
    bar = page.get_by_role("toolbar", name="Einfügen")
    bar.get_by_label("Überschrift", exact=True).click()
    page.keyboard.type("Seite eins")
    page.keyboard.press("Escape")
    bar.get_by_label("Text", exact=True).click()
    page.keyboard.type("Hallo")
    page.keyboard.press("Escape")
    y = page.get_by_label("Y", exact=True)
    y.fill("35")
    y.press("Enter")
    top, text = (page.locator(".block[data-id]", has_text=words) for words in ("Seite", "Hallo"))
    page.locator(".sheet").first.click(position={"x": 5, "y": 5})
    expect_picked(page)
    text.click()
    expect(text).to_have_class("block sel")
    # The handle of the text stands on the middle of the heading, and takes the press.
    x, y = centre(top)
    assert page.evaluate(f"document.elementFromPoint({x}, {y}).matches('{HANDLE}')")
    page.mouse.click(x, y)
    expect(top).to_have_class("block sel")
    expect(text).to_have_class("block")
    assert "rotate" not in text.evaluate("el => el.style.transform")


@pytest.mark.parametrize("by", WOBBLES, ids=["still", "one", "two"])
@pytest.mark.parametrize("kind", KINDS)
def test_a_click_on_the_handle_picks_the_block_under_it(editor, kind, by):
    page = under(editor, kind, heading())
    click(page, handle(page, "top"), by)
    expect_picked(page, "top")
    # The wobble turned nothing, and left no step to undo.
    for name in names(kind):
        assert angle(page, name) == 0
    expect_no_step(page)


@pytest.mark.parametrize("kind", KINDS)
def test_a_drag_by_the_handle_over_a_block_still_turns(editor, kind):
    page = under(editor, kind, heading())
    first, *rest = (centre(at(page, name)) for name in names(kind))
    about = ((first[0] + rest[0][0]) / 2, first[1]) if rest else first
    drag(page, *arc(handle(page, "top"), about, 90))
    expect_picked(page, *names(kind))
    for name in names(kind):
        assert abs(angle(page, name) - 90) <= 3
    # The whole drag was one step.
    page.keyboard.press("Control+z")
    for name in names(kind):
        assert angle(page, name) == 0
    expect_no_step(page)


def test_shift_and_a_click_on_the_handle_adds_the_block_under_it(editor):
    page = under(editor, "shape", heading())
    click(page, handle(page, "top"), keys=["Shift"])
    expect_picked(page, "a", "top")
    assert angle(page, "a") == 0
    expect_no_step(page)


@pytest.mark.parametrize("by", WOBBLES, ids=["still", "one", "two"])
@pytest.mark.parametrize("kind", ["shape", "group"])
def test_a_click_on_the_handle_over_empty_paper_changes_nothing(editor, kind, by):
    page = under(editor, kind)
    click(page, handle(page), by)
    expect_picked(page, *names(kind))
    for name in names(kind):
        assert angle(page, name) == 0
    expect_no_step(page)


def test_a_click_on_the_handle_over_a_block_of_a_group_picks_the_group(editor):
    mate = box("mate", "shape", RECT, z=6, x=15, y=20, w=30, h=10, group=["h"])
    page = under(editor, "shape", heading(group=["h"]), mate)
    click(page, handle(page, "top"))
    expect_picked(page, "top", "mate")
