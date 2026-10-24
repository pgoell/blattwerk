"""Syllable colours run across a word, a hand-set break, and a black and white print."""

import io
import re

import pytest
from PIL import Image
from playwright.sync_api import expect
from test_painter import held
from test_tints import (
    BLUE,
    FIRST,
    GREEN,
    GREYS,
    NAMES,
    ORANGE,
    PAIR,
    RED,
    SECOND,
    SPANS,
    WORDS,
    across,
    contrast,
    expect_tint_switch,
    gap,
    greys,
    near,
    set_colour,
    tint_switch,
    tinted,
    word,
)
from ui import (
    TABLE,
    TEXT,
    at,
    box,
    pick,
    syls,
    tints,
    user,
)


def test_one_click_colours_the_syllables_and_one_more_takes_the_colours_away(editor):
    """A1: the switch stands right after Silbenbögen; one click on, one off; off is as it was."""
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    pick(page, "a")
    expect_tint_switch(page, False)
    assert tint_switch(page).evaluate("(el) => el.previousElementSibling.textContent") == (
        "Silbenbögen"
    )
    tinted(page, "a").to_have_count(0)
    tint_switch(page).click()
    expect_tint_switch(page, True)
    tinted(page, "a").to_have_text([("Fens", BLUE), ("ter", RED), ("Maus", BLUE)])
    assert held(page, client)["a"]["tints"] == PAIR
    tint_switch(page).click()
    expect_tint_switch(page, False)
    tinted(page, "a").to_have_count(0)
    assert held(page, client)["a"] == WORDS


def test_each_word_starts_with_the_first_colour_and_a_number_has_none(editor):
    """A2: each word starts with the first colour; a number, a comma, a full stop and a space
    have none."""
    page = editor(box("a", "text", {**TEXT, "text": "Oma hat 3 Äpfel, Opa nicht.", "tints": PAIR}))
    found = tints(page, "a")
    assert found == [
        ("O", BLUE),
        ("ma", RED),
        ("hat", BLUE),
        ("Äp", BLUE),
        ("fel", RED),
        ("O", BLUE),
        ("pa", RED),
        ("nicht", BLUE),
    ]
    assert not [text for text, _ in found if re.search(r"[0-9,. ]", text)]


def test_the_colours_run_on_across_word_borders_when_asked(editor):
    """A3: each word starts anew; the setting runs the turn on, over a paragraph too; a table's
    cell starts anew."""
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": "Oma hat Opa", "tints": PAIR}), client=client)
    pick(page, "a")
    tinted(page, "a").to_have_text(
        [("O", BLUE), ("ma", RED), ("hat", BLUE), ("O", BLUE), ("pa", RED)]
    )
    across(page).click()
    expect(across(page)).to_have_attribute("aria-pressed", "true")
    tinted(page, "a").to_have_text(
        [("O", BLUE), ("ma", RED), ("hat", BLUE), ("O", RED), ("pa", BLUE)]
    )
    assert held(page, client)["a"]["tintsAcross"] is True
    across(page).click()
    expect(across(page)).to_have_attribute("aria-pressed", "false")
    tinted(page, "a").to_have_text(
        [("O", BLUE), ("ma", RED), ("hat", BLUE), ("O", BLUE), ("pa", RED)]
    )
    assert "tintsAcross" not in held(page, client)["a"]

    paragraphs = editor(
        box("a", "text", {**TEXT, "text": "Oma\nhat", "tints": PAIR, "tintsAcross": True})
    )
    tinted(paragraphs, "a").to_have_text([("O", BLUE), ("ma", RED), ("hat", BLUE)])

    cells = editor(
        box(
            "a",
            "table",
            {**TABLE, "cells": [["Oma", "Opa"], ["3", "7"]], "tints": PAIR, "tintsAcross": True},
        )
    )
    tinted(cells, "a").to_have_text([("O", BLUE), ("ma", RED), ("O", BLUE), ("pa", RED)])


def test_two_colour_fields_change_the_pair(editor):
    """A4: the two colour fields set the pair; the colours and the stored pair follow."""
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    pick(page, "a")
    tint_switch(page).click()
    expect_tint_switch(page, True)
    set_colour(page, "Erste Silbe", FIRST)
    set_colour(page, "Zweite Silbe", SECOND)
    tinted(page, "a").to_have_text([("Fens", FIRST), ("ter", SECOND), ("Maus", FIRST)])
    assert held(page, client)["a"]["tints"] == [FIRST, SECOND]
    # A colour the pair had, or a field passed on its way, leaves no highlight and no rule behind.
    assert page.evaluate(NAMES) == sorted(f"tint-{colour[1:]}" for colour in (FIRST, SECOND))
    assert page.evaluate("document.head.textContent.split('::highlight(tint-').length - 1") == 2


def test_a_soft_hyphen_in_a_word_does_not_start_the_colours_anew(editor):
    """A2: a word copied out of Word with a soft hyphen in it is one word to the reader."""
    page = editor(box("a", "text", {**TEXT, "text": "Fens­ter Maus", "tints": PAIR}))
    assert tints(page, "a") == [("Fens", BLUE), ("ter", RED), ("Maus", BLUE)]


def test_black_and_grey_stay_readable_on_a_black_and_white_print(editor):
    """A5: black and grey, at least 4.5 to 1 for the grey on white and 3 to 1 against the black."""
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    pick(page, "a")
    tint_switch(page).click()
    greys(page).click()
    expect(greys(page)).to_have_attribute("aria-pressed", "true")
    found = tints(page, "a")
    assert found == [("Fens", GREYS[0]), ("ter", GREYS[1]), ("Maus", GREYS[0])]
    assert held(page, client)["a"]["tints"] == GREYS
    black, grey = found[0][1], found[1][1]
    assert contrast(grey, "#ffffff") >= 4.5
    assert contrast(grey, black) >= 3
    greys(page).click()
    expect(greys(page)).to_have_attribute("aria-pressed", "false")
    tinted(page, "a").to_have_text([("Fens", BLUE), ("ter", RED), ("Maus", BLUE)])
    assert held(page, client)["a"]["tints"] == PAIR


def test_a_break_set_by_hand_moves_the_colour_and_the_bow(editor):
    """A6: a word with colours and no bows still opens; a break set there moves the colour, and
    the bows follow it when they go on."""
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": "Maus", "tints": PAIR}), client=client)
    pick(page, "a")
    expect(page.locator(".panel .words")).to_be_visible()
    word(page, "Maus").click()
    gap(page, "Ma|us").click()
    tinted(page, "a").to_have_text([("Ma", BLUE), ("us", RED)])
    assert held(page, client)["a"]["breaks"] == {"maus": [2]}
    page.locator(".panel").get_by_role("button", name="Silbenbögen", exact=True).click()
    assert syls(page, "a") == ["Ma", "us"]


def test_with_both_switches_on_each_bow_spans_the_letters_of_one_colour_and_takes_it(editor):
    """A7: a bow and its colour sit on the letters of one colour, and the same is true of the
    stroke."""
    page = editor(
        box("a", "text", {**TEXT, "text": "Fenster Abend", "syllables": True, "tints": PAIR})
    )
    texts = [text for text, _ in tints(page, "a")]
    assert texts == ["Fens", "ter", "A", "bend"]
    assert syls(page, "a") == texts
    strokes = (
        at(page, "a")
        .locator(".syl")
        .evaluate_all("els => els.map((el) => getComputedStyle(el).stroke)")
    )
    assert strokes == [
        "rgb(26, 86, 219)",
        "rgb(224, 36, 36)",
        "rgb(26, 86, 219)",
        "rgb(224, 36, 36)",
    ]
    spans = at(page, "a").evaluate(SPANS)
    bows = (
        at(page, "a")
        .locator(".syl")
        .evaluate_all(
            """els => els.map((el) => {
                const r = el.getBoundingClientRect();
                return [r.left, r.right];
            })"""
        )
    )
    assert len(spans) == len(bows) == 4
    for (left, right), (start, end) in zip(bows, spans, strict=True):
        assert left == pytest.approx(start, abs=3)
        assert right == pytest.approx(end, abs=3)


def test_a_colour_set_by_hand_on_a_run_wins_and_the_blocks_colour_loses(editor):
    """A8: a colour set by hand on a run wins; the colour of the block loses to Silbenfarbe."""
    props = {
        **TEXT,
        "text": "Fenster Maus",
        "size": 40,
        "color": GREEN,
        "tints": PAIR,
        "rich": [{"runs": [{"text": "Fens", "color": ORANGE}, {"text": "ter Maus"}]}],
    }
    page = editor(box("a", "text", props, h=40))
    assert tints(page, "a") == [("ter", RED), ("Maus", BLUE)]
    picture = Image.open(io.BytesIO(at(page, "a").screenshot())).convert("RGB")
    raw = picture.tobytes()
    pixels = [raw[i : i + 3] for i in range(0, len(raw), 3)]
    assert near(pixels, ORANGE) > 20
    assert near(pixels, RED) > 20
    assert near(pixels, BLUE) > 20
    assert near(pixels, GREEN) < 10
