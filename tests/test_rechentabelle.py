"""The Rechentabelle on screen: its block in the editor and its format panel.

The docstrings name the lines of the contract (#824, top of frontend/src/rechentabelle.ts) and of the panel
that each test proves. The numbers are read from the page, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

RT = {
    "count": 2,
    "columns": 2,
    "rows": 4,
    "cols": 4,
    "op": "+",
    "max": 20,
    "carry": "either",
    "reihen": [2, 4, 5, 10],
    "order": "related",
    "first": "all",
    "hideRows": 0,
    "hideCols": 0,
    "tint": "none",
    "seed": 7,
}
DEFAULTS = {k: v for k, v in RT.items() if k != "seed"}
H = 84.22  # a stored height; the drawing does not depend on it


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Rechentabelle's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def rt(name, props, **more):
    """A Rechentabelle block of 180 mm wide."""
    return box(name, "rechentabelle", props, w=180, h=H, **more)


def block_of(stored):
    """The one Rechentabelle of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "rechentabelle"]
    return block


def props_of(stored):
    """The props of the one Rechentabelle of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def values(page, axis="row", table=0):
    """The values of a table's rows (axis "row") or its columns, in order; None where a value is hidden."""
    return (
        at(page, "d")
        .locator(f"g.table[data-table='{table}']")
        .evaluate(
            """(t, axis) => {
        const own = axis === 'row' ? 'col' : 'row', pos = axis === 'row' ? 'row' : 'col';
        return [...t.querySelectorAll('g.head')]
          .filter(h => h.dataset[own] === '0')
          .sort((a, b) => a.dataset[pos] - b.dataset[pos])
          .map(h => { const x = h.querySelector('text'); return x && x.textContent ? Number(x.textContent) : null; });
      }""",
            axis,
        )
    )


def test_a_rechentabelle_is_inserted_from_the_maths_menu_with_the_default_props(editor):
    """Insert: the Mathe-Blöcke item "Rechentabelle" adds a 180 mm wide block with the default props and a whole seed, drawn as 2 tables with a corner each."""
    client = user()
    page = editor(client=client)
    insert(page, "Rechentabelle")
    expect(
        page.locator(".panel").get_by_role("heading", name="Rechentabelle", exact=True)
    ).to_be_visible()
    stored = block_of(doc(page, client))
    assert stored["w"] == 180
    props = stored["props"]
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    drawn = page.locator(".rechentabelle").first
    expect(drawn.locator("g.table")).to_have_count(2)
    expect(drawn.locator("g.corner")).to_have_count(2)


@pytest.mark.parametrize(
    "extra, key, before, after, act",
    [
        ({}, "count", 2, 3, lambda p: panel(p, "Eine Tabelle mehr").click()),
        ({}, "columns", 2, 3, lambda p: panel(p, "Mehr Tabellen nebeneinander").click()),
        ({}, "rows", 4, 5, lambda p: panel(p, "Eine Zeile mehr").click()),
        ({}, "cols", 4, 5, lambda p: panel(p, "Eine Spalte mehr").click()),
        ({}, "hideRows", 0, 1, lambda p: panel(p, "Ein versteckter Zeilenwert mehr").click()),
        ({}, "hideCols", 0, 1, lambda p: panel(p, "Ein versteckter Spaltenwert mehr").click()),
        ({}, "op", "+", "-", lambda p: field(p, "Rechenart").select_option("-")),
        ({}, "max", 20, 100, lambda p: field(p, "Zahlenraum").select_option("100")),
        ({}, "carry", "either", "none", lambda p: field(p, "Übertrag").select_option("none")),
        ({}, "tint", "none", "blue", lambda p: field(p, "Farbe").select_option("blue")),
        (
            {"op": "*"},
            "order",
            "related",
            "random",
            lambda p: field(p, "Anordnung").select_option("random"),
        ),
        (
            {"op": "*"},
            "first",
            "all",
            "kings",
            lambda p: field(p, "Erstfaktor").select_option("kings"),
        ),
        (
            {"op": "*"},
            "reihen",
            [2, 4, 5, 10],
            [2, 3, 4, 5, 10],
            lambda p: field(p, "3er-Reihe").check(),
        ),
    ],
    ids=[
        "tabellen",
        "nebeneinander",
        "zeilen",
        "spalten",
        "versteckte-zeilen",
        "versteckte-spalten",
        "rechenart",
        "zahlenraum",
        "uebertrag",
        "farbe",
        "anordnung",
        "erstfaktor",
        "reihe",
    ],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(
    editor, extra, key, before, after, act
):
    """Panel: each setting changes its stored prop; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    page = editor(rt("d", {**RT, **extra}), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_the_steppers_show_their_counts_and_stop_at_their_limits(editor):
    """Panel: the steppers say "2 Tabellen", "4 Zeilen", "4 Spalten" and "0 Zeilenwerte versteckt", and stop at 1 and 4 tables, 2 and 10 rows, 2 and 10 columns, 0 and rows minus 1 hidden."""
    page = editor(rt("d", RT))
    pick(page, "d")
    expect(page.locator(".panel").get_by_text("2 Tabellen", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("4 Zeilen", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("4 Spalten", exact=True)).to_be_visible()
    expect(
        page.locator(".panel").get_by_text("0 Zeilenwerte versteckt", exact=True)
    ).to_be_visible()
    expect(panel(page, "Eine Tabelle weniger")).to_be_enabled()
    top = editor(rt("d", {**RT, "count": 4, "rows": 10, "cols": 10, "hideRows": 9, "hideCols": 9}))
    pick(top, "d")
    expect(panel(top, "Eine Tabelle mehr")).to_be_disabled()
    expect(panel(top, "Eine Zeile mehr")).to_be_disabled()
    expect(panel(top, "Eine Spalte mehr")).to_be_disabled()
    expect(panel(top, "Ein versteckter Zeilenwert mehr")).to_be_disabled()
    expect(panel(top, "Ein versteckter Spaltenwert mehr")).to_be_disabled()
    low = editor(rt("d", {**RT, "count": 1, "rows": 2, "cols": 2}))
    pick(low, "d")
    expect(panel(low, "Eine Tabelle weniger")).to_be_disabled()
    expect(panel(low, "Eine Zeile weniger")).to_be_disabled()
    expect(panel(low, "Eine Spalte weniger")).to_be_disabled()
    expect(panel(low, "Ein versteckter Zeilenwert weniger")).to_be_disabled()


def test_fewer_rows_than_hidden_values_lowers_them_in_one_undo_step(editor):
    """Implied: with 3 hidden row values, going from 4 rows to 3 lowers the hidden count to 2 in the same step; one Ctrl+Z brings both back."""
    client = user()
    page = editor(rt("d", {**RT, "hideRows": 3}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eine Zeile weniger").click())
    props = props_of(doc(page, client))
    assert (props["rows"], props["hideRows"]) == (3, 2)
    undo(page)
    props = props_of(doc(page, client))
    assert (props["rows"], props["hideRows"]) == (4, 3)


@pytest.mark.parametrize(
    "op, label",
    [("+", "+"), ("-", "\N{MINUS SIGN}"), ("*", "\N{MIDDLE DOT}"), (":", ":")],
    ids=["plus", "minus", "mal", "geteilt"],
)
def test_the_corner_shows_the_operator(editor, op, label):
    """Drawing: the corner of each table shows the Rechenart: plus, minus, mal and Geteilt, as the operator sign."""
    page = editor(rt("d", {**RT, "op": op}))
    pick(page, "d")
    expect(at(page, "d").locator("g.table[data-table='0'] g.corner text.given")).to_have_text(label)


def test_mal_columns_are_the_chosen_reihen_in_related_order(editor):
    """Mal: the column values are the chosen Reihen; with Anordnung "Verwandte Reihen nebeneinander" in family order, with "Zufällig" the same set in a drawn order."""
    page = editor(rt("d", {**RT, "op": "*"}))
    pick(page, "d")
    assert values(page, "col") == [2, 4, 5, 10]
    shuffled = editor(rt("d", {**RT, "op": "*", "order": "random"}))
    pick(shuffled, "d")
    assert sorted(values(shuffled, "col")) == [2, 4, 5, 10]


def test_kings_gives_row_values_only_from_1_2_5_10(editor):
    """Mal: with Erstfaktor "Nur Königsaufgaben" every row value is 1, 2, 5 or 10."""
    page = editor(rt("d", {**RT, "op": "*", "first": "kings"}))
    pick(page, "d")
    rows = values(page, "row")
    assert rows and set(rows) <= {1, 2, 5, 10}, rows


def test_geteilt_strikes_exactly_the_cells_with_no_whole_answer(editor):
    """Geteilt: a cell with no whole answer (row value not divisible by column value) is struck through, every other cell is not."""
    page = editor(rt("d", {**RT, "op": ":"}))
    pick(page, "d")
    rows = values(page, "row")
    cols = values(page, "col")
    cells = (
        at(page, "d")
        .locator("g.table[data-table='0'] g.cell")
        .evaluate_all(
            "cells => cells.map(c => [Number(c.dataset.row), Number(c.dataset.col), !!c.querySelector('line.strike'), !!c.querySelector('text')])"
        )
    )
    assert len(cells) == len(rows) * len(cols)
    for r, c, strike, text in cells:
        whole = rows[r - 1] % cols[c - 1] == 0
        assert strike == (not whole), (r, c, rows[r - 1], cols[c - 1])
        if strike:
            assert not text, (r, c)


def test_hidden_values_leave_their_head_empty_and_give_a_cell(editor):
    """Hidden values: 2 row values and 1 column value hidden leave their heads empty, and each hidden value has a given cell of its row or column."""
    page = editor(rt("d", {**RT, "hideRows": 2, "hideCols": 1}))
    pick(page, "d")
    rows = values(page, "row")
    cols = values(page, "col")
    hidden_rows = [i for i, v in enumerate(rows, 1) if v is None]
    hidden_cols = [j for j, v in enumerate(cols, 1) if v is None]
    assert len(hidden_rows) == 2 and len(hidden_cols) == 1, (rows, cols)
    given = (
        at(page, "d")
        .locator("g.table[data-table='0'] g.cell text.given")
        .evaluate_all(
            "ts => ts.map(t => { const c = t.closest('g.cell'); return [Number(c.dataset.row), Number(c.dataset.col)]; })"
        )
    )
    for r in hidden_rows:
        assert any(gr == r and cols[gc - 1] is not None for gr, gc in given), (r, given)
    for c in hidden_cols:
        assert any(gc == c and rows[gr - 1] is not None for gr, gc in given), (c, given)


def test_typing_a_column_value_is_one_undo_step_and_changes_the_column(editor):
    """Eigene Zahlen: typing 7 into "Spaltenwert 1" stores [0, 0, 1, 7], the column shows 7, and one Ctrl+Z in the field takes it back."""
    client = user()
    page = editor(rt("d", RT), client=client)
    pick(page, "d")
    number = field(page, "Spaltenwert 1")
    number.click()
    step(page, lambda: page.keyboard.type("7"))
    assert props_of(doc(page, client))["typed"] == [[0, 0, 1, 7]]
    assert values(page, "col")[0] == 7
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_a_box_field_keeps_focus_and_digits_while_the_block_redraws(editor):
    """Eigene Zahlen: typing "17" into "Zeile 1, Spalte 3" keeps the focus and the digits, and stores [0, 1, 3, 17]."""
    client = user()
    page = editor(rt("d", RT), client=client)
    pick(page, "d")
    number = field(page, "Zeile 1, Spalte 3")
    number.click()
    step(page, lambda: page.keyboard.type("17"))
    expect(number).to_be_focused()
    expect(number).to_have_value("17")
    assert props_of(doc(page, client))["typed"] == [[0, 1, 3, 17]]
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_a_typed_cell_that_does_not_fit_gives_the_hint_and_marks_the_table_wrong(editor):
    """Eigene Zahlen: a typed 9999 in row 1, column 1 does not fit its row and column: the hint names Rechentabelle 1 and that table gets class wrong."""
    page = editor(rt("d", {**RT, "typed": [[0, 1, 1, 9999]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Rechentabelle 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.table.wrong")).to_have_count(1)
    expect(at(page, "d").locator("g.table[data-table='0'].wrong")).to_have_count(1)


def test_eigene_zahlen_entfernen_is_one_undo_step_and_removes_the_hint(editor):
    """Eigene Zahlen: "Eigene Zahlen entfernen" clears every typed number and the hint in one step; one Ctrl+Z brings them back."""
    client = user()
    typed = [[0, 1, 1, 9999]]
    page = editor(rt("d", {**RT, "typed": typed}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_count(1)
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    expect(hint(page)).to_have_count(0)
    undo(page)
    assert props_of(doc(page, client))["typed"] == typed
    expect(hint(page)).to_have_count(1)


def test_a_typed_zero_column_with_geteilt_is_wrong_and_shows_no_nan_or_infinity(editor):
    """Eigene Zahlen: with Geteilt a typed column value 0 gives the hint, marks the table wrong, and the drawing has no "NaN" or "Infinity"."""
    page = editor(rt("d", {**RT, "op": ":", "typed": [[0, 0, 1, 0]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Rechentabelle 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.table[data-table='0'].wrong")).to_have_count(1)
    text = at(page, "d").locator(".rechentabelle svg").text_content()
    assert "NaN" not in text and "Infinity" not in text, text


def test_neu_wuerfeln_changes_only_the_seed(editor):
    """Neu würfeln: stores another seed and keeps the other props; undo brings the old seed back."""
    client = user()
    page = editor(rt("d", {**RT, "typed": [[0, 1, 1, 5]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != RT["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == RT["seed"]


def test_one_more_row_grows_the_block_and_keeps_the_cell_size_in_one_undo(editor):
    """A change that needs more room: one more row grows the block and keeps the cell size; one Ctrl+Z gives back the row and the height."""
    client = user()
    page = editor(rt("d", RT), client=client)
    pick(page, "d")
    h0 = block_of(doc(page, client))["h"]
    before = at(page, "d").locator("g.cell rect").first.bounding_box()["width"]
    step(page, lambda: panel(page, "Eine Zeile mehr").click())
    grown = block_of(doc(page, client))
    assert grown["props"]["rows"] == 5
    assert grown["h"] > h0
    after = at(page, "d").locator("g.cell rect").first.bounding_box()["width"]
    assert abs(after - before) <= before * 0.02, (before, after)
    undo(page)
    back = block_of(doc(page, client))
    assert back["props"]["rows"] == 4
    assert abs(back["h"] - h0) < 0.2, back["h"]


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """Old sheets: odd stored props still draw, the panel opens and no fault shows."""
    client = user()
    odd = {
        **RT,
        "count": -3,
        "rows": 99,
        "cols": "x",
        "op": "x",
        "tint": "constructor",
        "reihen": "abc",
        "max": None,
        "typed": [[9, 9, 9, 9], "junk"],
    }
    page = editor(rt("odd", odd, z=1), rt("empty", {}, z=2, y=150), client=client)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".rechentabelle")).to_be_visible()
    expect(at(page, "empty").locator(".rechentabelle")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Rechentabelle", exact=True)
    ).to_be_visible()
    assert not errors, errors


def test_a_reload_keeps_the_tables_the_rows_and_the_rechenart(editor):
    """Panel: 3 Tabellen, 5 Zeilen and Rechenart Geteilt survive a save and reload, and the block still draws them."""
    client = user()
    page = editor(rt("d", {**RT, "count": 3, "rows": 5, "op": ":"}), client=client)
    pick(page, "d")
    doc(page, client)
    reload(page, page.url)
    pick(page, "d")
    expect(field(page, "Rechenart")).to_have_value(":")
    expect(page.locator(".panel").get_by_text("3 Tabellen", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("5 Zeilen", exact=True)).to_be_visible()
    props = props_of(doc(page, client))
    assert (props["count"], props["rows"], props["op"]) == (3, 5, ":")
    expect(at(page, "d").locator("g.table")).to_have_count(3)


def test_a_small_zahlenraum_says_values_repeat(editor):
    """Zahlenraum: with Plus, 10 rows and 10 columns in "bis 10" the values must repeat: the hint says so."""
    page = editor(rt("d", {**RT, "max": 10, "rows": 10, "cols": 10}))
    pick(page, "d")
    expect(
        page.locator(".panel").get_by_text(
            "Der Zahlenraum ist zu klein: manche Werte kommen zweimal vor.", exact=True
        )
    ).to_be_visible()
