"""Big numbers in a maths block: a gap between the groups of three from 10 000 on (#454).

A whole part of five digits or more is set in groups of three from the right, with a narrow
no-break space between the groups: 270 091, 1 000 000. A number up to 9999 has no gap, and the
written format keeps one digit to a square.
"""

import re

import pytest
from playwright.sync_api import expect
from test_compare import shown
from test_decimals import true_line
from test_feed_print import printed, sheet_id
from test_fix_mix import key
from ui import at, box, maths, pick, tool, user

GAP = "\N{NARROW NO-BREAK SPACE}"
NUMBER = re.compile(rf"\d+(?:{GAP}\d+)*(?:,\d+)?")
# A whole part of up to four digits has no gap; from five on it is in groups of three.
GROUPED = re.compile(rf"(?:\d{{1,4}}|\d{{1,3}}(?:{GAP}\d{{3}})+)(?:,\d+)?")


def numbers_of(texts):
    """Every number in the texts, a gap kept inside it: 270 091 is one number."""
    return [m.group() for text in texts for m in NUMBER.finditer(text)]


@pytest.mark.parametrize("format", ["row", "gap", "compare"])
def test_big_numbers_show_a_gap_between_the_thousands(editor, format):
    """#454: Every number of the sheet is grouped in threes, and some number has a gap."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format=format, ops=["+", "-"], max=1_000_000, count=20)),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(20)
    texts = at(page, "m").locator(".maths > div").all_text_contents()
    numbers = numbers_of(texts)
    assert numbers and all(GROUPED.fullmatch(n) for n in numbers)
    assert any(GAP in n for n in numbers)


@pytest.mark.parametrize("format", ["row", "gap", "compare"])
def test_the_pdf_and_the_key_show_the_same_gaps(editor, browser, server, format):
    """#454: The print page and the key show the editor's texts, gaps kept, with right results."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format=format, ops=["+", "-"], max=1_000_000, count=12)),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    unsolved = shown(at(page, "m"))
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    assert shown(paper) == unsolved
    assert any(GAP in n for n in numbers_of(paper.locator(".maths > div").all_text_contents()))
    paper.context.close()
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator(".maths.solved")).to_be_visible()
    solved = shown(at(page, "m"))
    paper = key(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    assert shown(paper) == solved
    if format != "compare":
        # true_line splits on every space, so a gap goes first: 592 921 is one number.
        lines = [
            " ".join(text.replace(GAP, "").split())
            for text in paper.locator(".maths > div").all_text_contents()
        ]
        assert all(true_line(line) for line in lines), lines
    paper.context.close()


@pytest.mark.parametrize("top", [1000, 10_000])
def test_numbers_up_to_9999_have_no_gap(editor, top):
    """#454: A number of four digits or fewer has no gap, whatever the room."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="row", ops=["+", "-"], max=top, count=12)),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    numbers = numbers_of(at(page, "m").locator(".maths > div").all_text_contents())
    short = [n for n in numbers if len(n.replace(GAP, "").split(",")[0]) <= 4]
    assert short and all(GAP not in n for n in short)


def test_the_gap_line_holds_a_grouped_number(editor, browser, server):
    """#454: In Lücke with max 1 000 000, no gap on the key is narrower than the number in it."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="gap", ops=["+", "-"], max=1_000_000, count=12)),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    paper = key(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    assert any(GAP in text for text in paper.locator(".maths u").all_text_contents())
    widths = paper.locator(".maths u").evaluate_all(
        "els => els.map((el) => [el.scrollWidth, el.clientWidth])"
    )
    assert widths and all(scroll <= box_width + 0.5 for scroll, box_width in widths)
    paper.context.close()


def test_the_written_format_keeps_a_digit_to_a_square(editor):
    """#454: Schriftlich stays as it is: no gap in any square of the grid."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="written", ops=["*", "/"], max=1_000_000, count=12)),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div").first).to_be_visible()
    squares = at(page, "m").locator("svg text").all_text_contents()
    assert squares and all(GAP not in square for square in squares)
