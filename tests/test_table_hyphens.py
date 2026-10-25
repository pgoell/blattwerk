"""A word too long for a closed table cell breaks at a syllable, with a hyphen (#524)."""

import io
import re

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import BROWSER, at, box, pick, saved, user

# What a reader sees of a cell: its lines, each as the letters it holds. The text is read piece by
# piece, a piece being the letters between two soft hyphens: a piece lies on one line, and a line
# break at a soft hyphen draws a hyphen that the DOM does not hold. A piece on two lines is marked.
LINES = """(cell) => {
  const p = cell.querySelector('p');
  const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
  const lines = [];
  for (let node = walk.nextNode(); node; node = walk.nextNode()) {
    let offset = 0;
    for (const part of node.data.split('\\u00AD')) {
      const start = offset;
      offset += part.length + 1;
      if (!part) continue;
      const range = document.createRange();
      // The first letter after a soft hyphen reports the line before it, so read from the second.
      range.setStart(node, start > 0 && part.length > 1 ? start + 1 : start);
      range.setEnd(node, start + part.length);
      const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0);
      const top = Math.round(rects[0].top);
      if (rects.some((r) => Math.abs(r.top - top) > 2)) {
        lines.push({ top: null, text: part + '!' });
        continue;
      }
      const last = lines[lines.length - 1];
      if (last && last.top !== null && Math.abs(last.top - top) < 3) last.text += part;
      else lines.push({ top, text: part });
    }
  }
  return lines.map((line) => line.text);
}"""

# Syllable borders of "Sachunterricht" as the splitter has them: Sach-un-ter-richt.
SACH = ["Sach", "Sachun", "Sachunter"]
WEEK = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"]


def table(cells, **more):
    base = {"cells": cells, "cols": [1] * 6, "size": 14, "align": "center", "line": "#222222"}
    return {**base, **more}


def cell(page, i):
    return page.locator(f'.block[data-id="a"] [data-cell="{i}"]')


def test_a_long_word_breaks_at_a_syllable_with_a_hyphen_on_screen(editor):
    props = table([WEEK, ["Sachunterricht", "", "", "", "", ""]])
    page = editor(box("a", "table", props))
    expect(cell(page, 6)).to_contain_text("­")
    expect(page.locator(".unsplit")).to_have_count(0)
    lines = page.evaluate(LINES, cell(page, 6).element_handle())
    assert len(lines) == 2 and lines[0] in SACH and lines[0] + lines[1] == "Sachunterricht", lines


def test_the_teachers_breaks_mend_the_word_where_they_say(editor):
    props = table([WEEK, ["Sachunterricht", "", "", "", "", ""]], breaks={"sachunterricht": [6]})
    page = editor(box("a", "table", props))
    # to_contain_text drops a soft hyphen, so it returns while the splitter is still on its way
    # and the word breaks mid-letter. CI then read ['Sachunterricht!'] (#767).
    # The text node is the signal.
    page.wait_for_function(
        "() => document.querySelector('[data-cell=\"6\"] p').textContent.includes('\\u00ad')"
    )
    lines = page.evaluate(LINES, cell(page, 6).element_handle())
    assert lines == ["Sachun", "terricht"], lines


def test_a_table_whose_words_all_fit_has_no_soft_hyphen_and_asks_no_splitter(editor):
    props = table([WEEK, ["Hallo", "", "", "", "", ""]])
    page = editor(box("a", "table", props))
    expect(cell(page, 6)).to_have_text("Hallo")
    assert "­" not in page.evaluate("() => document.querySelector('.table').textContent")
    asked = page.evaluate("performance.getEntriesByType('resource').map((entry) => entry.name)")
    assert not [url for url in asked if "syllables" in url]


def test_a_word_without_a_break_breaks_as_before_and_gets_no_hyphen(editor):
    props = table([WEEK, ["Deutsch", "", "", "", "", ""]], cols=[0.35, 1, 1, 1, 1, 1])
    page = editor(box("a", "table", props))
    expect(cell(page, 6)).to_have_text("Deutsch")
    assert "­" not in page.evaluate(
        "() => document.querySelector('[data-cell=\"6\"] p').textContent"
    )


def test_typing_in_a_hyphenated_table_saves_no_soft_hyphen(editor):
    client = user()
    props = table([WEEK, ["Sachunterricht", "", "", "", "", ""]])
    page = editor(box("a", "table", props), client=client)
    expect(cell(page, 6)).to_contain_text("­")
    pick(page, "a")
    cell(page, 1).dblclick()
    expect(at(page, "a").locator("textarea")).to_be_focused()
    page.keyboard.type("Montag neu")
    cell(page, 6).click()
    blocks = saved(page, client)
    saved_cells = next(b for b in blocks if b["id"] == "a")["props"]["cells"]
    assert saved_cells[0][1] == "Montag neu" and saved_cells[1][0] == "Sachunterricht"
    assert not [text for row in saved_cells for text in row if "­" in text]


def test_the_pdf_breaks_a_long_word_at_a_syllable_with_a_hyphen(editor, server):
    client = user()
    props = table([WEEK, ["Sachunterricht", "", "", "", "", ""]])
    page = editor(box("a", "table", props), client=client)
    expect(cell(page, 6)).to_contain_text("­")
    sheet_id = page.url.rsplit("/", 1)[1]
    res = httpx.get(
        f"{server}/api/sheets/{sheet_id}/pdf",
        headers={"Cookie": f"session={client.cookies['session']}"},
        timeout=60,
    )
    assert res.status_code == 200
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages)
    # The extracted text spaces the letters out, and a hyphen at a line's end comes out as a dash.
    found = re.search(r"(Sach(?:un)?(?:unter)?)\W([a-zäöüß]+)", re.sub(r"\s", "", text))
    assert found and found.group(1) + found.group(2) == "Sachunterricht", text


def test_a_merged_cell_and_a_narrow_cell_each_break_at_a_syllable(editor):
    props = table(
        [WEEK, ["Sachunterricht", "", "Sachunterricht", "", "", ""]],
        cols=[0.4, 0.4, 0.4, 1, 1, 1],
        spans=[[1, 0, 1, 2]],
    )
    page = editor(box("a", "table", props))
    # to_contain_text drops a soft hyphen, so it passes while the splitter is still on its way
    # and the word breaks mid-letter. CI then read ['Sachunterricht!'] (#753). The text node is the signal.
    for n in (6, 8):
        page.wait_for_function(
            """(n) => document.querySelector(`[data-cell="${n}"] p`).textContent.includes('\\u00ad')""",
            arg=n,
        )
    # Each line but the last ends at a syllable border: the narrow cell may take more lines.
    for n in (6, 8):
        lines = page.evaluate(LINES, cell(page, n).element_handle())
        ends = ["".join(lines[: i + 1]) for i in range(len(lines) - 1)]
        assert "".join(lines) == "Sachunterricht" and all(e in SACH for e in ends), lines


def test_a_column_made_narrower_after_the_first_draw_breaks_the_word(editor):
    props = table([WEEK, ["Sachunterricht", "", "", "", "", ""]], cols=[3, 1, 1, 1, 1, 1])
    page = editor(box("a", "table", props))
    expect(page.locator(".unsplit")).to_have_count(0)
    assert "­" not in page.evaluate(
        "() => document.querySelector('[data-cell=\"6\"] p').textContent"
    )
    # The first column is made as narrow as the others: the layout of the drawn table changes.
    page.evaluate(
        "() => { document.querySelector('.block[data-id=\"a\"] .table').style.gridTemplateColumns"
        " = 'repeat(6, minmax(0, 1fr))'; }"
    )
    page.wait_for_function(
        "() => document.querySelector('[data-cell=\"6\"] p').textContent.includes('\\u00ad')"
    )
    lines = page.evaluate(LINES, cell(page, 6).element_handle())
    assert len(lines) == 2 and lines[0] in SACH and lines[0] + lines[1] == "Sachunterricht", lines


def test_a_second_word_that_breaks_later_in_the_same_cell_breaks_at_a_syllable(editor):
    page = editor(box("a", "table", table([WEEK, ["Sachunterricht Erdkunde", "", "", "", "", ""]])))
    expect(cell(page, 6)).to_contain_text("­")
    expect(page.locator(".unsplit")).to_have_count(0)
    # A bigger type breaks Erdkunde too, in a cell that is hyphenated already.
    page.evaluate(
        "() => { document.querySelector('[data-cell=\"6\"] p').style.fontSize = '2.2em'; }"
    )
    page.wait_for_function(
        "() => /Erd\\u00ad?kun\\u00adde|Erd\\u00adkun\\u00ad?de/"
        ".test(document.querySelector('[data-cell=\"6\"] p').textContent)"
    )
    expect(page.locator(".unsplit")).to_have_count(0)
    lines = page.evaluate(LINES, cell(page, 6).element_handle())
    # Erdkunde breaks at a syllable: a line starts with the rest of it.
    assert [line for line in lines if line in ("kunde", "kun", "de")], lines


def test_a_splitter_that_does_not_load_lets_the_print_go_on(editor):
    page = editor(box("a", "table", table([WEEK, ["Hallo", "", "", "", "", ""]])))
    page.route(re.compile(r"syllables.*\.js"), lambda route: route.abort())
    pick(page, "a")
    cell(page, 6).dblclick()
    expect(at(page, "a").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.type("Sachunterricht")
    with page.expect_event("requestfailed", lambda request: "syllables" in request.url):
        cell(page, 1).click()
    expect(cell(page, 6)).to_have_text("Sachunterricht")
    # The PDF waits for no `.unsplit`: with the splitter gone the word breaks as before.
    expect(page.locator(".unsplit")).to_have_count(0)
