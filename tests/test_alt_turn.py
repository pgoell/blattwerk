"""Alt+Left and Alt+Right turn the picked blocks 15 degrees, as in PowerPoint. Asked #109."""

import math

import pytest
from playwright.sync_api import expect
from test_group_turn import G, group, hull, kinds, lie, pair
from ui import (
    LINE,
    RECT,
    TABLE,
    TEXT,
    angle,
    at,
    box,
    expect_picked,
    pick,
    saved,
    user,
)

# The types of test_every_type_goes_with_its_group that turn, a table and a line on its own not.
TURNABLE = ["text", "shape", "picture", "symbol", "ruling", "maths"]
# Records each Alt arrow that reaches the window, and whether a handler before it had prevented it.
RECORD = """() => {
  window.__alt = [];
  window.addEventListener("keydown", (e) => {
    if (e.altKey && e.key.startsWith("Arrow")) window.__alt.push([e.key, e.defaultPrevented]);
  });
}"""


def turned_about(point, middle, degrees):
    """Where a point lies after a turn clockwise about the middle, on a screen with y going down."""
    r = math.radians(degrees)
    dx, dy = point[0] - middle[0], point[1] - middle[1]
    return middle[0] + dx * math.cos(r) - dy * math.sin(r), middle[1] + dx * math.sin(
        r
    ) + dy * math.cos(r)


def centre(b):
    return b["x"] + b["w"] / 2, b["y"] + b["h"] / 2


def record(page):
    page.evaluate(RECORD)


def seen(page):
    """Each recorded Alt key, as [key, prevented]."""
    return page.evaluate("window.__alt")


@pytest.mark.parametrize("name", TURNABLE)
def test_alt_right_turns_every_type_by_15_degrees(editor, name):
    client = user()
    kind, props = kinds(client)[name]
    page = editor(box("k", kind, props, x=60, y=60, w=60, h=40), client=client)
    pick(page, "k")
    page.keyboard.press("Alt+ArrowRight")
    assert saved(page, client)[0]["angle"] == 15
    page.keyboard.press("Alt+ArrowLeft")
    page.keyboard.press("Alt+ArrowLeft")
    assert saved(page, client)[0]["angle"] == 345


def test_alt_arrows_turn_a_group_as_one(editor):
    client = user()
    first = pair()
    page = editor(*first, client=client)
    group(page, "a", "b")
    page.keyboard.press("Alt+ArrowRight")
    by_id = {b["id"]: b for b in saved(page, client)}
    # The blocks went round the middle of the group's box, 15 degrees clockwise.
    middle = (sum(hull(first)[0::2]) / 2, sum(hull(first)[1::2]) / 2)
    for b in first:
        x, y = turned_about(centre(b), middle, 15)
        got = by_id[b["id"]]
        assert (got["x"] + got["w"] / 2, got["y"] + got["h"] / 2) == pytest.approx((x, y), abs=0.01)
        assert got["angle"] == 15


def test_alt_arrows_turn_loose_blocks_each_on_its_spot(editor):
    client = user()
    a = box("a", "shape", RECT, x=30, y=60, w=40, h=30)
    b = box("b", "shape", RECT, z=2, x=120, y=120, w=50, h=20)
    page = editor(a, b, client=client)
    pick(page, "a", "b")
    page.keyboard.press("Alt+ArrowRight")
    got = {x["id"]: x for x in saved(page, client)}
    assert lie([got["a"]]) == lie([{**a, "angle": 15}])
    assert lie([got["b"]]) == lie([{**b, "angle": 15}])


def test_no_turn_while_a_text_is_written_in(editor):
    client = user()
    page = editor(box("t", "text", TEXT, x=60, y=60, w=60, h=40), client=client)
    pick(page, "t")
    page.keyboard.press("Enter")
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.type("x")
    expect(at(page, "t")).to_contain_text("x")
    assert saved(page, client)[0].get("angle", 0) == 0


def test_no_turn_while_a_panel_number_field_has_the_focus(editor):
    client = user()
    page = editor(box("a", "shape", RECT, x=60, y=60, w=60, h=40), client=client)
    pick(page, "a")
    page.locator("input.mm").first.focus()
    page.keyboard.press("Alt+ArrowRight")
    assert angle(page, "a") == 0


def test_alt_arrows_keep_the_browser_back(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=60, y=60, w=60, h=40),
        box("t", "text", TEXT, z=2, x=120, y=60, w=60, h=40),
        client=client,
    )
    address = page.url
    record(page)
    pick(page, "a")
    page.keyboard.press("Alt+ArrowLeft")
    page.keyboard.press("Alt+ArrowRight")
    assert seen(page) == [["ArrowLeft", True], ["ArrowRight", True]]
    assert page.url == address
    # In a text the keys stay the browser's.
    page.keyboard.press("Escape")
    pick(page, "t")
    page.keyboard.press("Enter")
    page.keyboard.press("Alt+ArrowRight")
    assert seen(page)[-1] == ["ArrowRight", False]


def test_each_alt_press_is_one_undo_step(editor):
    client = user()
    page = editor(box("k", "shape", RECT, x=60, y=60, w=60, h=40), client=client)
    pick(page, "k")
    for _ in range(3):
        page.keyboard.press("Alt+ArrowRight")
    assert saved(page, client)[0]["angle"] == 45
    page.keyboard.press("Control+z")
    assert saved(page, client)[0]["angle"] == 30


@pytest.mark.parametrize("name", ["locked", "table", "line"])
def test_locked_table_and_lone_line_do_not_turn(editor, name):
    client = user()
    kind, props, more = {
        "locked": ("shape", RECT, {"locked": True}),
        "table": ("table", TABLE, {}),
        "line": ("shape", LINE, {}),
    }[name]
    target = box("x", kind, props, x=30, y=60, w=60, h=40, **more)
    sentinel = box("s", "shape", RECT, z=3, x=120, y=120, w=40, h=20)
    page = editor(target, sentinel, client=client)
    record(page)
    pick(page, "x")
    page.keyboard.press("Alt+ArrowRight")
    assert seen(page) == [["ArrowRight", True]]
    # A free block picked after it shows the sheet was saved, and the blocks have not moved.
    pick(page, "s")
    page.keyboard.press("Alt+ArrowRight")
    got = {b["id"]: b for b in saved(page, client)}
    assert lie([got["x"]]) == lie([target])
    assert got["s"]["angle"] == 15


def test_a_block_picked_out_of_its_group_turns_on_its_spot(editor):
    client = user()
    a, b = pair()
    page = editor(a, b, client=client)
    group(page, "a", "b")
    # A second click picks the block alone. The frame around the picked group lies over it.
    at(page, "b").click(force=True)
    expect_picked(page, "b")
    page.keyboard.press("Alt+ArrowRight")
    assert lie(saved(page, client)) == lie([a, {**b, "angle": 15}])


def test_a_group_with_a_line_turns_the_line_too(editor):
    client = user()
    line = box("l", "shape", LINE, x=30, y=60, w=60, h=40, **G)
    rect = box("r", "shape", RECT, z=2, x=110, y=60, w=40, h=40, **G)
    page = editor(line, rect, client=client)
    group(page, "l", "r")
    page.keyboard.press("Alt+ArrowRight")
    got = {b["id"]: b for b in saved(page, client)}
    assert got["r"]["angle"] == 15
    # A line has no angle: its two ends went 15 degrees round the middle of the group's box.
    assert "angle" not in got["l"]
    middle = (90, 80)
    x, y, w, h = (got["l"][side] for side in "xywh")
    across = got["l"]["props"]["from"] in ("ne", "sw")
    ends = [(x, y + h), (x + w, y)] if across else [(x, y), (x + w, y + h)]
    wanted = [turned_about(p, middle, 15) for p in ((30, 60), (90, 100))]
    for got_end, want in zip(sorted(ends), sorted(wanted), strict=True):
        assert got_end == pytest.approx(want, abs=0.02)


def test_a_turn_past_360_degrees_wraps_to_small_angles(editor):
    client = user()
    page = editor(box("k", "shape", RECT, angle=350, x=60, y=60, w=60, h=40), client=client)
    pick(page, "k")
    page.keyboard.press("Alt+ArrowRight")
    assert saved(page, client)[0]["angle"] == 5
