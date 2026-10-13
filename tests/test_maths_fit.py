"""A maths block shrinks its type until every task fits its block and the page (issue #450).

The fit is measured on the screen and never stored: the checks read the block as drawn and the
PDF as printed. Each test names the line of the checklist it proves.
"""

import httpx
import pypdfium2
import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from ui import TEXT, at, box, maths, pick, tool, user

# The tasks of a block as the page draws them: each inside the block and the sheet, and the block
# not scrolled. A turned block is not measured by its rectangles.
INSIDE = """block => {
  const root = block.querySelector('.maths');
  const out = [];
  if (root.scrollWidth > root.clientWidth + 1) {
    out.push(`scrolls ${root.scrollWidth} > ${root.clientWidth}`);
  }
  if (getComputedStyle(block).transform !== 'none') return out;
  const sheet = block.closest('.sheet').getBoundingClientRect();
  const b = block.getBoundingClientRect();
  const inside = (r, o) => r.left >= o.left - 1 && r.right <= o.right + 1
    && r.top >= o.top - 1 && r.bottom <= o.bottom + 1;
  root.querySelectorAll(':scope > div > *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (!inside(r, b) || !inside(r, sheet)) {
      out.push(`${el.tagName} ${Math.round(r.left)}..${Math.round(r.right)}`);
    }
  });
  return out;
}"""

FONT = "el => parseFloat(getComputedStyle(el).fontSize)"

# The PDF's strip from 196 mm to the paper's edge: a block at 15 mm and 180 mm wide ends at 195 mm.
STRIP = 196

ROOMS = [10, 20, 100, 1000, 1000000]
FORMATS = ["row", "gap", "written", "compare"]


def inside(page, name):
    """The screen: every task of the block is inside the block and the sheet, and none scrolls."""
    problems = at(page, name).evaluate(INSIDE)
    assert not problems, f"{name}: tasks leave the block on screen: {problems}"


def print_inside(server, client, mine, pages=1, solved=False):
    """The PDF: no dark pixel right of 196 mm on any page, and the PDF has the pages expected."""
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    query = "?solved=true" if solved else ""
    url = f"{server}/api/sheets/{mine}/pdf{query}"
    res = httpx.get(url, headers=cookie, timeout=60)
    assert res.status_code == 200
    doc = pypdfium2.PdfDocument(res.content)
    assert len(doc) == pages
    for n in range(pages):
        picture = doc[n].render(scale=8).to_pil().convert("L")
        per_mm = picture.width / 210
        strip = picture.crop((round(STRIP * per_mm), 0, picture.width, picture.height))
        dark = sum(v < 128 for v in strip.tobytes())
        assert dark == 0, f"page {n}: {dark} dark pixels past 196 mm in the PDF"


def a_block(client, block_more=None, **more):
    """A Geld block of A1: sums up to 100, 12 tasks, 3 columns by default, 60 mm high."""
    props = maths(client, ops=["+", "-"], max=100, money=True, count=12, **more)
    return box("m", "maths", props, y=20, h=60, **(block_more or {}))


def reference():
    """A text of 14 pt under the block: its type is the size a block of 14 pt draws at."""
    return box("t", "text", TEXT, z=2, x=15, w=180, y=100, h=20)


def test_a1_geld_tasks_stay_inside_on_screen(editor):
    """A1: a Geld block of three columns has every task inside its block and the sheet on screen."""
    client = user()
    page = editor(a_block(client, columns=3, size=14), client=client)
    inside(page, "m")


def test_a2_geld_tasks_stay_inside_in_the_pdf(editor, server):
    """A2: a Geld block of three columns has no task past the block's edge in the PDF."""
    client = user()
    page = editor(a_block(client, columns=3, size=14), client=client)
    print_inside(server, client, sheet_id(page))


WIDE = [
    {"format": "compare", "ops": ["+", "-"], "max": 1000000},
    {"format": "gap", "ops": ["*", "/"], "max": 1000000},
    {"format": "row", "ops": ["+", "-"], "max": 1000000},
    {"format": "row", "ops": ["+", "-"], "max": 1000000, "decimals": 2},
]
WIDE_IDS = ["A3-compare", "A4-gap", "A5-row", "A5-row-decimals"]


@pytest.mark.parametrize("props", WIDE, ids=WIDE_IDS)
def test_a3_to_a5_wide_formats_stay_inside_on_screen(editor, props):
    """A3 to A5: a wide Vergleichen, Lücke or Zeile block of three columns is inside on screen."""
    client = user()
    block = box("m", "maths", maths(client, count=12, columns=3, size=14, **props), y=20, h=60)
    page = editor(block, client=client)
    inside(page, "m")


@pytest.mark.parametrize("props", WIDE, ids=WIDE_IDS)
def test_a3_to_a5_wide_formats_stay_inside_in_the_pdf(editor, server, props):
    """A3 to A5: a wide Vergleichen, Lücke or Zeile block of three columns is inside the PDF."""
    client = user()
    block = box("m", "maths", maths(client, count=12, columns=3, size=14, **props), y=20, h=60)
    page = editor(block, client=client)
    print_inside(server, client, sheet_id(page))


def test_i1_a_fitting_block_keeps_its_size(editor):
    """I1: a block whose tasks fit has the font of a 14 pt text, and no --fit is set."""
    client = user()
    block = box("m", "maths", maths(client, ops=["+"], max=20, count=12), y=20, h=60)
    page = editor(block, reference(), client=client)
    root = at(page, "m").locator(".maths")
    font = root.evaluate(FONT)
    full = at(page, "t").locator(".frame").evaluate(FONT)
    assert abs(font - full) < 0.01, f"font {font} px, the 14 pt text {full} px"
    assert root.evaluate("el => el.style.getPropertyValue('--fit')") == ""


def test_i2_fewer_columns_bring_the_type_back_to_its_size(editor):
    """I2: wide tasks draw smaller; one column less at a time, the type comes back to its size."""
    client = user()
    page = editor(a_block(client, columns=3, size=14), reference(), client=client)
    pick(page, "m")
    root = at(page, "m").locator(".maths")
    full = at(page, "t").locator(".frame").evaluate(FONT)
    assert root.evaluate(FONT) < full - 0.01
    panel = page.locator(".panel .seg output")
    for columns in (2, 1):
        page.get_by_label("Eine Spalte weniger").click()
        expect(panel.nth(1)).to_have_text("1 Spalte" if columns == 1 else f"{columns} Spalten")
        assert root.evaluate(FONT) <= full + 0.01
    assert abs(root.evaluate(FONT) - full) < 0.01


def test_i3_a_numbered_block_stays_inside(editor):
    """I3: numbered tasks stay inside their block on screen."""
    client = user()
    page = editor(a_block(client, columns=3, size=14, numbering="1"), client=client)
    inside(page, "m")


def test_i3_numbering_set_in_the_panel_keeps_the_tasks_inside(editor):
    """I3: the numbering brings the bold cut, which loads late: the block fits again then."""
    client = user()
    page = editor(a_block(client, columns=3, size=14), client=client)
    pick(page, "m")
    page.locator(".panel").get_by_role("button", name="1 2 3", exact=True).first.click()
    expect(at(page, "m").locator(".maths b")).to_have_count(12)
    page.evaluate("document.fonts.ready.then(() => 0)")
    inside(page, "m")


def test_i4_a_turned_block_does_not_scroll(editor):
    """I4: a turned maths block keeps all its tasks in the block's width: no scroll."""
    client = user()
    block = a_block(client, block_more={"angle": 30}, columns=3, size=14)
    page = editor(block, client=client)
    root = at(page, "m").locator(".maths")
    assert root.evaluate("el => el.scrollWidth <= el.clientWidth + 1")


def test_i4_a_block_in_a_group_does_not_scroll(editor):
    """I4: a maths block inside a group keeps all its tasks in the block's width: no scroll."""
    client = user()
    page = editor(a_block(client, block_more={"group": ["g"]}, columns=3, size=14), client=client)
    root = at(page, "m").locator(".maths")
    assert root.evaluate("el => el.scrollWidth <= el.clientWidth + 1")


def test_i5_undo_brings_back_the_tasks_and_the_type(editor):
    """I5: Geld makes the tasks wider and smaller; one undo brings back the tasks and the size."""
    client = user()
    block = box("m", "maths", maths(client, ops=["+"], max=20, count=12), y=20, h=60)
    page = editor(block, client=client)
    pick(page, "m")
    root = at(page, "m").locator(".maths")
    before = (root.inner_text(), root.evaluate(FONT))
    page.locator(".panel").get_by_role("button", name="Geld", exact=True).click()
    expect(root).not_to_have_css("font-size", f"{before[1]}px")
    page.keyboard.press("Control+z")
    expect(root).to_have_css("font-size", f"{before[1]}px")
    assert root.inner_text() == before[0]


def test_i6_the_answer_key_stays_inside_and_in_the_pdf(editor, server):
    """I6: with the answers shown the Geld block stays inside, and so does the solved PDF."""
    client = user()
    page = editor(a_block(client, columns=3, size=14), client=client)
    tool(page, "Lösungen zeigen").click()
    inside(page, "m")
    print_inside(server, client, sheet_id(page), solved=True)


def test_i8_the_panel_hints_at_fewer_columns_only_while_tasks_are_too_wide(editor):
    """I8: wide tasks at three columns get a hint about fewer columns; one column, another hint."""
    client = user()
    page = editor(a_block(client, columns=3, size=14), client=client)
    pick(page, "m")
    hint = page.locator(".panel p.hint")
    expect(hint).to_contain_text("Für 3 Spalten sind die Aufgaben zu breit")
    page.get_by_label("Eine Spalte weniger").click()
    page.get_by_label("Eine Spalte weniger").click()
    expect(hint).to_have_count(0)


def a6_blocks(client):
    """Every Zahlenraum, column count and format on one sheet, each block its own id and z."""
    specs = []
    for room in ROOMS:
        for columns in range(1, 7):
            for fmt in FORMATS:
                props = maths(client, format=fmt, max=room, ops=["+", "-"], count=2 * columns)
                specs.append({**props, "columns": columns})
    specs += [
        {**maths(client, money=True, max=1000000, ops=["+", "-"], count=12), "columns": 6},
        {**maths(client, decimals=2, max=1000000, ops=["+", "-"], count=12), "columns": 6},
        {
            **maths(
                client,
                format="row",
                numbers=3,
                pvs=True,
                brackets=True,
                max=1000000,
                ops=["+", "-", "*", "/"],
                count=12,
            ),
            "columns": 6,
        },
        {
            **maths(
                client,
                format="gap",
                numbers=3,
                pvs=True,
                brackets=True,
                max=1000000,
                ops=["+", "-", "*", "/"],
                count=12,
            ),
            "columns": 6,
        },
        {**maths(client, format="written", max=1000000, ops=["*", "/"], count=12), "columns": 6},
    ]
    return [
        box(f"b{i}", "maths", props, z=i + 1, x=15, w=180, y=20, h=120)
        for i, props in enumerate(specs)
    ]


def test_a6_every_room_column_count_and_format_stays_inside_on_screen(editor):
    """A6: every block of the grid of rooms, columns and formats has its tasks inside, on screen."""
    client = user()
    blocks = a6_blocks(client)
    page = editor(*blocks, client=client)
    failures = {}
    for block in blocks:
        problems = at(page, block["id"]).evaluate(INSIDE)
        if problems:
            failures[block["id"]] = problems
    assert not failures, f"blocks with tasks outside: {failures}"


def test_a6_every_room_column_count_and_format_stays_inside_in_the_pdf(editor, server):
    """A6: the same sheet, printed: no task past the page on any page."""
    client = user()
    page = editor(*a6_blocks(client), client=client)
    print_inside(server, client, sheet_id(page))
