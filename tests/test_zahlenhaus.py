"""The Zahlenhaus: its block in the editor and its format panel.

The docstrings name the lines of the checklist (#819) that each test proves.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

HAUS = {"count": 4, "columns": 4, "floors": 4, "max": 10, "given": "side", "seed": 7}
FREE = [True, True, True, False, False, False, False, False, False]
TYPED = [[0, 0, 9], [0, 1, 4], [0, 2, 5]]
GENAU = {"count": 4, "columns": 4, "floors": 4, "max": 10, "given": "side"}


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zahlenhaus's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def dz(name, props):
    """A Zahlenhaus block of 120 by 55 mm."""
    return box(name, "zahlenhaus", props, w=120, h=55)


def block_of(stored):
    """The one Zahlenhaus of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zahlenhaus"]
    return block


def props_of(stored):
    """The props of the one Zahlenhaus of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def house_box(page, house, box_index):
    """The box of a house on the block "d", which is drawn on the page."""
    return at(page, "d").locator(f'g.house[data-house="{house}"] g.box[data-box="{box_index}"]')


def given_boxes(page, house):
    """The box indexes of a house that show their number, in order."""
    shown = (
        at(page, "d")
        .locator(f'g.house[data-house="{house}"] g.box')
        .evaluate_all(
            "els => els.map((b) => [Number(b.dataset.box), !!b.querySelector('text.given')])",
        )
    )
    return [j for j, given in shown if given]


def test_the_bar_tool_adds_a_zahlenhaus_with_the_default_props(editor):
    """A1: the Mathe-Blöcke item "Zahlenhaus" adds a block with the default props and a whole seed."""
    client = user()
    page = editor(client=client)
    insert(page, "Zahlenhaus")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zahlenhaus", exact=True)
    ).to_be_visible()
    props = props_of(doc(page, client))
    assert {k: v for k, v in props.items() if k != "seed"} == GENAU
    assert isinstance(props["seed"], int)


@pytest.mark.parametrize(
    "key, before, after, act",
    [
        ("floors", 4, 7, lambda p: field(p, "Stockwerke").select_option("7")),
        ("count", 4, 5, lambda p: panel(p, "Ein Haus mehr").click()),
        ("columns", 4, 3, lambda p: panel(p, "Eine Spalte weniger").click()),
        ("max", 10, 20, lambda p: field(p, "Zahlenraum").select_option("20")),
        ("given", "side", "roof", lambda p: field(p, "Gegebene Felder").select_option("roof")),
        ("given", "side", "mix", lambda p: field(p, "Gegebene Felder").select_option("mix")),
        ("given", "side", "free", lambda p: field(p, "Gegebene Felder").select_option("free")),
    ],
    ids=["stockwerke", "haus", "spalte", "zahlenraum", "nur-dach", "gemischt", "freie-wahl"],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, before, after, act):
    """I1: the setting changes its stored prop; Ctrl+Z brings the old, Ctrl+Y the new."""
    client = user()
    page = editor(dz("d", HAUS), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_an_own_zahlenraum_stores_only_whole_numbers_from_2_to_1000(editor):
    """A4: Eigener and 37 store max 37; 1, 1001 and an empty field are not stored."""
    client = user()
    page = editor(dz("d", HAUS), client=client)
    pick(page, "d")
    field(page, "Zahlenraum").select_option(label="Eigener")
    step(page, lambda: field(page, "Eigener Zahlenraum").fill("37"))
    assert props_of(doc(page, client))["max"] == 37
    for text in ("1", "1001", ""):
        own = field(page, "Eigener Zahlenraum")
        own.fill(text)
        expect(own).to_have_value(text)
        assert props_of(doc(page, client))["max"] == 37


@pytest.mark.parametrize(
    "given, shown",
    [("side", [0, 1, 3, 5, 7]), ("roof", [0])],
    ids=["dach-und-eine-seite", "nur-dach"],
)
def test_the_given_boxes_show_their_numbers_in_every_house(editor, given, shown):
    """A5: "Dach und eine Seite" shows the roof and 4 left boxes per house, "Nur Dach" the roof."""
    page = editor(dz("d", {**HAUS, "given": given}))
    pick(page, "d")
    for house in range(4):
        expect(at(page, "d").locator(f'g.house[data-house="{house}"] text.given')).to_have_count(
            len(shown)
        )
        assert given_boxes(page, house) == shown


def test_mixed_shows_the_roof_and_one_box_of_each_floor(editor):
    """A5: "Gemischt" shows the roof and exactly one box of each floor, in every house."""
    page = editor(dz("d", {**HAUS, "given": "mix"}))
    pick(page, "d")
    for house in range(4):
        shown = given_boxes(page, house)
        assert len(shown) == 5
        assert shown[0] == 0
        for floor in range(4):
            assert sum(1 for j in shown if j in (1 + 2 * floor, 2 + 2 * floor)) == 1


def test_a_free_box_flips_shows_in_every_house_and_survives_a_reload(editor):
    """A6: "Stockwerk 2 rechts" flips free[4] and shows in every house; it survives a save and reload."""
    client = user()
    page = editor(dz("d", {**HAUS, "given": "free", "free": FREE}), client=client)
    pick(page, "d")
    right = panel(page, "Stockwerk 2 rechts")
    expect(right).to_have_attribute("aria-pressed", "false")
    step(page, right.click)
    assert props_of(doc(page, client))["free"][4] is True
    expect(right).to_have_attribute("aria-pressed", "true")
    for house in range(4):
        expect(house_box(page, house, 4).locator("text.given")).to_have_count(1)
    step(page, right.click)
    assert props_of(doc(page, client))["free"][4] is False
    for house in range(4):
        expect(house_box(page, house, 4).locator("text.given")).to_have_count(0)
    step(page, right.click)
    reload(page, page.url)
    pick(page, "d")
    expect(panel(page, "Stockwerk 2 rechts")).to_have_attribute("aria-pressed", "true")
    assert props_of(doc(page, client))["free"][4] is True


def test_typing_two_digits_into_the_roof_stores_them_and_one_undo_takes_both_back(editor):
    """A10/I1: "1" then "2" into "Zahl im Dach" store typed [[0, 0, 12]]; one Ctrl+Z removes both."""
    client = user()
    page = editor(dz("d", HAUS), client=client)
    pick(page, "d")
    number = field(page, "Zahl im Dach")

    def type_twelve():
        number.press("Control+a")
        number.press_sequentially("1")
        number.press_sequentially("2")

    step(page, type_twelve)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 12]]
    undo(page)
    assert "typed" not in props_of(doc(page, client))


def test_a_floor_that_misses_the_roof_gives_the_hint_and_fixing_it_removes_it(editor):
    """A10: roof 9 with floor 1 typed 3 and 3 gives "Haus 1: Stockwerk 1 ergibt nicht 9."; 6 on the right clears it."""
    client = user()
    page = editor(dz("d", {**HAUS, "typed": [[0, 0, 9], [0, 1, 3], [0, 2, 3]]}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_text("Haus 1: Stockwerk 1 ergibt nicht 9.")
    step(page, lambda: field(page, "Zahl in Stockwerk 1 rechts").fill("6"))
    expect(hint(page)).to_have_count(0)


def test_remove_own_numbers_is_one_undo_step(editor):
    """I5: "Eigene Zahlen entfernen" clears every typed number in one step; one Ctrl+Z brings them back."""
    client = user()
    page = editor(dz("d", {**HAUS, "typed": TYPED}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == TYPED


def test_new_dice_store_another_seed_and_keep_the_other_props(editor):
    """A: "Neu würfeln" stores another seed and keeps the other props; undo brings the old seed back."""
    client = user()
    page = editor(dz("d", {**HAUS, "typed": [[0, 0, 15]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != HAUS["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == HAUS["seed"]


def test_a_new_number_of_floors_keeps_the_free_flags_and_typed_numbers_that_still_fit(editor):
    """I4: more Stockwerke keep the free flags (the new floor takes the side flags) and the typed
    numbers; fewer drop those of the floors gone."""
    client = user()
    page = editor(dz("d", {**HAUS, "given": "free", "free": FREE, "typed": TYPED}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Stockwerke").select_option("5"))
    props = props_of(doc(page, client))
    assert props["floors"] == 5
    assert props["free"] == [*FREE, True, False]
    assert props["typed"] == TYPED
    expect(field(page, "Zahl im Dach")).to_have_value("9")
    step(page, lambda: field(page, "Stockwerke").select_option("2"))
    assert props_of(doc(page, client))["free"] == FREE[:5]
    # Floor 1's typed boxes are still there, so its numbers stay.
    expect(field(page, "Zahl in Stockwerk 1 links")).to_have_value("4")


def test_an_undo_of_an_own_zahlenraum_shows_the_old_entry_in_the_select(editor):
    """B of the review: after "Eigener" and 37, one undo brings max 10 back and the select says "bis 10"."""
    client = user()
    page = editor(dz("d", HAUS), client=client)
    pick(page, "d")
    field(page, "Zahlenraum").select_option("own")
    own = field(page, "Eigener Zahlenraum")
    step(page, lambda: own.fill("37"))
    assert props_of(doc(page, client))["max"] == 37
    undo(page)
    assert props_of(doc(page, client))["max"] == 10
    expect(field(page, "Zahlenraum")).to_have_value("10")
    expect(field(page, "Eigener Zahlenraum")).to_have_count(0)


def test_a_new_number_of_floors_grows_the_block_and_undo_brings_its_height_back(editor):
    """I2: Stockwerke 4 to 10 makes the stored block taller; one Ctrl+Z brings the old height back."""
    client = user()
    page = editor(dz("d", HAUS), client=client)
    pick(page, "d")
    assert block_of(doc(page, client))["h"] == 55
    step(page, lambda: field(page, "Stockwerke").select_option("10"))
    assert block_of(doc(page, client))["h"] > 55
    undo(page)
    assert block_of(doc(page, client))["h"] == 55
