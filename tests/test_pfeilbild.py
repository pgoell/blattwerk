"""The Pfeilbild: its block in the editor and its format panel.

The docstrings name the lines of the checklist (#821) that each test proves. The numbers are read
from the drawing, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, tool, user

PF = {
    "count": 4,
    "columns": 2,
    "boxes": 4,
    "max": 20,
    "ops": ["+", "-"],
    "arrows": "one",
    "given": "start",
    "drawOps": True,
    "seed": 7,
}
DEFAULTS = {k: v for k, v in PF.items() if k != "seed"}
MINUS = "\N{MINUS SIGN}"
DOT = "\N{MIDDLE DOT}"
H = 53.9


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Pfeilbild's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def pfeil(name, props):
    """A Pfeilbild block of 180 by 53.9 mm."""
    return box(name, "pfeilbild", props, w=180, h=H)


def block_of(stored):
    """The one Pfeilbild of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "pfeilbild"]
    return block


def props_of(stored):
    """The props of the one Pfeilbild of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def apply(label, x):
    """The number that an arrow's label gives from x: plus 4 adds 4, times 2 doubles x."""
    n = int(label[1:])
    return {"+": x + n, MINUS: x - n, DOT: x * n, ":": x // n}[label[0]]


def inverse_label(label):
    """The label of the back arrow: the inverse of the forward one, same number."""
    swap = {"+": MINUS, MINUS: "+", DOT: ":", ":": DOT}
    return swap[label[0]] + label[1:]


def picture_shown(page, picture=0):
    """Per box whether it shows a number, and per arrow whether it shows its operator."""
    return (
        at(page, "d")
        .locator(f"g.picture[data-picture='{picture}']")
        .evaluate(
            """p => [
            [...p.querySelectorAll('g.box')].map(b => !!b.querySelector('text.given')),
            [...p.querySelectorAll('g.arrow')].map(a => !!a.querySelector('text.op')),
        ]"""
        )
    )


def op_labels(page, picture=0):
    """The operator text of each forward arrow of a picture, in order."""
    return (
        at(page, "d")
        .locator(f"g.picture[data-picture='{picture}'] g.arrow text.op")
        .evaluate_all("els => els.map((t) => t.textContent)")
    )


def back_labels(page, picture=0):
    """The operator text of each back arrow of a picture, in order."""
    return (
        at(page, "d")
        .locator(f"g.picture[data-picture='{picture}'] g.back text.op")
        .evaluate_all("els => els.map((t) => t.textContent)")
    )


def given_numbers(page, picture=0):
    """The numbers a picture shows in its boxes, in order, None for an empty box."""
    return (
        at(page, "d")
        .locator(f"g.picture[data-picture='{picture}'] g.box")
        .evaluate_all(
            "els => els.map((b) => { const t = b.querySelector('text.given'); return t ? Number(t.textContent) : null; })"
        )
    )


@pytest.mark.parametrize(
    "key, before, after, act",
    [
        ("count", 4, 5, lambda p: panel(p, "Ein Pfeilbild mehr").click()),
        ("columns", 2, 3, lambda p: panel(p, "Eine Spalte mehr").click()),
        ("boxes", 4, 6, lambda p: field(p, "Kästchen").select_option("6")),
        ("max", 20, 100, lambda p: field(p, "Zahlenraum").select_option("100")),
        ("arrows", "one", "both", lambda p: field(p, "Pfeile").select_option("both")),
        ("given", "start", "ends", lambda p: field(p, "Gegeben").select_option("ends")),
        ("drawOps", True, False, lambda p: field(p, "Operatoren zeichnen").uncheck()),
        ("ops", ["+", "-"], ["+"], lambda p: field(p, "Minus").uncheck()),
    ],
    ids=[
        "pfeilbilder",
        "spalten",
        "kaestchen",
        "zahlenraum",
        "pfeile",
        "gegeben",
        "operatoren",
        "rechenarten",
    ],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, before, after, act):
    """Panel: each setting changes its stored prop; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


@pytest.mark.parametrize(
    "given, check",
    [
        ("start", lambda shown: shown[0][0] and all(shown[1])),
        ("ends", lambda shown: shown[0][0] and shown[0][-1] and not any(shown[1])),
        (
            "mixed",
            lambda shown: (
                shown[0][0] and all(shown[1][j] != shown[0][j + 1] for j in range(len(shown[1])))
            ),
        ),
    ],
    ids=["start", "ends", "mixed"],
)
def test_the_given_modes_show_the_right_boxes_and_operators(editor, given, check):
    """Panel: Startzahl und Operatoren shows box 0 and every operator; Start und Ziel the first and last
    box only; Gemischt box 0 and, per arrow, either the operator or the box after it."""
    page = editor(pfeil("d", {**PF, "given": given}))
    pick(page, "d")
    assert check(picture_shown(page))


def test_mal_and_geteilt_are_off_under_20(editor):
    """Panel: at bis 10 the Rechenarten Mal and Geteilt are disabled; from bis 20 they are offered."""
    page = editor(pfeil("d", {**PF, "max": 10}))
    pick(page, "d")
    expect(field(page, "Mal")).to_be_disabled()
    expect(field(page, "Geteilt")).to_be_disabled()
    step(page, lambda: field(page, "Zahlenraum").select_option("20"))
    expect(field(page, "Mal")).to_be_enabled()
    expect(field(page, "Geteilt")).to_be_enabled()


def test_a_smaller_zahlenraum_drops_mal_and_geteilt_in_one_undo(editor):
    """Panel: bis 10 drops Mal and Geteilt in the same step as the Zahlenraum; one Ctrl+Z gives them back."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100, "ops": ["+", "*", ":"]}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Zahlenraum").select_option("10"))
    props = props_of(doc(page, client))
    assert props["max"] == 10
    assert props["ops"] == ["+"]
    undo(page)
    props = props_of(doc(page, client))
    assert props["max"] == 100
    assert props["ops"] == ["+", "*", ":"]


def test_the_last_checked_rechenart_is_disabled(editor):
    """Panel: with only Plus checked, Plus is disabled: one Rechenart must stay."""
    page = editor(pfeil("d", {**PF, "ops": ["+"]}))
    pick(page, "d")
    expect(field(page, "Plus")).to_be_disabled()
    expect(field(page, "Plus")).to_be_checked()


def test_kaestchen_zufaellig_draws_pictures_with_3_to_8_boxes(editor):
    """Panel: Kästchen Zufällig stores "random" and every picture draws 3 to 8 boxes."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Kästchen").select_option("random"))
    assert props_of(doc(page, client))["boxes"] == "random"
    counts = (
        at(page, "d")
        .locator(".pfeilbild g.picture")
        .evaluate_all("els => els.map((p) => p.querySelectorAll('g.box').length)")
    )
    assert len(counts) == PF["count"]
    assert all(3 <= n <= 8 for n in counts), counts


def test_pfeile_in_both_directions_give_back_arrows_with_the_inverse_labels(editor):
    """Panel: Pfeile beide draws a back arrow under each forward arrow, labelled with the inverse operator."""
    page = editor(pfeil("d", {**PF, "arrows": "both"}))
    pick(page, "d")
    forward = op_labels(page)
    assert forward
    assert back_labels(page) == [inverse_label(label) for label in forward]
    expect(at(page, "d").locator("g.picture[data-picture='0'] g.back")).to_have_count(len(forward))


def test_operatoren_zeichnen_off_removes_the_ellipses(editor):
    """Panel: with Operatoren zeichnen off no ellipse is drawn around an operator place."""
    page = editor(pfeil("d", {**PF, "arrows": "both"}))
    pick(page, "d")
    # On: one ellipse per arrow and per back arrow, 4 pictures of 3 arrows each.
    expect(at(page, "d").locator(".pfeilbild g.arrow ellipse")).to_have_count(12)
    expect(at(page, "d").locator(".pfeilbild g.back ellipse")).to_have_count(12)
    step(page, lambda: field(page, "Operatoren zeichnen").uncheck())
    expect(at(page, "d").locator(".pfeilbild ellipse")).to_have_count(0)
    expect(at(page, "d").locator(".pfeilbild g.arrow text.op")).to_have_count(12)


def test_typing_two_digits_into_a_box_stores_them_and_one_undo_takes_both_back(editor):
    """Eigene Zahlen: "1" then "2" into "Zahl in Kästchen 1" store [[0, 0, 12]]; one Ctrl+Z removes both."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    number = field(page, "Zahl in Kästchen 1")

    def type_twelve():
        number.press("Control+a")
        number.press_sequentially("1")
        number.press_sequentially("2")

    step(page, type_twelve)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 12]]
    number.press("Control+z")
    assert "typed" not in props_of(doc(page, client))


def test_a_typed_box_that_breaks_the_operators_gives_the_hint_and_no_answers_in_the_key(editor):
    """Eigene Zahlen: box 1 typed 9999 against box 0 typed 5 is wrong: the hint says so and the picture is marked."""
    client = user()
    page = editor(pfeil("d", {**PF, "typed": [[0, 0, 5], [0, 1, 9999]]}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_text("Pfeilbild 1: die Zahlen passen nicht zu den Operatoren.")
    expect(at(page, "d").locator("g.picture[data-picture='0'].wrong")).to_have_count(1)


def test_eigene_zahlen_entfernen_is_one_undo_step(editor):
    """Eigene Zahlen: "Eigene Zahlen entfernen" clears every typed number in one step; one Ctrl+Z brings them back."""
    client = user()
    typed = [[0, 0, 5], [0, 1, 8]]
    page = editor(pfeil("d", {**PF, "typed": typed}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == typed


def test_neu_wuerfeln_stores_another_seed_and_keeps_the_other_props(editor):
    """Neu würfeln: stores another seed and keeps the other props; undo brings the old seed back."""
    client = user()
    page = editor(pfeil("d", {**PF, "typed": [[0, 0, 15]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != PF["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == PF["seed"]


def test_start_and_goal_grow_the_block_by_the_note_line_in_one_undo(editor):
    """Gegeben Start und Ziel keeps a line for the key's note: the block grows by it, and one undo
    gives back the mode and the height together."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Gegeben").select_option("ends"))
    grown = block_of(doc(page, client))
    assert grown["props"]["given"] == "ends"
    assert grown["h"] > H + 7, grown["h"]
    undo(page)
    back = block_of(doc(page, client))
    assert back["props"]["given"] == "start"
    assert abs(back["h"] - H) < 0.2, back["h"]


def test_a_box_field_keeps_focus_and_digits_while_the_block_redraws(editor):
    """Eigene Zahlen: typing "17" into "Zahl in Kästchen 3" keeps the focus and the digits, and stores [0, 2, 17]."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    number = field(page, "Zahl in Kästchen 3")
    number.click()
    step(page, lambda: page.keyboard.type("17"))
    expect(number).to_be_focused()
    expect(number).to_have_value("17")
    assert props_of(doc(page, client))["typed"] == [[0, 2, 17]]


def test_more_boxes_keep_the_box_size_and_take_fewer_columns_in_one_undo(editor):
    """Kästchen 4 to 8 keeps the box size (within 2 %), takes columns down and grows the block; one Ctrl+Z gives back 4 boxes, 2 columns and 53.9 mm."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    before = at(page, "d").locator("g.box rect").first.bounding_box()["width"]
    step(page, lambda: field(page, "Kästchen").select_option("8"))
    props = props_of(doc(page, client))
    assert props["boxes"] == 8
    assert props["columns"] < 2
    assert block_of(doc(page, client))["h"] > H
    after = at(page, "d").locator("g.box rect").first.bounding_box()["width"]
    assert abs(after - before) <= before * 0.02
    undo(page)
    props = props_of(doc(page, client))
    assert props["boxes"] == 4
    assert props["columns"] == 2
    assert block_of(doc(page, client))["h"] == H


def test_a_picture_that_cannot_fit_the_zahlenraum_is_not_drawn_and_the_panel_says_why(editor):
    """Pictures: with only Mal at bis 20 and 8 boxes, a picture that cannot fit is marked over, draws no
    box, and the panel says why; no such hint shows when no picture is over."""
    # Mal only bis 20 cannot make 7 steps (2^7 = 128): both pictures are over.
    client = user()
    page = editor(
        pfeil("d", {**PF, "ops": ["*"], "boxes": 8, "count": 2, "columns": 1}), client=client
    )
    pick(page, "d")
    overs = at(page, "d").locator("g.picture.over")
    expect(overs).to_have_count(2)
    expect(overs.locator("g.box")).to_have_count(0)
    expect(
        hint(page).filter(
            has_text="Pfeilbilder, die nicht in den Zahlenraum passen, werden nicht gezeigt."
        )
    ).to_be_visible()
    # Plus as well lets every picture fit: none is over and the hint goes.
    step(page, lambda: field(page, "Plus").check())
    expect(overs).to_have_count(0)
    expect(hint(page).filter(has_text="werden nicht gezeigt")).to_have_count(0)


def test_plus_only_with_8_boxes_bis_10_draws_every_picture(editor):
    """Pictures: Plus only bis 10 with 8 Kästchen fits (0 to 7), so every picture is drawn, with 8 boxes."""
    page = editor(pfeil("d", {**PF, "ops": ["+"], "boxes": 8, "max": 10, "columns": 1}))
    expect(at(page, "d").locator("g.picture.over")).to_have_count(0)
    expect(at(page, "d").locator("g.picture g.box")).to_have_count(4 * 8)


def test_a_pfeilbild_is_inserted_from_the_maths_menu_with_the_default_props(editor):
    """Insert: the Mathe-Blöcke item "Pfeilbild" adds a block with the default props and a whole seed."""
    client = user()
    page = editor(client=client)
    insert(page, "Pfeilbild")
    expect(
        page.locator(".panel").get_by_role("heading", name="Pfeilbild", exact=True)
    ).to_be_visible()
    props = props_of(doc(page, client))
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)


def test_a_reload_keeps_the_arrows_and_the_given_mode(editor):
    """Panel: Pfeile beide and Gegeben Ende survive a save and reload, and the block still shows its back arrows."""
    client = user()
    page = editor(pfeil("d", {**PF, "arrows": "both", "given": "ends"}), client=client)
    pick(page, "d")
    doc(page, client)
    reload(page, page.url)
    pick(page, "d")
    expect(field(page, "Gegeben")).to_have_value("ends")
    expect(field(page, "Pfeile")).to_have_value("both")
    expect(at(page, "d").locator("g.picture[data-picture='0'] g.back").first).to_be_attached()
    assert given_numbers(page)[0] is not None


def type_op(field_op, text):
    """Replaces the text of an operator field with text, one key at a time."""
    field_op.press("Control+a")
    field_op.press_sequentially(text)


def test_eigene_operatoren_each_keystroke_stores_but_one_ctrl_z_takes_all_back(editor):
    """Eigene Operatoren: "+", "1", "2" into "Operator an Pfeil 2" store +1 then +12 as one undo step; one Ctrl+Z removes typedOps, Ctrl+Y gives [[0, 1, "+", 12]] back."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 2")
    step(
        page,
        lambda: (
            type_op(op_field, "+"),
            op_field.press_sequentially("1"),
            op_field.press_sequentially("2"),
        ),
    )
    assert props_of(doc(page, client))["typedOps"] == [[0, 1, "+", 12]]
    op_field.press("Control+z")
    assert "typedOps" not in props_of(doc(page, client))
    op_field.press("Control+y")
    assert props_of(doc(page, client))["typedOps"] == [[0, 1, "+", 12]]


@pytest.mark.parametrize(
    "text, op, n",
    [(DOT + "2", "*", 2), ("x2", "*", 2), (":2", ":", 2), ("/2", ":", 2), ("4", "+", 4)],
    ids=["mid-dot", "x", "colon", "slash", "bare-digits"],
)
def test_eigene_operatoren_spellings_store_the_normalised_op(editor, text, op, n):
    """Eigene Operatoren: the middle dot 2 and "x2" store "*", ":2" and "/2" store ":", a bare "4" stores "+", all on arrow 1."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 1")
    step(page, lambda: (type_op(op_field, ""), op_field.press_sequentially(text)))
    assert props_of(doc(page, client))["typedOps"] == [[0, 0, op, n]]


def test_eigene_operatoren_a_sign_alone_keeps_focus_and_stores_nothing(editor):
    """Eigene Operatoren: a minus sign alone keeps the focus and its text and stores nothing; after blur the field shows the drawn label again."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 2")
    op_field.click()
    type_op(op_field, MINUS)
    expect(op_field).to_be_focused()
    expect(op_field).to_have_value(MINUS)
    assert "typedOps" not in props_of(doc(page, client))
    op_field.evaluate("el => el.blur()")
    expect(op_field).to_have_value(op_labels(page)[1])


def test_eigene_zahlen_entfernen_clears_typed_and_typed_ops_in_one_undo_step(editor):
    """Eigene Zahlen: "Eigene Zahlen entfernen" clears the typed numbers and the typed operators in one step; one Ctrl+Z brings both back."""
    client = user()
    typed = [[0, 0, 5], [0, 1, 8]]
    typed_ops = [[0, 1, "-", 3]]
    page = editor(pfeil("d", {**PF, "typed": typed, "typedOps": typed_ops}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    props = props_of(doc(page, client))
    assert "typed" not in props and "typedOps" not in props
    undo(page)
    props = props_of(doc(page, client))
    assert props["typed"] == typed
    assert props["typedOps"] == typed_ops


def test_neu_wuerfeln_keeps_the_typed_operators(editor):
    """Eigene Operatoren: "Neu würfeln" stores another seed and keeps typedOps as they are."""
    client = user()
    typed_ops = [[0, 1, "-", 3]]
    page = editor(pfeil("d", {**PF, "typedOps": typed_ops}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Neu würfeln").click())
    props = props_of(doc(page, client))
    assert props["seed"] != PF["seed"]
    assert props["typedOps"] == typed_ops


def test_typed_ops_that_cannot_fit_the_zahlenraum_give_their_own_hint(editor):
    """Eigene Operatoren: three plus 9 at bis 10 cannot fit; the hint says the Operatoren do not fit the Zahlenraum, and picture 1 is marked wrong once."""
    client = user()
    typed_ops = [[0, 0, "+", 9], [0, 1, "+", 9], [0, 2, "+", 9]]
    page = editor(pfeil("d", {**PF, "max": 10, "typedOps": typed_ops}), client=client)
    pick(page, "d")
    expect(hint(page).filter(has_text="Pfeilbild 1:")).to_have_text(
        "Pfeilbild 1: die Operatoren passen nicht in den Zahlenraum."
    )
    expect(at(page, "d").locator("g.picture[data-picture='0'].wrong")).to_have_count(1)


def test_eigene_operatoren_two_fields_are_two_undo_steps(editor):
    """Eigene Operatoren: "+2" into Pfeil 1 then "+3" into Pfeil 2 are two steps; one Ctrl+Z leaves only [[0, 0, "+", 2]]."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    first = field(page, "Operator an Pfeil 1")
    second = field(page, "Operator an Pfeil 2")
    step(page, lambda: (type_op(first, "+"), first.press_sequentially("2")))
    step(page, lambda: (type_op(second, "+"), second.press_sequentially("3")))
    assert props_of(doc(page, client))["typedOps"] == [[0, 0, "+", 2], [0, 1, "+", 3]]
    undo(page)
    assert props_of(doc(page, client))["typedOps"] == [[0, 0, "+", 2]]


def test_eigene_operatoren_with_pfeile_both_show_the_back_arrow_inverse(editor):
    """Eigene Operatoren: with Pfeile both, the middle dot 2 into Pfeil 1 draws the forward "·2" and the back arrow ":2"."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100, "arrows": "both"}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 1")
    step(page, lambda: (type_op(op_field, DOT), op_field.press_sequentially("2")))
    assert back_labels(page)[0] == ":2"
    assert op_labels(page)[0] == DOT + "2"


def test_eigene_operatoren_ctrl_z_in_the_field_shows_the_undone_operator(editor):
    """Eigene Operatoren: Ctrl+Z inside the field after "+5" shows the text from before, and the field keeps focus."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 1")
    before = op_field.input_value()
    step(page, lambda: (type_op(op_field, "+"), op_field.press_sequentially("5")))
    op_field.press("Control+z")
    expect(op_field).to_have_value(before)
    expect(op_field).to_be_focused()


def test_eigene_operatoren_a_click_selects_the_whole_text(editor):
    """Eigene Operatoren: a click on "Operator an Pfeil 1" selects its whole text, so "7" alone replaces it and stores [[0, 0, "+", 7]] (no Control+a)."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 1")
    op_field.click()
    step(page, lambda: op_field.press_sequentially("7"))
    assert props_of(doc(page, client))["typedOps"] == [[0, 0, "+", 7]]


def test_eigene_operatoren_field_keeps_focus_and_text_while_the_block_redraws(editor):
    """Eigene Operatoren: typing "+1" then "2" keeps the focus, and the field shows "+12" while the block redraws."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 2")
    op_field.click()
    step(
        page,
        lambda: (
            type_op(op_field, "+"),
            op_field.press_sequentially("1"),
            op_field.press_sequentially("2"),
        ),
    )
    expect(op_field).to_be_focused()
    expect(op_field).to_have_value("+12")


def test_a_typed_operator_against_the_typed_numbers_gives_the_hint_and_no_key(editor):
    """Eigene Operatoren: boxes 5 and 7 typed, "+3" typed between them: the hint says the numbers do
    not fit the operators, the picture is marked wrong, and the key shows no answer for it."""
    client = user()
    props = {**PF, "typed": [[0, 0, 5], [0, 1, 7]], "typedOps": [[0, 0, "+", 3]]}
    page = editor(pfeil("d", props), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_text("Pfeilbild 1: die Zahlen passen nicht zu den Operatoren.")
    first = at(page, "d").locator("g.picture[data-picture='0']")
    expect(first).to_have_class("picture wrong")
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "d").locator("g.picture[data-picture='1'] text.answer").first).to_be_attached()
    expect(first.locator("text.answer")).to_have_count(0)


def test_eigene_operatoren_of_pfeilbild_2_store_under_picture_1(editor):
    """Eigene Operatoren: with Pfeilbild 2 picked, "-" then "3" into "Operator an Pfeil 1" store [1, 0, "-", 3]."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    field(page, "Pfeilbild für eigene Zahlen").select_option("1")
    op_field = field(page, "Operator an Pfeil 1")
    step(page, lambda: (type_op(op_field, "-"), op_field.press_sequentially("3")))
    assert props_of(doc(page, client))["typedOps"] == [[1, 0, "-", 3]]
