"""Patterns for the numbers and the result of a Rechnen block (#839).

A pattern is `X` for any digit and a digit where it is fixed. Its length is the number of digits.
At most two of the first number, the second number and the result are fixed (no `X`); the panel
says so. A pattern combines with Übertrag, and a contradiction names the limit to loosen.
"Die Null darf vorkommen" is one switch per operation family: Strich (+ and -) and Punkt (* and /).
"""

import pytest
from playwright.sync_api import expect
from pydantic import ValidationError
from ui import box, maths, pick, saved, user

from blattwerk.maths import Settings, generate
from blattwerk.maths.pairs import carries


def block(**limits):
    return Settings.model_validate({"ops": ["+"], "max": 100, "count": 8, "seed": 1, **limits})


def like(pattern, n, zero=True):
    """Whether `n` is the pattern, apart from the generator."""
    text = str(n)
    if not zero and "0" in text:
        return False
    if not pattern:
        return True
    if len(text) != len(pattern):
        return False
    return all(ch == "X" or ch == digit for ch, digit in zip(pattern, text, strict=True))


def keeps(out, **rules):
    assert out["loosen"] is None
    assert len(out["exercises"]) == rules.get("count", 8)
    for e in out["exercises"]:
        assert like(rules.get("pa", ""), e["a"], rules.get("zero", True))
        assert like(rules.get("pb", ""), e["b"], rules.get("zero", True))
        assert like(rules.get("pr", ""), e["result"], rules.get("zero", True))


def test_x0_plus_x():
    """`X0 + X`: the first number ends in 0 and has two digits, the second has one."""
    keeps(generate(block(pa="X0", pb="X")), pa="X0", pb="X")


def test_twenty_plus_x():
    """`20 + X`: the first number is 20, the second has one digit."""
    out = generate(block(pa="20", pb="X"))
    keeps(out, pa="20", pb="X")
    assert {e["a"] for e in out["exercises"]} == {20}


def test_x7_plus_x5_carries_when_uebertrag_is_required():
    """`X7 + X5` with Übertrag Mit: every task carries, and both numbers have two digits."""
    out = generate(block(pa="X7", pb="X5", carry="required"))
    keeps(out, pa="X7", pb="X5")
    assert all(any(carries("+", e["a"], e["b"])) for e in out["exercises"])


def test_x0_plus_x_with_uebertrag_names_the_limit():
    """`X0 + X` never carries: the ones are 0 plus a single digit. Mit leaves no task."""
    out = generate(block(pa="X0", pb="X", carry="required", count=5))
    assert out["exercises"] == []
    assert out["loosen"] == ["carry", "pa", "pb"]


def test_xx_plus_xx_is_100():
    """`XX + XX = 100`: both numbers have two digits and the result is 100."""
    out = generate(block(pa="XX", pb="XX", pr="100", count=12))
    keeps(out, pa="XX", pb="XX", pr="100", count=12)
    assert {e["result"] for e in out["exercises"]} == {100}


def test_x00_minus_x0():
    """`X00 - X0`: a hundreds number minus a tens number, inside bis 1000."""
    out = generate(block(ops=["-"], max=1000, pa="X00", pb="X0"))
    keeps(out, pa="X00", pb="X0")
    assert all(e["op"] == "-" and e["a"] >= e["b"] for e in out["exercises"])


def test_no_zero_in_a_strich_task_and_x0_names_the_switch():
    """With the Strich switch off, no digit is 0. `X0` asks for a 0, so the hint names the switch."""
    out = generate(block(pa="XX", pb="XX", nil={"strich": False}))
    keeps(out, pa="XX", pb="XX", zero=False)
    blocked = generate(block(pa="X0", pb="X", nil={"strich": False}, count=4))
    assert blocked["exercises"] == []
    assert blocked["loosen"] == ["pa", "nil"]


def test_a_pattern_and_the_digit_ranges_that_disagree_name_both():
    """Ones only from 1 to 9 cannot end in the 0 of `X0`."""
    out = generate(block(pa="X0", pb="X", a=[[1, 9], [0, 9]], count=4))
    assert out["exercises"] == []
    assert "a" in out["loosen"] and "pa" in out["loosen"]


def test_three_fixed_numbers_that_disagree_name_the_result():
    """The server still takes three fixed numbers. 20 + 30 is not 100, so the result is in the way."""
    out = generate(block(pa="20", pb="30", pr="100", count=1))
    assert out["exercises"] == []
    assert "pr" in out["loosen"]
    fit = generate(block(pa="20", pb="30", pr="50", count=1))
    assert [(e["a"], e["b"], e["result"]) for e in fit["exercises"]] == [(20, 30, 50)]


def test_a_pattern_that_is_not_x_or_a_digit_is_refused():
    with pytest.raises(ValidationError):
        block(pa="Y0")


def test_the_panel_sets_a_pattern_and_refuses_a_third_fixed_number(editor):
    """The panel takes `X0 + X`, says that two numbers can be fixed, and keeps the third free."""
    client = user()
    page = editor(box("m", "maths", maths(client, max=100, count=6, seed=1)), client=client)
    pick(page, "m")
    panel = page.locator(".panel")
    panel.get_by_label("Muster der 1. Zahl").fill("X0")
    panel.get_by_label("Muster der 2. Zahl").fill("X")
    expect(page.locator("header [role=status]")).to_have_text("Speichert …")
    props = saved(page, client)[0]["props"]
    assert props["pa"] == "X0" and props["pb"] == "X"
    assert props["exercises"]
    assert all(like("X0", e["a"]) and like("X", e["b"]) for e in props["exercises"])
    expect(panel.get_by_text("Höchstens zwei der drei Zahlen können feststehen.")).to_be_visible()
    panel.get_by_label("Muster der 1. Zahl").fill("20")
    panel.get_by_label("Muster der 2. Zahl").fill("4")
    result = panel.get_by_label("Muster des Ergebnisses")
    # A fixed 25 would be the third fixed number. The field snaps back to empty.
    result.evaluate(
        """(el) => {
          Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, "25");
          el.dispatchEvent(new Event("input", { bubbles: true }));
        }"""
    )
    expect(result).to_have_value("")
    expect(
        panel.get_by_role("button", name="Die Null darf bei + und \N{MINUS SIGN} vorkommen")
    ).to_have_attribute("aria-pressed", "true")
