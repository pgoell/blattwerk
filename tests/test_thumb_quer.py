"""#633: a Quer page's thumbnail in the panel Seiten lies whole inside the panel, on its side."""

from playwright.sync_api import expect
from ui import TEXT, box, thumb, user


def paper(page, n):
    """The picture of page n's thumbnail, its box."""
    return thumb(page, n).locator(".paper")


def open_panel(page, width, height):
    """Sizes the window and opens the panel Seiten with its button.

    A visible scrollbar takes 15 px of the panel. Headless Chromium hides it, so a 16 px border
    (the scrollbar and the rule) stands in for it.
    """
    page.set_viewport_size({"width": width, "height": height})
    page.add_style_tag(content="aside.left { border-right: 16px solid transparent }")
    if width < 1100:
        # The wide window keeps the panel open; only a drawer has the button.
        page.get_by_role("button", name="Seiten und Vorlagen").click()
    expect(page.locator("aside.left")).to_be_visible()


def inside(page, n):
    """Page n's picture as a box, and the panel as a box with its inner width."""
    shown = paper(page, n).bounding_box()
    panel = page.locator("aside.left").bounding_box()
    panel["width"] = page.evaluate("document.querySelector('aside.left').clientWidth")
    return shown, panel


def room(page):
    """Where the thumbnails must stop: the strip's right edge less its gutter."""
    return page.evaluate(
        "() => { const s = document.querySelector('.pages'); const b = s.getBoundingClientRect();"
        " return b.right - s.clientLeft - parseFloat(getComputedStyle(s).paddingRight); }"
    )


def test_a_quer_thumbnail_lies_whole_inside_the_panel_at_1000_by_800(editor):
    """#633, the issue's case: page 2 on its side ends inside the panel and the strip's gutter."""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)], "landscape": True}]
    page = editor(box("a", "text", TEXT), pages=rest, theme=None, client=client)
    open_panel(page, 1000, 800)
    expect(thumb(page, 1)).to_be_visible()
    shown, panel = inside(page, 1)
    assert shown["x"] + shown["width"] <= panel["x"] + panel["width"], (shown, panel)
    assert shown["x"] + shown["width"] <= room(page), (shown, room(page))
    assert shown["width"] > shown["height"], shown


def test_a_hoch_thumbnail_beside_a_quer_one_keeps_its_size(editor):
    """#633: page 1 upright keeps the size it has on a sheet without a Quer page."""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)], "landscape": True}]
    page = editor(box("a", "text", TEXT), pages=rest, theme=None, client=client)
    open_panel(page, 1000, 800)
    expect(thumb(page, 1)).to_be_visible()
    beside = paper(page, 0).bounding_box()
    alone = editor(
        box("a", "text", TEXT),
        pages=[{"blocks": [box("b", "text", TEXT)]}],
        theme=None,
        client=client,
    )
    open_panel(alone, 1000, 800)
    expect(thumb(alone, 1)).to_be_visible()
    plain = paper(alone, 0).bounding_box()
    assert (round(beside["width"]), round(beside["height"])) == (
        round(plain["width"]),
        round(plain["height"]),
    ), (
        beside,
        plain,
    )


def test_a_quer_thumbnail_lies_whole_inside_the_panel_at_1400_by_900(editor):
    """#633 beyond the brief: the wide layout too, page 2 on its side inside the panel."""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)], "landscape": True}]
    page = editor(box("a", "text", TEXT), pages=rest, theme="", client=client)
    open_panel(page, 1400, 900)
    expect(thumb(page, 1)).to_be_visible()
    shown, panel = inside(page, 1)
    assert shown["x"] + shown["width"] <= panel["x"] + panel["width"], (shown, panel)
    assert shown["width"] > shown["height"], shown


def test_two_quer_pages_after_the_first_lie_whole_inside_the_panel_at_1000_by_800(editor):
    """#633 beyond the brief: two Quer pages after the first, each inside the panel."""
    client = user()
    rest = [
        {"blocks": [box("b", "text", TEXT)], "landscape": True},
        {"blocks": [box("c", "text", TEXT)], "landscape": True},
    ]
    page = editor(box("a", "text", TEXT), pages=rest, theme=None, client=client)
    open_panel(page, 1000, 800)
    expect(thumb(page, 2)).to_be_visible()
    panel = page.locator("aside.left").bounding_box()
    for n in (1, 2):
        shown = paper(page, n).bounding_box()
        assert shown["x"] + shown["width"] <= panel["x"] + panel["width"], (n, shown, panel)
        assert shown["width"] > shown["height"], (n, shown)
