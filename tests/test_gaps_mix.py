"""Neu mischen: the seed, one undo step, and a shuffle that has to move.

The gap helpers live in test_gaps.py."""

from playwright.sync_api import expect
from test_gaps import (
    GAPPED_TABLE,
    SHAPE_TWO,
    TWO,
    panel,
    step,
)
from test_lock import FRAMES
from test_painter import held
from ui import (
    TEXT,
    box,
    pick,
    user,
)


def test_losungswörter_stores_a_seed_that_neu_mischen_changes_and_off_removes(editor):
    """A7: the box stores a seed, a new shuffle stores another, and off removes the seed."""
    client = user()
    page = editor(box("a", "text", TWO), client=client)
    pick(page, "a")
    panel(page, "Lösungswörter").click()
    seed = held(page, client)["a"]["bank"]
    assert 1 <= seed <= 2147483647
    panel(page, "Neu mischen").click()
    assert held(page, client)["a"]["bank"] != seed
    panel(page, "Lösungswörter").click()
    assert "bank" not in held(page, client)["a"]


def test_neu_mischen_on_a_text_and_a_table_is_one_undo_step(editor):
    """A1, A2, I1: a press of Neu mischen on a text and a table is one step; two presses, two."""
    client = user()
    page = editor(box("a", "text", TWO), box("t", "table", GAPPED_TABLE, z=2), client=client)
    pick(page, "a", "t")
    step(page, lambda: panel(page, "Lösungswörter").click())
    s0 = {name: held(page, client)[name]["bank"] for name in ("a", "t")}
    step(page, lambda: panel(page, "Neu mischen").click())
    s1 = {name: held(page, client)[name]["bank"] for name in ("a", "t")}
    assert s1["a"] != s0["a"] and s1["t"] != s0["t"]
    step(page, lambda: panel(page, "Neu mischen").click())
    s2 = {name: held(page, client)[name]["bank"] for name in ("a", "t")}
    assert s2["a"] != s1["a"] and s2["t"] != s1["t"]
    step(page, lambda: page.keyboard.press("Control+z"))
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} == s1
    step(page, lambda: page.keyboard.press("Control+z"))
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} == s0
    step(page, lambda: page.keyboard.press("Control+y"))
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} == s1


def test_neu_mischen_on_a_shape_and_a_table_is_one_undo_step(editor):
    """I2: a press of Neu mischen on a shape with words and a table is one step, one undo."""
    client = user()
    page = editor(
        box("a", "shape", SHAPE_TWO),
        box("t", "table", GAPPED_TABLE, z=2),
        client=client,
    )
    pick(page, "a", "t")
    step(page, lambda: panel(page, "Lösungswörter").click())
    s0 = {name: held(page, client)[name]["bank"] for name in ("a", "t")}
    step(page, lambda: panel(page, "Neu mischen").click())
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} != s0
    step(page, lambda: page.keyboard.press("Control+z"))
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} == s0


def test_neu_mischen_draws_a_seed_no_selected_block_had(editor):
    """A3: the new seed differs from the old seed of every selected block, not just the first."""
    client = user()
    page = editor(
        box("a", "text", {**TWO, "bank": 5}),
        box("t", "table", {**GAPPED_TABLE, "bank": 7}, z=2),
        client=client,
    )
    pick(page, "a", "t")
    # The first draw gives the table's old seed 7, the next one 9; a draw of n - 0.5 gives n.
    # Then 9 stays.
    page.evaluate(
        """() => {
            const drawn = [7, 9].map((n) => (n - 0.5) / 2147483647);
            Math.random = () => (drawn.length > 1 ? drawn.shift() : drawn[0]);
        }"""
    )
    step(page, lambda: panel(page, "Neu mischen").click())
    now = held(page, client)
    assert now["a"]["bank"] == 9 and now["t"]["bank"] == 9


def test_neu_mischen_never_leaves_the_solution_words_as_they_stood(editor):
    """I3: every press of Neu mischen shows the solution words in another order than before."""
    client = user()
    gapped_words = {
        **TEXT,
        "text": "Hund Katze Vogel",
        "rich": [
            {
                "runs": [
                    {"text": "Hund", "gap": True},
                    {"text": " "},
                    {"text": "Katze", "gap": True},
                    {"text": " "},
                    {"text": "Vogel", "gap": True},
                ]
            }
        ],
        "bank": 7,
    }
    page = editor(box("a", "text", gapped_words), client=client)
    pick(page, "a")
    expect(page.locator(".bank span")).to_have_count(3)
    for _ in range(15):
        before = page.locator(".bank span").all_text_contents()
        step(page, lambda: panel(page, "Neu mischen").click())
        expect(page.locator(".bank span")).not_to_have_text(before)


def test_neu_mischen_with_one_solution_word_makes_no_step(editor):
    """A press of Neu mischen that moves no word stores nothing and makes no undo step."""
    client = user()
    hund = {"runs": [{"text": "Hund", "gap": True}]}
    page = editor(
        box("a", "text", {**TEXT, "text": "Hund", "rich": [hund], "bank": 7}), client=client
    )
    pick(page, "a")
    undo = page.get_by_label("Rückgängig", exact=True)
    expect(undo).to_be_disabled()
    panel(page, "Neu mischen").click()
    page.evaluate(FRAMES)
    expect(undo).to_be_disabled()
    assert held(page, client)["a"]["bank"] == 7
