"""A doc saved with a wrong prop prints anyway: the page draws it with the prop cut, and the stored
doc keeps it (#691)."""

import json
from pathlib import Path

import httpx
import pytest
from ui import MATHS, RECT, RULING, TABLE, TEXT, block, upload, user

from blattwerk import pdf

CORPUS = Path(__file__).parent / "corpus"
SUCHSEL = {
    "words": ["HAUS"],
    "cols": 10,
    "rows": 10,
    "ways": "down",
    "caps": True,
    "umlauts": True,
    "show": "words",
    "seed": 3,
}
ZAHLENMAUER = {
    "base": 3,
    "count": 4,
    "columns": 2,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 3,
}
RECHENDREIECK = {"count": 4, "columns": 4, "max": 20, "given": "inner", "empty": False, "seed": 3}
ZAHLENSTRAHL = {
    "start": 0,
    "end": 20,
    "minor": 1,
    "major": 5,
    "labels": "major",
    "size": 12,
    "cut": False,
    "tasks": "random",
    "boxes": 3,
    "arrows": 0,
    "jumps": False,
    "seed": 3,
}
HUNDERTERFELD = {
    "look": "tafel",
    "from": 1,
    "show": "all",
    "hide": 20,
    "tint": "none",
    "times": 2,
    "line": 1,
    "color": 1,
    "cut": False,
    "shape": [34, 43],
    "given": 44,
    "fill": "count",
    "dots": 0,
    "seed": 3,
}
UHR = {
    "numbers": "all",
    "minutes": True,
    "ring": False,
    "task": "read",
    "answer": "box",
    "format": "12",
    "region": "nach",
    "count": 4,
    "cols": 4,
    "step": 15,
    "fill": "random",
    "seed": 3,
}
SELBSTKONTROLLE = {
    "form": "mixed",
    "links": [],
    "word": "",
    "title": "Selbstkontrolle",
    "size": 14,
    "turn": "none",
    "seed": 3,
}

# One wrong prop per block type. The image's upload id is added in the test.
WRONG = {
    "text": {**TEXT, "text": 5},
    "shape": {**RECT, "text": 5},
    "ruling": {**RULING, "color": 5},
    "name": {"fields": "x"},
    "points": {"max": "x"},
    "symbol": {"code": 5},
    "image": {"ratio": "x", "cut": [0, 0, 0, 0]},
    "maths": {**MATHS, "max": "x"},
    "table": {**TABLE, "cells": "x"},
    "suchsel": {**SUCHSEL, "cols": "x"},
    "zahlenmauer": {**ZAHLENMAUER, "base": "x"},
    "rechendreieck": {**RECHENDREIECK, "max": "x"},
    "zahlenstrahl": {**ZAHLENSTRAHL, "start": "x"},
    "hunderterfeld": {**HUNDERTERFELD, "from": "x"},
    "uhr": {**UHR, "count": "x"},
    "selbstkontrolle": {**SELBSTKONTROLLE, "size": "x"},
}


def put(server, client, *blocks):
    """Saves a sheet of the blocks through the API, with a token of the client's account."""
    token = client.post("/api/tokens", json={"name": "x"}).json()["token"]
    head = {"Authorization": f"Bearer {token}"}
    doc = {"pages": [{"blocks": list(blocks)}], "guides": {"x": [], "y": []}, "grid": 0}
    made = httpx.post(f"{server}/api/sheets", json={"title": "Falsch", "doc": doc}, headers=head)
    assert made.status_code == 200
    return made.json(), head


def get(server, head, sheet_id, what, **params):
    return httpx.get(
        f"{server}/api/sheets/{sheet_id}/{what}", params=params, headers=head, timeout=60
    )


@pytest.mark.parametrize("kind", list(WRONG))
def test_one_wrong_prop_prints(server, monkeypatch, kind):
    monkeypatch.setattr(pdf, "DRAW", 5000)
    client = user()
    props = WRONG[kind]
    if kind == "image":
        props = {"upload": upload(client), **props}
    made, head = put(server, client, block(kind, 20, 60, props))
    res = get(server, head, made["id"], "pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    res = get(server, head, made["id"], "preview.png")
    assert res.status_code == 200
    assert res.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_maths_with_a_wrong_item_in_exercises_prints(server, monkeypatch):
    monkeypatch.setattr(pdf, "DRAW", 5000)
    client = user()
    made, head = put(server, client, block("maths", 20, 60, {**MATHS, "exercises": [5]}))
    assert get(server, head, made["id"], "pdf").status_code == 200


def test_the_stored_doc_keeps_its_wrong_prop(server, monkeypatch):
    monkeypatch.setattr(pdf, "DRAW", 5000)
    client = user()
    made, head = put(server, client, block("text", 20, 60, {**TEXT, "text": 5}))
    assert get(server, head, made["id"], "pdf").status_code == 200
    stored = httpx.get(f"{server}/api/sheets/{made['id']}", headers=head).json()
    assert stored["doc"] == made["doc"]
    assert stored["doc"]["pages"][0]["blocks"][0]["props"]["text"] == 5


@pytest.mark.parametrize("varianten", [1, 2])
def test_pdf_of_a_doc_the_page_cannot_draw_is_422(server, monkeypatch, varianten):
    # Nothing draws in 1 ms, so the page is one that never gets its body.ready.
    monkeypatch.setattr(pdf, "DRAW", 1)
    client = user()
    made, head = put(server, client, block("text", 20, 60, TEXT))
    res = get(server, head, made["id"], "pdf", varianten=varianten)
    assert res.status_code == 422
    assert res.json()["detail"]["problems"][0].startswith("doc: the page could not be drawn")


@pytest.mark.parametrize("file", sorted(CORPUS.glob("*.json")), ids=lambda file: file.stem)
def test_mended_leaves_a_sound_doc_as_it_is(file):
    from blattwerk.schema import mended

    doc = json.loads(file.read_text())["doc"]
    assert mended(doc) is doc
