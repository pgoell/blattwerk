"""The Suchsel on paper: the pupils' sheet and the answer key print the grid that the editor shows.

The docstrings name the lines of the checklist that each test proves.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed_print import pdf_text, printed, sheet_id
from test_suchsel import SUCHSEL, WORDS, grid, rings
from ui import at, box, tool, user


def key_print(browser, server, mine):
    """The print page of the answer key: the page with ?loesungen. The caller closes its context."""
    paper = printed(browser, server, mine)
    paper.goto(f"{server}/druck/{mine}?loesungen")
    paper.wait_for_selector("body.ready", state="attached")
    return paper


def test_the_pupils_print_has_the_editors_grid_and_no_rings(editor, browser, server):
    """A15: the print page shows the grid the editor shows, and no ring."""
    client = user()
    page = editor(box("s", "suchsel", SUCHSEL, w=120, h=140), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".suchsel text[data-at]")).to_have_count(100)
    assert grid(paper.locator(".suchsel")) == grid(at(page, "s"))
    expect(paper.locator("rect.ring")).to_have_count(0)
    paper.context.close()


def test_the_key_print_rings_the_words_where_the_editor_does(editor, browser, server):
    """A15: the answer key's print page shows the same grid, and six rings in the same places."""
    client = user()
    page = editor(box("s", "suchsel", SUCHSEL, w=120, h=140), client=client)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(6)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator("rect.ring")).to_have_count(6)
    assert grid(paper.locator(".suchsel")) == grid(at(page, "s"))
    assert sorted(rings(paper.locator(".suchsel")), key=str) == sorted(
        rings(at(page, "s")), key=str
    )
    paper.context.close()


@pytest.mark.parametrize(
    "show, shown",
    [("words", WORDS), ("count", ["Finde6Wörter."])],
    ids=["words", "count"],
)
def test_the_pdf_lists_the_words_or_counts_them(editor, server, show, shown):
    """A15: the PDF holds the word list, or "Finde 6 Wörter." with "Nur Anzahl"."""
    client = user()
    page = editor(box("s", "suchsel", {**SUCHSEL, "show": show}, w=120, h=140), client=client)
    text = re.sub(r"\s", "", pdf_text(server, client, sheet_id(page)))
    for word in shown:
        assert word in text


def test_the_answer_key_pdf_is_made_and_holds_the_words(editor, server):
    """A15: the PDF of the answer key answers, and holds the words of the list."""
    client = user()
    page = editor(box("s", "suchsel", SUCHSEL, w=120, h=140), client=client)
    text = re.sub(r"\s", "", pdf_text(server, client, sheet_id(page), solved=True))
    for word in WORDS:
        assert word in text


def test_the_print_counts_only_the_words_that_fit(editor, browser, server):
    """I5: the print says "Finde 2 Wörter." when one of three words does not fit the grid."""
    client = user()
    props = {
        **SUCHSEL,
        "cols": 6,
        "rows": 6,
        "ways": "across",
        "show": "count",
        "words": ["Schmetterling", "Hund", "Maus"],
    }
    page = editor(box("s", "suchsel", props, w=120, h=140), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator("p.found")).to_have_text("Finde 2 Wörter.")
    paper.context.close()
