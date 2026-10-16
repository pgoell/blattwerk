"""A finger held still opens the editor's menu when it lifts. A drag or an open text opens none."""

import pytest
from playwright.sync_api import expect
from test_menu import HELD, kept, menu, props, texts, watch
from test_order import boxes
from test_pages import three
from ui import at, box, centre, finger, jitter, outlast, thumb, user


@pytest.mark.parametrize("kind", HELD)
def test_a_finger_held_still_on_a_block_opens_the_menu_on_the_lift(editor, kind):
    """A1"""
    client = user()
    if kind == "group":
        blocks = boxes(*"abc", grouped="ab")
    else:
        blocks = [box("a", "shape" if kind == "line" else kind, props(client, kind))]
    page = editor(*blocks, client=client, touch=True)
    start = centre(at(page, "a"))
    with finger(page, start):
        outlast(page)
        expect(menu(page)).to_have_count(0)
    expect(menu(page)).to_be_visible()


@pytest.mark.parametrize("kind", HELD)
def test_a_finger_held_then_moved_away_opens_no_menu(editor, kind):
    """A2"""
    client = user()
    if kind == "group":
        blocks = boxes(*"abc", grouped="ab")
    else:
        blocks = [box("a", "shape" if kind == "line" else kind, props(client, kind))]
    page = editor(*blocks, client=client, touch=True)
    start = centre(at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (3, 0), (40, 0))
        outlast(page)
    expect(menu(page)).to_have_count(0)


def test_a_finger_held_still_in_an_open_text_gets_no_menu_and_the_browser_keeps_its_own(editor):
    """A3"""
    page = editor(*texts("a"), touch=True)
    at(page, "a").dblclick()
    field = page.locator(".ProseMirror").first
    expect(field).to_be_visible()
    watch(page)
    with finger(page, centre(field)):
        outlast(page)
    expect(menu(page)).to_have_count(0)
    field.dispatch_event("contextmenu", {"bubbles": True, "cancelable": True})
    assert not kept(page)


def test_a_finger_held_still_on_a_thumbnail_opens_the_pages_menu(editor):
    """A4"""
    page = three(editor)
    with finger(page, centre(thumb(page, 2))):
        outlast(page)
    expect(menu(page)).to_be_visible()


def test_a_finger_held_on_a_thumbnail_then_moved_away_opens_no_menu(editor):
    """A4, a drag"""
    page = three(editor)
    start = centre(thumb(page, 2))
    with finger(page, start):
        jitter(thumb(page, 2), start, (40, 0))
        outlast(page)
    expect(menu(page)).to_have_count(0)


def test_a_finger_held_still_on_the_empty_page_opens_the_menu_there(editor):
    """I5, and the menu lands where the finger lifts"""
    page = editor(*texts("a"), touch=True)
    sheet = page.locator(".sheet").first.bounding_box()
    start = (sheet["x"] + sheet["width"] / 2, sheet["y"] + sheet["height"] * 0.6)
    with finger(page, start):
        outlast(page)
    expect(menu(page)).to_be_visible()
    shown = menu(page).bounding_box()
    assert abs(shown["x"] - start[0]) < 30
