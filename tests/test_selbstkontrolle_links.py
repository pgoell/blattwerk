"""Selbstkontrolle links every task block that writes an answer, and can draw that list as a snake,
a caterpillar, a train or a plain box, with wrong answers mixed in.

The list is compared to the linked block's own answer key, not to the Selbstkontrolle's model.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import step
from test_selbstkontrolle import SK, field, props_of
from test_suchsel_print import key_print
from test_words import undo
from ui import at, box, doc, maths, pick, sheet, user

DIAGRAMM = {"points": [{"value": "", "label": "A", "color": "#c0392b", "answer": "4"}]}
# A box the drawing repeats is still one answer, so the list and the key are compared as sets.
SETS = {"zerlegungsfeld"}
ANSWERS = {"textaufgabe": "span.answer"}


def texts(locator):
    return sorted(" ".join(t.split()) for t in locator.all_text_contents() if t.strip())


@pytest.mark.parametrize(
    "kind, props, h",
    [
        ("zahlenhaus", {"seed": 7}, 70),
        ("zahlenkette", {"seed": 7}, 50),
        ("rechentabelle", {"seed": 7}, 80),
        ("pfeilbild", {"seed": 7}, 50),
        ("operatorfeld", {"seed": 7}, 80),
        ("rechenrad", {"seed": 7}, 80),
        ("magischesquadrat", {"seed": 7}, 80),
        ("malquadrat", {"seed": 7}, 90),
        ("zerlegungsfeld", {"seed": 7}, 80),
        ("halbschriftlich", {"seed": 7}, 90),
        ("zehnerfeld", {"seed": 7}, 80),
        ("textaufgabe", {"seed": 7}, 120),
        ("diagramm", DIAGRAMM, 80),
    ],
)
def test_the_list_holds_what_the_blocks_own_key_writes(browser, server, kind, props, h):
    """The mixed list equals the red answers of the linked block."""
    client = user()
    mine = sheet(
        client,
        [
            box("m", kind, props, z=1, w=180, h=h, y=10),
            box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=70, y=210),
        ],
    )["id"]
    paper = key_print(browser, server, mine)
    want = texts(paper.locator(f".block:has(.{kind}) {ANSWERS.get(kind, 'text.answer')}"))
    got = texts(paper.locator("ul.mixed li"))
    assert want
    if kind in SETS:
        assert set(got) == set(want)
    else:
        assert got == want
    paper.context.close()


SUMS = [{"op": "+", "a": n, "b": 1, "result": n + 1, "rest": 0} for n in (2, 4, 6)]


def linked(client, **sk):
    return [
        box("m", "maths", maths(client, exercises=SUMS, count=3), z=1, w=180, h=24),
        box("s", "selbstkontrolle", {**SK, "links": ["m"], **sk}, z=2, w=180, h=70, y=80),
    ]


@pytest.mark.parametrize(
    "look, root",
    [
        ("snake", "svg.snake"),
        ("caterpillar", "svg.caterpillar"),
        ("train", "svg.train"),
        ("box", "ul.box"),
    ],
)
def test_each_look_draws_its_shape_and_not_the_tick_list(editor, look, root):
    """Darstellung stores the look and the block draws that shape."""
    client = user()
    page = editor(*linked(client, look=look), client=client)
    expect(at(page, "s").locator(root)).to_be_visible()
    expect(at(page, "s").locator("ul.mixed")).to_have_count(0)
    expect(at(page, "s").locator("span.tick")).to_have_count(0)


def test_falsche_loesungen_adds_that_many_and_undo_removes_them(editor):
    """Falsche Lösungen stores the count; the snake shows the results plus that many; one undo
    takes the count back and the extra circles with it."""
    client = user()
    page = editor(*linked(client, look="snake"), client=client)
    bubbles = at(page, "s").locator("svg.snake circle.bubble")
    expect(bubbles).to_have_count(3)
    pick(page, "s")
    step(page, lambda: field(page, "Falsche Lösungen").fill("2"))
    assert props_of(doc(page, client), "s")["wrongs"] == 2
    expect(bubbles).to_have_count(5)
    undo(page)
    expect(bubbles).to_have_count(3)


def test_darstellung_stores_the_snake_and_undo_returns_the_tick_list(editor):
    """Choosing Zahlenschlange stores look snake and draws it; Ctrl+Z brings the tick list back."""
    client = user()
    page = editor(*linked(client), client=client)
    pick(page, "s")
    step(page, lambda: field(page, "Darstellung").select_option("snake"))
    assert props_of(doc(page, client), "s")["look"] == "snake"
    expect(at(page, "s").locator("svg.snake circle.bubble")).to_have_count(3)
    undo(page)
    expect(at(page, "s").locator("ul.mixed li")).to_have_count(3)
    expect(at(page, "s").locator("span.tick")).to_have_count(3)
