"""A Zahlenmauer and a Rechendreieck keep their content inside their box in print, at every size."""

import itertools
import uuid

from ui import user

from blattwerk import pdf, schema

# A small box, and a full page's height and width.
BOXES = [(20, 10), (180, 267)]
# Each block on its own page, so one sheet holds every case.
PAGE = {"x": 15, "y": 15, "z": 1, "locked": False}


def sheet_of(cases):
    """One page per case: one block of the type, its props and the box size."""
    pages = []
    for type_, props, (w, h) in cases:
        block = {"id": str(uuid.uuid4()), "type": type_, "w": w, "h": h, "props": props, **PAGE}
        pages.append({"blocks": [block]})
    return {"pages": pages, "guides": {"x": [], "y": []}, "grid": 0}


def overflow_of(browser, server, sheet_id, blocks):
    """Each drawn block whose content runs past its box, with the sizes that show it."""
    context = browser.new_context(
        viewport={"width": 1400, "height": 1400},
        extra_http_headers={"X-Render-Token": pdf.new_token(sheet_id)},
    )
    try:
        page = context.new_page()
        page.emulate_media(media="print")
        page.goto(f"{server}/druck/{sheet_id}")
        page.wait_for_selector("body.ready", state="attached", timeout=30000)
        drawn = page.evaluate(
            """() => {
                const out = {};
                for (const el of document.querySelectorAll('.print .block[data-block]')) {
                    out[el.dataset.block] = {
                        content: [el.scrollWidth, el.scrollHeight],
                        box: [el.clientWidth, el.clientHeight],
                    };
                }
                return out;
            }"""
        )
    finally:
        context.close()
    assert set(drawn) == {b["id"] for b in blocks}, f"drawn {len(drawn)} of {len(blocks)} blocks"
    return [
        f"{b['type']} {b['props']} box {drawn[b['id']]['box']} content {drawn[b['id']]['content']}"
        for b in blocks
        if drawn[b["id"]]["content"][0] > drawn[b["id"]]["box"][0]
        or drawn[b["id"]]["content"][1] > drawn[b["id"]]["box"][1]
    ]


def check(server, browser, title, cases):
    doc = sheet_of(cases)
    assert schema.problems(doc) == []
    client = user()
    saved = client.post("/api/sheets", json={"title": title, "doc": doc})
    assert saved.status_code == 200, saved.text
    sheet_id = saved.json()["id"]
    blocks = [b for page in doc["pages"] for b in page["blocks"]]
    failing = overflow_of(browser, server, sheet_id, blocks)
    listed = "; ".join(failing)
    assert failing == [], f"content runs past its box in {len(failing)} blocks: {listed}"


def test_zahlenmauer_fits_its_box(server, browser):
    cases = []
    for base, count, columns, (w, h) in itertools.product((3, 4, 5), (1, 12), (1, 2, 3, 4), BOXES):
        props = {
            "base": base,
            "count": count,
            "columns": columns,
            "max": 20,
            "op": "+",
            "given": "base",
            "empty": False,
            "seed": 7,
        }
        cases.append(("zahlenmauer", props, (w, h)))
    check(server, browser, "zahlenmauer-fits", cases)


def test_rechendreieck_fits_its_box(server, browser):
    cases = []
    for count, columns, given, (w, h) in itertools.product(
        (1, 12), (1, 2, 3, 4), ("inner", "outer", "mix"), BOXES
    ):
        props = {
            "count": count,
            "columns": columns,
            "max": 20,
            "given": given,
            "empty": False,
            "seed": 7,
        }
        cases.append(("rechendreieck", props, (w, h)))
    check(server, browser, "rechendreieck-fits", cases)
