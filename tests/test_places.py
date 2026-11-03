"""A sheet colours digits by place (#843).

Einer, Zehner, Hunderter and Tausender take the Montessori colours in every maths
block, and each colour can be changed. A text block stays black, and so does a
decimal.
"""

from playwright.sync_api import expect
from test_hunderterfeld import TAFEL
from ui import TEXT, at, box, doc, maths, user

from blattwerk import pdf

GREEN = "rgb(0, 150, 64)"
BLUE = "rgb(0, 87, 168)"
RED = "rgb(227, 6, 19)"
INK = "rgb(34, 34, 34)"
PINK = "rgb(255, 0, 255)"


def task(props, a, b, result):
    """One plus task, so the test reads a number it chose."""
    return {
        **props,
        "count": 1,
        "loosen": None,
        "exercises": [{"op": "+", "a": a, "b": b, "result": result, "rest": 0}],
    }


def test_a_sheet_colours_digits_by_place(editor, browser, server):
    """Off, then Montessori colours on the row, the written sum and the hundred square.

    The text block and the decimal stay black. A new Einer colour is kept, and the print uses it.
    """
    client = user()
    row = task(maths(client, max=100, count=1, seed=1), 12, 34, 46)
    decimal = task(maths(client, decimals=2, max=20, count=1, seed=1), 350, 125, 475)
    page = editor(
        box("m", "maths", row, y=12, h=28),
        box("w", "maths", maths(client, format="written", max=100, count=2, seed=3), y=44, h=50),
        box("d", "maths", decimal, y=98, h=24),
        box("t", "text", {**TEXT, "text": "Zahl 48"}, y=126, h=12),
        box("h", "hunderterfeld", TAFEL, y=142, h=100, w=100),
        client=client,
    )
    expect(page.locator("[data-place]")).to_have_count(0)

    page.get_by_role("tab", name="Ansicht").click()
    group = page.get_by_role("group", name="Stellenwerte")
    expect(group.get_by_role("button", name="Aus", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    group.get_by_role("button", name="An", exact=True).click()

    expect(at(page, "m").locator("[data-place='einer']").first).to_have_css("color", GREEN)
    expect(at(page, "m").locator("[data-place='zehner']").first).to_have_css("color", BLUE)
    expect(at(page, "w").locator("[data-place='einer']").first).to_have_css("fill", GREEN)
    expect(at(page, "h").locator("[data-place='hunderter']").first).to_have_css("fill", RED)
    expect(at(page, "h").locator("[data-place='einer']").first).to_have_css("fill", GREEN)
    expect(at(page, "d").locator("[data-place]")).to_have_count(0)
    expect(at(page, "t").locator("[data-place]")).to_have_count(0)
    expect(at(page, "t").get_by_text("Zahl 48")).to_have_css("color", INK)

    page.locator(".panel").get_by_label("Farbe der Einer").fill("#ff00ff")
    expect(at(page, "m").locator("[data-place='einer']").first).to_have_css("color", PINK)
    expect(at(page, "m").locator("[data-place='zehner']").first).to_have_css("color", BLUE)
    saved = doc(page, client)
    assert saved["places"]["on"] is True
    assert saved["places"]["einer"] == "#ff00ff"
    assert "zehner" not in saved["places"]

    mine = page.url.rstrip("/").split("/")[-1]
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    expect(paper.locator(".maths [data-place='einer']").first).to_have_css("color", PINK)
    expect(paper.locator(".hunderterfeld [data-place='hunderter']").first).to_have_css("fill", RED)
    expect(paper.get_by_text("Zahl 48").locator("[data-place]")).to_have_count(0)
    expect(paper.locator(".maths").nth(2).locator("[data-place]")).to_have_count(0)
    paper.context.close()
