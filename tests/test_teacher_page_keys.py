"""The teacher-page tool's keys: a slider, a chord, typing, and picking a colour."""

import pytest
from playwright.sync_api import expect
from test_teacher_page import (
    ONE,
    POPUP,
    TWO,
    far,
    folder,  # noqa: F401
    pytestmark,  # noqa: F401
    shape,
    slider,
    tool,
)
from ui import (
    FIELD,
    at,
    box,
    expect_picked,
    saved,
    user,
)

# The keys


def test_key_moves_the_slider_randstaerke_after_a_click_on_its_name(editor):
    client = user()
    page = shape(editor, client)
    # The click lands on the slider's middle: it takes the focus, and the knob jumps there.
    tool.click(page, "Randstärke")
    expect(slider(page)).to_be_focused()
    expect(slider(page)).to_have_value("1.5")
    said = tool.key(page, "ArrowRight", "3")
    assert said.startswith("pressed ArrowRight 3 times: ")
    expect(slider(page)).to_have_value("2.25")
    assert saved(page, client)[0]["props"]["strokeWidth"] == 2.25
    expect_picked(page, "a")


def test_key_takes_a_chord(editor):
    page = editor(box("a", "text", ONE), box("b", "text", TWO, z=2))
    tool.key(page, "Control+a")
    expect_picked(page, "a", "b")


def test_type_writes_into_the_text_that_enter_opened(editor):
    page = editor(box("a", "text", ONE))
    tool.click(page, "Eins")
    tool.key(page, "Enter")
    said = tool.type_(page, "du da")
    assert said.startswith("typed 5 letters: ")
    expect(page.locator(FIELD)).to_have_text("du da")


@pytest.mark.native
def test_key_arrows_60_times_and_enter_pick_a_colour_the_eye_can_tell(editor):
    page = editor(box("a", "text", ONE))
    words = at(page, "a").get_by_text("Eins")
    field = page.locator(".panel").get_by_label("Farbe", exact=True)
    tool.click(page, "Eins")
    expect(words).to_have_css("color", "rgb(34, 34, 34)")
    tool.click(page, "Farbe")
    expect(field).to_be_focused()
    expect(page.locator(POPUP)).to_have_count(1)
    # The picker is `:open` before it listens: an arrow that came too early is pressed again.
    for _ in range(5):
        tool.key(page, "ArrowUp")
        if field.input_value() != "#222222":
            break
    expect(field).not_to_have_value("#222222")
    # As the brief's recipe says: one arrow alone is a step too small to see.
    tool.key(page, "ArrowUp", "60")
    tool.key(page, "ArrowRight", "60")
    tool.key(page, "Enter")
    expect(page.locator(POPUP)).to_have_count(0)
    picked = field.input_value()
    assert far(picked) >= 60, picked
    red, green, blue = (int(picked[n : n + 2], 16) for n in (1, 3, 5))
    # The arrows to the right gave the grey a tint.
    assert red > green
    expect(words).to_have_css("color", f"rgb({red}, {green}, {blue})")
