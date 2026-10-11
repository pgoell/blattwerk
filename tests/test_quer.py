"""A sheet laid on its side or upright brings back what the page no longer holds, as PowerPoint
does: a group as one, so its blocks keep their places in it, and a turned block by its outline as
turned. What lies on the new page does not move.

The docstrings name the lines of the checklist of issues #327 and #328.
"""

import math

import pytest
from playwright.sync_api import expect
from test_lock import KINDS, undo
from test_lock_format import OTHER, every, named, redo
from ui import TEXT, box, doc, thumb, user

QUER, HOCH = (297, 210), (210, 297)
# Every kind of block by itself: the test puts each into a group.
ALONE = [*(k for k in KINDS if k != "group"), *OTHER]


def outline(b):
    """The level box around a block as turned, about its centre: left, top, right, bottom."""
    turn = math.radians(b.get("angle", 0))
    c, s = abs(math.cos(turn)), abs(math.sin(turn))
    w, h = b["w"] * c + b["h"] * s, b["w"] * s + b["h"] * c
    x, y = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    return x - w / 2, y - h / 2, x + w / 2, y + h / 2


def units(blocks):
    """What comes back as one: the blocks of an outermost group, or a block by itself."""
    found = {}
    for b in blocks:
        found.setdefault(b.get("group", [b["id"]])[0], []).append(b)
    return found.values()


def back(lo, hi, size):
    """How far a span moves to lie within the page: no farther than onto it, and the left or top
    edge wins where it is larger than the page."""
    return max(0, min(lo, size - (hi - lo))) - lo


def laid(was, now, size):
    """Each unit moved as one and only as far as onto the page, and nothing else changed. What lay
    on the page is exactly where it was. Gives the names of what moved."""
    assert [b["id"] for b in now] == [b["id"] for b in was]
    after = {b["id"]: b for b in now}
    moved = set()
    for blocks in units(was):
        boxes = [outline(b) for b in blocks]
        left, top = (min(o[i] for o in boxes) for i in (0, 1))
        right, bottom = (max(o[i] for o in boxes) for i in (2, 3))
        dx, dy = back(left, right, size[0]), back(top, bottom, size[1])
        for b in blocks:
            if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                assert after[b["id"]] == b
                continue
            moved.add(b["id"])
            now = after[b["id"]]
            assert {**now, "x": b["x"], "y": b["y"]} == b
            # A place is kept to the hundredth of a mm.
            assert (now["x"], now["y"]) == pytest.approx((b["x"] + dx, b["y"] + dy), abs=0.011)
    return moved


def fmt(page, name):
    """Clicks a format in the panel Ansicht."""
    page.get_by_role("tab", name="Ansicht").click()
    page.locator(".panel").get_by_role("button", name=name, exact=True).click()


def places(blocks, names):
    return [(blocks[n]["x"], blocks[n]["y"]) for n in names]


def text(name, y, x=15, **more):
    return {**box(name, "text", TEXT), "x": x, "y": y, **more}


def test_quer_brings_a_group_back_as_one(editor):
    """A9, A13, I1, #327: two texts in a group, the lower at the page's bottom edge."""
    client = user()
    page = editor(text("a", 230, group=["g"]), text("b", 265, group=["g"]), client=client)
    before = doc(page, client)
    fmt(page, "Quer")
    expect(undo(page)).to_be_enabled()
    quer = doc(page, client)
    assert places(named(quer), "ab") == [(15, 155), (15, 190)]
    undo(page).click()
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before
    redo(page).click()
    expect(redo(page)).to_be_disabled()
    assert doc(page, client) == quer


def test_quer_judges_a_turned_block_by_its_outline(editor):
    """A10, I2, #328: a text on its side whose outline hangs below the page comes back, and one
    whose outline fits stays at exactly its place, though its box as unturned would not fit."""
    client = user()
    # 20 wide and 190 high, on its side: 190 wide and 20 high, from x=15 and y=145.
    fits = {**text("fits", 60, x=100, angle=90), "w": 20, "h": 190}
    page = editor(text("low", 140, angle=90), fits, client=client)
    before = named(doc(page, client))
    fmt(page, "Quer")
    expect(undo(page)).to_be_enabled()
    now = named(doc(page, client))
    # Its outline spans y 60 to 240: 30 mm up.
    assert places(now, ["low"]) == [(15, 110)]
    assert now["fits"] == before["fits"]


def test_a_block_on_its_side_half_a_hundredth_off_the_edge_stays(editor):
    """I2: width and height differ by an odd count of hundredths, so the outline's left edge lies
    half a hundredth off the page's, where a quarter turn stores it. It is meant to lie at 0."""
    client = user()
    a = {**text("a", 50), "x": 84.99, "w": 20.01, "h": 190, "angle": 90}
    page = editor(a, text("z", 265), client=client)
    before = named(doc(page, client))
    fmt(page, "Quer")
    expect(undo(page)).to_be_enabled()
    assert named(doc(page, client))["a"] == before["a"]


def test_a_group_larger_than_the_page_lands_at_its_left_and_top_edge(editor):
    """I3: too high for the sheet on its side, then too wide for the upright one."""
    client = user()
    high = [text("a", 20, group=["g"]), text("b", 270, group=["g"])]
    wide = [text("a", 20, x=30, group=["g"]), text("b", 50, x=100, group=["g"])]
    page = editor(*high, client=client, pages=[{"blocks": wide, "landscape": True}])
    fmt(page, "Quer")
    expect(undo(page)).to_be_enabled()
    assert places(named(doc(page, client)), "ab") == [(15, 0), (15, 250)]
    fmt(page, "Hoch")
    expect(page.locator(".panel").get_by_role("button", name="Hoch", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    assert places(named(doc(page, client), 1), "ab") == [(0, 20), (70, 50)]


def test_a_page_with_a_format_of_its_own_brings_its_blocks_back(editor):
    """A11, A13: "Quer" for the second page alone."""
    client = user()
    low = [text("a", 230, group=["g"]), text("b", 265, group=["g"]), text("c", 140, angle=90)]
    page = editor(text("z", 265), client=client, more=low, theme="")
    before = doc(page, client)
    thumb(page, 1).click()
    page.get_by_role("tab", name="Ansicht").click()
    panel = page.locator(".panel")
    panel.get_by_role("button", name="Nur diese Seite").click()
    panel.get_by_role("button", name="Quer", exact=True).click()
    expect(undo(page)).to_be_enabled()
    quer = doc(page, client)
    assert quer["pages"][1]["landscape"] is True
    assert places(named(quer, 1), "abc") == [(15, 155), (15, 190), (15, 110)]
    # The first page stands upright as before.
    assert quer["pages"][0] == before["pages"][0]
    undo(page).click()
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before


@pytest.mark.parametrize("to", ["Hoch", "Wie Blatt"])
def test_a_page_that_lies_on_its_side_by_itself_brings_its_blocks_back_upright(editor, to):
    """A11: a group and two texts on their sides, right of where the upright page ends."""
    client = user()
    far = [
        text("a", 20, x=30, group=["g"]),
        text("b", 50, x=110, group=["g"]),
        # On its side its outline spans x 190 to 210: it fits the upright page too.
        text("c", 95, x=110, angle=90),
        # And this one's spans x 270 to 290.
        text("d", 95, x=190, angle=90),
    ]
    rest = [{"blocks": far, "landscape": True}]
    page = editor(text("z", 20), client=client, pages=rest, theme="")
    before = doc(page, client)
    thumb(page, 1).click()
    page.get_by_role("tab", name="Ansicht").click()
    panel = page.locator(".panel")
    panel.get_by_role("button", name="Nur diese Seite").click()
    expect(panel.get_by_role("button", name="Quer", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    # The first: the grid below has a "Wie Blatt" too.
    panel.get_by_role("button", name=to, exact=True).first.click()
    expect(undo(page)).to_be_enabled()
    after = doc(page, client)
    now = named(after, 1)
    # The group is 260 wide: its left edge wins, and 80 mm stay between its blocks.
    assert places(now, "abd") == [(0, 20), (80, 50), (110, 95)]
    assert now["c"] == named(before, 1)["c"]
    assert after["pages"][0] == before["pages"][0]
    undo(page).click()
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before


def some(client, kind, locked, far=False):
    """Blocks of the kind as `box` makes them, 180 by 20 mm: "allein" turned by 30 degrees, a group
    in a group with "a" on its side, and "bleibt" on its side in the page's middle. They hang below
    an upright page laid on its side, or with `far` right of one that lay so and stands upright.
    A line has no angle: a quarter turn swaps its width and height."""

    def made(name, x, y, **more):
        (b,) = every(client, kind)
        if kind == "line":
            more.pop("angle", None)
        return {**b, **more, "id": name, "x": x, "y": y, "locked": locked and name != "b"}

    shift = 90 if far else 0
    return [
        made("allein", 15 + shift, 100 if far else 265, angle=30, z=1),
        made("a", 15 + shift, 95 if far else 230, angle=90, z=2, group=["g"]),
        made("b", 15 + shift, 150 if far else 265, z=3, group=["g", "h"]),
        text("c", 120 if far else 250, x=15 + shift, z=4, group=["g", "h"]),
        made("bleibt", 15, 95, angle=90, z=5),
    ]


@pytest.mark.parametrize("locked", [False, True])
@pytest.mark.parametrize("kind", ALONE)
def test_quer_and_hoch_bring_every_kind_back_alone_turned_and_in_a_group(editor, kind, locked):
    """A9 to A14, I1, I2, I4, I5: every kind alone and turned by 30 degrees, in a group in a group
    and on its side there, locked or free. To Quer on the first page, to Hoch on the second, which
    lay on its side by itself."""
    client = user()
    rest = [{"blocks": some(client, kind, locked, far=True), "landscape": True}]
    page = editor(*some(client, kind, locked), client=client, pages=rest)
    before = doc(page, client)
    fmt(page, "Quer")
    expect(undo(page)).to_be_enabled()
    quer = doc(page, client)
    moved = {"allein", "a", "b", "c"}
    assert laid(before["pages"][0]["blocks"], quer["pages"][0]["blocks"], QUER) == moved
    # Every page follows the sheet, and the second is as wide as it was.
    assert quer["pages"][1]["blocks"] == before["pages"][1]["blocks"]
    fmt(page, "Hoch")
    expect(page.locator(".panel").get_by_role("button", name="Hoch", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    hoch = doc(page, client)
    assert laid(quer["pages"][1]["blocks"], hoch["pages"][1]["blocks"], HOCH) == moved
    # What Quer brought back lies on the upright page too.
    assert hoch["pages"][0]["blocks"] == quer["pages"][0]["blocks"]
    for b in hoch["pages"][0]["blocks"] + hoch["pages"][1]["blocks"]:
        assert b["locked"] == (locked and b["id"] not in "bc")
    # One step each way.
    undo(page).click()
    assert doc(page, client) == quer
    undo(page).click()
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before
    redo(page).click()
    assert doc(page, client) == quer
    redo(page).click()
    expect(redo(page)).to_be_disabled()
    assert doc(page, client) == hoch
