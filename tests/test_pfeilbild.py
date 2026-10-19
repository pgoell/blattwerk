"""The Pfeilbild: its block in the editor and its format panel.

The docstrings name the lines of the checklist (#821) that each test proves. The numbers are read
from the drawing, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

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
    """Panel: at bis 20 the Rechenarten Mal and Geteilt are disabled."""
    page = editor(pfeil("d", PF))
    pick(page, "d")
    expect(field(page, "Mal")).to_be_disabled()
    expect(field(page, "Geteilt")).to_be_disabled()


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
    page = editor(pfeil("d", {**PF, "drawOps": False}))
    pick(page, "d")
    expect(at(page, "d").locator(".pfeilbild g.arrow ellipse")).to_have_count(0)


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
    page = editor(pfeil("d", {**PF, "ops": ["*"], "boxes": 8, "count": 2, "columns": 1}))
    pick(page, "d")
    overs = at(page, "d").locator("g.picture.over")
    if overs.count():
        expect(
            hint(page).filter(
                has_text="Pfeilbilder, die nicht in den Zahlenraum passen, werden nicht gezeigt."
            )
        ).to_be_visible()
        expect(overs.locator("g.box")).to_have_count(0)
    else:
        expect(hint(page).filter(has_text="werden nicht gezeigt")).to_have_count(0)


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
