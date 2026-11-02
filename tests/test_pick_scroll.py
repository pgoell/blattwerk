"""A picked block stays picked when a wheel or a zoom brings another page into view (#815).

The selection lives on the page in use. A wheel used to hand that page on at once, so the
Format panel emptied. A zoom already waited and kept a picked block's page; the wheel does too.
"""

import re

from playwright.sync_api import expect
from test_page_lost import expect_out_of_view, zoomed_onto_page_two
from ui import RECT, box, pick

ON = re.compile(r"\bon\b")
PLACE = """el => {
    const s = el.closest('.sheet').getBoundingClientRect();
    return el.getBoundingClientRect().left - s.left;
}"""


def two(editor):
    """A box on page 1, an empty page 2. Page 1 is in use."""
    return editor(box("r", "shape", RECT), pages=[{"blocks": []}])


def wheel_to_page_two(page):
    """Turns the wheel over the middle of the desk until page 1 has left the view."""
    spot = page.locator(".desk").bounding_box()
    page.mouse.move(spot["x"] + spot["width"] / 2, spot["y"] + spot["height"] / 2)
    page.mouse.wheel(0, 5000)
    expect_out_of_view(page, 0)


def still_the_box(page):
    """The box is picked, the Format panel still names it, and page 1 is still in use."""
    expect(page.locator('.block[data-id="r"]')).to_have_class("block sel")
    expect(page.locator(".panel .what")).to_have_text("Form")
    expect(page.locator('.sheet[data-page="0"]')).to_have_class(ON)


def test_a_picked_box_stays_picked_when_the_wheel_brings_page_2(editor):
    """#815: page 2 fills the view, the box on page 1 stays picked, and an arrow still nudges it."""
    page = two(editor)
    pick(page, "r")
    expect(page.locator(".panel .what")).to_have_text("Form")
    wheel_to_page_two(page)
    still_the_box(page)
    before = page.locator('.block[data-id="r"]').evaluate(PLACE)
    page.keyboard.press("ArrowRight")
    # An arrow still nudges the box: with the pick gone it would scroll the desk instead.
    page.wait_for_function(
        """([was]) => {
            const el = document.querySelector('.block[data-id="r"]');
            const s = el.closest('.sheet').getBoundingClientRect();
            return el.getBoundingClientRect().left - s.left > was + 1;
        }""",
        arg=[before],
    )
    # A click on the empty page in view ends the pick, as a click elsewhere does.
    page.locator('.sheet[data-page="1"]').click(position={"x": 40, "y": 40})
    expect(page.locator(".block.sel")).to_have_count(0)
    expect(page.locator('.sheet[data-page="1"]')).to_have_class(ON)
    expect(page.locator(".panel .what")).to_have_count(0)


def test_a_picked_box_stays_picked_when_a_zoom_hides_its_page(editor):
    """#815: Ctrl and the wheel over page 2, until page 1 has left the view, leave the box picked."""
    page = two(editor)
    pick(page, "r")
    zoomed_onto_page_two(page)
    still_the_box(page)
