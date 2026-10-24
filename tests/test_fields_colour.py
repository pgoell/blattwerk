"""Farbe while typing: the colour beside a word, and a text whose words already have a look.

The field helpers live in test_fields.py."""

import pytest
from playwright.sync_api import expect
from test_fields import (
    WORDS,
    colour,
)
from ui import (
    FIELD,
    RECT,
    TEXT,
    at,
    box,
    caret,
    pick,
    saved,
    user,
)

# Asked: a colour beside a word


def test_a_colour_beside_a_word_is_for_what_is_typed_next(editor):
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    caret(page, "du", 2)
    colour(page, "#00ff00")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type(" da")
    expect(page.locator(FIELD)).to_have_text("Hallo du da")
    (a,) = saved(page, client)
    # The block and its words keep their colours.
    assert a["props"]["color"] == "#0000ff"
    assert a["props"]["rich"] == [
        {
            "runs": [
                {"text": "Hallo ", "color": "#ff0000"},
                {"text": "du"},
                {"text": " da", "color": "#00ff00"},
            ]
        }
    ]


# Asked: several texts, bold through their words


@pytest.mark.parametrize(
    "name, label, key",
    [("bold", "Fett", "b"), ("italic", "Kursiv", "i"), ("underline", "Unterstrichen", "u")],
)
def test_a_text_whose_words_all_have_a_look_counts_as_having_it(editor, name, label, key):
    client = user()
    words = [{"runs": [{"text": "Hallo ", name: True}, {"text": "du", name: True}]}]
    page = editor(
        box("a", "text", {**TEXT, "text": "Hallo du", "rich": words}),
        box("b", "text", {**TEXT, name: True}, z=2),
        client=client,
    )
    pick(page, "a", "b")
    button = page.locator(".panel").get_by_label(label, exact=True)
    expect(button).to_have_attribute("aria-pressed", "true")
    page.keyboard.press(f"Control+{key}")
    expect(button).to_have_attribute("aria-pressed", "false")
    for block in saved(page, client):
        assert not block["props"].get(name)
        assert name not in str(block["props"].get("rich"))


# Implied: "Farbe" shows the colour, and one undo


def test_farbe_shows_the_colour_for_what_is_typed_next_and_one_undo_takes_it_away(editor):
    page = editor(box("a", "text", WORDS))
    caret(page, "du", 2)
    expect(colour(page, "#00ff00")).to_have_value("#00ff00")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type(" da so")
    coloured = page.locator(f"{FIELD} span[data-color]")
    expect(coloured).to_have_text(["Hallo ", " da so"])
    page.keyboard.press("Control+z")
    expect(page.locator(FIELD)).to_have_text("Hallo du")
    expect(coloured).to_have_text(["Hallo "])
    expect(at(page, "a").locator(".frame")).to_have_css("color", "rgb(0, 0, 255)")


# Issue #308: a press in the panel right after the caret moved


def test_a_press_in_the_panel_reads_a_caret_that_has_just_moved(editor):
    page = editor(box("a", "text", WORDS))
    caret(page, "du", 1)
    control = page.locator(".panel").get_by_label("Farbe", exact=True)
    # The browser tells of a caret's move in a later task. Move and press in one task: the press
    # comes first, as it may in a busy browser.
    control.evaluate(
        """(el) => {
            getSelection().modify("move", "forward", "character");
            el.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
            el.focus();
        }"""
    )
    colour(page, "#00ff00")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type(" da so")
    expect(page.locator(f"{FIELD} span[data-color]")).to_have_text(["Hallo ", " da so"])


# Review: a text with no words keeps the colour as its own


def test_a_colour_in_an_empty_text_outlasts_the_field(editor):
    client = user()
    empty = box("a", "text", {**TEXT, "text": ""})
    page = editor(empty, box("b", "shape", RECT, z=2), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    colour(page, "#00ff00")
    page.keyboard.press("Escape")
    pick(page, "b")
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("x")
    assert saved(page, client)[0]["props"]["color"] == "#00ff00"
