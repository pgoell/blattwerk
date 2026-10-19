"""The Zahlenkette: its block in the editor and its format panel.

The docstrings name the lines of the checklist (#820) that each test proves.
"""

import itertools
import re

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import panel, step
from test_suchsel_print import key_print
from test_words import redo, undo
from test_zahlenkette_print import chains_of
from ui import at, box, doc, pick, reload, user

KETTE = {
    "count": 4,
    "columns": 2,
    "rings": 6,
    "max": 20,
    "op": "+",
    "showStep": False,
    "given": "start",
    "seed": 7,
}
FREE = [True, False, True, False, False, True]
TYPED = [[0, 0, 5], [0, 1, 8]]


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zahlenkette's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def kette(name, props):
    """A Zahlenkette block of 180 by 39 mm."""
    return box(name, "zahlenkette", props, w=180, h=39)


def block_of(stored):
    """The one Zahlenkette of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zahlenkette"]
    return block


def props_of(stored):
    """The props of the one Zahlenkette of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def given_rings(page, chain):
    """The ring indexes of a chain that show their number, in order."""
    shown = (
        at(page, "d")
        .locator(f'g.chain[data-chain="{chain}"] g.ring')
        .evaluate_all(
            "els => els.map((r) => [Number(r.dataset.ring), !!r.querySelector('text.given')])"
        )
    )
    return [j for j, given in shown if given]


def drawn_numbers(page, chain):
    """The numbers that a chain shows, in ring order."""
    return (
        at(page, "d")
        .locator(f'g.chain[data-chain="{chain}"] text.given')
        .evaluate_all("els => els.map((t) => Number(t.textContent))")
    )


@pytest.mark.parametrize(
    "key, before, after, act",
    [
        ("rings", 6, 8, lambda p: field(p, "Ringe").select_option("8")),
        ("count", 4, 5, lambda p: panel(p, "Eine Kette mehr").click()),
        ("columns", 2, 3, lambda p: panel(p, "Eine Spalte mehr").click()),
        ("max", 20, 100, lambda p: field(p, "Zahlenraum").select_option("100")),
        ("op", "+", "-", lambda p: field(p, "Rechenart").select_option(label="Minus")),
        ("showStep", False, True, lambda p: field(p, "Schritt anschreiben").click()),
        ("given", "start", "ends", lambda p: field(p, "Gegebene Ringe").select_option("ends")),
    ],
    ids=[
        "ringe",
        "ketten",
        "spalten",
        "zahlenraum",
        "rechenart",
        "schritt-anschreiben",
        "gegebene-ringe",
    ],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, before, after, act):
    """I1: each setting changes its stored prop; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    page = editor(kette("d", KETTE), client=client)
    pick(page, "d")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


@pytest.mark.parametrize(
    "given, expected",
    [("start", [0, 1]), ("ends", [0, 5]), ("random", None), ("free", [0, 2, 5])],
    ids=["start", "ends", "random", "free"],
)
def test_the_given_rings_show_their_numbers_in_every_chain(editor, given, expected):
    """A5: "Anfang" shows rings 1 and 2, "Anfang und Ende" the first and the last, "Zufällig" at least 2,
    and "Freie Wahl" the flagged rings, in every chain."""
    page = editor(kette("d", {**KETTE, "given": given, "free": FREE}))
    pick(page, "d")
    for chain in range(4):
        shown = given_rings(page, chain)
        if expected is None:
            assert len(shown) >= 2
        else:
            assert shown == expected


def test_a_free_ring_flips_shows_in_every_chain_and_survives_a_reload(editor):
    """A6: "Ring 3" flips free[2] and shows in every chain; it survives a save and reload."""
    client = user()
    page = editor(kette("d", {**KETTE, "given": "free", "free": [False] * 6}), client=client)
    pick(page, "d")
    ring = panel(page, "Ring 3")
    expect(ring).to_have_attribute("aria-pressed", "false")
    step(page, ring.click)
    assert props_of(doc(page, client))["free"][2] is True
    expect(ring).to_have_attribute("aria-pressed", "true")
    for chain in range(4):
        assert given_rings(page, chain) == [2]
    reload(page, page.url)
    pick(page, "d")
    expect(panel(page, "Ring 3")).to_have_attribute("aria-pressed", "true")
    assert props_of(doc(page, client))["free"][2] is True


def test_mal_is_not_offered_under_100_and_a_smaller_zahlenraum_turns_mal_to_plus_in_one_undo(
    editor,
):
    """I3: "Mal" is disabled at bis 20; at bis 100 Mal is stored, and bis 20 stores "+" and max 20 in one step."""
    client = user()
    page = editor(kette("d", KETTE), client=client)
    pick(page, "d")
    expect(field(page, "Rechenart").locator('option[value="*"][disabled]')).to_have_count(1)
    step(page, lambda: field(page, "Zahlenraum").select_option("100"))
    step(page, lambda: field(page, "Rechenart").select_option("*"))
    assert props_of(doc(page, client))["op"] == "*"
    step(page, lambda: field(page, "Zahlenraum").select_option("20"))
    props = props_of(doc(page, client))
    assert props["op"] == "+"
    assert props["max"] == 20
    undo(page)
    props = props_of(doc(page, client))
    assert props["op"] == "*"
    assert props["max"] == 100


def test_a_fixed_step_is_stored_and_every_chain_keeps_it(editor):
    """A7: "Fest" with 3 stores step 3; with all rings given, each chain's numbers differ by 3."""
    client = user()
    page = editor(kette("d", {**KETTE, "given": "free", "free": [True] * 6}), client=client)
    pick(page, "d")
    field(page, "Schrittweite").select_option(label="Fest")

    def type_three():
        field(page, "Schritt").fill("3")
        field(page, "Schritt").press("Enter")

    step(page, type_three)
    assert props_of(doc(page, client))["step"] == 3
    for chain in range(4):
        numbers = drawn_numbers(page, chain)
        assert len(numbers) == 6
        assert [b - a for a, b in itertools.pairwise(numbers)] == [3] * 5


def test_a_step_out_of_range_is_not_stored_and_escape_drops_it(editor):
    """A7: a step of 0 gives "Mindestens 1." and stores nothing; 5 typed then Escape stores nothing."""
    client = user()
    page = editor(kette("d", KETTE), client=client)
    pick(page, "d")
    field(page, "Schrittweite").select_option(label="Fest")
    field(page, "Schritt").fill("0")
    # While the field holds the wrong step it says why, as the Zahlenhaus's own Zahlenraum does.
    expect(hint(page)).to_have_text("Mindestens 1.")
    field(page, "Schritt").press("Enter")
    expect(field(page, "Schritt")).to_have_value("")
    assert "step" not in props_of(doc(page, client))
    field(page, "Schritt").fill("5")
    field(page, "Schritt").press("Escape")
    expect(field(page, "Schritt")).to_have_value("")
    assert "step" not in props_of(doc(page, client))


def test_new_dice_store_another_seed_and_keep_the_other_props(editor):
    """A8: "Neu würfeln" stores another seed and keeps the other props; undo brings the old seed back."""
    client = user()
    page = editor(kette("d", {**KETTE, "typed": [[0, 0, 15]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != KETTE["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == KETTE["seed"]


def test_a_new_number_of_chains_grows_the_block_and_undo_brings_its_height_back(editor):
    """I2: Ketten 4 to 6 makes the stored block taller; two Ctrl+Z bring the old height back."""
    client = user()
    page = editor(kette("d", KETTE), client=client)
    pick(page, "d")
    assert block_of(doc(page, client))["h"] == 39
    step(page, lambda: panel(page, "Eine Kette mehr").click())
    step(page, lambda: panel(page, "Eine Kette mehr").click())
    assert block_of(doc(page, client))["h"] > 39
    undo(page)
    undo(page)
    assert block_of(doc(page, client))["h"] == 39


def test_a_new_number_of_rings_keeps_the_free_flags_and_typed_numbers_that_still_fit(editor):
    """I4: more Ringe keep the free flags (new rings take "start"'s false); fewer drop the flags of the rings gone,
    and the typed number of ring 1 stays."""
    client = user()
    page = editor(
        kette("d", {**KETTE, "given": "free", "free": FREE, "typed": [[0, 0, 5], [0, 4, 9]]}),
        client=client,
    )
    pick(page, "d")
    step(page, lambda: field(page, "Ringe").select_option("8"))
    assert props_of(doc(page, client))["free"] == [*FREE, False, False]
    step(page, lambda: field(page, "Ringe").select_option("4"))
    assert props_of(doc(page, client))["free"] == FREE[:4]
    expect(field(page, "Zahl in Ring 1")).to_have_value("5")
    expect(field(page, "Zahl in Ring 5")).to_have_count(0)


def test_typing_two_digits_into_a_ring_stores_them_and_one_undo_takes_both_back(editor):
    """A10/I1: "1" then "2" into "Zahl in Ring 1" store typed [[0, 0, 12]]; one Ctrl+Z in the field removes both."""
    client = user()
    page = editor(kette("d", KETTE), client=client)
    pick(page, "d")
    number = field(page, "Zahl in Ring 1")

    def type_twelve():
        number.press("Control+a")
        number.press_sequentially("1")
        number.press_sequentially("2")

    step(page, type_twelve)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 12]]
    number.press("Control+z")
    assert "typed" not in props_of(doc(page, client))


def test_typed_numbers_that_break_the_step_give_the_hint_and_fixing_it_removes_it(editor):
    """A10: with step 3, 5 and 9 in rings 1 and 2 give "Kette 1: die Zahlen passen nicht zum Schritt."; 8 in ring 2 clears it."""
    client = user()
    page = editor(kette("d", {**KETTE, "step": 3, "typed": [[0, 0, 5], [0, 1, 9]]}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_text("Kette 1: die Zahlen passen nicht zum Schritt.")
    step(page, lambda: field(page, "Zahl in Ring 2").fill("8"))
    expect(hint(page).filter(has_text="passen nicht zum Schritt")).to_have_count(0)


def test_remove_own_numbers_is_one_undo_step(editor):
    """I5: "Eigene Zahlen entfernen" clears every typed number in one step; one Ctrl+Z brings them back."""
    client = user()
    page = editor(kette("d", {**KETTE, "typed": TYPED}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == TYPED


def test_a_step_too_big_for_the_zahlenraum_is_not_drawn_and_the_panel_says_why(editor):
    """A11: step 9 at bis 20 with 6 rings: every chain is marked "over" and draws no ring; the panel
    says the chains do not fit the Zahlenraum."""
    page = editor(kette("d", {**KETTE, "step": 9}))
    pick(page, "d")
    expect(
        hint(page).filter(
            has_text="Die Ketten passen nicht in den Zahlenraum und werden nicht gezeigt."
        )
    ).to_be_visible()
    for chain in range(4):
        chain_locator = at(page, "d").locator(f'g.chain[data-chain="{chain}"]')
        expect(chain_locator).to_have_class(re.compile(r"\bover\b"))
        expect(chain_locator.locator("g.ring")).to_have_count(0)


def test_a_long_mal_chain_at_the_smallest_zahlenraum_is_not_drawn_and_a_shorter_one_stays_inside(
    editor, browser, server
):
    """A11: Mal with 12 rings at bis 100 draws no chain and the panel says why; 7 rings draw every
    chain, and on the answer key every number stays at most 100."""
    client = user()
    page = editor(kette("d", {**KETTE, "op": "*", "max": 100, "rings": 12}), client=client)
    pick(page, "d")
    expect(
        hint(page).filter(
            has_text="Die Ketten passen nicht in den Zahlenraum und werden nicht gezeigt."
        )
    ).to_be_visible()
    expect(at(page, "d").locator("g.chain.over")).to_have_count(4)
    expect(at(page, "d").locator("g.ring")).to_have_count(0)
    step(page, lambda: field(page, "Ringe").select_option("7"))
    for chain in range(4):
        expect(at(page, "d").locator(f'g.chain[data-chain="{chain}"] g.ring')).to_have_count(7)
    paper = key_print(browser, server, sheet_id(page))
    key = chains_of(paper.locator(".zahlenkette"))
    paper.context.close()
    assert len(key) == 4
    for rings in key:
        assert len(rings) == 7
        assert all(n is not None and int(n) <= 100 for n in rings), rings


def test_more_rings_keep_the_ring_size_and_take_fewer_columns_in_one_undo(editor):
    """A8: Ringe 6 to 12 keeps the ring size (within 2 %), takes Spalten 2 down to 1 and grows the
    block; one Ctrl+Z gives back 6 rings, 2 columns and 39 mm."""
    client = user()
    page = editor(kette("d", KETTE), client=client)
    pick(page, "d")
    before = at(page, "d").locator("g.ring circle").first.bounding_box()["width"]
    step(page, lambda: field(page, "Ringe").select_option("12"))
    props = props_of(doc(page, client))
    assert props["columns"] == 1
    assert props["rings"] == 12
    assert block_of(doc(page, client))["h"] > 39
    after = at(page, "d").locator("g.ring circle").first.bounding_box()["width"]
    assert abs(after - before) <= before * 0.02
    undo(page)
    props = props_of(doc(page, client))
    assert props["rings"] == 6
    assert props["columns"] == 2
    assert block_of(doc(page, client))["h"] == 39


def test_a_rechenart_change_into_mal_drops_the_fixed_step_in_one_undo(editor):
    """A7: Rechenart Mal at bis 100 stores op "*" and drops the fixed step 50; one Ctrl+Z gives back
    "+" and step 50."""
    client = user()
    page = editor(kette("d", {**KETTE, "max": 100, "step": 50}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Rechenart").select_option("*"))
    props = props_of(doc(page, client))
    assert props["op"] == "*"
    assert "step" not in props
    undo(page)
    props = props_of(doc(page, client))
    assert props["op"] == "+"
    assert props["step"] == 50


def test_a_ring_field_keeps_focus_and_digits_while_the_block_redraws(editor):
    """A10: typing "17" into "Zahl in Ring 3" keeps the focus and the digits while the block redraws,
    and stores [0, 2, 17]."""
    client = user()
    page = editor(kette("d", KETTE), client=client)
    pick(page, "d")
    number = field(page, "Zahl in Ring 3")
    number.click()
    step(page, lambda: page.keyboard.type("17"))
    expect(number).to_be_focused()
    expect(number).to_have_value("17")
    assert props_of(doc(page, client))["typed"] == [[0, 2, 17]]
