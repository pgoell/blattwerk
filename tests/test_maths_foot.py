"""A maths block never grows past the foot of the page from the panel or the painter (issue #473).

The panel refuses a change that would make the block taller and end below the paper's edge: nothing
changes, and a line says why. A block that already ends below the edge says so. The PDF has every
task it was asked for. Each test names the case it proves.
"""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import math

from playwright.sync_api import expect
from ui import at

FOOT = 297  # the page's height in mm
PT = 25.4 / 72  # mm per point, as sheet.tsx


def height(props):
    """The height in mm the app gives a maths block with these props, as sheet.tsx mathsHeight."""
    fams = {}
    for e in props["exercises"]:
        if "sign" not in e and e.get("family") is not None:
            fams[e["family"]] = fams.get(e["family"], 0) + 1
    if fams:
        lines = math.ceil(len(fams) / props["columns"])
        return max(
            10, math.floor(lines * (max(fams.values()) * 1.8 + 0.9) * props["size"] * PT + 0.5)
        )
    lines = math.ceil(len(props["exercises"]) / props["columns"])
    rows = max(
        [0]
        + [0 if "sign" in e else (e.get("grid") or {}).get("rows", 0) for e in props["exercises"]]
    )
    per = (rows + 1) * 5 if props["format"] == "written" else props["size"] * PT * 2.4
    return max(10, math.floor(lines * per + 0.5))


def click(name):
    return lambda page: page.get_by_label(name).click()


def panel(name):
    return lambda page: page.locator(".panel").get_by_role("button", name=name, exact=True).click()


def asked(action):
    """The action, and the answer to it: the new exercises have come from the server."""

    def run(page):
        with page.expect_response(lambda r: r.url.endswith("/api/maths")):
            action(page)

    return run


def refusal(page):
    expect(page.locator('[data-foot="full"]')).to_be_visible()


def on_sheet(page, name):
    """The block ends on the sheet: its bottom is at most the sheet's bottom, 1 mm of slack."""
    block = at(page, name).bounding_box()
    sheet = page.locator(".sheet").first.bounding_box()
    assert block["y"] + block["height"] <= sheet["y"] + sheet["height"] + 1, (
        "the block ends below the sheet"
    )


def tasks(page):
    return page.locator(".panel .seg output")


# Two frames: what a page answer brings is on the screen by then.
FRAMES = "() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))"
