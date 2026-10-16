"""The position and size fields take a unit, and X and Y can count from the page's centre."""

import pytest
from playwright.sync_api import expect
from test_fields import by_id, enter, field, lock
from ui import (
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    maths,
    pick,
    picture,
    saved,
    unpick,
    upload,
    user,
)

# The page is A4: 210 mm wide, 297 mm high, so its centre is at 105 and 148,5 mm.
ROOM = {"x": 40, "y": 60, "w": 80, "h": 40}

# The block type each kind is stored as.
TYPES = {
    "text": "text",
    "shape": "shape",
    "line": "shape",
    "image": "image",
    "table": "table",
    "ruling": "ruling",
    "maths": "maths",
}


def props_of(client, kind):
    if kind == "image":
        return picture(upload(client))["props"]
    if kind == "maths":
        return maths(client)
    return {"text": TEXT, "shape": RECT, "line": LINE, "table": TABLE, "ruling": RULING}[kind]


def mitte(page, on):
    page.get_by_label("von", exact=True).select_option(on)


@pytest.mark.parametrize("kind", ["text", "shape", "line", "image", "table", "ruling", "maths"])
def test_x_and_y_take_a_unit(editor, kind):
    client = user()
    page = editor(box("a", TYPES[kind], props_of(client, kind)), client=client)
    pick(page, "a")
    enter(page, "X", "2 cm")
    enter(page, "Y", "1 in")
    expect(field(page, "X")).to_have_value("20")
    expect(field(page, "Y")).to_have_value("25,4")
    a = by_id(saved(page, client))["a"]
    assert (a["x"], a["y"]) == (20, 25.4)


@pytest.mark.parametrize("kind", ["text", "shape", "image", "ruling"])
def test_width_and_height_take_a_unit(editor, kind):
    client = user()
    page = editor(box("a", TYPES[kind], props_of(client, kind)), client=client)
    pick(page, "a")
    # 2,5 cm is 25 mm; 72 pt is 25,4 mm. A picture keeps its ratio, so only its width is checked.
    enter(page, "Breite", "2,5cm")
    expect(field(page, "Breite")).to_have_value("25")
    a = by_id(saved(page, client))["a"]
    assert a["w"] == 25
    if kind in ("text", "shape"):
        enter(page, "Höhe", "72 pt")
        expect(field(page, "Höhe")).to_have_value("25,4")
        assert by_id(saved(page, client))["a"]["h"] == 25.4


def test_a_group_takes_a_unit_for_its_place(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, group=["g"]),
        box("b", "shape", RECT, z=2, x=100, y=120, w=30, h=20, group=["g"]),
        client=client,
    )
    # A click on one member picks the whole group.
    at(page, "a").click()
    expect(page.locator(".block.sel")).to_have_count(2)
    # The group's box starts at 15 mm; 2 cm moves both blocks by 5 mm.
    expect(field(page, "X")).to_have_value("15")
    enter(page, "X", "2 cm")
    expect(field(page, "X")).to_have_value("20")
    blocks = by_id(saved(page, client))
    assert (blocks["a"]["x"], blocks["b"]["x"]) == (20, 105)


def test_a_wrong_unit_keeps_the_old_value(editor):
    page = editor(box("a", "shape", RECT, **ROOM))
    pick(page, "a")
    was = at(page, "a").bounding_box()
    wrong = (("X", "2 km"), ("X", "2 cmm"), ("X", "cm"), ("Y", "3 pt pt"), ("Breite", "2 km"))
    for label, value in wrong:
        enter(page, label, value)
    expect(field(page, "X")).to_have_value("40")
    expect(field(page, "Y")).to_have_value("60")
    expect(field(page, "Breite")).to_have_value("80")
    assert at(page, "a").bounding_box() == was


def test_a_unit_on_drehung_or_percent_keeps_the_old_value(editor):
    page = editor(box("a", "shape", RECT, **ROOM))
    pick(page, "a")
    enter(page, "Drehung", "90 cm")
    expect(field(page, "Drehung")).to_have_value("0")
    enter(page, "Breite %", "50 cm")
    expect(field(page, "Breite %")).to_have_value("100")
    expect(field(page, "Breite")).to_have_value("80")


def test_a_unit_entry_is_one_undo_step(editor):
    page = editor(box("a", "shape", RECT))
    pick(page, "a")
    enter(page, "X", "2 cm")
    enter(page, "Breite", "2,5cm")
    expect(field(page, "Breite")).to_have_value("25")
    page.keyboard.press("Control+z")
    expect(field(page, "Breite")).to_have_value("180")
    expect(field(page, "X")).to_have_value("20")
    page.keyboard.press("Control+z")
    expect(field(page, "X")).to_have_value("15")
    page.keyboard.press("Control+y")
    expect(field(page, "X")).to_have_value("20")


def test_mitte_counts_the_place_from_the_page_centre(editor):
    client = user()
    page = editor(box("a", "shape", RECT), client=client)
    pick(page, "a")
    # The block starts at 15 mm and 50 mm: 105 and 148,5 mm from the centre is -90 and -98,5.
    mitte(page, "Mitte")
    expect(field(page, "X")).to_have_value("-90")
    expect(field(page, "Y")).to_have_value("-98,5")
    # The switch is a view: it is no step to undo.
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    enter(page, "X", "2 cm")
    expect(field(page, "X")).to_have_value("20")
    enter(page, "Y", "0")
    a = by_id(saved(page, client))["a"]
    assert (a["x"], a["y"]) == (125, 148.5)
    # An arrow steps by 1 mm in the shown place.
    field(page, "X").focus()
    page.keyboard.press("ArrowUp")
    expect(field(page, "X")).to_have_value("21")
    assert by_id(saved(page, client))["a"]["x"] == 126


def test_mitte_stays_while_the_selection_changes(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    mitte(page, "Mitte")
    expect(field(page, "X")).to_have_value("-65")
    unpick(page)
    pick(page, "a")
    expect(field(page, "X")).to_have_value("-65")
    expect(page.get_by_label("von", exact=True)).to_have_value("centre")
    # Back in the corner mode the same block shows its own corner.
    mitte(page, "Ecke oben links")
    expect(field(page, "X")).to_have_value("40")


def test_a_lock_keeps_the_ratio_for_a_typed_unit(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    # The block is 80 by 40 mm. 20 mm wide makes it 10 mm high, and 2 cm is 20 mm.
    enter(page, "Breite", "2 cm")
    expect(field(page, "Breite")).to_have_value("20")
    expect(field(page, "Höhe")).to_have_value("10")
    a = by_id(saved(page, client))["a"]
    assert (a["w"], a["h"]) == (20, 10)


@pytest.mark.parametrize("kind", ["table", "maths"])
def test_a_table_and_a_maths_block_take_a_unit_for_their_width(editor, kind):
    client = user()
    page = editor(box("a", TYPES[kind], props_of(client, kind)), client=client)
    pick(page, "a")
    # Capitals count too: 4 IN is 101,6 mm.
    enter(page, "Breite", "4 IN")
    expect(field(page, "Breite")).to_have_value("101,6")
    assert by_id(saved(page, client))["a"]["w"] == 101.6


def test_a_group_takes_a_unit_for_its_width(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=20, y=50, w=30, h=20, group=["g"]),
        box("b", "shape", RECT, z=2, x=70, y=50, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    expect(page.locator(".block.sel")).to_have_count(2)
    # The group is 80 mm wide; 4 cm halves it from its left edge.
    enter(page, "Breite", "4cm")
    expect(field(page, "Breite")).to_have_value("40")
    a, b = (by_id(saved(page, client))[name] for name in "ab")
    assert (a["x"], a["w"], b["x"], b["w"]) == (20, 15, 45, 15)
