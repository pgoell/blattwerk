"""A Zahlenmauer block does what every block can do: copy, group, lock, layer, turn, resize, paint,
number, survive odd stored props and a save. The docstrings name the lines of the checklist (A17a,
A17b, A17c, A13, I3, A18). It tests the block as a box and its stored props, not what it shows.
"""

from playwright.sync_api import expect
from test_painter import paint
from ui import (
    TEXT,
    angle,
    at,
    box,
    centre,
    doc,
    drag,
    expect_picked,
    grow,
    pick,
    reload,
    saved,
    user,
)

WALL = {
    "base": 3,
    "count": 4,
    "columns": 2,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 7,
}
ODD = {
    "base": "x",
    "count": -3,
    "columns": 99,
    "max": None,
    "op": 7,
    "given": "?",
    "free": [True],
    "empty": "ja",
    "seed": "s",
    "typed": [[9, 9, 9], "a"],
}


def text(**more):
    """A text well below the wall, so that the two do not overlap."""
    return box("t", "text", TEXT, z=2, y=150, **more)


def wall(z=1, **more):
    return box("w", "zahlenmauer", WALL, z=z, w=180, h=60, **more)


def stored(client, page):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def button(page, label):
    return page.get_by_label(label, exact=True)


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def test_copy_and_paste_keep_type_and_props_and_ctrl_d_doubles_the_seed(editor):
    """A17a: copy and paste keep type and props, the copy has another id; Ctrl+D doubles it."""
    client = user()
    page = editor(wall(), text(), client=client)
    pick(page, "w")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zahlenmauer"]
    assert len(copies) == 2
    assert all(b["props"] == WALL for b in copies)
    assert len({b["id"] for b in copies}) == 2
    # The paste leaves its copy picked, and it lies over the original.
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    walls = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zahlenmauer"]
    assert len(walls) == 3
    assert all(b["props"]["seed"] == WALL["seed"] for b in walls)


def test_grouped_with_a_text_both_keep_the_group_and_ungroup_frees_them(editor):
    """A17b: grouped by Ctrl+G both carry one group id; a click picks both; Ctrl+Shift+G frees."""
    client = user()
    page = editor(wall(), text(), client=client)
    pick(page, "w", "t")
    page.keyboard.press("Control+g")
    expect(page.locator(".block.sel")).to_have_count(2)
    groups = {b["id"]: b.get("group") for b in saved(page, client)}
    assert groups["w"] and groups["w"] == groups["t"]
    page.keyboard.press("Escape")
    at(page, "w").click()
    expect_picked(page, "w", "t")
    page.keyboard.press("Control+Shift+G")
    expect(page.locator(".block.sel")).to_have_count(2)
    assert not any(b.get("group") for b in saved(page, client) if b["id"] in ("w", "t"))


def test_locked_it_stays_put_by_drag_and_arrows_and_unlocked_it_moves(editor):
    """A17b: locked it does not move by a drag or by the arrow keys; unlocked it moves."""
    client = user()
    page = editor(wall(locked=True), client=client)
    before = stored(client, page)["w"]
    pick(page, "w")
    page.keyboard.press("ArrowDown")
    drag(page, centre(at(page, "w")), (centre(at(page, "w"))[0] + 60, centre(at(page, "w"))[1]))
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["w"]["x"] == before["x"]
    assert stored(client, page)["w"]["y"] == before["y"]
    page.get_by_label("Entsperren", exact=True).click()
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["w"]["y"] == before["y"] + 1


def test_to_the_front_puts_the_wall_above_the_text(editor):
    """A17b: with a text over it, "In den Vordergrund" puts the wall's z above the text's."""
    page = editor(wall(z=1), text())
    pick(page, "w")
    at(page, "w").click(button="right")
    page.get_by_role("menuitem", name="In den Vordergrund", exact=True).click()
    # The stack's own numbers run 1 at the back, as test_order.py reads them.
    expect(at(page, "t")).to_have_css("z-index", "1")
    expect(at(page, "w")).to_have_css("z-index", "2")


def test_the_panel_turn_stores_angle_90_and_the_block_shows_it(editor):
    """A17b: "Rechtsdrehung 90°" stores angle 90 and the block shows turned."""
    client = user()
    page = editor(wall(), client=client)
    pick(page, "w")
    page.get_by_label("Rechtsdrehung 90°", exact=True).click()
    assert angle(page, "w") == 90
    assert stored(client, page)["w"]["angle"] == 90


def test_typed_size_and_a_corner_drag_store_w_and_h_and_undo_brings_the_old_size(editor):
    """A17b: typed Breite and Höhe store w and h; a corner drag changes them; undo brings back."""
    client = user()
    page = editor(wall(), client=client)
    pick(page, "w")
    for label, value in (("Breite", "90"), ("Höhe", "40")):
        field = button(page, label)
        field.click()
        field.fill(value)
        field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["w"]["w"] == 90
    assert stored(client, page)["w"]["h"] == 40
    grow(page, 30)
    assert stored(client, page)["w"]["w"] != 90
    undo(page).click()
    assert stored(client, page)["w"]["w"] == 90
    assert stored(client, page)["w"]["h"] == 40


def test_format_uebertragen_from_a_text_gives_the_wall_the_mark_and_keeps_its_props(editor):
    """A17c: from a text with mark "1." onto the wall: the wall gets "1.", its props unchanged."""
    client = user()
    page = editor(
        wall(),
        text(mark="1."),
        client=client,
    )
    before = stored(client, page)["w"]["props"]
    paint(page, "t", "w")
    assert stored(client, page)["w"].get("mark") == "1."
    assert stored(client, page)["w"]["props"] == before


def test_format_uebertragen_from_the_wall_gives_a_text_the_mark_and_changes_no_other_prop(editor):
    """A17c: from the wall with mark "a)" onto a text: the text gets the mark, the rest stays."""
    client = user()
    page = editor(
        wall(mark="a)"),
        text(),
        client=client,
    )
    before = stored(client, page)["t"]["props"]
    paint(page, "w", "t")
    assert stored(client, page)["t"].get("mark") == "a)"
    assert stored(client, page)["t"]["props"] == before


def test_a_wall_with_mark_shows_its_numbering(editor):
    """A13: a wall with mark "1." shows its numbering."""
    page = editor(wall(mark="1."))
    expect(at(page, "w").locator(".mark")).to_have_text("1.")


def test_numbering_1_2_3_in_the_panel_marks_a_wall_without_one(editor):
    """A13: "1 2 3" in the panel's Nummerierung sets a mark on a wall without one."""
    client = user()
    page = editor(wall(), client=client)
    pick(page, "w")
    page.locator(".panel").get_by_role("button", name="1 2 3", exact=True).first.click()
    expect(at(page, "w").locator(".mark")).to_be_visible()
    assert stored(client, page)["w"].get("mark")


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """I3: odd stored props draw, no fault shows and the editor breaks nothing; props {} too."""
    client = user()
    page = editor(
        box("odd", "zahlenmauer", ODD, z=1, w=180, h=60),
        box("empty", "zahlenmauer", {}, z=2, y=150, w=180, h=60),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".zahlenmauer")).to_be_visible()
    expect(at(page, "empty").locator(".zahlenmauer")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(page.locator(".panel .what")).to_have_text("Zahlenmauer")
    assert not errors, errors


def test_a_save_leaves_the_wall_props_as_they_were(editor):
    """A18: a save leaves a wall block's props exactly as they were."""
    client = user()
    page = editor(wall(), text(), client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["w"]["props"] == WALL
    reload(page, page.url)
    expect(at(page, "w").locator(".zahlenmauer")).to_be_visible()
    assert stored(client, page)["w"]["props"] == WALL


def test_delete_and_undo_brings_the_wall_back_with_its_props(editor):
    """Own case: Delete takes the wall off, undo brings it back with the same props."""
    client = user()
    page = editor(wall(), text(), client=client)
    pick(page, "w")
    page.keyboard.press("Delete")
    expect(at(page, "w")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "w")).to_have_count(1)
    page.keyboard.press("Control+z")
    assert stored(client, page)["w"]["props"] == WALL


def test_cut_and_paste_keeps_the_wall_type_and_props(editor):
    """Own case: a cut and a paste move the wall as it is, with its type and props."""
    client = user()
    page = editor(wall(), text(), client=client)
    pick(page, "w")
    page.keyboard.press("Control+x")
    expect(at(page, "w")).to_have_count(0)
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    walls = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zahlenmauer"]
    assert len(walls) == 1
    assert walls[0]["props"] == WALL
