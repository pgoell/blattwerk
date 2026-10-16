"""Silbenbögen: a bow under each syllable of a text's words, drawn over the words as they stand."""

import io

import pytest
from PIL import Image, ImageChops
from playwright.sync_api import expect
from test_fields import colour
from test_zoom import expect_width, wheel, width
from ui import FIELD, TABLE, TEXT, at, box, pick, sheet, syls, user

from blattwerk import pdf

FONTS = {
    "andika": 0.415,
    "grund": 0.4545,
    "va": 0.46,
    "sas": 0.4515,
    "la": 0.4545,
    "nord": 0.2888,
    "sued": 0.2888,
    "urff": 0.299,
}
SAID = {**TEXT, "text": "Die Maus isst 3 Äpfel.", "syllables": True}
RED = "#e03131"
# Each bow of a block with the syllable it is drawn for, in the window's pixels: the syllable's
# box, its baseline by the font's own measure `base`, the size of its letters, and the bow's box.
# The syllables are found again in the text, one after the other.
BOWS = """(block, base) => {
  const scale = block.getBoundingClientRect().width / block.offsetWidth;
  const paths = [...block.querySelectorAll('.syl')];
  const out = [];
  for (const p of block.querySelectorAll('p')) {
    if (p.querySelector('p')) continue;
    const nodes = [];
    const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) nodes.push(walk.currentNode);
    const text = nodes.map((node) => node.data).join('');
    const spot = (at) => {
      let i = 0;
      while (at > nodes[i].length) at -= nodes[i++].length;
      return [nodes[i], at];
    };
    for (let at = 0; out.length < paths.length; ) {
      const syl = paths[out.length].dataset.syl;
      const from = text.indexOf(syl, at);
      if (from < 0) break;
      at = from + syl.length;
      const range = document.createRange();
      range.setStart(...spot(from));
      range.setEnd(...spot(at));
      const r = range.getBoundingClientRect();
      const bow = paths[out.length].getBoundingClientRect();
      const em = parseFloat(getComputedStyle(p).fontSize) * scale;
      out.push({
        syl, em, left: r.left, right: r.right, base: (r.top + r.bottom) / 2 + base * em,
        bow: [bow.left, bow.top, bow.right, bow.bottom],
      });
    }
  }
  return out;
}"""
# Each letter's box against its block's corner.
LETTERS = """(block) => {
  const from = block.getBoundingClientRect();
  const out = [];
  const walk = document.createTreeWalker(block.querySelector('p'), NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  while (walk.nextNode())
    for (let i = 0; i < walk.currentNode.length; i++) {
      range.setStart(walk.currentNode, i);
      range.setEnd(walk.currentNode, i + 1);
      const r = range.getBoundingClientRect();
      out.push([r.left - from.left, r.top - from.top, r.width, r.height]);
    }
  return [...out.flat(), from.width, from.height];
}"""


def bows(page, name, font="andika"):
    """The block's bows and syllables, once the bows of its text are drawn."""
    syls(page, name)
    return at(page, name).evaluate(BOWS, FONTS[font])


def expect_under(found):
    """Each bow lies within its syllable's width, just below its baseline, and is seen."""
    assert found
    for one in found:
        left, top, right, bottom = one["bow"]
        em = one["em"]
        assert one["left"] - 0.5 <= left < right <= one["right"] + 0.5, one
        assert right - left > 0.5 * (one["right"] - one["left"]), one
        # Above the small letters of the next line, which is at least 1 em lower.
        assert one["base"] < top < bottom < one["base"] + 0.4 * em, one


def painted(page, where, room=0):
    """The box of the pixels that the bows alone paint, in a picture of `where` with `room` px
    more below it. None where they paint nothing."""
    area = where.bounding_box()
    clip = {**area, "height": area["height"] + room}
    shots = []
    for look in ("visible", "hidden"):
        page.add_style_tag(content=f".bows {{ visibility: {look} !important }}")
        shots.append(Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("L"))
    page.add_style_tag(content=".bows { visibility: visible !important }")
    return ImageChops.difference(*shots).point(lambda v: 255 if v > 64 else 0).getbbox()


def test_each_syllable_of_each_word_has_a_bow_and_a_number_has_none(editor):
    page = editor(box("a", "text", SAID), box("b", "text", {**SAID, "syllables": False}, z=2))
    assert syls(page, "a") == ["Die", "Maus", "isst", "Äp", "fel"]
    assert syls(page, "b") == []
    expect_under(bows(page, "a"))
    assert painted(page, at(page, "a"))
    assert not painted(page, at(page, "b"))


def test_a_word_split_by_hand_has_its_bows_where_the_teacher_set_them(editor):
    page = editor(box("a", "text", {**SAID, "breaks": {"maus": [2], "äpfel": []}}))
    assert syls(page, "a") == ["Die", "Ma", "us", "isst", "Äpfel"]


def test_a_shape_and_each_cell_of_a_table_have_their_bows(editor):
    shape = {**TEXT, "kind": "rect", "fill": "none", "text": "Banane", "syllables": True}
    cells = {**TABLE, "cells": [["Oma", "Igel"], ["3", "Radio"]], "line": "#222222"}
    page = editor(box("a", "shape", shape), box("b", "table", {**cells, "syllables": True}, z=2))
    assert syls(page, "a") == ["Ba", "na", "ne"]
    assert syls(page, "b") == ["O", "ma", "I", "gel", "Ra", "di", "o"]
    expect_under(bows(page, "a"))
    expect_under(bows(page, "b"))


def test_a_star_that_shrinks_its_text_has_its_bows_under_the_shrunk_syllables(editor):
    star = {**TEXT, "kind": "star", "inside": True, "fill": "none", "stroke": "#222222"}
    star |= {"text": "Sonnenblumenfeld am Morgen", "syllables": True, "align": "center"}
    page = editor(box("a", "shape", star, w=30, h=30))
    expect_under(bows(page, "a"))


def test_the_bows_follow_the_words_as_they_are_typed(editor):
    page = editor(box("a", "text", SAID))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("Banane")
    expect(page.locator(FIELD)).to_have_text("Banane")
    expect(at(page, "a").locator(".syl")).to_have_count(3)
    assert syls(page, "a") == ["Ba", "na", "ne"]
    expect_under(bows(page, "a"))
    page.keyboard.type(" Oma")
    expect(at(page, "a").locator(".syl")).to_have_count(5)
    assert syls(page, "a") == ["Ba", "na", "ne", "O", "ma"]
    page.keyboard.press("ControlOrMeta+a")
    page.keyboard.press("Backspace")
    expect(at(page, "a").locator(".syl")).to_have_count(0)


def test_each_bow_lies_under_its_syllable_at_every_zoom_size_spacing_and_font(editor):
    words = "Oma malt eine Banane und Opa liest im Garten"
    blocks = []
    for i, font in enumerate(FONTS):
        small = {**TEXT, "text": words, "font": font, "size": 12, "spacing": 1, "syllables": True}
        large = {**small, "size": 26, "spacing": 1.6}
        blocks.append(box(f"{font}-small", "text", small, x=10, y=6 + 36 * i, w=50, h=34))
        blocks.append(box(f"{font}-large", "text", large, x=65, y=6 + 36 * i, w=135, h=34))
    page = editor(*blocks)
    wide = width(page)
    # As the page opens, three steps smaller and three steps larger: about 50 and 200 % of it.
    for steps in (0, 3, -6):
        for _ in range(abs(steps)):
            wheel(page, 100 if steps > 0 else -100)
            wide = wide / 1.25 if steps > 0 else wide * 1.25
            expect_width(page, wide)
        for font in FONTS:
            for size in ("small", "large"):
                found = bows(page, f"{font}-{size}", font)
                assert len(found) == 15, (font, size)
                # The words stand in more than one line.
                assert len({round(one["base"]) for one in found}) > 1
                expect_under(found)


def test_a_turned_block_has_its_bows_where_the_level_one_has_them(editor):
    words = {**SAID, "font": "va"}
    page = editor(box("a", "text", words), box("b", "text", words, z=2, angle=30))
    assert syls(page, "b") == syls(page, "a")
    level, turned = (
        at(page, name).locator(".syl").evaluate_all("els => els.map((el) => el.getAttribute('d'))")
        for name in "ab"
    )
    assert turned == level


@pytest.mark.parametrize("font", FONTS)
def test_the_bows_move_no_letter_and_none_is_cut_off_under_the_last_line(editor, font):
    # Lines 1.0 apart, at the block's foot, in a block just as high as its one line of 14 pt.
    words = {**TEXT, "text": "Oma las", "font": font, "spacing": 1, "valign": "bottom"}
    tight = {"h": 4.94, "w": 60}
    page = editor(
        box("off", "text", words, **tight),
        box("on", "text", {**words, "syllables": True}, z=2, **tight),
    )
    assert syls(page, "on") == ["O", "ma", "las"]
    off, on = (at(page, name).evaluate(LETTERS) for name in ("off", "on"))
    assert on == pytest.approx(off, abs=0.01)
    found = bows(page, "on", font)
    expect_under(found)
    # The bows hang below the block's own box, and all of each is painted there: to 3 px, for
    # the stroke's round ends and soft edge, which WebKit leaves out of a path's box.
    area = at(page, "on").bounding_box()
    em = found[0]["em"]
    seen = painted(page, at(page, "on"), room=em)
    # Fibel's baseline lies higher in its line, so its bows end a hair inside the box.
    assert seen and (font in ("nord", "sued") or seen[3] > area["height"])
    lowest = max(one["bow"][3] for one in found) - area["y"]
    assert seen[3] == pytest.approx(lowest, abs=3)
    assert seen[0] == pytest.approx(found[0]["bow"][0] - area["x"], abs=3)
    assert seen[2] == pytest.approx(found[-1]["bow"][2] - area["x"], abs=3)


def test_a_sheet_without_bows_asks_for_no_splitter_and_saves_back_as_it_was(editor):
    client = user()
    old = [box("a", "text", TEXT), box("b", "table", {**TABLE, "line": "#222222"}, z=2)]
    page = editor(*old, client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    before = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    with page.expect_response(lambda res: res.request.method == "PATCH"):
        page.get_by_label("Titel", exact=True).fill("Anders")
    assert client.get(f"/api/sheets/{sheet_id}").json()["doc"] == before
    expect(page.locator(".syl, .bows")).to_have_count(0)
    asked = page.evaluate("performance.getEntriesByType('resource').map((entry) => entry.name)")
    assert asked and not [url for url in asked if "syllables" in url]


def test_a_sheet_with_bows_asks_for_the_splitter(editor):
    page = editor(box("a", "text", SAID))
    syls(page, "a")
    asked = page.evaluate("performance.getEntriesByType('resource').map((entry) => entry.name)")
    assert [url for url in asked if "syllables" in url]


def test_bold_italic_underline_colour_and_a_list_keep_their_look_under_bows(editor):
    runs = [
        {"text": "Rote ", "color": RED},
        {"text": "Ba", "bold": True},
        {"text": "nane ", "italic": True},
        {"text": "Esel", "underline": True},
    ]
    listed = [{"runs": runs, "list": "bullet"}, {"runs": [{"text": "Oma"}]}]
    text = "Rote Banane Esel\nOma"
    page = editor(box("a", "text", {**TEXT, "text": text, "rich": listed, "syllables": True}))
    # "Banane" is split whole, though a run ends inside it.
    assert syls(page, "a") == ["Ro", "te", "Ba", "na", "ne", "E", "sel", "O", "ma"]
    expect_under(bows(page, "a"))
    spans = at(page, "a").locator(".rich p span")
    expect(spans.nth(0)).to_have_css("color", "rgb(224, 49, 49)")
    expect(spans.nth(1)).to_have_css("font-weight", "700")
    expect(spans.nth(2)).to_have_css("font-style", "italic")
    expect(spans.nth(3)).to_have_css("text-decoration-line", "underline")
    item = at(page, "a").locator(".rich p").first
    assert item.evaluate("el => getComputedStyle(el, '::before').content") == '"•"'
    # A bow has the colour of its word.
    paths = at(page, "a").locator(".syl")
    strokes = paths.evaluate_all("els => els.map((el) => getComputedStyle(el).stroke)")
    assert strokes[:2] == ["rgb(224, 49, 49)"] * 2
    assert set(strokes[2:]) == {"rgb(34, 34, 34)"}


def test_the_sheet_lists_thumbnail_shows_the_bows(editor, server):
    page = editor(box("a", "text", {**SAID, "size": 40}, w=180, h=40))
    syls(page, "a")
    page.goto(server)
    paper = page.locator(".sheets li .paper")
    expect(paper.locator(".syl")).to_have_count(5)
    expect(paper.locator(".unsplit")).to_have_count(0)
    assert painted(page, paper)


CHUNK = "**/assets/syllables-*.js"
# Counts each time a block's bows are drawn anew, and keeps the bows it has now.
WATCH = """() => {
  window.draws = {};
  window.first = {};
  for (const svg of document.querySelectorAll('.sheet .block[data-id] .bows')) {
    const name = svg.closest('.block').dataset.id;
    window.draws[name] = 0;
    window.first[name] = [...svg.children];
    new MutationObserver(() => window.draws[name]++).observe(svg, { childList: true });
  }
}"""
# What WATCH counted, two frames on: a measure that was put off to the next frame is in.
DRAWS = """() => new Promise((done) =>
  requestAnimationFrame(() => requestAnimationFrame(() => done({ ...window.draws }))))"""
SAME = """(svg) => {
  const first = window.first[svg.closest('.block').dataset.id];
  return svg.children.length > 0 && [...svg.children].every((el, i) => el === first[i]);
}"""


def test_bows_are_measured_anew_only_for_the_block_that_changed(editor):
    page = editor(
        box("a", "text", SAID),
        box("b", "text", SAID, z=2),
        box("c", "text", TEXT, z=3),
    )
    assert syls(page, "a") == syls(page, "b")
    page.evaluate(WATCH)
    # A pick of another block, and of the block itself.
    pick(page, "c")
    pick(page, "a")
    assert page.evaluate(DRAWS) == {"a": 0, "b": 0}
    # The field opens and a letter is typed: one measure each for this block, none for the other.
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    opened = page.evaluate(DRAWS)
    page.keyboard.press("End")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_contain_text("Äpfel.x")
    typed = page.evaluate(DRAWS)
    assert typed["b"] == 0 and at(page, "b").locator(".bows").evaluate(SAME)
    assert opened["a"] <= 2 and typed["a"] - opened["a"] == 1, (opened, typed)
    # Another colour for the block: its bows take it.
    page.keyboard.press("Escape")
    colour(page, "#ff0000")
    expect(at(page, "a").locator(".syl").first).to_have_attribute("stroke", "rgb(255, 0, 0)")
    assert syls(page, "a") == ["Die", "Maus", "isst", "Äp", "fel", "x"]
    assert page.evaluate(DRAWS)["b"] == 0


def opened(browser, server, client, mine, path="blatt", **more):
    """A page of a window of its own, where the splitter's chunk fails to load, on the sheet
    `mine`; and the errors the page throws."""
    context = browser.new_context(viewport={"width": 1400, "height": 1000}, **more)
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route(CHUNK, lambda route: route.abort())
    with page.expect_event("requestfailed", lambda request: "syllables-" in request.url):
        page.goto(f"{server}/{path}/{mine}")
    return page, errors


def test_a_splitter_that_fails_to_load_leaves_the_text_without_bows_and_a_change_asks_again(
    browser, server
):
    client = user()
    mine = sheet(client, [box("a", "text", SAID)])["id"]
    page, errors = opened(browser, server, client, mine)
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
    expect(at(page, "a").locator(".bows")).to_have_count(1)
    expect(page.locator(".unsplit")).to_have_count(0)
    assert syls(page, "a") == []
    expect(at(page, "a")).to_have_text(SAID["text"])
    # A change of the block asks for the splitter again and still ends without bows.
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("Oma")
    expect(at(page, "a")).to_contain_text("Oma")
    assert syls(page, "a") == []
    # The server is back. A browser asks for a module that failed no second time while the page
    # lives, and the WebKit of the tests not after a reload either: the sheet opened anew has
    # its bows.
    page.unroute(CHUNK)
    anew = page.context.new_page()
    anew.goto(page.url)
    expect(at(anew, "a").locator(".syl").first).to_be_attached()
    assert syls(anew, "a")
    assert errors == []
    page.context.close()


def test_the_page_that_prints_is_ready_without_bows_when_the_splitter_fails_to_load(
    browser, server
):
    client = user()
    mine = sheet(client, [box("a", "text", SAID)])["id"]
    token = {"X-Render-Token": pdf.new_token(mine)}
    page, errors = opened(browser, server, client, mine, "druck", extra_http_headers=token)
    page.wait_for_selector("body.ready", state="attached")
    expect(page.locator(".block")).to_have_text(SAID["text"])
    expect(page.locator(".syl")).to_have_count(0)
    assert errors == []
    page.context.close()
