"""The Kleines Einmaleins switch of a maths block: on, it leaves only the tasks of the small
times and divide tables, it is greyed without times or divide and with three numbers, it undoes
and redoes, and the line under the panel names it when it stands in the way.
"""

from playwright.sync_api import expect
from test_compare import changed, ctl, shown
from test_three import SIGNS
from ui import at, box, maths, pick, user

SWITCH = "Kleines Einmaleins"


def test_kleines_einmaleins_gives_only_such_tasks(editor):
    """On, a divide block keeps its divisor and its quotient between 1 and 10."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["/"], max=100, count=12)), client=client)
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, SWITCH).click())
    assert props["small"] is True
    exercises = props["exercises"]
    assert len(exercises) == 12
    assert all(1 <= e["b"] <= 10 and 1 <= e["a"] // e["b"] <= 10 for e in exercises)


def test_the_switch_is_grey_without_times_or_divide_and_with_three_numbers_and_keeps_its_value(
    editor,
):
    """Without times or divide, or with three numbers, the switch is greyed; it keeps its value."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["*", "+"], max=100, count=6, small=True)),
        client=client,
    )
    pick(page, "m")
    expect(ctl(page, SWITCH)).to_have_attribute("aria-pressed", "true")
    props = changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    expect(ctl(page, SWITCH)).to_be_disabled()
    assert props["small"] is True
    props = changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    expect(ctl(page, SWITCH)).to_be_enabled()
    expect(ctl(page, SWITCH)).to_have_attribute("aria-pressed", "true")
    assert props["small"] is True
    props = changed(page, client, lambda: page.get_by_label("3 Zahlen", exact=True).click())
    expect(ctl(page, SWITCH)).to_be_disabled()
    expect(ctl(page, SWITCH)).to_have_attribute("aria-pressed", "true")
    assert props["small"] is True


def test_the_switch_undoes_and_redoes(editor):
    """On, then Control+z: the tasks before are back and the switch is off; Control+y: on again."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["/"], max=100, count=12)), client=client)
    pick(page, "m")
    before = shown(at(page, "m"))
    props = changed(page, client, lambda: ctl(page, SWITCH).click())
    assert props["small"] is True
    props = changed(page, client, lambda: page.keyboard.press("Control+z"))
    expect(ctl(page, SWITCH)).to_have_attribute("aria-pressed", "false")
    assert not props.get("small")
    assert shown(at(page, "m")) == before
    props = changed(page, client, lambda: page.keyboard.press("Control+y"))
    expect(ctl(page, SWITCH)).to_have_attribute("aria-pressed", "true")
    assert props["small"] is True


def test_the_line_names_kleines_einmaleins_when_it_stands_in_the_way(editor):
    """Times only, one off, 100 tasks at Zahlenraum 100: only 81 come, and the line names it."""
    client = user()
    page = editor(
        box(
            "m",
            "maths",
            maths(client, ops=["*"], max=100, count=100, one=False, small=True),
        ),
        client=client,
    )
    pick(page, "m")
    expect(page.locator(".panel .hint")).to_contain_text("Kleines Einmaleins")
