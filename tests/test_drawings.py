"""Sachunterricht line drawings: a catalogue beside the files, and a picture on the sheet.

The set is black line art a child can label. Each picture records where it came from.
A licence that asks for credit would have to ride onto the sheet the way picture search
does. This set's licence does not ask, so the sheet stays as an ordinary picture block.
"""

import json
import re
from pathlib import Path

import httpx
import pypdfium2
import pytest
from playwright.sync_api import expect
from ui import block, box, pick, saved, sheet, user

from blattwerk import svg

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "frontend" / "public" / "sachunterricht"
NS = "{http://www.w3.org/2000/svg}"
TOPICS = [
    ("koerper", "Körper"),
    ("pflanzen", "Pflanzen"),
    ("tiere", "Tiere im Wald"),
    ("wasser", "Wasserkreislauf und Wetter"),
    ("verkehr", "Verkehr"),
]
# Drawings made so a child can write the parts on them. The word is in the keywords.
LABELS = {
    "koerper-vorne",
    "gesicht",
    "auge",
    "ohr",
    "hand",
    "fuss",
    "skelett",
    "verdauung",
    "zahn",
    "haut",
    "pflanze",
    "bluete",
    "blatt",
    "baum",
    "wasserkreislauf",
    "fahrrad",
}
INK = {"none", "#000", "#000000", "black", "#fff", "#ffffff", "white"}
COLOUR = re.compile(r"(?:fill|stroke|color|stop-color)\s*[:=]\s*([^;\"'\s)]+)", re.IGNORECASE)


def catalogue():
    return json.loads((SET / "pictures.json").read_text(encoding="utf-8"))


def pictures():
    return catalogue()["pictures"]


def test_the_set_has_five_topics_and_about_a_hundred_drawings():
    data = catalogue()
    assert [(t["id"], t["name"]) for t in data["topics"]] == TOPICS
    got = pictures()
    assert len(got) == 100
    assert [p["id"] for p in got] == sorted(p["id"] for p in got)
    for topic, _name in TOPICS:
        assert sum(p["topic"] == topic for p in got) == 20
    assert {p["id"] for p in got} == {path.stem for path in SET.glob("*.svg")}


def test_each_picture_records_source_author_licence_and_address():
    data = catalogue()
    assert data["licence"]["name"] == "CC0 1.0"
    assert data["licence"]["asksForCredit"] is False
    assert data["licence"]["url"] == "https://creativecommons.org/publicdomain/zero/1.0/legalcode"
    text = (SET / "LICENCE.txt").read_text(encoding="utf-8")
    assert "CC0 1.0 Universal" in text
    assert "2. Waiver." in text
    assert "3. Public License Fallback." in text
    assert "commercial purposes" in text
    for picture in pictures():
        assert picture["source"] == "Blattomat"
        assert picture["author"] == "Blattomat"
        assert picture["licence"] == "CC0 1.0"
        assert picture["address"] == f"/sachunterricht/{picture['id']}.svg"
        assert picture["name"] and picture["keywords"]
        assert "blattwerk" not in json.dumps(picture).lower()
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    for words in ("Sachunterricht", "CC0 1.0", "frontend/public/sachunterricht"):
        assert words in notice
    assert "blattwerk" not in (SET / "pictures.json").read_text(encoding="utf-8").lower()
    assert "blattwerk" not in text.lower()


def test_labelling_pictures_are_found_by_beschriften():
    got = pictures()
    labelled = {p["id"] for p in got if "beschriften" in p["keywords"].lower()}
    assert labelled == LABELS
    found = [
        p["id"]
        for p in got
        if "beschriften" in f"{p['name']} {p['keywords']}".lower()
        and "fahrrad" in f"{p['name']} {p['keywords']}".lower()
    ]
    assert found == ["fahrrad"]
    koerper = [p["name"] for p in got if p["topic"] == "koerper"]
    assert "Körper von vorn" in koerper


def test_every_drawing_is_black_line_art_on_a_clear_ground():
    import xml.etree.ElementTree as ET

    for path in sorted(SET.glob("*.svg")):
        raw = path.read_bytes()
        assert b"blattwerk" not in raw.lower(), path.name
        cleaned = svg.clean(raw)
        assert cleaned is not None, path.name
        root = ET.fromstring(raw)
        assert root.tag == f"{NS}svg"
        assert root.get("viewBox")
        assert "style" not in root.attrib
        for el in root.iter():
            assert not el.tag.endswith("image"), path.name
            assert not el.tag.endswith("text"), path.name
            assert not el.tag.endswith("script"), path.name
            assert not el.tag.endswith("style"), path.name
            blob = " ".join(el.attrib.values())
            assert "url(" not in blob.lower(), path.name
            assert "gray" not in blob.lower() and "grey" not in blob.lower(), path.name
            for key in ("fill", "stroke", "color"):
                if key in el.attrib:
                    assert el.attrib[key].lower() in INK, (path.name, key, el.attrib[key])
            for found in COLOUR.findall(blob):
                assert found.lower() in INK, (path.name, found)


def test_a_catalogue_svg_stays_svg_and_prints_black(server):
    client = user()
    data = (SET / "fahrrad.svg").read_bytes()
    up = client.post("/api/uploads", files={"file": ("fahrrad.svg", data, "image/svg+xml")})
    assert up.status_code == 200
    shown = up.json()["id"]
    served = client.get(f"/api/uploads/{shown}")
    assert served.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in served.content
    picture = {
        **block("image", 40, 40, {"upload": shown, "ratio": 1, "cut": [0, 0, 0, 0]}),
        "x": 40,
        "w": 40,
    }
    mine = sheet(client, [picture])
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    scale = 4
    bitmap = pypdfium2.PdfDocument(res.content)[0].render(scale=scale, rev_byteorder=True)

    def seen(x, y):
        col, row = (int(mm * scale * 72 / 25.4) for mm in (x, y))
        start = row * bitmap.stride + col * bitmap.n_channels
        return bytes(bitmap.buffer[start : start + 3])

    darkest = 255
    for y in range(42, 78):
        for x in range(42, 78):
            darkest = min(darkest, max(seen(x, y)))
    assert darkest < 40
    assert min(seen(150, 250)) > 240


def test_the_sachunterricht_tab_places_a_picture_and_undo_brings_it_back(editor):
    client = user()
    page = editor(box("s", "symbol", {"code": "270F"}), client=client)
    pick(page, "s")
    page.get_by_role("tab", name="Sachunterricht").click()
    expect(page.get_by_role("heading", name="Körper")).to_be_visible()
    page.get_by_label("Sachunterricht suchen").fill("beschriften")
    page.get_by_role("button", name="Fahrrad", exact=True).click()
    expect(page.locator(".picture img")).to_be_visible()
    expect(page.get_by_role("button", name="Zuschneiden")).to_be_visible()
    held = [b for b in saved(page, client) if b["type"] == "image"]
    assert len(held) == 1
    assert held[0]["props"]["cut"] == [0, 0, 0, 0]
    assert held[0]["props"]["ratio"] == pytest.approx(held[0]["w"] / held[0]["h"], rel=0.02)
    assert held[0]["z"] > 1
    page.get_by_label("Rückgängig", exact=True).click()
    expect(page.locator(".picture")).to_have_count(0)
    page.get_by_label("Wiederholen", exact=True).click()
    expect(page.locator(".picture img")).to_be_visible()
    again = [b for b in saved(page, client) if b["type"] == "image"]
    assert len(again) == 1
