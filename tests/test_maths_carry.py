"""Übertrag per place (#838): Zehner, Hunderter and Tausender, each Ohne, Mit or Egal.

Plus crosses a place when its two digits sum to more than 10. Landing on 10
(7 + 3, 17 + 23) does not. Nothing is carried on, so 395 + 7 does not cross a hundred.
Minus crosses a place when that digit of the first number is smaller than the second's,
so it would go below 0. A place is offered once the Zahlenraum goes past it.
"""

from playwright.sync_api import expect
from test_compare import changed, ctl
from test_maths import settings_for
from ui import box, maths, pick, user

from blattwerk.maths import generate
from blattwerk.maths.carry import crosses_at, offered


def test_landing_on_ten_is_no_crossing():
    """#838: 7 + 3 and 17 + 23 do not cross at the Einer; 8 + 5 does; 6 + 3 does not."""
    assert crosses_at("+", 7, 3, 0) is False
    assert crosses_at("+", 17, 23, 0) is False
    assert crosses_at("+", 17, 23, 1) is False
    assert crosses_at("+", 8, 5, 0) is True
    assert crosses_at("+", 6, 3, 0) is False
    assert crosses_at("+", 20, 80, 1) is False


def test_a_carry_does_not_run_on_and_a_digit_below_zero_crosses():
    """#838: 395 + 7 does not cross a hundred; 370 + 280 does; 10 - 4 does, 16 - 4 does not."""
    assert crosses_at("+", 370, 280, 1) is True
    assert crosses_at("+", 395, 7, 1) is False
    assert crosses_at("-", 13, 5, 0) is True
    assert crosses_at("-", 10, 4, 0) is True
    assert crosses_at("-", 16, 4, 0) is False
    assert offered(10) == 0
    assert offered(20) == 1
    assert offered(100) == 1
    assert offered(1000) == 2
    assert offered(1_000_000) == 3


def test_ohne_zehner_and_mit_hunderter_keep_each_place():
    """#838: Ohne Zehnerübergang allows a sum of 10 and refuses one past it; Mit Hunderter needs the tens to pass 10."""
    out = generate(
        settings_for(
            max=1000,
            count=20,
            seed=1,
            ops=["+"],
            carry=["none", "required", "either"],
        )
    )
    assert out["exercises"]
    for e in out["exercises"]:
        assert (e["a"] % 10) + (e["b"] % 10) <= 10
        assert (e["a"] // 10 % 10) + (e["b"] // 10 % 10) > 10


def test_a_rule_that_leaves_no_task_is_named_in_the_hint():
    """#838: ones digits 6 to 9 always cross a ten, so Ohne names Zehnerübergang."""
    out = generate(
        settings_for(
            max=100,
            count=5,
            a=[(6, 9)],
            b=[(6, 9)],
            carry=["none", "either", "either"],
        )
    )
    assert out["exercises"] == []
    assert "zehner" in out["loosen"]


def test_the_panel_offers_a_place_when_the_zahlenraum_goes_past_it(editor):
    """#838: bis 1000000 offers all three, bis 1000 the first two, bis 20 only the Zehner."""
    client = user()
    page = editor(box("m", "maths", maths(client, max=1_000_000, count=4)), client=client)
    pick(page, "m")
    panel = page.locator(".panel")
    for name in ("Zehnerübergang", "Hunderterübergang", "Tausenderübergang"):
        expect(panel.get_by_role("heading", name=name, exact=True)).to_be_visible()
    panel.get_by_label("Zahlenraum", exact=True).select_option("1000")
    expect(panel.get_by_role("heading", name="Tausenderübergang", exact=True)).to_have_count(0)
    expect(panel.get_by_role("heading", name="Hunderterübergang", exact=True)).to_be_visible()
    panel.get_by_label("Zahlenraum", exact=True).select_option("20")
    expect(panel.get_by_role("heading", name="Hunderterübergang", exact=True)).to_have_count(0)
    expect(panel.get_by_role("heading", name="Zehnerübergang", exact=True)).to_be_visible()
    changed(
        page,
        client,
        lambda: panel.locator(".places").nth(0).get_by_label("E von").select_option("6"),
    )
    changed(
        page,
        client,
        lambda: panel.locator(".places").nth(1).get_by_label("E von").select_option("6"),
    )
    props = changed(page, client, lambda: ctl(page, "Ohne").click())
    assert props["carry"] == ["none", "either", "either"]
    assert props["exercises"] == []
    expect(panel.locator(".hint")).to_contain_text("Zehnerübergang")
