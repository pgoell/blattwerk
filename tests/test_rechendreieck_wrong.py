"""A Rechendreieck whose typed numbers allow no triangle, or a number above the Zahlenraum: the
answer key, the panel's hints and the number field's selection. Issues #559, #560.

The docstrings name the issue and the PR that brought the fault in.
"""

from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import step
from test_suchsel_print import key_print
from ui import box, pick, user

DREIECK = {
    "count": 4,
    "columns": 3,
    "max": 20,
    "given": "inner",
    "empty": False,
    "seed": 7,
}
# The first triangle's three inner numbers 1, 1, 1 and its outer 5 allow no triangle (#559).
WRONG = [[0, 0, 1], [0, 1, 1], [0, 2, 1], [0, 5, 5]]
INNER_TOP = "Zahl im Feld innen oben"


def dz(name, props):
    return box(name, "rechendreieck", props, w=180, h=50)


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def test_the_key_prints_no_made_up_numbers_for_a_triangle_that_allows_none(editor, browser, server):
    """#559 (PR #565): the key shows no answer text in the wrong triangle, the rest keep theirs."""
    client = user()
    page = editor(dz("d", {**DREIECK, "typed": WRONG}), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".triangle.wrong")).to_have_count(1)
    assert paper.locator(".triangle.wrong .answer").count() == 0
    assert paper.locator(".triangle:not(.wrong) .answer").count() > 0
    paper.context.close()


def test_the_panel_names_every_triangle_that_allows_none(editor):
    """#559 (PR #565): a wrong triangle 2 gives its hint while the panel shows Dreieck 1."""
    page = editor(dz("d", {**DREIECK, "typed": [[1, 0, 1], [1, 1, 1], [1, 2, 1], [1, 5, 5]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Dreieck 2 geht mit diesen Zahlen nicht auf.")


def test_a_number_above_the_zahlenraum_gives_the_hint(editor):
    """#560 (PR #565): 159 in an outer box of a bis 20 triangle names the Zahlenraum."""
    page = editor(dz("d", {**DREIECK, "typed": [[0, 3, 159]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Dreieck 1 geht über den Zahlenraum bis 20 hinaus.")


def test_a_click_into_a_field_selects_its_whole_number(editor):
    """#560 (PR #565): 19 in a field, a click into it and 5 typed give 5, not 195."""
    client = user()
    page = editor(dz("d", {**DREIECK, "typed": [[0, 0, 19]]}), client=client)
    pick(page, "d")
    expect(field(page, INNER_TOP)).to_have_value("19")
    field(page, INNER_TOP).click()
    step(page, lambda: page.keyboard.type("5"))
    expect(field(page, INNER_TOP)).to_have_value("5")
