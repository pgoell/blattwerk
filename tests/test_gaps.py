"""Lückentext, editing side: gaps of a picked text, their width, the solution words, every n-th
word, undo and redo, and what the field holds of a gap.

The docstrings name the checklist lines. The tests read what is stored and what the field holds,
never how a gap looks.
"""

import pytest
from playwright.sync_api import expect
from test_lock import fest
from test_painter import held
from ui import FIELD, TABLE, TEXT, box, pick, user

WORDS = "eins zwei drei vier fünf sechs sieben acht neun zehn"
WORDY = {**TEXT, "text": WORDS}


def panel(page, label):
    # "Gleiche Breite" names also the arrangement's button, which is disabled for one block.
    return (
        page.locator(".panel")
        .get_by_role("button", name=label, exact=True)
        .and_(page.locator("button:enabled"))
    )


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


def test_gleiche_breite_stores_a_width_that_the_field_changes_and_off_removes_it(editor):
    """A3: the width is stored at 30 mm with no gap drawn; a number changes it; off removes it."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    panel(page, "Gleiche Breite").click()
    expect(panel(page, "Gleiche Breite")).to_have_attribute("aria-pressed", "true")
    assert held(page, client)["a"]["gapWidth"] == 30
    width = page.locator(".panel").get_by_label("Breite der Lücken", exact=True)
    width.fill("12")
    width.press("Enter")
    assert held(page, client)["a"]["gapWidth"] == 12
    panel(page, "Gleiche Breite").click()
    expect(panel(page, "Gleiche Breite")).to_have_attribute("aria-pressed", "false")
    assert "gapWidth" not in held(page, client)["a"]


def test_losungswörter_stores_a_seed_that_neu_mischen_changes_and_off_removes(editor):
    """A7: the box stores a seed, a new shuffle stores another, and off removes the seed."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    panel(page, "Lösungswörter").click()
    seed = held(page, client)["a"]["bank"]
    assert 1 <= seed <= 2147483647
    panel(page, "Neu mischen").click()
    assert held(page, client)["a"]["bank"] != seed
    panel(page, "Lösungswörter").click()
    assert "bank" not in held(page, client)["a"]


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
    """A10: each gap change, width, switch, shuffle and every n-th word is one undo step."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    pick(page, "a")
    states = [held(page, client)["a"]]
    actions = [
        lambda: panel(page, "Lücke").click(),
        lambda: panel(page, "Lücke").click(),
        lambda: panel(page, "Gleiche Breite").click(),
        lambda: panel(page, "Lösungswörter").click(),
        lambda: panel(page, "Neu mischen").click(),
        lambda: panel(page, "Jedes n-te Wort").click(),
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


def test_a_caret_in_a_word_gaps_that_word(editor):
    """I1: with a caret in a word and no pick, Lücke gaps that word alone."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Home")
    for _ in range(7):
        page.keyboard.press("ArrowRight")
    panel(page, "Lücke").click()
    expect(page.locator(f"{FIELD} .gap")).to_have_text("zwei")
    assert gapped(held(page, client)["a"]["rich"]) == ["zwei"]


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


def test_the_lucke_button_shows_pressed_in_a_gap_and_keeps_the_field_focused(editor):
    """I4: pressed while the caret stands in a gap; a press on it keeps the field and its typing."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    page.keyboard.press("Home")
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "true")
    panel(page, "Lücke").click()
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "false")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("xHallo")


@pytest.mark.parametrize("kind", ["line", "image", "symbol", "maths", "ruling"])
def test_a_block_that_holds_no_words_shows_no_lucke_button(editor, kind):
    """A13: a line, a picture, a symbol, maths and a Lineatur have no gap to make."""
    client = user()
    page = editor(*({**b, "locked": False} for b in fest(client, kind)), client=client)
    pick(page, "fest")
    expect(page.locator(".panel h2").first).to_be_visible()
    # "Lücke" also names a maths exercise's format, so the gap's own neighbours are looked for.
    expect(
        page.locator(".panel").get_by_role("button", name="Jedes n-te Wort", exact=True)
    ).to_have_count(0)
    expect(
        page.locator(".panel").get_by_role("button", name="Lösungswörter", exact=True)
    ).to_have_count(0)


def test_a_sheet_without_gaps_saves_back_as_it_was(editor):
    """A15: a text with no gap, once the panel is opened on it, is saved with no gap fields."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "false")
    assert "rich" not in held(page, client)["a"]
