"""Two Nachkommastellen keep the last 0 on every number and result; one place drops it (#455)."""

import re

import pytest
from playwright.sync_api import expect
from test_compare import shown
from test_feed_print import printed, sheet_id
from test_fix_mix import key
from test_thousands import GAP, numbers_of
from ui import at, box, maths, pick, tool, user


def show_key(page, count):
    """Turns the key on in the editor and waits for its tasks; gives the tasks' texts."""
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator(".maths.solved")).to_be_visible()
    expect(at(page, "m").locator(".maths > div")).to_have_count(count)
    return at(page, "m").locator(".maths > div").all_text_contents()


@pytest.mark.parametrize("format", ["row", "gap"])
def test_two_places_show_on_every_number_and_result(editor, format):
    """#455: With 2 places each number and each result reads like 17,30 or 7,00."""
    client = user()
    page = editor(
        box(
            "m",
            "maths",
            maths(client, format=format, ops=["+", "-"], max=100, count=12, decimals=2),
        ),
        client=client,
    )
    pick(page, "m")
    numbers = numbers_of(show_key(page, 12))
    assert numbers and all(re.fullmatch(r"\d+,\d\d", n.replace(GAP, "")) for n in numbers)


def test_one_place_drops_a_zero_as_before(editor):
    """#455: With 1 place a whole result stays a whole number: 3 and not 3,0."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-"], max=100, count=12, decimals=1)),
        client=client,
    )
    pick(page, "m")
    numbers = numbers_of(show_key(page, 12))
    assert any("," in n for n in numbers)
    assert not any(n.endswith(",0") for n in numbers)


def test_the_pdf_and_the_key_show_two_places(editor, browser, server):
    """#455: The print page and the key show the editor's tasks with their two places."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-"], max=100, count=12, decimals=2)),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    unsolved = shown(at(page, "m"))
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    assert shown(paper) == unsolved
    paper.context.close()
    show_key(page, 12)
    solved = shown(at(page, "m"))
    paper = key(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    assert shown(paper) == solved
    paper.context.close()
