"""The Magisches Quadrat on screen: its block in the editor and its format panel.

The docstrings name the lines of the contract (#825, top of frontend/src/magischesquadrat.ts) and of the panel
that each test proves. The numbers are read from the page, never pinned: the generator may change.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

MQ = {
    "count": 2,
    "columns": 2,
    "size": 3,
    "max": 20,
    "given": 4,
    "showSum": False,
    "seed": 7,
}
DEFAULTS = {k: v for k, v in MQ.items() if k != "seed"}
FIVE = "5 \N{MULTIPLICATION SIGN} 5"
H = 96.52  # a stored height for the default block at 180 mm wide; the drawing does not depend on it
TYPED_WRONG = [[0, 1, 1, 1], [0, 1, 2, 2], [0, 1, 3, 3], [0, 2, 1, 5], [0, 3, 1, 9]]


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Magisches Quadrat's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def mq(name, props, **more):
    """A Magisches Quadrat block of 180 mm wide."""
    return box(name, "magischesquadrat", props, w=180, h=H, **more)


def block_of(stored):
    """The one Magisches Quadrat of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "magischesquadrat"]
    return block


def props_of(stored):
    """The props of the one Magisches Quadrat of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def test_a_magic_square_is_inserted_from_the_maths_menu_with_the_default_props(editor):
    """Insert (#825, the maths menu): "Magisches Quadrat" adds a 180 mm wide block with the default props and a whole
    seed, drawn as 2 squares of 9 cells each."""
    client = user()
    page = editor(client=client)
    insert(page, "Magisches Quadrat")
    expect(
        page.locator(".panel").get_by_role("heading", name="Magisches Quadrat", exact=True)
    ).to_be_visible()
    stored = block_of(doc(page, client))
    assert stored["w"] == 180
    props = stored["props"]
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    drawn = page.locator(".magischesquadrat").first
    expect(drawn.locator("g.square")).to_have_count(2)
    expect(drawn.locator("g.square g.cell")).to_have_count(18)
    expect(drawn.locator("g.square[data-square='0'] g.cell")).to_have_count(9)
    expect(drawn.locator("g.square[data-square='1'] g.cell")).to_have_count(9)


@pytest.mark.parametrize(
    "extra, key, before, after, act",
    [
        ({}, "size", 3, 5, lambda p: field(p, "Größe").select_option(label=FIVE)),
        (
            {},
            "max",
            20,
            100,
            lambda p: field(p, "Zahlenraum").select_option(label="bis 100"),
        ),
        ({}, "showSum", False, True, lambda p: field(p, "Zielzahl anzeigen").check()),
        (
            {},
            "given",
            4,
            5,
            lambda p: panel(p, "Eine vorgegebene Zahl mehr").click(),
        ),
    ],
    ids=["groesse", "zahlenraum", "zielzahl", "vorgegeben"],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(
    editor, extra, key, before, after, act
):
    """Panel (#825): each setting changes its stored prop; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    page = editor(mq("d", {**MQ, **extra}), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_the_steppers_show_their_counts_and_stop_at_their_limits(editor):
    """Panel (#825): the steppers say "2 Quadrate", "2 nebeneinander" and "4 Zahlen vorgegeben", and stop at 1 and 4
    squares, 1 and 3 squares side by side, and 2 and 8 given numbers in a 3 x 3."""
    page = editor(mq("d", MQ))
    pick(page, "d")
    expect(page.locator(".panel").get_by_text("2 Quadrate", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("2 nebeneinander", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("4 Zahlen vorgegeben", exact=True)).to_be_visible()
    expect(panel(page, "Ein Quadrat weniger")).to_be_enabled()
    top = editor(mq("d", {**MQ, "count": 4, "columns": 3, "given": 8}))
    pick(top, "d")
    expect(panel(top, "Ein Quadrat mehr")).to_be_disabled()
    expect(panel(top, "Mehr Quadrate nebeneinander")).to_be_disabled()
    expect(panel(top, "Eine vorgegebene Zahl mehr")).to_be_disabled()
    low = editor(mq("d", {**MQ, "count": 1, "columns": 1, "given": 2}))
    pick(low, "d")
    expect(panel(low, "Ein Quadrat weniger")).to_be_disabled()
    expect(panel(low, "Weniger Quadrate nebeneinander")).to_be_disabled()
    expect(panel(low, "Eine vorgegebene Zahl weniger")).to_be_disabled()


def test_size_5_draws_25_cells_sets_given_to_15_and_drops_typed_in_one_undo_step(editor):
    """Panel (#825): "Größe" 5 x 5 draws 25 cells per square, sets given to 15 and drops typed numbers, in one undo
    step."""
    client = user()
    typed = [[0, 1, 1, 3]]
    page = editor(mq("d", {**MQ, "typed": typed}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Größe").select_option(label=FIVE))
    stored = props_of(doc(page, client))
    assert (stored["size"], stored["given"]) == (5, 15)
    assert "typed" not in stored
    expect(at(page, "d").locator("g.square[data-square='0'] g.cell")).to_have_count(25)
    expect(at(page, "d").locator("g.square[data-square='1'] g.cell")).to_have_count(25)
    undo(page)
    stored = props_of(doc(page, client))
    assert (stored["size"], stored["given"]) == (3, 4)
    assert stored["typed"] == typed


def test_zahlenraum_bis_20_is_disabled_at_5_by_5_and_a_stored_5_by_5_with_max_20_shows_bis_100(
    editor,
):
    """Panel (#825): with 5 x 5 the "bis 20" option is disabled; a stored 5 x 5 with max 20 shows "bis 100", the
    Zahlenraum that holds 25 numbers."""
    page = editor(mq("d", {**MQ, "size": 5, "given": 15, "max": 20}))
    pick(page, "d")
    expect(field(page, "Zahlenraum").locator("option", has_text="bis 20")).to_have_attribute(
        "disabled", ""
    )
    expect(field(page, "Zahlenraum").locator("option:checked")).to_have_text("bis 100")


def test_eigener_shows_the_field_and_typing_50_stores_max_50(editor):
    """Panel (#825): "Eigener" shows the field "Eigener Zahlenraum"; typing 50 stores max 50."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    field(page, "Zahlenraum").select_option(label="Eigener")
    number = field(page, "Eigener Zahlenraum")
    expect(number).to_be_visible()
    number.fill("45")
    number.press("Enter")
    number.fill("50")
    number.press("Enter")
    expect(number).to_have_value("50")
    assert props_of(doc(page, client))["max"] == 50


def test_typing_500_and_1000_with_real_keys_keeps_the_eigener_field_and_its_digits(editor):
    """Panel (#825): typed with the keyboard, the field "Eigener Zahlenraum" keeps the focus and its digits while the
    number grows; 500 stores max 500, and 1000 then ends with max 1000."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    field(page, "Zahlenraum").select_option(label="Eigener")
    number = field(page, "Eigener Zahlenraum")
    number.click()
    page.keyboard.press("Control+A")
    page.keyboard.type("500")
    expect(number).to_be_focused()
    expect(number).to_have_value("500")
    assert props_of(doc(page, client))["max"] == 500
    number.click()
    page.keyboard.press("Control+A")
    page.keyboard.type("1000")
    expect(number).to_be_focused()
    expect(number).to_have_value("1000")
    assert props_of(doc(page, client))["max"] == 1000


@pytest.mark.parametrize("given", [3, 4, 6])
def test_the_pupils_sheet_shows_exactly_given_numbers_per_square(editor, browser, server, given):
    """Print (#825): the pupils' sheet shows exactly `given` numbers in each square, for given 3, 4 and 6."""
    client = user()
    page = editor(mq("k", {**MQ, "given": given}), client=client)
    paper = printed(browser, server, sheet_id(page))
    for square in (0, 1):
        expect(paper.locator(f"g.square[data-square='{square}'] g.cell text.given")).to_have_count(
            given
        )
    paper.context.close()


def test_zielzahl_anzeigen_draws_the_sum_above_each_square(editor):
    """Zielzahl (#825): with "Zielzahl anzeigen" each square has text.sum "Zielzahl: S" above it."""
    page = editor(mq("k", {**MQ, "showSum": True}))
    expect(at(page, "k").locator("g.square[data-square='0'] text.sum")).to_have_text(
        re.compile(r"^Zielzahl: \d+$")
    )
    expect(at(page, "k").locator("g.square[data-square='1'] text.sum")).to_have_text(
        re.compile(r"^Zielzahl: \d+$")
    )


def test_typing_a_number_is_one_undo_step_and_the_box_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#825): typing "17" into "Zeile 1, Spalte 3" keeps the focus and the digits while the block redraws,
    stores a typed entry, and one Ctrl+Z in the box takes it back."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    number = field(page, "Zeile 1, Spalte 3")
    number.click()
    step(page, lambda: page.keyboard.type("17"))
    expect(number).to_be_focused()
    expect(number).to_have_value("17")
    assert [0, 1, 3, 17] in props_of(doc(page, client))["typed"]
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_the_first_typed_number_keeps_the_drawn_given_numbers_as_typed_entries(editor):
    """Eigene Zahlen (#825): the first number typed into an empty box stores the square's drawn given cells as typed
    entries too, so the typed entries are given + 1."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    boxes = page.locator(".panel").get_by_label(re.compile(r"^Zeile \d+, Spalte \d+$"))
    empty = next(b for b in boxes.all() if b.input_value() == "")
    empty.click()
    step(page, lambda: page.keyboard.type("1"))
    assert len(props_of(doc(page, client))["typed"]) == MQ["given"] + 1


def test_typed_numbers_that_fit_no_square_give_the_hint_and_mark_the_square_wrong(editor):
    """Eigene Zahlen (#825): a row 1, 2, 3 and a column 1, 5, 9 (cell 1, 1 shared) fit no magic square: the hint names
    Magisches Quadrat 1 and that square gets class wrong."""
    page = editor(mq("d", {**MQ, "typed": TYPED_WRONG}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Magisches Quadrat 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.square.wrong")).to_have_count(1)
    expect(at(page, "d").locator("g.square[data-square='0'].wrong")).to_have_count(1)


def test_eigene_zahlen_entfernen_is_one_undo_step_and_removes_the_hint(editor):
    """Eigene Zahlen (#825): "Eigene Zahlen entfernen" clears every typed number and the hint in one step; one Ctrl+Z
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
    """Panel (#825): "Neu würfeln" stores another seed and keeps the other props; undo brings the old seed back."""
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
    """Layout (#825): one more square grows the block and keeps the cell size; one Ctrl+Z gives back the square and the
    height."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    h0 = block_of(doc(page, client))["h"]
    before = at(page, "d").locator("g.cell rect").first.bounding_box()["width"]
    step(page, lambda: panel(page, "Ein Quadrat mehr").click())
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
    """Old sheets (#825): odd stored props still draw, the panel opens and no fault shows."""
    client = user()
    odd = {
        **MQ,
        "count": -3,
        "columns": 99,
        "size": 4,
        "max": None,
        "given": "x",
        "showSum": "yes",
        "typed": [[9, 9, 9, 9], "junk"],
        "seed": "s",
    }
    page = editor(mq("odd", odd, z=1), mq("empty", {}, z=2, y=150), client=client)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".magischesquadrat")).to_be_visible()
    expect(at(page, "empty").locator(".magischesquadrat")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Magisches Quadrat", exact=True)
    ).to_be_visible()
    assert not errors, errors


def test_a_reload_keeps_the_squares_the_size_and_the_typed_numbers(editor):
    """Panel (#825): 3 squares, size 5 and typed numbers survive a save and reload, and the block still draws them."""
    client = user()
    typed = [[0, 1, 1, 4]]
    page = editor(
        mq("d", {**MQ, "count": 3, "size": 5, "given": 15, "typed": typed}), client=client
    )
    pick(page, "d")
    doc(page, client)
    reload(page, page.url)
    pick(page, "d")
    expect(field(page, "Größe").locator("option:checked")).to_have_text(FIVE)
    expect(page.locator(".panel").get_by_text("3 Quadrate", exact=True)).to_be_visible()
    props = props_of(doc(page, client))
    assert (props["count"], props["size"]) == (3, 5)
    assert props["typed"] == typed
    expect(at(page, "d").locator("g.square")).to_have_count(3)


def test_typed_entries_of_a_square_that_is_gone_stay_stored(editor):
    """Typed (#825): with 2 squares and typed numbers for square 1, "Ein Quadrat weniger" leaves the block with one
    square and the typed entry for the gone square is still stored."""
    client = user()
    typed = [[0, 1, 1, 5], [1, 1, 1, 7]]
    page = editor(mq("d", {**MQ, "typed": typed}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Ein Quadrat weniger").click())
    props = props_of(doc(page, client))
    assert props["count"] == 1
    assert [1, 1, 1, 7] in props["typed"]
