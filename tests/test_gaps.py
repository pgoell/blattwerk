"""Lückentext, editing side: gaps of a picked text, their width, the solution words, every n-th
word, undo and redo, and what the field holds of a gap.

The docstrings name the checklist lines. The tests read what is stored and what the field holds,
never how a gap looks.
"""

import pytest
from playwright.sync_api import expect
from test_lock import FRAMES
from test_painter import held
from test_zoom import wheel
from ui import FIELD, RECT, TABLE, TEXT, at, box, caret, pick, user

WORDS = "eins zwei drei vier fünf sechs sieben acht neun zehn"
WORDY = {**TEXT, "text": WORDS}
# Three solution words, so that a Neu mischen moves them: with two, the one order that is not
# the typed one is the only order there is, and a second press moves nothing.
THREE = [
    {
        "runs": [
            {"text": "Hund", "gap": True},
            {"text": " "},
            {"text": "Katze", "gap": True},
            {"text": " "},
            {"text": "Vogel", "gap": True},
        ]
    }
]
TWO = {**TEXT, "text": "Hund Katze Vogel", "rich": THREE}
SHAPE_TWO = {**RECT, "text": "Hund Katze Vogel", "rich": THREE}
GAPPED_TABLE = {**TABLE, "gaps": [[True, True], [True, True]]}
GAPPED = {**TEXT, "rich": [{"runs": [{"text": "Hallo", "gap": True}]}], "gapWidth": 12, "bank": 7}


def panel(page, label):
    return page.locator(".panel").get_by_role("button", name=label, exact=True)


def gapped(rich):
    """The stretches of a stored text that are gaps, in order."""
    return [run["text"] for para in rich for run in para["runs"] if run.get("gap")]


def step(page, action):
    """Does an action that the editor saves, and waits for the save."""
    with page.expect_response(lambda res: res.request.method == "PATCH"):
        action()


def test_lucke_turns_the_picked_words_of_an_open_text_into_a_gap(editor):
    """A1: the picked words of an open text become a gap, shown in the field and saved."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    expect(page.locator(f"{FIELD} .gap")).to_have_count(1)
    assert held(page, client)["a"]["rich"] == [{"runs": [{"text": "Hallo", "gap": True}]}]


def test_lucke_on_a_gap_turns_it_back_into_text(editor):
    """A4: the same button on a gap takes it away; the saved text has no rich form again."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    step(page, lambda: panel(page, "Lücke").click())
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "true")
    step(page, lambda: panel(page, "Lücke").click())
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "false")
    assert "rich" not in held(page, client)["a"]


def test_ctrl_l_makes_no_gap_in_a_block_or_in_an_open_text(editor):
    """A2: Ctrl+L is no shortcut of the gap, neither with the block picked nor in the open text."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Control+l")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+l")
    expect(page.locator(f"{FIELD} .gap")).to_have_count(0)
    page.keyboard.press("Escape")
    assert "rich" not in held(page, client)["a"]
    assert held(page, client)["a"]["text"] == "Hallo"


def test_lucken_gleich_breit_stores_a_width_that_the_field_changes_and_off_removes_it(editor):
    """A3: the width is stored at 30 mm with no gap drawn; a number changes it; off removes it."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    panel(page, "Lücken gleich breit").click()
    expect(panel(page, "Lücken gleich breit")).to_have_attribute("aria-pressed", "true")
    assert held(page, client)["a"]["gapWidth"] == 30
    width = page.locator(".panel").get_by_label("Breite der Lücken", exact=True)
    width.fill("12")
    width.press("Enter")
    assert held(page, client)["a"]["gapWidth"] == 12
    panel(page, "Lücken gleich breit").click()
    expect(panel(page, "Lücken gleich breit")).to_have_attribute("aria-pressed", "false")
    assert "gapWidth" not in held(page, client)["a"]


def test_jedes_n_te_wort_gaps_every_fifth_word_and_every_third_when_n_is_three(editor):
    """A8: words 5 and 10 are gaps; with n at 3, words 3, 6 and 9. The text is unchanged."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    pick(page, "a")
    step(page, lambda: panel(page, "Jedes n-te Wort").click())
    assert gapped(held(page, client)["a"]["rich"]) == ["fünf", "zehn"]
    assert held(page, client)["a"]["text"] == WORDS
    page.get_by_label("n", exact=True).fill("3")
    step(page, lambda: panel(page, "Jedes n-te Wort").click())
    assert gapped(held(page, client)["a"]["rich"]) == ["drei", "sechs", "neun"]
    assert held(page, client)["a"]["text"] == WORDS


def test_each_gap_change_is_one_undo_step_and_redo_brings_it_back(editor):
    """A10: each gap change, width, width typed, switch, shuffle and every n-th word is one step."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    pick(page, "a")
    width = page.locator(".panel").get_by_label("Breite der Lücken", exact=True)
    states = [held(page, client)["a"]]
    # Every third word is a gap: three solution words for Neu mischen to move. A gap over the
    # whole text is one solution word, so it comes last.
    page.get_by_label("n", exact=True).fill("3")
    actions = [
        lambda: panel(page, "Lücke").click(),
        lambda: panel(page, "Lücke").click(),
        lambda: panel(page, "Jedes n-te Wort").click(),
        lambda: panel(page, "Lücken gleich breit").click(),
        lambda: (width.fill("12"), width.press("Enter")),
        lambda: panel(page, "Lösungswörter").click(),
        lambda: panel(page, "Neu mischen").click(),
        lambda: panel(page, "Lücke").click(),
    ]
    for act in actions:
        step(page, act)
        states.append(held(page, client)["a"])
    for want in states[-2::-1]:
        step(page, lambda: page.keyboard.press("Control+z"))
        assert held(page, client)["a"] == want
    for want in states[1:]:
        step(page, lambda: page.keyboard.press("Control+y"))
        assert held(page, client)["a"] == want


@pytest.mark.parametrize("kind", ["text", "table"])
def test_lucke_gaps_each_held_block_as_a_whole_when_no_field_is_open(editor, kind):
    """A13 and I2: with no text open, Lücke gaps each block whole: its text, or its cells."""
    client = user()
    blocks = [box("a", "text", WORDY)] if kind == "text" else [box("t", "table", TABLE)]
    page = editor(*blocks, client=client)
    pick(page, "a" if kind == "text" else "t")
    panel(page, "Lücke").click()
    if kind == "text":
        assert gapped(held(page, client)["a"]["rich"]) == [WORDS]
    else:
        assert held(page, client)["t"]["gaps"] == [[True, True], [True, True]]


def test_lucke_gaps_the_words_of_a_shape_with_text(editor):
    """A13: a shape that holds words gets its gap like a text."""
    client = user()
    page = editor(box("a", "shape", {**RECT, "text": "Hund"}), client=client)
    pick(page, "a")
    panel(page, "Lücke").click()
    assert held(page, client)["a"]["rich"] == [{"runs": [{"text": "Hund", "gap": True}]}]


def test_lucke_in_an_open_table_cell_gaps_only_that_cell(editor):
    """A13: with a cell open, Lücke flags that cell alone; gaps has the shape of cells."""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    pick(page, "t")
    at(page, "t").locator("[data-cell='2']").dblclick()
    panel(page, "Lücke").click()
    assert held(page, client)["t"]["gaps"] == [[False, False], [True, False]]


def test_lucke_on_a_group_of_two_texts_gaps_each(editor):
    """A13: a group of two texts picked whole: each text gets its gap."""
    client = user()
    page = editor(
        box("a", "text", TEXT, group=["g"]),
        box("b", "text", {**TEXT, "text": "Maus"}, z=2, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    page.keyboard.press("Control+a")
    expect(page.locator(".block.sel")).to_have_count(2)
    panel(page, "Lücke").click()
    now = held(page, client)
    assert gapped(now["a"]["rich"]) == ["Hallo"]
    assert gapped(now["b"]["rich"]) == ["Maus"]


def test_a_caret_in_a_word_gaps_that_word(editor):
    """I1: with a caret in a word and no pick, Lücke gaps that word alone."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    caret(page, "fünf", 2)
    panel(page, "Lücke").click()
    expect(page.locator(f"{FIELD} .gap")).to_have_text("fünf")
    assert gapped(held(page, client)["a"]["rich"]) == ["fünf"]


def test_a_letter_typed_after_a_gap_is_no_part_of_it(editor):
    """I3: a letter typed just after the gap stays out of it."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    page.keyboard.press("End")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Hallox")
    assert held(page, client)["a"]["rich"] == [
        {"runs": [{"text": "Hallo", "gap": True}, {"text": "x"}]}
    ]


def test_a_letter_typed_right_before_a_gap_is_no_part_of_it(editor):
    """I3: a letter typed just before the gap stays out of it."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    page.keyboard.press("Home")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("xHallo")
    assert held(page, client)["a"]["rich"] == [
        {"runs": [{"text": "x"}, {"text": "Hallo", "gap": True}]}
    ]


def test_the_lucke_button_shows_pressed_in_a_gap_and_keeps_the_field_focused(editor):
    """I4: pressed while the caret stands in a gap; a press on it keeps the field and its typing."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    # At the very start a gap is no mark of the caret; one step in, the caret is inside it.
    page.keyboard.press("Home")
    page.keyboard.press("ArrowRight")
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "true")
    panel(page, "Lücke").click()
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "false")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Hxallo")


def test_a_shape_with_no_words_takes_no_gap_and_no_step(editor):
    """A13: a shape with no text takes no gap and no every n-th word: its props stay, no step."""
    client = user()
    page = editor(box("s", "shape", RECT), client=client)
    pick(page, "s")
    before = held(page, client)["s"]
    step_free = page.get_by_label("Rückgängig", exact=True)
    expect(step_free).to_be_disabled()
    page.evaluate(FRAMES)
    expect(step_free).to_be_disabled()
    panel(page, "Lücke").click()
    page.evaluate(FRAMES)
    expect(step_free).to_be_disabled()
    panel(page, "Jedes n-te Wort").click()
    page.evaluate(FRAMES)
    expect(step_free).to_be_disabled()
    assert held(page, client)["s"] == before


def test_lucken_gleich_breit_takes_the_same_width_at_any_zoom(editor):
    """A3: the width measured at the default zoom is the width measured zoomed in."""
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "rich": [{"runs": [{"text": "Hallo", "gap": True}]}]}),
        client=client,
    )
    pick(page, "a")
    expect(page.locator(".block.sel .gap")).to_have_count(1)
    panel(page, "Lücken gleich breit").click()
    first = held(page, client)["a"]["gapWidth"]
    step(page, lambda: page.keyboard.press("Control+z"))
    wheel(page, -100)
    wheel(page, -100)
    panel(page, "Lücken gleich breit").click()
    assert held(page, client)["a"]["gapWidth"] == first
