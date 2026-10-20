"""A Zerlegungsfeld block does what every block can do: copy, group, lock, layer, turn, resize, survive odd
stored props and a save, and move to another page. The docstrings name the lines of the checklist
(#827: block actions, old sheets). It tests the block as a box and its stored props, not what it
draws or what its panel offers.
"""

from playwright.sync_api import expect
from test_templates_panel import apply as apply_template
from test_templates_panel import open_panel
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

ZF = {
    "count": 6,
    "columns": 3,
    "op": "+",
    "max": 20,
    "step": "zehner",
    "big": False,
    "task": "task",
    "seed": 7,
}
ODD = {
    "count": -3,
    "columns": 99,
    "op": "x",
    "max": None,
    "step": "x",
    "big": "x",
    "task": 7,
    "typed": [[9, 9, 9], "a"],
    "seed": "s",
}
H = 128.9  # the default height: 111 * 180 / 155


def text(**more):
    """A text well below the Zerlegungsfeld block, so that the two do not overlap."""
    return box("t", "text", TEXT, z=2, y=150, **more)


def fields(z=1, **more):
    return box("k", "zerlegungsfeld", ZF, z=z, w=180, h=H, **more)


def stored(client, page):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def button(page, label):
    return page.get_by_label(label, exact=True)


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def zerlegungen(client, page):
    return [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zerlegungsfeld"]


def test_copy_and_paste_keep_type_and_props_and_ctrl_d_doubles_the_seed(editor):
    """Block actions: copy and paste keep type and props, the copy has another id; Ctrl+D doubles it."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "k")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = zerlegungen(client, page)
    assert len(copies) == 2
    assert all(b["props"] == ZF for b in copies)
    assert len({b["id"] for b in copies}) == 2
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(4)
    assert len(zerlegungen(client, page)) == 3
    assert all(b["props"]["seed"] == ZF["seed"] for b in zerlegungen(client, page))


def test_grouped_with_a_text_both_keep_the_group_and_ungroup_frees_them(editor):
    """Block actions: grouped by Ctrl+G both carry one group id; a click picks both; Ctrl+Shift+G frees."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "k", "t")
    page.keyboard.press("Control+g")
    expect(page.locator(".block.sel")).to_have_count(2)
    groups = {b["id"]: b.get("group") for b in saved(page, client)}
    assert groups["k"] and groups["k"] == groups["t"]
    page.keyboard.press("Escape")
    at(page, "k").click()
    expect_picked(page, "k", "t")
    page.keyboard.press("Control+Shift+G")
    expect(page.locator(".block.sel")).to_have_count(2)
    assert not any(b.get("group") for b in saved(page, client) if b["id"] in ("k", "t"))


def test_locked_it_stays_put_by_drag_and_arrows_and_unlocked_it_moves(editor):
    """Block actions: locked it does not move by a drag or by the arrow keys; unlocked it moves."""
    client = user()
    page = editor(fields(locked=True), client=client)
    before = stored(client, page)["k"]
    pick(page, "k")
    page.keyboard.press("ArrowDown")
    drag(page, centre(at(page, "k")), (centre(at(page, "k"))[0] + 60, centre(at(page, "k"))[1]))
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["k"]["x"] == before["x"]
    assert stored(client, page)["k"]["y"] == before["y"]
    page.get_by_label("Entsperren", exact=True).click()
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["k"]["y"] == before["y"] + 1


def test_to_the_front_puts_the_zerlegungsfeld_above_the_text(editor):
    """Block actions: with a text over it, "In den Vordergrund" puts the block's z above the text's."""
    page = editor(fields(z=1), text())
    pick(page, "k")
    at(page, "k").click(button="right")
    page.get_by_role("menuitem", name="In den Vordergrund", exact=True).click()
    # The stack's own numbers run 1 at the back, as test_order.py reads them.
    expect(at(page, "t")).to_have_css("z-index", "1")
    expect(at(page, "k")).to_have_css("z-index", "2")


def test_the_panel_turn_stores_angle_90_and_the_block_shows_it(editor):
    """Block actions: "Rechtsdrehung 90°" stores angle 90 and the block shows turned."""
    client = user()
    page = editor(fields(), client=client)
    pick(page, "k")
    page.get_by_label("Rechtsdrehung 90°", exact=True).click()
    assert angle(page, "k") == 90
    assert stored(client, page)["k"]["angle"] == 90


def test_typed_size_and_a_corner_drag_store_w_and_h_and_undo_brings_the_old_size(editor):
    """Block actions: typed Breite and Höhe store w and h; undo brings back the old size."""
    client = user()
    page = editor(fields(), client=client)
    pick(page, "k")
    for label, value in (("Breite", "90"), ("Höhe", "40")):
        field = button(page, label)
        field.click()
        field.fill(value)
        field.press("Enter")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["k"]["w"] == 90
    assert stored(client, page)["k"]["h"] == 40
    undo(page).click()
    undo(page).click()
    assert stored(client, page)["k"]["w"] == 180
    assert stored(client, page)["k"]["h"] == H


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """Old sheets: odd stored props draw, no fault shows and the editor breaks nothing; props {} too."""
    client = user()
    page = editor(
        box("odd", "zerlegungsfeld", ODD, z=1, w=180, h=H),
        box("empty", "zerlegungsfeld", {}, z=2, y=150, w=180, h=H),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".zerlegungsfeld")).to_be_visible()
    expect(at(page, "empty").locator(".zerlegungsfeld")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zerlegungsfeld", exact=True)
    ).to_be_visible()
    assert not errors, errors


def test_a_save_leaves_the_zerlegungsfeld_props_as_they_were(editor):
    """Old sheets: a save leaves a Zerlegungsfeld's props exactly as they were, no key added or dropped."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["k"]["props"] == ZF
    reload(page, page.url)
    expect(at(page, "k").locator(".zerlegungsfeld")).to_be_visible()
    assert stored(client, page)["k"]["props"] == ZF


def test_delete_and_undo_brings_the_zerlegungsfeld_back_with_its_props(editor):
    """Block actions: Delete takes the Zerlegungsfeld off, undo brings it back with the same props."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "k")
    page.keyboard.press("Delete")
    expect(at(page, "k")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "k")).to_have_count(1)
    assert stored(client, page)["k"]["props"] == ZF


def test_cut_and_paste_keeps_the_zerlegungsfeld_type_and_props(editor):
    """Block actions: a cut and a paste move the Zerlegungsfeld as it is, with its type and props."""
    client = user()
    page = editor(fields(), text(), client=client)
    pick(page, "k")
    page.keyboard.press("Control+x")
    expect(at(page, "k")).to_have_count(0)
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    found = zerlegungen(client, page)
    assert len(found) == 1
    assert found[0]["props"] == ZF


def test_a_zerlegungsfeld_on_page_2_keeps_its_props_through_a_save_and_a_reload(editor):
    """Old sheets: a Zerlegungsfeld on page 2 keeps type and props through a save and a reload."""
    client = user()
    page = editor(text(), more=[fields()], client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("zerlegungsfeld", ZF)]
    reload(page, page.url)
    expect(at(page, "k").locator(".zerlegungsfeld")).to_be_visible()
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second] == [("zerlegungsfeld", ZF)]


def test_a_zerlegungsfeld_moved_to_page_2_keeps_its_props(editor):
    """Block actions: a Zerlegungsfeld cut on page 1 and pasted on page 2 keeps type and props there."""
    client = user()
    # theme="" opens the panel Seiten, which holds the page thumbnails.
    page = editor(
        fields(),
        text(),
        pages=[{"blocks": [box("u", "text", TEXT, z=1)]}],
        client=client,
        theme="",
        touch=True,
    )
    drawer(page, "left")
    pick(page, "k")
    page.keyboard.press("Control+x")
    expect(at(page, "k")).to_have_count(0)
    # thumb counts from 0: page 2 is thumb 1.
    thumb(page, 1).click()
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    second = doc(page, client)["pages"][1]["blocks"]
    assert [(b["type"], b["props"]) for b in second if b["type"] == "zerlegungsfeld"] == [
        ("zerlegungsfeld", ZF)
    ]


def test_a_template_with_a_zerlegungsfeld_gives_a_sheet_with_the_same_zerlegungsfeld(editor):
    """Templates: a template holding a Zerlegungsfeld, applied in the editor, gives a sheet whose
    Zerlegungsfeld keeps its type and props and draws its tasks."""
    client = user()
    body = {"pages": [{"blocks": [fields()]}]}
    made = client.post("/api/templates", json={"name": "Zerlegungsfelder", "doc": body})
    assert made.status_code == 200, made.text
    page = editor(box("a", "text", TEXT), client=client)
    open_panel(page)
    apply_template(page, "Zerlegungsfelder")
    expect(page.locator(".zerlegungsfeld").first).to_be_visible()
    found = zerlegungen(client, page)
    assert [b["props"] for b in found] == [ZF]
    expect(at(page, found[0]["id"]).locator("g.task")).to_have_count(ZF["count"])
