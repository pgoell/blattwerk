"""A Hunderterfeld block does what every block can do: copy, group, lock, layer, turn, resize,
paint, number, survive odd stored props and a save. The docstrings name the lines of the
checklist (A12, A16, A17, I3). It tests the block as a box and its stored props, not what it
draws or what its panel offers. Being square, it keeps its shape on resize, as a picture does.
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

FELD = {
    "look": "tafel",
    "from": 1,
    "show": "random",
    "hide": 20,
    "hidden": [0, 5, 99],
    "tint": "free",
    "times": 2,
    "line": 1,
    "color": 2,
    "tints": [[11, 1], [12, 2]],
    "cut": True,
    "shape": [34, 43, 44, 45, 54],
    "given": 44,
    "fill": "free",
    "dots": 0,
    "filled": [3, 4],
    "seed": 7,
}
ODD = {
    "look": "??",
    "from": 5,
    "show": "x",
    "hide": "many",
    "hidden": "x",
    "tint": 3,
    "times": 0,
    "line": 99,
    "color": 9,
    "tints": [[3, 7], "a"],
    "cut": "ja",
    "shape": [200, 3, 3],
    "given": -4,
    "fill": "?",
    "dots": 500,
    "filled": "x",
    "seed": "s",
}


def text(**more):
    """A text below the field, so that the two do not overlap."""
    return box("t", "text", TEXT, z=2, y=150, **more)


def feld(z=1, **more):
    """A field of 100 by 100 mm, as the dock adds it."""
    return box("f", "hunderterfeld", FELD, z=z, w=100, h=100, **more)


def stored(client, page):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def button(page, label):
    return page.get_by_label(label, exact=True)


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def test_copy_and_paste_keep_type_and_props_and_ctrl_d_doubles_the_seed(editor):
    """A16: copy and paste keep type and props, the copy has another id; Ctrl+D doubles it."""
    client = user()
    page = editor(feld(), text(), client=client)
    pick(page, "f")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "hunderterfeld"]
    assert len(copies) == 2
    assert all(b["props"] == FELD for b in copies)
    assert len({b["id"] for b in copies}) == 2
    # The paste leaves its copy picked, and it lies over the original.
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    fields = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "hunderterfeld"]
    assert len(fields) == 3
    assert all(b["props"]["seed"] == FELD["seed"] for b in fields)


def test_grouped_with_a_text_both_keep_the_group_and_ungroup_frees_them(editor):
    """A16: grouped by Ctrl+G both carry one group id; a click picks both; Ctrl+Shift+G frees."""
    client = user()
    page = editor(feld(), text(), client=client)
    pick(page, "f", "t")
    page.keyboard.press("Control+g")
    expect(page.locator(".block.sel")).to_have_count(2)
    groups = {b["id"]: b.get("group") for b in saved(page, client)}
    assert groups["f"] and groups["f"] == groups["t"]
    page.keyboard.press("Escape")
    at(page, "f").click()
    expect_picked(page, "f", "t")
    page.keyboard.press("Control+Shift+G")
    expect(page.locator(".block.sel")).to_have_count(2)
    assert not any(b.get("group") for b in saved(page, client) if b["id"] in ("f", "t"))


def test_locked_it_stays_put_by_drag_and_arrows_and_unlocked_it_moves(editor):
    """A16: locked it does not move by a drag or by the arrow keys; unlocked it moves."""
    client = user()
    page = editor(feld(locked=True), client=client)
    before = stored(client, page)["f"]
    pick(page, "f")
    page.keyboard.press("ArrowDown")
    drag(page, centre(at(page, "f")), (centre(at(page, "f"))[0] + 60, centre(at(page, "f"))[1]))
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["f"]["x"] == before["x"]
    assert stored(client, page)["f"]["y"] == before["y"]
    page.get_by_label("Entsperren", exact=True).click()
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["f"]["y"] == before["y"] + 1


def test_to_the_front_puts_the_field_above_the_text(editor):
    """A16: with a text over it, "In den Vordergrund" puts the block's z above the text's."""
    page = editor(feld(z=1), text())
    pick(page, "f")
    at(page, "f").click(button="right")
    page.get_by_role("menuitem", name="In den Vordergrund", exact=True).click()
    # The stack's own numbers run 1 at the back, as test_order.py reads them.
    expect(at(page, "t")).to_have_css("z-index", "1")
    expect(at(page, "f")).to_have_css("z-index", "2")


def test_the_panel_turn_stores_angle_90_and_the_block_shows_it(editor):
    """A16: "Rechtsdrehung 90°" stores angle 90 and the block shows turned."""
    client = user()
    page = editor(feld(), client=client)
    pick(page, "f")
    page.get_by_label("Rechtsdrehung 90°", exact=True).click()
    assert angle(page, "f") == 90
    assert stored(client, page)["f"]["angle"] == 90


def test_typed_breite_stores_w_and_h_alike_and_undo_brings_the_old_size(editor):
    """Square: typing Breite 150 stores w and h both 150; undo gives 100 back."""
    client = user()
    page = editor(feld(), client=client)
    pick(page, "f")
    field = button(page, "Breite")
    field.click()
    field.fill("150")
    field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["f"]["w"] == 150
    assert stored(client, page)["f"]["h"] == 150
    undo(page).click()
    assert stored(client, page)["f"]["w"] == 100
    assert stored(client, page)["f"]["h"] == 100


def test_a_corner_drag_keeps_the_field_square(editor):
    """Square: a corner drag changes the size, and w stays equal to h."""
    client = user()
    page = editor(feld(), client=client)
    pick(page, "f")
    grow(page, 40)
    expect(page.locator(".block.sel")).to_have_count(1)
    stored_f = stored(client, page)["f"]
    assert stored_f["w"] != 100
    assert stored_f["w"] == stored_f["h"]


def test_the_field_shows_only_corner_handles_as_a_picture_does(editor):
    """Square: a picked field has its four corner handles and no edge handles."""
    page = editor(feld())
    pick(page, "f")
    expect(page.locator(".moveable-control.moveable-se")).to_have_count(1)
    expect(page.locator(".moveable-control.moveable-nw")).to_have_count(1)
    for edge in ("n", "e", "s", "w"):
        expect(page.locator(f".moveable-control.moveable-{edge}")).to_have_count(0)


def test_format_uebertragen_from_a_text_gives_the_field_the_mark_and_keeps_its_props(editor):
    """A16: from a text with mark "1." onto the field: it gets "1.", its props unchanged."""
    client = user()
    page = editor(feld(), text(mark="1."), client=client)
    before = stored(client, page)["f"]["props"]
    paint(page, "t", "f")
    assert stored(client, page)["f"].get("mark") == "1."
    assert stored(client, page)["f"]["props"] == before


def test_format_uebertragen_from_the_field_gives_a_text_the_mark_alone(editor):
    """A16: from the field with mark "a)" onto a text: the text gets the mark, the rest stays."""
    client = user()
    page = editor(feld(mark="a)"), text(), client=client)
    before = stored(client, page)["t"]["props"]
    paint(page, "f", "t")
    assert stored(client, page)["t"].get("mark") == "a)"
    assert stored(client, page)["t"]["props"] == before


def test_a_field_with_mark_shows_its_numbering(editor):
    """A12: a field block with mark "1." shows its numbering."""
    page = editor(feld(mark="1."))
    expect(at(page, "f").locator(".mark")).to_have_text("1.")


def test_numbering_1_2_3_in_the_panel_marks_a_field_without_one(editor):
    """A12: "1 2 3" in the panel's Nummerierung sets a mark on a field without one."""
    client = user()
    page = editor(feld(), client=client)
    pick(page, "f")
    page.locator(".panel").get_by_role("button", name="1 2 3", exact=True).first.click()
    expect(at(page, "f").locator(".mark")).to_be_visible()
    assert stored(client, page)["f"].get("mark")


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """I3: odd stored props draw, no fault shows and the editor breaks nothing; props {} too."""
    client = user()
    page = editor(
        box("odd", "hunderterfeld", ODD, z=1, w=100, h=100),
        box("empty", "hunderterfeld", {}, z=2, y=150, w=100, h=100),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".hunderterfeld")).to_be_visible()
    expect(at(page, "empty").locator(".hunderterfeld")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(page.locator(".panel .what")).to_have_text("Hunderterfeld")
    assert not errors, errors


def test_a_save_leaves_the_field_props_as_they_were(editor):
    """A17: a save leaves a field block's props exactly as they were, no key added or dropped."""
    client = user()
    page = editor(feld(), text(), client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["f"]["props"] == FELD
    reload(page, page.url)
    expect(at(page, "f").locator(".hunderterfeld")).to_be_visible()
    assert stored(client, page)["f"]["props"] == FELD


def test_delete_and_undo_brings_the_field_back_with_its_props(editor):
    """Own case: Delete takes the field off, undo brings it back with the same props."""
    client = user()
    page = editor(feld(), text(), client=client)
    pick(page, "f")
    page.keyboard.press("Delete")
    expect(at(page, "f")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "f")).to_have_count(1)
    page.keyboard.press("Control+z")
    assert stored(client, page)["f"]["props"] == FELD


def test_cut_and_paste_keeps_the_field_type_and_props(editor):
    """Own case: a cut and a paste move the field as it is, with its type and props."""
    client = user()
    page = editor(feld(), text(), client=client)
    pick(page, "f")
    page.keyboard.press("Control+x")
    expect(at(page, "f")).to_have_count(0)
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    fields = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "hunderterfeld"]
    assert len(fields) == 1
    assert fields[0]["props"] == FELD


def test_undo_of_a_paste_takes_the_copy_away_and_leaves_the_original(editor):
    """Own case: undo of a paste takes the copy away, the original keeps its type and props."""
    client = user()
    page = editor(feld(), text(), client=client)
    pick(page, "f")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    undo(page).click()
    expect(page.locator(".block[data-id]")).to_have_count(2)
    fields = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "hunderterfeld"]
    assert len(fields) == 1
    assert fields[0]["props"] == FELD


def test_a_field_on_page_2_keeps_its_props_through_a_save_and_a_reload(editor):
    """Own case: a field on page 2 keeps type and props through a save and a reload."""
    client = user()
    page = editor(text(), more=[feld()], client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("hunderterfeld", FELD)]
    reload(page, page.url)
    expect(at(page, "f").locator(".hunderterfeld")).to_be_visible()
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("hunderterfeld", FELD)]


def test_odd_field_props_survive_a_typed_breite_and_a_save(editor):
    """A17: a field with odd stored props keeps them when it is resized by the typed Breite."""
    client = user()
    page = editor(box("odd", "hunderterfeld", ODD, z=1, w=100, h=100), client=client)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    pick(page, "odd")
    field = button(page, "Breite")
    field.click()
    field.fill("120")
    field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["odd"]["w"] == 120
    assert stored(client, page)["odd"]["h"] == 120
    assert stored(client, page)["odd"]["props"] == ODD
    assert not errors, errors


def test_a_corner_resize_keeps_the_stored_props_seed_and_hidden_cells(editor):
    """A17: a corner drag changes the size only; the props stay as stored, seed too."""
    client = user()
    page = editor(feld(), client=client)
    pick(page, "f")
    grow(page, 40)
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["f"]["props"] == FELD
    reload(page, page.url)
    expect(at(page, "f").locator(".hunderterfeld")).to_be_visible()
    assert stored(client, page)["f"]["props"] == FELD


def test_a_field_picked_with_a_text_and_resized_by_breite_keeps_each_shape(editor):
    """Beyond: a field picked with a text, resized by Breite, stays square; the text, with no lock
    of its own, keeps its height (#122)."""
    client = user()
    page = editor(feld(), text(w=120, h=40), client=client)
    pick(page, "f", "t")
    field = button(page, "Breite")
    field.click()
    field.fill("150")
    field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(2)
    fields = stored(client, page)
    assert fields["f"]["w"] == fields["f"]["h"]
    assert (fields["t"]["w"], fields["t"]["h"]) == (150, 40)


def test_a_field_with_its_stored_hidden_and_tints_survives_a_corner_drag_and_a_reload(editor):
    """Beyond: a Tafel's hidden cells and tints stay through a resize and a reload."""
    client = user()
    page = editor(feld(), client=client)
    pick(page, "f")
    grow(page, 30)
    expect(page.locator(".block.sel")).to_have_count(1)
    reload(page, page.url)
    expect(at(page, "f").locator(".hunderterfeld")).to_be_visible()
    stored_f = stored(client, page)["f"]
    assert stored_f["props"]["hidden"] == [0, 5, 99]
    assert stored_f["props"]["tints"] == [[11, 1], [12, 2]]
