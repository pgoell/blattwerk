"""Raute, Vieleck, Bogen, Gedankenwolke, Bruchkreis and the other Formen from #835."""

import re

from playwright.sync_api import expect
from ui import saved, user

EIGHT = re.compile(r"^(\S+ ){7}\S+$")
TWELVE = re.compile(r"^(\S+ ){11}\S+$")


def insert(page, label):
    return page.locator(".insert").get_by_label(label, exact=True)


def outline(page):
    return page.locator(".block.sel svg.outline")


def test_the_bar_inserts_the_new_formen(editor):
    client = user()
    page = editor(client=client)

    insert(page, "Raute").click()
    diamond = outline(page).locator("polygon")
    expect(diamond).to_have_count(1)
    assert len(diamond.get_attribute("points").split()) == 4
    assert saved(page, client)[-1]["props"]["kind"] == "diamond"

    insert(page, "Vieleck").click()
    polygon = outline(page).locator("polygon")
    expect(polygon).to_have_count(1)
    assert len(polygon.get_attribute("points").split()) == 6
    page.get_by_label("Ecken", exact=True).fill("8")
    expect(polygon).to_have_attribute("points", EIGHT)
    assert saved(page, client)[-1]["props"]["corners"] == 8

    insert(page, "Stern").click()
    page.get_by_label("Zacken", exact=True).fill("6")
    star = outline(page).locator("polygon")
    expect(star).to_have_attribute("points", TWELVE)
    assert saved(page, client)[-1]["props"]["spikes"] == 6

    insert(page, "Bogen").click()
    arc = outline(page).locator("path.arc")
    expect(arc).to_have_count(1)
    assert "Q" in arc.get_attribute("d")
    assert saved(page, client)[-1]["props"]["bulge"] == 0.65

    insert(page, "Gebogener Pfeil").click()
    expect(outline(page).locator("polygon.head")).to_have_count(1)
    assert saved(page, client)[-1]["props"]["kind"] == "bow"

    insert(page, "Gedankenwolke").click()
    cloud = outline(page).locator("path")
    expect(cloud).to_have_count(1)
    assert cloud.get_attribute("d").count("A") == 8
    assert saved(page, client)[-1]["props"]["kind"] == "thought"

    insert(page, "Bruchkreis").click()
    pie = outline(page)
    expect(pie.locator(".wedge")).to_have_count(4)
    expect(pie.locator(".wedge.on")).to_have_count(1)
    page.get_by_label("Teile", exact=True).fill("6")
    page.get_by_label("Gefüllt", exact=True).fill("2")
    expect(pie.locator(".wedge")).to_have_count(6)
    expect(pie.locator(".wedge.on")).to_have_count(2)

    insert(page, "Bruchrechteck").click()
    bar = outline(page)
    expect(bar.locator(".strip.on")).to_have_count(1)
    assert saved(page, client)[-1]["props"]["kind"] == "bars"

    insert(page, "Kreis").click()
    expect(outline(page).locator(".hub")).to_have_count(0)
    page.get_by_label("Mittelpunkt", exact=True).check()
    expect(outline(page).locator(".hub")).to_have_count(1)
    assert saved(page, client)[-1]["props"]["hub"] is True

    insert(page, "Rechteck").click()
    expect(outline(page)).to_have_count(0)
    page.get_by_role("button", name="Quadratisch", exact=True).click()
    expect(outline(page).locator("rect")).to_have_count(1)
    assert saved(page, client)[-1]["props"]["form"] == "square"
    page.get_by_role("button", name="Kreisförmig", exact=True).click()
    expect(outline(page).locator("path")).to_have_count(1)
    assert saved(page, client)[-1]["props"]["form"] == "round"
