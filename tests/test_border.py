"""A line style or a width gives a text or a shape with no border one, as in PowerPoint (#291)."""

import io

import pytest
from PIL import Image
from pixels import over, screen_and_print
from playwright.sync_api import expect
from test_undo_steps import gesture
from ui import FIELD, RECT, TEXT, at, box, pick, saved, user

from blattwerk import pdf

# A box of 60 by 40 mm with room around it.
ROOM = {"x": 75, "y": 80, "w": 60, "h": 40}
STYLES = {"Durchgezogen": None, "Gestrichelt": "dashed", "Gepunktet": "dotted"}
# A text as sheets stored it before: a style and a width, and no border to show them.
OLD = {**TEXT, "dash": "dashed", "strokeWidth": 2}
BLACK = "#222222"
# A border's width in px, and the px of a mm of the sheet.
WIDTH = """(el) => [
    parseFloat(getComputedStyle(el).borderTopWidth),
    el.closest(".sheet").getBoundingClientRect().width / 210,
]"""


def button(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def none(page):
    return page.get_by_role("button", name="Kein Rand")


def expect_border(frame, dash=None, width=0.5):
    """Waits for the frame's border: the box's own where it is solid, else dashes drawn over it."""
    drawn = frame.locator("svg.dashes > rect")
    if dash:
        expect(drawn).to_have_attribute("stroke", BLACK)
        expect(drawn).to_have_attribute("stroke-width", str(width))
        # Dots are dashes of no length with round ends.
        assert drawn.get_attribute("stroke-linecap") == ("round" if dash == "dotted" else None)
    else:
        expect(drawn).to_have_count(0)
        expect(frame).to_have_css("border-top-style", "solid")
        expect(frame).to_have_css("border-top-color", "rgb(34, 34, 34)")
        # The browser rounds a border down to whole pixels.
        px, mm = frame.evaluate(WIDTH)
        assert 1 <= px == pytest.approx(width * mm, abs=1)


def expect_bare(page, frame):
    """Waits until the frame has no border, and the panel shows none."""
    expect(frame.locator("svg.dashes")).to_have_count(0)
    expect(frame).to_have_css("border-top-style", "none")
    expect(none(page)).to_be_disabled()
    for label in STYLES:
        expect(button(page, label)).not_to_have_class("on")


def opened(editor, props=TEXT, kind="text"):
    """The editor on one selected block. Gives the page, the block's frame and the user."""
    client = user()
    page = editor(box("a", kind, props, **ROOM), client=client)
    pick(page, "a")
    return page, at(page, "a").locator(".frame"), client


def inked(printed, width):
    """The share of the box's upper edge that the print has drawn dark.

    Of its right half: the words stand at the left, and in a box with no border at its very top.
    """
    image = Image.open(io.BytesIO(printed)).convert("L")
    mm = image.width / 210
    left, right = round((ROOM["x"] + 30) * mm), round((ROOM["x"] + ROOM["w"] - 5) * mm)
    top, bottom = int((ROOM["y"] - 0.3) * mm), round((ROOM["y"] + width + 0.3) * mm) + 1
    edge = image.crop((left, top, right, bottom)).tobytes()
    # Each column of the edge, by its darkest pixel.
    dark = [min(edge[x :: right - left]) < 200 for x in range(right - left)]
    return sum(dark) / len(dark)


# The issue as a teacher meets it


def test_a_new_text_takes_a_dashed_then_a_solid_border_of_a_width(editor):
    page = editor()
    page.get_by_label("Text", exact=True).click()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("Igel")
    page.keyboard.press("Escape")
    expect(page.locator(".block.sel")).to_have_count(1)
    frame = page.locator(".block.sel .frame")
    expect_bare(page, frame)
    button(page, "Gestrichelt").click()
    expect_border(frame, "dashed")
    expect(button(page, "Gestrichelt")).to_have_class("on")
    expect(none(page)).to_be_enabled()
    button(page, "Durchgezogen").click()
    expect_border(frame)
    expect(button(page, "Durchgezogen")).to_have_class("on")
    button(page, "Randstärke").fill("2")
    expect_border(frame, width=2)
    expect(button(page, "Randstärke")).to_have_value("2")


# A1


@pytest.mark.parametrize("label", STYLES, ids=["solid", "dashed", "dotted"])
def test_a_style_gives_a_text_with_no_border_a_border_in_that_style(editor, label):
    page, frame, client = opened(editor)
    button(page, label).click()
    expect_border(frame, STYLES[label])
    (a,) = saved(page, client)
    assert (a["props"]["stroke"], a["props"].get("dash")) == (BLACK, STYLES[label])


# A2


def test_a_width_gives_a_text_with_no_border_a_border_and_the_slider_stays(editor):
    page, frame, client = opened(editor)
    button(page, "Randstärke").fill("2")
    expect_border(frame, width=2)
    expect(button(page, "Randstärke")).to_have_value("2")
    (a,) = saved(page, client)
    assert (a["props"]["stroke"], a["props"]["strokeWidth"]) == (BLACK, 2)
    expect(button(page, "Randstärke")).to_have_value("2")


# A3


def test_kein_rand_is_live_with_a_border_and_no_style_is_lit_without_one(editor):
    page, frame, client = opened(editor)
    expect_bare(page, frame)
    button(page, "Gepunktet").click()
    expect_border(frame, "dotted")
    expect(button(page, "Gepunktet")).to_have_class("on")
    none(page).click()
    expect_bare(page, frame)
    # The style stays for the next border.
    (a,) = saved(page, client)
    assert (a["props"]["stroke"], a["props"]["dash"]) == ("none", "dotted")


# A4


@pytest.mark.parametrize(
    "label, width",
    [("Durchgezogen", 0.5), ("Gestrichelt", 0.5), ("Gepunktet", 0.5), (None, 0.25), (None, 3)],
    ids=["solid", "dashed", "dotted", "thin", "thick"],
)
def test_the_pdf_shows_the_border_a_text_was_given(editor, browser, server, label, width):
    page, frame, client = opened(editor)
    if label:
        button(page, label).click()
    else:
        button(page, "Randstärke").fill(str(width))
    expect_border(frame, STYLES.get(label), width)
    saved(page, client)
    screen, printed = screen_and_print(browser, server, client, page.url.rsplit("/", 1)[1])
    assert over(screen, printed) == []
    # A solid border runs all along the edge, dashes and dots over a part of it.
    low, high = (0.2, 0.8) if STYLES.get(label) else (0.99, 1)
    assert low <= inked(printed, width) <= high


# A5


def test_after_a_reload_the_border_is_there_and_its_style_is_lit(editor):
    page, frame, client = opened(editor)
    button(page, "Gestrichelt").click()
    expect_border(frame, "dashed")
    saved(page, client)
    page.reload()
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
    pick(page, "a")
    expect_border(frame, "dashed")
    expect(button(page, "Gestrichelt")).to_have_class("on")
    expect(button(page, "Durchgezogen")).not_to_have_class("on")
    expect(none(page)).to_be_enabled()


# A6, I2


@pytest.mark.parametrize("label", ["Gepunktet", "Randstärke"], ids=["style", "width"])
def test_one_undo_takes_the_border_away_and_redo_brings_it_back(editor, label):
    page, frame, client = opened(editor)
    undo, redo = (page.get_by_label(name, exact=True) for name in ("Rückgängig", "Wiederholen"))
    look = ("dotted", 0.5) if label == "Gepunktet" else (None, 2)
    if label == "Gepunktet":
        button(page, label).click()
    else:
        button(page, label).fill("2")
    expect_border(frame, *look)
    undo.click()
    expect_bare(page, frame)
    expect(button(page, "Randstärke")).to_have_value("0.5")
    expect(undo).to_be_disabled()
    redo.click()
    expect_border(frame, *look)
    undo.click()
    expect_bare(page, frame)
    # The style and the width went with the border.
    page.get_by_label("Duplizieren", exact=True).click()
    a, _ = saved(page, client)
    assert a["props"] == TEXT


# A7


@pytest.mark.parametrize("first", ["text", "shape"])
def test_a_style_for_a_bare_text_and_a_red_shape_goes_to_both(editor, first):
    client = user()
    red = {**RECT, "stroke": "#ff0000"}
    low = {**ROOM, "y": 140}
    page = editor(
        box("text", "text", TEXT, **ROOM), box("shape", "shape", red, **low), client=client
    )
    pick(page, first, "shape" if first == "text" else "text")
    button(page, "Gestrichelt").click()
    expect_border(at(page, "text").locator(".frame"), "dashed")
    expect(at(page, "shape").locator("svg.dashes > rect")).to_have_attribute("stroke", "#ff0000")
    now = {b["id"]: b["props"] for b in saved(page, client)}
    assert (now["text"]["stroke"], now["text"]["dash"]) == (BLACK, "dashed")
    assert (now["shape"]["stroke"], now["shape"]["dash"]) == ("#ff0000", "dashed")
    # One step for both.
    page.get_by_label("Rückgängig", exact=True).click()
    expect(at(page, "text").locator("svg.dashes")).to_have_count(0)
    expect(at(page, "shape").locator("svg.dashes")).to_have_count(0)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


# A8


def test_an_old_text_with_a_style_and_no_stroke_stays_bare_on_screen_and_in_the_pdf(
    editor, browser, server
):
    page, frame, client = opened(editor, OLD)
    expect_bare(page, frame)
    sheet_id = page.url.rsplit("/", 1)[1]
    # The page the PDF is printed from.
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(int(sheet_id))})
    paper.goto(f"{server}/druck/{sheet_id}")
    paper.wait_for_selector("body.ready", state="attached")
    expect(paper.locator(".frame svg.dashes")).to_have_count(0)
    expect(paper.locator(".frame")).to_have_css("border-top-style", "none")
    paper.close()
    screen, printed = screen_and_print(browser, server, client, sheet_id)
    assert over(screen, printed) == []
    assert inked(printed, 2) == 0


# I1


@pytest.mark.parametrize("label", ["Gestrichelt", "Randstärke"], ids=["style", "width"])
def test_a_shape_after_kein_rand_takes_a_style_or_a_width_and_has_its_border_back(editor, label):
    page, frame, client = opened(editor, {**RECT, "stroke": "#ff0000"}, "shape")
    none(page).click()
    expect_bare(page, frame)
    if label == "Gestrichelt":
        button(page, label).click()
        expect_border(frame, "dashed")
    else:
        button(page, label).fill("2")
        expect_border(frame, width=2)
    (a,) = saved(page, client)
    assert a["props"]["stroke"] == BLACK


# I3


@pytest.mark.parametrize("stops", [(1, 2), (1, 2, 0)], ids=["away", "back"])
def test_a_drag_of_the_width_that_turns_the_border_on_is_one_undo_step(editor, stops):
    page, frame, _ = opened(editor)
    undo = page.get_by_label("Rückgängig", exact=True)
    gesture(page, "Randstärke", *stops)
    # Back at the width the slider began with, the border is on all the same.
    expect_border(frame, width=1.75 if stops[-1] else 0.5)
    undo.click()
    expect_bare(page, frame)
    expect(button(page, "Randstärke")).to_have_value("0.5")
    expect(undo).to_be_disabled()


# I4


def test_the_colour_of_the_border_keeps_the_style_and_the_width(editor):
    page, frame, client = opened(editor)
    button(page, "Gestrichelt").click()
    button(page, "Randstärke").fill("2")
    button(page, "Rand").fill("#0000ff")
    expect(frame.locator("svg.dashes > rect")).to_have_attribute("stroke", "#0000ff")
    look = {"stroke": "#0000ff", "dash": "dashed", "strokeWidth": 2}
    (a,) = saved(page, client)
    assert a["props"] == {**TEXT, **look}
    # Kein Rand keeps them too, for the colour picked next.
    none(page).click()
    expect_bare(page, frame)
    button(page, "Rand").fill("#00ff00")
    expect(frame.locator("svg.dashes > rect")).to_have_attribute("stroke", "#00ff00")
    (a,) = saved(page, client)
    assert a["props"] == {**TEXT, **look, "stroke": "#00ff00"}


# I5


def test_a_style_picked_while_a_text_is_written_gives_the_border_and_typing_goes_on(editor):
    page, frame, _ = opened(editor)
    page.keyboard.press("Enter")
    page.keyboard.type("du")
    expect(page.locator(FIELD)).to_have_text("du")
    button(page, "Gestrichelt").click()
    expect_border(frame, "dashed")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("dux")
