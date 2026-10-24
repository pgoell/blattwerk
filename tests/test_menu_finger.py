"""A finger on a block: the browser's menu stays away, a hold selects several, and a drag snaps.

The helpers live in test_menu.py.
"""

import pytest
from playwright.sync_api import expect
from test_menu import (
    HELD,
    kept,
    menu,
    props,
    several,
    spot,
    texts,
    watch,
)
from test_order import boxes
from ui import (
    RECT,
    apart,
    at,
    box,
    centre,
    expect_picked,
    finger,
    hold_drag,
    jitter,
    outlast,
    saved,
    user,
)


def test_a_finger_on_a_block_keeps_the_browsers_own_menu_away(editor):
    """A held finger on a block: the browser's own menu is prevented. The editor's opens on lift."""
    page = editor(*texts("a"), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    watch(page)
    at(page, "a").dispatch_event("contextmenu", {"bubbles": True, "cancelable": True})
    assert kept(page)
    expect(menu(page)).to_have_count(0)


@pytest.mark.parametrize("kind", HELD)
def test_a_jittering_finger_held_on_a_block_starts_selecting_several(editor, kind):
    """B3"""
    client = user()
    if kind == "group":
        blocks = boxes(*"abc", grouped="ab")
    else:
        blocks = [box("a", "shape" if kind == "line" else kind, props(client, kind))]
    page = editor(*blocks, client=client, touch=True)
    expect(several(page)).to_have_attribute("aria-pressed", "false")
    # The block is selected with the finger still down: a tap would select it on the way up.
    by = ((3, 0), (0, 4), (-6, -7))
    hold_drag(page, at(page, "a"), centre(at(page, "a")), by=by, shows="sel")
    expect(several(page)).to_have_attribute("aria-pressed", "true")
    expect_picked(page, *("ab" if kind == "group" else "a"))


@pytest.mark.parametrize("kind", [*HELD, "several"])
def test_a_jittering_finger_held_on_a_selected_block_moves_no_block(editor, kind):
    """#178"""
    client = user()
    if kind in ("group", "several"):
        # Apart: a tap reaches each block, and no block or middle of the page lies near enough to
        # snap to. A snap moves the blocks before the finger has left (#261).
        blocks = apart(*boxes(*"abc", grouped="ab" if kind == "group" else ""))
    else:
        blocks = [box("a", "shape" if kind == "line" else kind, props(client, kind))]
    page = editor(*blocks, client=client, touch=True)
    names = "ab" if len(blocks) > 1 else "a"
    if kind == "several":
        several(page).tap()
    for name in names if kind == "several" else "a":
        at(page, name).tap()
    expect_picked(page, *names)
    before = [spot(page, name) for name in names]
    # A table's middle is the bar between its columns, which drags no block.
    start = centre(at(page, "a").locator("[data-cell]").first if kind == "table" else at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (3, 0), (3, 9))
        outlast(page)
        assert [spot(page, name) for name in names] == before
    assert [spot(page, name) for name in names] == before
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()


# Px to the mm of the sheet, by the window.
SCALE = {}
# How far above `a` its neighbour ends, in px: outside the slop, and a snap reaches it from 9 px.
GAP = 13


def beside(editor, client, kind, touch=True):
    """Selects `a`, or `a` and `b`, just below a neighbour to snap to. Gives the page, the selected
    names and where the finger comes down on `a`."""
    if touch not in SCALE:
        # The layout says how large the sheet is, and a snap counts in px: measure, then lay out.
        SCALE[touch] = editor(touch=touch).locator(".sheet").first.bounding_box()["width"] / 210
    y = round(40 + GAP / SCALE[touch], 2)
    neighbour = {**box("c", "shape", RECT, z=3), "y": 20}
    if kind in ("group", "several"):
        # 70 mm apart: a tap reaches each block past the other's handles.
        pair = boxes(*"ab", grouped="ab" if kind == "group" else "")
        mine = [{**b, "y": y + 70 * i} for i, b in enumerate(pair)]
    else:
        mine = [{**box("a", "shape" if kind == "line" else kind, props(client, kind)), "y": y}]
    page = editor(*mine, neighbour, client=client, touch=touch)
    names = "ab"[: len(mine)]
    if kind == "several":
        several(page).tap()
    for name in names if kind == "several" else "a":
        at(page, name).tap()
    expect_picked(page, *names)
    at(page, "a").scroll_into_view_if_needed()
    # A table's middle is the bar between its columns, which drags no block.
    on = at(page, "a").locator("[data-cell]").first if kind == "table" else at(page, "a")
    return page, names, centre(on)


@pytest.mark.parametrize("touch", [True, "landscape"])
@pytest.mark.parametrize("kind", [*HELD, "several"])
def test_a_jittering_finger_held_beside_a_snap_line_moves_no_block(editor, kind, touch):
    """#261"""
    client = user()
    page, names, start = beside(editor, client, kind, touch)
    before = [spot(page, name) for name in names]
    with finger(page, start):
        jitter(at(page, "a"), start, (3, 0), (3, -9))
        outlast(page)
        assert [spot(page, name) for name in names] == before
    assert [spot(page, name) for name in names] == before
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()
    assert saved(page, client)[0]["y"] == round(40 + GAP / SCALE[touch], 2)


@pytest.mark.parametrize("kind", ["shape", "group", "several"])
def test_a_finger_that_leaves_where_it_came_down_snaps_what_it_drags(editor, kind):
    """#261"""
    client = user()
    page, names, start = beside(editor, client, kind)
    with finger(page, start):
        jitter(at(page, "a"), start, (3, -14))
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()
    # Onto the neighbour's lower edge, and the second block by as much.
    assert [b["y"] for b in saved(page, client)[: len(names)]] == [40, 110][: len(names)]


@pytest.mark.parametrize("kind", HELD)
def test_a_finger_that_snaps_before_it_leaves_takes_the_block_along_in_one_step(editor, kind):
    """#268: A6, I6"""
    client = user()
    page, names, start = beside(editor, client, kind)
    # The snap takes hold while the finger has not left, and holds as it leaves: Moveable says so
    # once only, before the block may move.
    with finger(page, start):
        jitter(at(page, "a"), start, (3, -9), (3, -14), (3, -15))
    undo = page.get_by_role("button", name="Rückgängig")
    expect(undo).to_be_enabled()
    # Onto the neighbour's lower edge, and a group's second block by as much.
    assert [b["y"] for b in saved(page, client)[: len(names)]] == [40, 110][: len(names)]
    undo.tap()
    expect(undo).to_be_disabled()
    y = round(40 + GAP / SCALE[True], 2)
    assert [b["y"] for b in saved(page, client)[: len(names)]] == [y, y + 70][: len(names)]


def test_a_finger_that_leaves_where_it_came_down_drags_the_selected_block(editor):
    """#178"""
    page = editor(*texts("a"), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    before, start = spot(page, "a"), centre(at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (0, 9), (0, 14))
        far = spot(page, "a")
        assert far[0] == before[0] and far[1] != before[1]
        # Once it drags, the block follows the finger back to where it came down too.
        jitter(at(page, "a"), start, (0, 5))
        assert spot(page, "a") not in (before, far)
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()


def test_a_touch_the_browser_cancels_starts_no_selecting_of_several(editor):
    """#179, #225"""
    page = editor(*texts("a"), touch=True)
    with finger(page, centre(at(page, "a"))) as touch:
        touch("touchCancel")
        outlast(page)
        expect(several(page)).to_have_attribute("aria-pressed", "false")
        expect_picked(page)
        # The finger comes down again, and its lift is a tap. The centre is read now, not before
        # the wait: the desk can take its last size in that time, and the old point then lies on
        # the page and on no block (#225). A hold that fires in a slow lift does select the block.
        point = centre(at(page, "a"))
        touch("touchStart", point)
    try:
        expect_picked(page, "a")
    except AssertionError as e:
        raise AssertionError(f"DIAG {page.evaluate(STATE, list(point))}") from e


STATE = """([x, y]) => ({
    several: document.querySelector('[aria-pressed]')?.outerHTML.slice(0, 160),
    pressed: [...document.querySelectorAll('[aria-pressed=true]')].map((b) => b.ariaLabel),
    block: document.querySelector('.block')?.className,
    hit: document.elementsFromPoint(x, y).map((el) => el.tagName + '.' + el.className).slice(0, 6),
    active: document.activeElement?.tagName + '.' + document.activeElement?.className,
    fingers: !!window.fingers,
    main: document.querySelector('main')?.className,
    dialog: !!document.querySelector('dialog[open]'),
})"""


def test_a_tap_after_a_hold_the_browser_cancelled_selects_one_more(editor):
    """#179"""
    page = editor(*apart(*texts("a", "b")), touch=True)
    start = centre(at(page, "a"))
    with finger(page, start) as touch:
        expect(several(page)).to_have_attribute("aria-pressed", "true")
        touch("touchCancel")
        touch("touchStart", centre(at(page, "b")))
    expect_picked(page, "a", "b")


def test_a_swipe_over_a_block_starts_no_selecting_of_several(editor):
    """I7"""
    page = editor(*texts("a"), touch=True)
    start = centre(at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (14, 0))
        outlast(page)
        expect(several(page)).to_have_attribute("aria-pressed", "false")
        expect_picked(page)
