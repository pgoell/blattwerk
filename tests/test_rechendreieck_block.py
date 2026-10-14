"""A Rechendreieck block does what every block can do: copy, group, lock, layer, turn, resize,
paint, number, survive odd stored props and a save. The docstrings name the lines of the
checklist (A12, A13, A16, A17, I3). It tests the block as a box and its stored props, not what it
draws or what its panel offers.
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

RECHEN = {
    "count": 4,
    "columns": 4,
    "max": 20,
    "given": "inner",
    "empty": False,
    "seed": 7,
}
ODD = {
    "count": -3,
    "columns": 99,
    "max": None,
    "given": "?",
    "free": [True],
    "empty": "ja",
    "seed": "s",
    "typed": [[9, 9, 9], "a"],
}


def text(**more):
    """A text well below the triangle block, so that the two do not overlap."""
    return box("t", "text", TEXT, z=2, y=150, **more)


def triangle(z=1, **more):
    return box("w", "rechendreieck", RECHEN, z=z, w=180, h=50, **more)


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
    page = editor(triangle(), text(), client=client)
    pick(page, "w")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "rechendreieck"]
    assert len(copies) == 2
    assert all(b["props"] == RECHEN for b in copies)
    assert len({b["id"] for b in copies}) == 2
    # The paste leaves its copy picked, and it lies over the original.
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    triangles = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "rechendreieck"]
    assert len(triangles) == 3
    assert all(b["props"]["seed"] == RECHEN["seed"] for b in triangles)


def test_grouped_with_a_text_both_keep_the_group_and_ungroup_frees_them(editor):
    """A16: grouped by Ctrl+G both carry one group id; a click picks both; Ctrl+Shift+G frees."""
    client = user()
    page = editor(triangle(), text(), client=client)
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
    """A16: locked it does not move by a drag or by the arrow keys; unlocked it moves."""
    client = user()
    page = editor(triangle(locked=True), client=client)
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


def test_to_the_front_puts_the_triangle_above_the_text(editor):
    """A16: with a text over it, "In den Vordergrund" puts the block's z above the text's."""
    page = editor(triangle(z=1), text())
    pick(page, "w")
    at(page, "w").click(button="right")
    page.get_by_role("menuitem", name="In den Vordergrund", exact=True).click()
    # The stack's own numbers run 1 at the back, as test_order.py reads them.
    expect(at(page, "t")).to_have_css("z-index", "1")
    expect(at(page, "w")).to_have_css("z-index", "2")


def test_the_panel_turn_stores_angle_90_and_the_block_shows_it(editor):
    """A16: "Rechtsdrehung 90°" stores angle 90 and the block shows turned."""
    client = user()
    page = editor(triangle(), client=client)
    pick(page, "w")
    page.get_by_label("Rechtsdrehung 90°", exact=True).click()
    assert angle(page, "w") == 90
    assert stored(client, page)["w"]["angle"] == 90


def test_typed_size_and_a_corner_drag_store_w_and_h_and_undo_brings_the_old_size(editor):
    """A16: typed Breite and Höhe store w and h; a corner drag changes them; undo brings back."""
    client = user()
    page = editor(triangle(), client=client)
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


def test_format_uebertragen_from_a_text_gives_the_triangle_the_mark_and_keeps_its_props(editor):
    """A16: from a text with mark "1." onto the triangle: it gets "1.", its props unchanged."""
    client = user()
    page = editor(
        triangle(),
        text(mark="1."),
        client=client,
    )
    before = stored(client, page)["w"]["props"]
    paint(page, "t", "w")
    assert stored(client, page)["w"].get("mark") == "1."
    assert stored(client, page)["w"]["props"] == before


def test_format_uebertragen_from_the_triangle_gives_a_text_the_mark_alone(editor):
    """A16: from the triangle with mark "a)" onto a text: the text gets the mark, the rest stays."""
    client = user()
    page = editor(
        triangle(mark="a)"),
        text(),
        client=client,
    )
    before = stored(client, page)["t"]["props"]
    paint(page, "w", "t")
    assert stored(client, page)["t"].get("mark") == "a)"
    assert stored(client, page)["t"]["props"] == before


def test_a_triangle_with_mark_shows_its_numbering(editor):
    """A12: a triangle block with mark "1." shows its numbering."""
    page = editor(triangle(mark="1."))
    expect(at(page, "w").locator(".mark")).to_have_text("1.")


def test_numbering_1_2_3_in_the_panel_marks_a_triangle_without_one(editor):
    """A13: "1 2 3" in the panel's Nummerierung sets a mark on a triangle without one."""
    client = user()
    page = editor(triangle(), client=client)
    pick(page, "w")
    page.locator(".panel").get_by_role("button", name="1 2 3", exact=True).first.click()
    expect(at(page, "w").locator(".mark")).to_be_visible()
    assert stored(client, page)["w"].get("mark")


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """I3: odd stored props draw, no fault shows and the editor breaks nothing; props {} too."""
    client = user()
    page = editor(
        box("odd", "rechendreieck", ODD, z=1, w=180, h=50),
        box("empty", "rechendreieck", {}, z=2, y=150, w=180, h=50),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".rechendreieck")).to_be_visible()
    expect(at(page, "empty").locator(".rechendreieck")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(page.locator(".panel .what")).to_have_text("Rechendreieck")
    assert not errors, errors


def test_a_save_leaves_the_triangle_props_as_they_were(editor):
    """A17: a save leaves a triangle block's props exactly as they were, no key added or dropped."""
    client = user()
    page = editor(triangle(), text(), client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["w"]["props"] == RECHEN
    reload(page, page.url)
    expect(at(page, "w").locator(".rechendreieck")).to_be_visible()
    assert stored(client, page)["w"]["props"] == RECHEN


def test_delete_and_undo_brings_the_triangle_back_with_its_props(editor):
    """Own case: Delete takes the triangle off, undo brings it back with the same props."""
    client = user()
    page = editor(triangle(), text(), client=client)
    pick(page, "w")
    page.keyboard.press("Delete")
    expect(at(page, "w")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "w")).to_have_count(1)
    page.keyboard.press("Control+z")
    assert stored(client, page)["w"]["props"] == RECHEN


def test_cut_and_paste_keeps_the_triangle_type_and_props(editor):
    """Own case: a cut and a paste move the triangle as it is, with its type and props."""
    client = user()
    page = editor(triangle(), text(), client=client)
    pick(page, "w")
    page.keyboard.press("Control+x")
    expect(at(page, "w")).to_have_count(0)
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    triangles = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "rechendreieck"]
    assert len(triangles) == 1
    assert triangles[0]["props"] == RECHEN


def test_undo_of_a_paste_takes_the_copy_away_and_leaves_the_original(editor):
    """Own case: undo of a paste takes the copy away, the original keeps its type and props."""
    client = user()
    page = editor(triangle(), text(), client=client)
    pick(page, "w")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    undo(page).click()
    expect(page.locator(".block[data-id]")).to_have_count(2)
    triangles = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "rechendreieck"]
    assert len(triangles) == 1
    assert triangles[0]["props"] == RECHEN


def test_a_triangle_on_page_2_keeps_its_props_through_a_save_and_a_reload(editor):
    """Own case: a triangle on page 2 keeps type and props through a save and a reload."""
    client = user()
    page = editor(
        text(),
        more=[triangle()],
        client=client,
    )
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("rechendreieck", RECHEN)]
    reload(page, page.url)
    expect(at(page, "w").locator(".rechendreieck")).to_be_visible()
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("rechendreieck", RECHEN)]
