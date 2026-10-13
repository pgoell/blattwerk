"""The numbers of a maths block are as wide as the widest, flush right: the tasks of a column stand
under each other, on the screen and in the PDF (issue #474).

Before the fix the number "10" pushed its task a square to the right of the tasks with one digit.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_maths_written_print import PAGE_MM, RECTS, printed_picture
from ui import at, box, maths, tool, user


def numbered(client, numbering="1", **more):
    """Twelve written tasks in two columns, numbered."""
    return maths(
        client,
        ops=["-", "/"],
        max=100,
        format="written",
        count=12,
        columns=2,
        numbering=numbering,
        **more,
    )


def edges(page, n):
    """Each task's paper left edge and number's right edge on the screen, in task order."""
    page.evaluate("document.fonts.ready.then(() => 0)")
    svgs = at(page, "m").locator("svg")
    marks = at(page, "m").locator(".maths > div > b")
    expect(svgs).to_have_count(n)
    expect(marks).to_have_count(n)
    lefts = [svgs.nth(i).bounding_box()["x"] for i in range(n)]
    rights = []
    for i in range(n):
        r = marks.nth(i).bounding_box()
        rights.append(r["x"] + r["width"])
    return lefts, rights


def assert_columns_line_up(lefts, rights, cols):
    """In each column the papers start at one x and the numbers end at one x, within 1 px."""
    for c in range(cols):
        ls = lefts[c::cols]
        rs = rights[c::cols]
        assert max(ls) - min(ls) <= 1, f"column {c}: paper left edges {ls}"
        assert max(rs) - min(rs) <= 1, f"column {c}: number right edges {rs}"


def test_a6_the_papers_of_a_column_stand_under_each_other(editor):
    """A6: the papers of one column start at one x, and their numbers end at one x."""
    client = user()
    props = numbered(client)
    rows = max(e["grid"]["rows"] for e in props["exercises"])
    page = editor(box("m", "maths", props, y=20, h=6 * (rows + 1) * 5), client=client)
    lefts, rights = edges(page, 12)
    assert_columns_line_up(lefts, rights, cols=2)


def test_a6_the_papers_stand_under_each_other_in_the_pdf(editor, server):
    """A6: in the PDF the paper of task 10 stands on the line of the paper of task 0."""
    client = user()
    props = numbered(client)
    rows = max(e["grid"]["rows"] for e in props["exercises"])
    page = editor(box("m", "maths", props, y=20, h=6 * (rows + 1) * 5), client=client)
    picture = printed_picture(server, client, sheet_id(page), False)
    found = page.evaluate(RECTS)
    sx, sy, sw, _ = found["sheet"]
    scale = picture.width / sw
    first = found["svgs"][0]
    last = found["svgs"][10]
    x0 = round((first[0] - sx) * scale)
    y_mid = round((last[1] - sy + last[3] / 2) * scale)
    # 0.3 mm either side of the first paper's left line, at the middle of the last paper.
    room = round(0.3 * picture.width / PAGE_MM)
    strip = picture.crop((x0 - room, y_mid, x0 + room, y_mid + 1))
    pale = min(strip.tobytes())
    assert pale < 240, f"no paper line at task 0's edge beside task 10 (darkest {pale})"


@pytest.mark.parametrize("numbering", ["a)", "1o"])
def test_i5_letters_and_ringed_numbers_line_up_too(editor, numbering):
    """I5: letters and ringed numbers end at one x in a column, and so does the answer key."""
    client = user()
    props = numbered(client, numbering=numbering)
    rows = max(e["grid"]["rows"] for e in props["exercises"])
    page = editor(box("m", "maths", props, y=20, h=6 * (rows + 1) * 5), client=client)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator("svg text.answer").first).to_be_visible()
    lefts, rights = edges(page, 12)
    assert_columns_line_up(lefts, rights, cols=2)


def test_i6_numbers_below_ten_leave_the_papers_where_they_were(editor):
    """I6: with one digit the paper stands as far from its number as before, and nothing shrinks."""
    client = user()
    props = maths(client, format="written", max=100, ops=["+", "-"], count=6, numbering="1")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    svgs = at(page, "m").locator("svg")
    marks = at(page, "m").locator(".maths > div > b")
    expect(svgs).to_have_count(6)
    gaps = []
    for i in range(6):
        s = svgs.nth(i).bounding_box()
        b = marks.nth(i).bounding_box()
        gaps.append(s["x"] - b["x"])
    assert max(gaps) - min(gaps) <= 0.5, f"paper minus number left edges {gaps}"
    fit = at(page, "m").locator(".maths").evaluate("el => el.style.getPropertyValue('--fit')")
    assert fit == "", f"the block shrinks to {fit} though nothing is too wide"


def test_a6_numbered_rows_start_under_each_other_too(editor):
    """A6: in a row format the texts of one column start at one x."""
    client = user()
    props = maths(client, ops=["+"], max=20, count=12, columns=1, numbering="1")
    page = editor(box("m", "maths", props, y=20, h=200), client=client)
    page.evaluate("document.fonts.ready.then(() => 0)")
    texts = at(page, "m").locator(".maths > div > span")
    expect(texts).to_have_count(12)
    lefts = [texts.nth(i).bounding_box()["x"] for i in range(12)]
    assert max(lefts) - min(lefts) <= 1, f"task texts start at {lefts}"
