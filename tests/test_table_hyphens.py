"""A word too long for a closed table cell breaks at a syllable, with a hyphen (#524)."""

from playwright.sync_api import expect
from ui import at, box, pick, saved, user

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
      const top = rects[0].top;
      if (rects.some((r) => Math.abs(r.top - top) > 2)) {
        lines.push({ top: null, text: part + '!' });
        continue;
      }
      const last = lines[lines.length - 1];
      if (last && last.top === top) last.text += part;
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
    expect(cell(page, 6)).to_contain_text("­")
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
