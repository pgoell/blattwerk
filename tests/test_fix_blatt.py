"""A regression: the small picture of a Knickblatt on Meine Blätter draws its words under one another."""

# The fixture `window` is imported, and each test names it as its argument.
# ruff: noqa: F811

from itertools import pairwise

from playwright.sync_api import expect
from test_knick import KNICK
from test_loading import window  # noqa: F401
from ui import box, sheet

WORDS = ["Hund", "Katze", "Maus"]
BLATT = ["text", "name", "ruling", "ruling", "ruling"]


def test_the_list_shows_a_knickblatts_words_under_one_another(window, server):
    """#426 The small picture on Meine Blätter shows a Knickblatt's words under one another."""
    page, client = window()
    sheet(client, [box("k", "ruling", KNICK, w=180, h=69)], words=WORDS)
    page.goto(server)
    expect(page.locator(".sheets li")).to_have_count(1)
    rows = page.locator(".sheets .written.listed .row")
    expect(rows).to_have_count(len(WORDS))
    spots = rows.evaluate_all(
        "els => els.map((el) => { const r = el.getBoundingClientRect(); return [r.top, r.left]; })"
    )
    tops = [top for top, _ in spots]
    lefts = [left for _, left in spots]
    assert all(a < b for a, b in pairwise(tops)), tops
    assert max(lefts) - min(lefts) <= 0.5, lefts
