"""The preview of "Varianten drucken" shows each page whole, not cut at the preview's edges.

The sheets here carry a wide text on each upright page, so that a page drawn too wide for its place
shows at its right side. A Quer page is one the sheet has turned.
"""

import pytest
from playwright.sync_api import expect
from ui import TEXT, box, user

UPRIGHT = 210 / 297
QUER = 297 / 210
WIDE = "Mathetest Klasse 2: Rechnen bis zwanzig, Zahlenmauern und Uhren, zum Schluss ENDE"


def wide(name, y=20):
    """A text on a page's left that reaches 195 mm, the page's right edge less 15."""
    return box(name, "text", {**TEXT, "text": WIDE}, x=15, y=y, w=180, h=40)


def open_preview(page):
    """Opens the dialog Varianten drucken from the panel Ansicht."""
    page.get_by_role("tab", name="Ansicht").click()
    page.locator(".panel").get_by_role("button", name="Varianten drucken", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()


@pytest.mark.parametrize(
    "landscapes",
    [
        [False, False, True],
        [False, True],
    ],
    ids=["three-one-quer", "two-one-quer"],
)
def test_each_page_of_the_preview_shows_whole(editor, landscapes):
    """Asked #616: the upright pages are not cut at the right, and each keeps its page's shape."""
    first, *rest = landscapes
    pages = [{"blocks": [wide(f"p{n}")], "landscape": flag} for n, flag in enumerate(rest, start=2)]
    page = editor(wide("p1"), client=user(), pages=pages)
    open_preview(page)
    preview = page.get_by_role("dialog").locator(".preview")
    papers = preview.locator(".paper")
    expect(papers).to_have_count(len(landscapes))
    frame = preview.bounding_box()
    for n, flag in enumerate([first, *rest]):
        paper = papers.nth(n).bounding_box()
        assert frame["x"] - 0.5 <= paper["x"], n
        assert paper["x"] + paper["width"] <= frame["x"] + frame["width"] + 0.5, n
        assert frame["y"] - 0.5 <= paper["y"], n
        assert paper["y"] + paper["height"] <= frame["y"] + frame["height"] + 0.5, n
        expected = QUER if flag else UPRIGHT
        assert abs(paper["width"] / paper["height"] / expected - 1) < 0.02, n


# Own case: one Quer page alone shows whole too.
def test_one_quer_page_alone_shows_whole(editor):
    page = editor(box("a", "text", {**TEXT, "text": WIDE}, x=15, y=20, w=260, h=40))
    page.get_by_role("tab", name="Ansicht").click()
    panel = page.locator(".panel")
    panel.get_by_role("button", name="Nur diese Seite").click()
    panel.get_by_role("button", name="Quer", exact=True).click()
    open_preview(page)
    preview = page.get_by_role("dialog").locator(".preview")
    paper = preview.locator(".paper").bounding_box()
    frame = preview.bounding_box()
    assert frame["x"] - 0.5 <= paper["x"]
    assert paper["x"] + paper["width"] <= frame["x"] + frame["width"] + 0.5
    assert abs(paper["width"] / paper["height"] / QUER - 1) < 0.02


def test_eight_upright_pages_stay_readable_and_scroll_sideways(editor):
    """Asked #616 review: a page is at least 120 px wide on screen; the row scrolls for the rest."""
    pages = [{"blocks": [wide(f"p{n}")]} for n in range(2, 9)]
    page = editor(wide("p1"), client=user(), pages=pages)
    open_preview(page)
    preview = page.get_by_role("dialog").locator(".preview")
    papers = preview.locator(".paper")
    expect(papers).to_have_count(8)
    for n in range(8):
        paper = papers.nth(n).bounding_box()
        assert paper["width"] >= 119, n
        assert abs(paper["width"] / paper["height"] / UPRIGHT - 1) < 0.02, n
    assert preview.evaluate("e => e.scrollWidth > e.clientWidth")


def test_forty_pages_each_keep_a_width(editor):
    """Asked #616 review: with many pages no page is drawn with a negative width."""
    page = editor(wide("p1"), client=user(), pages=[{"blocks": []} for _ in range(39)])
    open_preview(page)
    papers = page.get_by_role("dialog").locator(".preview .paper")
    expect(papers).to_have_count(40)
    for n in range(40):
        assert papers.nth(n).bounding_box()["width"] >= 119, n
