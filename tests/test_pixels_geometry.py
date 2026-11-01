"""Table lines, cell boxes, a row of text and a picture's edge lie where they print."""

import pytest
from pixels import (
    LOADED,
    dark,
    grey,
    runs,
)
from playwright.sync_api import expect
from test_pixels import (
    EDGE,
    LONG,
    PLACES,
    ROWS,
    at,
    blocks,
    fuller,
    lower,
    right_edge,
)
from ui import (
    TEXT,
    pick,
    sheet,
    user,
)

from blattwerk import pdf


def test_a_tables_lines_are_as_wide_and_as_dark_as_they_print(browser, server):
    """A4"""
    client = user()
    page = blocks("table", client)
    screen, printed = grey(browser, server, client, page)
    x, y, w, h = (page[0][side] for side in "xywh")
    # Clear of the letters: a strip down the first column and one along the first row.
    for part, down in (
        ((x + 10, y - 3, x + 14, y + h + 3), True),
        ((x - 3, y + 1, x + w + 3, y + 2), False),
    ):
        shown, paper = (runs(dark(picture, part, down)) for picture in (screen, printed))
        assert len(shown) == len(paper) == 3
        for (_, darkest, ink), (_, on_paper, printed_ink) in zip(shown, paper, strict=True):
            # The ink is the line's width in pixels times its darkness. pdfium fills every pixel a
            # line touches, half a pixel more than the browser draws: 2.2 against 1.8.
            assert abs(darkest - on_paper) < 0.05, (darkest, on_paper)
            assert abs(ink - printed_ink) < 0.5, (ink, printed_ink)


def test_a_tables_cells_lie_where_they_print(browser, server):
    """I7"""
    client = user()
    mine = sheet(client, fuller("table", client))["id"]
    # A sharp screen, as an iPad has: there WebKit rounds a border under a pixel down to half.
    context = browser.new_context(device_scale_factor=2)
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    shown = context.new_page()
    shown.goto(f"{server}/blatt/{mine}")
    shown.locator('main.editor[data-ready="1"]').wait_for()
    # The page that prints, at one pixel to a pixel as Chromium prints it.
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    places = [tab.evaluate(f"{LOADED}.then({PLACES})") for tab in (shown, paper)]
    assert len(places[0]) == 32
    for here, there in zip(*places, strict=True):
        assert here == pytest.approx(there, abs=0.01)

    pick(shown, "b60")
    shown.keyboard.press("Enter")
    field = shown.locator(".table textarea")
    expect(field).to_be_focused()
    (left, top, right, low), cell = (
        (b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"])
        for b in (field.bounding_box(), shown.locator('[data-cell="0"]').bounding_box())
    )
    assert cell[0] < left < right < cell[2] and cell[1] < top < low < cell[3]
    paper.close()
    context.close()


@pytest.mark.parametrize(
    "look", [{"font": "sas", "bold": True}, {}], ids=["school script", "andika"]
)
def test_a_row_of_text_lies_as_low_as_it_prints(browser, server, look):
    """A5"""
    client = user()
    page = [at("text", {**TEXT, "text": LONG, **look}, h=120)]
    screen, printed = grey(browser, server, client, page)
    found = lower(screen, printed, page[0])
    assert max(abs(by) for by in found) < ROWS, found


# Where each line's baseline sits, in the page's own pixels. A textarea has no strut to read, so a
# paragraph with its font and line height stands in for the offset inside the box, and the box's
# own top supplies the place.
LINES = """async () => {
    await document.fonts.ready;
    // The lift is applied on the draw after the fonts load. `data-baselines` is set on that draw.
    if (document.documentElement.dataset.baselines !== "1") {
        await new Promise((done) => {
            const look = new MutationObserver(() => {
                if (document.documentElement.dataset.baselines === "1") {
                    look.disconnect();
                    done();
                }
            });
            look.observe(document.documentElement, { attributes: true, attributeFilter: ["data-baselines"] });
        });
    }
    const page = document.querySelector(".scaled, .paper");
    const box = page.getBoundingClientRect();
    const scale = box.width / page.offsetWidth;
    const textOf = (el) => [...el.childNodes].find((n) => n.nodeType === 3 && n.textContent.length);
    const startsOf = (el) => {
        const node = textOf(el);
        if (!node) return [];
        const range = document.createRange();
        const starts = [];
        let prev = -1e9;
        for (let i = 0; i < node.length; i++) {
            range.setStart(node, i);
            range.setEnd(node, i + 1);
            const r = range.getClientRects()[0];
            if (!r || r.width < 0.1) continue;
            if (r.top > prev + 1) {
                starts.push(i);
                prev = r.top;
            }
        }
        return starts;
    };
    const at = (el, index) => {
        const range = document.createRange();
        range.setStart(textOf(el), index);
        range.collapse(true);
        const strut = document.createElement("span");
        strut.style.cssText = "display:inline-block;width:1px;height:0";
        range.insertNode(strut);
        const y = strut.getBoundingClientRect().top;
        strut.remove();
        el.normalize();
        return y;
    };
    const linesOf = (el) => {
        if (el.tagName !== "TEXTAREA") return startsOf(el).map((i) => at(el, i));
        const cs = getComputedStyle(el);
        const probe = document.createElement("p");
        probe.style.cssText = "position:absolute;visibility:hidden;margin:0;padding:0;white-space:pre-wrap"
            + `;width:${el.clientWidth}px;font:${cs.font};line-height:${cs.lineHeight}`;
        probe.textContent = el.value;
        el.parentElement.append(probe);
        const shift = el.getBoundingClientRect().top - probe.getBoundingClientRect().top;
        const ys = startsOf(probe).map((i) => at(probe, i) + shift);
        probe.remove();
        return ys;
    };
    const out = {};
    for (const block of document.querySelectorAll(".block")) {
        const el = block.querySelector("textarea.written, p.written, .frame > p, .table p");
        const id = block.dataset.id || block.dataset.block;
        if (el && id) out[id] = linesOf(el).map((y) => +((y - box.top) / scale).toFixed(3));
    }
    return out;
}"""


def test_a_lines_baseline_lies_where_it_prints(browser, server, playwright):
    """A text, a school's script and a Lineatur sit on the baseline the print uses (#504)."""
    client = user()
    blocks = [
        at("text", {**TEXT, "text": "Hägen und Nüsse\nliegen im Garten"}, y=20, h=30),
        at(
            "text",
            {**TEXT, "text": "Hägen und Nüsse\nliegen im Garten", "font": "sas", "bold": True},
            y=60,
            h=30,
        ),
        at(
            "ruling",
            {"kind": "l3", "color": "#222222", "text": "Oma\nOpa\nIgel\nNest"},
            y=110,
            h=50,
        ),
        # Schulausgangsschrift is still the fallback while its file loads: its Lineatur must be
        # measured again, or every row keeps the fallback's pixel (#504).
        at(
            "ruling",
            {"kind": "l3", "color": "#222222", "font": "sas", "text": "Oma\nOpa\nIgel\nNest"},
            y=210,
            h=50,
        ),
        at("table", {"cells": [["Hägen"]], "cols": [1], "size": 14, "align": "left"}, y=170, h=24),
        # 24 pt is an exact half pixel of descent. A binary hair under that half must not borrow.
        at("text", {**TEXT, "text": "Hägen und Nüsse\nliegen im Garten", "size": 24}, y=265, h=30),
    ]
    mine = sheet(client, blocks)["id"]
    context = browser.new_context(viewport={"width": 1400, "height": 1400})
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    shown = context.new_page()
    shown.goto(f"{server}/blatt/{mine}")
    shown.locator('main.editor[data-ready="1"]').wait_for()
    screen = shown.evaluate(LINES)
    # The PDF is Chromium even when the screen is WebKit: the same engine page.pdf() uses.
    chrome = playwright.chromium.launch()
    paper = chrome.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    printed = paper.evaluate(LINES)
    paper.close()
    chrome.close()
    context.close()
    found = []
    for name in screen:
        assert name in printed, (name, sorted(printed))
        assert len(screen[name]) == len(printed[name]) > 0, (name, screen[name], printed[name])
        found += [here - there for here, there in zip(screen[name], printed[name], strict=True)]
    # A part of a pixel: what the two engines still round differently. A borrowed pixel is 1.
    assert max(abs(by) for by in found) < 0.2, found


def test_a_picture_ends_where_it_prints(browser, server):
    """A6"""
    client = user()
    page = blocks("picture", client)
    screen, printed = (right_edge(image, page[0]) for image in grey(browser, server, client, page))
    assert abs(screen - printed) < EDGE, (screen, printed)
