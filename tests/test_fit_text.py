"""An Text anpassen: a framed text box as wide as its longest line and as high as its lines."""

import pytest
from playwright.sync_api import expect
from ui import FIELD, RECT, TEXT, box, grow, pick, saved, user

from blattwerk import pdf

FITTED = {**RECT, "fit": True}
TICK = "An Text anpassen"


def tick(page, on=True):
    """Ticks or unticks the panel's "An Text anpassen" for the picked boxes."""
    box_ = page.get_by_label(TICK)
    expect(box_).to_be_visible()
    box_.set_checked(on)


def test_fit_makes_the_box_as_wide_as_its_text(editor):
    client = user()
    page = editor(box("a", "text", {**RECT, **TEXT}, x=40, w=150, h=20), client=client)
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    assert a["props"]["fit"] is True
    assert a["w"] < 40


def test_fit_works_on_a_rounded_shape(editor):
    client = user()
    page = editor(
        box(
            "a",
            "shape",
            {**RECT, "kind": "rounded", "text": "Hallo", "size": 14, "align": "left"},
            x=40,
            w=150,
            h=20,
        ),
        client=client,
    )
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    assert a["props"]["fit"] is True
    assert a["w"] < 40


def test_typing_grows_and_shrinks_the_fitted_box(editor):
    client = user()
    page = editor(box("a", "text", {**FITTED, **TEXT, "text": ""}, x=40, w=10, h=20), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("Wir lesen heute eine Geschichte")
    expect(page.locator(FIELD)).to_have_text("Wir lesen heute eine Geschichte")
    (a,) = saved(page, client)
    grown = a["w"]
    assert grown > 40
    for _ in range(len("Wir lesen heute eine Geschichte")):
        page.keyboard.press("Backspace")
    (a,) = saved(page, client)
    assert a["w"] < grown


def test_fit_is_one_undo_step(editor):
    client = user()
    page = editor(box("a", "text", {**RECT, **TEXT}, x=40, w=150, h=20), client=client)
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    assert a["w"] < 150
    page.keyboard.press("Control+z")
    (a,) = saved(page, client)
    assert a["w"] == 150
    assert "fit" not in a["props"] or a["props"]["fit"] is not True


def test_the_pdf_keeps_the_fitted_lines(editor, browser, server):
    client = user()
    long = "Wir lesen heute eine sehr lange Geschichte über den Wald und den Fuchs"
    page = editor(
        box("a", "text", {**RECT, **TEXT, "text": long}, x=40, w=150, h=20), client=client
    )
    pick(page, "a")
    tick(page)
    saved(page, client)
    sheet_id = page.url.rsplit("/", 1)[1]
    shape = page.locator('.block[data-id="a"]').bounding_box()
    # The print page lays the box out as the PDF does: its width and height keep the same ratio as on screen.
    printed = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(sheet_id)})
    printed.goto(f"{server}/druck/{sheet_id}")
    printed.wait_for_selector("body.ready", state="attached")
    frame = printed.locator('[data-block="a"]').bounding_box()
    printed.close()
    assert frame["width"] / frame["height"] == pytest.approx(
        shape["width"] / shape["height"], rel=0.01
    )


def test_a_fitted_box_stops_at_the_right_margin(editor):
    client = user()
    long = "Wir lesen heute eine sehr lange Geschichte über den Wald und den Fuchs"
    page = editor(
        box("a", "text", {**RECT, **TEXT, "text": long}, x=150, w=20, h=20), client=client
    )
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    # The page's right margin is 210 - 15 mm; the box stops there, and its words break.
    assert a["x"] + a["w"] <= 195.5


def test_an_empty_fitted_box_keeps_10_mm(editor):
    client = user()
    page = editor(box("a", "text", {**RECT, **TEXT, "text": ""}, x=40, w=150, h=20), client=client)
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    assert a["w"] == 10


def test_fit_keeps_the_edge_its_text_is_aligned_to(editor):
    client = user()
    page = editor(
        box("a", "text", {**RECT, **TEXT, "align": "right"}, x=100, w=150, h=20), client=client
    )
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    assert a["x"] + a["w"] == 250


def test_a_hand_resize_turns_fit_off(editor):
    client = user()
    page = editor(box("a", "text", {**FITTED, **TEXT}, x=40, w=20, h=20), client=client)
    pick(page, "a")
    grow(page, 40)
    (a,) = saved(page, client)
    assert "fit" not in a["props"] or a["props"]["fit"] is not True
    assert a["w"] > 20


def test_a_typed_width_turns_fit_off(editor):
    client = user()
    page = editor(box("a", "text", {**FITTED, **TEXT}, x=40, w=20, h=20), client=client)
    pick(page, "a")
    page.get_by_role("textbox", name="Breite", exact=True).fill("60")
    page.get_by_role("textbox", name="Breite", exact=True).press("Enter")
    (a,) = saved(page, client)
    assert a["w"] == 60
    assert "fit" not in a["props"] or a["props"]["fit"] is not True


def test_fit_with_several_picked(editor):
    client = user()
    page = editor(
        box("a", "text", {**RECT, **TEXT}, x=40, w=150, h=20),
        box("b", "text", {**RECT, **TEXT}, z=2, x=40, w=150, h=20),
        client=client,
    )
    pick(page, "a", "b")
    tick(page)
    a, b = saved(page, client)
    assert a["w"] < 40 and b["w"] < 40
    page.keyboard.press("Control+z")
    a, b = saved(page, client)
    assert a["w"] == 150 and b["w"] == 150


def test_unticking_fit_keeps_the_fitted_size(editor):
    client = user()
    page = editor(box("a", "text", {**RECT, **TEXT}, x=40, w=150, h=20), client=client)
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    fitted_w = a["w"]
    tick(page, False)
    (a,) = saved(page, client)
    assert "fit" not in a["props"] or a["props"]["fit"] is not True
    assert a["w"] == fitted_w


def test_a_box_without_fit_keeps_its_size(editor):
    client = user()
    page = editor(box("a", "text", {**RECT, **TEXT}, x=40, w=150, h=20), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    (a,) = saved(page, client)
    assert a["w"] == 150
    assert "fit" not in a["props"]
