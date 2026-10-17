"""The recipes in docs/okf/recipes: each doc passes the schema, saves, previews and prints clean."""

import json
import re
from pathlib import Path

import httpx
import pytest
from ui import user

from blattwerk import pdf, schema

ROOT = Path(__file__).parent.parent
RECIPES = sorted(p for p in (ROOT / "docs/okf/recipes").glob("*.md") if p.name != "index.md")
MARGIN = 15
TOLERANCE = 0.5


def doc_of(path):
    """The one JSON block of a recipe."""
    found = re.findall(r"```json\n(.*?)\n```", path.read_text(), re.DOTALL)
    assert len(found) == 1, f"{path.name}: one ```json block, found {len(found)}"
    return json.loads(found[0])


def cookie(client):
    return {"Cookie": f"session={client.cookies['session']}"}


def boxes_of(doc):
    return [b for page in doc["pages"] for b in page["blocks"]]


def paper_of(doc, page):
    """The paper of a page in mm, width and height: Quer when the page or the sheet says so."""
    quer = page.get("landscape", doc.get("landscape", False))
    return (297, 210) if quer else (210, 297)


def assert_clear(rects, label, paper):
    """Each rect (x, y, w, h) lies within the margin of the paper and no two rects meet."""
    paper_w, paper_h = paper
    for name, (x, y, w, h) in rects.items():
        assert x >= MARGIN - TOLERANCE, f"{label} {name}: {x} mm from the left edge"
        assert y >= MARGIN - TOLERANCE, f"{label} {name}: {y} mm from the top edge"
        assert x + w <= paper_w - MARGIN + TOLERANCE, f"{label} {name}: past the right margin"
        assert y + h <= paper_h - MARGIN + TOLERANCE, f"{label} {name}: past the bottom margin"
    names = list(rects)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ax, ay, aw, ah = rects[a]
            bx, by, bw, bh = rects[b]
            meet = ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
            assert not meet, f"{label}: {a} and {b} overlap"


def drawn_boxes(browser_page, doc):
    """Per page of the print, each block the page draws: its box (x, y, w, h) in mm, and whether
    its content fits."""
    widths = [paper_of(doc, page)[0] for page in doc["pages"]]
    return browser_page.evaluate(
        """(widths) => [...document.querySelectorAll('.print .paper')].map((paper, i) => {
            const p = paper.getBoundingClientRect();
            const k = widths[i] / p.width;
            const out = {};
            for (const el of paper.querySelectorAll('.block[data-block]')) {
                const r = el.getBoundingClientRect();
                out[el.dataset.block] = {
                    box: [(r.left - p.left) * k, (r.top - p.top) * k, r.width * k, r.height * k],
                    fits: el.scrollHeight <= el.clientHeight + 2,
                    size: [el.scrollHeight, el.clientHeight],
                    text: el.innerText,
                };
            }
            return out;
        })""",
        widths,
    )


@pytest.mark.parametrize("path", RECIPES, ids=lambda p: p.stem)
def test_recipe(path, server, browser):
    doc = doc_of(path)
    assert schema.problems(doc) == []

    client = user()
    saved = client.post("/api/sheets", json={"title": path.stem, "doc": doc})
    assert saved.status_code == 200, saved.text
    sheet_id = saved.json()["id"]

    preview = httpx.post(
        f"{server}/api/preview.png", json={"doc": doc}, headers=cookie(client), timeout=60
    )
    assert preview.status_code == 200

    blocks = boxes_of(doc)
    for n, page_doc in enumerate(doc["pages"], 1):
        assert_clear(
            {b["id"]: (b["x"], b["y"], b["w"], b["h"]) for b in page_doc["blocks"]},
            f"doc page {n}",
            paper_of(doc, page_doc),
        )

    context = browser.new_context(
        viewport={"width": 1400, "height": 1400},
        extra_http_headers={"X-Render-Token": pdf.new_token(sheet_id)},
    )
    try:
        page = context.new_page()
        page.emulate_media(media="print")
        page.goto(f"{server}/druck/{sheet_id}")
        page.wait_for_selector("body.ready", state="attached", timeout=30000)
        if path.stem == "lernwoerter-silbenboegen":
            # The splitter loads after the page is ready; `unsplit` stands until the bows are drawn.
            page.wait_for_selector(".unsplit", state="detached", timeout=15000)
            bows = page.locator(".print .syl").count()
            # The top of each word's text on the page, found by its text node.
            tops = page.evaluate(
                """(words) => words.map((word) => {
                    const ruling = document.querySelector('.print .block[data-block] .ruling');
                    const walk = document.createTreeWalker(ruling.closest('.block'),
                        NodeFilter.SHOW_TEXT);
                    while (walk.nextNode()) {
                        const at = walk.currentNode.data.indexOf(word);
                        if (at >= 0) {
                            const range = document.createRange();
                            range.setStart(walk.currentNode, at);
                            range.setEnd(walk.currentNode, at + word.length);
                            return [word, range.getBoundingClientRect().top];
                        }
                    }
                    return [word, null];
                })""",
                ["Hase", "Igel", "Maus", "Katze"],
            )
        drawn_pages = drawn_boxes(page, doc)
    finally:
        context.close()

    drawn = {k: v for found in drawn_pages for k, v in found.items()}
    assert set(drawn) == {b["id"] for b in blocks}
    for n, (found, page_doc) in enumerate(zip(drawn_pages, doc["pages"], strict=True), 1):
        assert_clear(
            {k: tuple(v["box"]) for k, v in found.items()},
            f"print page {n}",
            paper_of(doc, page_doc),
        )
    overflowing = [k for k, v in drawn.items() if not v["fits"]]
    assert overflowing == [], (
        f"content overflows its box: {[drawn[k]['size'] for k in overflowing]}"
    )

    # The generated blocks draw their content: an empty block prints no clock, digit or word.
    text_of = {b["type"]: drawn[b["id"]]["text"] for b in blocks if b["type"] != "text"}
    if path.stem == "uhrzeiten-lesen":
        # Each face's 1 to 12, not only the answer line under it.
        faces = re.findall(r"\d+", text_of["uhr"])
        assert all(str(n) in faces for n in range(1, 13)), text_of["uhr"]
    if path.stem == "suchsel-tiere":
        # The grid's 12 x 10 letters, and the list's words under it.
        assert len(re.findall(r"[A-ZÄÖÜ]", text_of["suchsel"])) >= 120, text_of["suchsel"]
        assert "HUND" in text_of["suchsel"], text_of["suchsel"]

    if path.stem == "plusaufgaben-bis-20":
        maths = next(b for b in blocks if b["type"] == "maths")
        check = next(b for b in blocks if b["type"] == "selbstkontrolle")
        assert check["props"]["links"] == [maths["id"]]
        assert isinstance(maths["props"]["seed"], int)
        assert len(maths["props"]["exercises"]) >= 1

    if path.stem == "lernwoerter-silbenboegen":
        ruling = next(b for b in blocks if b["type"] == "ruling")
        assert ruling["props"]["syllables"] is True
        # Ha-se, I-gel, Mau-s, Kat-ze: 7 syllables, one bow each.
        assert bows == 7
        # Each word on its own row: the paragraph's top differs from the others.
        row_tops = [top for _, top in tops]
        assert None not in row_tops, tops
        assert len(set(row_tops)) == 4, row_tops
