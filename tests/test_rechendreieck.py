"""The Rechendreieck: its block in the editor and its format panel.

The docstrings name the lines of the checklist that each test proves. The test of the wrong hint
waits for the real generator.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import box, doc, insert, pick, user

DREIECK = {
    "count": 4,
    "columns": 3,
    "max": 20,
    "given": "inner",
    "empty": False,
    "seed": 7,
}
FREE = [True, True, True, False, False, False]
TYPED = [[0, 0, 1], [0, 1, 1], [0, 2, 1], [0, 5, 5]]
INNER_TOP = "Zahl im Feld innen oben"


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Rechendreieck's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def dz(name, props):
    """A Rechendreieck block of 180 by 50 mm."""
    return box(name, "rechendreieck", props, w=180, h=50)


def props_of(stored):
    """The props of the one Rechendreieck of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "rechendreieck"]
    return block["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def test_the_bar_tool_adds_a_rechendreieck_with_the_default_props(editor):
    """A1: the bar's "Rechendreieck" adds a block with the default props and a whole seed."""
    client = user()
    page = editor(client=client)
    insert(page, "Rechendreieck")
    expect(
        page.locator(".panel").get_by_role("heading", name="Rechendreieck", exact=True)
    ).to_be_visible()
    props = props_of(doc(page, client))
    assert {k: v for k, v in props.items() if k != "seed"} == {
        "count": 4,
        "columns": 4,
        "max": 20,
        "given": "inner",
        "empty": False,
    }
    assert isinstance(props["seed"], int)


@pytest.mark.parametrize(
    "key, before, after, act",
    [
        ("count", 4, 5, lambda p: panel(p, "Ein Dreieck mehr").click()),
        ("columns", 3, 4, lambda p: panel(p, "Eine Spalte mehr").click()),
        ("max", 20, 100, lambda p: field(p, "Zahlenraum").select_option("100")),
        ("given", "inner", "outer", lambda p: field(p, "Gegebene Felder").select_option("outer")),
        ("empty", False, True, lambda p: panel(p, "Leer").click()),
    ],
    ids=["dreiecke", "spalten", "zahlenraum", "gegebene", "leer"],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, before, after, act):
    """A2/A3/A14: the setting changes its stored prop; Ctrl+Z brings the old, Ctrl+Y the new."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


@pytest.mark.parametrize(
    "setting, label",
    [
        ({"count": 1}, "Ein Dreieck weniger"),
        ({"count": 12}, "Ein Dreieck mehr"),
        ({"columns": 1}, "Eine Spalte weniger"),
        ({"columns": 4}, "Eine Spalte mehr"),
    ],
)
def test_the_triangles_and_columns_stop_at_their_limits(editor, setting, label):
    """A2: the weniger and mehr buttons are off at 1 and 12 triangles, 1 and 4 columns."""
    page = editor(dz("d", {**DREIECK, **setting}))
    pick(page, "d")
    expect(panel(page, label)).to_be_disabled()


def test_a_free_field_flips_and_the_warning_comes_and_goes(editor):
    """A7: with three given fields no warning; unchecking one shows it, checking it hides it."""
    client = user()
    page = editor(dz("d", {**DREIECK, "given": "free", "free": FREE}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_count(0)
    field_top = panel(page, "Feld innen oben")
    expect(field_top).to_have_attribute("aria-pressed", "true")
    step(page, field_top.click)
    assert props_of(doc(page, client))["free"][0] is False
    expect(field_top).to_have_attribute("aria-pressed", "false")
    expect(hint(page)).to_have_text("Die gegebenen Felder legen das Dreieck nicht fest.")
    step(page, field_top.click)
    assert props_of(doc(page, client))["free"][0] is True
    expect(hint(page)).to_have_count(0)


def test_typing_a_number_stores_it_and_one_undo_takes_both_digits_back(editor):
    """A10/I1: 15 typed into the top inner field stores [[0, 0, 15]]; one Ctrl+Z removes both."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    number = field(page, INNER_TOP)
    # The field shows the generated number: select it, so that the two keys replace it.
    step(page, lambda: (number.press("Control+a"), number.press_sequentially("15")))
    assert props_of(doc(page, client))["typed"] == [[0, 0, 15]]
    undo(page)
    assert "typed" not in props_of(doc(page, client))


def test_each_field_is_its_own_undo_step(editor):
    """A10/I1: 7 and then 8 typed into two fields; one Ctrl+Z takes back only the second."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    step(page, lambda: field(page, INNER_TOP).fill("7"))
    step(page, lambda: field(page, "Zahl im Feld innen links").fill("8"))
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 7]]


def test_a_wrong_triangle_gives_its_hint_whichever_is_picked(editor):
    """A10: Dreieck 2 holds contradicting numbers; with Dreieck 1 picked its hint still shows."""
    page = editor(dz("d", {**DREIECK, "typed": [[1, 0, 1], [1, 1, 1], [1, 2, 1], [1, 5, 5]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Dreieck 2 geht mit diesen Zahlen nicht auf.")


def test_typed_numbers_that_allow_no_triangle_give_the_hint(editor):
    """A10: typed numbers that contradict (an outer not the sum of its inner ones) give the hint."""
    page = editor(dz("d", {**DREIECK, "typed": TYPED}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Dreieck 1 geht mit diesen Zahlen nicht auf.")


def test_new_dice_store_another_seed_and_keep_the_settings_and_typed(editor):
    """A11/I6: "Neu würfeln" stores another seed and keeps the rest; undo brings the old seed."""
    client = user()
    page = editor(dz("d", {**DREIECK, "typed": [[0, 0, 15]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != DREIECK["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    assert after["typed"] == [[0, 0, 15]]
    undo(page)
    assert props_of(doc(page, client))["seed"] == DREIECK["seed"]


@pytest.mark.parametrize(
    "start, act, key",
    [
        (
            {**DREIECK, "given": "free", "free": FREE},
            lambda p: panel(p, "Feld innen oben").click(),
            "free",
        ),
        (
            DREIECK,
            lambda p: (
                field(p, INNER_TOP).press("Control+a"),
                field(p, INNER_TOP).press_sequentially("15"),
            ),
            "typed",
        ),
        ({**DREIECK, "typed": [[0, 0, 15]]}, lambda p: panel(p, "Neu würfeln").click(), "seed"),
        (
            {**DREIECK, "typed": TYPED},
            lambda p: panel(p, "Eigene Zahlen entfernen").click(),
            "typed",
        ),
    ],
    ids=["frei", "tippen", "neu", "entfernen"],
)
def test_undo_and_redo_bring_back_each_change(editor, start, act, key):
    """A14: a free field, a typed number, Neu würfeln and Eigene Zahlen entfernen undo and redo."""
    client = user()
    page = editor(dz("d", start), client=client)
    pick(page, "d")
    before = props_of(doc(page, client)).get(key)
    step(page, lambda: act(page))
    after = props_of(doc(page, client)).get(key)
    assert after != before
    undo(page)
    assert props_of(doc(page, client)).get(key) == before
    redo(page)
    assert props_of(doc(page, client)).get(key) == after


def test_numbers_of_a_hidden_triangle_stay_when_the_count_goes_back(editor):
    """I8: a number of Dreieck 4 survives: count down to 3, type into Dreieck 1, count back to 4."""
    client = user()
    page = editor(dz("d", {**DREIECK, "typed": [[3, 0, 9]]}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Ein Dreieck weniger").click())
    step(page, lambda: field(page, INNER_TOP).fill("7"))
    step(page, lambda: panel(page, "Ein Dreieck mehr").click())
    assert sorted(props_of(doc(page, client))["typed"]) == [[0, 0, 7], [3, 0, 9]]


def test_remove_own_numbers_is_one_undo_step(editor):
    """ "Eigene Zahlen entfernen" drops every typed number; one Ctrl+Z brings them back."""
    client = user()
    page = editor(dz("d", {**DREIECK, "typed": TYPED}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == TYPED


def test_typing_goes_to_the_picked_triangle(editor):
    """Own case: with "Dreieck 2" picked, a typed number goes to that triangle."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    field(page, "Dreieck für eigene Zahlen").select_option("1")
    step(page, lambda: field(page, INNER_TOP).fill("6"))
    assert props_of(doc(page, client))["typed"] == [[1, 0, 6]]


def test_a_number_over_four_digits_is_refused(editor):
    """Own case: a fifth digit is not taken; the field keeps 1234 and stores that."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    number = field(page, INNER_TOP)
    step(page, lambda: number.fill("1234"))
    number.press("5")
    expect(number).to_have_value("1234")
    assert props_of(doc(page, client))["typed"] == [[0, 0, 1234]]
