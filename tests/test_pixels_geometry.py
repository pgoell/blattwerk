"""Table lines, cell boxes, a row of text and a picture's edge lie where they print."""

import pytest
from pixels import (
    LOADED,
    dark,
    grey,
    runs,
)
from playwright.sync_api import expect
from test_pixels import (
    EDGE,
    LONG,
    PLACES,
    ROWS,
    at,
    blocks,
    fuller,
    lower,
    right_edge,
)
from ui import (
    TEXT,
    pick,
    sheet,
    user,
)

from blattwerk import pdf


def test_a_tables_lines_are_as_wide_and_as_dark_as_they_print(browser, server):
    """A4"""
    client = user()
    page = blocks("table", client)
    screen, printed = grey(browser, server, client, page)
    x, y, w, h = (page[0][side] for side in "xywh")
    # Clear of the letters: a strip down the first column and one along the first row.
    for part, down in (
        ((x + 10, y - 3, x + 14, y + h + 3), True),
        ((x - 3, y + 1, x + w + 3, y + 2), False),
    ):
        shown, paper = (runs(dark(picture, part, down)) for picture in (screen, printed))
        assert len(shown) == len(paper) == 3
        for (_, darkest, ink), (_, on_paper, printed_ink) in zip(shown, paper, strict=True):
            # The ink is the line's width in pixels times its darkness. pdfium fills every pixel a
            # line touches, half a pixel more than the browser draws: 2.2 against 1.8.
            assert abs(darkest - on_paper) < 0.05, (darkest, on_paper)
            assert abs(ink - printed_ink) < 0.5, (ink, printed_ink)


def test_a_tables_cells_lie_where_they_print(browser, server):
    """I7"""
    client = user()
    mine = sheet(client, fuller("table", client))["id"]
    # A sharp screen, as an iPad has: there WebKit rounds a border under a pixel down to half.
    context = browser.new_context(device_scale_factor=2)
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    shown = context.new_page()
    shown.goto(f"{server}/blatt/{mine}")
    shown.locator('main.editor[data-ready="1"]').wait_for()
    # The page that prints, at one pixel to a pixel as Chromium prints it.
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    places = [tab.evaluate(f"{LOADED}.then({PLACES})") for tab in (shown, paper)]
    assert len(places[0]) == 32
    for here, there in zip(*places, strict=True):
        assert here == pytest.approx(there, abs=0.01)

    pick(shown, "b60")
    shown.keyboard.press("Enter")
    field = shown.locator(".table textarea")
    expect(field).to_be_focused()
    (left, top, right, low), cell = (
        (b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"])
        for b in (field.bounding_box(), shown.locator('[data-cell="0"]').bounding_box())
    )
    assert cell[0] < left < right < cell[2] and cell[1] < top < low < cell[3]
    paper.close()
    context.close()


@pytest.mark.parametrize(
    "look", [{"font": "sas", "bold": True}, {}], ids=["school script", "andika"]
)
def test_a_row_of_text_lies_as_low_as_it_prints(browser, server, look):
    """A5"""
    client = user()
    page = [at("text", {**TEXT, "text": LONG, **look}, h=120)]
    screen, printed = grey(browser, server, client, page)
    found = lower(screen, printed, page[0])
    assert max(abs(by) for by in found) < ROWS, found


def test_a_picture_ends_where_it_prints(browser, server):
    """A6"""
    client = user()
    page = blocks("picture", client)
    screen, printed = (right_edge(image, page[0]) for image in grey(browser, server, client, page))
    assert abs(screen - printed) < EDGE, (screen, printed)
