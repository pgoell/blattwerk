"""The recipes in docs/okf/recipes: each doc passes the schema, saves, previews and prints clean."""

import json
import re
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import sync_playwright
from ui import user

from blattwerk import pdf, schema

ROOT = Path(__file__).parent.parent
RECIPES = sorted(p for p in (ROOT / "docs/okf/recipes").glob("*.md") if p.name != "index.md")
MARGIN = 15
TOLERANCE = 0.5
PAPER_W, PAPER_H = 210, 297


def doc_of(path):
    """The one JSON block of a recipe."""
    found = re.findall(r"```json\n(.*?)\n```", path.read_text(), re.DOTALL)
    assert len(found) == 1, f"{path.name}: one ```json block, found {len(found)}"
    return json.loads(found[0])


def cookie(client):
    return {"Cookie": f"session={client.cookies['session']}"}


def boxes_of(doc):
    return [b for page in doc["pages"] for b in page["blocks"]]


def assert_clear(rects, label):
    """Each rect (x, y, w, h) lies within the margin and no two rects meet."""
    for name, (x, y, w, h) in rects.items():
        assert x >= MARGIN - TOLERANCE, f"{label} {name}: {x} mm from the left edge"
        assert y >= MARGIN - TOLERANCE, f"{label} {name}: {y} mm from the top edge"
        assert x + w <= PAPER_W - MARGIN + TOLERANCE, f"{label} {name}: past the right margin"
        assert y + h <= PAPER_H - MARGIN + TOLERANCE, f"{label} {name}: past the bottom margin"
    names = list(rects)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ax, ay, aw, ah = rects[a]
            bx, by, bw, bh = rects[b]
            meet = ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
            assert not meet, f"{label}: {a} and {b} overlap"


def drawn_boxes(browser_page):
    """Each block the print page draws: its box (x, y, w, h) in mm, and whether its content fits."""
    return browser_page.evaluate(
        """() => {
            const paper = document.querySelector('.print .paper');
            const p = paper.getBoundingClientRect();
            const k = 210 / p.width;
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
        }"""
    )


@pytest.mark.parametrize("path", RECIPES, ids=lambda p: p.stem)
def test_recipe(path, server):
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
    assert_clear({b["id"]: (b["x"], b["y"], b["w"], b["h"]) for b in blocks}, "doc")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(
                viewport={"width": 1400, "height": 1400},
                extra_http_headers={"X-Render-Token": pdf.new_token(sheet_id)},
            )
            page = context.new_page()
            page.emulate_media(media="print")
            page.goto(f"{server}/druck/{sheet_id}")
            page.wait_for_selector("body.ready", state="attached", timeout=30000)
            drawn = drawn_boxes(page)
            page.close()
        finally:
            browser.close()

    assert set(drawn) == {b["id"] for b in blocks}
    assert_clear({k: tuple(v["box"]) for k, v in drawn.items()}, "print")
    overflowing = [k for k, v in drawn.items() if not v["fits"]]
    assert overflowing == [], (
        f"content overflows its box: {[drawn[k]['size'] for k in overflowing]}"
    )

    if path.stem == "plusaufgaben-bis-20":
        maths = next(b for b in blocks if b["type"] == "maths")
        check = next(b for b in blocks if b["type"] == "selbstkontrolle")
        assert check["props"]["links"] == [maths["id"]]
        assert isinstance(maths["props"]["seed"], int)
        assert len(maths["props"]["exercises"]) >= 1

    if path.stem == "lernwoerter-silbenboegen":
        ruling = next(b for b in blocks if b["type"] == "ruling")
        assert ruling["props"]["syllables"] is True
        # Known gap: the page draws bows only under a ruling's own text, not under its list rows.
        for word in doc["words"]:
            assert word in drawn[ruling["id"]]["text"], word
