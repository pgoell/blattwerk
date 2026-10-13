"""The Nachkommastellen row with Geld: one row, one choice lit. A click on 0, 1 or 2 with Geld on
takes Geld off in the same step, and Control+z undoes that step in one go.
"""

import pytest
from playwright.sync_api import expect
from test_compare import changed, ctl, shown
from ui import at, box, maths, pick, user

NACH = {0: "0 Nachkommastellen", 1: "1 Nachkommastelle", 2: "2 Nachkommastellen"}
ROW = [*NACH.values(), "Geld"]


@pytest.mark.parametrize("n", [0, 1, 2])
def test_a_click_on_a_number_turns_geld_off_at_once(editor, n):
    """A click on 0, 1 or 2 with Geld on: Geld goes off, the number is lit, and no task shows €."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+"], max=10, count=6, decimals=1, money=True)),
        client=client,
    )
    pick(page, "m")
    expect(ctl(page, "Geld")).to_have_attribute("aria-pressed", "true")
    props = changed(page, client, lambda: ctl(page, NACH[n]).click())
    expect(ctl(page, "Geld")).to_have_attribute("aria-pressed", "false")
    expect(ctl(page, NACH[n])).to_have_attribute("aria-pressed", "true")
    assert props["money"] is False and props["decimals"] == n
    assert all("€" not in text for text in shown(at(page, "m")))
    if n == 0:
        assert all("," not in text for text in shown(at(page, "m")))


def test_only_one_button_of_the_row_is_lit(editor):
    """With Geld on exactly one button of the row is pressed: Geld."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+"], max=10, count=6, decimals=1, money=True)),
        client=client,
    )
    pick(page, "m")
    expect(ctl(page, "Geld")).to_have_attribute("aria-pressed", "true")
    pressed = [ctl(page, name).get_attribute("aria-pressed") for name in ROW]
    assert pressed.count("true") == 1


def test_the_geld_row_undoes_in_one_step(editor):
    """Geld on, a click on 0, then Control+z once: Geld is on again and the tasks show €."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+"], max=10, count=6, decimals=1, money=True)),
        client=client,
    )
    pick(page, "m")
    changed(page, client, lambda: ctl(page, NACH[0]).click())
    props = changed(page, client, lambda: page.keyboard.press("Control+z"))
    expect(ctl(page, "Geld")).to_have_attribute("aria-pressed", "true")
    assert props["money"] is True
    assert all("€" in text for text in shown(at(page, "m")))
