"""A picture dragged from another web page.

The drop helpers live in test_drop.py."""

import pytest
from playwright.sync_api import expect
from test_clipboard import blocks
from test_drop import (
    HTTP,
    KEPT,
    LINK_EFFECT,
    PNG,
    WEB_PICTURE,
    behind,
    data_png,
    docs,
    drop_items,
    landed,
    middle,
    new,
    picture,
    spot,
)
from ui import (
    TEXT,
    at,
    box,
    centre,
    drop,
    saved,
    user,
)


def test_a_picture_dragged_from_a_web_page_lands_under_the_pointer(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    url = page.url
    assert drop_items(page, *spot(page, 105, 150), *picture(data_png())) == KEPT
    landed(page, 2)
    assert page.url == url
    [held] = new(saved(page, client), "a")
    assert held["type"] == "image"
    assert isinstance(held["props"]["upload"], int)
    assert middle(held) == pytest.approx((105, 150), abs=0.5)
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(1)
    expect(at(page, "a")).to_be_visible()


def test_a_web_picture_dropped_on_the_second_page_lands_there(editor):
    client = user()
    page = editor(box("a", "text", TEXT), more=[box("far", "text", TEXT)], client=client)
    second = page.locator('.sheet[data-page="1"]')
    second.scroll_into_view_if_needed()
    expect(second).to_be_in_viewport()
    drop_items(page, *spot(page, 105, 148.5, n=1), *picture(data_png()))
    landed(page, 3)
    first, other = docs(page, client)
    assert [b["id"] for b in first] == ["a"]
    [held] = new(other, "far")
    assert middle(held) == pytest.approx((105, 148.5), abs=0.5)


def test_a_web_picture_address_is_not_fetched_and_the_hint_says_how(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    url = page.url
    asked = []
    page.on("request", lambda r: asked.append(r.url))
    assert drop_items(page, *spot(page, 105, 150), *picture(HTTP)) == KEPT
    expect(page.locator(".notice.fault")).to_contain_text(WEB_PICTURE)
    expect(blocks(page)).to_have_count(1)
    assert page.url == url
    assert [u for u in asked if "example.org" in u] == []
    assert [b["id"] for b in saved(page, client)] == ["a"]


def test_a_lazy_picture_is_taken_by_the_address_it_shows_not_its_placeholder(editor):
    # Review: the <img> holds a blank data: placeholder, the browser hands over the real address.
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    items = [("text/uri-list", HTTP), ("text/html", f'<img src="{data_png()}" data-src="{HTTP}">')]
    assert drop_items(page, *spot(page, 105, 150), *items) == KEPT
    expect(page.locator(".notice.fault")).to_contain_text(WEB_PICTURE)
    assert [b["id"] for b in saved(page, client)] == ["a"]


def test_a_picture_in_a_link_lands_by_its_own_address(editor):
    # Review: a thumbnail in a link hands over the link's address; its <img> holds the picture.
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    items = [
        ("text/uri-list", "https://example.org/seite"),
        ("text/html", f'<a href="https://example.org/seite"><img src="{data_png()}"></a>'),
    ]
    assert drop_items(page, *spot(page, 105, 150), *items) == KEPT
    landed(page, 2)
    [held] = new(saved(page, client), "a")
    assert held["type"] == "image"


def test_a_link_that_is_no_picture_adds_nothing(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    url = page.url
    link = "https://example.org/seite"
    items = [("text/uri-list", link), ("text/html", f'<a href="{link}">Seite</a>')]
    assert drop_items(page, *spot(page, 105, 150), *items) == KEPT
    expect(page.locator(".notice.fault")).to_have_count(0)
    drop(page, *spot(page, 105, 150), PNG)
    landed(page, 2)
    assert [b["type"] for b in new(saved(page, client), "a")] == ["image"]
    assert page.url == url


def test_a_web_picture_dropped_while_a_dialog_is_open_adds_nothing(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    point = behind(page)
    assert drop_items(page, *point, *picture(data_png())) == KEPT
    page.keyboard.press("Escape")
    expect(page.locator("dialog")).to_have_count(0)
    # A picture of the file drop would be there by the time the web one's is.
    drop(page, *spot(page, 105, 150), PNG)
    landed(page, 2)
    assert [b["type"] for b in new(saved(page, client), "a")] == ["image"]


def test_a_web_picture_is_copied_over_the_sheet_and_refused_over_the_top_bar(editor):
    page = editor(box("a", "text", TEXT))
    assert page.evaluate(LINK_EFFECT, [*spot(page, 105, 150), picture(HTTP)]) == "copy"
    bar = centre(page.locator("header button").first)
    assert page.evaluate(LINK_EFFECT, [*bar, picture(HTTP)]) == "none"
