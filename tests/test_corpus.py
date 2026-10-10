"""The corpus: old sheets and templates as teachers stored them, blanked by scripts/corpus.py.

Each must open, save back as it was, and print as it shows. The repo is public, so two tests
watch what the files hold: one of their shape, which runs everywhere, and one against a copy of
the database they were made from, which runs where BLATTWERK_CORPUS_SOURCE names that copy.
"""

import importlib.util
import json
import os
import re
import sqlite3
from pathlib import Path

import pytest
from pixels import LIMIT, diff, screen_and_print
from playwright.sync_api import expect
from ui import sheet, user

ROOT = Path(__file__).parent.parent
CORPUS = Path(__file__).parent / "corpus"
FILES = sorted(CORPUS.glob("*.json"))
SOURCE = os.environ.get("BLATTWERK_CORPUS_SOURCE")
each = pytest.mark.parametrize("file", FILES, ids=lambda file: file.stem)

spec = importlib.util.spec_from_file_location("corpus", ROOT / "scripts" / "corpus.py")
assert spec and spec.loader
corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)

UUID = "[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}"
# Every key the files may hold, and every string that may stand unblanked under a key. Written
# down here and not read from the script, so a script that keeps more fails here first.
KEYS = {"title", "name", "doc", "pages", "blocks", "guides", "grid", "id", "type", "props"}
KEYS |= {"x", "y", "w", "h", "z", "locked", "mark", "text", "size", "align", "font", "bold"}
KEYS |= {"color", "fill", "kind", "max", "stroke", "strokeWidth"}
KEPT = {
    "id": f"{UUID}|vorlage-[0-9]+",
    "type": "text|shape|ruling|name|points",
    "kind": "rect|l1|k7",
    "align": "left|center",
    "font": "sas",
    "color": "#555555",
    "fill": "none",
    "stroke": "#222222|#ffffff",
    "mark": r"1\.",
}
# A doc no teacher wrote, with one of all that the blanking has to tell apart.
MADE = {
    "grid": 5,
    "guides": {"x": [10.5], "y": []},
    "pages": [
        {
            "landscape": True,
            "blocks": [
                {
                    "id": "0850d336-02bc-4595-ae97-997ce26ab931",
                    "type": "text",
                    "x": 15,
                    "y": 20.5,
                    "locked": False,
                    "mark": "a)",
                    "props": {
                        "text": "Über 12 Äpfel,\nStraße 7b!",
                        "align": "center",
                        "color": "#ff0000",
                        "font": "Comic Sans",
                        "rich": [
                            {
                                "list": "bullet",
                                "runs": [{"text": "Öl <b>3</b>", "bold": True, "color": "red"}],
                            }
                        ],
                    },
                },
                {
                    "id": "Anna-Lena",
                    "type": "table",
                    "mark": "Nr. 1",
                    "props": {
                        "cells": [["Hund", "2"], ["", "Maus"]],
                        "line": "none",
                        "new": "Geheim",
                    },
                },
                {
                    "id": "vorlage-3",
                    "type": "image",
                    "props": {
                        "upload": 41,
                        "ratio": 1.5,
                        "cut": [0, 0.1, 0, 0],
                        "src": "data:image/png;base64,iVBORw0KGgo=",
                        "alt": "Mein Hund",
                    },
                },
            ],
        }
    ],
}
BLANK = {
    "grid": 5,
    "guides": {"x": [10.5], "y": []},
    "pages": [
        {
            "landscape": True,
            "blocks": [
                {
                    "id": "0850d336-02bc-4595-ae97-997ce26ab931",
                    "type": "text",
                    "x": 15,
                    "y": 20.5,
                    "locked": False,
                    "mark": "a)",
                    "props": {
                        "text": "Xxxx 00 Xxxxx,\nXxxxxx 0x!",
                        "align": "center",
                        "color": "#ff0000",
                        "font": "Xxxxx Xxxx",
                        "rich": [
                            {
                                "list": "bullet",
                                "runs": [{"text": "Xx <x>0</x>", "bold": True, "color": "xxx"}],
                            }
                        ],
                    },
                },
                {
                    "id": "Xxxx-Xxxx",
                    "type": "table",
                    "mark": "Xx. 0",
                    "props": {
                        "cells": [["Xxxx", "0"], ["", "Xxxx"]],
                        "line": "none",
                        "new": "Xxxxxx",
                    },
                },
                {
                    "id": "vorlage-3",
                    "type": "image",
                    "props": {"ratio": 1.5, "cut": [0, 0.1, 0, 0], "upload": 0},
                },
            ],
        }
    ],
}


def test_the_blanking_turns_letters_to_x_and_digits_to_0_and_replaces_a_picture():
    assert corpus.blank(MADE) == BLANK
    assert corpus.blanked("Jörg Weiß, 4a") == "Xxxx Xxxx, 0x"


def layout(value, key=""):
    """The value with each string that is no layout told by its length alone."""
    if isinstance(value, str):
        return value if corpus.kept(key, value) else len(value)
    if isinstance(value, list):
        return [layout(item, key) for item in value]
    if isinstance(value, dict):
        return {k: layout(v, k) for k, v in value.items()}
    return value


def test_the_blanking_keeps_what_lays_the_sheet_out():
    """Places, sizes, kinds, colours and fonts stay, and a text keeps its length."""
    text, table, _ = blocks(MADE)
    doc = {**MADE, "pages": [{"blocks": [text, table]}]}
    blank = corpus.blank(doc)
    assert layout(blank) == layout(doc)
    assert list(corpus.strings(blank)).count(("color", "#ff0000")) == 1
    # A second pass finds nothing left to blank.
    assert corpus.blank(blank) == blank


def test_the_corpus_holds_sheets_and_a_template():
    assert [f.name for f in FILES if f.name.startswith("sheet-")]
    assert [f.name for f in FILES if f.name.startswith("template-")]
    for file in FILES:
        assert re.fullmatch(r"(sheet|template)-[0-9]+\.json", file.name)
        made = json.loads(file.read_text())
        assert set(made) == {"title" if file.name.startswith("sheet") else "name", "doc"}
        assert made["doc"]["pages"]


def keys(value):
    for k, v in value.items() if isinstance(value, dict) else []:
        yield k
        yield from keys(v)
    for item in value if isinstance(value, list) else []:
        yield from keys(item)


def blocks(doc):
    return [b for page in doc["pages"] for b in page["blocks"]]


@each
def test_a_corpus_file_holds_no_word_but_layout(file):
    """The shape, which needs no database: only known keys, known layout words, and x and 0."""
    made = json.loads(file.read_text())
    assert set(keys(made)) <= KEYS
    for key, text in corpus.strings(made):
        if not (key in KEPT and re.fullmatch(KEPT[key], text)):
            assert re.fullmatch(r"[xX0\W_]*", text), f"under {key}"
    # A picture shows upload 0, which no one has.
    assert all(b["props"]["upload"] == 0 for b in blocks(made["doc"]) if b["type"] == "image")


def words(texts):
    """The words of three letters and more, but for those of x alone."""
    found = {w for text in texts for w in re.findall(r"[^\W\d_]{3,}", text.casefold())}
    return {w for w in found if w.strip("x")}


def test_no_live_word_is_in_the_corpus():
    """Against the copy of the database: the files are the script's, and hold none of its words."""
    if not SOURCE:
        pytest.skip("BLATTWERK_CORPUS_SOURCE names no copy of the database the corpus is from")
    con = sqlite3.connect(f"file:{Path(SOURCE).resolve()}?mode=ro", uri=True)
    rows = list(corpus.rows(con))
    assert [file for file, *_ in rows] == [f.name for f in FILES]
    free = [
        part for (email,) in con.execute("SELECT email FROM users") for part in email.split("@")
    ]
    for file, name, text, doc in rows:
        # The file is what the script makes of the row today.
        assert json.loads((CORPUS / file).read_text()) == {
            name: corpus.blanked(text),
            "doc": corpus.blank(doc),
        }
        free += [text, *(s for key, s in corpus.strings(doc) if not corpus.kept(key, s))]
    live = words(free)
    hay = [f.name for f in FILES]
    for file in FILES:
        made = json.loads(file.read_text())
        hay += [s for key, s in corpus.strings(made) if not corpus.kept(key, s)]
    hay = "\n".join(hay).casefold()
    # The README's few lines are prose, so there a whole word counts.
    prose = len(live & words([(CORPUS / "README.md").read_text()]))
    found = sum(word in hay for word in live)
    # Counted first, and the words dropped: a failure must print a number, never a teacher's word.
    looked = len(live)
    del live, free, rows, hay
    assert (found, prose) == (0, 0)
    print(f"\n{looked} live words looked for in {len(FILES)} corpus files: none found")


@pytest.fixture
def desk(browser, server):
    """Opens the editor on a stored sheet and gives its page and the errors it logs."""
    contexts = []

    def start(client, sheet_id):
        context = browser.new_context(viewport={"width": 1400, "height": 1000})
        contexts.append(context)
        # The tour would lie over the sheet, and the panel with the templates starts shut.
        context.add_init_script("localStorage.setItem('tour', '1')")
        context.add_init_script("localStorage.setItem('theme', '')")
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        context.add_cookies(
            [{"name": "session", "value": client.cookies["session"], "url": server}]
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda said: said.type == "error" and errors.append(said.text))
        page.goto(f"{server}/blatt/{sheet_id}")
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
        return page, errors

    yield start
    for context in contexts:
        context.close()


def stored(file):
    """The file's sheet as the server holds it, for a new user. A template is stored as one, and
    the sheet is empty."""
    made = json.loads(file.read_text())
    client = user()
    if "name" in made:
        mine = client.post("/api/templates", json=made).json()["id"]
        held = [t for t in client.get("/api/templates").json() if t["id"] == mine]
        sheet_id = sheet(client, [])["id"]
    else:
        sheet_id = client.post("/api/sheets", json=made).json()["id"]
        held = [client.get(f"/api/sheets/{sheet_id}").json()]
    # The server keeps a document as it comes.
    assert held[0]["doc"] == made["doc"]
    return client, sheet_id, made


def change(page, made):
    """What makes the editor save: a sheet gets another title, and a template takes the place of
    the empty sheet, which is how a template opens."""
    if "name" in made:
        page.locator(".tpl button").get_by_text(made["name"], exact=True).click()
    else:
        page.get_by_label("Titel", exact=True).fill("Anders")


@each
def test_a_corpus_file_opens_with_no_error(desk, file):
    client, sheet_id, made = stored(file)
    page, errors = desk(client, sheet_id)
    if "name" in made:
        change(page, made)
    # The editor lays out every page at once.
    expect(page.locator(".sheet")).to_have_count(len(made["doc"]["pages"]))
    expect(page.locator(".block[data-id]")).to_have_count(len(blocks(made["doc"])))
    assert errors == []


@each
def test_a_corpus_file_saves_back_unchanged(desk, file):
    client, sheet_id, made = stored(file)
    page, errors = desk(client, sheet_id)
    # A change is saved two seconds after it.
    with page.expect_response(lambda res: res.request.method == "PATCH"):
        change(page, made)
    saved = client.get(f"/api/sheets/{sheet_id}").json()
    assert saved["version"] == 2
    assert saved["doc"] == made["doc"]
    assert errors == []


@each
def test_a_corpus_file_prints_as_it_shows(browser, server, file):
    made = json.loads(file.read_text())
    client = user()
    sheet_id = client.post("/api/sheets", json={"title": "Blatt", "doc": made["doc"]}).json()["id"]
    for n in range(len(made["doc"]["pages"])):
        share, _ = diff(*screen_and_print(browser, server, client, sheet_id, n))
        assert share < LIMIT, f"page {n}"
