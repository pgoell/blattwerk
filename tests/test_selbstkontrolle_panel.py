"""The Selbstkontrolle's panel: each setting, undo and redo, typing as one step, the heading and
Neu mischen. The contract is the comment at the top of frontend/src/selbstkontrolle.ts.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import step
from test_selbstkontrolle import SK, field, props_of
from test_words import redo, undo
from ui import at, box, doc, maths, pick, user

# Twelve different results, so two shuffles almost never agree.
TWELVE = [{"op": "+", "a": n, "b": 1, "result": n + 1, "rest": 0} for n in range(12)]


def linked(client):
    return [
        box("m", "maths", maths(client, exercises=TWELVE, count=12), z=1, w=180, h=30),
        box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=60, y=120),
    ]


@pytest.mark.parametrize(
    "key, before, after, act",
    [
        ("form", "mixed", "sum", lambda p: field(p, "Form").select_option("sum")),
        ("turn", "none", "fold", lambda p: field(p, "Drucken").select_option("fold")),
        ("size", 14, 18, lambda p: field(p, "Schriftgröße").fill("18")),
    ],
    ids=["form", "drucken", "schriftgroesse"],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, before, after, act):
    """A setting stores its prop; Ctrl+Z brings the old value, Ctrl+Y the new."""
    client = user()
    page = editor(*linked(client), client=client)
    pick(page, "s")
    step(page, lambda: act(page))
    assert props_of(doc(page, client), "s")[key] == after
    undo(page)
    assert props_of(doc(page, client), "s")[key] == before
    redo(page)
    assert props_of(doc(page, client), "s")[key] == after


@pytest.mark.parametrize("label, key", [("Überschrift", "title"), ("Lösungswort", "word")])
def test_typing_into_a_text_field_is_one_undo_step(editor, label, key):
    """Typing a heading or a word stores it; one Ctrl+Z takes the whole typing back."""
    client = user()
    page = editor(*linked(client), client=client)
    pick(page, "s")
    if key == "word":
        step(page, lambda: field(page, "Form").select_option("word"))
    before = props_of(doc(page, client), "s")[key]
    text = field(page, label)
    step(page, lambda: (text.press("Control+a"), text.press_sequentially("Prüfe dich")))
    assert props_of(doc(page, client), "s")[key] == "Prüfe dich"
    undo(page)
    assert props_of(doc(page, client), "s")[key] == before


def test_the_heading_prints_what_was_typed_and_an_empty_one_none(editor):
    """The heading shows the typed text; an empty heading draws no heading."""
    client = user()
    page = editor(*linked(client), client=client)
    pick(page, "s")
    text = field(page, "Überschrift")
    step(page, lambda: (text.press("Control+a"), text.press_sequentially("Kontrolle")))
    expect(at(page, "s").locator("h3.title")).to_have_text("Kontrolle")
    step(page, lambda: (text.press("Control+a"), text.press("Backspace")))
    expect(at(page, "s").locator("h3.title")).to_have_count(0)


def test_neu_mischen_stores_a_new_seed_and_shuffles_the_same_results_anew(editor):
    """Neu mischen: another seed, another order, the same results; undo brings the old order."""
    client = user()
    page = editor(*linked(client), client=client)
    items = at(page, "s").locator("ul.mixed li")
    expect(items).to_have_count(12)
    first = items.all_text_contents()
    pick(page, "s")
    seed = props_of(doc(page, client), "s")["seed"]
    step(page, lambda: page.locator(".panel").get_by_role("button", name="Neu mischen").click())
    assert props_of(doc(page, client), "s")["seed"] != seed
    second = items.all_text_contents()
    assert sorted(second) == sorted(first)
    assert second != first
    undo(page)
    expect(items).to_have_text(first)
