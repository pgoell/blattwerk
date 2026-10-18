"""A block dropped with its middle in the grey gap between two pages lands whole on the page nearest
to it (#816).

The gap is the grey strip between page 1 and page 2. A block whose middle lies there, nearer page 1,
used to stay on page 1 hanging past its edge, where .paper clips it and the PDF leaves that part out.
Now it moves by the least it takes to lie whole on page 1. One drag is one undo step, and with Ctrl
the copy stays where the block began. A block dragged across the gap to page 2 keeps its place
there through a save, a reload and the PDF, and one undo brings it back.
"""

import pytest
from playwright.sync_api import expect
from test_desk_scroll import PAGE, on_page, press
from test_fix_blatt import pdf_pages
from ui import (
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    centre,
    doc,
    maths,
    picture,
    reload,
    upload,
    user,
)

WORDS = ["Hase", "Igel", "Kaninchen"]


def gap_target(page):
    """The screen y that puts the block's middle a quarter of the gap below page 1's bottom edge."""
    return page.evaluate(
        """() => {
            const a = document.querySelector('.block[data-id="a"]').getBoundingClientRect();
            const p1 = document.querySelector('.sheet[data-page="0"]').getBoundingClientRect();
            const p2 = document.querySelector('.sheet[data-page="1"]').getBoundingClientRect();
            return [(a.top + a.bottom) / 2, p1.bottom + (p2.top - p1.bottom) * 0.25];
        }"""
    )


def to_gap(page):
    """Scrolls the desk so the gap below page 1 lies in the desk's middle, in view."""
    page.evaluate(
        """() => {
            const d = document.querySelector('.desk');
            const p1 = document.querySelector('.sheet[data-page="0"]').getBoundingClientRect();
            const r = d.getBoundingClientRect();
            d.scrollTop += p1.bottom - (r.top + r.height / 2);
        }"""
    )


def drop_in_gap(page, extra_steps=10):
    """Drags "a" on page 1 until its middle lies in the gap, nearer page 1, and returns there."""
    to_gap(page)
    press(page, "a")
    mid, target = gap_target(page)
    x, y = centre(at(page, "a"))
    page.mouse.move(x, y + (target - mid), steps=extra_steps)
    return x, y + (target - mid)


def sheets(editor, client, *blocks, words=None):
    """Two pages and the blocks on page 1, the middle of the first 5 mm above the bottom edge, so a
    short drag puts it in the gap."""
    first = blocks[0]
    shift = round(292 - first["h"] / 2 - first["y"], 2)
    blocks = [{**b, "y": round(b["y"] + shift, 2)} for b in blocks]
    return editor(
        *blocks,
        pages=[{"blocks": []}, {"blocks": []}],
        client=client,
        **({"words": words} if words is not None else {}),
    )


def group(*blocks):
    return [{**b, "group": ["g"]} for b in blocks]


def gap_case(client, kind):
    """The block (or group) for each type, id "a", with its own height and width."""
    if kind == "text":
        return [box("a", "text", TEXT)]
    if kind == "shape":
        return [box("a", "shape", RECT)]
    if kind == "line":
        return [box("a", "shape", LINE)]
    if kind == "picture":
        return [{**picture(upload(client)), "id": "a"}]
    if kind == "table":
        return [box("a", "table", TABLE)]
    if kind == "ruling":
        return [box("a", "ruling", RULING)]
    if kind == "maths":
        return [box("a", "maths", maths(client))]
    if kind == "group":
        a = box("a", "text", TEXT)
        b = {**box("b", "text", TEXT, z=2), "x": 100, "w": 80, "y": a["y"]}
        return group(a, b)
    raise ValueError(kind)


@pytest.mark.parametrize(
    "kind", ["text", "shape", "line", "picture", "table", "ruling", "maths", "group"]
)
def test_a_block_dropped_with_its_middle_in_the_gap_lands_whole_on_page_1(editor, kind):
    """A6: the block of each type dropped with its middle in the gap nearer page 1 lands whole on
    page 1 and is saved so. A line's box holds both its ends, so both lie on the page too."""
    client = user()
    page = sheets(editor, client, *gap_case(client, kind))
    before = doc(page, client)["pages"][0]["blocks"]
    drop_in_gap(page)
    page.mouse.up()
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    saved = doc(page, client)
    assert [len(p["blocks"]) for p in saved["pages"]] == [len(before), 0, 0], [
        [(b["id"], b["x"], b["y"], b["w"], b["h"]) for b in p["blocks"]] for p in saved["pages"]
    ]
    for b in saved["pages"][0]["blocks"]:
        assert on_page(b), (kind, b["y"], b["h"])


def test_one_undo_takes_the_gap_drop_back(editor):
    """I4: one Ctrl+Z takes the gap drop back to where the block began on page 1."""
    client = user()
    page = sheets(editor, client, box("a", "text", TEXT))
    before = doc(page, client)["pages"][0]["blocks"][0]
    drop_in_gap(page)
    page.mouse.up()
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    page.keyboard.press("Control+z")
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    assert doc(page, client)["pages"][0]["blocks"] == [before]


def test_a_ctrl_copy_dropped_in_the_gap_stays_where_the_block_began(editor):
    """I8: with Ctrl held at the drop, the copy stays where the block began and the moved block lands
    whole on page 1."""
    client = user()
    page = sheets(editor, client, box("a", "text", TEXT))
    before = doc(page, client)["pages"][0]["blocks"][0]
    page.keyboard.down("Control")
    drop_in_gap(page)
    page.mouse.up()
    page.keyboard.up("Control")
    expect(page.locator(".sheet[data-page] .block")).to_have_count(2)
    saved = doc(page, client)
    first = saved["pages"][0]["blocks"]
    assert len(first) == 2
    assert (before["x"], before["y"]) in [(b["x"], b["y"]) for b in first]
    # The copy keeps the block's old place, which hangs past the edge; only the moved block must lie whole.
    (moved,) = [b for b in first if (b["x"], b["y"]) != (before["x"], before["y"])]
    assert on_page(moved)


def across(page):
    """The drag of "a" from page 1 over the gap to page 2, as test_desk_scroll does it."""
    grip = at(page, "a").bounding_box()
    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    b = page.locator(".desk").bounding_box()
    page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] - 5, steps=10)
    page.wait_for_function(
        """() => document.querySelector('.sheet[data-page="1"]').getBoundingClientRect().top
            < document.querySelector('.desk').getBoundingClientRect().top + 200"""
    )
    b = page.locator(".desk").bounding_box()
    page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=5)
    page.mouse.up()


A7_CASES = [
    pytest.param(lambda c: [box("a", "text", TEXT)], "Hallo", id="control-text"),
    pytest.param(lambda c: [box("a", "table", TABLE)], "Z", id="table"),
    pytest.param(
        lambda c: [box("a", "ruling", {**RULING, "list": "copy"})],
        "Hase",
        id="lernwoerter-lineatur",
    ),
    pytest.param(lambda c: [box("a", "text", {**TEXT, "list": True})], "Hase", id="linked-text"),
    pytest.param(
        lambda c: [
            {**box("a", "text", TEXT), "group": ["g"]},
            {**box("b", "text", TEXT, z=2), "group": ["g"]},
        ],
        "Hallo",
        id="group-unlocked",
    ),
]


def test_a_group_with_a_locked_block_stays_put_when_dragged_toward_page_2(editor):
    """A group with a locked block is fixed there: a drag toward page 2 moves nothing, and the group
    stays whole on page 1, as saved."""
    client = user()
    page = editor(
        {**box("a", "text", TEXT), "locked": True, "group": ["g"]},
        {**box("b", "text", TEXT, z=2), "group": ["g"]},
        pages=[{"blocks": []}, {"blocks": []}],
        client=client,
    )
    before = doc(page, client)["pages"]
    press(page, "a")
    x, y = centre(at(page, "a"))
    page.mouse.move(x, y + 150, steps=10)
    page.mouse.up()
    page.wait_for_timeout(1000)
    saved = doc(page, client)["pages"]
    assert saved == before
    assert [len(p["blocks"]) for p in saved] == [2, 0, 0]
    assert all(on_page(b) for b in saved[0]["blocks"])


@pytest.mark.parametrize(("make", "marker"), A7_CASES)
def test_a_block_moved_across_the_gap_to_page_2_saves_reloads_prints_and_undoes(
    editor, server, make, marker
):
    """A7: moved across the gap to page 2, the block is there after save and reload, prints on PDF
    page 2 and not on page 1, and one Ctrl+Z brings it back to page 1."""
    client = user()
    page = editor(*make(client), pages=[{"blocks": []}, {"blocks": []}], client=client, words=WORDS)
    across(page)
    expect(page.locator(PAGE.format(1)).locator('.block[data-id="a"]')).to_have_count(1)
    saved = doc(page, client)
    assert "a" in [b["id"] for b in saved["pages"][1]["blocks"]]
    assert all(on_page(b) for b in saved["pages"][1]["blocks"])
    page.keyboard.press("Control+z")
    expect(page.locator(PAGE.format(0)).locator('.block[data-id="a"]')).to_have_count(1)
    assert "a" in [b["id"] for b in doc(page, client)["pages"][0]["blocks"]]
    page.keyboard.press("Control+y")
    expect(page.locator(PAGE.format(1)).locator('.block[data-id="a"]')).to_have_count(1)
    reload(page, page.url)
    expect(page.locator(PAGE.format(1)).locator('.block[data-id="a"]')).to_have_count(1)
    printed = pdf_pages(server, client, page.url.rsplit("/", 1)[1])
    assert marker in printed[1], printed
    assert marker not in printed[0]
