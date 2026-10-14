"""A Zahlenmauer whose typed numbers allow no wall, or a number above the Zahlenraum: the answer
key, the panel's hints and the number field's selection. Issues #559, #560.

The docstrings name the issue and the PR that brought the fault in.
"""

from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import step
from test_suchsel_print import key_print
from test_zahlenmauer import props_of
from ui import box, doc, pick, user

WALL = {
    "base": 3,
    "count": 4,
    "columns": 2,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 7,
}
# The first wall's three base stones 1, 1, 1 and its top 5 allow no wall (#559).
WRONG = [[0, 0, 1], [0, 1, 1], [0, 2, 1], [0, 5, 5]]
ONE_STONE = "Zahl im Stein 1 der Reihe 1"
TOP = "Zahl im Stein 1 der Reihe 3"


def zw(name, props):
    return box(name, "zahlenmauer", props, w=180, h=60)


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def test_the_key_prints_no_made_up_numbers_for_a_wall_that_allow_none(editor, browser, server):
    """#559 (PR #548): the key shows no answer text in the wrong wall, the others keep theirs."""
    client = user()
    page = editor(zw("w", {**WALL, "typed": WRONG}), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenmauer .wall.wrong")).to_have_count(1)
    assert paper.locator(".zahlenmauer .wall.wrong text.answer").count() == 0
    assert paper.locator(".zahlenmauer .wall:not(.wrong) text.answer").count() == 9
    paper.context.close()


def test_the_panel_names_every_wall_that_allow_none(editor):
    """#559 (PR #548): a wrong wall 2 gives its hint while the panel shows Mauer 1."""
    page = editor(zw("w", {**WALL, "typed": [[1, 0, 1], [1, 1, 1], [1, 2, 1], [1, 5, 5]]}))
    pick(page, "w")
    expect(hint(page)).to_have_text("Mauer 2 geht mit diesen Zahlen nicht auf.")


def test_a_number_above_the_zahlenraum_gives_the_hint(editor):
    """#560 (PR #548): 159 in the top of a bis 20 wall names the Zahlenraum, the solver stays."""
    page = editor(zw("w", {**WALL, "typed": [[0, 5, 159]]}))
    pick(page, "w")
    expect(hint(page)).to_have_text("Mauer 1 geht über den Zahlenraum bis 20 hinaus.")


def test_one_undo_brings_back_the_base_stones_after_a_typed_top(editor):
    """#560 (PR #548): a top 159 changes the base stones; one Ctrl+Z after leaving the field brings
    the old base back."""
    client = user()
    page = editor(zw("w", WALL), client=client)
    pick(page, "w")
    base = [field(page, f"Zahl im Stein {c} der Reihe 1").input_value() for c in (1, 2, 3)]
    step(page, lambda: field(page, TOP).fill("159"))
    expect(hint(page)).to_have_text("Mauer 1 geht über den Zahlenraum bis 20 hinaus.")
    page.locator(".panel").get_by_role("heading", name="Zahlenmauer", exact=True).click()
    page.keyboard.press("Control+z")
    assert [field(page, f"Zahl im Stein {c} der Reihe 1").input_value() for c in (1, 2, 3)] == base
    assert "typed" not in props_of(doc(page, client))


def test_a_click_into_a_stone_selects_its_whole_number(editor):
    """#560 (PR #548): 19 in a stone, a click into it and 5 typed give 5, not 195."""
    client = user()
    page = editor(zw("w", {**WALL, "typed": [[0, 5, 19]]}), client=client)
    pick(page, "w")
    expect(field(page, TOP)).to_have_value("19")
    field(page, TOP).click()
    step(page, lambda: page.keyboard.type("5"))
    expect(field(page, TOP)).to_have_value("5")
