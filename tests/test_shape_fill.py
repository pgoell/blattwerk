"""A closed shape's fill: a Muster, or Millimeterpapier and Karo. #836."""

import re

from playwright.sync_api import expect
from ui import RECT, at, box, pick, saved, user

ROOM = {"x": 75, "y": 80, "w": 60, "h": 40}


def panel(page):
    return page.locator(".panel")


def press(page, name):
    button = panel(page).get_by_role("button", name=name, exact=True)
    button.scroll_into_view_if_needed()
    button.click()


def test_a_rectangle_takes_a_pattern_and_graph_paper(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    expect(panel(page).get_by_role("button", name="Muster", exact=True)).to_be_visible()
    expect(panel(page).get_by_role("button", name="Keine Füllung", exact=True)).to_be_disabled()

    press(page, "Lineatur")
    paper = at(page, "a").locator("svg.hatch pattern")
    expect(paper).to_have_attribute("width", "10")
    expect(paper.locator("line")).to_have_count(20)
    expect(paper.locator("line").first).to_have_attribute("stroke", "#8aa4be")
    (a,) = saved(page, client)
    assert a["props"]["paper"] == "mm"
    assert a["props"]["fill"] == "#8aa4be"
    assert "motif" not in a["props"]

    press(page, "Karo 5 mm")
    expect(paper).to_have_attribute("width", "5")
    expect(paper.locator("line")).to_have_count(2)

    press(page, "Muster")
    motif = at(page, "a").locator("svg.hatch pattern")
    expect(motif).to_have_attribute("width", "5")
    expect(motif.locator("rect")).to_have_attribute("fill", "#8aa4be")
    (a,) = saved(page, client)
    assert a["props"]["motif"] == "stripes"
    assert "paper" not in a["props"]

    panel(page).get_by_label("Füllung", exact=True).fill("#ff0000")
    expect(motif.locator("rect")).to_have_attribute("fill", "#ff0000")
    panel(page).get_by_label("Schwarz-Weiß", exact=True).check()
    expect(motif.locator("rect")).to_have_attribute("fill", "#000000")
    (a,) = saved(page, client)
    assert (a["props"]["mono"], a["props"]["fill"]) == (True, "#ff0000")

    panel(page).get_by_label("Schwarz-Weiß", exact=True).uncheck()
    expect(motif.locator("rect")).to_have_attribute("fill", "#ff0000")
    panel(page).get_by_label("Skalierung", exact=True).fill("8")
    expect(motif).to_have_attribute("width", "8")
    press(page, "Punkte")
    expect(motif.locator("circle")).to_have_count(1)
    press(page, "Wellen")
    expect(motif.locator("path")).to_have_count(1)
    press(page, "Kariert")
    expect(motif.locator("rect")).to_have_count(2)

    press(page, "Farbe")
    expect(at(page, "a").locator("svg.hatch")).to_have_count(0)
    expect(at(page, "a").locator(".frame")).to_have_css("background-color", "rgb(255, 0, 0)")
    press(page, "Keine Füllung")
    expect(at(page, "a").locator("svg.hatch")).to_have_count(0)
    expect(panel(page).get_by_label("Transparenz", exact=True)).to_be_disabled()
    (a,) = saved(page, client)
    assert a["props"]["fill"] == "none"
    for gone in ("motif", "paper", "mono", "scale"):
        assert gone not in a["props"]


def test_a_triangle_fills_its_outline_with_the_pattern(editor):
    client = user()
    page = editor(box("a", "shape", {**RECT, "kind": "triangle"}, **ROOM), client=client)
    pick(page, "a")
    press(page, "Muster")
    expect(at(page, "a").locator("svg.outline pattern")).to_have_count(1)
    expect(at(page, "a").locator("svg.outline > polygon")).to_have_attribute(
        "fill", re.compile(r"^url\(#")
    )
    (a,) = saved(page, client)
    assert (a["props"]["motif"], a["props"]["fill"], a["props"]["kind"]) == (
        "stripes",
        "#ffd43b",
        "triangle",
    )
