"""The Malquadrat on screen: its block in the editor and its format panel.

The docstrings name the lines of the contract (#826, top of frontend/src/malquadrat.ts) and of the panel that each test
proves. The numbers are read from the page, never pinned: the generator may change.
"""

import re

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

MQ = {
    "count": 2,
    "columns": 2,
    "size": 3,
    "op": "*",
    "reihen": [2, 3, 4, 5, 6, 7, 8, 9],
    "max": 20,
    "task": "factors",
    "seed": 7,
}
DEFAULTS = {k: v for k, v in MQ.items() if k != "seed"}
TIMES = "\N{MULTIPLICATION SIGN}"
H = 96.52  # a stored height for the default block at 180 mm wide; the drawing does not depend on it
TYPED_WRONG = [
    [0, 0, 1, 2],
    [0, 1, 0, 3],
    [0, 1, 1, 7],
]  # column 1 = 2, row 1 = 3, cell (1, 1) = 7 is no 3 x 2


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Malquadrat's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def mq(name, props, **more):
    """A Malquadrat block of 180 mm wide."""
    return box(name, "malquadrat", props, w=180, h=H, **more)


def block_of(stored):
    """The one Malquadrat of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "malquadrat"]
    return block


def props_of(stored):
    """The props of the one Malquadrat of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def test_a_malquadrat_is_inserted_from_the_maths_menu_with_the_default_props(editor):
    """Insert (#826, the maths menu): "Malquadrat" adds a 180 mm wide block with the default props and a whole seed,
    drawn as 2 squares of 9 inner cells each, the corner "·", and with "factors" every row and column number shown."""
    client = user()
    page = editor(client=client)
    insert(page, "Malquadrat")
    expect(
        page.locator(".panel").get_by_role("heading", name="Malquadrat", exact=True)
    ).to_be_visible()
    stored = block_of(doc(page, client))
    assert stored["w"] == 180
    props = stored["props"]
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    drawn = page.locator(".malquadrat").first
    expect(drawn.locator("g.square")).to_have_count(2)
    expect(
        drawn.locator("g.square[data-square='0'] g.cell[data-row='1'][data-col='1']")
    ).to_have_count(1)
    expect(drawn.locator("g.square g.corner text.op")).to_have_text(["·", "·"])
    expect(
        drawn.locator("g.square[data-square='0'] g.cell[data-row='0'][data-col='1'] text.given")
    ).to_have_count(1)
    expect(
        drawn.locator("g.square[data-square='0'] g.cell[data-row='1'][data-col='0'] text.given")
    ).to_have_count(1)
    expect(
        drawn.locator("g.square[data-square='0'] g.cell[data-row='1'][data-col='1'] text.given")
    ).to_have_count(0)


@pytest.mark.parametrize(
    "start, key, before, after, act",
    [
        (
            {},
            "task",
            "factors",
            "mixed",
            lambda p: field(p, "Aufgabentyp").select_option(label="Rand und Innen gemischt"),
        ),
        (
            {"op": "+", "reihen": None, "max": 20},
            "op",
            "+",
            "*",
            lambda p: field(p, "Rechenart").select_option(label="Mal"),
        ),
        (
            {},
            "reihen",
            [2, 3, 4, 5, 6, 7, 8, 9],
            [2, 4, 5, 6, 7, 8, 9],
            lambda p: field(p, "3er-Reihe").uncheck(),
        ),
        (
            {"op": "+"},
            "max",
            20,
            100,
            lambda p: field(p, "Zahlenraum").select_option(label="bis 100"),
        ),
    ],
    ids=["aufgabentyp", "rechenart", "reihe", "zahlenraum"],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(
    editor, start, key, before, after, act
):
    """Panel (#826): each setting changes its stored prop; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    props = {**MQ, **start}
    if props.get("reihen") is None:
        props.pop("reihen", None)
    page = editor(mq("d", props), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_the_steppers_show_their_counts_and_stop_at_their_limits(editor):
    """Panel (#826): the steppers say "2 Malquadrate", "2 nebeneinander" and "3 by 3 Felder" at the start, and stop at
    1 and 4 squares, 1 and 3 squares side by side, and 2 and 4 inner cells per side."""
    page = editor(mq("d", MQ))
    pick(page, "d")
    expect(page.locator(".panel").get_by_text("2 Malquadrate", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("2 nebeneinander", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text(f"3 {TIMES} 3 Felder", exact=True)).to_be_visible()
    top = editor(mq("d", {**MQ, "count": 4, "columns": 3, "size": 4}))
    pick(top, "d")
    expect(panel(top, "Ein Malquadrat mehr")).to_be_disabled()
    expect(panel(top, "Mehr Malquadrate nebeneinander")).to_be_disabled()
    expect(panel(top, "Größer")).to_be_disabled()
    low = editor(mq("d", {**MQ, "count": 1, "columns": 1, "size": 2}))
    pick(low, "d")
    expect(panel(low, "Ein Malquadrat weniger")).to_be_disabled()
    expect(panel(low, "Weniger Malquadrate nebeneinander")).to_be_disabled()
    expect(panel(low, "Kleiner")).to_be_disabled()


def test_rechenart_plus_shows_the_zahlenraum_and_hides_the_reihen_and_the_corner_shows_plus(editor):
    """Rechenart (#826): "Plus" shows the select "Zahlenraum" and no Reihen checkbox, and the corner shows "+"; "Mal"
    the other way round, with the corner "·"."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    expect(page.locator(".panel").get_by_label("3er-Reihe", exact=True)).to_be_visible()
    expect(field(page, "Zahlenraum")).to_have_count(0)
    field(page, "Rechenart").select_option(label="Plus")
    expect(field(page, "Zahlenraum")).to_be_visible()
    expect(page.locator(".panel").get_by_label("3er-Reihe", exact=True)).to_have_count(0)
    expect(at(page, "d").locator("g.corner text.op").first).to_have_text("+")
    field(page, "Rechenart").select_option(label="Mal")
    expect(field(page, "Zahlenraum")).to_have_count(0)
    expect(page.locator(".panel").get_by_label("3er-Reihe", exact=True)).to_be_visible()
    expect(at(page, "d").locator("g.corner text.op").first).to_have_text("·")


def test_size_and_rechenart_changes_drop_typed_numbers_in_one_undo_step(editor):
    """Panel (#826): "Größer" and the Rechenart drop the typed numbers, each in one undo step with the change."""
    client = user()
    typed = [[0, 1, 1, 3]]
    page = editor(mq("d", {**MQ, "typed": typed}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Größer").click())
    stored = props_of(doc(page, client))
    assert stored["size"] == 4
    assert "typed" not in stored
    undo(page)
    stored = props_of(doc(page, client))
    assert (stored["size"], stored["typed"]) == (3, typed)
    step(page, lambda: field(page, "Rechenart").select_option(label="Plus"))
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == typed


def test_the_last_checked_reihe_is_disabled(editor):
    """Panel (#826): with one Reihe left checked, that checkbox is disabled; the others stay enabled."""
    page = editor(mq("d", {**MQ, "reihen": [7]}))
    pick(page, "d")
    expect(page.locator(".panel").get_by_label("7er-Reihe", exact=True)).to_be_disabled()
    expect(page.locator(".panel").get_by_label("2er-Reihe", exact=True)).to_be_enabled()


def test_typing_a_number_is_one_undo_step_and_the_box_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#826): typing "12" into "Zeile 1, Spalte 3" keeps the focus and both digits while the block
    redraws, stores a typed entry, and one Ctrl+Z in the box takes the whole number back."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    number = field(page, "Zeile 1, Spalte 3")
    number.click()
    number.press("Control+A")
    step(page, lambda: page.keyboard.type("12"))
    expect(number).to_be_focused()
    expect(number).to_have_value("12")
    assert [0, 1, 3, 12] in props_of(doc(page, client))["typed"]
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_the_first_typed_number_keeps_the_drawn_given_numbers_as_typed_entries(editor):
    """Eigene Zahlen (#826): the first number typed into an empty box stores the square's drawn given cells as typed
    entries too, so the typed entries are the drawn given numbers + 1."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    drawn = at(page, "d").locator("g.square[data-square='0'] text.given").count()
    boxes = page.locator(".panel").get_by_label(re.compile(r"^Zeile \d+, Spalte \d+$"))
    empty = next(b for b in boxes.all() if b.input_value() == "")
    empty.click()
    step(page, lambda: page.keyboard.type("1"))
    assert len(props_of(doc(page, client))["typed"]) == drawn + 1


def test_typed_numbers_win_and_the_square_works_out_from_them(editor):
    """Eigene Zahlen (#826): column number 1 = 3 and inner cell (1, 1) = 12 leave more than one way (the square is
    not fixed), so the hint says "Es gibt mehr als eine Lösung." for Malquadrat 1, and the square is not wrong."""
    typed = [[0, 0, 1, 3], [0, 1, 1, 12]]
    page = editor(mq("d", {**MQ, "typed": typed}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Malquadrat 1: Es gibt mehr als eine Lösung.")
    expect(at(page, "d").locator("g.square.wrong")).to_have_count(0)


def test_typed_numbers_that_do_not_fit_give_the_hint_and_mark_the_square_wrong(editor):
    """Eigene Zahlen (#826): column number 1 = 2, row number 1 = 3 and cell (1, 1) = 7 fit no square: the hint names
    Malquadrat 1 and that square gets class wrong."""
    page = editor(mq("d", {**MQ, "typed": TYPED_WRONG}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Malquadrat 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.square.wrong")).to_have_count(1)
    expect(at(page, "d").locator("g.square[data-square='0'].wrong")).to_have_count(1)


@pytest.mark.parametrize(
    ("op", "typed"),
    [
        # Plus 2 by 2 with only the total 2: row and column numbers 1, 0 and 0, 0 fit.
        ("+", [[0, 3, 3, 2]]),
        # Mal 2 by 2 with only the total 7 and row sum 1 is 7: rows 1 and 0, columns 7 and 0 fit.
        ("*", [[0, 3, 3, 7], [0, 1, 3, 7]]),
        # Mal 3 by 3 with the cells of one row and one column sum far from the first tries: 3 * 40 = 120, 3 * 50 = 150,
        # column 1 sum 120 + 2 * 40 = 200 with rows 3, 1 and 1.
        ("*", [[0, 1, 1, 120], [0, 1, 2, 150], [0, 4, 1, 200]]),
    ],
    ids=["plus-total", "mal-total-and-row-sum", "mal-far"],
)
def test_typed_numbers_that_fit_give_no_wrong_hint(editor, op, typed):
    """Eigene Zahlen (#826): typed numbers that fit some Malquadrat never give "Die Zahlen passen nicht zusammen";
    the square says there is more than one solution instead."""
    size = 3 if len(typed) == 3 else 2
    page = editor(mq("d", {**MQ, "op": op, "size": size, "count": 1, "typed": typed}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Malquadrat 1: Es gibt mehr als eine Lösung.")
    expect(at(page, "d").locator("g.square.wrong")).to_have_count(0)


def test_eigene_zahlen_entfernen_is_one_undo_step_and_removes_the_hint(editor):
    """Eigene Zahlen (#826): "Eigene Zahlen entfernen" clears every typed number and the hint in one step; one Ctrl+Z
    brings them back."""
    client = user()
    page = editor(mq("d", {**MQ, "typed": TYPED_WRONG}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_count(1)
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    expect(hint(page)).to_have_count(0)
    undo(page)
    assert props_of(doc(page, client))["typed"] == TYPED_WRONG
    expect(hint(page)).to_have_count(1)


def test_neu_wuerfeln_changes_only_the_seed(editor):
    """Panel (#826): "Neu würfeln" stores another seed and keeps the other props; undo brings the old seed back."""
    client = user()
    page = editor(mq("d", {**MQ, "typed": [[0, 1, 1, 5]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != MQ["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == MQ["seed"]


def test_one_more_square_grows_the_block_and_keeps_the_cell_size_in_one_undo(editor):
    """Layout (#826): one more square grows the block and keeps the cell size; one Ctrl+Z gives back the square and the
    height."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    h0 = block_of(doc(page, client))["h"]
    before = at(page, "d").locator("g.cell rect").first.bounding_box()["width"]
    step(page, lambda: panel(page, "Ein Malquadrat mehr").click())
    grown = block_of(doc(page, client))
    assert grown["props"]["count"] == 3
    assert grown["h"] > h0
    after = at(page, "d").locator("g.cell rect").first.bounding_box()["width"]
    assert abs(after - before) <= before * 0.02, (before, after)
    undo(page)
    back = block_of(doc(page, client))
    assert back["props"]["count"] == 2
    assert abs(back["h"] - h0) < 0.2, back["h"]


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """Old sheets (#826): odd stored props still draw, the panel opens and no fault shows."""
    client = user()
    odd = {
        **MQ,
        "count": -3,
        "columns": 99,
        "size": 9,
        "op": "x",
        "reihen": [],
        "task": "nope",
        "max": None,
        "typed": [[9, 9, 9, 9], "junk"],
        "seed": "s",
    }
    page = editor(mq("odd", odd, z=1), mq("empty", {}, z=2, y=150), client=client)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".malquadrat")).to_be_visible()
    expect(at(page, "empty").locator(".malquadrat")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Malquadrat", exact=True)
    ).to_be_visible()
    assert not errors, errors


def test_a_reload_keeps_the_squares_the_size_and_the_typed_numbers(editor):
    """Panel (#826): 3 squares, size 4 and typed numbers survive a save and reload, and the block still draws them."""
    client = user()
    typed = [[0, 1, 1, 4]]
    page = editor(mq("d", {**MQ, "count": 3, "size": 4, "typed": typed}), client=client)
    pick(page, "d")
    doc(page, client)
    reload(page, page.url)
    pick(page, "d")
    expect(page.locator(".panel").get_by_text("3 Malquadrate", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text(f"4 {TIMES} 4 Felder", exact=True)).to_be_visible()
    props = props_of(doc(page, client))
    assert (props["count"], props["size"]) == (3, 4)
    assert props["typed"] == typed
    expect(at(page, "d").locator("g.square")).to_have_count(3)


def test_typed_entries_of_a_square_that_is_gone_stay_stored(editor):
    """Typed (#826): with 2 squares and typed numbers for square 1, "Ein Malquadrat weniger" leaves the block with one
    square and the typed entry for the gone square is still stored."""
    client = user()
    typed = [[0, 1, 1, 5], [1, 1, 1, 7]]
    page = editor(mq("d", {**MQ, "typed": typed}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Ein Malquadrat weniger").click())
    props = props_of(doc(page, client))
    assert props["count"] == 1
    assert [1, 1, 1, 7] in props["typed"]


def test_knobelaufgabe_gives_one_row_sum_and_hides_that_rows_number_and_its_cells(editor):
    """Aufgabentyp (#826): "Knobelaufgabe" shows one row sum, hides one row number and one column number, and gives one
    inner cell fewer than "Rand und Innen gemischt" (the hidden row has none)."""
    mixed = editor(mq("d", {**MQ, "task": "mixed"}))
    pick(mixed, "d")
    knobel = editor(mq("k", {**MQ, "task": "knobel"}))
    square = "g.square[data-square='0']"
    inner = "g.cell:not([data-row='0']):not([data-col='0']):not([data-row='4']):not([data-col='4'])"
    expect(at(knobel, "k").locator(f"{square} g.cell[data-col='0'] text.given")).to_have_count(2)
    expect(at(knobel, "k").locator(f"{square} g.cell[data-row='0'] text.given")).to_have_count(2)
    expect(at(knobel, "k").locator(f"{square} g.cell[data-col='4'] text.given")).to_have_count(1)
    expect(at(knobel, "k").locator(f"{square} {inner} text.given")).to_have_count(1)
    expect(at(mixed, "d").locator(f"{square} {inner} text.given")).to_have_count(2)
