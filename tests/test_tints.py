"""Silbenfarbe: the switch in the format panel, two colours turn by turn, the greys, the setting
that runs the turn on, and the colours with bows, hand fixes and a hand colour.

The docstrings name the lines of the checklist for the feature. The words whose own split the
tests name are ones the patterns split as a child speaks them: Fens-ter, Was-ser, A-bend.
"""

import io
import re
from contextlib import suppress

import pytest
import ui
from PIL import Image
from playwright.sync_api import TimeoutError, expect
from test_lock import fest, undo
from test_painter import held, paint
from ui import (
    FIELD,
    LINE,
    RECT,
    TABLE,
    TEXT,
    TINTS,
    at,
    box,
    caret,
    expect_picked,
    pick,
    saved,
    syls,
    tints,
    user,
)

BLUE, RED = "#1a56db", "#e02424"
PAIR = [BLUE, RED]
GREYS = ["#000000", "#707070"]
FIRST, SECOND = "#2f9e44", "#f08c00"
GREEN, ORANGE = "#2f9e44", "#f08c00"
WORDS = {**TEXT, "text": "Fenster Maus"}
# A text with its bows on and "Maus" split by hand.
MENDED = {**TEXT, "text": "Maus", "syllables": True, "breaks": {"maus": [2]}}
CELLS = {**TABLE, "cells": [["Fenster", "Wasser"], ["3", "7"]]}
# The kinds that hold words, each with "Fenster" and "Wasser" in it.
WORDY = {
    "text": [box("a", "text", {**TEXT, "text": "Fenster Wasser"})],
    "shape": [box("a", "shape", {**RECT, "text": "Fenster Wasser"})],
    "table": [box("a", "table", CELLS)],
    "group": [
        box("a", "text", {**TEXT, "text": "Fenster"}, group=["g"]),
        box("b", "shape", {**RECT, "text": "Wasser"}, z=2, group=["g"]),
        box("c", "shape", LINE, z=3, group=["g"]),
    ],
}
GARBAGE = ["red", ["#1a56db"], ["#1a56db", "}*{display:none}"], [1, 2], {"0": "#000000"}, True]

# The stored colour of a stretch of text, and the colour a pixel shows, from the page's own text.
TINTED = f"""([names, want]) => {{
    const found = names.flatMap((name) => {{
        const block = document.querySelector(`.block[data-id="${{name}}"]`);
        return block ? ({TINTS})(block) : [];
    }});
    return JSON.stringify(found) === JSON.stringify(want);
}}"""
SPANS = """(block) => {
    const found = [];
    for (const [name, marked] of CSS.highlights)
        if (name.startsWith("tint-"))
            for (const range of marked)
                if (block.contains(range.startContainer) && !range.collapsed) found.push(range);
    found.sort((a, b) => a.compareBoundaryPoints(Range.START_TO_START, b));
    return found.map((range) => {
        const box = range.getBoundingClientRect();
        return [box.left, box.right];
    });
}"""
NAMES = "[...CSS.highlights.keys()].filter((name) => name.startsWith('tint-')).sort()"
# Counts each rule for a colour that comes or goes from now on.
RULES = """() => {
    window.rules = 0;
    const own = [...document.head.querySelectorAll("style")].find((el) =>
        el.textContent.startsWith("::highlight(tint-"));
    new MutationObserver((all) => (window.rules += all.length)).observe(own, { childList: true });
}"""
COUNT = """() => {
    let n = 0;
    for (const [name, marked] of CSS.highlights)
        if (name.startsWith("tint-")) n += marked.size;
    return n;
}"""
IN_PAPER = """() => {
    const paper = document.querySelector(".sheets li .paper");
    if (!paper) return -1;
    let n = 0;
    for (const [name, marked] of CSS.highlights)
        if (name.startsWith("tint-"))
            for (const range of marked) if (paper.contains(range.startContainer)) n++;
    return n;
}"""


def tint_switch(page):
    return page.locator(".panel").get_by_role("button", name="Silbenfarbe", exact=True)


def greys(page):
    return page.locator(".panel").get_by_role("button", name="Schwarz/Grau", exact=True)


def across(page):
    return page.locator(".panel").get_by_role("button", name="Über Wortgrenzen", exact=True)


def expect_tint_switch(page, on):
    """Waits until the switch says its state, to the eye and to a screen reader."""
    expect(tint_switch(page)).to_have_attribute("aria-pressed", "true" if on else "false")
    expect(tint_switch(page)).to_have_class("on" if on else "")


def set_colour(page, label, value):
    """Picks a colour in a field of the panel as the mouse does: a press, the focus, the pick.

    Headless Chromium opens no colour picker. The `input` comes while a picker is dragged and
    the `change` when it closes.
    """
    control = page.locator(".panel").get_by_label(label, exact=True)
    control.dispatch_event("pointerdown")
    control.focus()
    # React hears only of a value set as the browser sets it.
    control.evaluate(
        """(el, value) => {
            const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
            for (const step of ["#123456", value]) {
                own.set.call(el, step);
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
        value,
    )


def luminance(colour):
    """The relative luminance of a colour, as WCAG 2 has it."""
    lit = []
    for i in (1, 3, 5):
        channel = int(colour[i : i + 2], 16) / 255
        lit.append(channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lit[0] + 0.7152 * lit[1] + 0.0722 * lit[2]


def contrast(one, other):
    """The contrast ratio of two colours, from 1 to 21."""
    high, low = sorted([luminance(one), luminance(other)], reverse=True)
    return (high + 0.05) / (low + 0.05)


def near(pixels, colour):
    """The pixels whose every channel lies within 40 of the colour's."""
    target = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    return sum(
        all(abs(p - t) <= 40 for p, t in zip(pixel, target, strict=True)) for pixel in pixels
    )


class tinted:
    """The colours of the stretches in the blocks, one block after the other: waits as `expect`.

    The colours are drawn a frame after the text changes, in the open field and the open cell too.
    """

    def __init__(self, page, *names):
        self.page, self.names = page, names

    def to_have_text(self, want):
        # A wait that runs out leaves the telling to the comparison below.
        with suppress(TimeoutError):
            self.page.wait_for_function(TINTED, arg=[self.names, want], timeout=5000)
        assert [tint for name in self.names for tint in tints(self.page, name)] == want

    def to_have_count(self, count):
        assert not count
        self.to_have_text([])


def word(page, name):
    """The button of a word in the panel's list, by the word as it is split."""
    return page.locator(".panel .words").get_by_role("button", name=name, exact=True)


def gap(page, name):
    """The button between two letters of the open word: "Ma|us"."""
    return page.locator(".panel .gaps").get_by_role("button", name=name, exact=True)


def redo(page):
    return page.get_by_label("Wiederholen", exact=True)


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


@pytest.mark.parametrize("kind", ["line", "image", "symbol", "maths", "ruling"])
def test_a_block_that_holds_no_words_shows_no_colour_switch(editor, kind):
    """A11: a line, a picture, a symbol, maths and a Lineatur have no colours to switch on."""
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


def test_tab_reaches_the_colour_switch_and_its_settings_and_space_and_enter_press_them(editor):
    """I7: by keyboard alone, the switch and its settings, which the switch shows when on."""
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    pick(page, "a")
    page.get_by_label("Zeilenabstand").focus()
    page.keyboard.press("Tab")
    expect(
        page.locator(".panel").get_by_role("button", name="Silbenbögen", exact=True)
    ).to_be_focused()
    page.keyboard.press("Tab")
    expect(tint_switch(page)).to_be_focused()
    expect_tint_switch(page, False)
    page.keyboard.press("Space")
    expect_tint_switch(page, True)
    tinted(page, "a").to_have_text([("Fens", BLUE), ("ter", RED), ("Maus", BLUE)])
    # WebKit's Tab passes a colour field, the block's own "Farbe" too.
    if ui.BROWSER != "webkit":
        page.keyboard.press("Tab")
        expect(page.locator(".panel").get_by_label("Erste Silbe", exact=True)).to_be_focused()
        page.keyboard.press("Tab")
        expect(page.locator(".panel").get_by_label("Zweite Silbe", exact=True)).to_be_focused()
    page.keyboard.press("Tab")
    expect(greys(page)).to_be_focused()
    page.keyboard.press("Space")
    expect(greys(page)).to_have_attribute("aria-pressed", "true")
    tinted(page, "a").to_have_text([("Fens", GREYS[0]), ("ter", GREYS[1]), ("Maus", GREYS[0])])
    page.keyboard.press("Tab")
    expect(across(page)).to_be_focused()
    page.keyboard.press("Enter")
    expect(across(page)).to_have_attribute("aria-pressed", "true")
    assert held(page, client)["a"]["tintsAcross"] is True
    tint_switch(page).focus()
    page.keyboard.press("Enter")
    expect_tint_switch(page, False)
    tinted(page, "a").to_have_count(0)


def test_a_tables_open_cell_shows_its_colours_and_they_follow_each_letter_typed(editor):
    """I2: the colours show in the cell being written in, as in a text's open field."""
    page = editor(box("a", "table", {**CELLS, "tints": PAIR}))
    tinted(page, "a").to_have_text([("Fens", BLUE), ("ter", RED), ("Was", BLUE), ("ser", RED)])
    at(page, "a").locator("[data-cell='0']").dblclick()
    expect(at(page, "a").locator("textarea")).to_be_focused()
    # A browser colours nothing inside a field: the cell's own text shows, the field's does not.
    expect(at(page, "a").locator("p.open")).to_have_css("visibility", "visible")
    expect(at(page, "a").locator("textarea")).to_have_css("color", "rgba(0, 0, 0, 0)")
    page.keyboard.press("End")
    page.keyboard.type(" Ta")
    tinted(page, "a").to_have_text(
        [("Fens", BLUE), ("ter", RED), ("Ta", BLUE), ("Was", BLUE), ("ser", RED)]
    )
    page.keyboard.type("sche")
    tinted(page, "a").to_have_text(
        [("Fens", BLUE), ("ter", RED), ("Ta", BLUE), ("sche", RED), ("Was", BLUE), ("ser", RED)]
    )
    # The field still takes the mouse: a click in its middle is a click in the field.
    area = at(page, "a").locator("textarea")
    area.click()
    expect(area).to_be_focused()
    page.keyboard.press("Home")
    page.keyboard.type("O ")
    expect(area).to_have_value("O Fenster Tasche")


@pytest.mark.parametrize("kind", ["text", "shape"])
def test_the_colours_follow_each_letter_typed_and_the_switch_leaves_the_caret(editor, kind):
    """I2: colours in the open field; the switch works with the field open and the caret stays."""
    client = user()
    props = {**TEXT, "text": "Fenster"} if kind == "text" else {**RECT, "text": "Fenster"}
    page = editor(box("a", kind, props), client=client)
    caret(page, "Fenster", 4)
    tinted(page, "a").to_have_count(0)
    tint_switch(page).click()
    expect_tint_switch(page, True)
    tinted(page, "a").to_have_text([("Fens", BLUE), ("ter", RED)])
    # The field is still written in, at the place the caret had.
    expect(page.locator(FIELD)).to_be_focused()
    # A letter typed makes no rule anew: the colours that stay keep theirs.
    page.evaluate(RULES)
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Fensxter")
    tinted(page, "a").to_have_text([("Fensx", BLUE), ("ter", RED)])
    assert page.evaluate("window.rules") == 0
    page.keyboard.press("Backspace")
    page.keyboard.press("End")
    for typed, shown in (
        (" ", [("Fens", BLUE), ("ter", RED)]),
        ("Was", [("Fens", BLUE), ("ter", RED), ("Was", BLUE)]),
        ("ser", [("Fens", BLUE), ("ter", RED), ("Was", BLUE), ("ser", RED)]),
    ):
        page.keyboard.type(typed)
        tinted(page, "a").to_have_text(shown)
    # The word the caret stands at is open with no click; a break set there shows in the field.
    expect(word(page, "Was·ser")).to_have_attribute("aria-pressed", "true")
    gap(page, "Wa|sser").click()
    tinted(page, "a").to_have_text(
        [("Fens", BLUE), ("ter", RED), ("Wa", BLUE), ("s", RED), ("ser", BLUE)]
    )
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("n")
    expect(page.locator(FIELD)).to_have_text("Fenster Wassern")
    page.keyboard.press("Backspace")
    # The caret in another word opens that one.
    page.keyboard.press("Home")
    expect(word(page, "Fens·ter")).to_have_attribute("aria-pressed", "true")
    expect(gap(page, "Fens|ter")).to_have_attribute("aria-pressed", "true")
    tint_switch(page).click()
    expect_tint_switch(page, False)
    tinted(page, "a").to_have_count(0)
    expect(page.locator(FIELD)).to_be_focused()
    assert held(page, client)["a"]["breaks"] == {"wasser": [2, 3]}


def test_the_brush_carries_the_colours_and_their_setting_and_leaves_the_words_split_by_hand(
    editor,
):
    """I3: the format painter carries the colours and the setting, not the hand fixes."""
    client = user()
    coloured = {**MENDED, "tints": PAIR, "tintsAcross": True}
    blocks = [
        box("a", "text", coloured),
        box("b", "text", {**TEXT, "text": "Maus"}, z=2),
        box("t", "table", CELLS, z=3),
        box("c", "text", TEXT, z=4),
    ]
    page = editor(*blocks, client=client)
    paint(page, "a", "b")
    tinted(page, "b").to_have_text([("Maus", BLUE)])
    now = held(page, client)
    assert (now["b"]["tints"], now["b"]["tintsAcross"]) == (PAIR, True)
    assert "breaks" not in now["b"]
    paint(page, "a", "t")
    tinted(page, "t").to_have_text([("Fens", BLUE), ("ter", RED), ("Was", BLUE), ("ser", RED)])
    now = held(page, client)
    assert (now["t"]["tints"], now["t"]["tintsAcross"]) == (PAIR, True)
    assert "breaks" not in now["t"]
    # A block without colours takes them away, as one not bold takes the bold; the fix stays.
    paint(page, "c", "a")
    tinted(page, "a").to_have_count(0)
    now = held(page, client)["a"]
    assert "tints" not in now and "tintsAcross" not in now
    assert "syllables" not in now and now["breaks"] == {"maus": [2]}


def test_a_copy_and_a_duplicate_keep_the_colours_and_the_words_split_by_hand(editor):
    """I4: copy and paste, and duplicate, of a block keep the colours and its hand fixes."""
    client = user()
    page = editor(box("a", "text", {**MENDED, "tints": PAIR}), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    made = page.eval_on_selector_all(".block[data-id]", "els => els.map((el) => el.dataset.id)")
    tinted(page, *made).to_have_text([("Ma", BLUE), ("us", RED)] * 3)
    assert list(held(page, client).values()) == [{**MENDED, "tints": PAIR}] * 3


@pytest.mark.parametrize("kind", ["text", "table"])
def test_a_locked_block_takes_the_colours_and_a_word_split_by_hand(editor, kind):
    """I5: as it takes any format; its place, size and text stay."""
    client = user()
    props = {"text": {**TEXT, "text": "Maus"}, "table": {**TABLE, "cells": [["Maus", "7"]]}}[kind]
    block = box("a", kind, props, locked=True)
    page = editor(block, client=client)
    at(page, "a").click()
    expect_picked(page, "a")
    tint_switch(page).click()
    tinted(page, "a").to_have_text([("Maus", BLUE)])
    word(page, "Maus").click()
    gap(page, "Ma|us").click()
    tinted(page, "a").to_have_text([("Ma", BLUE), ("us", RED)])
    assert saved(page, client) == [
        {**block, "props": {**props, "tints": PAIR, "breaks": {"maus": [2]}}}
    ]


def test_bold_italic_underline_colour_and_a_list_keep_their_look_in_a_coloured_text(editor):
    """I6: the runs keep their look, and so does the bullet, under the colours."""
    hand = "#e03131"
    runs = [
        {"text": "Rote ", "color": hand},
        {"text": "Ba", "bold": True},
        {"text": "nane ", "italic": True},
        {"text": "Esel", "underline": True},
    ]
    listed = [{"runs": runs, "list": "bullet"}, {"runs": [{"text": "Oma"}]}]
    text = "Rote Banane Esel\nOma"
    props = {**TEXT, "text": text, "rich": listed, "color": GREEN, "tints": PAIR}
    page = editor(box("a", "text", props))
    # The colours skip the letters of the hand colour; "Banane" is coloured whole.
    tinted(page, "a").to_have_text(
        [
            ("Ba", BLUE),
            ("na", RED),
            ("ne", BLUE),
            ("E", BLUE),
            ("sel", RED),
            ("O", BLUE),
            ("ma", RED),
        ]
    )
    spans = at(page, "a").locator(".rich p span")
    expect(spans.nth(0)).to_have_css("color", "rgb(224, 49, 49)")
    expect(spans.nth(1)).to_have_css("font-weight", "700")
    expect(spans.nth(2)).to_have_css("font-style", "italic")
    expect(spans.nth(3)).to_have_css("text-decoration-line", "underline")
    item = at(page, "a").locator(".rich p").first
    assert item.evaluate("el => getComputedStyle(el, '::before').content") == '"•"'
    assert item.evaluate("el => getComputedStyle(el, '::before').color") == "rgb(47, 158, 68)"


def test_the_sheet_lists_thumbnail_shows_the_colours(editor, server):
    """I8: the thumbnail on the list draws the colours too: one range per syllable."""
    page = editor(box("a", "text", {**WORDS, "size": 40, "tints": PAIR}, w=180, h=40))
    tints(page, "a")
    page.goto(server)
    expect(page.locator(".sheets li .paper")).to_be_visible()
    with suppress(TimeoutError):
        page.wait_for_function(f"() => ({IN_PAPER})() === 3", timeout=5000)
    assert page.evaluate(f"({IN_PAPER})()") == 3


def test_a_word_that_every_object_knows_takes_its_colours(editor):
    """ "constructor" names a member of every object: it takes its colours like any word."""
    text = {**TEXT, "text": "constructor toString Maus", "tints": PAIR}
    page = editor(box("a", "text", text))
    faults = []
    page.on("pageerror", lambda fault: faults.append(fault))
    expect(at(page, "a")).to_be_visible()
    assert "".join(text for text, _ in tints(page, "a")) == "constructortoStringMaus"
    assert not faults


def test_a_block_that_goes_takes_its_colours_along(editor):
    """Extra: a block deleted takes its colour ranges with it: none stay on the page."""
    page = editor(
        box("a", "text", {**WORDS, "tints": PAIR}),
        box("b", "text", {**TEXT, "text": "Wasser", "tints": PAIR}, z=2),
    )
    pick(page, "b")
    page.keyboard.press("Delete")
    expect(at(page, "b")).to_have_count(0)
    # The three of "Fenster Maus" and no more.
    with suppress(TimeoutError):
        page.wait_for_function(f"() => ({COUNT})() === 3", timeout=5000)
    assert page.evaluate(f"({COUNT})()") == 3
