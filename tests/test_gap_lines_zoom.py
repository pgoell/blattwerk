"""A gap's line shows on the screen at the small zooms of the opening page, as the print draws it
(issue #399, a regression of PR #387)."""

import io
import re

import pytest
from PIL import Image
from playwright.sync_api import expect
from ui import TEXT, at, box

SENTENCE = (
    "Am Abend fahren Oma und Opa mit dem Skateboard in den Garten. "
    "Die Familie isst Spiegeleier und Erdbeeren. Der Igel schläft unter der Bank."
)
# Every fifth word is a gap: und, in, isst and Igel.
EVERY_FIFTH = {
    **TEXT,
    "text": SENTENCE,
    "size": 18,
    "rich": [
        {
            "runs": [
                run
                for i, word in enumerate(SENTENCE.split(" "))
                for run in ([{"text": " "}] if i else [])
                + [{"text": word, "gap": True} if (i + 1) % 5 == 0 else {"text": word}]
            ]
        }
    ],
}
# The school script of the teachers' screenshots, next to the print face.
FONTS = ["andika", "va"]
# The opening zoom at 1280 by 1024 reads 88 % in Chromium, 90 % in WebKit; Ganze Seite reads 77 %.
# The percent button shows the page's size, so the test takes those few points of difference.
OPENING = r"^(8[6-9]|90)\s*%"
FIT = r"^7[5-9]\s*%"
ZOOMS = ["opening", "Ganze Seite"]

# A line is clearly dark: the editor draws it in #222, a gap's words in grey #999 (153).
DARK = 200


def percent(page):
    return int(page.locator("button.zoom").first.inner_text().split()[0])


def line_shows(locator):
    """Whether the lower half of the element holds a row that is dark across 80 % of its width.

    A row of letters never fills that much, so only a line can.
    """
    # The window cut at the element's place, not the element's own screenshot: that one scrolls the
    # desk first, and WebKit then cuts where the element was.
    # The place is read once it has stood still for five frames: a new window size or zoom moves
    # the page a frame or two later.
    locator.scroll_into_view_if_needed()
    cut = locator.evaluate("""async el => {
        const place = () => {
            const r = el.getBoundingClientRect();
            return [r.x, r.y, r.width, r.height];
        };
        let [was, still] = [place(), 0];
        while (still < 5) {
            await new Promise(requestAnimationFrame);
            const now = place();
            still = now.every((n, i) => n === was[i]) ? still + 1 : 0;
            was = now;
        }
        return { x: was[0], y: was[1], width: was[2], height: was[3] };
    }""")
    shot = Image.open(io.BytesIO(locator.page.screenshot(clip=cut))).convert("L")
    grey, (width, height) = shot.tobytes(), shot.size
    return any(
        # Less one pixel: the cut starts and ends on a part of a pixel, which counts for a gap that
        # is five pixels wide at 23 %.
        sum(grey[y * width + x] < DARK for x in range(width)) >= 0.8 * width - 1
        for y in range(height // 2, height)
    )


def at_zoom(page, zoom):
    """The sheet at the zoom of the issue: a window of 1280 by 1024, then the zoom's button."""
    page.set_viewport_size({"width": 1280, "height": 1024})
    if zoom == "opening":
        expect(page.locator("button.zoom").first).to_have_text(re.compile(OPENING))
    else:
        page.get_by_label(zoom, exact=True).first.click()
        expect(page.locator("button.zoom").first).to_have_text(re.compile(FIT))
    page.evaluate("document.fonts.ready.then(() => 0)")


@pytest.mark.parametrize("font", FONTS)
@pytest.mark.parametrize("gap_width", [None, 30], ids=["plain", "gapWidth"])
@pytest.mark.parametrize("zoom", list(ZOOMS))
def test_every_gap_of_a_text_shows_its_line_at_small_zoom(editor, zoom, gap_width, font):
    """A1: each gap of the text shows its line on screen, at the opening zoom and Ganze Seite."""
    props = {**EVERY_FIFTH, "font": font}
    if gap_width:
        props["gapWidth"] = gap_width
    # At 20 mm from the top a line lies on a fraction of a pixel, which is when the screen drops it.
    # High enough for its three rows: a box cuts the rows it has no room for.
    page = editor(box("a", "text", props, w=170, y=20, h=40))
    at_zoom(page, zoom)
    gaps = at(page, "a").locator(".gap")
    assert gaps.count() == 4
    for i in range(4):
        assert line_shows(gaps.nth(i)), f"gap {i} shows no line at {zoom}"


def test_a_table_gap_cell_and_a_scrambled_words_line_show_at_small_zoom(editor):
    """I1: a table's gap cell and each scrambled word's line show their line at 77 % and 88 %."""
    table = {
        "cells": [["Hund", "Katze"], ["Maus", "Ei"]],
        "cols": [1, 1],
        "size": 14,
        "align": "center",
        "gaps": [[True, False], [False, True]],
        "gapWidth": 30,
    }
    under = {**TEXT, "text": "Hund bellt Katze miaut", "size": 18, "mix": 7, "mixLine": "under"}
    after = {**TEXT, "text": "Der Igel schläft", "size": 18, "mix": 7, "mixLine": "after"}
    page = editor(
        box("t", "table", table, y=20),
        box("m1", "text", under, z=2, y=45),
        box("m2", "text", after, z=3, y=70),
    )
    for zoom in ZOOMS:
        at_zoom(page, zoom)
        cells = at(page, "t").locator(".gap")
        assert cells.count() == 2
        for i in range(2):
            assert line_shows(cells.nth(i)), f"table gap {i} at {zoom}"
        for name in ("m1", "m2"):
            lines = at(page, name).locator(".gap.line")
            assert lines.count() > 0
            for i in range(lines.count()):
                assert line_shows(lines.nth(i)), f"{name} line {i} at {zoom}"


def test_a_gaps_line_shows_at_every_step_of_the_zoom_buttons(editor):
    """I2: Kleiner to the bottom, then Größer step by step to the top: each gap shows a line."""
    page = editor(box("a", "text", EVERY_FIFTH, w=170, y=20, h=40))
    page.set_viewport_size({"width": 1280, "height": 1024})
    expect(page.locator("button.zoom").first).to_have_text(re.compile(OPENING))
    for _ in range(12):
        page.get_by_label("Kleiner", exact=True).first.click()
    # A quarter of the opening zoom, 88 %.
    expect(page.locator("button.zoom").first).to_have_text(re.compile(r"^2[1-4]\s*%"))
    shown = []
    for _ in range(20):
        page.evaluate("document.fonts.ready.then(() => 0)")
        gaps = at(page, "a").locator(".gap")
        for i in range(gaps.count()):
            assert line_shows(gaps.nth(i)), f"gap {i} shows no line at {percent(page)} %"
        shown.append(percent(page))
        if shown[-1] >= 350:
            break
        before = shown[-1]
        page.get_by_label("Größer", exact=True).first.click()
        expect(page.locator("button.zoom").first).not_to_have_text(re.compile(rf"^{before}\s*%"))
    # The top zoom is four times the opening one.
    assert shown[-1] >= 350, shown
