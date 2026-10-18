"""The written method on the screen: each task's ones stand in the paper's last column (issue #811).

Each task's grid is only as wide as its own sum, but all tasks of a block share one paper. Each
character must stand at its grid column shifted right by the paper's columns less the task's own,
and a division is not shifted. The checks read the svg's text positions with the answers shown.
"""

from playwright.sync_api import expect
from ui import at, box, maths, tool, user

# A square in the svg's user units.
S = 10


def block(props):
    """The maths block at 20 mm from the top, tall enough for the tasks."""
    return box("m", "maths", props, y=20, h=120)


def texts(page):
    """Each Karo svg's characters as [x, y, text], in the order the grid lists them."""
    return page.evaluate(
        """() => [...document.querySelectorAll('.block[data-id="m"] svg')]
            .filter((s) => s.querySelector('text'))
            .map((s) => [...s.querySelectorAll('text')].map((t) => [
                parseFloat(t.getAttribute('x')), parseFloat(t.getAttribute('y')), t.textContent]))"""
    )


def check(page, props):
    """Every character stands at its grid column, moved right to the paper's last column unless the task is a division.

    Returns how many tasks have a result shorter than the paper.
    """
    tasks = [e for e in props["exercises"] if "grid" in e]
    cols = max(e["grid"]["cols"] for e in tasks)
    shorter = 0
    drawn = texts(page)
    assert len(drawn) == len(tasks)
    for e, found in zip(tasks, drawn, strict=True):
        grid = e["grid"]
        dx = 0 if e["op"] == "/" else cols - grid["cols"]
        shorter += dx > 0
        # The sign of a plus or a minus stays in the first column, as in every other task of the block.
        sign = e["op"] in "+-"
        expected = [
            [((0 if sign and x == 0 else x + dx) + 0.5) * S, (y + 0.5) * S, ch]
            for x, y, ch, _ in grid["cells"]
        ]
        assert found == expected, (e, found)
    return shorter


def test_a1_a_one_digit_result_stands_in_the_ones_column(editor):
    """A1: a one-digit result stands in the paper's last column, as a two-digit result does."""
    client = user()
    props = maths(client, format="written", max=20, ops=["+"], count=12)
    page = editor(block(props), client=client)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator("svg text.answer").first).to_be_visible()
    assert check(page, props) > 0, "no one-digit result in the block"


def test_a3_two_and_three_digit_results_and_carries_line_up(editor):
    """A3: two- and three-digit results and their carries stand in their own columns."""
    client = user()
    props = maths(client, format="written", max=1000, ops=["+", "-"], count=12)
    page = editor(block(props), client=client)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator("svg text.answer").first).to_be_visible()
    check(page, props)
    assert any(c[3] == 2 for e in props["exercises"] for c in e["grid"]["cells"]), (
        "no carry in the block"
    )


def test_i7_mixed_plus_and_times_keep_the_ones_column_and_division_stays(editor):
    """I7: a block of + and * keeps each task's ones in the last column; a division stays where it was."""
    client = user()
    props = maths(client, format="written", max=1000, ops=["+", "*", "/"], count=9)
    page = editor(block(props), client=client)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator("svg text.answer").first).to_be_visible()
    check(page, props)
