"""The Hunderterfeld's grid of 100 squares in the format panel fits the panel at any width (#575).

The docstrings name what each test proves.
"""

from playwright.sync_api import expect
from test_bar import resize
from test_gaps import step
from test_hunderterfeld import TAFEL, feld, field, props_of, square
from ui import at, bar, box, doc, pick, user


def inside(outer, inner):
    """Whether the box inner lies within the box outer, sideways."""
    return outer["x"] <= inner["x"] and inner["x"] + inner["width"] <= outer["x"] + outer["width"]


def no_sideways_scroll(page):
    return page.locator(".panel").evaluate("el => el.scrollWidth <= el.clientWidth")


def client_box(page):
    """The panel's content box, inside its border and padding: what a square must lie in.

    Headless Chromium hides the scroll bar, so the width is taken from the box, not from the bar.
    """
    return page.locator(".panel").evaluate(
        """el => {
          const r = el.getBoundingClientRect(), s = getComputedStyle(el);
          const left = parseFloat(s.paddingLeft), right = parseFloat(s.paddingRight);
          return { x: r.left + el.clientLeft + left, width: el.clientWidth - left - right };
        }"""
    )


def test_the_grid_fits_the_panel_with_ausschnitt_ticked_and_a_click_on_100_takes_it_in(editor):
    """At 1280 by 1024 the panel shows squares 10 and 100 within its box and no sideways scroll bar;
    a click on square 100 takes it into the cut-out."""
    client = user()
    page = editor(feld("h", TAFEL), client=client)
    resize(page, 1280, 1024)
    pick(page, "h")
    step(page, lambda: field(page, "Ausschnitt").check())
    expect(square(page, 100)).to_be_visible()
    assert no_sideways_scroll(page)
    box_panel = client_box(page)
    assert inside(box_panel, square(page, 10).bounding_box())
    assert inside(box_panel, square(page, 100).bounding_box())
    step(page, lambda: square(page, 100).click())
    assert props_of(doc(page, client))["shape"] == [34, 43, 44, 45, 54, 99]
    expect(square(page, 100)).to_have_attribute("data-cut", "in")


def test_the_grid_fits_a_narrow_window_with_the_panel_opened_by_format_und_ansicht(editor):
    """At 820 by 1180 the panel, opened with Format und Ansicht, shows squares 10 and 100 within its
    box and no sideways scroll bar."""
    client = user()
    page = editor(feld("h", {**TAFEL, "cut": True}), client=client)
    resize(page, 820, 1180)
    pick(page, "h")
    if not page.locator(".panel").is_visible():
        bar(page, "right").click()
    expect(square(page, 100)).to_be_visible()
    assert no_sideways_scroll(page)
    box_panel = client_box(page)
    assert inside(box_panel, square(page, 10).bounding_box())
    assert inside(box_panel, square(page, 100).bounding_box())


def test_the_grid_fits_with_selbst_faerben_and_a_click_on_100_tints_it(editor):
    """With Färben set to Selbst färben the grid fits the panel as well, and a click on square 100
    tints it."""
    client = user()
    page = editor(feld("h", TAFEL), client=client)
    resize(page, 1280, 1024)
    pick(page, "h")
    step(page, lambda: field(page, "Färben").select_option("free"))
    expect(square(page, 100)).to_be_visible()
    assert no_sideways_scroll(page)
    box_panel = client_box(page)
    assert inside(box_panel, square(page, 10).bounding_box())
    assert inside(box_panel, square(page, 100).bounding_box())
    step(page, lambda: square(page, 100).click())
    assert props_of(doc(page, client))["tints"] == [[99, 1]]


def test_picking_another_block_leaves_the_panel_scrolled_to_the_left_edge(editor):
    """The panel is scrolled sideways as far as it goes while the grid shows; picking another block
    brings it back to scrollLeft 0."""
    text = {"text": "Hallo", "size": 14, "align": "left"}
    page = editor(feld("h", {**TAFEL, "cut": True}), box("t", "text", text, z=5))
    resize(page, 820, 1180)
    pick(page, "h")
    if not page.locator(".panel").is_visible():
        bar(page, "right").click()
    expect(square(page, 100)).to_be_visible()
    page.locator(".panel").evaluate("el => { el.scrollLeft = el.scrollWidth; }")
    pick(page, "t")
    expect(at(page, "t")).to_have_class("block sel")
    assert page.locator(".panel").evaluate("el => el.scrollLeft") == 0
