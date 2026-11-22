"""The tasks of a maths block stand under each other piece by piece (issue #1160): the ones of a
number under the ones of the number above, the signs under the signs, and every answer line from
one x to one x.

Before the fix each task was set as running text from its left edge, so `7 · 8 = __` and
`120 : 4 = __` had their signs and their lines at different places.
"""

from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_maths_written_print import PAGE_MM, printed_picture
from ui import at, box, maths, user

# Each task's pieces: where the last character of each number ends, where each sign's middle
# lies, and where the answer line starts and ends. In px, in task order.
PIECES = """(block) => [...block.querySelectorAll('.maths > div, .maths .family > div')].map((task) => {
    const out = {};
    for (const piece of task.querySelectorAll('.at')) {
        const box = piece.getBoundingClientRect();
        const line = piece.querySelector('u');
        const walker = document.createTreeWalker(piece, NodeFilter.SHOW_TEXT);
        let last = null;
        while (walker.nextNode()) if (walker.currentNode.data) last = walker.currentNode;
        const at = piece.dataset.at;
        if (line) {
            const u = line.getBoundingClientRect();
            out[at] = { line: [u.left, u.right] };
        } else if (last && (at === 'op' || at === 'op2')) {
            const range = document.createRange();
            range.selectNodeContents(last);
            const r = range.getBoundingClientRect();
            out[at] = { middle: (r.left + r.right) / 2 };
        } else if (last) {
            const range = document.createRange();
            range.setStart(last, last.data.length - 1);
            range.setEnd(last, last.data.length);
            out[at] = { ones: range.getBoundingClientRect().right, chars: piece.textContent.length };
        } else out[at] = { empty: box.width };
    }
    return out;
})"""


def pieces(page, n):
    """The pieces of the block's n tasks, once the fonts are in and the block has measured them."""
    page.evaluate("document.fonts.ready.then(() => 0)")
    expect(at(page, "m").locator(".maths .at[data-at=result]")).to_have_count(n)
    return at(page, "m").evaluate(PIECES)


def spread(tasks, name, key):
    """How far the values of one piece lie apart over the tasks that have it, in px."""
    values = [v for task in tasks if key in task.get(name, {}) for v in [task[name][key]]]
    assert values, f"no task has {name}.{key}"
    if isinstance(values[0], list):
        return max(max(v[i] for v in values) - min(v[i] for v in values) for i in (0, 1))
    return max(values) - min(values)


def test_a1_times_and_divide_tasks_stand_under_each_other(editor):
    """A1: with one, two and three digits mixed, ones, signs and answer lines line up."""
    client = user()
    props = maths(client, ops=["*", "/"], max=1000, count=18, columns=3)
    page = editor(box("m", "maths", props, y=20, h=60, w=180), client=client)
    tasks = pieces(page, 18)
    lengths = {task["a"]["chars"] for task in tasks}
    assert len(lengths) > 1, f"the first numbers all have {lengths} digits: the test shows nothing"
    signs = {e["op"] for e in props["exercises"]}
    assert signs == {"*", "/"}, f"the tasks have only {signs}"
    # The tasks of one column start at one x, so over the block each piece keeps its distance to it.
    starts = (
        at(page, "m")
        .locator(".maths > div")
        .evaluate_all("els => els.map((el) => el.getBoundingClientRect().left)")
    )
    for task, start in zip(tasks, starts, strict=True):
        for piece in task.values():
            for key, value in piece.items():
                if key != "chars":
                    piece[key] = (
                        [v - start for v in value] if isinstance(value, list) else value - start
                    )
    assert spread(tasks, "a", "ones") <= 0.5
    assert spread(tasks, "b", "ones") <= 0.5
    assert spread(tasks, "op", "middle") <= 0.5
    assert spread(tasks, "result", "line") <= 0.5
    fit = at(page, "m").locator(".maths").evaluate("el => el.style.getPropertyValue('--fit')")
    assert fit == "", f"the block shrinks to {fit} though nothing is too wide"


def test_a2_a_gap_in_any_place_keeps_the_numbers_under_each_other(editor):
    """A2: where the gap stands for the first or the second number, the lines and the ones still line up."""
    client = user()
    props = maths(
        client,
        ops=["+", "-"],
        max=100,
        count=12,
        columns=1,
        format="gap",
        gaps=["a", "b", "result"],
    )
    hidden = {e.get("hide", "result") for e in props["exercises"]}
    assert hidden == {"a", "b", "result"}, f"the gaps stand only for {hidden}"
    page = editor(box("m", "maths", props, y=20, h=120, w=120), client=client)
    tasks = pieces(page, 12)
    for name in ("a", "b", "result"):
        assert spread(tasks, name, "ones") <= 0.5, name
        assert spread(tasks, name, "line") <= 0.5, name
    assert spread(tasks, "op", "middle") <= 0.5


def test_a3_brackets_keep_their_place(editor):
    """A3: a chain with brackets round the first two numbers or the last two keeps numbers and signs in line."""
    client = user()
    props = maths(
        client,
        ops=["+", "-", "*"],
        max=100,
        count=12,
        columns=1,
        numbers=3,
        pvs=True,
        brackets=True,
    )
    parens = {e.get("paren") for e in props["exercises"]}
    assert {"left", "right"} <= parens, f"the tasks have only the brackets {parens}"
    page = editor(box("m", "maths", props, y=20, h=120, w=150), client=client)
    tasks = pieces(page, 12)
    for name in ("a", "b", "c"):
        assert spread(tasks, name, "ones") <= 0.5, name
    for name in ("op", "op2"):
        assert spread(tasks, name, "middle") <= 0.5, name
    assert spread(tasks, "result", "line") <= 0.5
    texts = [" ".join(t.split()) for t in at(page, "m").locator(".maths > div").all_text_contents()]
    assert any(t.startswith("(") for t in texts) and any(t.endswith(") =") for t in texts), texts


def test_a4_the_rings_of_comparisons_stand_under_each_other(editor):
    """A4: the left sides of comparisons end at one x, so the rings stand in one column."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=10, columns=1, format="compare", sides="tn")
    page = editor(box("m", "maths", props, y=20, h=120, w=120), client=client)
    page.evaluate("document.fonts.ready.then(() => 0)")
    rings = at(page, "m").locator(".maths .ring")
    expect(rings).to_have_count(10)
    lefts = rings.evaluate_all("els => els.map((el) => el.getBoundingClientRect().left)")
    widths = (
        at(page, "m")
        .locator(".maths .at[data-at=left]")
        .evaluate_all("els => els.map((el) => el.textContent.length)")
    )
    assert len(set(widths)) > 1, "every left side is as long as the next: the test shows nothing"
    assert max(lefts) - min(lefts) <= 0.5, f"the rings start at {lefts}"


def test_a5_the_answer_lines_start_under_each_other_in_the_pdf(editor, server):
    """A5: in the PDF every task's answer line starts where the screen has it, at one x."""
    client = user()
    props = maths(client, ops=["*", "/"], max=1000, count=8, columns=1)
    page = editor(box("m", "maths", props, y=20, h=80, w=120), client=client)
    tasks = pieces(page, 8)
    assert len({task["a"]["chars"] for task in tasks}) > 1, "the first numbers are all as long"
    assert spread(tasks, "result", "line") <= 0.5
    picture = printed_picture(server, client, sheet_id(page), False)
    places = page.evaluate(
        """() => {
            const sheet = document.querySelector('.sheet[data-page="0"]').getBoundingClientRect();
            const rows = [...document.querySelectorAll('.block[data-id="m"] .maths > div')];
            return rows.map((row) => {
                const r = row.getBoundingClientRect();
                const u = row.querySelector('u').getBoundingClientRect();
                return [(u.left - sheet.x) / sheet.width, (r.top - sheet.y) / sheet.width, (r.bottom - sheet.y) / sheet.width];
            });
        }"""
    )
    half = round(0.5 * picture.width / PAGE_MM)
    for i, (left, top, bottom) in enumerate(places):
        x, y0, y1 = (round(v * picture.width) for v in (left, top, bottom))
        inside = min(picture.crop((x + half, y0, x + half + 1, y1)).tobytes())
        before = min(picture.crop((x - half, y0, x - half + 1, y1)).tobytes())
        assert inside < 128, (
            f"task {i}: no answer line 0.5 mm right of its start (darkest {inside})"
        )
        assert before > 200, (
            f"task {i}: ink 0.5 mm left of the answer line's start (darkest {before})"
        )
