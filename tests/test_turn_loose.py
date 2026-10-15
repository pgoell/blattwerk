"""Turning several picked blocks by the handle: loose blocks each about their own centre."""

import math

import pytest
from pixels import over, screen_and_print
from playwright.sync_api import expect
from test_alt_turn import turned_about
from test_group_turn import group, hull
from test_rotate import HANDLE, turn
from ui import LINE, RECT, angle, arc, at, box, centre, expect_picked, pick, saved, user


def test_the_handle_turns_loose_blocks_each_on_its_spot(editor):
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20),
        box("b", "shape", RECT, z=2, x=100, y=80, w=30, h=20),
    )
    pick(page, "a", "b")
    before = {n: centre(at(page, n)) for n in ("a", "b")}
    (ax, ay), (bx, by) = before["a"], before["b"]
    turn(page, ((ax + bx) / 2, (ay + by) / 2), 90)
    for name in ("a", "b"):
        assert abs(angle(page, name) - 90) <= 3
        x, y = centre(at(page, name))
        assert x == pytest.approx(before[name][0], abs=2)
        assert y == pytest.approx(before[name][1], abs=2)


def test_shift_turns_loose_blocks_in_15_degree_steps(editor):
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20),
        box("b", "shape", RECT, z=2, x=100, y=80, w=30, h=20),
    )
    pick(page, "a", "b")
    (ax, ay), (bx, by) = centre(at(page, "a")), centre(at(page, "b"))
    turn(page, ((ax + bx) / 2, (ay + by) / 2), 50, keys=("Shift",))
    for name in ("a", "b"):
        assert angle(page, name) % 15 == 0
        assert angle(page, name) != 0


@pytest.mark.parametrize("second", ["arrow", "triangle"])
def test_a_group_with_a_line_turned_and_back(editor, second):
    client = user()
    rect = box("a", "shape", RECT, x=60, y=80, w=40, h=20, group=["g"])
    if second == "arrow":
        other = box(
            "b", "shape", {**LINE, "kind": "arrow"}, z=2, x=110, y=80, w=30, h=20, group=["g"]
        )
    else:
        other = box(
            "b", "shape", {**RECT, "kind": "triangle"}, z=2, x=110, y=80, w=20, h=30, group=["g"]
        )
    page = editor(rect, other, client=client)
    at(page, "a").click()
    expect_picked(page, "a", "b")
    expect(page.locator(HANDLE)).to_have_count(1)
    (ax, ay, aw, ah), (bx, by, bw, bh) = (
        (r["x"], r["y"], r["width"], r["height"])
        for r in (at(page, "a").bounding_box(), at(page, "b").bounding_box())
    )
    about = (min(ax, bx) + max(ax + aw, bx + bw)) / 2, (min(ay, by) + max(ay + ah, by + bh)) / 2
    start = {b["id"]: b for b in saved(page, client)}
    # With Shift each turn stops at 15 degrees, so the way back is exact.
    turn(page, about, 15, keys=("Shift",))
    turn(page, about, -15, keys=("Shift",))
    back = {b["id"]: b for b in saved(page, client)}
    for name in ("a", "b"):
        for key in ("x", "y", "w", "h"):
            assert back[name][key] == pytest.approx(start[name][key], abs=0.02)
    if second == "arrow":
        for got, want in zip(ends(back["b"]), ends(start["b"]), strict=True):
            assert got == pytest.approx(want, abs=0.02)
        assert math.dist(*ends(back["b"])) == pytest.approx(math.dist(*ends(start["b"])), abs=0.02)


def test_undo_and_redo_of_a_loose_turn(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20),
        box("b", "shape", RECT, z=2, x=100, y=80, w=30, h=20),
        client=client,
    )
    pick(page, "a", "b")
    start = {b["id"]: b for b in saved(page, client)}
    (ax, ay), (bx, by) = centre(at(page, "a")), centre(at(page, "b"))
    turn(page, ((ax + bx) / 2, (ay + by) / 2), 40)
    turned = {b["id"]: b for b in saved(page, client)}
    assert turned["a"]["angle"] == pytest.approx(40, abs=1)
    page.keyboard.press("Control+z")
    back = {b["id"]: b for b in saved(page, client)}
    for n in "ab":
        assert {k: back[n].get(k) for k in KEYS} == {k: start[n].get(k) for k in KEYS}
    page.keyboard.press("Control+y")
    again = {b["id"]: b for b in saved(page, client)}
    for n in "ab":
        assert {k: again[n].get(k) for k in KEYS} == {k: turned[n].get(k) for k in KEYS}


KEYS = ("x", "y", "w", "h", "angle")


def test_a_saved_sheet_keeps_its_blocks(editor):
    client = user()
    seeded = {
        "rect": box("rect", "shape", RECT, x=20, y=40, w=40, h=20, angle=30, group=["g"]),
        "pfeil": box(
            "pfeil",
            "shape",
            {**LINE, "kind": "arrow", "from": "sw"},
            z=2,
            x=70,
            y=40,
            w=30,
            h=20,
            angle=0,
            group=["g"],
        ),
        "links": box("links", "shape", RECT, z=3, x=20, y=120, w=30, h=20, angle=20),
        "rechts": box("rechts", "shape", RECT, z=4, x=120, y=120, w=30, h=20, angle=45),
        "rand": box("rand", "shape", RECT, z=5, x=20, y=200, w=30, h=20),
    }
    page = editor(*seeded.values(), client=client)
    page.keyboard.press("Escape")
    pick(page, "rand")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowLeft")
    saved_now = {b["id"]: b for b in saved(page, client)}
    for name, want in seeded.items():
        for key in ("x", "y", "w", "h", "angle"):
            assert saved_now[name].get(key, 0) == pytest.approx(want.get(key, 0), abs=0.02)
        assert saved_now[name].get("props", {}).get("from") == want.get("props", {}).get("from")


def test_a_group_and_a_loose_block_turn_their_own_ways(editor):
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20, group=["g"]),
        box("b", "shape", RECT, z=2, x=100, y=80, w=30, h=20, group=["g"]),
        box("c", "shape", RECT, z=3, x=200, y=80, w=30, h=20),
    )
    at(page, "a").click()
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    (ax, ay), (bx, by), (cx, cy) = (centre(at(page, n)) for n in "abc")
    # The handle sits over the box around all three, so that is the point it turns about.
    boxes = [at(page, n).bounding_box() for n in "abc"]
    left, top = min(r["x"] for r in boxes), min(r["y"] for r in boxes)
    right, bottom = (
        max(r["x"] + r["width"] for r in boxes),
        max(r["y"] + r["height"] for r in boxes),
    )
    turn(page, ((left + right) / 2, (top + bottom) / 2), 90)
    # The group goes a quarter round its own middle, between its two blocks.
    about = ((ax + bx) / 2, (ay + by) / 2)
    (ax2, ay2), (bx2, by2) = centre(at(page, "a")), centre(at(page, "b"))
    for (px, py), (qx, qy) in (((ax, ay), (ax2, ay2)), ((bx, by), (bx2, by2))):
        dx, dy = px - about[0], py - about[1]
        assert qx - about[0] == pytest.approx(-dy, abs=3)
        assert qy - about[1] == pytest.approx(dx, abs=3)
    for name in ("a", "b", "c"):
        assert abs(angle(page, name) - 90) <= 3
    # The loose block stays on its spot.
    assert centre(at(page, "c")) == pytest.approx((cx, cy), abs=2)


def test_escape_puts_loose_blocks_back(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20),
        box("b", "shape", RECT, z=2, x=100, y=80, w=30, h=20),
        client=client,
    )
    pick(page, "a", "b")
    start = {b["id"]: b for b in saved(page, client)}
    (ax, ay), (bx, by) = centre(at(page, "a")), centre(at(page, "b"))
    about = ((ax + bx) / 2, (ay + by) / 2)
    points = arc(centre(page.locator(HANDLE)), about, 60)
    page.mouse.move(*points[0])
    page.mouse.down()
    for point in points[1:]:
        page.mouse.move(*point, steps=5)
    assert angle(page, "a") != pytest.approx(0, abs=3)
    page.keyboard.press("Escape")
    page.mouse.up()
    back = {b["id"]: b for b in saved(page, client)}
    for n in "ab":
        assert {k: back[n].get(k) for k in KEYS} == {k: start[n].get(k) for k in KEYS}


ODD = (
    box("a", "shape", RECT, x=60, y=80, w=60, h=10.01, group=["g"]),
    box("b", "shape", RECT, z=2, x=60, y=100, w=10, h=30.03, group=["g"]),
)


def close(page, client, start, tolerance):
    """The saved blocks lie where they started, within the tolerance in mm."""
    back = {b["id"]: b for b in saved(page, client)}
    for n in "ab":
        for key in ("x", "y", "w", "h"):
            assert back[n][key] == pytest.approx(start[n][key], abs=tolerance)


def test_undo_then_back_comes_to_the_start(editor):
    client = user()
    page = editor(*ODD, client=client)
    group(page, "a", "b")
    start = {b["id"]: b for b in saved(page, client)}
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.press("Control+z")
    page.keyboard.press("Alt+ArrowLeft")
    close(page, client, start, 0.005)


def test_escape_keeps_the_middle_for_the_way_back(editor):
    client = user()
    page = editor(*ODD, client=client)
    group(page, "a", "b")
    start = {b["id"]: b for b in saved(page, client)}
    boxes = [at(page, n).bounding_box() for n in "ab"]
    left, top = min(r["x"] for r in boxes), min(r["y"] for r in boxes)
    right, bottom = (
        max(r["x"] + r["width"] for r in boxes),
        max(r["y"] + r["height"] for r in boxes),
    )
    about = ((left + right) / 2, (top + bottom) / 2)
    page.keyboard.press("Alt+ArrowRight")
    points = arc(centre(page.locator(HANDLE)), about, 33)
    page.mouse.move(*points[0])
    page.mouse.down()
    for point in points[1:]:
        page.mouse.move(*point, steps=5)
    page.keyboard.press("Escape")
    page.mouse.up()
    page.keyboard.press("Alt+ArrowLeft")
    close(page, client, start, 0.005)


def test_four_quarter_buttons_give_the_first_sheet_exactly(editor):
    client = user()
    page = editor(*ODD, client=client)
    group(page, "a", "b")
    start = {b["id"]: b for b in saved(page, client)}
    for _ in range(4):
        page.get_by_label("Rechtsdrehung 90°", exact=True).click()
        saved(page, client)
    close(page, client, start, 0.001)


def same(page, client, before, names=("l", "m")):
    """The saved blocks are as they were: box and a line's start, within 0.02 mm."""
    after = {b["id"]: b for b in saved(page, client)}
    for n in names:
        for key in ("x", "y", "w", "h"):
            assert after[n][key] == pytest.approx(before[n][key], abs=0.02)
        assert after[n]["props"].get("from") == before[n]["props"].get("from")


def test_a_group_of_only_lines_turns_back_to_where_it_was(editor):
    client = user()
    page = editor(
        box("l", "shape", {**LINE, "from": "nw"}, x=40, y=60, w=50, h=30, group=["g"]),
        box("m", "shape", {**LINE, "from": "ne"}, z=2, x=100, y=60, w=40, h=20, group=["g"]),
        client=client,
    )
    group(page, "l", "m")
    before = {b["id"]: b for b in saved(page, client)}
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.press("Alt+ArrowLeft")
    same(page, client, before)


def test_alt_turns_and_buttons_share_the_centre(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=60, h=10, group=["g"]),
        box("b", "shape", RECT, z=2, x=60, y=100, w=10, h=30, group=["g"]),
        client=client,
    )
    group(page, "a", "b")
    before = {b["id"]: b for b in saved(page, client)}
    page.keyboard.press("Alt+ArrowRight")
    page.get_by_label("Rechtsdrehung 90°", exact=True).click()
    page.keyboard.press("Alt+ArrowLeft")
    page.get_by_label("Linksdrehung 90°", exact=True).click()
    same(page, client, before, names=("a", "b"))


@pytest.mark.parametrize("swap", [False, True])
def test_a_group_turns_about_the_middle_of_its_frame(editor, swap):
    client = user()
    blocks = [
        box("a", "shape", RECT, x=60, y=80, w=60, h=10, angle=45, group=["g"]),
        box("b", "shape", RECT, z=2, x=60, y=120, w=60, h=10, group=["g"]),
    ]
    page = editor(*(blocks[::-1] if swap else blocks), client=client)
    group(page, "a", "b")
    before = {b["id"]: b for b in saved(page, client)}
    page.keyboard.press("Alt+ArrowRight")
    after = {b["id"]: b for b in saved(page, client)}
    left, top, right, bottom = hull(list(before.values()))
    middle = ((left + right) / 2, (top + bottom) / 2)
    for n in ("a", "b"):
        b0, b1 = before[n], after[n]
        centre0 = (b0["x"] + b0["w"] / 2, b0["y"] + b0["h"] / 2)
        centre1 = (b1["x"] + b1["w"] / 2, b1["y"] + b1["h"] / 2)
        expected = turned_about(centre0, middle, 15)
        assert centre1[0] == pytest.approx(expected[0], abs=0.02)
        assert centre1[1] == pytest.approx(expected[1], abs=0.02)


def ends(arrow):
    """The two ends of a line in mm, from its box and the corner it starts at."""
    f = arrow.get("props", {}).get("from", "nw")
    x, y, w, h = arrow["x"], arrow["y"], arrow["w"], arrow["h"]
    start = (x + (w if f[1] == "e" else 0), y + (h if f[0] == "s" else 0))
    end = (x + (0 if f[1] == "e" else w), y + (0 if f[0] == "s" else h))
    return start, end


def test_a_group_with_a_line_turns_by_the_handle(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20, group=["g"]),
        box("b", "shape", {**LINE, "kind": "arrow"}, z=2, x=100, y=80, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    expect_picked(page, "a", "b")
    expect(page.locator(HANDLE)).to_have_count(1)
    start = {b["id"]: b for b in saved(page, client)}
    (p, q) = ends(start["b"])
    cx, cy = (60 + 130) / 2, (80 + 100) / 2
    (ax, ay), (bx, by) = centre(at(page, "a")), centre(at(page, "b"))
    turn(page, ((ax + bx) / 2, (ay + by) / 2), 30)
    after = {b["id"]: b for b in saved(page, client)}
    (p2, q2) = ends(after["b"])
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))

    def rot(pt):
        dx, dy = pt[0] - cx, pt[1] - cy
        return cx + dx * c - dy * s, cy + dx * s + dy * c

    # Each end went round the centre: it is now where one of the new ends lies, within 1 mm.
    for end in (rot(p), rot(q)):
        assert any(math.dist(end, new) <= 1 for new in (p2, q2))
    assert math.dist(p2, q2) == pytest.approx(math.dist(p, q), abs=0.05)
    assert angle(page, "a") == pytest.approx(30, abs=1)


def test_a_turned_line_prints_where_the_screen_shows_it(editor, browser, server):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=40, h=20, group=["g"]),
        box("b", "shape", {**LINE, "kind": "arrow"}, z=2, x=110, y=70, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    expect_picked(page, "a", "b")
    (ax, ay), (bx, by) = centre(at(page, "a")), centre(at(page, "b"))
    turn(page, ((ax + bx) / 2, (ay + by) / 2), 30, keys=("Shift",))
    blocks = {b["id"]: b for b in saved(page, client)}
    assert blocks["a"]["angle"] == 30
    assert "angle" not in blocks["b"]
    sheet_id = page.url.rsplit("/", 1)[1]
    assert over(*screen_and_print(browser, server, client, sheet_id)) == []


@pytest.mark.parametrize("start", ["nw", "ne", "se", "sw"])
def test_a_line_from_any_corner_keeps_its_ends_through_a_group_turn(editor, start):
    # Beyond the brief: a line that starts at each corner goes round as its ends do, by Alt+Right
    # and back by Alt+Left to where it was.
    client = user()
    line = box("l", "shape", {**LINE, "from": start}, x=40, y=60, w=50, h=30, group=["g"])
    first = [box("r", "shape", RECT, x=100, y=60, w=40, h=30, group=["g"]), line]
    page = editor(*first, client=client)
    at(page, "r").click()
    expect_picked(page, "r", "l")
    page.keyboard.press("Alt+ArrowRight")
    turned = {b["id"]: b for b in saved(page, client)}["l"]
    (p, q), (p2, q2) = ends(line), ends(turned)
    # The start stays the start: it went round the group's middle (90, 75) by 15 degrees.
    c, s = math.cos(math.radians(15)), math.sin(math.radians(15))
    for was, now in ((p, p2), (q, q2)):
        dx, dy = was[0] - 90, was[1] - 75
        assert now == pytest.approx((90 + dx * c - dy * s, 75 + dx * s + dy * c), abs=0.02)
    page.keyboard.press("Alt+ArrowLeft")
    back = {b["id"]: b for b in saved(page, client)}
    for b in first:
        for side in "xywh":
            assert back[b["id"]][side] == pytest.approx(b[side], abs=0.02)
        assert back[b["id"]].get("angle", 0) == 0
    assert back["l"]["props"]["from"] == start
