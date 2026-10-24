"""The Lernwörter in a text block, editing side: the choice, the columns, a change to the list, undo
and redo, the keys, copies, and the switches. What the block draws and prints is in
test_feed_print.py, the Knickblatt in test_knick.py.

The docstrings name the lines of the checklist that each test proves. The sheet starts with WORDS.
"""

from itertools import pairwise

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_gaps import panel, step
from test_painter import held
from test_words import field, list_tab, redo, undo
from ui import (
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    apart,
    at,
    box,
    doc,
    pick,
    saved,
    unpick,
    user,
)

WORDS = ["Hund", "Katze", "Maus", "Vogel", "Pferd", "Schule"]
LISTED = {**TEXT, "list": True}
KNICK = {**RULING, "kind": "l3", "list": "fold", "folds": 2}
CHOICE = "Text des Textfelds"


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the tabs Format and Lernwörter are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def heights(page, client):
    """Each block's height as the server holds it, by the block's name."""
    return {b["id"]: b["h"] for b in saved(page, client)}


@pytest.mark.parametrize(
    "kind, props",
    [
        pytest.param("text", TEXT, id="text"),
        pytest.param("shape", {**RECT, **TEXT}, id="shape"),
    ],
)
def test_the_choice_links_a_text_and_it_lists_the_words(editor, kind, props):
    """A1: the choice "Text aus Lernwörtern" links a text or shape, which then lists the words."""
    client = user()
    page = editor(box("a", kind, props), client=client, words=WORDS)
    pick(page, "a")
    choice = page.get_by_label(CHOICE)
    choice.select_option(label="Text aus Lernwörtern")
    expect(choice).to_have_value("list")
    stored = held(page, client)["a"]
    assert stored["list"] is True
    assert stored["text"] == "Hallo"
    paragraphs = at(page, "a").locator(".frame.listed .rich p")
    expect(paragraphs).to_have_count(len(WORDS))
    assert paragraphs.all_text_contents() == WORDS


def test_a_linked_text_with_no_words_says_so_in_the_editor(editor):
    """A1: a linked text with no list in the sheet says so in the editor."""
    page = editor(box("a", "text", LISTED))
    expect(at(page, "a").locator(".rich.nolist")).to_have_count(1)


def test_the_words_stand_in_one_to_four_columns(editor):
    """A2: the words stand in 1 to 4 columns; "1 Spalte" stores no column count."""
    client = user()
    page = editor(box("a", "text", LISTED), client=client, words=WORDS)
    pick(page, "a")
    panel(page, "3 Spalten").click()
    assert held(page, client)["a"]["listCols"] == 3
    paragraphs = at(page, "a").locator(".frame.listed .rich p")
    expect(paragraphs).to_have_count(len(WORDS))
    corners = paragraphs.evaluate_all(
        "els => els.map((el) => { const r = el.getBoundingClientRect();"
        " return [Math.round(r.left), Math.round(r.top)]; })"
    )
    assert len({left for left, _ in corners}) == 3
    (left, top), (second_left, second_top) = corners[0], corners[1]
    assert second_left == left and second_top > top
    panel(page, "1 Spalte").click()
    assert "listCols" not in held(page, client)["a"]


def test_a_change_to_the_list_reaches_every_fed_block_in_one_undo_step(editor):
    """A8: a word added to the list reaches every block it feeds, and one undo takes it from all."""
    client = user()
    page = editor(
        box("a", "text", LISTED),
        box("b", "text", {**LISTED, "mix": 7}, z=2),
        box("c", "text", {**LISTED, "holes": "one", "holeSeed": 7}, z=3),
        # Seven rows of 11.5 mm: a Lineatur does not grow when the list grows, it warns.
        box("k", "ruling", KNICK, z=4, w=180, h=81),
        client=client,
        words=WORDS,
    )

    def fed():
        return [
            at(page, "a").locator(".frame.listed .rich p"),
            at(page, "b").locator(".mix"),
            at(page, "c").locator(".rich.holes p"),
            at(page, "k").locator(".listed .row"),
        ]

    for block in fed():
        expect(block).to_have_count(len(WORDS))
    list_tab(page)
    field(page).press("Control+End")
    field(page).press_sequentially("\nIgel")
    for block in fed():
        expect(block).to_have_count(len(WORDS) + 1)
    assert doc(page, client)["words"] == [*WORDS, "Igel"]
    undo(page)
    for block in fed():
        expect(block).to_have_count(len(WORDS))
    assert doc(page, client)["words"] == WORDS
    redo(page)
    for block in fed():
        expect(block).to_have_count(len(WORDS) + 1)


def test_undo_and_redo_walk_every_new_control(editor):
    """A9: link, columns, Lückenwörter, a mode, Neu wählen and Eigener Text each undo and redo."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client, words=WORDS)
    pick(page, "a")
    choice = page.get_by_label(CHOICE)
    actions = [
        lambda: choice.select_option(label="Text aus Lernwörtern"),
        lambda: panel(page, "2 Spalten").click(),
        lambda: panel(page, "Lückenwörter").click(),
        lambda: panel(page, "Jeder zweite").click(),
        # Neu wählen shows in Ein Buchstabe alone (#428).
        lambda: panel(page, "Ein Buchstabe").click(),
        lambda: panel(page, "Neu wählen").click(),
        lambda: choice.select_option(label="Eigener Text"),
    ]
    states = [held(page, client)["a"]]
    for act in actions:
        step(page, act)
        states.append(held(page, client)["a"])
    assert all(after != before for before, after in pairwise(states))
    for want in states[-2::-1]:
        step(page, lambda: undo(page))
        assert held(page, client)["a"] == want
    for want in states[1:]:
        step(page, lambda: redo(page))
        assert held(page, client)["a"] == want


def test_a_text_in_a_group_takes_the_list(editor):
    """A11: two texts in one group both take the list in one choice."""
    client = user()
    page = editor(
        box("a", "text", TEXT, group=["g"]),
        box("b", "text", TEXT, z=2, group=["g"]),
        client=client,
        words=WORDS,
    )
    at(page, "a").click()
    page.keyboard.press("Control+a")
    expect(page.locator(".block.sel")).to_have_count(2)
    page.get_by_label(CHOICE).select_option(label="Text aus Lernwörtern")
    for name in ("a", "b"):
        expect(at(page, name).locator(".frame.listed .rich p")).to_have_count(len(WORDS))
        assert held(page, client)[name]["list"] is True


@pytest.mark.parametrize(
    "kind, props",
    [
        pytest.param("shape", LINE, id="line"),
        pytest.param("table", TABLE, id="table"),
        pytest.param("ruling", RULING, id="ruling"),
    ],
)
def test_a_block_that_holds_no_text_shows_no_choice(editor, kind, props):
    """A11: a line, a table or a Lineatur has no choice of a text from the list."""
    page = editor(box("x", kind, props))
    pick(page, "x")
    expect(page.locator(".panel h2").first).to_be_visible()
    expect(page.get_by_label(CHOICE)).to_have_count(0)


@pytest.mark.parametrize("how", ["dblclick", "enter", "typing"])
def test_a_linked_text_opens_no_field(editor, how):
    """I1: a linked text opens no field by a double click, by Enter or by a typed letter."""
    client = user()
    page = editor(box("a", "text", LISTED), client=client, words=WORDS)
    if how == "dblclick":
        at(page, "a").dblclick()
    else:
        pick(page, "a")
        if how == "enter":
            page.keyboard.press("Enter")
        else:
            page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_count(0)
    stored = doc(page, client)
    assert stored["pages"][0]["blocks"][0]["props"]["text"] == "Hallo"
    assert stored["words"] == WORDS


def test_lernwoerter_bearbeiten_leads_to_the_list(editor):
    """I1: "Lernwörter bearbeiten" opens the list in its tab, with the words in it."""
    client = user()
    page = editor(box("a", "text", LISTED), client=client, words=WORDS)
    pick(page, "a")
    panel(page, "Lernwörter bearbeiten").click()
    expect(field(page)).to_have_value("\n".join(WORDS))


def test_a_linked_block_grows_to_hold_the_list(editor):
    """I3: a text linked, and then a word added to its list, each make the block taller."""
    client = user()
    page = editor(box("a", "text", TEXT, h=10), client=client, words=WORDS)
    pick(page, "a")
    assert heights(page, client)["a"] == 10
    page.get_by_label(CHOICE).select_option(label="Text aus Lernwörtern")
    grown = heights(page, client)["a"]
    assert grown > 10
    list_tab(page)
    field(page).press("Control+End")
    field(page).press_sequentially("\nIgel")
    assert heights(page, client)["a"] > grown


def test_words_past_the_stored_height_draw_whole(editor, browser, server):
    """I3: a linked text stored 5 mm high still draws its last word inside its frame, on the
    editor and on the print."""
    page = editor(box("a", "text", LISTED, h=5), words=WORDS)
    paper = printed(browser, server, sheet_id(page))
    for scope in (at(page, "a"), paper.locator(".block").first):
        last = scope.locator(".frame.listed .rich p").last
        expect(last).to_be_visible()
        frame = scope.locator(".frame.listed").bounding_box()
        block = scope.bounding_box()
        word = last.bounding_box()
        assert frame["height"] > block["height"] + 1
        assert word["y"] + word["height"] <= frame["y"] + frame["height"] + 1
    paper.context.close()


def test_a_measured_block_still_draws_its_words_whole_after_an_undo(editor):
    """I3: a linked text the grow effect measured still draws its words whole after an undo."""
    client = user()
    page = editor(
        box("a", "text", LISTED, h=5),
        box("b", "text", TEXT, y=150),
        client=client,
        words=WORDS,
    )
    pick(page, "b")
    page.keyboard.press("Control+b")
    assert heights(page, client)["a"] > 5
    undo(page)
    assert heights(page, client)["a"] == 5
    scope = at(page, "a")
    last = scope.locator(".frame.listed .rich p").last
    expect(last).to_be_visible()
    frame = scope.locator(".frame.listed").bounding_box()
    block = scope.bounding_box()
    rich = scope.locator(".frame.listed .rich").bounding_box()
    word = last.bounding_box()
    bottom = word["y"] + word["height"]
    assert frame["height"] > block["height"] + 1
    assert bottom <= frame["y"] + frame["height"] + 1
    assert bottom <= rich["y"] + rich["height"] + 1


def test_a_switch_is_on_only_when_all_have_it(editor):
    """I5: Lückenwörter is on only when every picked text has it; the choice is "own" otherwise."""
    client = user()
    # Apart, so that a linked text grown to its words does not lie under the next block.
    page = editor(
        *apart(
            box("a", "text", {**LISTED, "holes": "one", "holeSeed": 7}),
            box("b", "text", LISTED, z=2),
            box("c", "text", TEXT, z=3),
        ),
        client=client,
        words=WORDS,
    )
    pick(page, "a", "b")
    expect(panel(page, "Lückenwörter")).to_have_attribute("aria-pressed", "false")
    unpick(page)
    pick(page, "a", "c")
    expect(page.get_by_label(CHOICE)).to_have_value("own")
