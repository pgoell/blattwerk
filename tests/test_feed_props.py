"""Stored props, the keys, and Lückenwörter against Schüttelwörter.

The helpers live in test_feed.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_feed import (
    CHOICE,
    LISTED,
    WORDS,
    editor,  # noqa: F401
)
from test_gaps import panel, step
from test_keys_focus import choose
from test_painter import held
from ui import (
    FIELD,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    pick,
    user,
)


def test_tab_reaches_the_new_controls_and_keys_press_them(editor):
    """I6: Tab reaches "3 Spalten" and "Lückenwörter"; Space and Enter press them."""
    client = user()
    page = editor(box("a", "text", LISTED), client=client, words=WORDS)
    pick(page, "a")
    page.get_by_label(CHOICE).focus()
    for _ in range(12):
        if panel(page, "3 Spalten").evaluate("el => el === document.activeElement"):
            break
        page.keyboard.press("Tab")
    expect(panel(page, "3 Spalten")).to_be_focused()
    page.keyboard.press("Space")
    expect(panel(page, "3 Spalten")).to_have_attribute("aria-pressed", "true")
    for _ in range(12):
        if panel(page, "Lückenwörter").evaluate("el => el === document.activeElement"):
            break
        page.keyboard.press("Tab")
    expect(panel(page, "Lückenwörter")).to_be_focused()
    page.keyboard.press("Enter")
    expect(panel(page, "Lückenwörter")).to_have_attribute("aria-pressed", "true")
    stored = held(page, client)["a"]
    assert stored["listCols"] == 3
    assert stored["holes"] == "one"


@pytest.mark.parametrize(
    "props, expected, gaps",
    [
        pytest.param({**TEXT, "list": "yes"}, ["Hallo"], 0, id="list-yes"),
        pytest.param({**LISTED, "listCols": 9}, WORDS, 0, id="cols-9"),
        pytest.param({**LISTED, "holes": "x"}, WORDS, 0, id="holes-x"),
        pytest.param({**LISTED, "holes": "one", "holeSeed": "q"}, WORDS, 6, id="seed-q"),
    ],
)
def test_garbage_in_the_new_props_draws_the_plain_block(editor, props, expected, gaps):
    """I7: stored garbage draws the plain text, or the words whole in one column."""
    page = editor(box("a", "text", props), words=WORDS)
    # A plain text draws its paragraphs in the frame with no .rich around them.
    paragraphs = at(page, "a").locator(".frame p")
    expect(paragraphs).to_have_count(len(expected))
    assert paragraphs.all_text_contents() == expected
    lefts = paragraphs.evaluate_all(
        "els => new Set(els.map((p) => Math.round(p.getBoundingClientRect().left))).size"
    )
    assert lefts == 1
    expect(at(page, "a").locator(".gap")).to_have_count(gaps)


def test_a_sheet_without_the_new_props_saves_back_as_it_was(editor):
    """I7: a sheet with no list, columns, holes or seed saves back as it was."""
    client = user()
    old = [
        box("a", "text", TEXT),
        box("c", "shape", {**RECT, "text": "Hund"}, z=2),
        box("t", "table", TABLE, z=3),
    ]
    page = editor(*old, client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    before = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    pick(page, "a")
    page.get_by_label("Titel", exact=True).fill("Anders")
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert", timeout=5000)
    after = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    assert after == before
    new = {"list", "listCols", "holes", "holeSeed"}
    for block in before["pages"][0]["blocks"]:
        assert not new & set(block["props"])


def test_lueckenwoerter_and_schuettelwoerter_shut_each_other_out(editor):
    """I8: Lückenwörter and Schüttelwörter shut each other out."""
    client = user()
    page = editor(box("a", "text", {**LISTED, "mix": 7}), client=client, words=WORDS)
    pick(page, "a")
    step(page, lambda: panel(page, "Lückenwörter").click())
    stored = held(page, client)["a"]
    assert "mix" not in stored
    assert stored["holes"] == "one"
    step(page, lambda: panel(page, "Schüttelwörter").click())
    stored = held(page, client)["a"]
    assert "holes" not in stored
    assert type(stored["mix"]) is int


def test_the_choice_gives_the_keys_back_to_the_sheet_and_ends_the_writing(editor):
    """I6: a choice made while a text is written in gives the keys back and ends the writing."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client, words=WORDS)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    control = choose(page, CHOICE)
    expect(control).not_to_be_focused()
    expect(page.locator(FIELD)).to_have_count(0)
    assert held(page, client)["a"]["list"] is True
    expect(at(page, "a").locator(".frame.listed .rich p")).to_have_count(len(WORDS))
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("X", exact=True)).to_have_value("16")


def test_a_linked_block_shows_no_gap_controls(editor):
    """I8: a linked text shows no Lücke, Jedes n-te Wort or Lösungswörter; an unlinked one does."""
    linked = editor(box("a", "text", LISTED), words=WORDS)
    pick(linked, "a")
    for label in ("Lücke", "Jedes n-te Wort", "Lösungswörter"):
        expect(panel(linked, label)).to_have_count(0)
    plain = editor(box("b", "text", TEXT))
    pick(plain, "b")
    for label in ("Lücke", "Jedes n-te Wort", "Lösungswörter"):
        expect(panel(plain, label)).to_have_count(1)
