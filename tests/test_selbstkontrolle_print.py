"""The Selbstkontrolle on paper: the turned and folded layouts, a lost link, the answer key and
the letter boxes of a sheet without the block.

The docstrings name what each test proves. The pupils' print is `printed`, the key `key_print`.
"""

from playwright.sync_api import expect
from test_feed_print import printed
from test_selbstkontrolle import SK, SUMS, WORDED
from test_suchsel_print import key_print
from ui import box, maths, sheet, user

RED = "rgb(192, 57, 43)"


def turned_sheet(client, turn):
    """A maths block and a Selbstkontrolle that links it, turned as `turn` says."""
    return sheet(
        client,
        [
            box("m", "maths", maths(client, exercises=SUMS), z=1, w=180, h=20),
            box("s", "selbstkontrolle", {**SK, "links": ["m"], "turn": turn}, z=2, w=180, h=60),
        ],
    )["id"]


def test_upside_turns_the_content_by_180_degrees_on_paper(browser, server):
    """Drucken Auf dem Kopf: the inner part of the block is turned by 180 degrees."""
    client = user()
    paper = printed(browser, server, turned_sheet(client, "upside"))
    inner = paper.locator("div.selbstkontrolle div.inner").first
    assert inner.evaluate("el => getComputedStyle(el).transform").startswith("matrix(-1,")
    paper.context.close()


def test_fold_puts_the_fold_line_at_the_top_edge_and_turns_the_content(browser, server):
    """Mit Knicklinie: the dashed fold lies along the block's top edge, within 1 px, and the
    content under it is turned by 180 degrees."""
    client = user()
    paper = printed(browser, server, turned_sheet(client, "fold"))
    block = paper.locator("div.selbstkontrolle").first
    gap = block.locator("div.fold").bounding_box()["y"] - block.bounding_box()["y"]
    assert abs(gap) <= 1
    inner = block.locator("div.inner")
    assert inner.evaluate("el => getComputedStyle(el).transform").startswith("matrix(-1,")
    paper.context.close()


def test_a_lost_link_prints_no_result_and_no_hint(browser, server):
    """A link to a block the sheet no longer has: the print shows no result and no hint."""
    client = user()
    mine = sheet(
        client,
        [box("s", "selbstkontrolle", {**SK, "links": ["gone"]}, z=1, w=180, h=60)],
    )["id"]
    paper = printed(browser, server, mine)
    expect(paper.locator("div.selbstkontrolle")).to_have_count(1)
    assert paper.locator("div.selbstkontrolle li").count() == 0
    assert paper.locator("div.selbstkontrolle p.hint").count() == 0
    paper.context.close()


def test_the_key_writes_the_word_in_red_and_each_letter_in_its_box(browser, server):
    """Lösungswort ABA: the key prints the word ABA in red, and the maths block's three letter
    boxes hold A, B and A."""
    client = user()
    mine = sheet(
        client,
        [
            box("m", "maths", maths(client, exercises=WORDED), z=1, w=180, h=20),
            box(
                "s",
                "selbstkontrolle",
                {**SK, "form": "word", "word": "ABA", "links": ["m"]},
                z=2,
                w=180,
                h=60,
            ),
        ],
    )["id"]
    key = key_print(browser, server, mine)
    answer = key.locator("div.selbstkontrolle p.answer")
    assert answer.text_content().strip() == "ABA"
    assert answer.evaluate("e => getComputedStyle(e).color") == RED
    assert key.locator(".letter").all_text_contents() == ["A", "B", "A"]
    key.context.close()


def test_a_sheet_without_the_block_prints_no_letter_box(browser, server):
    """An old sheet: a maths block that no Selbstkontrolle links has no letter box on paper."""
    client = user()
    mine = sheet(client, [box("m", "maths", maths(client, exercises=SUMS), w=180, h=20)])["id"]
    paper = printed(browser, server, mine)
    assert paper.locator(".letter").count() == 0
    paper.context.close()
