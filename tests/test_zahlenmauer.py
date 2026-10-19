"""The Zahlenmauer: its block in the editor and its format panel.

The docstrings name the lines of the checklist that each test proves. Tests that need the real
generator (the hint on too few walls, the wrong wall) wait for it.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import box, doc, insert, pick, user

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
FREE = [True, True, True, False, False, False]
TYPED = [[0, 0, 1], [0, 1, 1], [0, 2, 1], [0, 5, 5]]
ONE_STONE = "Zahl im Stein 1 der Reihe 1"


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zahlenmauer's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zw(name, props):
    """A Zahlenmauer block of 180 by 60 mm."""
    return box(name, "zahlenmauer", props, w=180, h=60)


def props_of(stored):
    """The props of the one Zahlenmauer of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zahlenmauer"]
    return block["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def test_the_bar_tool_adds_a_zahlenmauer_with_the_default_props(editor):
    """Z1: the bar's "Zahlenmauer" adds a block with the default props and a whole seed."""
    client = user()
    page = editor(client=client)
    insert(page, "Zahlenmauer")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zahlenmauer", exact=True)
    ).to_be_visible()
    props = props_of(doc(page, client))
    assert {k: v for k, v in props.items() if k != "seed"} == {
        "base": 3,
        "count": 4,
        "columns": 2,
        "max": 20,
        "op": "+",
        "given": "base",
        "empty": False,
    }
    assert isinstance(props["seed"], int)


@pytest.mark.parametrize(
    "label, key, before, after, act",
    [
        ("Grundsteine", "base", 3, 4, lambda p: field(p, "Grundsteine").select_option("4")),
        ("Mauern", "count", 4, 5, lambda p: panel(p, "Eine Mauer mehr").click()),
        ("Spalten", "columns", 2, 3, lambda p: panel(p, "Eine Spalte mehr").click()),
        ("Zahlenraum", "max", 20, 100, lambda p: field(p, "Zahlenraum").select_option("100")),
        ("Plus/Mal", "op", "+", "*", lambda p: panel(p, "Mal").click()),
        (
            "Gegebene Steine",
            "given",
            "base",
            "mix",
            lambda p: field(p, "Gegebene Steine").select_option("mix"),
        ),
        ("Leer", "empty", False, True, lambda p: panel(p, "Leer").click()),
    ],
    ids=["grundsteine", "mauern", "spalten", "zahlenraum", "plus-mal", "gegebene", "leer"],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(
    editor, label, key, before, after, act
):
    """Z2: the setting changes its stored prop; Ctrl+Z brings the old value, Ctrl+Y the new."""
    client = user()
    page = editor(zw("w", WALL), client=client)
    pick(page, "w")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


@pytest.mark.parametrize(
    "setting, label",
    [
        ({"count": 1}, "Eine Mauer weniger"),
        ({"count": 12}, "Eine Mauer mehr"),
        ({"columns": 1}, "Eine Spalte weniger"),
        ({"columns": 4}, "Eine Spalte mehr"),
    ],
)
def test_the_walls_and_columns_stop_at_their_limits(editor, setting, label):
    """Z2: the weniger and mehr buttons are off at 1 and 12 walls, 1 and 4 columns."""
    page = editor(zw("w", {**WALL, **setting}))
    pick(page, "w")
    expect(panel(page, label)).to_be_disabled()


def test_a_free_stone_flips_and_the_warning_comes_and_goes(editor):
    """Z3: a click flips a free stone; the warning shows while the base row is not whole."""
    client = user()
    page = editor(zw("w", {**WALL, "given": "free", "free": FREE}), client=client)
    pick(page, "w")
    stone = panel(page, "Stein 1 der Reihe 1")
    expect(stone).to_have_attribute("aria-pressed", "true")
    step(page, stone.click)
    assert props_of(doc(page, client))["free"][0] is False
    expect(stone).to_have_attribute("aria-pressed", "false")
    expect(hint(page)).to_have_text("Die gegebenen Steine legen die Mauer nicht fest.")
    step(page, stone.click)
    assert props_of(doc(page, client))["free"][0] is True
    expect(hint(page)).to_have_count(0)


def test_new_dice_store_another_seed_and_keep_the_typed_numbers(editor):
    """Z4: "Neu würfeln" stores another seed and keeps the rest; undo brings the old seed."""
    client = user()
    page = editor(zw("w", {**WALL, "typed": [[0, 0, 15]]}), client=client)
    pick(page, "w")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != WALL["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    assert after["typed"] == [[0, 0, 15]]
    undo(page)
    assert props_of(doc(page, client))["seed"] == WALL["seed"]


def test_too_few_walls_name_what_loosens_them(editor):
    """Z5: base 4, Zahlenraum 10, 8 walls: the hint names the ways out. Waits for the generator."""
    page = editor(zw("w", {**WALL, "base": 4, "max": 10, "count": 8}))
    pick(page, "w")
    expect(hint(page)).to_have_text(
        "Nur 6 Mauern möglich. Mehr gibt es mit: größerem Zahlenraum, weniger Grundsteinen."
    )


def test_typing_a_number_stores_it_and_one_undo_takes_both_digits_back(editor):
    """Z6: 15 typed into the first stone stores [[0, 0, 15]]; one Ctrl+Z removes it whole."""
    client = user()
    page = editor(zw("w", WALL), client=client)
    pick(page, "w")
    stone = field(page, ONE_STONE)
    step(page, lambda: stone.fill("15"))
    assert props_of(doc(page, client))["typed"] == [[0, 0, 15]]
    undo(page)
    assert "typed" not in props_of(doc(page, client))


def test_numbers_of_a_hidden_wall_stay_when_the_count_goes_back(editor):
    """Z6: a number of Mauer 4 survives: count down to 3, type into Mauer 1, count back to 4."""
    client = user()
    page = editor(zw("w", {**WALL, "typed": [[3, 0, 9]]}), client=client)
    pick(page, "w")
    step(page, lambda: panel(page, "Eine Mauer weniger").click())
    step(page, lambda: field(page, ONE_STONE).fill("7"))
    step(page, lambda: panel(page, "Eine Mauer mehr").click())
    assert sorted(props_of(doc(page, client))["typed"]) == [[0, 0, 7], [3, 0, 9]]


def test_each_stone_is_its_own_undo_step(editor):
    """Z6: 7 and then 8 typed into two stones; one Ctrl+Z takes back only the second."""
    client = user()
    page = editor(zw("w", WALL), client=client)
    pick(page, "w")
    step(page, lambda: field(page, ONE_STONE).fill("7"))
    step(page, lambda: field(page, "Zahl im Stein 2 der Reihe 1").fill("8"))
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 7]]


def test_emptying_a_number_field_removes_its_entry(editor):
    """Z6: emptying the field removes the entry; the stored props have no typed numbers left."""
    client = user()
    page = editor(zw("w", {**WALL, "typed": [[0, 0, 15]]}), client=client)
    pick(page, "w")
    step(page, lambda: field(page, ONE_STONE).fill(""))
    assert "typed" not in props_of(doc(page, client))


def test_typed_numbers_that_allow_no_wall_give_the_hint(editor):
    """Z6: typed 1, 1, 1 and a top 5 show the wrong hint. Waits for the generator."""
    page = editor(zw("w", {**WALL, "typed": TYPED}))
    pick(page, "w")
    expect(hint(page)).to_have_text("Mauer 1 geht mit diesen Zahlen nicht auf.")


def test_remove_own_numbers_removes_all_of_them(editor):
    """Z6: "Eigene Zahlen entfernen" removes every typed number."""
    client = user()
    page = editor(zw("w", {**WALL, "typed": TYPED}), client=client)
    pick(page, "w")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))


def type_and_remove(page, client):
    """Types a number other than the shown one into the first stone, then clicks "Eigene Zahlen entfernen".

    Returns the number the stone showed before typing and the number typed.
    """
    stone = field(page, ONE_STONE)
    shown = stone.input_value()
    digit = "7" if shown == "6" else "6"
    step(page, lambda: stone.fill(digit))
    for _ in range(50):
        if props_of(doc(page, client)).get("typed") == [[0, 0, int(digit)]]:
            break
        page.wait_for_timeout(100)
    assert props_of(doc(page, client))["typed"] == [[0, 0, int(digit)]]
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    return shown, digit


def test_910_after_remove_own_numbers_the_typed_box_shows_the_walls_number(editor):
    """#910: after "Eigene Zahlen entfernen" the box that had focus shows the number the sheet shows in it."""
    client = user()
    page = editor(zw("w", WALL), client=client)
    pick(page, "w")
    shown, _ = type_and_remove(page, client)
    expect(field(page, ONE_STONE)).to_have_value(shown)


def test_910_ctrl_z_in_a_box_brings_the_typed_numbers_back(editor):
    """#910: Ctrl+Z with the focus in a box is the sheet's undo: the typed number comes back and the box shows it."""
    client = user()
    page = editor(zw("w", WALL), client=client)
    pick(page, "w")
    _, digit = type_and_remove(page, client)
    field(page, ONE_STONE).focus()
    step(page, lambda: page.keyboard.press("Control+z"))
    assert props_of(doc(page, client))["typed"] == [[0, 0, int(digit)]]
    expect(panel(page, "Eigene Zahlen entfernen")).to_be_visible()
    expect(field(page, ONE_STONE)).to_have_value(digit)


def test_910_ctrl_y_right_after_ctrl_z_in_a_box_redoes_the_removal(editor):
    """#910: Ctrl+Y with the focus in a box is the sheet's redo: the removal comes back after the undo."""
    client = user()
    page = editor(zw("w", WALL), client=client)
    pick(page, "w")
    type_and_remove(page, client)
    field(page, ONE_STONE).focus()
    step(page, lambda: page.keyboard.press("Control+z"))
    step(page, lambda: page.keyboard.press("Control+y"))
    assert "typed" not in props_of(doc(page, client))


def test_changing_the_base_row_drops_free_and_typed(editor):
    """Z7: Grundsteine from 3 to 4 removes free and typed from the stored props."""
    client = user()
    page = editor(zw("w", {**WALL, "given": "free", "free": FREE, "typed": TYPED}), client=client)
    pick(page, "w")
    step(page, lambda: field(page, "Grundsteine").select_option("4"))
    stored = props_of(doc(page, client))
    assert stored["base"] == 4
    assert "free" not in stored and "typed" not in stored


def test_the_free_wall_has_a_button_per_stone(editor):
    """Own case: with "Freie Wahl" the panel shows six stone buttons, top row first."""
    page = editor(zw("w", WALL))
    pick(page, "w")
    field(page, "Gegebene Steine").select_option("free")
    expect(page.locator(".panel .mauer button")).to_have_count(6)
    expect(page.locator(".panel .mauer button").first).to_have_attribute(
        "aria-label", "Stein 1 der Reihe 3"
    )


def test_a_number_over_four_digits_is_refused(editor):
    """Own case: a fifth digit is not taken; the field keeps 1234 and stores that."""
    client = user()
    page = editor(zw("w", WALL), client=client)
    pick(page, "w")
    stone = field(page, ONE_STONE)
    step(page, lambda: stone.fill("1234"))
    stone.press("5")
    expect(stone).to_have_value("1234")
    assert props_of(doc(page, client))["typed"] == [[0, 0, 1234]]


# The words written beside a panel list, its options left out.
HEADING = "el => { const l = el.closest('label'); return l ? [...l.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim() : ''; }"


def test_the_lists_of_the_panel_say_what_they_set(editor):
    """#899: each list of the Zahlenmauer panel has its heading beside it, so "3" reads as Grundsteine."""
    page = editor(zw("w", WALL), client=user())
    pick(page, "w")
    headings = {
        "Grundsteine": "Grundsteine",
        "Zahlenraum": "Zahlenraum",
        "Gegebene Steine": "Gegebene Steine",
        "Mauer für eigene Zahlen": "Eigene Zahlen",
    }
    for name, heading in headings.items():
        assert page.locator(f'.panel select[aria-label="{name}"]').evaluate(HEADING) == heading, (
            name
        )
