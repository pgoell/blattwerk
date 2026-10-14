"""Every built-in template prints: one page for each, three for the Klassenarbeit."""

import io
from typing import cast

import httpx
import pytest
from pypdf import PdfReader
from ui import sheet, user

from blattwerk.templates import BUILT_IN

NAMES = [cast(dict, t)["name"] for t in BUILT_IN]
WORDS = ["Hund", "Katze", "Maus", "Baum", "Haus", "Ball"]


def template(name):
    return cast(dict, next(t for t in BUILT_IN if t["name"] == name))


def printed(server, client, made):
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{made['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(res.content))
    text = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    return len(reader.pages), text


@pytest.mark.parametrize("name", NAMES)
def test_template_prints(server, name):
    client = user()
    pages = template(name)["doc"]["pages"]
    words = WORDS if name == "Lernwörter" else None
    made = sheet(client, *pages, words=words)
    count, text = printed(server, client, made)
    assert count == (3 if name == "Klassenarbeit" else 1)
    if name == "Lernwörter":
        assert "Hund" in text


def test_wochenplan_prints_its_days(server):
    client = user()
    made = sheet(client, *template("Wochenplan")["doc"]["pages"])
    _, text = printed(server, client, made)
    assert "Montag" in text and "Freitag" in text


def blocks_of(name, kind):
    return [
        b for page in template(name)["doc"]["pages"] for b in page["blocks"] if b["type"] == kind
    ]


@pytest.mark.parametrize("name", [f"Rechenblatt Klasse {n}" for n in range(1, 5)])
def test_rechenblatt_numbers_stay_in_their_zahlenraum(name):
    maths = blocks_of(name, "maths")
    assert maths
    for block in maths:
        props = block["props"]
        assert props["exercises"]
        for exercise in props["exercises"]:
            numbers = [
                v for v in exercise.values() if isinstance(v, int) and not isinstance(v, bool)
            ]
            assert all(0 <= n <= props["max"] for n in numbers), exercise
            # The 1x1 to 100 has factors up to 10; the written multiplication of Klasse 4 has more.
            if exercise["op"] == "*" and props["max"] == 100:
                assert exercise["a"] <= 10 and exercise["b"] <= 10, exercise


@pytest.mark.parametrize("name", NAMES)
def test_no_two_blocks_of_a_page_overlap(name):
    # Boxes that touch along an edge, or a line with no height, do not count.
    for page in template(name)["doc"]["pages"]:
        boxes = page["blocks"]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                across = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
                down = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
                assert not (across > 0 and down > 0), (name, a["id"], b["id"])


def test_wochenplan_day_is_one_word(server):
    client = user()
    made = sheet(client, *template("Wochenplan")["doc"]["pages"])
    _, text = printed(server, client, made)
    assert "Donnerstag" in text.split()
