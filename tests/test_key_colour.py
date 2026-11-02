"""A sheet chooses the colour its Lösungen print in (#848).

The answers are red until the teacher picks another colour, or "Wie der Text", which uses the
sheet's own ink. The choice is kept, and the print uses it too.
"""

from playwright.sync_api import expect
from ui import LINE, at, box, doc, maths, tool, user

from blattwerk import pdf

RED = "rgb(192, 57, 43)"
GREEN = "rgb(0, 128, 0)"
INK = "rgb(34, 34, 34)"


def sums(page):
    """The filled results of the maths block."""
    return at(page, "m").locator(".maths u")


def length(page):
    """The length printed on the answer key, an svg text."""
    return at(page, "l").locator("svg text")


def test_a_teacher_picks_the_colour_of_the_answers(editor, browser, server):
    """Red until the teacher picks green, then the sheet's own ink with "Wie der Text"."""
    client = user()
    page = editor(
        box("m", "maths", maths(client), y=20, h=30),
        box("l", "shape", {**LINE, "label": "key"}, z=2, y=70, w=80, h=20),
        client=client,
    )
    tool(page, "Lösungen zeigen").click()
    expect(sums(page).first).to_have_css("color", RED)
    expect(length(page)).to_have_css("fill", RED)
    expect(at(page, "m").locator(".maths")).to_have_css("color", INK)

    page.get_by_role("tab", name="Ansicht").click()
    group = page.get_by_role("group", name="Lösungsfarbe")
    expect(group.get_by_role("button", name="Farbe", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    page.locator(".panel").get_by_label("Farbe der Lösungen").fill("#008000")
    expect(sums(page).first).to_have_css("color", GREEN)
    expect(length(page)).to_have_css("fill", GREEN)
    expect(at(page, "m").locator(".maths")).to_have_css("color", INK)
    saved = doc(page, client)
    assert saved["keyColor"] == "#008000"
    assert "keyAsText" not in saved

    mine = page.url.rstrip("/").split("/")[-1]
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}?loesungen")
    paper.wait_for_selector("body.ready", state="attached")
    expect(paper.locator(".maths u").first).to_have_css("color", GREEN)
    expect(paper.locator("svg text").first).to_have_css("fill", GREEN)
    expect(paper.locator(".key")).to_have_css("color", GREEN)

    group.get_by_role("button", name="Wie der Text", exact=True).click()
    expect(sums(page).first).to_have_css("color", INK)
    expect(length(page)).to_have_css("fill", INK)
    saved = doc(page, client)
    assert saved["keyAsText"] is True
    assert saved["keyColor"] == "#008000"

    paper.goto(f"{server}/druck/{mine}?loesungen")
    paper.wait_for_selector("body.ready", state="attached")
    expect(paper.locator(".maths u").first).to_have_css("color", INK)
    expect(paper.locator(".key")).to_have_css("color", INK)
    expect(paper.locator("svg text").first).to_have_css("fill", INK)
    paper.context.close()
