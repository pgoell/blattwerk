"""A maths block never grows past the foot of the page from the panel or the painter (issue #473).

The panel refuses a change that would make the block taller and end below the paper's edge: nothing
changes, and a line says why. A block that already ends below the edge says so. The PDF has every
task it was asked for. Each test names the case it proves.
"""

import math

import httpx
import pypdfium2
import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_maths_fit import inside
from test_painter import paint
from ui import at, box, doc, maths, pick, saved, user

FOOT = 297  # the page's height in mm
PT = 25.4 / 72  # mm per point, as sheet.tsx


def height(props):
    """The height in mm the app gives a maths block with these props, as sheet.tsx mathsHeight."""
    fams = {}
    for e in props["exercises"]:
        if "sign" not in e and e.get("family") is not None:
            fams[e["family"]] = fams.get(e["family"], 0) + 1
    if fams:
        lines = math.ceil(len(fams) / props["columns"])
        return max(
            10, math.floor(lines * (max(fams.values()) * 1.8 + 0.9) * props["size"] * PT + 0.5)
        )
    lines = math.ceil(len(props["exercises"]) / props["columns"])
    rows = max(
        [0]
        + [0 if "sign" in e else (e.get("grid") or {}).get("rows", 0) for e in props["exercises"]]
    )
    per = (rows + 1) * 5 if props["format"] == "written" else props["size"] * PT * 2.4
    return max(10, math.floor(lines * per + 0.5))


def click(name):
    return lambda page: page.get_by_label(name).click()


def panel(name):
    return lambda page: page.locator(".panel").get_by_role("button", name=name, exact=True).click()


def asked(action):
    """The action, and the answer to it: the new exercises have come from the server."""

    def run(page):
        with page.expect_response(lambda r: r.url.endswith("/api/maths")):
            action(page)

    return run


def refusal(page):
    expect(page.locator('[data-foot="full"]')).to_be_visible()


def on_sheet(page, name):
    """The block ends on the sheet: its bottom is at most the sheet's bottom, 1 mm of slack."""
    block = at(page, name).bounding_box()
    sheet = page.locator(".sheet").first.bounding_box()
    assert block["y"] + block["height"] <= sheet["y"] + sheet["height"] + 1, (
        "the block ends below the sheet"
    )


def tasks(page):
    return page.locator(".panel .seg output")


def test_a1_anzahl_stops_at_the_foot_with_neighbour_families(editor):
    """A1: one family more would end the block below the foot: the count stays, a line says why."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, family="neighbour", count=24, columns=3, size=14)
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    expect(tasks(page).first).to_have_text("24 Familien")
    on_sheet(page, "m")
    inside(page, "m")


@pytest.mark.parametrize(
    "case, props, action, grows",
    [
        pytest.param(
            "row-more", {"format": "row"}, click("Eine Aufgabe mehr"), True, id="row-more"
        ),
        pytest.param(
            "gap-more", {"format": "gap"}, click("Eine Aufgabe mehr"), True, id="gap-more"
        ),
        pytest.param(
            "compare-more",
            {"format": "compare"},
            click("Eine Aufgabe mehr"),
            True,
            id="compare-more",
        ),
        pytest.param(
            "written-more",
            {"format": "written"},
            click("Eine Aufgabe mehr"),
            True,
            id="written-more",
        ),
        pytest.param(
            "row-fewer-columns",
            {"format": "row"},
            click("Eine Spalte weniger"),
            True,
            id="row-fewer-columns",
        ),
        pytest.param(
            "row-bigger", {"format": "row"}, click("Schrift größer"), True, id="row-bigger"
        ),
        pytest.param(
            "row-written", {"format": "row"}, panel("Schriftlich"), True, id="row-written"
        ),
        pytest.param(
            "row-neighbour",
            {"format": "row", "ops": ["+"]},
            lambda page: page.get_by_label("Aufgabenfamilien").select_option("neighbour"),
            True,
            id="row-neighbour",
        ),
        pytest.param(
            "written-division",
            {"format": "written", "ops": ["+"]},
            panel(":"),
            True,
            id="written-division",
        ),
        pytest.param(
            "written-room",
            {"format": "written", "ops": ["/"], "max": 10},
            asked(lambda page: page.get_by_label("Zahlenraum").select_option("1000000")),
            True,
            id="written-room",
        ),
        pytest.param(
            "written-rest",
            {"format": "written", "ops": ["/"]},
            asked(panel("Mit Rest")),
            False,
            id="written-rest",
        ),
        pytest.param(
            "written-roll",
            {"format": "written", "ops": ["-", "/"]},
            asked(panel("Neu würfeln")),
            False,
            id="written-roll",
        ),
    ],
)
def test_a2_no_panel_change_pushes_the_block_past_the_foot(editor, case, props, action, grows):
    """A2: each change from the panel that would grow the block past the foot is refused."""
    client = user()
    mine = maths(
        client,
        ops=props.get("ops", ["+", "-"]),
        max=props.get("max", 100),
        count=12,
        columns=3,
        size=14,
        format=props["format"],
    )
    # The block's foot is 1 mm above the page's: the first line more passes it.
    page = editor(box("m", "maths", mine, y=FOOT - height(mine) - 1, h=height(mine)), client=client)
    pick(page, "m")
    action(page)
    if grows:
        refusal(page)
    else:
        # The new exercises are drawn: each of the 12 divisions has its svg.
        expect(at(page, "m").locator("svg")).to_have_count(12)
    on_sheet(page, "m")
    inside(page, "m")


def test_a3_at_the_stop_the_pdf_has_every_task(editor, server):
    """A3: the block stops at 12 tasks at the foot, and the PDF prints all 12."""
    client = user()
    props = maths(
        client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row", numbering="1"
    )
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id(page)}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    doc = pypdfium2.PdfDocument(res.content)
    assert len(doc) == 1
    text = doc[0].get_textpage().get_text_range()
    # Each task of a row has one "=": the PDF holds as many as the screen has tasks.
    assert text.count("=") == at(page, "m").locator(".maths > div").count() == 12, text[:300]


def test_i1_a_refused_click_is_no_step_of_undo(editor):
    """I1: a refused change is no undo step: one Control+z takes back the last change that went."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(tasks(page).first).to_have_text("11 Aufgaben")
    page.get_by_label("Eine Aufgabe mehr").click()
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(tasks(page).first).to_have_text("11 Aufgaben")


def test_i1b_a_quick_second_click_keeps_the_first_when_its_answer_is_late(editor):
    """I1b: two quick clicks on "mehr": the first answer comes late, and it still counts; the second is refused."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    held = []

    def hold(route):
        # The first answer waits until the second click is sent; then both go on.
        if held:
            held.pop().continue_()
            route.continue_()
        else:
            held.append(route)

    pick(page, "m")
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(tasks(page).first).to_have_text("11 Aufgaben")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(tasks(page).first).to_have_text("11 Aufgaben")


def test_i1c_a_quick_more_then_less_ends_at_the_height_it_had(editor):
    """I1c: "mehr" then "weniger" quickly, the first answer late: the second is measured on the
    block the first left, so the block ends with its 9 tasks at the height of 3 rows."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    held = []

    def hold(route):
        # The first answer waits until the second click is sent; then both go on.
        if held:
            held.pop().continue_()
            route.continue_()
        else:
            held.append(route)

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)
    expect(tasks(page).first).to_have_text("9 Aufgaben")
    (block,) = saved(page, client)
    assert block["h"] == height(props)


def test_i1d_two_quick_clicks_that_both_count_are_two_undo_steps(editor):
    """I1d: "mehr" twice quickly, the first answer late, both fit: one Control+z takes back one."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    held = []

    def hold(route):
        if held:
            held.pop().continue_()
            route.continue_()
        else:
            held.append(route)

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Aufgabe mehr").click()
    expect(at(page, "m").locator(".maths > div")).to_have_count(11)
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    expect(tasks(page).first).to_have_text("10 Aufgaben")


# Two frames: what a page answer brings is on the screen by then.
FRAMES = "() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))"


def test_i1e_a_retried_old_click_does_not_land_over_a_newer_one(editor):
    """I1e: "mehr" fails, its retry comes late, "weniger" was clicked meanwhile: "weniger" stays."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    pick(page, "m")
    page.route("**/api/maths", lambda route: route.abort())
    page.get_by_label("Eine Aufgabe mehr").click()
    again = page.get_by_role("button", name="Erneut versuchen")
    expect(again).to_be_visible()
    held = []
    page.unroute("**/api/maths")
    page.route("**/api/maths", lambda route: held.append(route) if not held else route.continue_())
    again.click()
    asked(click("Eine Aufgabe weniger"))(page)
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)
    with page.expect_response(lambda r: r.url.endswith("/api/maths")):
        held.pop().continue_()
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)
    expect(tasks(page).first).to_have_text("9 Aufgaben")


def test_i1f_a_click_before_a_refused_answer_builds_on_the_blocks_own(editor):
    """I1f: "mehr" is refused for want of room, "Spalte mehr" is clicked before that answer lands: it builds on the block's own 12 tasks."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    held = []

    def hold(route):
        if held:
            route.continue_()
        else:
            held.append(route)

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Spalte mehr").click()
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    held.pop().continue_()
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    (block,) = saved(page, client)
    assert block["props"]["columns"] == 4
    assert len(block["props"]["exercises"]) == block["props"]["count"]
    # Two undo steps, in the order they landed: the late answer, then the column.
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    page.keyboard.press("Control+z")
    expect(tasks(page).nth(1)).to_have_text("3 Spalten")


def test_i1g_a_limit_click_before_a_refused_answer_drops_the_refused_count(editor):
    """I1g: "mehr" is refused, "Neu würfeln" is clicked before that answer lands: it is applied on 12 tasks, not 13."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    sent = []

    def hold(route):
        # Only the first request waits; the ones after it, the retry of the second click too, go on.
        sent.append(route)
        if len(sent) > 1:
            route.continue_()

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_role("button", name="Neu würfeln").click()
    sent[0].continue_()
    expect(page.locator('[data-foot="full"]')).to_be_hidden()
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    (block,) = saved(page, client)
    assert block["props"]["count"] == 12
    assert len(block["props"]["exercises"]) == 12
    # Neu würfeln took: on master it carried the refused 13 and was refused with it.
    assert block["props"]["exercises"] != props["exercises"]


def test_i1h_a_failed_clicks_line_goes_when_a_later_click_lands(editor):
    """I1h: "mehr" fails, "weniger" lands after it: the line of the failed click goes, the block ends with 9 tasks."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    held = []

    def hold(route):
        if held:
            route.continue_()
        else:
            held.append(route)

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Aufgabe weniger").click()
    held.pop().abort()
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)
    expect(tasks(page).first).to_have_text("9 Aufgaben")
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(page.get_by_role("button", name="Erneut versuchen")).to_be_hidden()
    expect(
        page.locator(".notice.fault").filter(has_text="Die Aufgaben konnten nicht erzeugt werden")
    ).to_have_count(0)


def test_i1j_a_failed_clicks_change_rides_on_the_next_click(editor):
    """I1j: "mehr" fails, "Neu würfeln" lands after it: failed is not refused, so the block gets 10 tasks."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    held = []
    page.route("**/api/maths", lambda route: route.continue_() if held else held.append(route))
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_role("button", name="Neu würfeln").click()
    held.pop().abort()
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    expect(tasks(page).first).to_have_text("10 Aufgaben")
    expect(page.get_by_role("button", name="Erneut versuchen")).to_be_hidden()


def test_i1k_a_moot_retry_that_fails_again_says_nothing(editor):
    """I1k: "mehr" fails, its retry is on its way when "weniger" lands, then the retry fails too: no line."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    pick(page, "m")
    page.route("**/api/maths", lambda route: route.abort())
    page.get_by_label("Eine Aufgabe mehr").click()
    again = page.get_by_role("button", name="Erneut versuchen")
    expect(again).to_be_visible()
    held = []
    page.unroute("**/api/maths")
    page.route("**/api/maths", lambda route: route.continue_() if held else held.append(route))
    again.click()
    asked(click("Eine Aufgabe weniger"))(page)
    expect(tasks(page).first).to_have_text("9 Aufgaben")
    held.pop().abort()
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(again).to_be_hidden()
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)


def test_i2_the_line_goes_when_there_is_room_again(editor):
    """I2: after a refusal, one column more makes room: the line goes and one task more works."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    page.get_by_label("Eine Spalte mehr").click()
    expect(page.locator('[data-foot="full"]')).to_be_hidden()
    page.get_by_label("Eine Aufgabe mehr").click()
    expect(tasks(page).first).to_have_text("13 Aufgaben")


def test_i3_a_block_below_the_edge_says_so_and_can_still_shrink(editor):
    """I3: a block that ends below the edge says so, and one task less still works."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=280, h=height(props)), client=client)
    pick(page, "m")
    expect(page.locator('[data-foot="over"]')).to_be_visible()
    before = at(page, "m").bounding_box()["height"]
    # Four columns take three lines in place of four: the block gets shorter.
    page.get_by_label("Eine Spalte mehr").click()
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    assert at(page, "m").bounding_box()["height"] < before - 1, "the block did not get shorter"


def test_a_refused_own_zahlenraum_shows_the_blocks_in_the_field(editor):
    """#479: a refused own Zahlenraum leaves the field the block's number, not the refused one."""
    client = user()
    props = maths(client, ops=["/"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("100000")
    field.press("Enter")
    refusal(page)
    expect(field).to_be_focused()
    expect(field).to_have_value("100")


def test_a_refusal_that_comes_after_more_typing_leaves_the_field_as_typed(editor):
    """#479: the answer for 100000 comes after more typing: the field keeps what was typed."""
    client = user()
    props = maths(client, ops=["/"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    held = []
    page.route("**/api/maths", lambda route: held.append(route))
    field = page.get_by_label("Größte Zahl")
    with page.expect_request("**/api/maths"):
        field.fill("100000")
        field.press("Enter")
    # An empty field asks the server nothing: the answer for 100000 stays the last one.
    field.fill("")
    held[0].continue_()
    refusal(page)
    expect(field).to_be_focused()
    expect(field).to_have_value("")


def test_an_accepted_own_zahlenraum_keeps_what_was_typed_and_undo_shows_the_old(editor):
    """#479: a fitting own Zahlenraum keeps the typed number, and one undo shows the old one."""
    client = user()
    props = maths(client, ops=["/"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("1000")
    asked(lambda page: field.press("Enter"))(page)
    expect(field).to_have_value("1000")
    field.blur()
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(field).to_have_value("100")


def test_an_own_zahlenraum_above_the_limit_says_so_and_shows_the_used_number(editor):
    """#734: 50000000 is above the limit: a line says so, and Enter shows the number in use."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("50000000")
    expect(page.get_by_role("status").filter(has_text="Höchstens 1.000.000")).to_be_visible()
    field.press("Enter")
    stored = next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "m")
    expect(field).to_have_value(str(stored["props"]["max"]))
    expect(page.get_by_role("status").filter(has_text="Höchstens 1.000.000")).to_have_count(0)


def test_an_own_zahlenraum_below_one_says_so(editor):
    """#734: 0 is below the limit: a line says so, and Enter shows the number the exercises use."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("0")
    expect(page.get_by_role("status").filter(has_text="Mindestens 1")).to_be_visible()
    field.fill("50")
    expect(page.get_by_role("status").filter(has_text="Mindestens 1")).to_have_count(0)
    asked(lambda page: field.press("Enter"))(page)
    field.fill("0")
    field.press("Enter")
    expect(field).to_have_value("50")
    expect(page.get_by_role("status").filter(has_text="Mindestens 1")).to_have_count(0)


def test_a2_a_block_sized_by_hand_does_not_grow_past_the_foot(editor):
    """A2 by hand: a block of 20 mm counts growth from its own foot: one column more is refused."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=270, h=20), client=client)
    pick(page, "m")
    page.get_by_label("Eine Spalte mehr").click()
    refusal(page)
    on_sheet(page, "m")


def test_i7_a_turned_block_stops_at_its_lowest_corner(editor):
    """I7: a turned block counts its lowest corner, so one more task is refused at the foot."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    h, w = height(props), 180
    s, c = math.sin(math.radians(30)), math.cos(math.radians(30))
    # lowest = y + h/2 + (w|sin| + h|cos|)/2 ; put it at 296 mm.
    y = (FOOT - 1) - h / 2 - (w * s + h * c) / 2
    page = editor(box("m", "maths", props, y=round(y, 2), h=h, angle=30), client=client)
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    expect(tasks(page).first).to_have_text("12 Aufgaben")


def test_i4_the_painter_does_not_grow_a_maths_block_past_the_foot(editor):
    """I4: the painter lays 20 pt on a block at the foot: it keeps 14 pt and stays on the sheet."""
    client = user()
    big = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=20, format="row")
    small = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("a", "maths", big, y=20, h=height(big)),
        box("m", "maths", small, y=FOOT - height(small) - 1, h=height(small)),
        client=client,
    )
    paint(page, "a", "m")
    pick(page, "m")
    expect(tasks(page).nth(2)).to_have_text("14 pt")
    on_sheet(page, "m")


def test_i4_the_painter_does_not_grow_a_block_sized_by_hand(editor):
    """I4 by hand: the painter's 10 pt would move the foot below the page: the block keeps 14 pt."""
    client = user()
    small = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=10, format="row")
    mine = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("a", "maths", small, y=20, h=height(small)),
        box("m", "maths", mine, y=270, h=20),
        client=client,
    )
    paint(page, "a", "m")
    pick(page, "m")
    expect(tasks(page).nth(2)).to_have_text("14 pt")
    on_sheet(page, "m")


def test_an_own_zahlenraum_with_a_decimal_says_so(editor):
    """#734: 12.5 is no Zahlenraum: a line says so, and the exercises keep theirs."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("12.5")
    expect(page.get_by_role("status").filter(has_text="Nur ganze Zahlen")).to_be_visible()
    field.press("Enter")
    expect(field).to_have_value("100")


def test_typing_past_the_limit_never_applies_its_first_digits(editor):
    """#743: typing 1500000 applies no digit on the way. Enter applies 5000, one undo gives 100."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.select_text()
    field.press_sequentially("1500000")
    expect(page.get_by_role("status").filter(has_text="Höchstens 1.000.000")).to_be_visible()
    field.blur()
    expect(field).to_have_value("100")
    stored = next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "m")
    assert stored["props"]["max"] == 100
    field.fill("5000")
    asked(lambda page: field.press("Enter"))(page)
    expect(field).to_have_value("5000")
    field.blur()
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(field).to_have_value("100")
