"""Issue #76: the panel's choices for trace text (Nachspurtext): Aus, Grau, Umriss, Gepunktet.

Checklist ids are in each docstring.
"""

from playwright.sync_api import expect
from test_undo_steps import step
from ui import RECT, RULING, TEXT, box, doc, pick, user

CHOICES = ["Aus", "Grau", "Umriss", "Gepunktet"]


def block(page, client, name):
    return next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == name)


def trace_of(page, client, name):
    return block(page, client, name)["props"].get("trace")


def fade_of(page, client, name):
    return block(page, client, name)["props"].get("fade")


def choose(page, key):
    page.get_by_label("Nachspurtext", exact=True).select_option(key)


def test_a_lineatur_has_four_choices(editor):
    """B1: the Lineatur's select has four choices in order; each stores its trace."""
    client = user()
    page = editor(box("l1", "ruling", RULING), client=client)
    pick(page, "l1")
    select = page.get_by_label("Nachspurtext", exact=True)
    expect(select.locator("option")).to_have_text(CHOICES)
    choose(page, "grey")
    expect(select).to_have_value("grey")
    assert trace_of(page, client, "l1") is True
    choose(page, "off")
    expect(select).to_have_value("off")
    assert trace_of(page, client, "l1") is None


def test_dotted_is_off_for_a_font_without_a_cut(editor):
    """B4: Gepunktet is off in Andika, with a hint; in Urff it is on and stores "dotted"."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    select = page.get_by_label("Nachspurtext", exact=True)
    expect(select.locator("option", has_text="Gepunktet")).to_be_disabled()
    expect(page.get_by_text("Gepunktet gibt es nur in der Grundschrift (Urff).")).to_be_visible()
    page.get_by_label("Schriftart", exact=True).select_option("urff")
    expect(select.locator("option", has_text="Gepunktet")).to_be_enabled()
    expect(page.get_by_text("Gepunktet gibt es nur in der Grundschrift (Urff).")).to_have_count(0)
    choose(page, "dotted")
    assert trace_of(page, client, "a") == "dotted"


def test_fading_switch_and_direction(editor):
    """B5: Ausblenden shows only with a look on; the directions store "row" and "rows"."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    expect(page.get_by_role("button", name="Ausblenden")).to_have_count(0)
    choose(page, "outline")
    page.get_by_role("button", name="Ausblenden").click()
    assert fade_of(page, client, "a") == "row"
    expect(page.get_by_role("button", name="In der Zeile")).to_have_attribute(
        "aria-pressed", "true"
    )
    page.get_by_role("button", name="Von Zeile zu Zeile").click()
    assert fade_of(page, client, "a") == "rows"
    page.get_by_role("button", name="Ausblenden").click()
    assert fade_of(page, client, "a") is None


def test_each_choice_is_one_undo_step(editor):
    """B8: each choice is one undo step; redo walks them forward again."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    choose(page, "outline")
    page.get_by_role("button", name="Ausblenden").click()
    page.get_by_role("button", name="Von Zeile zu Zeile").click()
    for _ in range(3):
        step(page, lambda: page.keyboard.press("Control+z"))
    expect(page.get_by_label("Nachspurtext", exact=True)).to_have_value("off")
    for _ in range(3):
        step(page, lambda: page.keyboard.press("Control+y"))
    expect(page.get_by_label("Nachspurtext", exact=True)).to_have_value("outline")
    assert fade_of(page, client, "a") == "rows"


def test_one_choice_sets_all_picked_blocks(editor):
    """I1: one choice sets Umriss on every picked block, and one Control+z takes it from all."""
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", TEXT, z=2),
        box("c", "shape", {**RECT, "text": "Im Kasten"}, z=3),
        client=client,
    )
    pick(page, "a", "b", "c")
    choose(page, "outline")
    for name in "abc":
        assert trace_of(page, client, name) == "outline"
    step(page, lambda: page.keyboard.press("Control+z"))
    for name in "abc":
        assert trace_of(page, client, name) is None
