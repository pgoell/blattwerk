"""The thin lines of the school blocks and the words of a Punkte box, screen against print."""

import pytest
from pixels import dark, grey, runs
from ui import BROWSER, box, maths, user

# Each block 120 mm wide in the middle of the page, with the strips that hold its lines and no
# letter: the part in mm, whether its rows are read, and how many lines cross it.
NAME = box("b0", "name", {}, x=45, y=100, w=120, h=10), [((70, 97, 90, 113), True, 1)]
POINTS = (
    box("b0", "points", {"max": 10}, x=45, y=100, w=120, h=10),
    [((50, 97, 60, 113), True, 2), ((42, 104, 48, 106), False, 1)],
)


def gap(client):
    # At 12 pt, as the Name and the Punkte block are set: .06em is just under a pixel there. The
    # strip lies in the first sum's gap.
    block = box("b0", "maths", maths(client, size=12), x=45, y=100, w=120, h=12)
    return block, [((61, 98, 67, 114), True, 1)]


def as_wide_and_as_dark(browser, server, client, block, strips):
    screen, printed = grey(browser, server, client, [block])
    for part, down, lines in strips:
        shown, paper = (runs(dark(picture, part, down)) for picture in (screen, printed))
        assert len(shown) == len(paper) == lines, (shown, paper)
        for (_, darkest, ink), (_, on_paper, printed_ink) in zip(shown, paper, strict=True):
            # The ink is the line's width in pixels times its darkness. pdfium fills every pixel a
            # line touches, half a pixel more than the browser draws.
            assert abs(darkest - on_paper) < 0.05, (darkest, on_paper)
            assert abs(ink - printed_ink) < 0.5, (ink, printed_ink)


def test_a_names_line_is_as_wide_and_as_dark_as_it_prints(browser, server):
    """A3"""
    as_wide_and_as_dark(browser, server, user(), *NAME)


def test_a_points_box_is_as_wide_and_as_dark_as_it_prints(browser, server):
    """A4"""
    as_wide_and_as_dark(browser, server, user(), *POINTS)


def test_a_maths_gaps_line_is_as_wide_and_as_dark_as_it_prints(browser, server):
    """I4"""
    client = user()
    as_wide_and_as_dark(browser, server, client, *gap(client))


# How far the words may lie from the print, in pixels of pictures twice the page's size, eight to
# a millimetre. WebKit lays a row of Andika up to 2.5 lower than Chromium prints it (ROWS in
# test_pixels.py), by font heights it rounds its own way.
WORDS = 3 if BROWSER == "webkit" else 1


# The box of tests/corpus/sheet-4.json, 12 mm high, and the one a new Punkte block has.
@pytest.mark.parametrize("h", [12, 10])
def test_a_points_boxs_words_lie_as_low_as_they_print(browser, server, h):
    """A9"""
    client = user()
    x, y, w = 155, 168.5, 40
    pictures = grey(browser, server, client, [box("b0", "points", {"max": 10}, x=x, y=y, w=w, h=h)])
    # The words' place is where their ink has its middle, inside the box's border.
    inks = (dark(picture, (x + 5, y + 1, x + w - 1, y + h - 1)) for picture in pictures)
    screen, printed = (sum(i * v for i, v in enumerate(ink)) / sum(ink) for ink in inks)
    assert abs(screen - printed) < WORDS, (screen, printed)
