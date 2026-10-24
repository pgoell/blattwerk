"""The format painter: one block's look carried to the next one picked, in Chromium."""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import re

from playwright.sync_api import expect
from ui import (
    ITEM,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
    maths,
    pick,
    picture,
    saved,
    upload,
)

# All that travels, each unlike what a new text has.
LOOK = {
    "font": "grund",
    "size": 20,
    "bold": True,
    "italic": True,
    "underline": True,
    "color": "#ff0000",
    "spacing": 1.6,
    "align": "right",
    "valign": "bottom",
    "fill": "#00ff00",
    "opacity": 0.5,
    "stroke": "#0000ff",
    "strokeWidth": 2,
    "dash": "dashed",
}
FINE = {**TEXT, **LOOK}
# A shape of 60 by 40 mm with room around it.
ROOM = {"x": 75, "y": 150, "w": 60, "h": 40}


def brush(page):
    return page.get_by_label("Format übertragen", exact=True)


def expect_brush(page, on):
    """Waits until the brush is on or off: the button, the cursor over the desk and the editor."""
    expect(brush(page)).to_have_attribute("aria-pressed", "true" if on else "false")
    desk, main = page.locator(".desk"), page.locator("main.editor")
    if on:
        expect(desk).to_have_css("cursor", "copy")
        expect(main).to_have_class(re.compile(r"\bbrush\b"))
    else:
        expect(desk).not_to_have_css("cursor", "copy")
        expect(main).not_to_have_class(re.compile(r"\bbrush\b"))


def paint(page, source, target, *group):
    """Picks the look of `source` up with one click on the brush and lays it on `target`."""
    pick(page, source)
    brush(page).click()
    expect_brush(page, True)
    at(page, target).click()
    # The painted block is the selected one, with its group, and the brush is spent.
    expect_picked(page, target, *group)
    expect_brush(page, False)


def held(page, client):
    """The props of each block as the server holds them, by the block's name."""
    return {b["id"]: b["props"] for b in saved(page, client)}


def look(props):
    """What of the look these props set. A key they lack counts as one set to nothing."""
    return {key: props.get(key) for key in LOOK}


def whole(page, client):
    """Each block as the server holds it, by the block's name: its numbering and its box too."""
    return {b["id"]: b for b in saved(page, client)}


def marks(page, client):
    """The numbering before each block. A block with none has no `mark` at all."""
    return {b["id"]: b.get("mark", "keins") for b in saved(page, client)}


STAR = {"code": "2B50"}
SCRIPT = {**RULING, "font": "grund", "color": "#ff0000"}
# One block of every type by name, "b" and "c" in one group.
EVERY = ("text", "form", "strich", "bild", "stern", "tabelle", "lines", "rechnen", "name", "punkte")
EVERY = (*EVERY, "b")


def cell(name, kind, props, i, **more):
    """A block 80 mm wide at the `i`th place of two columns, so more of them fit a page."""
    place = {"z": i + 1, "x": 15 + 100 * (i % 2), "y": 20 + 30 * (i // 2), "w": 80}
    return box(name, kind, props, **{**place, **more})


def every(client):
    """One block of every type, each with room of its own, and two texts in a group."""
    kinds = {
        "text": ("text", TEXT),
        "form": ("shape", RECT),
        "strich": ("shape", LINE),
        "bild": ("image", picture(upload(client))["props"]),
        "stern": ("symbol", STAR),
        "tabelle": ("table", TABLE),
        "lines": ("ruling", RULING),
        "rechnen": ("maths", maths(client)),
        "name": ("name", {}),
        "punkte": ("points", {"max": 10}),
        "b": ("text", TEXT),
        # A list, which a brush with no look for a text must leave whole.
        "c": ("text", ITEM),
    }
    return [
        cell(name, kind, props, i, **({"group": ["g"]} if name in ("b", "c") else {}))
        for i, (name, (kind, props)) in enumerate(kinds.items())
    ]


GREY = "rgb(170, 170, 170)"


RED_LINE = "rgb(255, 0, 0)"


def word(page, name, text):
    """The screen box of the first `text` in the block `name`: its middle height and both sides."""
    return page.evaluate(
        """([name, text]) => {
            const el = document.querySelector(`.block[data-id="${name}"]`);
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            for (let node = walker.nextNode(); node; node = walker.nextNode()) {
                const i = node.textContent.indexOf(text);
                if (i < 0) continue;
                const range = document.createRange();
                range.setStart(node, i);
                range.setEnd(node, i + text.length);
                const r = range.getBoundingClientRect();
                return { x: r.left, right: r.right, y: r.top + r.height / 2 };
            }
            return null;
        }""",
        [name, text],
    )


def drag(page, name, text):
    """Presses on the start of `text` in the block `name`, drags across it and lets go."""
    w = word(page, name, text)
    page.mouse.move(w["x"] + 1, w["y"])
    page.mouse.down()
    page.mouse.move(w["right"] - 1, w["y"], steps=5)
    page.mouse.up()


def runs_of(props):
    return [run for para in props.get("rich", []) for run in para["runs"]]


def painted(props):
    """The words of a text that have a bold or a red look of their own, as (words, bold, colour)."""
    return [
        (run["text"], run.get("bold", False), run.get("color"))
        for run in runs_of(props)
        if run.get("bold") or run.get("color")
    ]


# A word "Hallo" in bold red, as the source of a look.
BOLD_RED = [{"runs": [{"text": "Hallo", "bold": True, "color": "#ff0000"}, {"text": " Welt"}]}]


def saved_x(page, client):
    return next(b["x"] for b in saved(page, client) if b["id"] == "a")


def saved_xs(page, client):
    return {b["id"]: b["x"] for b in saved(page, client)}


def group_texts(client, group, extra=False):
    """Texts "a" (bold) and "b" (plain) in `group`; with `extra`, "c" in the outer group only."""
    blocks = [
        box("a", "text", {**TEXT, "text": "eins", "bold": True}, z=2, w=25, group=group),
        box("b", "text", {**TEXT, "text": "eins zwei drei"}, z=3, w=25, group=group),
    ]
    if extra:
        blocks.append(box("c", "text", {**TEXT, "text": "fern"}, z=4, w=25, group=group[:1], y=120))
    return blocks
