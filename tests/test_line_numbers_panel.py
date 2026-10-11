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
