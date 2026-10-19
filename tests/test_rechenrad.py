"""The Rechenrad on screen: its block in the editor and its format panel.

The docstrings name the lines of the checklist (#823) that each test proves. The numbers are read
from the page, never pinned: the generator may change.
"""

from collections import Counter

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

RR = {
    "count": 2,
    "columns": 2,
    "rings": 2,
    "segments": 8,
    "max": 20,
    "op": "+",
    "task": "outer",
    "seed": 7,
}
DEFAULTS = {k: v for k, v in RR.items() if k != "seed"}
DOT = "\N{MIDDLE DOT}"
H = 85.53  # the default height: 67 * 180 / 141, rounded as the insert does


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Rechenrad's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def rr(name, props, **more):
    """A Rechenrad block of 180 by 85.53 mm."""
    return box(name, "rechenrad", props, w=180, h=H, **more)


def block_of(stored):
    """The one Rechenrad of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "rechenrad"]
    return block


def props_of(stored):
    """The props of the one Rechenrad of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def numbers(page):
    """Per box of the Rechenräder on the page: wheel, ring, segment, and the text it shows (None if empty)."""
    return (
        at(page, "d")
        .locator("g.wheel")
        .evaluate_all(
            """wheels => wheels.flatMap(w => [...w.querySelectorAll('g.box')].map(b => {
            const t = b.querySelector('text.given');
            return [Number(w.dataset.wheel), Number(b.dataset.ring), Number(b.dataset.segment), t ? t.textContent : null];
        }))"""
        )
    )


def grid(page):
    """The number each box shows, by (wheel, ring, segment); None for an empty box."""
    return {(w, r, s): (None if t is None else int(t)) for w, r, s, t in numbers(page)}


def centres(page):
    """The label of each wheel's centre, such as "+7", in wheel order."""
    return (
        at(page, "d")
        .locator("g.wheel")
        .evaluate_all(
            """wheels => wheels.map(w => {
            const t = w.querySelector('g.centre text.given');
            return t ? t.textContent : null;
        })"""
        )
    )


def centre_number(page, wheel=0):
    """The number of a wheel's centre: its label without the operator."""
    return int(centres(page)[wheel][1:])


def test_a_rechenrad_is_inserted_from_the_maths_menu_with_the_default_props(editor):
    """Insert: the Mathe-Blöcke item "Rechenrad" adds a block with the default props and a whole seed, drawn as 2 wheels of 8 by 2 boxes with a centre each."""
    client = user()
    page = editor(client=client)
    insert(page, "Rechenrad")
    expect(
        page.locator(".panel").get_by_role("heading", name="Rechenrad", exact=True)
    ).to_be_visible()
    props = props_of(doc(page, client))
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    drawn = page.locator(".rechenrad").first
    expect(drawn.locator("g.wheel")).to_have_count(2)
    expect(drawn.locator("g.box")).to_have_count(32)
    expect(drawn.locator("g.centre")).to_have_count(2)


@pytest.mark.parametrize(
    "key, before, after, act",
    [
        ("count", 2, 3, lambda p: panel(p, "Ein Rechenrad mehr").click()),
        ("columns", 2, 3, lambda p: panel(p, "Eine Spalte mehr").click()),
        ("rings", 2, 3, lambda p: panel(p, "Ein Ring mehr").click()),
        ("segments", 8, 9, lambda p: panel(p, "Ein Segment mehr").click()),
        ("max", 20, 100, lambda p: field(p, "Zahlenraum").select_option("100")),
        ("op", "+", "-", lambda p: field(p, "Rechenart").select_option("-")),
        ("task", "outer", "inner", lambda p: field(p, "Aufgabe").select_option("inner")),
    ],
    ids=[
        "rechenraeder",
        "spalten",
        "ringe",
        "segmente",
        "zahlenraum",
        "rechenart",
        "aufgabe",
    ],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, before, after, act):
    """Panel: each setting changes its stored prop; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    page = editor(rr("d", RR), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_the_steppers_show_their_counts_and_stop_at_their_limits(editor):
    """Panel: the steppers say "2 Rechenräder", "2 Ringe" and "8 Segmente", and stop at 1 and 6 wheels, 1 and 3 columns, 2 and 3 rings, 4 and 12 segments."""
    page = editor(rr("d", RR))
    pick(page, "d")
    expect(page.locator(".panel").get_by_text("2 Rechenräder", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("2 Ringe", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("8 Segmente", exact=True)).to_be_visible()
    expect(panel(page, "Ein Rechenrad weniger")).to_be_enabled()
    expect(panel(page, "Ein Segment mehr")).to_be_enabled()
    top = editor(rr("d", {**RR, "count": 6, "columns": 3, "rings": 3, "segments": 12}))
    pick(top, "d")
    expect(panel(top, "Ein Rechenrad mehr")).to_be_disabled()
    expect(panel(top, "Eine Spalte mehr")).to_be_disabled()
    expect(panel(top, "Ein Ring mehr")).to_be_disabled()
    expect(panel(top, "Ein Segment mehr")).to_be_disabled()
    low = editor(rr("d", {**RR, "count": 1, "columns": 1, "segments": 4}))
    pick(low, "d")
    expect(panel(low, "Ein Rechenrad weniger")).to_be_disabled()
    expect(panel(low, "Eine Spalte weniger")).to_be_disabled()
    expect(panel(low, "Ein Ring weniger")).to_be_disabled()
    expect(panel(low, "Ein Segment weniger")).to_be_disabled()


def test_ringe_three_to_two_with_aufgabe_middle_is_one_undo_step(editor):
    """Implied 3: going from 3 Ringe to 2 sets Aufgabe "outer" in the same step; one Ctrl+Z brings 3 rings and "middle" back."""
    client = user()
    page = editor(rr("d", {**RR, "rings": 3, "task": "middle"}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Ein Ring weniger").click())
    props = props_of(doc(page, client))
    assert props["rings"] == 2
    assert props["task"] == "outer"
    undo(page)
    props = props_of(doc(page, client))
    assert props["rings"] == 3
    assert props["task"] == "middle"


def test_zahlenraum_ten_with_mal_is_one_undo_step_and_mal_and_geteilt_are_off(editor):
    """Implied 3: Zahlenraum 10 sets Rechenart "+" in the same step as Mal is chosen; one Ctrl+Z gives Mal back. Mal and Geteilt are disabled under 20."""
    client = user()
    page = editor(rr("d", {**RR, "op": "*"}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Zahlenraum").select_option("10"))
    props = props_of(doc(page, client))
    assert props["max"] == 10
    assert props["op"] == "+"
    for op in "*:":
        expect(field(page, "Rechenart").locator(f'option[value="{op}"]')).to_have_attribute(
            "disabled", ""
        )
    undo(page)
    props = props_of(doc(page, client))
    assert props["max"] == 20
    assert props["op"] == "*"


@pytest.mark.parametrize(
    "task, rings, check",
    [
        ("outer", 2, lambda g: {r for (_, r, _), x in g.items() if x is None} == {2}),
        ("inner", 2, lambda g: {r for (_, r, _), x in g.items() if x is None} == {1}),
        ("middle", 3, lambda g: {r for (_, r, _), x in g.items() if x is None} == {2}),
        (
            "mixed",
            2,
            lambda g: (
                all(
                    n == 1
                    for n in Counter((w, s) for (w, _, s), x in g.items() if x is None).values()
                )
                and len({(w, s) for (w, _, s) in g}) == 16
            ),
        ),
    ],
    ids=["outer", "inner", "middle", "mixed"],
)
def test_every_task_shows_the_right_boxes(editor, task, rings, check):
    """Aufgabentyp: outer leaves the outer ring empty, inner the inner ring, middle (3 rings) the middle ring, mixed one empty box per segment; the centre always shows."""
    page = editor(rr("d", {**RR, "task": task, "rings": rings}))
    pick(page, "d")
    g = grid(page)
    assert len(g) == 2 * rings * 8, g
    assert check(g), g
    expect(at(page, "d").locator("g.centre text.given")).to_have_count(2)


@pytest.mark.parametrize(
    "op, task, rings, max_",
    [("+", "mixed", 3, 20), ("-", "mixed", 3, 20), ("*", "inner", 3, 100)],
    ids=["plus", "minus", "mal"],
)
def test_each_segments_chain_holds_on_screen(editor, op, task, rings, max_):
    """Chain: on screen the numbers of neighbouring rings differ by the centre: x(r+1) = xr op c, with * for Mal."""
    page = editor(rr("d", {**RR, "op": op, "task": task, "rings": rings, "max": max_}))
    pick(page, "d")
    g = grid(page)
    pairs = 0
    for (w, r, s), x in g.items():
        y = g.get((w, r + 1, s))
        if x is None or y is None:
            continue
        c = centre_number(page, w)
        pairs += 1
        if op == "+":
            assert y == x + c, (w, r, s, x, y, c)
        elif op == "-":
            assert y == x - c, (w, r, s, x, y, c)
        else:
            assert y == x * c, (w, r, s, x, y, c)
    assert pairs > 0


def test_typing_a_number_into_the_centre_is_one_undo_step_and_changes_the_wheel(editor):
    """Eigene Zahlen: typing 9 into "Zahl im Zentrum" stores [0, 0, 0, 9], the centre shows "+9", and one Ctrl+Z removes it."""
    client = user()
    page = editor(rr("d", RR), client=client)
    pick(page, "d")
    centre = field(page, "Zahl im Zentrum")

    def type_nine():
        centre.press("Control+a")
        centre.press_sequentially("9")

    step(page, type_nine)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 0, 9]]
    expect(at(page, "d").locator("g.wheel[data-wheel='0'] g.centre text.given")).to_have_text("+9")
    centre.press("Control+z")
    assert "typed" not in props_of(doc(page, client))


def test_typing_into_ring_one_stores_the_number_and_the_outer_box_follows(editor):
    """Eigene Zahlen: typing 5 into "Ring 1, Feld 1" stores [0, 1, 0, 5], and the outer box of that segment shows 5 plus the centre."""
    client = user()
    page = editor(rr("d", {**RR, "task": "inner"}), client=client)
    pick(page, "d")
    number = field(page, "Ring 1, Feld 1")

    def type_five():
        number.press("Control+a")
        number.press_sequentially("5")

    step(page, type_five)
    assert props_of(doc(page, client))["typed"] == [[0, 1, 0, 5]]
    assert grid(page)[(0, 2, 0)] == 5 + centre_number(page)


def test_a_box_field_keeps_focus_and_digits_while_the_block_redraws(editor):
    """Eigene Zahlen: typing "17" into "Ring 1, Feld 3" keeps the focus and the digits, and stores [0, 1, 2, 17]."""
    client = user()
    page = editor(rr("d", RR), client=client)
    pick(page, "d")
    number = field(page, "Ring 1, Feld 3")
    number.click()
    step(page, lambda: page.keyboard.type("17"))
    expect(number).to_be_focused()
    expect(number).to_have_value("17")
    assert props_of(doc(page, client))["typed"] == [[0, 1, 2, 17]]
    # Both digits are one undo step: one Ctrl+Z in the field takes the whole number back.
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


WRONG = {**RR, "typed": [[0, 1, 0, 5], [0, 2, 0, 9999]]}


def test_a_typed_outer_number_that_does_not_fit_gives_the_hint_and_marks_the_wheel_wrong(editor):
    """Eigene Zahlen: typed 5 in ring 1 and 9999 in ring 2 of segment 1 do not fit the centre: the hint names Rechenrad 1 and that wheel gets class wrong."""
    page = editor(rr("d", WRONG))
    pick(page, "d")
    expect(hint(page)).to_have_text("Rechenrad 1: Die Zahlen passen nicht zum Zentrum.")
    expect(at(page, "d").locator("g.wheel.wrong")).to_have_count(1)
    expect(at(page, "d").locator("g.wheel[data-wheel='0'].wrong")).to_have_count(1)


def test_eigene_zahlen_entfernen_is_one_undo_step_and_removes_the_hint(editor):
    """Eigene Zahlen: "Eigene Zahlen entfernen" clears every typed number and the hint in one step; one Ctrl+Z brings them back."""
    client = user()
    page = editor(rr("d", WRONG), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_count(1)
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    expect(hint(page)).to_have_count(0)
    undo(page)
    assert props_of(doc(page, client))["typed"] == WRONG["typed"]
    expect(hint(page)).to_have_count(1)


def test_a_typed_zero_centre_with_geteilt_is_wrong_and_shows_no_nan_or_infinity(editor):
    """Eigene Zahlen: with Geteilt a typed centre 0 gives the hint, marks the wheel wrong, and the svg has no "NaN" or "Infinity"."""
    page = editor(rr("d", {**RR, "op": ":", "typed": [[0, 0, 0, 0]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Rechenrad 1: Die Zahlen passen nicht zum Zentrum.")
    expect(at(page, "d").locator("g.wheel[data-wheel='0'].wrong")).to_have_count(1)
    text = at(page, "d").locator(".rechenrad svg").text_content()
    assert "NaN" not in text and "Infinity" not in text, text
    # No inner number fits a centre of 0 with Geteilt: every box stays empty, none shows a made-up 0.
    expect(at(page, "d").locator("g.wheel[data-wheel='0'] g.box text")).to_have_count(0)


def test_a_typed_number_that_does_not_fit_shows_as_typed(editor):
    """Review of #927: typed 5 in ring 1 and 99 in ring 2 of segment 1 with a centre +7: the wheel is wrong and both show as typed."""
    page = editor(rr("d", {**RR, "typed": [[0, 0, 0, 7], [0, 1, 0, 5], [0, 2, 0, 99]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Rechenrad 1: Die Zahlen passen nicht zum Zentrum.")
    expect(field(page, "Ring 1, Feld 1")).to_have_value("5")
    expect(field(page, "Ring 2, Feld 1")).to_have_value("99")


def test_neu_wuerfeln_changes_only_the_seed(editor):
    """Neu würfeln: stores another seed and keeps the other props; undo brings the old seed back."""
    client = user()
    page = editor(rr("d", {**RR, "typed": [[0, 1, 0, 5]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != RR["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == RR["seed"]


def test_one_more_rechenrad_grows_the_block_and_keeps_the_wheel_size_in_one_undo(editor):
    """A change that needs more room: a third Rechenrad (2 columns, a second row) grows the block and keeps the wheel size; one Ctrl+Z gives back the wheel and the height."""
    client = user()
    page = editor(rr("d", RR), client=client)
    pick(page, "d")
    before = at(page, "d").locator("g.wheel").first.bounding_box()["width"]
    step(page, lambda: panel(page, "Ein Rechenrad mehr").click())
    grown = block_of(doc(page, client))
    assert grown["props"]["count"] == 3
    assert grown["h"] > H
    after = at(page, "d").locator("g.wheel").first.bounding_box()["width"]
    assert abs(after - before) <= before * 0.02
    undo(page)
    back = block_of(doc(page, client))
    assert back["props"]["count"] == 2
    assert abs(back["h"] - H) < 0.2, back["h"]


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """Old sheets: odd stored props still draw, the panel opens and no fault shows."""
    client = user()
    odd = {
        "count": -3,
        "columns": 99,
        "rings": "x",
        "segments": 99,
        "max": None,
        "op": "?",
        "task": "?",
        "seed": "s",
        "typed": [[9, 9, 9, 9], "a"],
    }
    page = editor(rr("odd", odd, z=1), rr("empty", {}, z=2, y=150), client=client)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".rechenrad")).to_be_visible()
    expect(at(page, "empty").locator(".rechenrad")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Rechenrad", exact=True)
    ).to_be_visible()
    assert not errors, errors


def test_a_reload_keeps_the_rings_the_segments_and_the_task(editor):
    """Panel: 3 Ringe, 6 Segmente and Aufgabe Gemischt survive a save and reload, and the block still draws them."""
    client = user()
    page = editor(rr("d", {**RR, "rings": 3, "segments": 6, "task": "mixed"}), client=client)
    pick(page, "d")
    doc(page, client)
    reload(page, page.url)
    pick(page, "d")
    expect(field(page, "Aufgabe")).to_have_value("mixed")
    expect(page.locator(".panel").get_by_text("3 Ringe", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("6 Segmente", exact=True)).to_be_visible()
    props = props_of(doc(page, client))
    assert (props["rings"], props["segments"], props["task"]) == (3, 6, "mixed")
    expect(at(page, "d").locator("g.box[data-ring='3']")).to_have_count(12)
