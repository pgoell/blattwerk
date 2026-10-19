"""An Text anpassen: a framed text box as wide as its longest line and as high as its lines."""

import pytest
from playwright.sync_api import expect
from ui import FIELD, RECT, TEXT, at, box, centre, drag, grow, pick, saved, user

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


# The rows a box's text breaks into, top to bottom: the words of each row.
ROWS = """el => {
  const rows = new Map();
  const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode())
    for (const m of n.data.matchAll(/\\S+/g)) {
      const r = document.createRange();
      r.setStart(n, m.index);
      r.setEnd(n, m.index + m[0].length);
      const top = Math.round(r.getBoundingClientRect().top / 4);
      rows.set(top, [...(rows.get(top) ?? []), m[0]]);
    }
  return [...rows.keys()].sort((a, b) => a - b).map((k) => rows.get(k).join(" "));
}"""


@pytest.mark.parametrize("words", ["Hallo Kinder", " ".join(["Wir lesen heute im Wald."] * 8)])
def test_the_pdf_keeps_the_fitted_lines(editor, browser, server, words):
    """A heading prints on one row, a long text breaks at the margin where the screen breaks it."""
    client = user()
    page = editor(
        box("a", "text", {**RECT, **TEXT, "text": words}, x=40, w=150, h=20), client=client
    )
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    page.keyboard.press("Escape")
    shown = page.locator('.block[data-id="a"] .frame').evaluate(ROWS)
    sheet_id = page.url.rsplit("/", 1)[1]
    printed = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(sheet_id)})
    printed.goto(f"{server}/druck/{sheet_id}")
    printed.wait_for_selector("body.ready", state="attached")
    rows = printed.locator('[data-block="a"] .frame').evaluate(ROWS)
    printed.close()
    assert rows == shown
    assert (len(rows) == 1) == (words == "Hallo Kinder")
    assert a["w"] <= 155.01


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
        box("a", "text", {**RECT, **TEXT, "align": "right"}, x=40, w=150, h=20), client=client
    )
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    assert a["w"] < 40
    assert a["x"] + a["w"] == pytest.approx(190, abs=0.01)


def test_a_hand_resize_turns_fit_off(editor):
    client = user()
    page = editor(box("a", "text", {**FITTED, **TEXT}, x=40, w=20, h=20), client=client)
    pick(page, "a")
    k = page.locator(".sheet").bounding_box()["width"] / 210
    # The right edge's handle, pulled 30 mm out.
    x, y = centre(page.locator(".moveable-control.moveable-e"))
    drag(page, (x, y), (x + 30 * k, y))
    expect(page.get_by_label(TICK)).not_to_be_checked()
    (a,) = saved(page, client)
    assert "fit" not in a["props"]
    assert a["w"] == pytest.approx(50, abs=1)


def test_a_group_resize_turns_fit_off(editor):
    client = user()
    page = editor(
        box("a", "text", {**FITTED, **TEXT}, x=40, w=20, h=20),
        box("b", "text", {**FITTED, **TEXT}, x=40, y=100, w=20, h=20, z=2),
        client=client,
    )
    pick(page, "a", "b")
    grow(page, 60)
    expect(page.get_by_label(TICK)).not_to_be_checked()
    for b in saved(page, client):
        assert "fit" not in b["props"]
        assert b["w"] > 20


def test_a_locked_box_keeps_its_place_and_size(editor):
    client = user()
    page = editor(
        box("a", "text", {**RECT, **TEXT, "align": "center"}, x=40, w=150, h=20, locked=True),
        client=client,
    )
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    assert a["props"]["fit"] is True
    assert (a["x"], a["w"], a["h"]) == (40, 150, 20)


def test_a_linked_text_does_not_fit(editor):
    """A text linked to the Lernwörter grows on with its list and keeps its width."""
    client = user()
    page = editor(
        box("a", "text", {**FITTED, **TEXT, "list": True}, x=40, w=150, h=20), client=client
    )
    pick(page, "a")
    page.keyboard.press("Control+b")
    expect(at(page, "a").locator(".frame")).to_have_css("font-weight", "700")
    (a,) = saved(page, client)
    assert a["props"]["bold"] is True
    assert (a["x"], a["w"]) == (40, 150)


def test_a_fitted_width_is_rounded_to_a_hundredth(editor):
    client = user()
    page = editor(box("a", "text", {**RECT, **TEXT}, x=40, w=150, h=20), client=client)
    pick(page, "a")
    tick(page)
    (a,) = saved(page, client)
    assert a["w"] == round(a["w"], 2)


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
    # A change to the text and to its size: a box without fit keeps its width.
    page.keyboard.press("Enter")
    page.keyboard.type("Hallo Kinder")
    page.keyboard.press("Escape")
    page.keyboard.press("Control+b")
    expect(at(page, "a").locator(".frame")).to_have_css("font-weight", "700")
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Hallo Kinder"
    assert a["props"]["bold"] is True
    assert a["w"] == 150
    assert "fit" not in a["props"]
