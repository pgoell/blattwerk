"""The format panel's switch for line numbers on texts, and its step, with undo and redo."""

import pytest
from playwright.sync_api import expect
from ui import RECT, RULING, TABLE, TEXT, box, doc, pick, user


def button(page, name):
    """A button of the format panel, by its text."""
    return page.locator(".panel").get_by_role("button", name=name, exact=True)


def props(page, client):
    """Each block's props on the first page, by the block's name, as the server holds them."""
    return {b["id"]: b["props"] for b in doc(page, client)["pages"][0]["blocks"]}


# Asked #63, A6


def test_the_switch_numbers_a_text(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    switch = button(page, "Zeilennummern")
    expect(switch).to_have_attribute("aria-pressed", "false")
    switch.click()
    expect(switch).to_have_attribute("aria-pressed", "true")
    # A new switch starts with every fifth line.
    assert props(page, client)["a"]["lines"] == 5
    switch.click()
    expect(switch).to_have_attribute("aria-pressed", "false")
    assert "lines" not in props(page, client)["a"]


# Asked #63, A7


def test_the_step_is_every_line_or_every_fifth(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    button(page, "Zeilennummern").click()
    every_line = button(page, "Jede Zeile")
    every_fifth = button(page, "Jede 5. Zeile")
    expect(every_fifth).to_have_attribute("aria-pressed", "true")
    every_line.click()
    expect(every_line).to_have_attribute("aria-pressed", "true")
    expect(every_fifth).to_have_attribute("aria-pressed", "false")
    assert props(page, client)["a"]["lines"] == 1
    every_fifth.click()
    expect(every_fifth).to_have_attribute("aria-pressed", "true")
    assert props(page, client)["a"]["lines"] == 5


# Asked #63, A11


def test_undo_and_redo_walk_the_switch_and_the_step_one_press_at_a_time(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    switch = button(page, "Zeilennummern")
    switch.click()
    every_line = button(page, "Jede Zeile")
    every_line.click()
    expect(every_line).to_have_attribute("aria-pressed", "true")
    assert props(page, client)["a"]["lines"] == 1
    # Back to the step of 5, then off, one press each.
    page.keyboard.press("Control+z")
    expect(button(page, "Jede 5. Zeile")).to_have_attribute("aria-pressed", "true")
    assert props(page, client)["a"]["lines"] == 5
    page.keyboard.press("Control+z")
    expect(switch).to_have_attribute("aria-pressed", "false")
    assert "lines" not in props(page, client)["a"]
    page.keyboard.press("Control+y")
    expect(switch).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Control+y")
    expect(every_line).to_have_attribute("aria-pressed", "true")
    assert props(page, client)["a"]["lines"] == 1


# Asked #63, A13


@pytest.mark.parametrize(
    "kind, props_",
    [
        pytest.param("shape", {**RECT, "text": "Hallo"}, id="shape"),
        pytest.param("table", TABLE, id="table"),
        pytest.param("ruling", RULING, id="ruling"),
    ],
)
def test_only_a_text_has_the_switch(editor, kind, props_):
    page = editor(box("a", kind, props_))
    pick(page, "a")
    expect(button(page, "Zeilennummern")).to_have_count(0)


def test_with_a_text_and_a_shape_picked_only_the_text_gets_lines(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("b", "shape", {**RECT, "text": "Hallo"}, z=2),
        client=client,
    )
    pick(page, "a", "b")
    button(page, "Zeilennummern").click()
    expect(button(page, "Zeilennummern")).to_have_attribute("aria-pressed", "true")
    saved = props(page, client)
    assert saved["a"]["lines"] == 5
    assert "lines" not in saved["b"]


# Asked #63, I1


def test_several_texts_get_one_step_and_one_undo(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "lines": 1}),
        box("b", "text", TEXT, z=2),
        client=client,
    )
    pick(page, "a", "b")
    switch = button(page, "Zeilennummern")
    expect(switch).to_have_attribute("aria-pressed", "false")
    switch.click()
    expect(switch).to_have_attribute("aria-pressed", "true")
    saved = props(page, client)
    assert saved["a"]["lines"] == 5
    assert saved["b"]["lines"] == 5
    page.keyboard.press("Control+z")
    expect(switch).to_have_attribute("aria-pressed", "false")
    saved = props(page, client)
    assert saved["a"]["lines"] == 1
    assert "lines" not in saved["b"]


def test_several_numbered_texts_are_switched_off_in_one_step(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "lines": 1}),
        box("b", "text", {**TEXT, "lines": 5}, z=2),
        client=client,
    )
    pick(page, "a", "b")
    switch = button(page, "Zeilennummern")
    expect(switch).to_have_attribute("aria-pressed", "true")
    switch.click()
    expect(switch).to_have_attribute("aria-pressed", "false")
    saved = props(page, client)
    assert "lines" not in saved["a"]
    assert "lines" not in saved["b"]
    page.keyboard.press("Control+z")
    expect(switch).to_have_attribute("aria-pressed", "true")
    saved = props(page, client)
    assert saved["a"]["lines"] == 1
    assert saved["b"]["lines"] == 5


# Asked #63, A15


@pytest.mark.parametrize("stored", ["5", 0], ids=["text-5", "zero"])
def test_a_stored_value_that_is_no_step_shows_the_switch_off(editor, stored):
    page = editor(box("a", "text", {**TEXT, "lines": stored}))
    pick(page, "a")
    expect(button(page, "Zeilennummern")).to_have_attribute("aria-pressed", "false")


# Asked #63, A6 and A11: the switch and the numbers drawn, together


def test_the_switch_and_the_step_draw_the_numbers_and_undo_takes_them_away(editor):
    words = "Der kleine Igel sucht im Herbst unter den Bäumen nach Futter. " * 6
    page = editor(box("a", "text", {**TEXT, "text": words}, w=80, h=120))
    pick(page, "a")
    numbers = page.locator('.block[data-id="a"] .ln')
    expect(numbers).to_have_count(0)
    button(page, "Zeilennummern").click()
    expect(numbers.first).to_have_text("5")
    fifths = numbers.count()
    button(page, "Jede Zeile").click()
    expect(numbers.first).to_have_text("1")
    assert numbers.count() >= 5 * fifths
    page.keyboard.press("Control+z")
    expect(numbers.first).to_have_text("5")
    page.keyboard.press("Control+z")
    expect(page.locator('.block[data-id="a"] .numbers')).to_have_count(0)
    page.keyboard.press("Control+y")
    expect(numbers).to_have_count(fifths)


# Asked #396: a text's numbers start at any number, "Beginnt bei"

WORDS = "Der kleine Igel sucht im Herbst unter den Bäumen nach Futter. " * 12


def start_field(page):
    """The field "Beginnt bei" of the format panel."""
    return page.locator(".panel").get_by_label("Beginnt bei", exact=True)


def start_at(page, value):
    """Types a value into "Beginnt bei" and commits it on Enter."""
    field = start_field(page)
    field.click()
    field.fill(value)
    field.press("Enter")


def numbers_of(page):
    """The line numbers drawn beside the text "a", top to bottom."""
    return page.locator('.block[data-id="a"] .ln')


def test_beginnt_bei_sets_the_first_number(editor):
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": WORDS, "lines": 1}, w=80, h=200), client=client)
    pick(page, "a")
    start_at(page, "7")
    assert props(page, client)["a"]["linesFrom"] == 7
    numbers = numbers_of(page)
    expect(numbers.first).to_have_text("7")
    assert numbers.all_text_contents()[:3] == ["7", "8", "9"]


def test_a_text_without_a_start_counts_from_one(editor):
    page = editor(box("a", "text", {**TEXT, "text": WORDS, "lines": 1}, w=80, h=200))
    pick(page, "a")
    numbers = numbers_of(page)
    expect(numbers.first).to_have_text("1")
    assert numbers.all_text_contents()[:3] == ["1", "2", "3"]
    button(page, "Jede 5. Zeile").click()
    expect(numbers.first).to_have_text("5")
    assert numbers.all_text_contents()[:2] == ["5", "10"]


def test_the_start_is_one_undo_step(editor):
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": WORDS, "lines": 1}, w=80, h=200), client=client)
    pick(page, "a")
    start_at(page, "7")
    expect(numbers_of(page).first).to_have_text("7")
    page.keyboard.press("Control+z")
    expect(numbers_of(page).first).to_have_text("1")
    assert "linesFrom" not in props(page, client)["a"]
    page.keyboard.press("Control+y")
    expect(numbers_of(page).first).to_have_text("7")
    assert props(page, client)["a"]["linesFrom"] == 7


def test_every_fifth_line_counts_multiples_of_five_from_the_start(editor):
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": WORDS, "lines": 1}, w=80, h=200), client=client)
    pick(page, "a")
    start_at(page, "3")
    numbers = numbers_of(page)
    expect(numbers.first).to_have_text("3")
    assert numbers.all_text_contents()[:3] == ["3", "4", "5"]
    # The third line of the text is the one numbered 5.
    third_line = numbers.nth(2).get_attribute("y")
    button(page, "Jede 5. Zeile").click()
    expect(numbers.first).to_have_text("5")
    assert numbers.all_text_contents()[:2] == ["5", "10"]
    assert numbers.first.get_attribute("y") == third_line
    assert props(page, client)["a"]["linesFrom"] == 3


def test_several_texts_with_other_starts_leave_the_field_blank_and_one_step_sets_all(editor):
    client = user()
    text = {**TEXT, "text": WORDS, "lines": 1}
    page = editor(
        box("a", "text", {**text, "linesFrom": 7}, w=80, h=200),
        box("b", "text", {**text, "linesFrom": 2}, w=80, h=200, z=2, x=130),
        client=client,
    )
    pick(page, "a", "b")
    expect(start_field(page)).to_have_value("")
    start_at(page, "9")
    saved = props(page, client)
    assert saved["a"]["linesFrom"] == 9
    assert saved["b"]["linesFrom"] == 9
    page.keyboard.press("Control+z")
    saved = props(page, client)
    assert saved["a"]["linesFrom"] == 7
    assert saved["b"]["linesFrom"] == 2


@pytest.mark.parametrize("junk", ["abc", "0", "-2"])
def test_a_start_that_is_no_number_from_one_is_refused(editor, junk):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "text": WORDS, "lines": 1, "linesFrom": 4}, w=80, h=200),
        client=client,
    )
    pick(page, "a")
    expect(start_field(page)).to_have_value("4")
    start_at(page, junk)
    expect(start_field(page)).to_have_value("4")
    assert props(page, client)["a"]["linesFrom"] == 4


# Own case: the field is only there while the text is numbered.
def test_the_start_field_shows_only_with_the_numbers(editor):
    page = editor(box("a", "text", {**TEXT, "text": WORDS}, w=80, h=200))
    pick(page, "a")
    expect(start_field(page)).to_have_count(0)
    button(page, "Zeilennummern").click()
    expect(start_field(page)).to_have_value("1")


# Own case: a stored start that is no whole number from 1 draws from 1, as a text saved without one.
@pytest.mark.parametrize("stored", [0, "abc"], ids=["zero", "text"])
def test_a_stored_start_that_is_no_number_draws_from_one(editor, stored):
    props_ = {**TEXT, "text": WORDS, "lines": 1, "linesFrom": stored}
    page = editor(box("a", "text", props_, w=80, h=200))
    pick(page, "a")
    numbers = numbers_of(page)
    expect(numbers.first).to_have_text("1")
    assert numbers.all_text_contents()[:3] == ["1", "2", "3"]


def numbered_text(page):
    """A text with every line numbered, its right panel open on it."""
    pick(page, "a")
    expect(button(page, "Jede Zeile")).to_have_attribute("aria-pressed", "true")


def start_row(page):
    """The row of "Beginnt bei": its label, which holds the field."""
    return page.locator(".panel label", has=page.get_by_label("Beginnt bei", exact=True))


# Asked #615: the row Beginnt bei fits the panel, and typing in it does not slide the panel.
@pytest.mark.parametrize(
    "typed,width",
    [("7", 1400), ("9999", 1400), ("7", 1024)],
    ids=["seven", "four-digits", "narrow-window"],
)
def test_the_start_row_fits_and_typing_does_not_slide_the_panel(editor, typed, width):
    page = editor(box("a", "text", {**TEXT, "text": WORDS, "lines": 1}, w=80, h=200))
    page.set_viewport_size({"width": width, "height": 1000})
    numbered_text(page)
    above = button(page, "Jede 5. Zeile").locator("xpath=..").bounding_box()
    row = start_row(page).bounding_box()
    assert row["x"] + row["width"] <= above["x"] + above["width"] + 0.5
    panel = page.locator(".panel")
    assert panel.evaluate("e => e.scrollWidth <= e.clientWidth")
    start_field(page).click()
    page.keyboard.press("Control+a")
    page.keyboard.type(typed)
    page.keyboard.press("Tab")
    expect(start_field(page)).to_have_value(typed)
    assert panel.evaluate("e => e.scrollLeft") == 0
    inside = panel.bounding_box()
    label = start_row(page).bounding_box()
    right = inside["x"] + inside["width"]
    assert inside["x"] <= label["x"] and label["x"] + label["width"] <= right + 0.5
