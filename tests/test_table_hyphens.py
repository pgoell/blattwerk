"""A word too long for a closed table cell breaks at a syllable, with a hyphen (#524)."""

from playwright.sync_api import expect
from ui import box

# What a reader sees of a cell: its lines, each as the letters it holds, soft hyphens left out.
# A hyphen drawn at a line break is not in the DOM, so the lines are what the eye reads.
LINES = """(cell) => {
  const p = cell.querySelector('p');
  const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
  const lines = [];
  for (let node = walk.nextNode(); node; node = walk.nextNode()) {
    for (let i = 0; i < node.data.length; i++) {
      const range = document.createRange();
      range.setStart(node, i);
      range.setEnd(node, i + 1);
      const rect = range.getClientRects()[0];
      if (!rect || rect.width === 0) continue;
      const top = Math.round(rect.top);
      const last = lines[lines.length - 1];
      if (last && last.top === top) last.text += node.data[i];
      else lines.push({ top, text: node.data[i] });
    }
  }
  return lines.map((line) => line.text.replace(/\\u00AD/g, ''));
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
    assert len(lines) == 2, lines
    assert lines[0] in SACH and lines[0] + lines[1] == "Sachunterricht", lines
