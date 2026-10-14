"""An Uhr block does what every block can do: copy, group, lock, layer, turn, resize, paint,
number, survive odd stored props and a save. The docstrings name the lines of the checklist
(A12, A16, A17, I3). It tests the block as a box and its stored props, not what it draws or
what its panel offers. Unlike a Hunderterfeld, it is not shape-locked: it shows all handles
and may change its aspect. Its clocks stay round, which another test covers.
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

UHR = {
    "numbers": "all",
    "minutes": True,
    "ring": False,
    "task": "read",
    "answer": "box",
    "format": "12",
    "region": "nach",
    "count": 4,
    "cols": 4,
    "step": 15,
    "fill": "free",
    "times": [210, 585, 720, 370],
    "seed": 3,
}
ODD = {"numbers": 7, "times": "x", "count": -3}


def text(**more):
    """A text below the clock (110 mm tall from 50), so that the two do not overlap."""
    return box("t", "text", TEXT, z=2, y=180, **more)


def uhr(z=1, **more):
    """A clock block of 180 by 110 mm, as a block of the page is."""
    return box("u", "uhr", UHR, z=z, w=180, h=110, **more)


def stored(client, page):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def button(page, label):
    return page.get_by_label(label, exact=True)


def test_copy_and_paste_keep_type_and_props_and_ctrl_d_doubles_the_seed(editor):
    """A16: copy and paste keep type and props, the copy has another id; Ctrl+D doubles it."""
    client = user()
    page = editor(uhr(), text(), client=client)
    pick(page, "u")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "uhr"]
    assert len(copies) == 2
    assert all(b["props"] == UHR for b in copies)
    assert len({b["id"] for b in copies}) == 2
    # The paste leaves its copy picked, and it lies over the original.
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    clocks = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "uhr"]
    assert len(clocks) == 3
    assert all(b["props"]["seed"] == UHR["seed"] for b in clocks)


def test_grouped_with_a_text_both_keep_the_group_and_ungroup_frees_them(editor):
    """A16: grouped by Ctrl+G both carry one group id; a click picks both; Ctrl+Shift+G frees."""
    client = user()
    page = editor(uhr(), text(), client=client)
    pick(page, "u", "t")
    page.keyboard.press("Control+g")
    expect(page.locator(".block.sel")).to_have_count(2)
    groups = {b["id"]: b.get("group") for b in saved(page, client)}
    assert groups["u"] and groups["u"] == groups["t"]
    page.keyboard.press("Escape")
    at(page, "u").click()
    expect_picked(page, "u", "t")
    page.keyboard.press("Control+Shift+G")
    expect(page.locator(".block.sel")).to_have_count(2)
    assert not any(b.get("group") for b in saved(page, client) if b["id"] in ("u", "t"))


def test_locked_it_stays_put_by_drag_and_arrows_and_unlocked_it_moves(editor):
    """A16: locked it does not move by a drag or by the arrow keys; unlocked it moves."""
    client = user()
    page = editor(uhr(locked=True), client=client)
    before = stored(client, page)["u"]
    pick(page, "u")
    page.keyboard.press("ArrowDown")
    drag(page, centre(at(page, "u")), (centre(at(page, "u"))[0] + 60, centre(at(page, "u"))[1]))
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["u"]["x"] == before["x"]
    assert stored(client, page)["u"]["y"] == before["y"]
    page.get_by_label("Entsperren", exact=True).click()
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["u"]["y"] == before["y"] + 1


def test_to_the_front_puts_the_clock_above_the_text(editor):
    """A16: with a text over it, "In den Vordergrund" puts the block's z above the text's."""
    page = editor(uhr(z=1), text())
    pick(page, "u")
    at(page, "u").click(button="right")
    page.get_by_role("menuitem", name="In den Vordergrund", exact=True).click()
    # The stack's own numbers run 1 at the back, as test_order.py reads them.
    expect(at(page, "t")).to_have_css("z-index", "1")
    expect(at(page, "u")).to_have_css("z-index", "2")


def test_the_panel_turn_stores_angle_90_and_the_block_shows_it(editor):
    """A16: "Rechtsdrehung 90°" stores angle 90 and the block shows turned."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    page.get_by_label("Rechtsdrehung 90°", exact=True).click()
    assert angle(page, "u") == 90
    assert stored(client, page)["u"]["angle"] == 90


def test_typed_breite_stores_w_and_keeps_h_and_undo_brings_the_old_width(editor):
    """Not square: typing Breite 150 stores w 150 and leaves h; undo gives 180 back."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    field = button(page, "Breite")
    field.click()
    field.fill("150")
    field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["u"]["w"] == 150
    assert stored(client, page)["u"]["h"] == 110
    undo(page).click()
    assert stored(client, page)["u"]["w"] == 180
    assert stored(client, page)["u"]["h"] == 110


def test_a_corner_drag_shows_all_handles_and_changes_the_size(editor):
    """Not shape-locked: a corner drag changes the size, and all eight handles show."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    grow(page, 40)
    expect(page.locator(".block.sel")).to_have_count(1)
    stored_u = stored(client, page)["u"]
    assert (stored_u["w"], stored_u["h"]) != (180, 110)
    for corner in ("nw", "ne", "sw", "se"):
        expect(page.locator(f".moveable-control.moveable-{corner}")).to_have_count(1)
    for edge in ("n", "e", "s", "w"):
        expect(page.locator(f".moveable-control.moveable-{edge}")).to_have_count(1)


def test_format_uebertragen_from_a_text_gives_the_clock_the_mark_and_keeps_its_props(editor):
    """A16: from a text with mark "1." onto the clock: it gets "1.", its props unchanged."""
    client = user()
    page = editor(uhr(), text(mark="1."), client=client)
    before = stored(client, page)["u"]["props"]
    paint(page, "t", "u")
    assert stored(client, page)["u"].get("mark") == "1."
    assert stored(client, page)["u"]["props"] == before


def test_format_uebertragen_from_the_clock_gives_a_text_the_mark_alone(editor):
    """A16: from the clock with mark "a)" onto a text: the text gets the mark, the rest stays."""
    client = user()
    page = editor(uhr(mark="a)"), text(), client=client)
    before = stored(client, page)["t"]["props"]
    paint(page, "u", "t")
    assert stored(client, page)["t"].get("mark") == "a)"
    assert stored(client, page)["t"]["props"] == before


def test_a_clock_with_mark_shows_its_numbering(editor):
    """A12: a clock block with mark "1." shows its numbering."""
    page = editor(uhr(mark="1."))
    expect(at(page, "u").locator(".mark")).to_have_text("1.")


def test_numbering_1_2_3_in_the_panel_marks_a_clock_without_one(editor):
    """A12: "1 2 3" in the panel's Nummerierung sets a mark on a clock without one."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    page.locator(".panel").get_by_role("button", name="1 2 3", exact=True).first.click()
    expect(at(page, "u").locator(".mark")).to_be_visible()
    assert stored(client, page)["u"].get("mark")


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """I3: odd stored props draw, no fault shows and the editor breaks nothing; props {} too."""
    client = user()
    page = editor(
        box("odd", "uhr", ODD, z=1, w=180, h=110),
        box("empty", "uhr", {}, z=2, y=150, w=180, h=110),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".uhr")).to_be_visible()
    expect(at(page, "empty").locator(".uhr")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(page.locator(".panel .what")).to_have_text("Uhr")
    assert not errors, errors


def test_a_save_leaves_the_clock_props_as_they_were(editor):
    """A17: a save leaves a clock block's props exactly as they were, no key added or dropped."""
    client = user()
    page = editor(uhr(), text(), client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["u"]["props"] == UHR
    reload(page, page.url)
    expect(at(page, "u").locator(".uhr")).to_be_visible()
    assert stored(client, page)["u"]["props"] == UHR


def test_delete_and_undo_brings_the_clock_back_with_its_props(editor):
    """Own case: Delete takes the clock off, undo brings it back with the same props."""
    client = user()
    page = editor(uhr(), text(), client=client)
    pick(page, "u")
    page.keyboard.press("Delete")
    expect(at(page, "u")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "u")).to_have_count(1)
    page.keyboard.press("Control+z")
    assert stored(client, page)["u"]["props"] == UHR


def test_cut_and_paste_keeps_the_clock_type_and_props(editor):
    """Own case: a cut and a paste move the clock as it is, with its type and props."""
    client = user()
    page = editor(uhr(), text(), client=client)
    pick(page, "u")
    page.keyboard.press("Control+x")
    expect(at(page, "u")).to_have_count(0)
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    clocks = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "uhr"]
    assert len(clocks) == 1
    assert clocks[0]["props"] == UHR


def test_undo_of_a_paste_takes_the_copy_away_and_leaves_the_original(editor):
    """Own case: undo of a paste takes the copy away, the original keeps its type and props."""
    client = user()
    page = editor(uhr(), text(), client=client)
    pick(page, "u")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    undo(page).click()
    expect(page.locator(".block[data-id]")).to_have_count(2)
    clocks = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "uhr"]
    assert len(clocks) == 1
    assert clocks[0]["props"] == UHR


def test_a_clock_on_page_2_keeps_its_props_through_a_save_and_a_reload(editor):
    """Own case: a clock on page 2 keeps type and props through a save and a reload."""
    client = user()
    page = editor(text(), more=[uhr()], client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("uhr", UHR)]
    reload(page, page.url)
    expect(at(page, "u").locator(".uhr")).to_be_visible()
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("uhr", UHR)]


def test_odd_clock_props_survive_a_typed_breite_and_a_save(editor):
    """A17: a clock with odd stored props keeps them when it is resized by the typed Breite."""
    client = user()
    page = editor(box("odd", "uhr", ODD, z=1, w=180, h=110), client=client)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    pick(page, "odd")
    field = button(page, "Breite")
    field.click()
    field.fill("120")
    field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["odd"]["w"] == 120
    assert stored(client, page)["odd"]["props"] == ODD
    assert not errors, errors


def test_a_corner_resize_keeps_the_stored_props_and_times(editor):
    """A17: a corner drag changes the size only; the props stay as stored, times too."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    grow(page, 40)
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["u"]["props"] == UHR
    reload(page, page.url)
    expect(at(page, "u").locator(".uhr")).to_be_visible()
    assert stored(client, page)["u"]["props"] == UHR


def test_a_clock_picked_with_a_text_and_resized_by_breite_keeps_each_shape(editor):
    """Beyond: a clock picked with a text, resized by Breite, takes the new width."""
    client = user()
    page = editor(uhr(), text(w=120, h=40), client=client)
    pick(page, "u", "t")
    field = button(page, "Breite")
    field.click()
    field.fill("150")
    field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(2)
    blocks = stored(client, page)
    assert blocks["u"]["w"] == 150
    assert blocks["t"]["h"] == 40


def test_a_clock_with_its_stored_times_survives_a_corner_drag_and_a_reload(editor):
    """Beyond: a clock's stored times and numbers stay through a resize and a reload."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    grow(page, 30)
    expect(page.locator(".block.sel")).to_have_count(1)
    reload(page, page.url)
    expect(at(page, "u").locator(".uhr")).to_be_visible()
    stored_u = stored(client, page)["u"]
    assert stored_u["props"]["times"] == [210, 585, 720, 370]
    assert stored_u["props"]["numbers"] == "all"
