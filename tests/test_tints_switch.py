"""The colour switch, its undo step, and which blocks show it."""

import pytest
from playwright.sync_api import expect
from test_lock import (
    fest,
    undo,
)
from test_painter import held
from test_tints import (
    BLUE,
    CELLS,
    FIRST,
    GARBAGE,
    GREYS,
    PAIR,
    RED,
    SECOND,
    WORDS,
    WORDY,
    across,
    expect_tint_switch,
    greys,
    redo,
    set_colour,
    tint_switch,
    tinted,
)
from ui import (
    LINE,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
    pick,
    tints,
    user,
)


def test_the_switch_each_colour_the_greys_and_the_setting_undo_and_redo_one_step_each(editor):
    """A9: five changes, each one undo step; undo and redo walk them one by one."""
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    pick(page, "a")
    tint_switch(page).click()
    expect_tint_switch(page, True)
    set_colour(page, "Erste Silbe", FIRST)
    set_colour(page, "Zweite Silbe", SECOND)
    greys(page).click()
    expect(greys(page)).to_have_attribute("aria-pressed", "true")
    across(page).click()
    expect(across(page)).to_have_attribute("aria-pressed", "true")
    states = [
        WORDS,
        {**WORDS, "tints": PAIR},
        {**WORDS, "tints": [FIRST, RED]},
        {**WORDS, "tints": [FIRST, SECOND]},
        {**WORDS, "tints": GREYS},
        {**WORDS, "tints": GREYS, "tintsAcross": True},
    ]
    assert held(page, client)["a"] == states[5]
    for want in states[4::-1]:
        with page.expect_response(lambda res: res.request.method == "PATCH"):
            page.keyboard.press("Control+z")
        assert held(page, client)["a"] == want
    for want in states[1:]:
        with page.expect_response(lambda res: res.request.method == "PATCH"):
            page.keyboard.press("Control+y")
        assert held(page, client)["a"] == want


@pytest.mark.parametrize("kind", list(WORDY))
def test_every_kind_that_holds_words_takes_the_colours(editor, kind):
    """A11: a text, a shape with text, a table's cells, and each member of a group with words."""
    client = user()
    page = editor(*WORDY[kind], client=client)
    at(page, "a").click()
    wordy = ["a", "b"] if kind == "group" else ["a"]
    expect_picked(page, *(b["id"] for b in WORDY[kind]))
    expect(tint_switch(page)).to_have_count(1)
    tint_switch(page).click()
    expect_tint_switch(page, True)
    # The digits of a table get none.
    tinted(page, *wordy).to_have_text([("Fens", BLUE), ("ter", RED), ("Was", BLUE), ("ser", RED)])
    now = held(page, client)
    assert [now[name].get("tints") for name in wordy] == [PAIR] * len(wordy)
    # A group's line holds no words and stays as it is.
    assert kind != "group" or now["c"] == LINE


# A Lineatur with lines takes the colours since #357; Karo has none (tests/test_ruling_bows.py).
@pytest.mark.parametrize("kind", ["line", "image", "symbol", "maths"])
def test_a_block_that_holds_no_words_shows_no_colour_switch(editor, kind):
    """A11: a line, a picture, a symbol and maths have no colours to switch on."""
    client = user()
    page = editor(*({**b, "locked": False} for b in fest(client, kind)), client=client)
    pick(page, "fest")
    expect(page.locator(".panel h2").first).to_be_visible()
    expect(tint_switch(page)).to_have_count(0)


def test_a_sheet_without_colours_asks_for_no_splitter_and_saves_back_as_it_was(editor):
    """A12: a sheet with no colours asks for no splitter, and a save leaves it as it was."""
    client = user()
    old = [box("a", "text", TEXT), box("b", "table", {**TABLE, "line": "#222222"}, z=2)]
    page = editor(*old, client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    before = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    with page.expect_response(lambda res: res.request.method == "PATCH"):
        page.get_by_label("Titel", exact=True).fill("Anders")
    assert client.get(f"/api/sheets/{sheet_id}").json()["doc"] == before
    expect(page.locator(".syl, .bows")).to_have_count(0)
    asked = page.evaluate("performance.getEntriesByType('resource').map((entry) => entry.name)")
    assert asked and not [url for url in asked if "syllables" in url]


def test_a_sheet_with_colours_asks_for_the_splitter(editor):
    """A12: a text with colours asks for the splitter."""
    page = editor(box("a", "text", {**WORDS, "tints": PAIR}))
    tints(page, "a")
    asked = page.evaluate("performance.getEntriesByType('resource').map((entry) => entry.name)")
    assert [url for url in asked if "syllables" in url]


@pytest.mark.parametrize(
    "value", GARBAGE, ids=["text", "one", "hostile", "numbers", "object", "bool"]
)
def test_garbage_in_the_colours_shows_the_text_and_breaks_nothing(editor, value):
    """A12: a sheet with garbage in its colours shows the text, no colour, and no error."""
    page = editor(box("a", "text", {**WORDS, "tints": value}))
    faults = []
    page.on("pageerror", lambda fault: faults.append(fault))
    expect(at(page, "a")).to_have_text("Fenster Maus")
    assert tints(page, "a") == []
    pick(page, "a")
    expect(page.locator(".panel h2").first).to_be_visible()
    expect(
        page.locator(".panel").get_by_role("button", name="Silbenbögen", exact=True)
    ).to_be_visible()
    assert not faults


def test_the_switch_goes_on_unless_all_picked_have_the_colours_in_one_undo_step(editor):
    """I1: as the bows, for a text, a shape and a table picked together; one step for all."""
    client = user()
    blocks = [
        box("a", "text", {**WORDS, "tints": PAIR}),
        box("b", "shape", {**RECT, "text": "Wasser"}, z=2),
        box("t", "table", CELLS, z=3),
    ]
    page = editor(*blocks, client=client)

    def have():
        now = held(page, client)
        return [name for name in "abt" if now[name].get("tints")]

    pick(page, "a", "b", "t")
    # One of them has the colours, not all: the switch shows off, and a click sets them on all.
    expect_tint_switch(page, False)
    expect(tint_switch(page)).to_have_count(1)
    tint_switch(page).click()
    expect_tint_switch(page, True)
    tinted(page, "a", "b", "t").to_have_text(
        [
            ("Fens", BLUE),
            ("ter", RED),
            ("Maus", BLUE),
            ("Was", BLUE),
            ("ser", RED),
            ("Fens", BLUE),
            ("ter", RED),
            ("Was", BLUE),
            ("ser", RED),
        ]
    )
    assert have() == ["a", "b", "t"]
    undo(page).click()
    expect(undo(page)).to_be_disabled()
    tinted(page, "b", "t").to_have_count(0)
    assert have() == ["a"]
    redo(page).click()
    expect(redo(page)).to_be_disabled()
    expect_tint_switch(page, True)
    assert have() == ["a", "b", "t"]
    # All have them now: the next click takes them from all, in one step again.
    tint_switch(page).click()
    expect_tint_switch(page, False)
    tinted(page, "a", "b", "t").to_have_count(0)
    assert have() == []
    undo(page).click()
    tinted(page, "t").to_have_text([("Fens", BLUE), ("ter", RED), ("Was", BLUE), ("ser", RED)])
    assert have() == ["a", "b", "t"]
