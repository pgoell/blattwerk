"""Picking a block that reaches the page's edge does not make the desk scroll (issue 418)."""

from playwright.sync_api import expect
from ui import RECT, box, centre, drag, pick, saved, user


def desk_size(page):
    return page.locator(".desk").evaluate("el => [el.scrollWidth, el.scrollHeight]")


def test_a_block_at_the_right_edge_does_not_widen_the_desk_when_picked(editor):
    """Asked: a block with x 0 and w 210, edge to edge, picked: the desk's scrollWidth stays."""
    page = editor(box("a", "shape", RECT, x=0, y=80, w=210, h=30))
    before = desk_size(page)
    pick(page, "a")
    expect(page.locator(".moveable-control.moveable-e")).to_be_visible()
    assert desk_size(page)[0] == before[0], f"scrollWidth {before[0]} -> {desk_size(page)[0]}"


def test_a_block_at_the_foot_does_not_grow_the_desk_when_picked(editor):
    """Implied: a block whose foot is the page's foot, picked: the desk's scrollHeight stays."""
    page = editor(box("a", "shape", RECT, x=0, y=247, w=210, h=50))
    before = desk_size(page)
    pick(page, "a")
    expect(page.locator(".moveable-control.moveable-s")).to_be_visible()
    assert desk_size(page)[1] == before[1], f"scrollHeight {before[1]} -> {desk_size(page)[1]}"


def test_the_right_edge_handle_of_an_edge_block_still_drags(editor):
    """Implied: the right edge's handle of a block at x 0, w 210 is grabbable and shrinks it."""
    client = user()
    page = editor(box("a", "shape", RECT, x=0, y=80, w=210, h=30), client=client)
    pick(page, "a")
    x, y = centre(page.locator(".moveable-control.moveable-e"))
    drag(page, (x, y), (x - 40, y))
    (a,) = saved(page, client)
    assert a["w"] < 210
    assert a["x"] == 0
