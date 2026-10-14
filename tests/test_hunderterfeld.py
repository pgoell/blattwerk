"""The Hunderterfeld: its format panel.

The docstrings name what each test proves. The drawing is tested with the model.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import box, doc, pick, user

TAFEL = {
    "look": "tafel",
    "from": 1,
    "show": "all",
    "hide": 20,
    "hidden": [],
    "tint": "none",
    "times": 2,
    "line": 1,
    "color": 1,
    "tints": [],
    "cut": False,
    "shape": [34, 43, 44, 45, 54],
    "given": 44,
    "fill": "count",
    "dots": 0,
    "filled": [],
    "seed": 7,
}


def feld(name, props, w=100):
    """A Hunderterfeld block of w by 100 mm."""
    return box(name, "hunderterfeld", props, w=w, h=100)


def props_of(stored):
    """The props of the one Hunderterfeld of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "hunderterfeld"]
    return block["props"]


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def square(page, v):
    return panel(page, f"Feld {v}")


@pytest.mark.parametrize(
    "key, base, before, after, act",
    [
        ("look", {}, "tafel", "punkte", lambda p: field(p, "Darstellung").select_option("punkte")),
        ("from", {}, 1, 0, lambda p: field(p, "Erste Zahl").select_option("0")),
        ("show", {}, "all", "none", lambda p: field(p, "Zahlen").select_option("none")),
        ("hide", {"show": "random"}, 20, 35, lambda p: field(p, "Verdeckt").fill("35")),
        ("tint", {}, "none", "even", lambda p: field(p, "Färben").select_option("even")),
        ("times", {"tint": "times"}, 2, 5, lambda p: field(p, "Reihe").fill("5")),
        ("line", {"tint": "row"}, 1, 4, lambda p: field(p, "Nummer").fill("4")),
        ("color", {"tint": "even"}, 1, 2, lambda p: field(p, "Farbe").select_option("2")),
        ("cut", {}, False, True, lambda p: field(p, "Ausschnitt").check()),
        (
            "fill",
            {"look": "punkte"},
            "count",
            "free",
            lambda p: field(p, "Füllen").select_option("free"),
        ),
        ("dots", {"look": "punkte"}, 0, 40, lambda p: field(p, "Gefüllt").fill("40")),
    ],
    ids=[
        "darstellung",
        "erste",
        "zahlen",
        "verdeckt",
        "faerben",
        "reihe",
        "nummer",
        "farbe",
        "ausschnitt",
        "fuellen",
        "gefuellt",
    ],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, base, before, after, act):
    """A Hunderterfeld setting stores its prop; Ctrl+Z brings the old value, Ctrl+Y the new."""
    client = user()
    page = editor(feld("h", {**TAFEL, **base}), client=client)
    pick(page, "h")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_typing_35_into_verdeckt_is_one_undo_step(editor):
    """Typing 35 digit by digit into Verdeckt is one step; one Ctrl+Z brings back 20."""
    client = user()
    page = editor(feld("h", {**TAFEL, "show": "random"}), client=client)
    pick(page, "h")
    number = field(page, "Verdeckt")
    step(page, lambda: (number.press("Control+a"), number.press_sequentially("35")))
    assert props_of(doc(page, client))["hide"] == 35
    undo(page)
    assert props_of(doc(page, client))["hide"] == 20


def test_neu_wuerfeln_stores_a_new_seed_and_keeps_the_rest(editor):
    """Neu würfeln changes the seed only; the hidden count and the other settings stay."""
    client = user()
    page = editor(feld("h", {**TAFEL, "show": "random", "hide": 30}), client=client)
    pick(page, "h")
    step(page, lambda: panel(page, "Neu würfeln").click())
    stored = props_of(doc(page, client))
    assert stored["seed"] != 7
    assert {**stored, "seed": 7} == {**TAFEL, "show": "random", "hide": 30}


@pytest.mark.parametrize(
    "base, prop, before, after_click",
    [
        ({"show": "free", "hidden": []}, "hidden", [], [34]),
        ({"tint": "free", "tints": []}, "tints", [], [[34, 1]]),
        ({"cut": True, "shape": [44], "given": 44}, "shape", [44], [34, 44]),
        ({"look": "punkte", "fill": "free", "filled": []}, "filled", [], [34]),
    ],
    ids=["verdecken", "faerben", "ausschnitt", "fuellen"],
)
def test_a_square_click_stores_its_list_and_undoes(editor, base, prop, before, after_click):
    """A click on square 35 sets its mode's list; Ctrl+Z brings the list back."""
    client = user()
    page = editor(feld("h", {**TAFEL, **base}), client=client)
    pick(page, "h")
    step(page, lambda: square(page, 35).click())
    assert props_of(doc(page, client))[prop] == after_click
    undo(page)
    assert props_of(doc(page, client))[prop] == before


def test_a_second_given_replaces_the_first(editor):
    """The cut-out has one given cell: a click on another shape cell moves the given."""
    client = user()
    page = editor(feld("h", {**TAFEL, "cut": True, "shape": [34, 44], "given": 34}), client=client)
    pick(page, "h")
    step(page, lambda: square(page, 45).click())
    stored = props_of(doc(page, client))
    assert (stored["given"], stored["shape"]) == (44, [34, 44])


def test_the_given_leaving_the_shape_hands_its_part_on_and_the_panel_marks_what_the_sheet_shows(
    editor,
):
    """A click on the given 45 takes it out: 35, the lowest left, is given on the sheet and in the
    panel; 45 clicked back comes in plain, not given."""
    client = user()
    page = editor(feld("h", {**TAFEL, "cut": True}), client=client)
    pick(page, "h")
    expect(square(page, 45)).to_have_attribute("data-cut", "given")
    step(page, lambda: square(page, 45).click())
    assert props_of(doc(page, client))["given"] == 34
    expect(square(page, 35)).to_have_attribute("data-cut", "given")
    shown = page.locator('.block[data-id="h"] text.given')
    expect(shown).to_have_text(["35"])
    step(page, lambda: square(page, 45).click())
    expect(square(page, 45)).to_have_attribute("data-cut", "in")
    expect(shown).to_have_text(["35"])


def test_klick_setzt_picks_the_mode_and_the_grid_marks_only_modes_that_are_on(editor):
    """With free tints and a cut-out, "Klick setzt" offers Färben and Ausschnitt (no Verdecken,
    which a cut-out ignores); a click in Färben tints, in Ausschnitt takes the square in. Stored
    tints show only while the tint is free."""
    client = user()
    props = {**TAFEL, "show": "free", "tint": "free", "tints": [[0, 2]], "cut": True}
    page = editor(feld("h", props), client=client)
    pick(page, "h")
    mode = field(page, "Klick setzt")
    expect(mode.locator("option")).to_have_text(["Färben", "Ausschnitt"])
    expect(square(page, 1)).to_have_attribute("data-tint", "2")
    step(page, lambda: square(page, 36).click())
    assert props_of(doc(page, client))["tints"] == [[0, 2], [35, 1]]
    mode.select_option("cut")
    step(page, lambda: square(page, 36).click())
    assert props_of(doc(page, client))["shape"] == [34, 35, 43, 44, 45, 54]
    expect(square(page, 36)).to_have_attribute("data-cut", "in")
    step(page, lambda: field(page, "Färben").select_option("even"))
    expect(square(page, 1)).not_to_have_attribute("data-tint", "2")


def test_zahlen_free_to_all_and_back_keeps_hidden(editor):
    """Switching Zahlen to all and back to free keeps the cells hidden by clicking."""
    client = user()
    page = editor(feld("h", {**TAFEL, "show": "free", "hidden": [34, 50]}), client=client)
    pick(page, "h")
    step(page, lambda: field(page, "Zahlen").select_option("all"))
    assert props_of(doc(page, client))["hidden"] == [34, 50]
    step(page, lambda: field(page, "Zahlen").select_option("free"))
    assert props_of(doc(page, client))["hidden"] == [34, 50]


def test_the_last_cell_out_of_the_ausschnitt_shows_a_hint(editor):
    """Taking the last cell out of the Ausschnitt shows a hint; a click puts it back."""
    client = user()
    page = editor(feld("h", {**TAFEL, "cut": True, "shape": [44], "given": 44}), client=client)
    pick(page, "h")
    hint = page.locator(".panel p.hint", has_text="Keine Felder im Ausschnitt")
    step(page, lambda: square(page, 45).click())
    assert props_of(doc(page, client))["shape"] == []
    expect(hint).to_have_count(1)
    step(page, lambda: square(page, 45).click())
    assert props_of(doc(page, client))["shape"] == [44]
    expect(hint).to_have_count(0)
