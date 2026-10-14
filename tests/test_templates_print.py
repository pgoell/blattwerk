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


@pytest.mark.parametrize(
    ("name", "limit"),
    [("Rechenblatt Klasse 1", 20), ("Rechenblatt Klasse 2", 100), ("Rechenblatt Klasse 3", 1000)],
)
def test_rechenblatt_numbers_stay_in_their_zahlenraum(name, limit):
    maths = [b for b in template(name)["doc"]["pages"][0]["blocks"] if b["type"] == "maths"]
    assert len(maths) == 1
    props = maths[0]["props"]
    assert props["max"] == limit
    assert props["exercises"]
    for exercise in props["exercises"]:
        numbers = [v for k, v in exercise.items() if isinstance(v, int) and not isinstance(v, bool)]
        assert all(0 <= n <= limit for n in numbers), exercise
