"""The Operatorfeld on screen: its block in the editor and its format panel.

The docstrings name the lines of the checklist (#822) that each test proves. The numbers are read
from the page, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

OF = {
    "centre": False,
    "count": 2,
    "columns": 2,
    "boxes": 4,
    "max": 20,
    "ops": ["+", "-"],
    "only": "none",
    "given": "start",
    "drawOps": True,
    "seed": 7,
}
DEFAULTS = {k: v for k, v in OF.items() if k != "seed"}
MINUS = "\N{MINUS SIGN}"
DOT = "\N{MIDDLE DOT}"
H = 85.99  # the default height: 75 * 180 / 157, rounded as insert.ts does


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Operatorfeld's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def of(name, props, **more):
    """An Operatorfeld block of 180 by 85.99 mm."""
    return box(name, "operatorfeld", props, w=180, h=H, **more)


def block_of(stored):
    """The one Operatorfeld of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "operatorfeld"]
    return block


def props_of(stored):
    """The props of the one Operatorfeld of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def apply(label, x):
    """The number that a link's label gives from x: plus 4 adds 4, times 2 doubles x."""
    n = int(label[1:])
    return {"+": x + n, MINUS: x - n, DOT: x * n, ":": x // n}[label[0]]


def shown(page, f=0):
    """Per box of field f whether it shows a number, and per link whether it shows its operator."""
    return (
        at(page, "d")
        .locator(f"g.field[data-field='{f}']")
        .evaluate(
            """p => [
            [...p.querySelectorAll('g.box')].map(b => !!b.querySelector('text.given')),
            [...p.querySelectorAll('g.link')].map(l => !!l.querySelector('text.op')),
        ]"""
        )
    )


def op_labels(page, f=0):
    """The operator text of each link of field f, in order."""
    return (
        at(page, "d")
        .locator(f"g.field[data-field='{f}'] g.link text.op")
        .evaluate_all("els => els.map((t) => t.textContent)")
    )


def given_numbers(page, f=0):
    """The numbers field f shows in its boxes, in order, None for an empty box."""
    return (
        at(page, "d")
        .locator(f"g.field[data-field='{f}'] g.box")
        .evaluate_all(
            "els => els.map((b) => { const t = b.querySelector('text.given'); return t ? Number(t.textContent) : null; })"
        )
    )


def test_an_operatorfeld_is_inserted_from_the_maths_menu_with_the_default_props(editor):
    """Insert: the Mathe-Blöcke item "Operatorfeld" adds a block with the default props and a whole seed."""
    client = user()
    page = editor(client=client)
    insert(page, "Operatorfeld")
    expect(
        page.locator(".panel").get_by_role("heading", name="Operatorfeld", exact=True)
    ).to_be_visible()
    props = props_of(doc(page, client))
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)


@pytest.mark.parametrize(
    "key, before, after, act",
    [
        ("count", 2, 3, lambda p: panel(p, "Ein Operatorfeld mehr").click()),
        ("columns", 2, 3, lambda p: panel(p, "Eine Spalte mehr").click()),
        ("boxes", 4, 5, lambda p: panel(p, "Ein Kästchen mehr").click()),
        ("max", 20, 100, lambda p: field(p, "Zahlenraum").select_option("100")),
        ("centre", False, True, lambda p: field(p, "Variante").select_option(label="Mit Zentrum")),
        ("given", "start", "ops", lambda p: field(p, "Gegeben").select_option("ops")),
        ("drawOps", True, False, lambda p: field(p, "Operatoren zeichnen").uncheck()),
        ("ops", ["+", "-"], ["+"], lambda p: field(p, "Minus").uncheck()),
    ],
    ids=[
        "operatorfelder",
        "spalten",
        "kaestchen",
        "zahlenraum",
        "variante",
        "gegeben",
        "operatoren",
        "rechenarten",
    ],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, before, after, act):
    """Panel: each setting changes its stored prop; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    page = editor(of("d", OF), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_the_einschraenkung_changes_its_prop_and_undoes_and_redoes(editor):
    """Panel: at bis 100 the Einschränkung "Nur Zehnerzahlen" stores only "tens"; one Ctrl+Z brings "none", one redo "tens"."""
    client = user()
    page = editor(of("d", {**OF, "max": 100}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Einschränkung").select_option("tens"))
    assert props_of(doc(page, client))["only"] == "tens"
    undo(page)
    assert props_of(doc(page, client))["only"] == "none"
    redo(page)
    assert props_of(doc(page, client))["only"] == "tens"


def test_the_steppers_show_their_counts_and_stop_at_their_limits(editor):
    """Panel: the steppers say "2 Operatorfelder" and "4 Kästchen", and stop at 1 and 6 fields, 1 and 3 columns, 3 and 8 boxes."""
    page = editor(of("d", OF))
    pick(page, "d")
    expect(page.locator(".panel").get_by_text("2 Operatorfelder", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("4 Kästchen", exact=True)).to_be_visible()
    expect(panel(page, "Ein Operatorfeld weniger")).to_be_enabled()
    expect(panel(page, "Ein Operatorfeld mehr")).to_be_enabled()
    page2 = editor(of("d", {**OF, "count": 6, "columns": 3, "boxes": 8}))
    pick(page2, "d")
    expect(panel(page2, "Ein Operatorfeld mehr")).to_be_disabled()
    expect(panel(page2, "Eine Spalte mehr")).to_be_disabled()
    expect(panel(page2, "Ein Kästchen mehr")).to_be_disabled()
    page3 = editor(of("d", {**OF, "count": 1, "columns": 1, "boxes": 3}))
    pick(page3, "d")
    expect(panel(page3, "Ein Operatorfeld weniger")).to_be_disabled()
    expect(panel(page3, "Eine Spalte weniger")).to_be_disabled()
    expect(panel(page3, "Ein Kästchen weniger")).to_be_disabled()


def test_mit_zentrum_draws_a_centre_box_linked_to_every_outer_box(editor):
    """Variante Mit Zentrum: each field has a centre box and one link per outer box, every link from the centre."""
    page = editor(of("d", {**OF, "centre": True, "count": 1, "columns": 1, "boxes": 4}))
    pick(page, "d")
    field_ = at(page, "d").locator("g.field[data-field='0']")
    expect(field_.locator("g.box")).to_have_count(5)
    expect(field_.locator("g.link")).to_have_count(4)
    centre = given_numbers(page)[0]
    assert centre is not None
    for label in op_labels(page):
        assert label[0] in ("+", MINUS), label


def test_ohne_zentrum_draws_a_closed_ring_of_boxes_and_links(editor):
    """Variante Ohne Zentrum: boxes stand in a ring and each box has a link to the next, the last back to the first."""
    page = editor(of("d", {**OF, "count": 1, "columns": 1, "boxes": 5}))
    pick(page, "d")
    field_ = at(page, "d").locator("g.field[data-field='0']")
    expect(field_.locator("g.box")).to_have_count(5)
    expect(field_.locator("g.link")).to_have_count(5)


def test_switching_the_variante_drops_mal_geteilt_and_typed_numbers_in_one_undo(editor):
    """Implied 3: switching to Mit Zentrum drops Mal and Geteilt and the typed numbers in one step; one Ctrl+Z gives them back."""
    client = user()
    typed = [[0, 0, 5]]
    page = editor(
        of("d", {**OF, "max": 100, "ops": ["+", "*", ":"], "typed": typed}), client=client
    )
    pick(page, "d")
    step(page, lambda: field(page, "Variante").select_option(label="Mit Zentrum"))
    props = props_of(doc(page, client))
    assert props["centre"] is True
    assert "*" not in props["ops"] and ":" not in props["ops"]
    assert "typed" not in props
    undo(page)
    props = props_of(doc(page, client))
    assert props["centre"] is False
    assert props["ops"] == ["+", "*", ":"]
    assert props["typed"] == typed


def test_a_smaller_zahlenraum_drops_mal_and_geteilt_in_one_undo(editor):
    """Implied 3: bis 10 drops Mal and Geteilt in the same step as the Zahlenraum; one Ctrl+Z gives them back."""
    client = user()
    page = editor(of("d", {**OF, "max": 100, "ops": ["+", "*", ":"]}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Zahlenraum").select_option("10"))
    props = props_of(doc(page, client))
    assert props["max"] == 10
    assert props["ops"] == ["+"]
    undo(page)
    props = props_of(doc(page, client))
    assert props["max"] == 100
    assert props["ops"] == ["+", "*", ":"]


def test_a_smaller_zahlenraum_drops_a_too_small_einschraenkung_in_the_same_undo(editor):
    """Implied 3: bis 100 drops Nur Hunderterzahlen (it needs bis 1000) in the same step as the Zahlenraum."""
    client = user()
    page = editor(of("d", {**OF, "max": 1000, "only": "hundreds"}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Zahlenraum").select_option("100"))
    props = props_of(doc(page, client))
    assert props["max"] == 100
    assert props["only"] == "none"
    undo(page)
    props = props_of(doc(page, client))
    assert props["max"] == 1000
    assert props["only"] == "hundreds"


def test_mal_and_geteilt_are_off_under_20(editor):
    """Rechenarten: ohne Zentrum at bis 10 Mal and Geteilt are disabled; from bis 20 they are offered."""
    page = editor(of("d", {**OF, "max": 10}))
    pick(page, "d")
    expect(field(page, "Mal")).to_be_disabled()
    expect(field(page, "Geteilt")).to_be_disabled()
    step(page, lambda: field(page, "Zahlenraum").select_option("20"))
    expect(field(page, "Mal")).to_be_enabled()
    expect(field(page, "Geteilt")).to_be_enabled()


def test_mit_zentrum_offers_only_plus_and_minus(editor):
    """Rechenarten: mit Zentrum Mal and Geteilt are disabled, whatever the Zahlenraum."""
    page = editor(of("d", {**OF, "centre": True, "max": 100}))
    pick(page, "d")
    expect(field(page, "Mal")).to_be_disabled()
    expect(field(page, "Geteilt")).to_be_disabled()
    expect(field(page, "Plus")).to_be_enabled()
    expect(field(page, "Minus")).to_be_enabled()


def test_the_last_checked_rechenart_is_disabled(editor):
    """Rechenarten: with only Plus checked, Plus is disabled: one Rechenart must stay."""
    page = editor(of("d", {**OF, "ops": ["+"]}))
    pick(page, "d")
    expect(field(page, "Plus")).to_be_disabled()
    expect(field(page, "Plus")).to_be_checked()


def test_several_rechenarten_give_links_of_their_own_operators(editor):
    """Rechenarten: Plus and Mal together (gemischt) give some links "+" and some "·"."""
    page = editor(of("d", {**OF, "max": 20, "ops": ["+", "*"], "count": 1, "columns": 1}))
    pick(page, "d")
    labels = op_labels(page)
    assert any(label[0] == "+" for label in labels), labels
    assert any(label[0] == DOT for label in labels), labels


def test_nur_zehnerzahlen_shows_only_multiples_of_ten(editor):
    """Einschränkung Nur Zehnerzahlen: at bis 100 every number and every Plus or Minus operand is a multiple of 10."""
    page = editor(
        of("d", {**OF, "max": 100, "only": "tens", "given": "ops", "count": 1, "columns": 1})
    )
    pick(page, "d")
    numbers = given_numbers(page)
    assert numbers and all(n % 10 == 0 for n in numbers), numbers


def test_nur_zehnerzahlen_operands_are_multiples_of_ten(editor):
    """Einschränkung Nur Zehnerzahlen: the Plus and Minus labels show multiples of 10 only."""
    page = editor(of("d", {**OF, "max": 100, "only": "tens", "count": 1, "columns": 1}))
    pick(page, "d")
    labels = op_labels(page)
    assert labels
    for label in labels:
        if label[0] in ("+", MINUS):
            assert int(label[1:]) % 10 == 0, label


def test_nur_hunderterzahlen_at_bis_1000_shows_only_multiples_of_100(editor):
    """Einschränkung Nur Hunderterzahlen: at bis 1000 every number is a multiple of 100."""
    page = editor(
        of("d", {**OF, "max": 1000, "only": "hundreds", "given": "ops", "count": 1, "columns": 1})
    )
    pick(page, "d")
    numbers = given_numbers(page)
    assert numbers and all(n % 100 == 0 for n in numbers), numbers


@pytest.mark.parametrize(
    "given, check",
    [
        ("start", lambda shown: shown[0][0] and not any(shown[0][1:]) and all(shown[1])),
        ("ops", lambda shown: all(shown[0]) and not any(shown[1])),
        (
            "mixed",
            lambda shown: (
                shown[0][0]
                and all(shown[1][j] != shown[0][j + 1] for j in range(len(shown[1]) - 1))
                and shown[1][-1]
            ),
        ),
    ],
    ids=["start", "ops", "mixed"],
)
def test_the_given_modes_show_the_right_boxes_and_operators(editor, given, check):
    """Gegeben: Startzahl und Operatoren shows the first box and every operator; Alle Zahlen, Operatoren fehlen
    every box and no operator; Gemischt the first box and, per link, either its operator or the box after it."""
    page = editor(of("d", {**OF, "given": given}))
    pick(page, "d")
    assert check(shown(page))


def test_mit_zentrum_shows_the_centre_as_the_given_number(editor):
    """Gegeben Startzahl und Operatoren: mit Zentrum the centre is the given number and every operator shows."""
    page = editor(of("d", {**OF, "centre": True, "count": 1, "columns": 1}))
    pick(page, "d")
    boxes, ops = shown(page)
    assert boxes[0] and not any(boxes[1:])
    assert all(ops)


def test_operatoren_zeichnen_off_removes_the_ellipses(editor):
    """Operatoren zeichnen: with it off no ellipse is drawn around an operator place, and the operators stay."""
    page = editor(of("d", OF))
    pick(page, "d")
    expect(at(page, "d").locator(".operatorfeld g.link ellipse").first).to_be_attached()
    step(page, lambda: field(page, "Operatoren zeichnen").uncheck())
    expect(at(page, "d").locator(".operatorfeld g.link ellipse")).to_have_count(0)
    expect(at(page, "d").locator(".operatorfeld g.link text.op").first).to_be_attached()


def test_neu_wuerfeln_changes_only_the_seed(editor):
    """Neu würfeln: stores another seed and keeps the other props; undo brings the old seed back."""
    client = user()
    page = editor(of("d", {**OF, "typed": [[0, 0, 15]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != OF["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == OF["seed"]


def test_one_more_operatorfeld_grows_the_block_and_keeps_the_box_size_in_one_undo(editor):
    """A change that needs more room: one more Operatorfeld (a second row) grows the block and keeps the
    box size; one Ctrl+Z gives back 2 fields and the height."""
    client = user()
    page = editor(of("d", OF), client=client)
    pick(page, "d")
    before = at(page, "d").locator("g.box rect").first.bounding_box()["width"]
    step(page, lambda: panel(page, "Ein Operatorfeld mehr").click())
    grown = block_of(doc(page, client))
    assert grown["props"]["count"] == 3
    assert grown["h"] > H
    after = at(page, "d").locator("g.box rect").first.bounding_box()["width"]
    assert abs(after - before) <= before * 0.02
    undo(page)
    back = block_of(doc(page, client))
    assert back["props"]["count"] == 2
    assert abs(back["h"] - H) < 0.2, back["h"]


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """Old sheets: odd stored props still draw, the panel opens and no fault shows."""
    client = user()
    odd = {
        "centre": "?",
        "count": -3,
        "columns": 99,
        "boxes": "x",
        "max": None,
        "ops": "?",
        "only": "?",
        "given": "?",
        "drawOps": "?",
        "typed": [[9, 9, 9], "a"],
        "seed": "s",
    }
    page = editor(
        of("odd", odd, z=1), box("empty", "operatorfeld", {}, z=2, y=150, w=180, h=H), client=client
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".operatorfeld")).to_be_visible()
    expect(at(page, "empty").locator(".operatorfeld")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Operatorfeld", exact=True)
    ).to_be_visible()
    assert not errors, errors


def test_mal_only_with_8_boxes_draws_every_field_and_no_hint(editor):
    """Every field fits: the hardest setting, Mal only bis 20 with 8 Kästchen, draws each field with its 8 boxes
    and the panel has no hint that fields are not shown (the vitest sweep proves it for every setting)."""
    page = editor(of("d", {**OF, "ops": ["*"], "boxes": 8, "count": 6, "columns": 3}))
    pick(page, "d")
    expect(at(page, "d").locator("g.field.over")).to_have_count(0)
    expect(at(page, "d").locator("g.box")).to_have_count(48)
    expect(hint(page).filter(has_text="werden nicht gezeigt")).to_have_count(0)


def test_an_operatorfeld_is_drawn_with_the_default_props(editor):
    """Pictures: the default block draws its 2 fields, each with 4 boxes and 4 links, and no field over."""
    page = editor(of("d", OF))
    expect(at(page, "d").locator(".operatorfeld g.field")).to_have_count(2)
    expect(at(page, "d").locator(".operatorfeld g.field g.box")).to_have_count(8)
    expect(at(page, "d").locator(".operatorfeld g.field g.link")).to_have_count(8)
    expect(at(page, "d").locator("g.field.over")).to_have_count(0)


def test_a_reload_keeps_the_variante_and_the_given_mode(editor):
    """Panel: Mit Zentrum and Gegeben Alle Zahlen survive a save and reload, and the block still shows its fields."""
    client = user()
    page = editor(of("d", {**OF, "centre": True, "given": "ops"}), client=client)
    pick(page, "d")
    doc(page, client)
    reload(page, page.url)
    pick(page, "d")
    expect(field(page, "Gegeben")).to_have_value("ops")
    assert props_of(doc(page, client))["centre"] is True
    expect(at(page, "d").locator("g.field[data-field='0'] g.box").first).to_be_attached()
