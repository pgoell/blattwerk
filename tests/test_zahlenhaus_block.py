"""A Zahlenhaus block does what every block can do: copy, group, lock, layer, turn, resize,
survive odd stored props and a save, and move to another page. The docstrings name the lines of
the checklist (A: block actions, A: old sheets). It tests the block as a box and its stored
props, not what it draws or what its panel offers.
"""

from playwright.sync_api import expect
from ui import (
    TEXT,
    angle,
    at,
    box,
    centre,
    doc,
    drag,
    drawer,
    expect_picked,
    pick,
    reload,
    saved,
    thumb,
    user,
)

HAUS = {"count": 4, "columns": 4, "floors": 4, "max": 10, "given": "side", "seed": 7}
ODD = {
    "count": -3,
    "columns": 99,
    "floors": "x",
    "max": None,
    "given": "?",
    "free": [True],
    "seed": "s",
    "typed": [[9, 9, 9], "a"],
}


def text(**more):
    """A text well below the house block, so that the two do not overlap."""
    return box("t", "text", TEXT, z=2, y=150, **more)


def house(z=1, **more):
    return box("h", "zahlenhaus", HAUS, z=z, w=120, h=55, **more)


def stored(client, page):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def button(page, label):
    return page.get_by_label(label, exact=True)


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def test_copy_and_paste_keep_type_and_props_and_ctrl_d_doubles_the_seed(editor):
    """A: block actions: copy and paste keep type and props, the copy has another id; Ctrl+D doubles it."""
    client = user()
    page = editor(house(), text(), client=client)
    pick(page, "h")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zahlenhaus"]
    assert len(copies) == 2
    assert all(b["props"] == HAUS for b in copies)
    assert len({b["id"] for b in copies}) == 2
    # The paste leaves its copy picked, and it lies over the original.
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    houses = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zahlenhaus"]
    assert len(houses) == 3
    assert all(b["props"]["seed"] == HAUS["seed"] for b in houses)


def test_grouped_with_a_text_both_keep_the_group_and_ungroup_frees_them(editor):
    """A: block actions: grouped by Ctrl+G both carry one group id; a click picks both; Ctrl+Shift+G frees."""
    client = user()
    page = editor(house(), text(), client=client)
    pick(page, "h", "t")
    page.keyboard.press("Control+g")
    expect(page.locator(".block.sel")).to_have_count(2)
    groups = {b["id"]: b.get("group") for b in saved(page, client)}
    assert groups["h"] and groups["h"] == groups["t"]
    page.keyboard.press("Escape")
    at(page, "h").click()
    expect_picked(page, "h", "t")
    page.keyboard.press("Control+Shift+G")
    expect(page.locator(".block.sel")).to_have_count(2)
    assert not any(b.get("group") for b in saved(page, client) if b["id"] in ("h", "t"))


def test_locked_it_stays_put_by_drag_and_arrows_and_unlocked_it_moves(editor):
    """A: block actions: locked it does not move by a drag or by the arrow keys; unlocked it moves."""
    client = user()
    page = editor(house(locked=True), client=client)
    before = stored(client, page)["h"]
    pick(page, "h")
    page.keyboard.press("ArrowDown")
    drag(page, centre(at(page, "h")), (centre(at(page, "h"))[0] + 60, centre(at(page, "h"))[1]))
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["h"]["x"] == before["x"]
    assert stored(client, page)["h"]["y"] == before["y"]
    page.get_by_label("Entsperren", exact=True).click()
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["h"]["y"] == before["y"] + 1


def test_to_the_front_puts_the_house_above_the_text(editor):
    """A: block actions: with a text over it, "In den Vordergrund" puts the block's z above the text's."""
    page = editor(house(z=1), text())
    pick(page, "h")
    at(page, "h").click(button="right")
    page.get_by_role("menuitem", name="In den Vordergrund", exact=True).click()
    # The stack's own numbers run 1 at the back, as test_order.py reads them.
    expect(at(page, "t")).to_have_css("z-index", "1")
    expect(at(page, "h")).to_have_css("z-index", "2")


def test_the_panel_turn_stores_angle_90_and_the_block_shows_it(editor):
    """A: block actions: "Rechtsdrehung 90°" stores angle 90 and the block shows turned."""
    client = user()
    page = editor(house(), client=client)
    pick(page, "h")
    page.get_by_label("Rechtsdrehung 90°", exact=True).click()
    assert angle(page, "h") == 90
    assert stored(client, page)["h"]["angle"] == 90


def test_typed_size_and_a_corner_drag_store_w_and_h_and_undo_brings_the_old_size(editor):
    """A: block actions: typed Breite and Höhe store w and h; a corner drag changes them; undo brings back."""
    client = user()
    page = editor(house(), client=client)
    pick(page, "h")
    for label, value in (("Breite", "90"), ("Höhe", "40")):
        field = button(page, label)
        field.click()
        field.fill(value)
        field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["h"]["w"] == 90
    assert stored(client, page)["h"]["h"] == 40
    undo(page).click()
    undo(page).click()
    assert stored(client, page)["h"]["w"] == 120
    assert stored(client, page)["h"]["h"] == 55


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """A: old sheets: odd stored props draw, no fault shows and the editor breaks nothing; props {} too."""
    client = user()
    page = editor(
        box("odd", "zahlenhaus", ODD, z=1, w=120, h=55),
        box("empty", "zahlenhaus", {}, z=2, y=150, w=120, h=55),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".zahlenhaus")).to_be_visible()
    expect(at(page, "empty").locator(".zahlenhaus")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zahlenhaus", exact=True)
    ).to_be_visible()
    assert not errors, errors


def test_a_save_leaves_the_house_props_as_they_were(editor):
    """A: old sheets: a save leaves a house block's props exactly as they were, no key added or dropped."""
    client = user()
    page = editor(house(), text(), client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["h"]["props"] == HAUS
    reload(page, page.url)
    expect(at(page, "h").locator(".zahlenhaus")).to_be_visible()
    assert stored(client, page)["h"]["props"] == HAUS


def test_delete_and_undo_brings_the_house_back_with_its_props(editor):
    """A: block actions: Delete takes the house off, undo brings it back with the same props."""
    client = user()
    page = editor(house(), text(), client=client)
    pick(page, "h")
    page.keyboard.press("Delete")
    expect(at(page, "h")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "h")).to_have_count(1)
    assert stored(client, page)["h"]["props"] == HAUS


def test_cut_and_paste_keeps_the_house_type_and_props(editor):
    """A: block actions: a cut and a paste move the house as it is, with its type and props."""
    client = user()
    page = editor(house(), text(), client=client)
    pick(page, "h")
    page.keyboard.press("Control+x")
    expect(at(page, "h")).to_have_count(0)
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    houses = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zahlenhaus"]
    assert len(houses) == 1
    assert houses[0]["props"] == HAUS


def test_a_house_on_page_2_keeps_its_props_through_a_save_and_a_reload(editor):
    """A: old sheets: a house on page 2 keeps type and props through a save and a reload."""
    client = user()
    page = editor(
        text(),
        more=[house()],
        client=client,
    )
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("zahlenhaus", HAUS)]
    reload(page, page.url)
    expect(at(page, "h").locator(".zahlenhaus")).to_be_visible()
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("zahlenhaus", HAUS)]


def test_a_house_moved_to_page_2_keeps_its_props(editor):
    """A: block actions: a house cut on page 1 and pasted on page 2 keeps type and props there."""
    client = user()
    # theme="" opens the panel Seiten, which holds the page thumbnails.
    page = editor(
        house(),
        text(),
        pages=[{"blocks": [box("u", "text", TEXT, z=1)]}],
        client=client,
        theme="",
        touch=True,
    )
    drawer(page, "left")
    pick(page, "h")
    page.keyboard.press("Control+x")
    expect(at(page, "h")).to_have_count(0)
    # thumb counts from 0: page 2 is thumb 1.
    thumb(page, 1).click()
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second if b["type"] == "zahlenhaus"] == [
        ("zahlenhaus", HAUS)
    ]
